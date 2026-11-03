"""Tests V2 : filtres avancés, comparaisons, alertes, risques, objectifs, nouveaux rapports, filtres spécifiques."""
from __future__ import annotations

import io
from datetime import date, timedelta

import pytest
from openpyxl import load_workbook
from sqlalchemy import select

from app.models import Alert, Cohort, Domain, Project, Responsable
from app.services import alerts, kpi, risks


def _v(r, cle):
    return next(x["value"] for x in r["all"] if x["key"] == cle)


# ------------------------------------------------------------------ filtres V2 (calculés côté serveur)
def test_filtres_niveaux_et_responsable(client, analyste, db):
    tout = client.get("/api/analytics/kpis", headers=analyste).json()
    faible = client.get("/api/analytics/kpis?performance=Faible", headers=analyste).json()
    assert 0 < _v(faible, "applications") < _v(tout, "applications")
    assert "Performance : Faible" in faible["perimetre"]
    r = db.scalars(select(Responsable)).first()
    par_resp = client.get(f"/api/analytics/kpis?responsible_id={r.id}", headers=analyste).json()
    attendu = db.query(Project).filter(Project.responsible_id == r.id, Project.is_archived.is_(False)).count()
    assert _v(par_resp, "applications") == attendu
    non_finance = client.get("/api/analytics/kpis?funding_level=Non financé", headers=analyste).json()
    assert _v(non_finance, "funding_granted") == 0  # aucun montant accordé sur ce périmètre


def test_filtres_combines_et_niveaux_coherents(client, analyste):
    d = client.get("/api/analytics/charts", headers=analyste).json()
    assert sum(x["count"] for x in d["levels"]["performance"]) == sum(s["count"] for s in d["by_status"])
    combi = client.get("/api/analytics/kpis?performance=Faible&status=En développement", headers=analyste).json()
    assert _v(combi, "applications") <= _v(client.get("/api/analytics/kpis?performance=Faible",
                                                      headers=analyste).json(), "applications")


@pytest.mark.parametrize("param", ["performance=Excellente", "funding_level=Énorme", "status=Brouillon"])
def test_filtres_invalides_refuses(client, analyste, param):
    assert client.get(f"/api/analytics/kpis?{param}", headers=analyste).status_code == 422


def test_etat_vide(client, analyste):
    r = client.get("/api/analytics/kpis?start_date=1990-01-01&end_date=1990-12-31", headers=analyste).json()
    assert _v(r, "applications") == 0 and _v(r, "completion_rate") is None


def test_niveau_performance_conforme_a_la_definition(db):
    """Le niveau calculé en SQL est identique au calcul Python de la progression attendue."""
    today = date.today()
    for p, niveau in db.execute(select(Project, kpi.performance_level_expr(today))
                                .where(Project.status.in_(["En incubation", "En développement"]))).all():
        attendu = risks.progression_attendue(p, today)
        ecart = p.progress_pct - attendu * 100
        assert niveau == ("Élevée" if ecart >= -10 else "Moyenne" if ecart >= -30 else "Faible"), (p.id, ecart)


def test_filtres_specifiques_projets_et_financements(client, coordo, db):
    r = client.get("/api/projects?progress_min=40&progress_max=60&page_size=200", headers=coordo).json()
    assert r["total"] > 0 and all(40 <= p["progress_pct"] <= 60 for p in r["items"])
    resp = db.scalars(select(Responsable)).first()
    r = client.get(f"/api/projects?responsible_id={resp.id}&page_size=200", headers=coordo).json()
    assert r["total"] > 0 and all(p["responsible"] == resp.full_name for p in r["items"])
    f = client.get("/api/fundings?amount_min=1000000&amount_max=2000000&page_size=200", headers=coordo).json()
    assert all(1_000_000 <= x["amount_requested"] <= 2_000_000 for x in f["items"])
    partenaire = next(x for x in client.get("/api/fundings?page_size=200", headers=coordo).json()["items"]
                      if x["partner_id"])
    f = client.get(f"/api/fundings?partner_id={partenaire['partner_id']}&page_size=200", headers=coordo).json()
    assert f["total"] > 0 and all(x["partner_id"] == partenaire["partner_id"] for x in f["items"])
    assert client.get("/api/fundings?amount_min=5&amount_max=1", headers=coordo).status_code == 422


def test_indicateur_ventile(client, analyste):
    r = client.get("/api/analytics/indicator?key=completion_rate&by=domain", headers=analyste).json()
    assert r["label"] == "Taux d'achèvement" and len(r["items"]) >= 2
    assert client.get("/api/analytics/indicator?key=inconnu", headers=analyste).status_code == 422


# ------------------------------------------------------------------ comparaisons
def test_comparaison_domaines_coherente_avec_les_kpi(client, analyste, db):
    ids = [d.id for d in db.scalars(select(Domain).order_by(Domain.id)).all()[:2]]
    r = client.post("/api/compare", headers=analyste, json={"dimension": "domain", "ids": ids}).json()
    assert len(r["items"]) == 2 and set(r["metrics"]) == set(kpi.COMPARISON_KPIS)
    for item in r["items"]:
        k = {x["key"]: x["value"] for x in client.get(f"/api/analytics/kpis?domain_id={item['id']}",
                                                       headers=analyste).json()["all"]}
        assert item["completion_rate"] == k["completion_rate"] and item["total_projects"] == k["total_projects"]


def test_comparaison_periodes_avertit_si_durees_differentes(client, analyste):
    an = date.today().year
    r = client.post("/api/compare", headers=analyste, json={"dimension": "period", "periods": [
        {"start_date": f"{an - 2}-01-01", "end_date": f"{an - 2}-12-31"},
        {"start_date": f"{an - 1}-01-01", "end_date": f"{an - 1}-03-31"}]}).json()
    assert len(r["items"]) == 2 and any("même durée" in w for w in r["warnings"])


def test_comparaison_projets_et_responsables(client, analyste, db):
    ids = list(db.scalars(select(Project.id).where(Project.status.in_(["En développement", "Terminé"])).limit(3)))
    r = client.post("/api/compare", headers=analyste, json={"dimension": "project", "ids": ids}).json()
    assert len(r["items"]) == 3 and all("progress_pct" in i and "funding_granted" in i for i in r["items"])
    resp = list(db.scalars(select(Responsable.id).limit(3)))
    r = client.post("/api/compare", headers=analyste, json={"dimension": "responsible", "ids": resp}).json()
    assert len(r["items"]) == 3
    assert client.post("/api/compare", headers=analyste, json={"dimension": "domain", "ids": [1]}).status_code == 422


# ------------------------------------------------------------------ risques
def test_analyse_des_risques(client, analyste):
    r = client.get("/api/risks", headers=analyste).json()
    assert r["total"] > 0 and "pas une prédiction" in r["avertissement"]
    for p in r["projets"]:
        assert p["score"] == min(100, sum(f["points"] for f in p["factors"]))
        assert p["level"] == ("Élevé" if p["score"] >= 50 else "Modéré" if p["score"] >= 25 else "Faible")
        assert all(f["detail"] for f in p["factors"])  # chaque point de risque est expliqué
    filtre = client.get("/api/risks?performance=Faible", headers=analyste).json()
    assert filtre["total"] <= r["total"]


# ------------------------------------------------------------------ objectifs
def test_objectifs_crud_et_statuts(client, coordo, analyste):
    an = date.today().year
    corps = {"label": "Projets à terminer (test)", "indicator": "projets_termines", "target_value": 1,
             "start_date": f"{an - 3}-01-01", "end_date": f"{an + 1}-12-31"}
    assert client.post("/api/objectives", headers=analyste, json=corps).status_code == 403
    r = client.post("/api/objectives", headers=coordo, json=corps)
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["current"] >= 1 and o["status"] == "Atteint" and o["gap"] == o["current"] - 1
    r = client.put(f"/api/objectives/{o['id']}", headers=coordo, json={**corps, "target_value": 100000})
    assert r.json()["status"] in ("En retard", "En bonne voie")
    passe = {**corps, "start_date": f"{an - 3}-01-01", "end_date": f"{an - 3}-06-30", "target_value": 100000}
    r = client.put(f"/api/objectives/{o['id']}", headers=coordo, json=passe)
    assert r.json()["status"] == "Non atteint"
    assert client.post("/api/objectives", headers=coordo,
                       json={**corps, "indicator": "taux_achevement", "target_value": 150}).status_code == 422
    assert client.delete(f"/api/objectives/{o['id']}", headers=coordo).status_code == 204
    liste = client.get("/api/objectives", headers=analyste).json()
    assert len(liste["indicators"]) == 5 and all("status" in x for x in liste["items"])


# ------------------------------------------------------------------ alertes
def test_alertes_generation_deduplication_resolution(db):
    premier = alerts.generer(db)
    db.commit()
    second = alerts.generer(db)
    db.commit()
    assert second["creees"] == 0 and second["mises_a_jour"] == premier["ouvertes"]
    for a in db.scalars(select(Alert).where(Alert.resolved_at.is_(None))):
        assert a.problem and a.explanation and a.recommended_action and a.level in alerts.NIVEAUX
    # Résolution : un projet en retard qui est terminé ne doit plus avoir d'alerte de retard ouverte
    ouverte = db.scalars(select(Alert).where(Alert.resolved_at.is_(None), Alert.type == "Projet en retard")).first()
    p = db.get(Project, ouverte.project_id)
    ancien = (p.status, p.progress_pct, p.deadline)
    for m in p.milestones:
        m.completed_date = m.completed_date or date.today()
    p.deadline = date.today() + timedelta(days=200)
    db.commit()
    alerts.generer(db)
    db.commit()
    db.refresh(ouverte)
    assert ouverte.resolved_at is not None
    p.status, p.progress_pct, p.deadline = ancien
    db.commit()


def test_aucune_alerte_echeance_sans_date_limite(db):
    p = db.scalars(select(Project).where(Project.status == "En développement")).first()
    ancienne = p.deadline
    p.deadline = None
    db.commit()
    cles = {d["key"] for d in alerts.detecter(db)}
    assert f"echeance:{p.id}" not in cles and f"donnees:{p.id}" in cles  # donnée manquante signalée, pas inventée
    p.deadline = ancienne
    db.commit()


def test_alertes_api_lecture_archivage_droits(client, analyste, coordo, admin):
    r = client.get("/api/alerts", headers=analyste).json()
    assert r["total"] > 0 and r["items"][0]["level"] == "Critique"  # tri par priorité
    aid = r["items"][0]["id"]
    s1 = client.get("/api/alerts/summary", headers=analyste).json()
    assert client.post(f"/api/alerts/{aid}/read", headers=analyste).status_code == 204
    s2 = client.get("/api/alerts/summary", headers=analyste).json()
    assert s2["unread"] == s1["unread"] - 1
    # Le marquage « lu » est propre à chaque utilisateur
    assert any(i["id"] == aid and not i["is_read"] for i in client.get("/api/alerts", headers=coordo).json()["items"])
    assert client.get("/api/alerts?level=Critique", headers=analyste).json()["total"] <= r["total"]
    assert client.post(f"/api/alerts/{aid}/archive", headers=analyste).status_code == 403
    assert client.post(f"/api/alerts/{aid}/archive", headers=coordo).status_code == 200
    assert any(i["id"] == aid for i in client.get("/api/alerts?statut=archivees", headers=coordo).json()["items"])
    assert client.delete(f"/api/alerts/{aid}", headers=coordo).status_code == 403
    assert client.delete(f"/api/alerts/{aid}", headers=admin).status_code == 204
    assert client.post("/api/alerts/read-all", headers=analyste).json()["marquees"] >= 0
    assert client.get("/api/alerts/summary", headers=analyste).json()["unread"] == 0


# ------------------------------------------------------------------ rapports V2
@pytest.mark.parametrize("rtype", ["domains", "alerts", "global", "performance"])
def test_rapports_v2_respectent_les_filtres(client, coordo, db, rtype):
    c = db.scalars(select(Cohort).order_by(Cohort.year)).first()
    for fmt in ("pdf", "xlsx", "csv"):
        r = client.post("/api/reports/generate", headers=coordo, json={
            "report_type": rtype, "format": fmt, "filters": {"cohort_ids": [c.id], "performance_levels": ["Élevée"]}})
        assert r.status_code == 200, r.text
    texte = client.post("/api/reports/generate", headers=coordo, json={
        "report_type": rtype, "format": "csv",
        "filters": {"cohort_ids": [c.id], "performance_levels": ["Élevée"]}}).content.decode("utf-8-sig")
    assert c.name in texte and "Performance : Élevée" in texte


def test_rapport_par_projet(client, coordo, db):
    pid = db.scalar(select(Project.id).where(Project.status == "En développement"))
    assert client.post("/api/reports/generate", headers=coordo,
                       json={"report_type": "project", "format": "pdf"}).status_code == 422
    r = client.post("/api/reports/generate", headers=coordo,
                    json={"report_type": "project", "format": "xlsx", "project_id": pid})
    feuilles = load_workbook(io.BytesIO(r.content)).sheetnames
    assert "Fiche du projet" in feuilles and "Jalons" in feuilles
    c = client.post("/api/reports/commentary", headers=coordo, json={"report_type": "project", "project_id": pid})
    assert "Recommandation" in c.json()["commentary"]


def test_projet_avec_responsable(client, coordo, db):
    resp = db.scalars(select(Responsable)).first()
    domaine = db.scalars(select(Domain)).first()
    cohorte = db.scalars(select(Cohort)).first()
    r = client.post("/api/projects", headers=coordo, json={
        "name": "Projet avec responsable", "domain_id": domaine.id, "cohort_id": cohorte.id,
        "responsible_id": resp.id, "leader": {"first_name": "Test", "last_name": "Resp", "profile": "Externe"}})
    assert r.status_code == 201 and r.json()["responsible"]["name"] == resp.full_name
    assert client.put(f"/api/projects/{r.json()['id']}", headers=coordo,
                      json={"responsible_id": 999999}).status_code == 422
    assert client.get("/api/responsables", headers=coordo).json()[0]["full_name"]
