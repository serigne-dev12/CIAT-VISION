"""Dépendances partagées par les routes : filtres d'analyse et raccourcis de contrôle des rôles."""
from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Query

from app.constants import EDITORS, PROJECT_STATUSES, Role
from app.security import require_roles
from app.services.kpi import Filters

# Raccourcis : qui a le droit de faire quoi (matrice du cahier des charges § 4.2)
any_user = require_roles(Role.ADMIN, Role.COORDINATOR, Role.ANALYST)
editor = require_roles(*EDITORS)
admin_only = require_roles(Role.ADMIN)


def filters_dep(
    start_date: date | None = Query(None, description="Début de la période de dépôt"),
    end_date: date | None = Query(None, description="Fin de la période de dépôt"),
    cohort_ids: list[int] = Query([], alias="cohort_id"),
    domain_ids: list[int] = Query([], alias="domain_id"),
    statuses: list[str] = Query([], alias="status"),
) -> Filters:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "La fin de période doit être postérieure au début.")
    inconnus = [s for s in statuses if s not in PROJECT_STATUSES]
    if inconnus:
        raise HTTPException(422, f"Statut inconnu : {', '.join(inconnus)}")
    return Filters(start_date, end_date, cohort_ids, domain_ids, statuses)
