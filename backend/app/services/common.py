"""Services transverses : journal d'audit et paramètres de l'application."""
from __future__ import annotations

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_SETTINGS
from app.models import AppSetting, AuditLog, Project, User


def audit(db: Session, user: User | None, action: str, entity: str | None = None, entity_id: int | None = None,
          details: str | None = None, request: Request | None = None, username: str | None = None) -> None:
    """Ajoute une ligne au journal d'audit. La validation (commit) est faite par l'appelant."""
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=(user.username if user else username),
        action=action, entity=entity, entity_id=entity_id,
        details=(details or "")[:2000] or None,
        ip_address=(request.client.host if request and request.client else None),
    ))


def get_setting(db: Session, key: str) -> str:
    row = db.get(AppSetting, key)
    return row.value if row else DEFAULT_SETTINGS[key]


def get_int_setting(db: Session, key: str) -> int:
    try:
        return int(get_setting(db, key))
    except ValueError:
        return int(DEFAULT_SETTINGS[key])


def all_settings(db: Session) -> dict[str, str]:
    values = dict(DEFAULT_SETTINGS)
    for row in db.scalars(select(AppSetting)):
        values[row.key] = row.value
    return values


def has_simulated_data(db: Session) -> bool:
    """Vrai tant qu'il reste au moins un projet simulé (le bandeau « données simulées » s'affiche)."""
    return db.scalar(select(Project.id).where(Project.is_simulated.is_(True)).limit(1)) is not None
