"""Tests : connexion, session, blocage après échecs, permissions par rôle (critères § 16.2)."""
from __future__ import annotations


def test_login_ok_et_profil(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Admin@2026"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "admin" and body["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["username"] == "admin"
    assert "password_hash" not in me.json()


def test_mauvais_mot_de_passe_refuse(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "faux"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Identifiant ou mot de passe incorrect."


def test_identifiant_inconnu_meme_message(client):
    r = client.post("/api/auth/login", json={"username": "inconnu", "password": "x"})
    assert r.status_code == 401 and r.json()["detail"] == "Identifiant ou mot de passe incorrect."


def test_sans_jeton_ou_jeton_invalide(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_blocage_apres_5_echecs(client, admin):
    r = client.post("/api/admin/users", headers=admin, json={"username": "victime", "full_name": "Compte test",
                                                             "role": "analyst", "password": "Victime2026"})
    assert r.status_code == 201
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "victime", "password": "mauvais"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "victime", "password": "Victime2026"})
    assert r.status_code == 423 and "bloqué" in r.json()["detail"]


def test_compte_desactive(client, admin):
    r = client.post("/api/admin/users", headers=admin, json={"username": "inactif", "full_name": "Compte inactif",
                                                             "role": "analyst", "password": "Inactif2026"})
    uid = r.json()["id"]
    assert client.put(f"/api/admin/users/{uid}", headers=admin, json={"is_active": False}).status_code == 200
    r = client.post("/api/auth/login", json={"username": "inactif", "password": "Inactif2026"})
    assert r.status_code == 403


def test_refresh_renouvelle_la_session(client, coordo):
    r = client.post("/api/auth/refresh", headers=coordo)
    assert r.status_code == 200 and r.json()["access_token"]


def test_politique_mot_de_passe(client, admin):
    r = client.post("/api/admin/users", headers=admin, json={"username": "faible", "full_name": "Faible",
                                                             "role": "analyst", "password": "motdepasse"})
    assert r.status_code == 422


def test_analyste_ne_peut_pas_modifier(client, analyste):
    assert client.post("/api/projects", headers=analyste, json={"name": "X", "domain_id": 1, "cohort_id": 1}
                       ).status_code == 403
    assert client.delete("/api/projects/1", headers=analyste).status_code == 403
    assert client.post("/api/fundings", headers=analyste, json={}).status_code in (403, 422)
    assert client.get("/api/imports/entities", headers=analyste).status_code == 403


def test_seul_admin_administre(client, coordo, analyste):
    for h in (coordo, analyste):
        assert client.get("/api/admin/users", headers=h).status_code == 403
        assert client.get("/api/admin/audit-logs", headers=h).status_code == 403
        assert client.post("/api/admin/purge-simulated?confirmation=PURGER", headers=h).status_code == 403


def test_analyste_peut_consulter_et_exporter(client, analyste):
    assert client.get("/api/analytics/kpis", headers=analyste).status_code == 200
    assert client.get("/api/projects", headers=analyste).status_code == 200
    r = client.post("/api/reports/generate", headers=analyste, json={"report_type": "global", "format": "csv"})
    assert r.status_code == 200


def test_coordonnees_masquees_pour_analyste(client, analyste, coordo):
    pid = client.get("/api/projects?page_size=1", headers=coordo).json()["items"][0]["id"]
    vu_coordo = client.get(f"/api/projects/{pid}", headers=coordo).json()["leader"]
    vu_analyste = client.get(f"/api/projects/{pid}", headers=analyste).json()["leader"]
    assert vu_coordo["email"] and vu_analyste["email"] is None and vu_analyste["phone"] is None


def test_changement_mot_de_passe(client, admin):
    client.post("/api/admin/users", headers=admin, json={"username": "change", "full_name": "Change",
                                                         "role": "coordinator", "password": "Ancien2026"})
    h = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"username": "change",
                                                                           "password": "Ancien2026"}).json()["access_token"]}
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "faux", "new_password": "Nouveau2026"}).status_code == 422
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "Ancien2026", "new_password": "Nouveau2026"}).status_code == 204
    assert client.post("/api/auth/login", json={"username": "change", "password": "Nouveau2026"}).status_code == 200
