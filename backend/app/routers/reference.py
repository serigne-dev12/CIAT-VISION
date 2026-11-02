"""Référentiels : domaines, cohortes (module 5), partenaires, porteurs, activités."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants import Role
from app.database import get_db
from app.deps import any_user, editor
from app.models import Activity, Cohort, Domain, Partner, Project, ProjectLeader, User
from app.schemas import ActivityIn, CohortIn, CohortOut, DomainOut, LeaderOut, PartnerIn, PartnerOut
from app.services import kpi
from app.services.common import audit

router = APIRouter(tags=["Référentiels et cohortes"])


@router.get("/domains", response_model=list[DomainOut])
def domains(db: Session = Depends(get_db), _: User = Depends(any_user)):
    return db.scalars(select(Domain).order_by(Domain.name)).all()


# ------------------------------------------------------------------ cohortes
@router.get("/cohorts", response_model=list[CohortOut])
def cohorts(db: Session = Depends(get_db), _: User = Depends(any_user)):
    return db.scalars(select(Cohort).order_by(Cohort.year.desc())).all()


@router.get("/cohorts/comparison")
def cohorts_comparison(cohort_ids: list[int] = Query([], alias="cohort_id"), db: Session = Depends(get_db),
                       _: User = Depends(any_user)):
    """Indicateurs côte à côte pour les cohortes choisies (toutes si aucune)."""
    return kpi.cohorts_comparison(db, kpi.Filters(cohort_ids=cohort_ids))


@router.get("/cohorts/{cohort_id}")
def cohort_detail(cohort_id: int, db: Session = Depends(get_db), _: User = Depends(any_user)):
    c = db.get(Cohort, cohort_id)
    if c is None:
        raise HTTPException(404, "Cohorte introuvable.")
    f = kpi.Filters(cohort_ids=[cohort_id])
    retards = {p["id"] for p in kpi.delayed_projects(db, f)}
    projets = db.scalars(select(Project).where(Project.cohort_id == cohort_id, Project.is_archived.is_(False))
                         .order_by(Project.name)).all()
    return {
        "cohort": CohortOut.model_validate(c),
        "kpis": kpi.kpi_payload(kpi.compute_kpis(db, f)),
        "projects": [{"id": p.id, "name": p.name, "leader": p.leader.full_name, "domain": p.domain.name,
                      "status": p.status, "progress_pct": p.progress_pct, "is_delayed": p.id in retards}
                     for p in projets],
        "by_status": kpi.projects_by_status(db, f),
        "activities": [{"id": a.id, "title": a.title, "type": a.type, "date": a.activity_date,
                        "participants": a.participants_count}
                       for a in db.scalars(select(Activity).where(Activity.cohort_id == cohort_id)
                                           .order_by(Activity.activity_date))],
    }


@router.post("/cohorts", response_model=CohortOut, status_code=201)
def create_cohort(data: CohortIn, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    if db.scalar(select(Cohort.id).where(func.lower(Cohort.name) == data.name.lower())):
        raise HTTPException(409, "Une cohorte porte déjà ce nom.")
    c = Cohort(**data.model_dump())
    db.add(c)
    db.flush()
    audit(db, user, "CREATION_COHORTE", "cohort", c.id, c.name, request)
    db.commit()
    return c


@router.put("/cohorts/{cohort_id}", response_model=CohortOut)
def update_cohort(cohort_id: int, data: CohortIn, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(editor)):
    c = db.get(Cohort, cohort_id)
    if c is None:
        raise HTTPException(404, "Cohorte introuvable.")
    if db.scalar(select(Cohort.id).where(func.lower(Cohort.name) == data.name.lower(), Cohort.id != cohort_id)):
        raise HTTPException(409, "Une cohorte porte déjà ce nom.")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    audit(db, user, "MAJ_COHORTE", "cohort", c.id, c.name, request)
    db.commit()
    return c


# ------------------------------------------------------------------ partenaires, porteurs, activités
@router.get("/partners", response_model=list[PartnerOut])
def partners(db: Session = Depends(get_db), _: User = Depends(any_user)):
    return db.scalars(select(Partner).order_by(Partner.name)).all()


@router.post("/partners", response_model=PartnerOut, status_code=201)
def create_partner(data: PartnerIn, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    if db.scalar(select(Partner.id).where(func.lower(Partner.name) == data.name.lower())):
        raise HTTPException(409, "Ce partenaire existe déjà.")
    p = Partner(**data.model_dump())
    db.add(p)
    db.flush()
    audit(db, user, "CREATION_PARTENAIRE", "partner", p.id, p.name, request)
    db.commit()
    return p


@router.get("/leaders", response_model=list[LeaderOut])
def leaders(q: str = Query("", max_length=60), db: Session = Depends(get_db), user: User = Depends(any_user)):
    """Recherche de porteurs. Les coordonnées sont masquées pour le rôle Analyste."""
    stmt = select(ProjectLeader).order_by(ProjectLeader.last_name, ProjectLeader.first_name).limit(30)
    if q.strip():
        motif = f"%{q.strip()}%"
        stmt = stmt.where(or_(ProjectLeader.first_name.ilike(motif), ProjectLeader.last_name.ilike(motif)))
    out = [LeaderOut.model_validate(x) for x in db.scalars(stmt)]
    if user.role == Role.ANALYST:
        for x in out:
            x.email = x.phone = None
    return out


@router.get("/activities")
def activities(db: Session = Depends(get_db), _: User = Depends(any_user)):
    return [{"id": a.id, "title": a.title, "type": a.type, "date": a.activity_date, "cohort_id": a.cohort_id,
             "participants": a.participants_count, "description": a.description}
            for a in db.scalars(select(Activity).order_by(Activity.activity_date.desc()))]


@router.post("/activities", status_code=201)
def create_activity(data: ActivityIn, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    if data.cohort_id is not None and db.get(Cohort, data.cohort_id) is None:
        raise HTTPException(422, "Cohorte inconnue.")
    a = Activity(**data.model_dump())
    db.add(a)
    db.flush()
    audit(db, user, "CREATION_ACTIVITE", "activity", a.id, a.title, request)
    db.commit()
    return {"id": a.id}
