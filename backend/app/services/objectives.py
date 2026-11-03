"""Module 7 (V2) – Suivi des objectifs.

Chaque objectif porte sur une période et, facultativement, une cohorte ou un domaine. Les valeurs « réalisées » sont
mesurées par des ÉVÉNEMENTS DATÉS dans la période, pour que l'objectif et sa mesure portent sur la même période :

| Indicateur              | Valeur réalisée                                                                       |
|-------------------------|---------------------------------------------------------------------------------------|
| projets_accompagnes     | candidatures acceptées dont la décision du comité tombe dans la période               |
| projets_termines        | projets passés au statut « Terminé » dans la période (historique des statuts)         |
| prototypes              | projets passés au statut « Prototype réalisé » dans la période                         |
| financements_mobilises  | somme des montants accordés dont la date d'accord tombe dans la période (FCFA)        |
| taux_achevement         | taux d'achèvement (%) du périmètre à la date du jour (indicateur de stock, pas de flux)|
"""
from __future__ import annotations

from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ApplicationStatus, ProjectStatus
from app.models import Application, Funding, Objective, Project, ProjectStatusHistory
from app.services import kpi

INDICATEURS = {
    "projets_accompagnes": ("Projets accompagnés", "count",
                            "Candidatures acceptées dont la décision du comité tombe dans la période."),
    "projets_termines": ("Projets terminés", "count", "Projets passés au statut « Terminé » dans la période."),
    "prototypes": ("Prototypes réalisés", "count", "Projets passés au statut « Prototype réalisé » dans la période."),
    "financements_mobilises": ("Financements mobilisés", "amount",
                               "Montants accordés (FCFA) dont la date d'accord tombe dans la période."),
    "taux_achevement": ("Taux d'achèvement", "percent",
                        "Projets terminés ÷ projets incubés (%), sur le périmètre, à la date du jour."),
}
STATUTS = ["Atteint", "En bonne voie", "En retard", "Non atteint", "En dessous de la cible"]


def _perimetre(o: Objective) -> list:
    c = [Project.is_archived.is_(False)]
    if o.cohort_id:
        c.append(Project.cohort_id == o.cohort_id)
    if o.domain_id:
        c.append(Project.domain_id == o.domain_id)
    return c


def _bornes(o: Objective, today: date) -> tuple[datetime, datetime, date]:
    fin = min(o.end_date, today)
    return (datetime.combine(o.start_date, time.min, tzinfo=UTC), datetime.combine(fin, time.max, tzinfo=UTC), fin)


def _passages(db: Session, o: Objective, statut: str, today: date) -> int:
    d1, d2, _ = _bornes(o, today)
    return db.scalar(select(func.count(func.distinct(ProjectStatusHistory.project_id)))
                     .join(Project, Project.id == ProjectStatusHistory.project_id)
                     .where(*_perimetre(o), ProjectStatusHistory.new_status == statut,
                            ProjectStatusHistory.changed_at >= d1, ProjectStatusHistory.changed_at <= d2)) or 0


def valeur_realisee(db: Session, o: Objective, today: date | None = None) -> float | None:
    today = today or date.today()
    if today < o.start_date:
        return 0.0
    _, _, fin = _bornes(o, today)
    if o.indicator == "projets_accompagnes":
        return float(db.scalar(select(func.count(Project.id)).join(Application, Application.id == Project.application_id)
                               .where(*_perimetre(o), Application.status == ApplicationStatus.ACCEPTED,
                                      Application.decision_date >= o.start_date, Application.decision_date <= fin)) or 0)
    if o.indicator == "projets_termines":
        return float(_passages(db, o, ProjectStatus.COMPLETED.value, today))
    if o.indicator == "prototypes":
        return float(_passages(db, o, ProjectStatus.PROTOTYPE.value, today))
    if o.indicator == "financements_mobilises":
        return float(db.scalar(select(func.coalesce(func.sum(Funding.amount_granted), 0))
                               .join(Project, Project.id == Funding.project_id)
                               .where(*_perimetre(o), Funding.grant_date >= o.start_date, Funding.grant_date <= fin)) or 0)
    if o.indicator == "taux_achevement":
        f = kpi.Filters(cohort_ids=[o.cohort_id] if o.cohort_id else [],
                        domain_ids=[o.domain_id] if o.domain_id else [])
        taux = kpi.compute_kpis(db, f)["completion_rate"]
        return round(taux * 100, 1) if taux is not None else None
    raise ValueError("Indicateur inconnu.")


def evaluer(db: Session, o: Objective, today: date | None = None) -> dict:
    today = today or date.today()
    cible = float(o.target_value)
    realise = valeur_realisee(db, o, today)
    duree = max(1, (o.end_date - o.start_date).days)
    ecoule = max(0.0, min(1.0, (today - o.start_date).days / duree))
    termine = today > o.end_date
    if realise is None:
        statut, taux = "Non calculable", None
    else:
        taux = realise / cible
        if realise >= cible:
            statut = "Atteint"
        elif o.indicator == "taux_achevement":
            statut = "En dessous de la cible"
        elif termine:
            statut = "Non atteint"
        else:  # rythme attendu : la réalisation doit suivre la part de la période écoulée (marge de 10 %)
            statut = "En bonne voie" if taux >= ecoule * 0.9 else "En retard"
    lib, unite, definition = INDICATEURS[o.indicator]
    return {
        "id": o.id, "label": o.label, "indicator": o.indicator, "indicator_label": lib, "unit": unite,
        "definition": definition, "target": cible, "current": realise,
        "realization_rate": round(taux, 4) if taux is not None else None,
        "gap": round(realise - cible, 2) if realise is not None else None,
        "status": statut, "start_date": o.start_date, "end_date": o.end_date,
        "elapsed_rate": round(ecoule, 4), "cohort_id": o.cohort_id, "cohort": o.cohort.name if o.cohort else None,
        "domain_id": o.domain_id, "domain": o.domain.name if o.domain else None, "is_simulated": o.is_simulated,
    }


def lister(db: Session, today: date | None = None) -> list[dict]:
    return [evaluer(db, o, today) for o in db.scalars(select(Objective).order_by(Objective.end_date, Objective.id))]
