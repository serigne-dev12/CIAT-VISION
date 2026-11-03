"""CIAT AI Analyst : assistant d'aide à la décision en langage naturel (cahier des charges § 6.7, V2).

Mode IA : le modèle Claude reçoit la question, les filtres actifs du tableau de bord et la liste des fonctions
d'analyse autorisées. Il demande l'exécution de fonctions ; le backend les exécute (paramètres validés) et lui
renvoie les résultats ; il rédige une réponse en trois niveaux (diagnostic, explication, recommandations) à partir
de ces seuls résultats.

Mode dégradé (pas de clé d'API, IA désactivée ou service indisponible) : reconnaissance de mots-clés qui appelle
directement la fonction d'analyse correspondante, avec les filtres actifs. Les trois niveaux sont produits par des
gabarits : aucun texte libre, aucun chiffre qui ne vienne d'une fonction d'analyse.
"""
from __future__ import annotations

import json
import logging
import unicodedata
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AIConversation, User
from app.services import analysis, kpi
from app.services.common import get_int_setting, get_setting, has_simulated_data

log = logging.getLogger("ciat.assistant")

MAX_TOURS = 6
MENTION_SIMULEES = ("⚠️ Ces résultats proviennent de **données simulées** : ils ne constituent pas des "
                    "statistiques officielles du CIAT.")

SYSTEM_PROMPT = """Tu es CIAT AI Analyst, l'assistant d'aide à la décision de la plateforme CIAT VISION du Centre \
d'Innovation, d'Application et de Transfert (CIAT) de l'ISEP Amadou Trawaré de Diamniadio (Sénégal). Tu réponds en \
français aux responsables du CIAT.

Tu n'as accès aux données QUE par les fonctions d'analyse fournies. Méthode :
1. Identifie les données nécessaires et appelle la ou les fonctions adaptées (plusieurs appels possibles).
2. Rédige ta réponse UNIQUEMENT à partir des résultats renvoyés. Chaque chiffre que tu cites doit figurer dans un \
résultat de fonction. N'invente jamais un chiffre, une tendance ou un nom de projet.
3. Si l'information n'est fournie par aucune fonction (chiffre d'affaires, satisfaction, données personnelles des \
porteurs…) ou si les données sont insuffisantes pour conclure, dis-le clairement.

Structure OBLIGATOIRE de la réponse, en trois niveaux :
**Diagnostic** – la situation en 1 à 3 phrases, avec les chiffres utiles.
**Explication** – les facteurs OBSERVABLES dans les résultats. Distingue explicitement les faits (« Constat : ») \
des hypothèses (« Hypothèse : », à vérifier sur le terrain).
**Recommandations** – 2 à 4 actions concrètes, présentées comme des propositions à examiner par la direction.
Termine par une ligne « Période et indicateurs : » qui indique la période analysée, le périmètre (filtres) et les \
définitions des indicateurs utilisés, et rappelle les limites éventuelles.
Montants en FCFA avec des espaces (12 500 000 FCFA), taux avec une décimale. Pas de tableaux Markdown.
{simulees}{filtres}
Référentiel (noms exacts à utiliser dans les filtres) :
- Cohortes : {cohortes}
- Domaines : {domaines}
- Responsables de suivi : {responsables}
- Statuts : {statuts}
Date du jour : {aujourdhui}."""


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def ai_available(db: Session) -> bool:
    return bool(get_settings().anthropic_api_key) and get_setting(db, "ai_enabled") == "true"


def questions_today(db: Session, user: User) -> int:
    debut = datetime.combine(date.today(), datetime.min.time(), tzinfo=UTC)
    return db.scalar(select(func.count(AIConversation.id)).where(AIConversation.user_id == user.id,
                                                                 AIConversation.created_at >= debut)) or 0


def _client():
    import anthropic
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key, timeout=120, max_retries=2)


# Point d'injection pour les tests (client simulé)
client_factory = _client


def _system(db: Session, actifs: kpi.Filters | None = None) -> str:
    ref = analysis.reference_data(db)
    bloc_filtres = ""
    if actifs is not None and not actifs.is_empty():
        bloc_filtres = (
            "\nFILTRES ACTIFS du tableau de bord de l'utilisateur : " + actifs.describe(db) + ".\nQuand la question "
            "ne précise pas de périmètre, applique ces filtres dans les fonctions (paramètre « filtres » : "
            + json.dumps(analysis.filtres_vers_noms(db, actifs), ensure_ascii=False) + ") et rappelle-le.")
    return SYSTEM_PROMPT.format(
        simulees=("IMPORTANT : la base contient des DONNÉES SIMULÉES ; rappelle-le dans la dernière ligne."
                  if has_simulated_data(db) else ""),
        filtres=bloc_filtres, cohortes=", ".join(ref["cohortes"]), domaines=", ".join(ref["domaines"]),
        responsables=", ".join(ref["responsables"]) or "aucun", statuts=", ".join(ref["statuts"]),
        aujourdhui=date.today().isoformat())


def _execute(db: Session, name: str, args: Any) -> tuple[dict | None, str | None]:
    try:
        return analysis.run(db, name, args if isinstance(args, dict) else {}), None
    except analysis.AnalysisError as e:
        return None, str(e)


def ask_ai(db: Session, question: str, history: list[dict], actifs: kpi.Filters | None = None) -> dict:
    """Boucle d'appel d'outils avec Claude. Renvoie {answer, tools, mode}."""
    client = client_factory()
    messages: list[dict] = []
    for h in history[-4:]:  # contexte léger : uniquement le texte des derniers échanges
        messages += [{"role": "user", "content": h["question"]}, {"role": "assistant", "content": h["answer"]}]
    messages.append({"role": "user", "content": question})
    system = _system(db, actifs)
    trace: list[dict] = []

    for _ in range(MAX_TOURS):
        resp = client.beta.messages.create(
            model=get_settings().ai_model,
            max_tokens=16000,
            system=system,
            tools=analysis.TOOLS,
            messages=messages,
            output_config={"effort": "medium"},
            # Repli automatique sur un autre modèle si la requête est déclinée par le modèle principal
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if resp.stop_reason == "refusal":
            return {"answer": "La demande n'a pas pu être traitée. Reformulez votre question.", "tools": trace,
                    "mode": "IA"}
        messages.append({"role": "assistant", "content": resp.content})  # contenu complet ré-injecté
        if resp.stop_reason != "tool_use":
            texte = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            return {"answer": texte or "(réponse vide)", "tools": trace, "mode": "IA"}

        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            out, err = _execute(db, block.name, block.input)
            trace.append({"name": block.name, "arguments": block.input, "result": out, "error": err})
            content = (f"ERREUR : {err}" if err else json.dumps(out, ensure_ascii=False, default=str))
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": content,
                            **({"is_error": True} if err else {})})
        messages.append({"role": "user", "content": results})

    return {"answer": "La question a nécessité trop d'étapes d'analyse. Posez une question plus précise.",
            "tools": trace, "mode": "IA"}


# ------------------------------------------------------------------ mode dégradé
def _fmt(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def _route(q: str, filtres: dict | None) -> tuple[str, dict] | None:
    """Associe une question à une fonction d'analyse (mots-clés). Les filtres actifs sont appliqués."""
    q = _norm(q)
    if "cette annee" in q or "annee en cours" in q:
        an = date.today().year
        vides = {"cohortes": None, "domaines": None, "statuts": None, "responsables": None}
        filtres = {**(filtres or vides), "date_debut": f"{an}-01-01", "date_fin": f"{an}-12-31"}
    if any(m in q for m in ("performant", "meilleurs projets", "plus avances", "top")):
        return "classement_projets", {"ordre": "meilleurs", "filtres": filtres, "limite": 10}
    if "alerte" in q:
        return "alertes_actives", {"niveau": None, "limite": 15}
    if "objectif" in q:
        return "suivi_objectifs", {}
    if any(m in q for m in ("intervention", "attention", "surveiller", "difficult", "risque", "recommand",
                            "action", "ameliorer")):
        return "analyse_risques", {"filtres": filtres, "limite": 10}
    if "retard" in q:
        return "projets_en_retard", {"filtres": filtres, "limite": 10}
    if "domaine" in q and any(m in q for m in ("meilleur", "resultat", "performan", "compar")):
        return "comparer", {"dimension": "domaine", "elements": None, "filtres": filtres}
    if "responsable" in q:
        return "comparer", {"dimension": "responsable", "elements": None, "filtres": filtres}
    if "cohorte" in q and any(m in q for m in ("meilleur", "compar", "resultat", "performan", "classement")):
        return "comparer_cohortes", {"cohortes": None}
    if any(m in q for m in ("evolu", "par mois", "mensuel")) and any(m in q for m in ("financ", "montant", "fcfa")):
        return "synthese_financements", {"regroupement": "mois", "filtres": filtres}
    if any(m in q for m in ("financ", "montant", "fcfa", "argent", "budget", "bailleur", "source")):
        return "synthese_financements", {"regroupement": "source", "filtres": filtres}
    if any(m in q for m in ("domaine", "secteur")):
        return "repartition_projets", {"dimension": "domaine", "filtres": filtres}
    if "statut" in q:
        return "repartition_projets", {"dimension": "statut", "filtres": filtres}
    if any(m in q for m in ("candidature", "mensuel", "evolution", "par mois")):
        return "evolution_candidatures", {"filtres": filtres}
    if "cohorte" in q:
        return "comparer_cohortes", {"cohortes": None}
    if any(m in q for m in ("combien", "nombre", "total", "taux", "indicateur", "kpi", "reussite", "achevement",
                            "incub", "prototype", "termine", "selection", "progression", "situation", "bilan")):
        return "indicateurs_cles", {"filtres": filtres}
    return None


def _pct(v) -> str:
    return "non calculable" if v is None else f"{v * 100:.1f} %".replace(".", ",")


def _trois_niveaux(name: str, r: dict) -> tuple[str, str, str]:
    """(diagnostic, explication, recommandations) à partir des seuls résultats de la fonction."""
    d = r["donnees"]
    if name == "indicateurs_cles":
        v = lambda c: d[c]["affichage"]  # noqa: E731
        diag = (f"{v('Total des projets')} projets ({v('Projets actifs')} actifs, {v('Projets terminés')} terminés, "
                f"{v('Projets en retard')} en retard) pour {v('Candidatures reçues')} candidatures.")
        achevement = v("Taux d'achèvement")
        expl = (f"Constat : taux de sélection {v('Taux de sélection')}, taux d'achèvement {achevement}, "
                f"taux de retard {v('Taux de retard')}, progression moyenne {v('Progression moyenne')}, "
                f"{v('Prototypes réalisés')} prototypes, {v('Financements reçus')} reçus.")
        reco = ("Suivre en priorité les projets en retard (page Alertes) ; comparer les domaines et les cohortes pour "
                "repérer où se concentrent les difficultés.")
    elif name == "projets_en_retard":
        lignes = [f"{p['name']} ({p['domain']}) : {p['days_late']} jours, progression {p['progress_pct']} %"
                  for p in d["projets"]]
        diag = f"{d['nombre_total_en_retard']} projet(s) actif(s) en retard."
        expl = "Constat : les retards les plus importants — " + ("; ".join(lignes) if lignes else "aucun") + "."
        reco = ("Programmer un point de suivi avec chaque porteur concerné et réviser les jalons irréalistes ; "
                "examiner en comité les retards de plus de 90 jours.")
    elif name in ("comparer", "comparer_cohortes"):
        if not d:
            return "Aucune donnée sur ce périmètre.", "Données insuffisantes pour comparer.", "Élargir les filtres."
        cle = "element" if name == "comparer" else "cohorte"
        ach = "Taux d'achèvement"

        def taux(x):
            return -1.0 if x[ach] == "non calculable" else float(x[ach].split()[0].replace(",", "."))
        meilleur = max(d, key=taux)
        diag = f"Meilleur taux d'achèvement : {meilleur[cle]} ({meilleur[ach]})."
        expl = "Constat : " + " ; ".join(f"{x[cle]} – achèvement {x[ach]}, retard {x['Taux de retard']}, "
                                          f"progression {x['Progression moyenne']}" for x in d) + (
            ". Hypothèse : une cohorte en cours a mécaniquement un taux d'achèvement faible.")
        reco = "Analyser les pratiques du meilleur élément et les diffuser ; accompagner en priorité les moins avancés."
    elif name == "synthese_financements":
        t = d["totaux"]
        diag = f"{t['Financements accordés']} accordés, dont {t['Financements reçus']} reçus."
        detail = d["detail_montants_fcfa"]
        if detail and "month" in detail[0]:
            expl = "Constat (par mois de demande) : " + " ; ".join(
                f"{x['month']} : {_fmt(x['granted'])} accordés" for x in detail[-6:]) + "."
        else:
            expl = "Constat : " + " ; ".join(f"{x['label']} : {_fmt(x['granted'])} FCFA accordés" for x in detail) + \
                   f". Reste à recevoir {t['Reste à recevoir']} ; besoin non couvert {t['Besoin non couvert']}."
        reco = "Relancer les bailleurs pour les montants accordés non versés ; orienter les projets sous-financés vers " \
               "de nouveaux partenaires."
    elif name == "classement_projets":
        lignes = [f"{p['projet']} ({p['statut']}, {p['progression_pct']} %"
                  + (f", écart {p['ecart_points']:+} pts" if p["ecart_points"] is not None else "") + ")"
                  for p in d["projets"]]
        diag = f"{d['nombre_total']} projet(s) classé(s) selon leur niveau de performance."
        expl = "Constat : " + "; ".join(lignes) + ". " + r.get("methode", "")
        reco = "Valoriser les projets les plus avancés (vitrine, investisseurs) et partager leurs pratiques."
    elif name in ("analyse_risques", "projets_a_surveiller"):
        projets = d["projets"]
        if name == "analyse_risques":
            diag = (f"{d['nombre_projets_evalues']} projets évalués : {d['par_niveau']['Élevé']} à risque élevé, "
                    f"{d['par_niveau']['Modéré']} modéré, {d['par_niveau']['Faible']} faible.")
            freq = "; ".join(f"{x['facteur']} ({x['projets']} projets)" for x in d["facteurs_frequents"][:4])
            expl = f"Constat : facteurs les plus fréquents — {freq}. Projets prioritaires — " + "; ".join(
                f"{p['projet']} (score {p['score']})" for p in projets[:5]) + "."
        else:
            diag = f"{d['nombre_total']} projet(s) nécessitent une intervention (risque élevé ou modéré)."
            expl = "Constat : " + "; ".join(f"{p['projet']} : " + ", ".join(p["motifs"][:2]) for p in projets[:5]) + "."
        expl += " Hypothèse : les causes réelles (techniques, financières, personnelles) restent à vérifier avec les " \
                "porteurs."
        reco = ("1. Réunir le comité de suivi sur les projets à risque élevé et fixer un plan d'action daté. "
                "2. Mettre à jour les fiches sans mise à jour récente. 3. Orienter les projets sous-financés vers les "
                "partenaires financiers.")
    elif name == "alertes_actives":
        diag = f"{d['nombre_total']} alerte(s) active(s) : " + ", ".join(f"{k} {v}" for k, v in d["par_niveau"].items()) \
            + "."
        expl = "Constat : " + "; ".join(f"{k} : {v}" for k, v in d["par_type"].items()) + "."
        reco = "Traiter d'abord les alertes critiques (page Alertes) en suivant l'action recommandée de chacune."
    elif name == "suivi_objectifs":
        diag = f"{len(d)} objectif(s) suivi(s) : " + ", ".join(
            f"{o['status']} ({sum(1 for x in d if x['status'] == o['status'])})"
            for o in {x['status']: x for x in d}.values()) + "."
        expl = "Constat : " + "; ".join(
            f"{o['label']} – {o['current']:,.0f} / {o['target']:,.0f} ({o['status']})".replace(",", " ") for o in d) + "."
        reco = "Réexaminer en comité les objectifs en retard : moyens supplémentaires ou cible révisée."
    elif name == "repartition_projets":
        lignes = []
        for x in d:
            if "domain" in x:
                lignes.append(f"{x['domain']} : {x['projects']} projets")
            elif "status" in x:
                lignes.append(f"{x['status']} : {x['count']}")
            elif "cohorte" in x:
                lignes.append(f"{x['cohorte']} : {x['projets']} projets")
            elif "level" in x:
                lignes.append(f"{x['level']} : {x['count']}")
        diag = "Répartition : " + "; ".join(lignes[:4]) + ("…" if len(lignes) > 4 else ".")
        expl = "Constat : " + "; ".join(lignes) + "."
        reco = "Comparer ensuite les performances par domaine pour savoir si la taille d'un domaine va avec ses résultats."
    elif name == "evolution_candidatures":
        diag = f"{sum(x['received'] for x in d)} candidatures sur {len(d)} mois de dépôt."
        expl = "Constat : " + "; ".join(f"{x['month']} : {x['received']} reçues, {x['accepted']} acceptées"
                                        for x in d[-6:]) + "."
        reco = "Anticiper les campagnes d'appel à candidatures sur les mois de forte affluence."
    else:
        return "Résultat disponible.", json.dumps(d, ensure_ascii=False)[:1500], "—"
    return diag, expl, reco


def ask_degraded(db: Session, question: str, reason: str, actifs: kpi.Filters | None = None) -> dict:
    filtres = analysis.filtres_vers_noms(db, actifs) if actifs is not None and not actifs.is_empty() else None
    route = _route(question, filtres)
    if route is None:
        return {"answer": (f"{reason}\n\nJe n'ai pas reconnu la question. Je peux répondre sur : les indicateurs "
                           "clés, les projets les plus performants, les projets en retard ou nécessitant une "
                           "intervention, les risques, les alertes, les objectifs, la comparaison des domaines, "
                           "cohortes ou responsables, les financements et leur évolution, l'évolution des "
                           "candidatures."), "tools": [], "mode": "dégradé"}
    name, args = route
    out, err = _execute(db, name, args)
    if err:
        return {"answer": f"{reason}\n\nErreur : {err}", "tools": [{"name": name, "arguments": args, "result": None,
                                                                    "error": err}], "mode": "dégradé"}
    diag, expl, reco = _trois_niveaux(name, out)
    defs = "; ".join(f"{k} = {v}" for k, v in list(out.get("definitions", {}).items())[:4])
    texte = (f"{reason}\n\n**Diagnostic** – {diag}\n\n**Explication** – {expl}\n\n**Recommandations** – {reco}\n\n"
             f"Période et indicateurs : {out['periode_analysee']} ; périmètre « {out['perimetre']} »"
             + (f" ; définitions : {defs}" if defs else "")
             + ". Réponse automatique sans IA générative (gabarits appliqués aux résultats des fonctions d'analyse).")
    return {"answer": texte, "tools": [{"name": name, "arguments": args, "result": out, "error": None}],
            "mode": "dégradé"}


# ------------------------------------------------------------------ point d'entrée
def ask(db: Session, user: User, question: str, actifs: kpi.Filters | None = None) -> dict:
    limite = get_int_setting(db, "ai_daily_limit")
    if questions_today(db, user) >= limite:
        return {"answer": f"Limite quotidienne de {limite} questions atteinte. Réessayez demain.", "tools": [],
                "mode": "limite", "simulated": has_simulated_data(db)}

    history = [{"question": c.question, "answer": c.answer} for c in db.scalars(
        select(AIConversation).where(AIConversation.user_id == user.id).order_by(AIConversation.id.desc()).limit(4))][::-1]

    if ai_available(db):
        try:
            res = ask_ai(db, question, history, actifs)
        except Exception as e:  # réseau, quota, clé invalide… → on reste utile en mode dégradé
            log.warning("Assistant IA indisponible : %s", e)
            res = ask_degraded(db, question, "ℹ️ Le service d'IA est momentanément indisponible : réponse en "
                                             "mode dégradé.", actifs)
    else:
        res = ask_degraded(db, question, "ℹ️ Mode dégradé : l'IA générative n'est pas configurée sur ce serveur.",
                           actifs)

    res["simulated"] = has_simulated_data(db)
    res["filters"] = actifs.describe(db) if actifs is not None and not actifs.is_empty() else None
    if res["simulated"] and MENTION_SIMULEES not in res["answer"]:
        res["answer"] = f"{res['answer']}\n\n{MENTION_SIMULEES}"

    db.add(AIConversation(user_id=user.id, question=question, answer=res["answer"], mode=res["mode"],
                          tools_used=json.loads(json.dumps(res["tools"], default=str, ensure_ascii=False))))
    return res


# ------------------------------------------------------------------ commentaires des rapports
def rule_based_commentary(k: dict) -> str:
    """Commentaire analytique déterministe (utilisé sans IA, et comme base vérifiable)."""
    f = kpi.format_value
    phrases = [f"Sur le périmètre analysé, {f('applications', k['applications'])} candidatures ont été reçues et "
               f"{f('selected', k['selected'])} projets sélectionnés (taux de sélection : "
               f"{f('selection_rate', k['selection_rate'])})."]
    phrases.append(f"{f('completed', k['completed'])} projets sont terminés, soit un taux d'achèvement de "
                   f"{f('completion_rate', k['completion_rate'])} des projets incubés ; "
                   f"{f('prototypes', k['prototypes'])} prototypes ont été réalisés.")
    phrases.append(f"{f('delayed', k['delayed'])} projets actifs sont en retard ({f('delay_rate', k['delay_rate'])} "
                   f"des projets actifs) et la progression moyenne des projets actifs atteint "
                   f"{f('avg_progress', k['avg_progress'])}.")
    phrases.append(f"Les financements accordés s'élèvent à {f('funding_granted', k['funding_granted'])}, dont "
                   f"{f('funding_received', k['funding_received'])} effectivement reçus ; le besoin non couvert est "
                   f"de {f('uncovered_need', k['uncovered_need'])}.")
    reco = []
    if (k["delay_rate"] or 0) >= 0.2:
        reco.append("Mettre en place un point de suivi mensuel des projets en retard et réviser leurs jalons.")
    if k["funding_granted"] and k["funding_received"] < 0.8 * k["funding_granted"]:
        reco.append("Relancer les bailleurs pour accélérer le versement des montants accordés.")
    if k["uncovered_need"] > 0:
        reco.append("Orienter les projets sous-financés vers de nouveaux partenaires financiers.")
    if (k["selection_rate"] or 0) < 0.3:
        reco.append("Renforcer l'accompagnement des candidats en amont pour améliorer la qualité des dossiers.")
    if not reco:
        reco.append("Maintenir le dispositif de suivi actuel et capitaliser sur les bonnes pratiques des projets terminés.")
    return " ".join(phrases) + "\n\nRecommandations :\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(reco, 1))


def ai_commentary(db: Session, k: dict, perimetre: str, titre: str) -> tuple[str, str]:
    """Commentaire rédigé par l'IA à partir des seuls indicateurs. Renvoie (texte, mode)."""
    if not ai_available(db):
        return rule_based_commentary(k), "automatique"
    lignes = "\n".join(f"- {kpi.KPI_DEFINITIONS[key][0]} : {kpi.format_value(key, v)}" for key, v in k.items())
    try:
        resp = client_factory().beta.messages.create(
            model=get_settings().ai_model,
            max_tokens=4000,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=("Tu es analyste au CIAT de l'ISEP Amadou Trawaré de Diamniadio. Rédige en français un "
                    "commentaire analytique sobre pour un rapport officiel, à partir des SEULS indicateurs fournis, "
                    "sans inventer aucun chiffre. Format : un paragraphe de 4 à 6 phrases, puis « Recommandations : » "
                    "suivi de 3 recommandations numérotées, concrètes. Texte brut, sans Markdown."
                    + (" Mentionne que les données sont simulées." if has_simulated_data(db) else "")),
            messages=[{"role": "user", "content": f"Rapport : {titre}\nPérimètre : {perimetre}\n\n{lignes}"}],
        )
        if resp.stop_reason == "refusal":
            raise RuntimeError("refus")
        texte = "\n".join(b.text for b in resp.content if b.type == "text").strip()
        return (texte or rule_based_commentary(k)), "IA"
    except Exception as e:
        log.warning("Commentaire IA indisponible : %s", e)
        return rule_based_commentary(k), "automatique"
