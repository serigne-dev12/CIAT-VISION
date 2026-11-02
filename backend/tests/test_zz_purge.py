"""Test exécuté en DERNIER : purge des données simulées puis remise en place (critère § 16.2)."""
from __future__ import annotations

from app.database import SessionLocal
from app.seed import seed_simulated


def test_purge_donnees_simulees(client, admin):
    assert client.get("/api/analytics/meta", headers=admin).json()["simulated"] is True
    assert client.post("/api/admin/purge-simulated?confirmation=oui", headers=admin).status_code == 422
    r = client.post("/api/admin/purge-simulated?confirmation=PURGER", headers=admin)
    assert r.status_code == 200 and r.json()["projets"] > 100
    assert client.get("/api/analytics/meta", headers=admin).json()["simulated"] is False
    k = {x["key"]: x["value"] for x in client.get("/api/analytics/kpis", headers=admin).json()["all"]}
    # Seuls les projets réels créés pendant les tests subsistent ; aucun projet simulé
    assert client.get("/api/projects?page_size=200", headers=admin).json()["total"] == k["applications"]
    assert all(not p["is_simulated"] for p in client.get("/api/projects?page_size=200", headers=admin).json()["items"])
    # Les comptes sont conservés
    assert client.get("/api/admin/users", headers=admin).status_code == 200


def test_reseed_apres_purge():
    with SessionLocal() as db:
        assert seed_simulated(db) is False  # la base contient encore des projets réels : pas de re-peuplement
