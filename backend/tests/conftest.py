"""Configuration des tests : base PostgreSQL DÉDIÉE (jamais la base de développement), recréée à chaque session."""
from __future__ import annotations

import os

from pathlib import Path


def _url_de_test() -> str:
    """TEST_DATABASE_URL : variable d'environnement, sinon ligne du fichier backend/.env (non versionné),
    sinon base de test du docker-compose.yml."""
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for ligne in env.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("TEST_DATABASE_URL="):
                return ligne.split("=", 1)[1].strip()
    return "postgresql+psycopg://ciat:ciat_local@127.0.0.1:5432/ciat_vision_test"


os.environ["DATABASE_URL"] = _url_de_test()
os.environ["ANTHROPIC_API_KEY"] = ""  # les tests n'appellent jamais le vrai service d'IA
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401
from app.config import get_settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.seed import create_demo_accounts, ensure_reference_data, seed_simulated  # noqa: E402

assert "test" in get_settings().database_url, "Les tests doivent utiliser une base de test dédiée."


@pytest.fixture(scope="session", autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_reference_data(db)
        create_demo_accounts(db)
        seed_simulated(db)
    yield


@pytest.fixture(scope="session")
def client(database):
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    with SessionLocal() as s:
        yield s


def _login(client: TestClient, username: str, password: str) -> dict:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin", "Admin@2026")


@pytest.fixture(scope="session")
def coordo(client):
    return _login(client, "coordo", "Coordo@2026")


@pytest.fixture(scope="session")
def analyste(client):
    return _login(client, "analyste", "Analyste@2026")
