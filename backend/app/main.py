"""Point d'entrée de l'API CIAT VISION.

Lancement local :  uvicorn app.main:app --reload
Documentation interactive de l'API : http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import SessionLocal
from app.routers import (admin, alerts, analytics, assistant, auth, fundings, imports, pilotage, projects, reference,
                         reports)
from app.seed import create_demo_accounts, ensure_reference_data, seed_simulated

log = logging.getLogger("ciat")
settings = get_settings()

# Traduction des principaux messages de validation Pydantic
MESSAGES = {
    "missing": "champ obligatoire",
    "string_too_short": "texte trop court",
    "string_too_long": "texte trop long",
    "string_pattern_mismatch": "format invalide",
    "greater_than_equal": "valeur trop petite",
    "less_than_equal": "valeur trop grande",
    "literal_error": "valeur non autorisée",
    "enum": "valeur non autorisée",
    "int_parsing": "nombre entier attendu",
    "int_from_float": "nombre entier attendu",
    "float_parsing": "nombre attendu",
    "date_parsing": "date invalide",
    "date_from_datetime_parsing": "date invalide",
    "bool_parsing": "valeur oui/non attendue",
    "value_error": None,  # message déjà rédigé en français dans les validateurs
}
CHAMPS = {"name": "nom", "full_name": "nom complet", "username": "identifiant", "password": "mot de passe",
          "new_password": "nouveau mot de passe", "email": "e-mail", "phone": "téléphone", "domain_id": "domaine",
          "cohort_id": "cohorte", "planned_budget": "budget prévisionnel", "deadline": "date limite",
          "amount_requested": "montant demandé", "amount_granted": "montant accordé",
          "amount_received": "montant reçu", "request_date": "date de demande", "score": "note",
          "first_name": "prénom", "last_name": "nom", "start_date": "date de début", "end_date": "date de fin"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Au démarrage : référentiels, comptes de démonstration et données simulées si la base est vide."""
    try:
        with SessionLocal() as db:
            ensure_reference_data(db)
            if settings.create_demo_accounts:
                create_demo_accounts(db)
            if settings.seed_simulated_data and seed_simulated(db):
                log.info("Base peuplée avec les données SIMULÉES de démonstration.")
            from app.services.alerts import generer
            generer(db)  # alertes à jour dès le démarrage
            db.commit()
    except Exception as e:  # la base n'est pas encore migrée : on démarre quand même pour afficher l'erreur
        log.error("Initialisation des données impossible : %s (avez-vous lancé « alembic upgrade head » ?)", e)
    yield


app = FastAPI(title="CIAT VISION – API", version="1.0.0", lifespan=lifespan,
              description="Plateforme de pilotage et d'analyse décisionnelle du CIAT – ISEP Amadou Trawaré de "
                          "Diamniadio. Toutes les routes (sauf la connexion) exigent un jeton JWT.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"], expose_headers=["Content-Disposition"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_request: Request, exc: RequestValidationError):
    erreurs = []
    for e in exc.errors():
        champ = next((str(x) for x in reversed(e.get("loc", [])) if isinstance(x, str) and x not in ("body", "query")),
                     "")
        msg = MESSAGES.get(e.get("type", ""), "") or str(e.get("msg", "")).removeprefix("Value error, ")
        erreurs.append(f"{CHAMPS.get(champ, champ)} : {msg}" if champ else msg)
    return JSONResponse(status_code=422, content={"detail": " ; ".join(erreurs) or "Données invalides."})


TRADUCTIONS_HTTP = {
    "There was an error parsing the body": "Corps de requête invalide : JSON encodé en UTF-8 attendu.",
    "Not Found": "Ressource introuvable.",
    "Method Not Allowed": "Méthode non autorisée.",
    "Not authenticated": "Authentification requise.",
}


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    detail = TRADUCTIONS_HTTP.get(exc.detail, exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=getattr(exc, "headers", None))


@app.exception_handler(IntegrityError)
async def integrity_error(_request: Request, exc: IntegrityError):
    log.warning("Contrainte d'intégrité : %s", exc.orig)
    return JSONResponse(status_code=409, content={"detail": "Opération refusée : elle violerait une règle d'intégrité "
                                                             "des données (doublon ou référence utilisée)."})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, exc: Exception):
    log.exception("Erreur inattendue : %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur. L'incident a été journalisé."})


for r in (auth, reference, projects, fundings, analytics, assistant, reports, imports, admin, alerts, pilotage):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health", tags=["Système"])
def health():
    return {"status": "ok", "app": settings.app_name}


# ------------------------------------------------------------------ frontend compilé (déploiement en un service)
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{chemin:path}", include_in_schema=False)
    def spa(chemin: str):
        if chemin.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Ressource introuvable."})
        fichier = (DIST / chemin).resolve()
        if chemin and fichier.is_file() and DIST in fichier.parents:
            return FileResponse(fichier)
        return FileResponse(DIST / "index.html")
