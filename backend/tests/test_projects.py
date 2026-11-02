"""Tests : création, modification, cycle de vie, suppression d'un projet ; recherche et filtres."""
from __future__ import annotations

from datetime import date, timedelta


def _ref(client, h):
    domaine = client.get("/api/domains", headers=h).json()[0]["id"]
    cohortes = client.get("/api/cohorts", headers=h).json()
    return domaine, cohortes[0]["id"], cohortes


def _nouveau(client, h, nom="Projet de test automatisé"):
    domaine, cohorte, _ = _ref(client, h)
    return client.post("/api/projects", headers=h, json={
        "name": nom, "description": "Créé par les tests", "domain_id": domaine, "cohort_id": cohorte,
        "planned_budget": 4_000_000, "deadline": (date.today() + timedelta(days=200)).isoformat(),
        "leader": {"first_name": "Awa", "last_name": "Test", "gender": "Femme", "email": "awa.test@exemple.sn",
                   "profile": "Étudiant ISEP"}})


def test_creation_et_doublon(client, coordo):
    r = _nouveau(client, coordo, "Projet création")
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["status"] == "En attente" and p["application"]["status"] == "Reçue"
    assert p["funding_obtained"] == 0 and p["progress_pct"] == 0
    # Doublon détecté sans tenir compte des majuscules
    assert _nouveau(client, coordo, "PROJET création").status_code == 409


def test_validation_formulaire(client, coordo):
    domaine, cohorte, _ = _ref(client, coordo)
    r = client.post("/api/projects", headers=coordo, json={"name": "", "domain_id": domaine, "cohort_id": cohorte,
                                                           "planned_budget": -5})
    assert r.status_code == 422
    assert "budget prévisionnel" in r.json()["detail"]


def test_modification(client, coordo):
    pid = _nouveau(client, coordo, "Projet à modifier").json()["id"]
    r = client.put(f"/api/projects/{pid}", headers=coordo, json={"name": "Projet modifié", "planned_budget": 6_500_000})
    assert r.status_code == 200
    assert r.json()["name"] == "Projet modifié" and r.json()["planned_budget"] == 6_500_000


def test_cycle_de_vie_complet(client, coordo):
    pid = _nouveau(client, coordo, "Projet cycle de vie").json()["id"]
    # Transition interdite
    r = client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": "Terminé"})
    assert r.status_code == 422 and "Transition interdite" in r.json()["detail"]
    # Décision impossible sans évaluation
    client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": "En évaluation"})
    r = client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": "Sélectionné"})
    assert r.status_code == 422 and "évaluation" in r.json()["detail"]
    # Évaluation puis sélection
    r = client.post(f"/api/projects/{pid}/evaluations", headers=coordo, json={
        "evaluator": "Jury test", "score": 15.5, "recommendation": "Favorable", "evaluated_at": date.today().isoformat()})
    assert r.status_code == 201
    r = client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": "Sélectionné"})
    assert r.status_code == 200 and r.json()["application"]["status"] == "Acceptée"
    # Incubation : création automatique des 5 jalons
    r = client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": "En incubation"})
    assert len(r.json()["milestones"]) == 5
    # Progression : une baisse doit être justifiée
    assert client.post(f"/api/projects/{pid}/progress", headers=coordo, json={"progress_pct": 40}).status_code == 200
    assert client.post(f"/api/projects/{pid}/progress", headers=coordo, json={"progress_pct": 30}).status_code == 422
    assert client.post(f"/api/projects/{pid}/progress", headers=coordo,
                       json={"progress_pct": 30, "comment": "Réévaluation"}).status_code == 200
    for s in ("En développement", "Prototype réalisé", "Terminé"):
        r = client.post(f"/api/projects/{pid}/status", headers=coordo, json={"status": s})
        assert r.status_code == 200, r.text
    assert r.json()["progress_pct"] == 100
    assert r.json()["allowed_transitions"] == []
    assert [h["new_status"] for h in r.json()["history"]][-1] == "Terminé"


def test_jalon_futur_refuse(client, coordo):
    pid = _nouveau(client, coordo, "Projet jalon").json()["id"]
    demain = (date.today() + timedelta(days=1)).isoformat()
    r = client.post(f"/api/projects/{pid}/milestones", headers=coordo,
                    json={"title": "Jalon", "due_date": demain, "completed_date": demain})
    assert r.status_code == 422


def test_suppression_logique_et_restauration(client, coordo, admin):
    pid = _nouveau(client, coordo, "Projet à supprimer").json()["id"]
    avant = client.get("/api/analytics/kpis", headers=coordo).json()["all"]
    avant = {k["key"]: k["value"] for k in avant}
    assert client.delete(f"/api/projects/{pid}", headers=coordo).status_code == 204
    assert client.get(f"/api/projects/{pid}", headers=coordo).status_code == 404
    apres = {k["key"]: k["value"] for k in client.get("/api/analytics/kpis", headers=coordo).json()["all"]}
    assert apres["applications"] == avant["applications"] - 1
    archives = client.get("/api/admin/data-status", headers=admin).json()["archived"]
    assert any(a["id"] == pid for a in archives)
    assert client.post(f"/api/admin/projects/{pid}/restore", headers=admin).status_code == 200
    assert client.get(f"/api/projects/{pid}", headers=coordo).status_code == 200


def test_recherche_filtres_pagination(client, coordo):
    _nouveau(client, coordo, "Projet Recherche Unique XYZ")
    r = client.get("/api/projects?q=unique xyz", headers=coordo).json()
    assert r["total"] == 1 and r["items"][0]["name"] == "Projet Recherche Unique XYZ"
    tous = client.get("/api/projects?page_size=5", headers=coordo).json()
    assert len(tous["items"]) == 5 and tous["total"] > 5
    r = client.get("/api/projects?status=Terminé&page_size=200", headers=coordo).json()
    assert r["total"] > 0 and all(p["status"] == "Terminé" for p in r["items"])
    r = client.get("/api/projects?delayed_only=true&page_size=200", headers=coordo).json()
    assert r["total"] > 0 and all(p["is_delayed"] for p in r["items"])
    assert client.get("/api/projects?status=Inventé", headers=coordo).status_code == 422
