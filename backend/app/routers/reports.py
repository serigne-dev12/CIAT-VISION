"""Module 8 – Rapports et exportations."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import any_user
from app.models import User
from app.schemas import CommentaryRequest, FiltersIn, ReportRequest
from app.services import kpi, reports
from app.services.assistant import ai_commentary
from app.services.common import audit

router = APIRouter(prefix="/reports", tags=["Rapports"])


def _filters(f: FiltersIn) -> kpi.Filters:
    return kpi.Filters(f.start_date, f.end_date, f.cohort_ids, f.domain_ids, list(f.statuses))


@router.get("/types")
def types(_: User = Depends(any_user)):
    return [{"key": k, "title": v} for k, v in reports.TITRES.items()]


@router.post("/commentary")
def commentary(data: CommentaryRequest, db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Propose un commentaire analytique (IA si disponible, sinon règles automatiques) que l'utilisateur relit."""
    f = _filters(data.filters)
    k = kpi.compute_kpis(db, f)
    texte, mode = ai_commentary(db, {key: k[key] for key in k}, f.describe(db), reports.TITRES[data.report_type])
    return {"commentary": texte, "mode": mode}


@router.post("/generate")
def generate(data: ReportRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(any_user)):
    f = _filters(data.filters)
    r = reports.build_report(db, data.report_type, f, data.commentary)
    contenu, mime, nom = reports.render(r, data.format)
    audit(db, user, "EXPORT_RAPPORT", "report", None, f"{r.title} ({data.format.upper()}) – {r.perimetre}", request)
    db.commit()
    return Response(contenu, media_type=mime,
                    headers={"Content-Disposition": f"attachment; filename=\"{nom}\"; filename*=UTF-8''{quote(nom)}"})
