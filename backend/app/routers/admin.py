"""Module 9 – Administration : utilisateurs, paramètres, journal d'audit, données simulées, projets archivés."""
from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ROLE_LABELS, Role
from app.database import get_db
from app.deps import admin_only
from app.models import AppSetting, AuditLog, Project, User
from app.schemas import SettingsUpdate, UserCreate, UserOut, UserUpdate
from app.security import hash_password, password_policy_error
from app.seed import purge_simulated
from app.services import projects as svc
from app.services.common import all_settings, audit

router = APIRouter(prefix="/admin", tags=["Administration"])


# ------------------------------------------------------------------ utilisateurs
@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(User).order_by(User.username)).all()


@router.get("/roles")
def roles(_: User = Depends(admin_only)):
    return [{"key": r.value, "label": ROLE_LABELS[r]} for r in Role]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if err := password_policy_error(data.password):
        raise HTTPException(422, err)
    if db.scalar(select(User.id).where(func.lower(User.username) == data.username.lower())):
        raise HTTPException(409, "Cet identifiant est déjà utilisé.")
    u = User(username=data.username, full_name=data.full_name, email=data.email, role=data.role.value,
             password_hash=hash_password(data.password))
    db.add(u)
    db.flush()
    audit(db, admin, "CREATION_COMPTE", "user", u.id, f"{u.username} ({u.role})", request)
    db.commit()
    return u


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(admin_only)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "Utilisateur introuvable.")
    champs = data.model_dump(exclude_unset=True)
    if u.id == admin.id and (champs.get("is_active") is False or champs.get("role", Role.ADMIN) != Role.ADMIN):
        raise HTTPException(422, "Vous ne pouvez ni désactiver votre propre compte ni retirer votre rôle "
                                 "d'administrateur.")
    if "new_password" in champs and champs["new_password"]:
        if err := password_policy_error(champs["new_password"]):
            raise HTTPException(422, err)
        u.password_hash = hash_password(champs["new_password"])
        u.failed_attempts, u.locked_until = 0, None
    for k in ("full_name", "email", "is_active"):
        if k in champs:
            setattr(u, k, champs[k])
    if "role" in champs and champs["role"]:
        u.role = Role(champs["role"]).value
    details = ", ".join(k for k in champs if k != "new_password") + (" + mot de passe réinitialisé"
                                                                      if champs.get("new_password") else "")
    audit(db, admin, "MAJ_COMPTE", "user", u.id, f"{u.username} : {details}", request)
    db.commit()
    return u


# ------------------------------------------------------------------ paramètres
@router.get("/settings")
def get_settings_(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return all_settings(db)


@router.put("/settings")
def update_settings(data: SettingsUpdate, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    for k, v in data.model_dump(exclude_none=True).items():
        valeur = ("true" if v else "false") if isinstance(v, bool) else str(v)
        row = db.get(AppSetting, k)
        if row:
            row.value = valeur
        else:
            db.add(AppSetting(key=k, value=valeur))
    audit(db, admin, "MAJ_PARAMETRES", "settings", None, str(data.model_dump(exclude_none=True)), request)
    db.commit()
    return all_settings(db)


# ------------------------------------------------------------------ journal d'audit
@router.get("/audit-logs")
def audit_logs(action: str | None = None, username: str | None = None, start_date: date | None = None,
               end_date: date | None = None, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500),
               db: Session = Depends(get_db), _: User = Depends(admin_only)):
    conds = []
    if action:
        conds.append(AuditLog.action == action)
    if username:
        conds.append(AuditLog.username.ilike(f"%{username}%"))
    if start_date:
        conds.append(AuditLog.created_at >= datetime.combine(start_date, time.min))
    if end_date:
        conds.append(AuditLog.created_at <= datetime.combine(end_date, time.max))
    total = db.scalar(select(func.count(AuditLog.id)).where(*conds))
    rows = db.scalars(select(AuditLog).where(*conds).order_by(AuditLog.id.desc())
                      .offset((page - 1) * page_size).limit(page_size))
    return {"total": total, "actions": list(db.scalars(select(AuditLog.action).distinct().order_by(AuditLog.action))),
            "items": [{"id": a.id, "created_at": a.created_at, "username": a.username, "action": a.action,
                       "entity": a.entity, "entity_id": a.entity_id, "details": a.details, "ip_address": a.ip_address}
                      for a in rows]}


# ------------------------------------------------------------------ données
@router.get("/data-status")
def data_status(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return {"simulated_projects": db.scalar(select(func.count(Project.id)).where(Project.is_simulated.is_(True))),
            "real_projects": db.scalar(select(func.count(Project.id)).where(Project.is_simulated.is_(False))),
            "archived": [{"id": p.id, "name": p.name, "cohort": p.cohort.name, "archived_at": p.archived_at}
                         for p in db.scalars(select(Project).where(Project.is_archived.is_(True))
                                             .order_by(Project.archived_at.desc()))]}


@router.post("/purge-simulated")
def purge(request: Request, confirmation: str = Query(...), db: Session = Depends(get_db),
          admin: User = Depends(admin_only)):
    """Supprime TOUTES les données simulées. Exige la saisie du mot « PURGER »."""
    if confirmation != "PURGER":
        raise HTTPException(422, "Saisissez « PURGER » pour confirmer la suppression des données simulées.")
    bilan = purge_simulated(db)
    audit(db, admin, "PURGE_DONNEES_SIMULEES", "data", None, str(bilan), request)
    db.commit()
    return bilan


@router.post("/projects/{project_id}/restore")
def restore_project(project_id: int, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    p = db.get(Project, project_id)
    if p is None or not p.is_archived:
        raise HTTPException(404, "Projet archivé introuvable.")
    svc.restore(db, p)
    audit(db, admin, "RESTAURATION_PROJET", "project", p.id, p.name, request)
    db.commit()
    return {"id": p.id, "name": p.name}
