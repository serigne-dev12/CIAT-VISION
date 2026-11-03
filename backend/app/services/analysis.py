"""Fonctions d'analyse AUTORISÉES pour l'assistant IA (cahier des charges § 6.7, V2).

C'est la seule porte d'accès de l'IA aux données :
- liste fermée de 12 fonctions, paramètres validés ;
- aucun SQL n'est écrit ni exécuté par le modèle ;
- aucune donnée personnelle (nom, e-mail, téléphone des porteurs) n'est renvoyée ;
- chaque résultat indique son périmètre (période, filtres) et les définitions des indicateurs utilisés.
"""
from __future__ import annotations

import unicodedata
from dataclasses import replace
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import ACTIVE_STATUSES, PROJECT_STATUSES, ProjectStatus
from app.models import Alert, Cohort, Domain, Project, Responsable
from app.services import kpi, objectives, risks
from app.services.common import has_simulated_data

# ------------------------------------------------------------------ schéma commun des filtres
_NULLABLE_LIST = {"type": ["array", "null"], "items": {"type": "string"}}
FILTRES_SCHEMA = {
    "type": "object",
    "description": "Périmètre de l'analyse. Mettre null pour ne pas filtrer. Reprendre les filtres actifs du "
                   "tableau de bord quand la question ne précise pas de périmètre.",
    "properties": {
        "cohortes": {**_NULLABLE_LIST, "description": "Noms exacts des cohortes (voir le référentiel)."},
        "domaines": {**_NULLABLE_LIST, "description": "Noms exacts des domaines (voir le référentiel)."},
        "statuts": {**_NULLABLE_LIST, "description": "Statuts de projet (voir le référentiel)."},
        "responsables": {**_NULLABLE_LIST, "description": "Noms exacts des responsables de suivi (référentiel)."},
        "date_debut": {"type": ["string", "null"], "description": "Début de période de dépôt, AAAA-MM-JJ."},
        "date_fin": {"type": ["string", "null"], "description": "Fin de période de dépôt, AAAA-MM-JJ."},
    },
    "required": ["cohortes", "domaines", "statuts", "responsables", "date_debut", "date_fin"],
    "additionalProperties": False,
}


def _tool(name: str, description: str, properties: dict) -> dict:
    return {"name": name, "description": description, "strict": True,
            "input_schema": {"type": "object", "properties": properties, "required": list(properties),
                             "additionalProperties": False}}


_LIMITE = {"type": "integer", "description": "Nombre maximum de lignes (1 à 30)."}

TOOLS = [
    _tool("indicateurs_cles",
          "Calcule les indicateurs clés officiels (projets, candidatures, actifs, terminés, retards, prototypes, "
          "financements, taux de sélection, d'achèvement et de retard, progression moyenne) sur un périmètre.",
          {"filtres": FILTRES_SCHEMA}),
    _tool("repartition_projets",
          "Répartit les projets selon une dimension : domaine, statut, cohorte, mois de dépôt, niveau de performance "
          "ou niveau de financement.",
          {"dimension": {"type": "string", "enum": ["domaine", "statut", "cohorte", "mois", "performance",
                                                    "financement"]},
           "filtres": FILTRES_SCHEMA}),
    _tool("projets_en_retard",
          "Liste les projets actifs en retard (date limite dépassée ou jalon en retard) avec l'ampleur du retard.",
          {"filtres": FILTRES_SCHEMA, "limite": _LIMITE}),
    _tool("comparer_cohortes",
          "Compare les indicateurs des cohortes côte à côte (taux de réussite, retards, progression, financements).",
          {"cohortes": {**_NULLABLE_LIST, "description": "Cohortes à comparer ; null pour toutes."}}),
    _tool("comparer",
          "Compare des domaines, des cohortes ou des responsables de suivi avec les mêmes définitions : nombre de "
          "projets, taux d'achèvement, progression moyenne, taux de retard, financement obtenu, prototypes.",
          {"dimension": {"type": "string", "enum": ["domaine", "cohorte", "responsable"]},
           "elements": {**_NULLABLE_LIST, "description": "Noms exacts à comparer ; null pour tous."},
           "filtres": FILTRES_SCHEMA}),
    _tool("synthese_financements",
          "Montants demandés, accordés et reçus regroupés par source, domaine, cohorte ou mois (évolution).",
          {"regroupement": {"type": "string", "enum": ["source", "domaine", "cohorte", "mois"]},
           "filtres": FILTRES_SCHEMA}),
    _tool("classement_projets",
          "Classe les projets actifs ou terminés du plus au moins performant selon l'écart entre progression réelle "
          "et progression attendue (temps écoulé), avec leur niveau de performance.",
          {"ordre": {"type": "string", "enum": ["meilleurs", "moins_bons"]}, "filtres": FILTRES_SCHEMA,
           "limite": _LIMITE}),
    _tool("analyse_risques",
          "Analyse des risques par règles transparentes : score de 0 à 100, niveau (Élevé, Modéré, Faible) et "
          "raisons de chaque projet actif ou suspendu, facteurs les plus fréquents. Ce n'est pas une prédiction.",
          {"filtres": FILTRES_SCHEMA, "limite": _LIMITE}),
    _tool("projets_a_surveiller",
          "Projets qui nécessitent une intervention : score de risque élevé ou modéré, avec les constats à "
          "l'origine du classement.", {"limite": _LIMITE}),
    _tool("alertes_actives",
          "Alertes actives du centre d'alertes (retards, échéances proches, progression ou financement insuffisants, "
          "objectifs non atteints, données manquantes, risques), par niveau de priorité.",
          {"niveau": {"type": ["string", "null"], "enum": ["Critique", "Élevé", "Moyen", "Information", None]},
           "limite": _LIMITE}),
    _tool("suivi_objectifs",
          "Objectifs fixés par le CIAT : cible, réalisé, pourcentage de réalisation, écart et statut.", {}),
    _tool("evolution_candidatures",
          "Évolution mensuelle des candidatures reçues, acceptées et rejetées.", {"filtres": FILTRES_SCHEMA}),
]
TOOL_NAMES = {t["name"] for t in TOOLS}


class AnalysisError(ValueError):
    """Paramètre invalide : le message est renvoyé au modèle pour qu'il corrige son appel."""


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn").strip()


def _resolve(db: Session, model, col, names: list[str] | None, label: str) -> list[int]:
    if not names:
        return []
    rows = {_norm(n): i for i, n in db.execute(select(model.id, col)).all()}
    ids = []
    for n in names:
        if _norm(n) not in rows:
            raise AnalysisError(f"{label} inconnu(e) : « {n} ». Valeurs possibles : "
                                + ", ".join(db.scalars(select(col))))
        ids.append(rows[_norm(n)])
    return ids


def build_filters(db: Session, f: dict | None) -> kpi.Filters:
    f = f or {}
    statuts = f.get("statuts") or []
    inconnus = [s for s in statuts if s not in PROJECT_STATUSES]
    if inconnus:
        raise AnalysisError(f"Statut(s) inconnu(s) : {inconnus}. Valeurs possibles : {PROJECT_STATUSES}")
    try:
        d1 = date.fromisoformat(f["date_debut"]) if f.get("date_debut") else None
        d2 = date.fromisoformat(f["date_fin"]) if f.get("date_fin") else None
    except ValueError:
        raise AnalysisError("Les dates doivent être au format AAAA-MM-JJ.") from None
    return kpi.Filters(start_date=d1, end_date=d2,
                       cohort_ids=_resolve(db, Cohort, Cohort.name, f.get("cohortes"), "Cohorte"),
                       domain_ids=_resolve(db, Domain, Domain.name, f.get("domaines"), "Domaine"), statuses=statuts,
                       responsible_ids=_resolve(db, Responsable, Responsable.full_name, f.get("responsables"),
                                                "Responsable"))


def filtres_vers_noms(db: Session, f: kpi.Filters) -> dict:
    """Convertit un périmètre (identifiants) en filtres nommés, tels que l'assistant les manipule."""
    def noms(model, col, ids):
        return list(db.scalars(select(col).where(model.id.in_(ids)))) if ids else None
    return {"cohortes": noms(Cohort, Cohort.name, f.cohort_ids), "domaines": noms(Domain, Domain.name, f.domain_ids),
            "statuts": f.statuses or None,
            "responsables": noms(Responsable, Responsable.full_name, f.responsible_ids),
            "date_debut": f.start_date.isoformat() if f.start_date else None,
            "date_fin": f.end_date.isoformat() if f.end_date else None}


def _limit(v: Any, maxi: int, defaut: int) -> int:
    try:
        return max(1, min(maxi, int(v)))
    except (TypeError, ValueError):
        return defaut


def _envelope(db: Session, f: kpi.Filters | None, donnees: Any, definitions: list[str] | None = None,
              methode: str | None = None) -> dict:
    out = {
        "perimetre": f.describe(db) if f else "Toutes les données",
        "periode_analysee": (f"dépôts du {f.start_date or 'début'} au {f.end_date or date.today()}" if f and
                             (f.start_date or f.end_date) else "toutes les périodes disponibles"),
        "donnees": donnees,
        "definitions": {k: kpi.KPI_DEFINITIONS[k][2] for k in (definitions or [])},
        "donnees_simulees": has_simulated_data(db),
        "date_du_calcul": date.today().isoformat(),
    }
    if methode:
        out["methode"] = methode
    return out


# ------------------------------------------------------------------ fonctions
def indicateurs_cles(db: Session, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    k = kpi.compute_kpis(db, f)
    donnees = {kpi.KPI_DEFINITIONS[key][0]: {"valeur": val, "affichage": kpi.format_value(key, val)}
               for key, val in k.items()}
    return _envelope(db, f, donnees, list(k))


def repartition_projets(db: Session, dimension: str, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    if dimension == "domaine":
        d = kpi.projects_by_domain(db, f)
    elif dimension == "statut":
        d = kpi.projects_by_status(db, f)
    elif dimension == "cohorte":
        d = [{"cohorte": c["cohort"], "candidatures": c["applications"], "projets": c["total_projects"]}
             for c in kpi.cohorts_comparison(db, f)]
    elif dimension == "mois":
        d = kpi.applications_monthly(db, f)
    elif dimension == "performance":
        return _envelope(db, f, kpi.level_distribution(db, f)["performance"], methode=kpi.DEFINITION_PERFORMANCE)
    elif dimension == "financement":
        return _envelope(db, f, kpi.level_distribution(db, f)["funding"], methode=kpi.DEFINITION_FINANCEMENT)
    else:
        raise AnalysisError("Dimension invalide : domaine, statut, cohorte, mois, performance ou financement.")
    return _envelope(db, f, d, ["total_projects"])


def projets_en_retard(db: Session, filtres: dict | None = None, limite: int | None = 10) -> dict:
    f = build_filters(db, filtres)
    tous = kpi.delayed_projects(db, f)  # sans le nom du porteur (données personnelles)
    return _envelope(db, f, {"nombre_total_en_retard": len(tous), "projets": tous[:_limit(limite, 30, 10)]},
                     ["delayed"])


def comparer_cohortes(db: Session, cohortes: list[str] | None = None) -> dict:
    f = kpi.Filters(cohort_ids=_resolve(db, Cohort, Cohort.name, cohortes, "Cohorte"))
    champs = ["applications", "selected", "selection_rate", "total_projects", "completed", "completion_rate",
              "delayed", "delay_rate", "avg_progress", "funding_granted", "funding_received", "avg_funding"]
    d = [{"cohorte": c["cohort"], **{kpi.KPI_DEFINITIONS[k][0]: kpi.format_value(k, c[k]) for k in champs}}
         for c in kpi.cohorts_comparison(db, f)]
    return _envelope(db, f, d, champs)


def comparer(db: Session, dimension: str, elements: list[str] | None = None, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    cible = {"domaine": ("domain", "domain_ids", Domain, Domain.name), "cohorte": ("cohort", "cohort_ids", Cohort,
                                                                                  Cohort.name),
             "responsable": ("responsible", "responsible_ids", Responsable, Responsable.full_name)}.get(dimension)
    if cible is None:
        raise AnalysisError("Dimension invalide : domaine, cohorte ou responsable.")
    by, champ, model, col = cible
    if elements:
        f = replace(f, **{champ: _resolve(db, model, col, elements, dimension.capitalize())})
    lignes = [{"element": g["label"], **{kpi.KPI_DEFINITIONS[k][0]: kpi.format_value(k, g[k])
                                        for k in kpi.COMPARISON_KPIS}, "valeurs": {k: g[k] for k in kpi.COMPARISON_KPIS}}
              for g in kpi.group_kpis(db, f, by)]
    return _envelope(db, f, lignes, kpi.COMPARISON_KPIS)


def synthese_financements(db: Session, regroupement: str, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    if regroupement == "mois":
        d = kpi.fundings_monthly(db, f)
    elif regroupement in ("source", "domaine", "cohorte"):
        d = kpi.fundings_by(db, f, {"source": "source", "domaine": "domain", "cohorte": "cohort"}[regroupement])
    else:
        raise AnalysisError("Regroupement invalide : source, domaine, cohorte ou mois.")
    k = kpi.compute_kpis(db, f)
    totaux = {kpi.KPI_DEFINITIONS[x][0]: kpi.format_value(x, k[x]) for x in
              ("funding_requested", "funding_granted", "funding_received", "remaining_to_receive", "uncovered_need",
               "planned_budget")}
    return _envelope(db, f, {"totaux": totaux, "detail_montants_fcfa": d},
                     ["funding_requested", "funding_granted", "funding_received", "remaining_to_receive",
                      "uncovered_need"])


def classement_projets(db: Session, ordre: str = "meilleurs", filtres: dict | None = None,
                       limite: int | None = 10) -> dict:
    f = build_filters(db, filtres)
    today = date.today()
    projets = db.scalars(select(Project).join(Project.application).where(
        *f.conditions(), Project.status.in_([*ACTIVE_STATUSES, ProjectStatus.COMPLETED]))).all()
    lignes = []
    for p in projets:
        attendu = risks.progression_attendue(p, today)
        if p.status == ProjectStatus.COMPLETED:
            ecart, niveau = None, "Élevée"
        elif attendu is None:
            continue
        else:
            ecart = round(p.progress_pct - attendu * 100, 1)
            niveau = "Élevée" if ecart >= -10 else ("Moyenne" if ecart >= -30 else "Faible")
        lignes.append({"projet": p.name, "id": p.id, "domaine": p.domain.name, "cohorte": p.cohort.name,
                       "statut": p.status, "progression_pct": p.progress_pct,
                       "progression_attendue_pct": None if attendu is None or ecart is None else round(attendu * 100, 1),
                       "ecart_points": ecart, "niveau_performance": niveau})
    # Terminés en tête des « meilleurs » ; puis par écart décroissant
    cle = (lambda x: (x["statut"] == ProjectStatus.COMPLETED, x["ecart_points"] if x["ecart_points"] is not None
                      else 999))
    lignes.sort(key=cle, reverse=(ordre != "moins_bons"))
    return _envelope(db, f, {"nombre_total": len(lignes), "projets": lignes[:_limit(limite, 30, 10)]},
                     methode=kpi.DEFINITION_PERFORMANCE)


def analyse_risques(db: Session, filtres: dict | None = None, limite: int | None = 10) -> dict:
    f = build_filters(db, filtres)
    a = risks.analyser(db, f)
    projets = [{"projet": e["name"], "id": e["project_id"], "domaine": e["domain"], "cohorte": e["cohort"],
                "statut": e["status"], "score": e["score"], "niveau": e["level"],
                "raisons": [x["detail"] for x in e["factors"]]} for e in a["projets"][:_limit(limite, 30, 10)]]
    return _envelope(db, f, {"nombre_projets_evalues": a["total"], "par_niveau": a["par_niveau"],
                             "facteurs_frequents": a["facteurs_frequents"], "projets": projets},
                     methode=a["modele"]["methode"] + " " + a["avertissement"])


def projets_a_surveiller(db: Session, limite: int | None = 10) -> dict:
    a = risks.analyser(db, kpi.Filters())
    retenus = [e for e in a["projets"] if e["level"] in ("Élevé", "Modéré")]
    projets = [{"projet": e["name"], "id": e["project_id"], "domaine": e["domain"], "cohorte": e["cohort"],
                "statut": e["status"], "progression_pct": e["progress_pct"], "score_risque": e["score"],
                "niveau": e["level"], "motifs": [x["detail"] for x in e["factors"]]} for e in retenus]
    return _envelope(db, kpi.Filters(), {"nombre_total": len(projets), "projets": projets[:_limit(limite, 30, 10)]},
                     methode=a["modele"]["methode"] + " " + a["avertissement"])


def alertes_actives(db: Session, niveau: str | None = None, limite: int | None = 15) -> dict:
    from app.services import alerts as svc_alertes
    svc_alertes.generer_si_necessaire(db)
    q = select(Alert).where(Alert.resolved_at.is_(None), Alert.archived_at.is_(None))
    if niveau:
        q = q.where(Alert.level == niveau)
    toutes = db.scalars(q).all()
    ordre = {n: i for i, n in enumerate(svc_alertes.NIVEAUX)}
    toutes = sorted(toutes, key=lambda a: ordre.get(a.level, 9))
    par_niveau: dict[str, int] = {}
    par_type: dict[str, int] = {}
    for a in toutes:
        par_niveau[a.level] = par_niveau.get(a.level, 0) + 1
        par_type[a.type] = par_type.get(a.type, 0) + 1
    return _envelope(db, None, {
        "nombre_total": len(toutes), "par_niveau": par_niveau, "par_type": par_type,
        "alertes": [{"niveau": a.level, "type": a.type, "titre": a.title, "probleme": a.problem,
                     "action_recommandee": a.recommended_action, "detectee_le": a.detected_at.date().isoformat()}
                    for a in toutes[:_limit(limite, 30, 15)]]})


def suivi_objectifs(db: Session) -> dict:
    return _envelope(db, None, objectives.lister(db),
                     methode="Valeurs réalisées mesurées par des événements datés dans la période de chaque objectif.")


def evolution_candidatures(db: Session, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    return _envelope(db, f, kpi.applications_monthly(db, f), ["applications", "selection_rate"])


FUNCTIONS = {
    "indicateurs_cles": lambda db, a: indicateurs_cles(db, a.get("filtres")),
    "repartition_projets": lambda db, a: repartition_projets(db, a.get("dimension", ""), a.get("filtres")),
    "projets_en_retard": lambda db, a: projets_en_retard(db, a.get("filtres"), a.get("limite")),
    "comparer_cohortes": lambda db, a: comparer_cohortes(db, a.get("cohortes")),
    "comparer": lambda db, a: comparer(db, a.get("dimension", ""), a.get("elements"), a.get("filtres")),
    "synthese_financements": lambda db, a: synthese_financements(db, a.get("regroupement", ""), a.get("filtres")),
    "classement_projets": lambda db, a: classement_projets(db, a.get("ordre") or "meilleurs", a.get("filtres"),
                                                           a.get("limite")),
    "analyse_risques": lambda db, a: analyse_risques(db, a.get("filtres"), a.get("limite")),
    "projets_a_surveiller": lambda db, a: projets_a_surveiller(db, a.get("limite")),
    "alertes_actives": lambda db, a: alertes_actives(db, a.get("niveau"), a.get("limite")),
    "suivi_objectifs": lambda db, a: suivi_objectifs(db),
    "evolution_candidatures": lambda db, a: evolution_candidatures(db, a.get("filtres")),
}


def run(db: Session, name: str, arguments: dict) -> dict:
    """Point d'entrée unique : refuse tout nom de fonction hors de la liste autorisée."""
    if name not in FUNCTIONS:
        raise AnalysisError(f"Fonction non autorisée : {name}.")
    if not isinstance(arguments, dict):
        raise AnalysisError("Les paramètres doivent être un objet JSON.")
    return FUNCTIONS[name](db, arguments)


def reference_data(db: Session) -> dict:
    return {"cohortes": list(db.scalars(select(Cohort.name).order_by(Cohort.year))),
            "domaines": list(db.scalars(select(Domain.name).order_by(Domain.name))),
            "responsables": list(db.scalars(select(Responsable.full_name).order_by(Responsable.full_name))),
            "statuts": PROJECT_STATUSES}
