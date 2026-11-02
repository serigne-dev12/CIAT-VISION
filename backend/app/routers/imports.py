"""Module 10 – Importation de données Excel / CSV (prévisualisation puis confirmation)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import editor
from app.models import User
from app.services import importer

router = APIRouter(prefix="/imports", tags=["Importation"])


@router.get("/entities")
def entities(_: User = Depends(editor)):
    return [{"key": k, "label": importer.LABELS[k],
             "columns": [{"name": c.name, "required": c.required, "kind": c.kind, "choices": c.choices}
                         for c in cols]} for k, cols in importer.ENTITIES.items()]


@router.get("/template/{entity}")
def template(entity: str, format: str = "xlsx", _: User = Depends(editor)):
    if entity not in importer.ENTITIES or format not in ("xlsx", "csv"):
        raise HTTPException(404, "Modèle introuvable.")
    contenu, mime, nom = importer.template(entity, format)
    return Response(contenu, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{nom}"'})


async def _analyse(db: Session, entity: str, file: UploadFile):
    contenu = await file.read(importer.MAX_BYTES + 1)
    rows = importer.read_file(contenu, file.filename or "")
    return importer.validate(db, entity, rows)


def _summary(missing, results) -> dict:
    return {
        "missing_columns": missing,
        "total_rows": len(results),
        "valid_rows": sum(1 for r in results if r.valid),
        "error_rows": sum(1 for r in results if r.errors),
        "duplicate_rows": sum(1 for r in results if r.duplicate and not r.errors),
        "rows": [{"line": r.line, "valid": r.valid, "errors": r.errors, "duplicate": r.duplicate,
                  "data": {k: v for k, v in r.data.items() if not k.startswith("_")}} for r in results[:500]],
    }


@router.post("/preview")
async def preview(entity: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db),
                  _: User = Depends(editor)):
    """Analyse le fichier SANS rien enregistrer."""
    missing, results = await _analyse(db, entity, file)
    return _summary(missing, results)


@router.post("/commit")
async def commit(request: Request, entity: str = Form(...), confirm: bool = Form(False),
                 ignore_invalid: bool = Form(False), file: UploadFile = File(...), db: Session = Depends(get_db),
                 user: User = Depends(editor)):
    """Ré-analyse le fichier puis l'enregistre en une seule transaction, après confirmation explicite."""
    if not confirm:
        raise HTTPException(422, "Confirmation requise avant l'importation.")
    missing, results = await _analyse(db, entity, file)
    if missing:
        raise HTTPException(422, f"Colonnes obligatoires manquantes : {', '.join(missing)}.")
    invalides = [r for r in results if not r.valid]
    if invalides and not ignore_invalid:
        raise HTTPException(422, f"{len(invalides)} ligne(s) en erreur ou en double. Corrigez le fichier ou "
                                 "confirmez l'import des seules lignes valides.")
    if not any(r.valid for r in results):
        raise HTTPException(422, "Aucune ligne valide à importer.")
    try:
        bilan = importer.commit(db, entity, results, user, file.filename or "fichier")
        db.commit()
    except Exception:
        db.rollback()  # tout ou rien
        raise
    return bilan
