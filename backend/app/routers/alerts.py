"""Module 4 (V2) – Centre d'alertes : consultation, marquage « lu », archivage et suppression selon les droits."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import admin_only, any_user, editor
from app.models import Alert, AlertRead, User
from app.services import alerts as svc
from app.services.common import audit, get_setting

router = APIRouter(prefix="/alerts", tags=["Alertes"])

ORDRE_NIVEAU = {n: i for i, n in enumerate(svc.NIVEAUX)}


def _etat(statut: str):
    if statut == "actives":
        return [Alert.resolved_at.is_(None), Alert.archived_at.is_(None)]
    if statut == "archivees":
        return [Alert.resolved_at.is_(None), Alert.archived_at.isnot(None)]
    return [Alert.resolved_at.isnot(None)]  # historique : alertes résolues


def _out(a: Alert, lus: set[int]) -> dict:
    return {"id": a.id, "type": a.type, "level": a.level, "title": a.title, "problem": a.problem,
            "explanation": a.explanation, "recommended_action": a.recommended_action,
            "project_id": a.project_id, "project": a.project.name if a.project else None,
            "objective_id": a.objective_id, "detected_at": a.detected_at, "last_seen_at": a.last_seen_at,
            "resolved_at": a.resolved_at, "archived_at": a.archived_at, "is_read": a.id in lus}


@router.get("")
def list_alerts(statut: Literal["actives", "archivees", "historique"] = "actives",
                level: list[str] = Query([]), type: list[str] = Query([]), unread_only: bool = False,
                project_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(any_user)):
    if svc.generer_si_necessaire(db):
        db.commit()
    conds = _etat(statut)
    if level:
        conds.append(Alert.level.in_(level))
    if type:
        conds.append(Alert.type.in_(type))
    if project_id:
        conds.append(Alert.project_id == project_id)
    lus = set(db.scalars(select(AlertRead.alert_id).where(AlertRead.user_id == user.id)))
    items = [_out(a, lus) for a in db.scalars(select(Alert).where(*conds))]
    if unread_only:
        items = [i for i in items if not i["is_read"]]
    items.sort(key=lambda i: (ORDRE_NIVEAU.get(i["level"], 9), i["is_read"], -i["detected_at"].timestamp()))
    return {"items": items, "total": len(items), "levels": svc.NIVEAUX, "types": list(svc.TYPES.values()),
            "generated_at": get_setting(db, "alerts_generated_at") or None}


@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(any_user)):
    """Compteurs pour la cloche de la barre supérieure et le tableau de bord."""
    if svc.generer_si_necessaire(db):
        db.commit()
    lus = select(AlertRead.alert_id).where(AlertRead.user_id == user.id)
    rows = db.execute(select(Alert.level, func.count(Alert.id), func.count(Alert.id).filter(Alert.id.not_in(lus)))
                      .where(*_etat("actives")).group_by(Alert.level)).all()
    par_niveau = {n: {"total": 0, "unread": 0} for n in svc.NIVEAUX}
    for niveau, total, non_lues in rows:
        par_niveau[niveau] = {"total": total, "unread": non_lues}
    return {"by_level": par_niveau, "total": sum(v["total"] for v in par_niveau.values()),
            "unread": sum(v["unread"] for v in par_niveau.values())}


@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    bilan = svc.generer(db)
    audit(db, user, "GENERATION_ALERTES", "alert", None, str(bilan), request)
    db.commit()
    return bilan


def _alerte(db: Session, alert_id: int) -> Alert:
    a = db.get(Alert, alert_id)
    if a is None:
        raise HTTPException(404, "Alerte introuvable.")
    return a


@router.post("/{alert_id}/read", status_code=204)
def mark_read(alert_id: int, db: Session = Depends(get_db), user: User = Depends(any_user)):
    _alerte(db, alert_id)
    if db.get(AlertRead, (alert_id, user.id)) is None:
        db.add(AlertRead(alert_id=alert_id, user_id=user.id))
        db.commit()


@router.post("/{alert_id}/unread", status_code=204)
def mark_unread(alert_id: int, db: Session = Depends(get_db), user: User = Depends(any_user)):
    lu = db.get(AlertRead, (alert_id, user.id))
    if lu:
        db.delete(lu)
        db.commit()


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(any_user)):
    deja = set(db.scalars(select(AlertRead.alert_id).where(AlertRead.user_id == user.id)))
    n = 0
    for aid in db.scalars(select(Alert.id).where(*_etat("actives"))):
        if aid not in deja:
            db.add(AlertRead(alert_id=aid, user_id=user.id))
            n += 1
    db.commit()
    return {"marquees": n}


@router.post("/{alert_id}/archive")
def archive(alert_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    a = _alerte(db, alert_id)
    a.archived_at, a.archived_by = datetime.now(UTC), user.id
    audit(db, user, "ARCHIVAGE_ALERTE", "alert", a.id, a.title, request)
    db.commit()
    return {"id": a.id}


@router.post("/{alert_id}/unarchive")
def unarchive(alert_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    a = _alerte(db, alert_id)
    a.archived_at = a.archived_by = None
    audit(db, user, "DESARCHIVAGE_ALERTE", "alert", a.id, a.title, request)
    db.commit()
    return {"id": a.id}


@router.delete("/{alert_id}", status_code=204)
def delete(alert_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    a = _alerte(db, alert_id)
    audit(db, user, "SUPPRESSION_ALERTE", "alert", a.id, a.title, request)
    db.delete(a)
    db.commit()
