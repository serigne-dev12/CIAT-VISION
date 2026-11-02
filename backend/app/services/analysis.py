"""Fonctions d'analyse AUTORISÉES pour l'assistant IA (cahier des charges § 6.7).

C'est la seule porte d'accès de l'IA aux données :
- liste fermée de 7 fonctions, paramètres validés ;
- aucun SQL n'est écrit ni exécuté par le modèle ;
- aucune donnée personnelle (nom, e-mail, téléphone des porteurs) n'est renvoyée.
"""
from __future__ import annotations

import unicodedata
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ACTIVE_STATUSES, PROJECT_STATUSES
from app.models import Cohort, Domain, Funding, Project
from app.services import kpi
from app.services.common import has_simulated_data

# ------------------------------------------------------------------ schéma commun des filtres
_NULLABLE_LIST = {"type": ["array", "null"], "items": {"type": "string"}}
FILTRES_SCHEMA = {
    "type": "object",
    "description": "Périmètre de l'analyse. Mettre null pour ne pas filtrer.",
    "properties": {
        "cohortes": {**_NULLABLE_LIST, "description": "Noms exacts des cohortes (voir le référentiel)."},
        "domaines": {**_NULLABLE_LIST, "description": "Noms exacts des domaines (voir le référentiel)."},
        "statuts": {**_NULLABLE_LIST, "description": "Statuts de projet (voir le référentiel)."},
        "date_debut": {"type": ["string", "null"], "description": "Début de période de dépôt, AAAA-MM-JJ."},
        "date_fin": {"type": ["string", "null"], "description": "Fin de période de dépôt, AAAA-MM-JJ."},
    },
    "required": ["cohortes", "domaines", "statuts", "date_debut", "date_fin"],
    "additionalProperties": False,
}


def _tool(name: str, description: str, properties: dict) -> dict:
    return {"name": name, "description": description, "strict": True,
            "input_schema": {"type": "object", "properties": properties, "required": list(properties),
                             "additionalProperties": False}}


TOOLS = [
    _tool("indicateurs_cles",
          "Calcule les indicateurs clés officiels (projets, candidatures, sélectionnés, incubation, prototypes, "
          "terminés, retards, financements, taux de sélection, d'achèvement et de retard, progression moyenne) "
          "sur un périmètre.", {"filtres": FILTRES_SCHEMA}),
    _tool("repartition_projets",
          "Répartit les projets selon une dimension : domaine, statut, cohorte ou mois de dépôt.",
          {"dimension": {"type": "string", "enum": ["domaine", "statut", "cohorte", "mois"]},
           "filtres": FILTRES_SCHEMA}),
    _tool("projets_en_retard",
          "Liste les projets actifs en retard (date limite dépassée ou jalon en retard) avec l'ampleur du retard.",
          {"filtres": FILTRES_SCHEMA, "limite": {"type": "integer", "description": "Nombre maximum (1 à 50)."}}),
    _tool("comparer_cohortes",
          "Compare les indicateurs des cohortes côte à côte (taux de réussite, retards, progression, financements).",
          {"cohortes": {**_NULLABLE_LIST, "description": "Cohortes à comparer ; null pour toutes."}}),
    _tool("synthese_financements",
          "Montants demandés, accordés et reçus regroupés par source, domaine, cohorte ou mois.",
          {"regroupement": {"type": "string", "enum": ["source", "domaine", "cohorte", "mois"]},
           "filtres": FILTRES_SCHEMA}),
    _tool("projets_a_surveiller",
          "Projets actifs qui cumulent des signaux d'alerte : retard, progression faible par rapport au temps "
          "écoulé, besoin de financement non couvert. Renvoie les motifs.",
          {"limite": {"type": "integer", "description": "Nombre maximum (1 à 30)."}}),
    _tool("evolution_candidatures",
          "Évolution mensuelle des candidatures reçues, acceptées et rejetées.", {"filtres": FILTRES_SCHEMA}),
]
TOOL_NAMES = {t["name"] for t in TOOLS}


class AnalysisError(ValueError):
    """Paramètre invalide : le message est renvoyé au modèle pour qu'il corrige son appel."""


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn").strip()


def _resolve(db: Session, model, names: list[str] | None, label: str) -> list[int]:
    if not names:
        return []
    rows = {_norm(n): i for i, n in db.execute(select(model.id, model.name)).all()}
    ids = []
    for n in names:
        if _norm(n) not in rows:
            raise AnalysisError(f"{label} inconnu(e) : « {n} ». Valeurs possibles : "
                                + ", ".join(db.scalars(select(model.name))))
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
    return kpi.Filters(start_date=d1, end_date=d2, cohort_ids=_resolve(db, Cohort, f.get("cohortes"), "Cohorte"),
                       domain_ids=_resolve(db, Domain, f.get("domaines"), "Domaine"), statuses=statuts)


def _limit(v: Any, maxi: int, defaut: int) -> int:
    try:
        return max(1, min(maxi, int(v)))
    except (TypeError, ValueError):
        return defaut


def _envelope(db: Session, f: kpi.Filters | None, donnees: Any, definitions: list[str] | None = None) -> dict:
    return {
        "perimetre": f.describe(db) if f else "Toutes les données",
        "donnees": donnees,
        "definitions": {k: kpi.KPI_DEFINITIONS[k][2] for k in (definitions or [])},
        "donnees_simulees": has_simulated_data(db),
        "date_du_calcul": date.today().isoformat(),
    }


# ------------------------------------------------------------------ les 7 fonctions
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
    else:
        raise AnalysisError("Dimension invalide : domaine, statut, cohorte ou mois.")
    return _envelope(db, f, d, ["total_projects"])


def projets_en_retard(db: Session, filtres: dict | None = None, limite: int | None = 10) -> dict:
    f = build_filters(db, filtres)
    tous = kpi.delayed_projects(db, f)  # sans le nom du porteur (données personnelles)
    return _envelope(db, f, {"nombre_total_en_retard": len(tous), "projets": tous[:_limit(limite, 50, 10)]},
                     ["delayed"])


def comparer_cohortes(db: Session, cohortes: list[str] | None = None) -> dict:
    f = kpi.Filters(cohort_ids=_resolve(db, Cohort, cohortes, "Cohorte"))
    champs = ["applications", "selected", "selection_rate", "total_projects", "completed", "completion_rate",
              "delayed", "delay_rate", "avg_progress", "funding_granted", "funding_received", "avg_funding"]
    d = [{"cohorte": c["cohort"], **{kpi.KPI_DEFINITIONS[k][0]: kpi.format_value(k, c[k]) for k in champs}}
         for c in kpi.cohorts_comparison(db, f)]
    return _envelope(db, f, d, champs)


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


def projets_a_surveiller(db: Session, limite: int | None = 10) -> dict:
    today = date.today()
    f = kpi.Filters()
    retards = {p["id"]: p for p in kpi.delayed_projects(db, f)}
    granted = dict(db.execute(select(Funding.project_id, func.sum(Funding.amount_granted))
                              .group_by(Funding.project_id)).all())
    resultats = []
    for p in db.scalars(select(Project).where(Project.is_archived.is_(False), Project.status.in_(ACTIVE_STATUSES))):
        motifs, score = [], 0.0
        if p.id in retards:
            j = retards[p.id]["days_late"]
            motifs.append(f"en retard de {j} jours")
            score += min(j, 180) / 30
        fin = p.deadline or p.cohort.end_date
        debut = p.cohort.start_date
        if fin > debut and today > debut:
            ecoule = min(1.0, (today - debut).days / (fin - debut).days)
            if ecoule - p.progress_pct / 100 >= 0.25:
                motifs.append(f"progression de {p.progress_pct} % alors que {ecoule:.0%} du délai est écoulé")
                score += (ecoule - p.progress_pct / 100) * 4
        accorde = int(granted.get(p.id) or 0)
        if p.planned_budget and accorde < 0.5 * p.planned_budget:
            manque = p.planned_budget - accorde
            motifs.append(f"besoin de financement non couvert de {manque:,} FCFA".replace(",", " "))
            score += 1
        if motifs:
            resultats.append({"projet": p.name, "id": p.id, "domaine": p.domain.name, "cohorte": p.cohort.name,
                              "statut": p.status, "progression_pct": p.progress_pct, "motifs": motifs,
                              "score_alerte": round(score, 2)})
    resultats.sort(key=lambda x: x["score_alerte"], reverse=True)
    return _envelope(db, f, {"nombre_total": len(resultats), "projets": resultats[:_limit(limite, 30, 10)]})


def evolution_candidatures(db: Session, filtres: dict | None = None) -> dict:
    f = build_filters(db, filtres)
    return _envelope(db, f, kpi.applications_monthly(db, f), ["applications", "selection_rate"])


FUNCTIONS = {
    "indicateurs_cles": lambda db, a: indicateurs_cles(db, a.get("filtres")),
    "repartition_projets": lambda db, a: repartition_projets(db, a.get("dimension", ""), a.get("filtres")),
    "projets_en_retard": lambda db, a: projets_en_retard(db, a.get("filtres"), a.get("limite")),
    "comparer_cohortes": lambda db, a: comparer_cohortes(db, a.get("cohortes")),
    "synthese_financements": lambda db, a: synthese_financements(db, a.get("regroupement", ""), a.get("filtres")),
    "projets_a_surveiller": lambda db, a: projets_a_surveiller(db, a.get("limite")),
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
            "statuts": PROJECT_STATUSES}
