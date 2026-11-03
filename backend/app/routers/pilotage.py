"""Modules V2 de pilotage : objectifs, comparaisons, analyse des risques, responsables de suivi."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ProjectStatus
from app.database import get_db
from app.deps import any_user, build_filters, editor, filters_dep
from app.models import Cohort, Domain, Funding, Objective, Project, Responsable, User
from app.schemas import CompareIn, FiltersIn, ObjectiveIn, ResponsableIn
from app.services import kpi, objectives, risks
from app.services.common import audit

router = APIRouter(tags=["Pilotage (V2)"])


def filtres_json(f: FiltersIn) -> kpi.Filters:
    return build_filters(f.start_date, f.end_date, f.cohort_ids, f.domain_ids, list(f.statuses), f.responsible_ids,
                         f.performance_levels, f.funding_levels)


# ------------------------------------------------------------------ objectifs
@router.get("/objectives")
def list_objectives(db: Session = Depends(get_db), _: User = Depends(any_user)):
    return {"items": objectives.lister(db), "indicators": [
        {"key": k, "label": v[0], "unit": v[1], "definition": v[2]} for k, v in objectives.INDICATEURS.items()]}


def _verifier_objectif(db: Session, data: ObjectiveIn) -> None:
    if data.cohort_id is not None and db.get(Cohort, data.cohort_id) is None:
        raise HTTPException(422, "Cohorte inconnue.")
    if data.domain_id is not None and db.get(Domain, data.domain_id) is None:
        raise HTTPException(422, "Domaine inconnu.")


@router.post("/objectives", status_code=201)
def create_objective(data: ObjectiveIn, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    _verifier_objectif(db, data)
    o = Objective(**data.model_dump(), created_by=user.id)
    db.add(o)
    db.flush()
    audit(db, user, "CREATION_OBJECTIF", "objective", o.id, f"{o.label} : cible {data.target_value}", request)
    db.commit()
    db.refresh(o)
    return objectives.evaluer(db, o)


@router.put("/objectives/{objective_id}")
def update_objective(objective_id: int, data: ObjectiveIn, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(editor)):
    o = db.get(Objective, objective_id)
    if o is None:
        raise HTTPException(404, "Objectif introuvable.")
    _verifier_objectif(db, data)
    for k, v in data.model_dump().items():
        setattr(o, k, v)
    audit(db, user, "MAJ_OBJECTIF", "objective", o.id, o.label, request)
    db.commit()
    db.refresh(o)
    return objectives.evaluer(db, o)


@router.delete("/objectives/{objective_id}", status_code=204)
def delete_objective(objective_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    o = db.get(Objective, objective_id)
    if o is None:
        raise HTTPException(404, "Objectif introuvable.")
    audit(db, user, "SUPPRESSION_OBJECTIF", "objective", o.id, o.label, request)
    db.delete(o)
    db.commit()


# ------------------------------------------------------------------ risques
@router.get("/risks")
def risk_analysis(f: kpi.Filters = Depends(filters_dep), db: Session = Depends(get_db), _: User = Depends(any_user)):
    return {"perimetre": f.describe(db), **risks.analyser(db, f)}


# ------------------------------------------------------------------ comparaisons
METRIQUES = {k: {"label": kpi.KPI_DEFINITIONS[k][0], "unit": kpi.KPI_DEFINITIONS[k][1],
                 "definition": kpi.KPI_DEFINITIONS[k][2]} for k in kpi.COMPARISON_KPIS}
METRIQUES["funding_granted"]["label"] = "Financement obtenu"


def _metriques(k: dict) -> dict:
    return {m: k[m] for m in kpi.COMPARISON_KPIS}


@router.post("/compare")
def compare(data: CompareIn, db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Compare des domaines, cohortes, responsables, projets ou périodes avec les MÊMES définitions et le même
    périmètre (filtres communs), seule la dimension comparée change."""
    f = filtres_json(data.filters)
    avertissements: list[str] = []
    if data.dimension in ("domain", "cohort", "responsible"):
        if len(data.ids) < 2:
            raise HTTPException(422, "Choisissez au moins deux éléments à comparer.")
        champ = {"domain": "domain_ids", "cohort": "cohort_ids", "responsible": "responsible_ids"}[data.dimension]
        groupes = kpi.group_kpis(db, replace(f, **{champ: list(data.ids)}), data.dimension)
        items = [{"id": g["id"], "label": g["label"], **_metriques(g), "applications": g["applications"],
                  "active": g["active"], "incubated": g["incubated"]} for g in groupes]
        absents = len(data.ids) - len(items)
        if absents:
            avertissements.append(f"{absents} élément(s) sans aucune donnée sur ce périmètre n'apparaissent pas.")
    elif data.dimension == "period":
        if len(data.periods) < 2:
            raise HTTPException(422, "Choisissez au moins deux périodes à comparer.")
        items = []
        for i, per in enumerate(data.periods, start=1):
            k = kpi.compute_kpis(db, replace(f, start_date=per.start_date, end_date=per.end_date))
            items.append({"id": i, "label": per.label or f"{per.start_date:%d/%m/%Y} – {per.end_date:%d/%m/%Y}",
                          "start_date": per.start_date, "end_date": per.end_date, **_metriques(k),
                          "applications": k["applications"], "active": k["active"], "incubated": k["incubated"]})
        durees = [(p.end_date - p.start_date).days + 1 for p in data.periods]
        if max(durees) > min(durees) * 1.1:
            avertissements.append("Les périodes n'ont pas la même durée : comparez plutôt les taux que les volumes "
                                  "(nombre de projets, montants).")
        avertissements.append("La période porte sur la date de dépôt des candidatures.")
    else:  # projets
        if len(data.ids) < 2:
            raise HTTPException(422, "Choisissez au moins deux projets à comparer.")
        retards = {r["id"]: r["days_late"] for r in kpi.delayed_projects(db, kpi.Filters())}
        accorde = dict(db.execute(select(Funding.project_id, func.sum(Funding.amount_granted))
                                  .where(Funding.project_id.in_(data.ids)).group_by(Funding.project_id)).all())
        evaluations = {e["project_id"]: e for e in risks.analyser(db, kpi.Filters())["projets"]}
        items = []
        for p in db.scalars(select(Project).where(Project.id.in_(data.ids), Project.is_archived.is_(False))):
            attendu = risks.progression_attendue(p, date.today())
            a = int(accorde.get(p.id) or 0)
            items.append({
                "id": p.id, "label": p.name, "domain": p.domain.name, "cohort": p.cohort.name, "status": p.status,
                "progress_pct": p.progress_pct,
                "expected_pct": round(attendu * 100, 1) if attendu is not None and p.status != ProjectStatus.COMPLETED
                else None,
                "days_late": retards.get(p.id, 0), "funding_granted": a, "planned_budget": p.planned_budget,
                "coverage_rate": round(a / p.planned_budget, 4) if p.planned_budget else None,
                "prototype": p.status in (ProjectStatus.PROTOTYPE, ProjectStatus.COMPLETED),
                "completed": p.status == ProjectStatus.COMPLETED,
                "risk_score": evaluations.get(p.id, {}).get("score"), "risk_level": evaluations.get(p.id, {}).get("level"),
            })
        return {"dimension": "project", "items": items, "perimetre": "Projets sélectionnés",
                "warnings": ["Pour des projets individuels, les taux (achèvement, retard) sont remplacés par la "
                             "situation de chaque projet."]}
    return {"dimension": data.dimension, "metrics": METRIQUES, "items": items, "perimetre": f.describe(db),
            "warnings": avertissements}


# ------------------------------------------------------------------ responsables de suivi
@router.get("/responsables")
def list_responsables(db: Session = Depends(get_db), _: User = Depends(any_user)):
    nb = dict(db.execute(select(Project.responsible_id, func.count(Project.id))
                         .where(Project.is_archived.is_(False)).group_by(Project.responsible_id)).all())
    return [{"id": r.id, "full_name": r.full_name, "function": r.function, "is_active": r.is_active,
             "projects": nb.get(r.id, 0), "is_simulated": r.is_simulated}
            for r in db.scalars(select(Responsable).order_by(Responsable.full_name))]


@router.post("/responsables", status_code=201)
def create_responsable(data: ResponsableIn, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(editor)):
    if db.scalar(select(Responsable.id).where(func.lower(Responsable.full_name) == func.lower(data.full_name))):
        raise HTTPException(409, "Ce responsable existe déjà.")
    r = Responsable(**data.model_dump())
    db.add(r)
    db.flush()
    audit(db, user, "CREATION_RESPONSABLE", "responsable", r.id, r.full_name, request)
    db.commit()
    return {"id": r.id, "full_name": r.full_name}
