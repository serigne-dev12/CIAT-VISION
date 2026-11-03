"""Module 3 – Gestion des projets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants import TRANSITIONS, ProjectStatus, Role
from app.database import get_db
from app.deps import any_user, editor, filters_dep
from app.models import Application, Evaluation, Funding, Milestone, Project, ProjectLeader, User
from app.schemas import (EvaluationIn, EvaluationOut, MilestoneIn, MilestoneOut, ProgressUpdate, ProjectCreate,
                         ProjectUpdate, StatusChange)
from app.services import projects as svc
from app.services.common import audit
from app.services.kpi import Filters, delayed_condition

router = APIRouter(prefix="/projects", tags=["Projets"])

TRIS = {"name": Project.name, "updated_at": Project.updated_at, "created_at": Project.created_at,
        "progress": Project.progress_pct, "deadline": Project.deadline, "status": Project.status,
        "budget": Project.planned_budget}


def _granted_subquery():
    return (select(Funding.project_id, func.sum(Funding.amount_granted).label("granted"))
            .group_by(Funding.project_id).subquery())


@router.get("")
def list_projects(
    f: Filters = Depends(filters_dep),
    q: str = Query("", max_length=100, description="Recherche : nom, description ou porteur"),
    delayed_only: bool = False,
    progress_min: int | None = Query(None, ge=0, le=100),
    progress_max: int | None = Query(None, ge=0, le=100),
    sort: str = Query("updated_at", pattern="^(" + "|".join(TRIS) + ")$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(any_user),
):
    g = _granted_subquery()
    delayed = delayed_condition(db)
    conds = f.conditions()
    if q.strip():
        motif = f"%{q.strip()}%"
        conds.append(or_(Project.name.ilike(motif), Project.description.ilike(motif),
                         (ProjectLeader.first_name + " " + ProjectLeader.last_name).ilike(motif)))
    if progress_min is not None:
        conds.append(Project.progress_pct >= progress_min)
    if progress_max is not None:
        conds.append(Project.progress_pct <= progress_max)
    if delayed_only:
        conds.append(delayed)
    base = (select(Project.id).join(Application, Application.id == Project.application_id)
            .join(ProjectLeader, ProjectLeader.id == Project.leader_id).where(*conds))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    col = TRIS[sort]
    stmt = (select(Project, func.coalesce(g.c.granted, 0), delayed)
            .join(Application, Application.id == Project.application_id)
            .join(ProjectLeader, ProjectLeader.id == Project.leader_id)
            .outerjoin(g, g.c.project_id == Project.id).where(*conds)
            .order_by(col.desc().nulls_last() if order == "desc" else col.asc().nulls_last(), Project.id)
            .offset((page - 1) * page_size).limit(page_size))
    items = [{
        "id": p.id, "name": p.name, "leader": p.leader.full_name, "domain": p.domain.name, "domain_id": p.domain_id,
        "cohort": p.cohort.name, "cohort_id": p.cohort_id, "status": p.status, "progress_pct": p.progress_pct,
        "planned_budget": p.planned_budget, "funding_obtained": int(granted), "deadline": p.deadline,
        "is_delayed": bool(is_late), "created_at": p.created_at, "updated_at": p.updated_at,
        "is_simulated": p.is_simulated, "responsible": p.responsible.full_name if p.responsible else None,
        "responsible_id": p.responsible_id,
    } for p, granted, is_late in db.execute(stmt).all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _detail(db: Session, p: Project, user: User) -> dict:
    voir_contacts = user.role != Role.ANALYST
    delayed = bool(db.scalar(select(delayed_condition(db)).where(Project.id == p.id).select_from(Project)))
    granted = sum(x.amount_granted for x in p.fundings)
    received = sum(x.amount_received for x in p.fundings)
    app_ = p.application
    return {
        "id": p.id, "name": p.name, "description": p.description, "status": p.status,
        "progress_pct": p.progress_pct, "planned_budget": p.planned_budget, "deadline": p.deadline,
        "created_at": p.created_at, "updated_at": p.updated_at, "is_simulated": p.is_simulated,
        "is_archived": p.is_archived, "is_delayed": delayed,
        "domain": {"id": p.domain_id, "name": p.domain.name},
        "responsible": {"id": p.responsible_id, "name": p.responsible.full_name} if p.responsible else None,
        "cohort": {"id": p.cohort_id, "name": p.cohort.name, "start_date": p.cohort.start_date,
                   "end_date": p.cohort.end_date},
        "leader": {"id": p.leader_id, "first_name": p.leader.first_name, "last_name": p.leader.last_name,
                   "gender": p.leader.gender, "profile": p.leader.profile,
                   "email": p.leader.email if voir_contacts else None,
                   "phone": p.leader.phone if voir_contacts else None},
        "application": {"id": app_.id, "status": app_.status, "submitted_at": app_.submitted_at,
                        "decision_date": app_.decision_date,
                        "average_score": round(sum(float(e.score) for e in app_.evaluations) / len(app_.evaluations), 2)
                        if app_.evaluations else None},
        "evaluations": [EvaluationOut.model_validate(e) for e in app_.evaluations],
        "milestones": [MilestoneOut.model_validate(m) for m in p.milestones],
        "fundings": [{"id": x.id, "source_type": x.source_type, "partner": x.partner.name if x.partner else None,
                      "amount_requested": x.amount_requested, "amount_granted": x.amount_granted,
                      "amount_received": x.amount_received, "status": x.status, "request_date": x.request_date}
                     for x in p.fundings],
        "funding": {"planned_budget": p.planned_budget, "requested": sum(x.amount_requested for x in p.fundings),
                    "granted": granted, "received": received, "remaining_to_receive": granted - received,
                    "uncovered_need": max(0, p.planned_budget - granted)},
        "funding_obtained": granted,
        "history": [{"old_status": h.old_status, "new_status": h.new_status, "comment": h.comment,
                     "changed_at": h.changed_at, "changed_by": h.user.full_name if h.user else None}
                    for h in p.history],
        "allowed_transitions": [s.value for s in TRANSITIONS[ProjectStatus(p.status)]],
    }


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(any_user)):
    return _detail(db, svc.get_project(db, project_id, include_archived=user.role == Role.ADMIN), user)


@router.post("", status_code=201)
def create_project(data: ProjectCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    p = svc.create_project(db, data, user)
    audit(db, user, "CREATION_PROJET", "project", p.id, p.name, request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    champs = data.model_dump(exclude_unset=True)
    if "responsible_id" in champs:
        svc.check_responsible(db, champs["responsible_id"])
    if "domain_id" in champs or "cohort_id" in champs:
        svc.check_references(db, champs.get("domain_id", p.domain_id), champs.get("cohort_id", p.cohort_id))
    if "name" in champs or "cohort_id" in champs:
        svc.check_duplicate_name(db, champs.get("name", p.name), champs.get("cohort_id", p.cohort_id), exclude_id=p.id)
    deadline = champs.get("deadline", p.deadline)
    if deadline and deadline <= p.application.submitted_at:
        raise HTTPException(422, "La date limite doit être postérieure à la date de dépôt.")
    for k, v in champs.items():
        setattr(p, k, v)
    if "domain_id" in champs:
        p.application.domain_id = p.domain_id
    if "cohort_id" in champs:
        p.application.cohort_id = p.cohort_id
    if "name" in champs:
        p.application.project_title = p.name
    audit(db, user, "MAJ_PROJET", "project", p.id, ", ".join(champs), request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    """Suppression LOGIQUE : le projet est archivé (restaurable par l'administrateur)."""
    p = svc.get_project(db, project_id)
    svc.archive(p)
    audit(db, user, "SUPPRESSION_PROJET", "project", p.id, p.name, request)
    db.commit()


@router.post("/{project_id}/status")
def change_status(project_id: int, data: StatusChange, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    ancien = p.status
    svc.change_status(db, p, data.status, user, data.comment)
    audit(db, user, "CHANGEMENT_STATUT", "project", p.id, f"{ancien} → {p.status}", request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.post("/{project_id}/progress")
def update_progress(project_id: int, data: ProgressUpdate, request: Request, db: Session = Depends(get_db),
                    user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    ancien = p.progress_pct
    svc.update_progress(p, data.progress_pct, data.comment)
    audit(db, user, "MAJ_PROGRESSION", "project", p.id,
          f"{ancien} % → {p.progress_pct} %" + (f" – {data.comment}" if data.comment else ""), request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.post("/{project_id}/evaluations", status_code=201)
def add_evaluation(project_id: int, data: EvaluationIn, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    if p.status not in (ProjectStatus.PENDING, ProjectStatus.EVALUATION):
        raise HTTPException(422, "Les évaluations se saisissent avant la décision du comité.")
    if data.evaluated_at < p.application.submitted_at:
        raise HTTPException(422, "L'évaluation ne peut pas précéder le dépôt de la candidature.")
    db.add(Evaluation(application_id=p.application_id, **data.model_dump()))
    if p.status == ProjectStatus.PENDING:
        svc.change_status(db, p, ProjectStatus.EVALUATION.value, user, "Première évaluation saisie")
    audit(db, user, "AJOUT_EVALUATION", "project", p.id, f"note {data.score}/20", request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.post("/{project_id}/milestones", status_code=201)
def add_milestone(project_id: int, data: MilestoneIn, request: Request, db: Session = Depends(get_db),
                  user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    pos = (max((m.position for m in p.milestones), default=0)) + 1
    p.milestones.append(Milestone(title=data.title, due_date=data.due_date, completed_date=data.completed_date,
                                  position=pos))
    audit(db, user, "AJOUT_JALON", "project", p.id, data.title, request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.put("/{project_id}/milestones/{milestone_id}")
def update_milestone(project_id: int, milestone_id: int, data: MilestoneIn, request: Request,
                     db: Session = Depends(get_db), user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    m = db.get(Milestone, milestone_id)
    if m is None or m.project_id != p.id:
        raise HTTPException(404, "Jalon introuvable.")
    m.title, m.due_date, m.completed_date = data.title, data.due_date, data.completed_date
    audit(db, user, "MAJ_JALON", "project", p.id,
          f"{m.title} : {'atteint le ' + m.completed_date.isoformat() if m.completed_date else 'non atteint'}", request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)


@router.delete("/{project_id}/milestones/{milestone_id}")
def delete_milestone(project_id: int, milestone_id: int, request: Request, db: Session = Depends(get_db),
                     user: User = Depends(editor)):
    p = svc.get_project(db, project_id)
    m = db.get(Milestone, milestone_id)
    if m is None or m.project_id != p.id:
        raise HTTPException(404, "Jalon introuvable.")
    db.delete(m)
    audit(db, user, "SUPPRESSION_JALON", "project", p.id, m.title, request)
    db.commit()
    db.refresh(p)
    return _detail(db, p, user)

