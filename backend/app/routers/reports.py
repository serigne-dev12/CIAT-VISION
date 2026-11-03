"""Module 8 – Rapports et exportations (les rapports respectent les filtres appliqués)."""
from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import any_user
from app.models import Project, User
from app.routers.pilotage import filtres_json
from app.schemas import CommentaryRequest, ReportRequest
from app.services import kpi, reports, risks
from app.services.assistant import ai_commentary

router = APIRouter(prefix="/reports", tags=["Rapports"])


@router.get("/types")
def types(_: User = Depends(any_user)):
    return [{"key": k, "title": v} for k, v in reports.TITRES.items()]


def _commentaire_projet(db: Session, project_id: int | None) -> str:
    """Observations factuelles sur un projet, à partir de sa situation et de ses facteurs de risque."""
    p = db.get(Project, project_id) if project_id else None
    if p is None:
        raise HTTPException(422, "Choisissez un projet.")
    evaluation = next((e for e in risks.analyser(db, kpi.Filters())["projets"] if e["project_id"] == p.id), None)
    attendu = risks.progression_attendue(p, date.today())
    phrases = [f"Le projet « {p.name} » est au statut « {p.status} » avec une progression de {p.progress_pct} %"
               + (f" pour {attendu * 100:.0f} % du délai écoulé." if attendu is not None and p.status != "Terminé"
                  else ".")]
    if evaluation and evaluation["factors"]:
        phrases.append(f"Score de risque : {evaluation['score']}/100 ({evaluation['level']}). Constats : "
                       + " ; ".join(x["detail"] for x in evaluation["factors"]))
        reco = "Recommandation : examiner ces points avec le porteur et le responsable de suivi et fixer un plan " \
               "d'action daté."
    elif evaluation:
        phrases.append("Aucun facteur de risque n'est détecté par les règles d'analyse.")
        reco = "Recommandation : maintenir le rythme de suivi actuel."
    else:
        reco = "Le projet n'est pas en phase d'incubation active : pas d'analyse de risque."
    return " ".join(phrases) + "\n\n" + reco


@router.post("/commentary")
def commentary(data: CommentaryRequest, db: Session = Depends(get_db), _: User = Depends(any_user)):
    """Propose un commentaire analytique (IA si disponible, sinon règles automatiques) que l'utilisateur relit."""
    if data.report_type == "project":
        return {"commentary": _commentaire_projet(db, data.project_id), "mode": "automatique"}
    f = filtres_json(data.filters)
    k = kpi.compute_kpis(db, f)
    texte, mode = ai_commentary(db, k, f.describe(db), reports.TITRES[data.report_type])
    return {"commentary": texte, "mode": mode}


@router.post("/generate")
def generate(data: ReportRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(any_user)):
    from app.services.common import audit

    f = filtres_json(data.filters)
    r = reports.build_report(db, data.report_type, f, data.commentary, data.project_id)
    contenu, mime, nom = reports.render(r, data.format)
    audit(db, user, "EXPORT_RAPPORT", "report", data.project_id, f"{r.title} ({data.format.upper()}) – {r.perimetre}",
          request)
    db.commit()
    return Response(contenu, media_type=mime,
                    headers={"Content-Disposition": f"attachment; filename=\"{nom}\"; filename*=UTF-8''{quote(nom)}"})
