"""Module 6 – Suivi des financements."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import any_user, editor, filters_dep
from app.models import Application, Funding, Partner, Project, User
from app.schemas import FundingIn
from app.services import kpi
from app.services import projects as svc
from app.services.common import audit

router = APIRouter(prefix="/fundings", tags=["Financements"])


def _out(x: Funding) -> dict:
    return {"id": x.id, "project_id": x.project_id, "project_name": x.project.name, "cohort": x.project.cohort.name,
            "domain": x.project.domain.name, "partner_id": x.partner_id, "partner": x.partner.name if x.partner else None,
            "source_type": x.source_type, "amount_requested": x.amount_requested, "amount_granted": x.amount_granted,
            "amount_received": x.amount_received, "remaining": x.amount_granted - x.amount_received,
            "request_date": x.request_date, "grant_date": x.grant_date, "status": x.status, "notes": x.notes,
            "is_simulated": x.is_simulated}


@router.get("")
def list_fundings(f: kpi.Filters = Depends(filters_dep), q: str = Query("", max_length=100),
                  source: str | None = None, funding_status: str | None = Query(None, alias="funding_status"),
                  partner_id: int | None = None,
                  request_start: date | None = Query(None, description="Demandes à partir de cette date"),
                  request_end: date | None = Query(None, description="Demandes jusqu'à cette date"),
                  amount_min: int | None = Query(None, ge=0, description="Montant demandé minimum (FCFA)"),
                  amount_max: int | None = Query(None, ge=0, description="Montant demandé maximum (FCFA)"),
                  page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
                  db: Session = Depends(get_db), _: User = Depends(any_user)):
    conds = f.conditions()
    if q.strip():
        conds.append(or_(Project.name.ilike(f"%{q.strip()}%"), Partner.name.ilike(f"%{q.strip()}%")))
    if source:
        conds.append(Funding.source_type == source)
    if funding_status:
        conds.append(Funding.status == funding_status)
    if partner_id:
        conds.append(Funding.partner_id == partner_id)
    if request_start and request_end and request_end < request_start:
        raise HTTPException(422, "La fin de période doit être postérieure au début.")
    if request_start:
        conds.append(Funding.request_date >= request_start)
    if request_end:
        conds.append(Funding.request_date <= request_end)
    if amount_min is not None and amount_max is not None and amount_max < amount_min:
        raise HTTPException(422, "Le montant maximum doit être supérieur au montant minimum.")
    if amount_min is not None:
        conds.append(Funding.amount_requested >= amount_min)
    if amount_max is not None:
        conds.append(Funding.amount_requested <= amount_max)
    base = (select(Funding).join(Project, Project.id == Funding.project_id)
            .join(Application, Application.id == Project.application_id)
            .outerjoin(Partner, Partner.id == Funding.partner_id).where(*conds))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.scalars(base.order_by(Funding.request_date.desc(), Funding.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    k = kpi.compute_kpis(db, f)
    summary = {key: k[key] for key in ("planned_budget", "funding_requested", "funding_granted", "funding_received",
                                       "remaining_to_receive", "uncovered_need", "avg_funding")}
    return {"items": [_out(x) for x in rows], "total": total, "page": page, "page_size": page_size,
            "summary": kpi.kpi_payload(summary), "by_source": kpi.fundings_by(db, f, "source"),
            "by_domain": kpi.fundings_by(db, f, "domain"), "monthly": kpi.fundings_monthly(db, f)}


@router.post("", status_code=201)
def create_funding(data: FundingIn, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    p = svc.get_project(db, data.project_id)
    svc.validate_funding(db, data)
    x = Funding(**data.model_dump(mode="python"))
    x.status = data.status.value
    db.add(x)
    db.flush()
    audit(db, user, "AJOUT_FINANCEMENT", "funding", x.id,
          f"{p.name} – {x.source_type} – demandé {x.amount_requested} FCFA ({x.status})", request)
    db.commit()
    db.refresh(x)
    return _out(x)


@router.put("/{funding_id}")
def update_funding(funding_id: int, data: FundingIn, request: Request, db: Session = Depends(get_db),
                   user: User = Depends(editor)):
    x = db.get(Funding, funding_id)
    if x is None:
        raise HTTPException(404, "Financement introuvable.")
    svc.get_project(db, data.project_id)
    svc.validate_funding(db, data)
    for k, v in data.model_dump(mode="python").items():
        setattr(x, k, v)
    x.status = data.status.value
    audit(db, user, "MAJ_FINANCEMENT", "funding", x.id, f"{x.status} – reçu {x.amount_received} FCFA", request)
    db.commit()
    db.refresh(x)
    return _out(x)


@router.delete("/{funding_id}", status_code=204)
def delete_funding(funding_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(editor)):
    x = db.get(Funding, funding_id)
    if x is None:
        raise HTTPException(404, "Financement introuvable.")
    audit(db, user, "SUPPRESSION_FINANCEMENT", "funding", x.id, f"{x.project.name} – {x.amount_requested} FCFA",
          request)
    db.delete(x)
    db.commit()
