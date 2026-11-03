"""Modules 2 et 4 – Tableau de bord et analyse des performances (toutes les statistiques viennent d'ici)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.constants import PROJECT_STATUSES
from app.database import get_db
from app.deps import any_user, filters_dep
from app.models import User
from app.services import kpi
from app.services.common import get_setting, has_simulated_data

router = APIRouter(prefix="/analytics", tags=["Indicateurs et analyses"])


@router.get("/meta")
def meta(db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Informations générales : mention « données simulées », institution, statuts."""
    return {"simulated": has_simulated_data(db), "institution": get_setting(db, "institution_name"),
            "statuses": PROJECT_STATUSES,
            "performance_levels": kpi.PERFORMANCE_LEVELS, "funding_levels": kpi.FUNDING_LEVELS,
            "performance_definition": kpi.DEFINITION_PERFORMANCE, "funding_definition": kpi.DEFINITION_FINANCEMENT,
            "delay_tolerance_days": int(get_setting(db, "delay_tolerance_days")),
            "definitions": {k: {"label": v[0], "unit": v[1], "definition": v[2]} for k, v in kpi.KPI_DEFINITIONS.items()}}


@router.get("/kpis")
def kpis(f: kpi.Filters = Depends(filters_dep), db: Session = Depends(get_db), _: User = Depends(any_user)):
    values = kpi.compute_kpis(db, f)
    return {"perimetre": f.describe(db), "dashboard": kpi.kpi_payload({k: values[k] for k in kpi.DASHBOARD_KPIS}),
            "all": kpi.kpi_payload(values)}


@router.get("/charts")
def charts(f: kpi.Filters = Depends(filters_dep), db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Séries de tous les graphiques d'analyse, calculées sur le même périmètre."""
    return {
        "perimetre": f.describe(db),
        "applications_monthly": kpi.applications_monthly(db, f),
        "by_domain": kpi.projects_by_domain(db, f),
        "by_status": kpi.projects_by_status(db, f),
        "cohorts": kpi.cohorts_comparison(db, f),
        "fundings_monthly": kpi.fundings_monthly(db, f),
        "fundings_by_domain": kpi.fundings_by(db, f, "domain"),
        "fundings_by_source": kpi.fundings_by(db, f, "source"),
        "progress_distribution": kpi.progress_distribution(db, f),
        "projects_monthly": kpi.projects_monthly(db, f),
        "domain_performance": [{"domain": g["label"], "completion_rate": g["completion_rate"],
                                "delay_rate": g["delay_rate"], "avg_progress": g["avg_progress"],
                                "projects": g["total_projects"], "funding_granted": g["funding_granted"]}
                               for g in kpi.group_kpis(db, f, "domain")],
        "levels": kpi.level_distribution(db, f),
    }


@router.get("/indicator")
def indicator(key: str = Query(..., description="Clé d'un indicateur de KPI_DEFINITIONS"),
              by: str = Query("domain", pattern="^(domain|cohort|responsible)$"),
              f: kpi.Filters = Depends(filters_dep), db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Valeur d'un indicateur choisi, ventilée par domaine, cohorte ou responsable (sélecteur « Indicateur »)."""
    if key not in kpi.KPI_DEFINITIONS:
        raise HTTPException(422, "Indicateur inconnu.")
    lab, unit, definition = kpi.KPI_DEFINITIONS[key]
    return {"key": key, "label": lab, "unit": unit, "definition": definition, "by": by, "perimetre": f.describe(db),
            "items": [{"label": g["label"], "value": g[key]} for g in kpi.group_kpis(db, f, by)]}


@router.get("/delayed")
def delayed(f: kpi.Filters = Depends(filters_dep), limit: int = Query(50, ge=1, le=500),
            db: Session = Depends(get_db), _: User = Depends(any_user)):
    items = kpi.delayed_projects(db, f, include_leader=True)
    return {"total": len(items), "items": items[:limit]}
