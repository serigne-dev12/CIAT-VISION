"""Module 7 – CIAT AI Analyst."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import Role
from app.database import get_db
from app.deps import any_user
from app.models import AIConversation, User
from app.schemas import AskIn
from app.services import assistant as svc
from app.routers.pilotage import filtres_json
from app.services.analysis import TOOLS
from app.services.common import audit, get_int_setting

router = APIRouter(prefix="/assistant", tags=["Assistant IA"])


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(any_user)):
    return {"ai_available": svc.ai_available(db), "daily_limit": get_int_setting(db, "ai_daily_limit"),
            "used_today": svc.questions_today(db, user),
            "functions": [{"name": t["name"], "description": t["description"]} for t in TOOLS],
            "examples": ["Quels sont les projets les plus performants ?", "Quels projets sont en retard ?",
                         "Quel domaine présente les meilleurs résultats ?",
                         "Quel est le taux d'achèvement cette année ?", "Quels projets nécessitent une intervention ?",
                         "Comment évoluent les financements ?", "Quelles sont les principales difficultés ?",
                         "Quelles actions recommandes-tu ?"]}


@router.post("/ask")
def ask(data: AskIn, request: Request, db: Session = Depends(get_db), user: User = Depends(any_user)):
    actifs = filtres_json(data.filters) if data.filters else None
    res = svc.ask(db, user, data.question, actifs)
    audit(db, user, "QUESTION_IA", "assistant", None, data.question[:300], request)
    db.commit()
    return res


@router.get("/history")
def history(all_users: bool = False, limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db),
            user: User = Depends(any_user)):
    """Chacun voit son historique ; l'administrateur peut consulter celui de tous."""
    stmt = select(AIConversation).order_by(AIConversation.id.desc()).limit(limit)
    if not (all_users and user.role == Role.ADMIN):
        stmt = stmt.where(AIConversation.user_id == user.id)
    return [{"id": c.id, "user": c.user.username, "question": c.question, "answer": c.answer, "mode": c.mode,
             "tools_used": c.tools_used, "created_at": c.created_at} for c in db.scalars(stmt)]
