"""CIAT AI Analyst : assistant d'interrogation des données en langage naturel (cahier des charges § 6.7).

Mode IA : le modèle Claude reçoit la question et la liste des fonctions d'analyse autorisées. Il demande
l'exécution de fonctions ; le backend les exécute (paramètres validés) et lui renvoie les résultats ; il rédige
la réponse à partir de ces seuls résultats.

Mode dégradé (pas de clé d'API, IA désactivée ou service indisponible) : reconnaissance de mots-clés qui appelle
directement la fonction d'analyse correspondante. Aucune rédaction libre : les chiffres sont mis en forme par
des gabarits.
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

SYSTEM_PROMPT = """Tu es CIAT AI Analyst, l'assistant d'analyse de la plateforme CIAT VISION du Centre \
d'Innovation, d'Application et de Transfert (CIAT) de l'ISEP Amadou Trawaré de Diamniadio (Sénégal). \
Tu réponds en français aux responsables du CIAT.

Tu n'as accès aux données QUE par les fonctions d'analyse fournies. Méthode :
1. Identifie les données nécessaires et appelle la ou les fonctions adaptées (plusieurs appels possibles).
2. Rédige ta réponse UNIQUEMENT à partir des résultats renvoyés. Chaque chiffre que tu cites doit figurer \
dans un résultat de fonction. N'invente jamais un chiffre, une tendance ou un nom de projet.
3. Si la question porte sur une information qu'aucune fonction ne fournit (chiffre d'affaires, satisfaction, \
données personnelles des porteurs…), dis clairement que l'information n'est pas disponible dans la plateforme.
4. Si une fonction renvoie une erreur, corrige les paramètres (noms exacts du référentiel) et réessaie.

Format de la réponse :
- d'abord la réponse directe en une ou deux phrases ;
- puis 2 à 5 puces « Chiffres utilisés » (avec le périmètre) ;
- si la question le demande, une section « Recommandations » : des propositions à examiner par la direction, \
clairement distinguées des constats ;
- termine par « Limites : » en une phrase (périmètre, définition utilisée, données manquantes).
Montants en FCFA avec des espaces (12 500 000 FCFA), taux avec une décimale. Pas de tableaux Markdown.
{simulees}
Référentiel (noms exacts à utiliser dans les filtres) :
- Cohortes : {cohortes}
- Domaines : {domaines}
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


def _system(db: Session) -> str:
    ref = analysis.reference_data(db)
    return SYSTEM_PROMPT.format(
        simulees=("IMPORTANT : la base contient des DONNÉES SIMULÉES ; rappelle-le dans « Limites »."
                  if has_simulated_data(db) else ""),
        cohortes=", ".join(ref["cohortes"]), domaines=", ".join(ref["domaines"]), statuts=", ".join(ref["statuts"]),
        aujourdhui=date.today().isoformat())


def _execute(db: Session, name: str, args: Any) -> tuple[dict | None, str | None]:
    try:
        return analysis.run(db, name, args if isinstance(args, dict) else {}), None
    except analysis.AnalysisError as e:
        return None, str(e)


def ask_ai(db: Session, question: str, history: list[dict]) -> dict:
    """Boucle d'appel d'outils avec Claude. Renvoie {answer, tools, mode}."""
    client = client_factory()
    messages: list[dict] = []
    for h in history[-4:]:  # contexte léger : uniquement le texte des derniers échanges
        messages += [{"role": "user", "content": h["question"]}, {"role": "assistant", "content": h["answer"]}]
    messages.append({"role": "user", "content": question})
    system = _system(db)
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


def _route(q: str) -> tuple[str, dict] | None:
    q = _norm(q)
    if any(m in q for m in ("attention", "surveiller", "risque", "difficult", "recommand", "ameliorer", "alerte")):
        return "projets_a_surveiller", {"limite": 10}
    if "retard" in q:
        return "projets_en_retard", {"filtres": None, "limite": 10}
    if "cohorte" in q and any(m in q for m in ("meilleur", "compar", "resultat", "performan", "classement")):
        return "comparer_cohortes", {"cohortes": None}
    if any(m in q for m in ("financ", "montant", "fcfa", "argent", "budget", "bailleur", "source")):
        return "synthese_financements", {"regroupement": "source", "filtres": None}
    if any(m in q for m in ("domaine", "secteur")):
        return "repartition_projets", {"dimension": "domaine", "filtres": None}
    if "statut" in q:
        return "repartition_projets", {"dimension": "statut", "filtres": None}
    if any(m in q for m in ("candidature", "mensuel", "evolution", "par mois")):
        return "evolution_candidatures", {"filtres": None}
    if "cohorte" in q:
        return "comparer_cohortes", {"cohortes": None}
    if any(m in q for m in ("combien", "nombre", "total", "taux", "indicateur", "kpi", "reussite", "achevement",
                            "incub", "prototype", "termine", "selection", "progression")):
        return "indicateurs_cles", {"filtres": None}
    return None


def _template(name: str, r: dict) -> str:
    d = r["donnees"]
    if name == "indicateurs_cles":
        cles = ["Total des projets", "Candidatures reçues", "Projets sélectionnés", "Projets en incubation",
                "Prototypes réalisés", "Projets terminés", "Projets en retard", "Taux de sélection",
                "Taux d'achèvement", "Taux de retard", "Progression moyenne", "Financements reçus"]
        return "Indicateurs clés :\n" + "\n".join(f"- {c} : {d[c]['affichage']}" for c in cles if c in d)
    if name == "projets_en_retard":
        lignes = [f"- {p['name']} ({p['domain']}, {p['cohort']}) : {p['days_late']} jours de retard, "
                  f"progression {p['progress_pct']} %" for p in d["projets"]]
        return f"{d['nombre_total_en_retard']} projet(s) en retard. Les plus importants :\n" + "\n".join(lignes)
    if name == "comparer_cohortes":
        if not d:
            return "Aucune cohorte avec des données."
        ach = "Taux d'achèvement"

        def taux(c: dict) -> float:
            return -1.0 if c[ach] == "non calculable" else float(c[ach].split()[0].replace(",", "."))

        meilleure = max(d, key=taux)
        lignes = [f"- {c['cohorte']} : achèvement {c[ach]}, retard {c['Taux de retard']}, progression moyenne "
                  f"{c['Progression moyenne']}, financements reçus {c['Financements reçus']}" for c in d]
        return (f"Meilleur taux d'achèvement : {meilleure['cohorte']}.\n" + "\n".join(lignes))
    if name == "synthese_financements":
        t = d["totaux"]
        lignes = [f"- {x['label']} : {_fmt(x['granted'])} FCFA accordés, {_fmt(x['received'])} FCFA reçus"
                  for x in d["detail_montants_fcfa"]]
        return ("Financements :\n" + "\n".join(f"- {k} : {v}" for k, v in t.items())
                + "\n\nPar source :\n" + "\n".join(lignes))
    if name == "repartition_projets":
        lignes = []
        for x in d:
            if "domain" in x:
                lignes.append(f"- {x['domain']} : {x['projects']} projets ({x['applications']} candidatures)")
            elif "status" in x:
                lignes.append(f"- {x['status']} : {x['count']}")
            elif "cohorte" in x:
                lignes.append(f"- {x['cohorte']} : {x['projets']} projets")
        return "Répartition :\n" + "\n".join(lignes)
    if name == "projets_a_surveiller":
        lignes = [f"- {p['projet']} ({p['domaine']}) : " + " ; ".join(p["motifs"]) for p in d["projets"]]
        return (f"{d['nombre_total']} projet(s) actif(s) présentent au moins un signal d'alerte. Priorités :\n"
                + "\n".join(lignes)
                + "\n\nPistes : programmer un point de suivi avec les projets en retard, réviser les jalons "
                  "irréalistes et orienter les projets sous-financés vers les partenaires financiers.")
    if name == "evolution_candidatures":
        lignes = [f"- {x['month']} : {x['received']} reçues, {x['accepted']} acceptées, {x['rejected']} rejetées"
                  for x in d]
        return "Candidatures par mois de dépôt :\n" + "\n".join(lignes)
    return json.dumps(d, ensure_ascii=False)[:2000]


def ask_degraded(db: Session, question: str, reason: str) -> dict:
    route = _route(question)
    if route is None:
        return {"answer": (f"{reason}\n\nJe n'ai pas reconnu la question. Je peux répondre sur : les indicateurs "
                           "clés, les projets en retard, la comparaison des cohortes, les financements, la "
                           "répartition par domaine ou par statut, l'évolution des candidatures et les projets "
                           "nécessitant une attention particulière."), "tools": [], "mode": "dégradé"}
    name, args = route
    out, err = _execute(db, name, args)
    texte = _template(name, out) if out else f"Erreur : {err}"
    return {"answer": f"{reason}\n\n{texte}\n\nLimites : réponse automatique sans IA générative, "
                      f"périmètre « {out['perimetre'] if out else '—'} ».",
            "tools": [{"name": name, "arguments": args, "result": out, "error": err}], "mode": "dégradé"}


# ------------------------------------------------------------------ point d'entrée
def ask(db: Session, user: User, question: str) -> dict:
    limite = get_int_setting(db, "ai_daily_limit")
    if questions_today(db, user) >= limite:
        return {"answer": f"Limite quotidienne de {limite} questions atteinte. Réessayez demain.", "tools": [],
                "mode": "limite", "simulated": has_simulated_data(db)}

    history = [{"question": c.question, "answer": c.answer} for c in db.scalars(
        select(AIConversation).where(AIConversation.user_id == user.id).order_by(AIConversation.id.desc()).limit(4))][::-1]

    if ai_available(db):
        try:
            res = ask_ai(db, question, history)
        except Exception as e:  # réseau, quota, clé invalide… → on reste utile en mode dégradé
            log.warning("Assistant IA indisponible : %s", e)
            res = ask_degraded(db, question, "ℹ️ Le service d'IA est momentanément indisponible : réponse en "
                                             "mode dégradé.")
    else:
        res = ask_degraded(db, question, "ℹ️ Mode dégradé : l'IA générative n'est pas configurée sur ce serveur.")

    res["simulated"] = has_simulated_data(db)
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
