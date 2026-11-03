"""Dépendances partagées par les routes : filtres d'analyse et raccourcis de contrôle des rôles."""
from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Query

from app.constants import EDITORS, PROJECT_STATUSES, Role
from app.security import require_roles
from app.services.kpi import FUNDING_LEVELS, PERFORMANCE_LEVELS, Filters

# Raccourcis : qui a le droit de faire quoi (matrice du cahier des charges § 4.2)
any_user = require_roles(Role.ADMIN, Role.COORDINATOR, Role.ANALYST)
editor = require_roles(*EDITORS)
admin_only = require_roles(Role.ADMIN)


def build_filters(start_date: date | None, end_date: date | None, cohort_ids: list[int], domain_ids: list[int],
                  statuses: list[str], responsible_ids: list[int] | None = None,
                  performance_levels: list[str] | None = None, funding_levels: list[str] | None = None) -> Filters:
    """Valide puis construit le périmètre d'analyse (utilisé par les routes GET et par les rapports)."""
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, "La fin de période doit être postérieure au début.")
    for valeurs, autorisees, nom in ((statuses, PROJECT_STATUSES, "Statut"),
                                     (performance_levels or [], PERFORMANCE_LEVELS, "Niveau de performance"),
                                     (funding_levels or [], FUNDING_LEVELS, "Niveau de financement")):
        inconnus = [v for v in valeurs if v not in autorisees]
        if inconnus:
            raise HTTPException(422, f"{nom} inconnu : {', '.join(inconnus)}")
    return Filters(start_date, end_date, list(cohort_ids), list(domain_ids), list(statuses),
                   list(responsible_ids or []), list(performance_levels or []), list(funding_levels or []))


def filters_dep(
    start_date: date | None = Query(None, description="Début de la période (date de dépôt de la candidature)"),
    end_date: date | None = Query(None, description="Fin de la période (date de dépôt de la candidature)"),
    cohort_ids: list[int] = Query([], alias="cohort_id"),
    domain_ids: list[int] = Query([], alias="domain_id"),
    statuses: list[str] = Query([], alias="status"),
    responsible_ids: list[int] = Query([], alias="responsible_id"),
    performance_levels: list[str] = Query([], alias="performance"),
    funding_levels: list[str] = Query([], alias="funding_level"),
) -> Filters:
    return build_filters(start_date, end_date, cohort_ids, domain_ids, statuses, responsible_ids,
                         performance_levels, funding_levels)
