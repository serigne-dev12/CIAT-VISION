"""Tests : financements (contrôles des montants) et rapports PDF / Excel / CSV."""
from __future__ import annotations

import io
from datetime import date, timedelta

import pytest
from openpyxl import load_workbook

TYPES = ["global", "projects", "cohorts", "fundings", "performance", "delays"]


def _projet_selectionne(client, h) -> int:
    return client.get("/api/projects?status=En incubation&page_size=1", headers=h).json()["items"][0]["id"]


def _financement(pid, **kw):
    base = {"project_id": pid, "source_type": "Subvention", "amount_requested": 2_000_000, "amount_granted": 1_500_000,
            "amount_received": 500_000, "request_date": (date.today() - timedelta(days=30)).isoformat(),
            "grant_date": (date.today() - timedelta(days=10)).isoformat(), "status": "Partiellement reçu"}
    base.update(kw)
    return base


def test_financement_valide_et_projet_mis_a_jour(client, coordo):
    pid = _projet_selectionne(client, coordo)
    avant = client.get(f"/api/projects/{pid}", headers=coordo).json()["funding"]
    r = client.post("/api/fundings", headers=coordo, json=_financement(pid))
    assert r.status_code == 201, r.text
    assert r.json()["remaining"] == 1_000_000
    apres = client.get(f"/api/projects/{pid}", headers=coordo).json()["funding"]
    assert apres["granted"] == avant["granted"] + 1_500_000  # financement obtenu CALCULÉ, jamais saisi
    fid = r.json()["id"]
    r = client.put(f"/api/fundings/{fid}", headers=coordo,
                   json=_financement(pid, amount_received=1_500_000, status="Reçu"))
    assert r.status_code == 200 and r.json()["status"] == "Reçu"


@pytest.mark.parametrize("modif, message", [
    ({"amount_received": 1_800_000}, "reçu ≤ accordé ≤ demandé"),
    ({"amount_granted": 2_500_000}, "reçu ≤ accordé ≤ demandé"),
    ({"status": "Reçu"}, "ne correspond pas"),
    ({"grant_date": (date.today() - timedelta(days=60)).isoformat()}, "date d'accord"),
])
def test_financement_incoherent_refuse(client, coordo, modif, message):
    pid = _projet_selectionne(client, coordo)
    r = client.post("/api/fundings", headers=coordo, json=_financement(pid, **modif))
    assert r.status_code == 422 and message in r.json()["detail"]


def test_liste_et_synthese_financements(client, analyste):
    r = client.get("/api/fundings?page_size=10", headers=analyste).json()
    assert r["total"] > 10 and len(r["items"]) == 10
    resume = {x["key"]: x["value"] for x in r["summary"]}
    assert resume["remaining_to_receive"] == resume["funding_granted"] - resume["funding_received"]


@pytest.mark.parametrize("rtype", TYPES)
def test_rapport_pdf(client, coordo, rtype):
    r = client.post("/api/reports/generate", headers=coordo,
                    json={"report_type": rtype, "format": "pdf", "commentary": "Commentaire de test → vérifié."})
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF" and len(r.content) > 5000
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.parametrize("rtype", TYPES)
def test_rapport_excel(client, coordo, rtype):
    r = client.post("/api/reports/generate", headers=coordo, json={"report_type": rtype, "format": "xlsx"})
    assert r.status_code == 200
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames[0] == "Synthèse"
    assert "CIAT VISION" in wb["Synthèse"]["A1"].value
    assert any("SIMULÉES" in str(c.value) for row in wb["Synthèse"].iter_rows() for c in row if c.value)


def test_rapport_csv_et_filtres(client, coordo):
    cohorte = client.get("/api/cohorts", headers=coordo).json()[-1]
    r = client.post("/api/reports/generate", headers=coordo, json={
        "report_type": "projects", "format": "csv", "filters": {"cohort_ids": [cohorte["id"]]}})
    texte = r.content.decode("utf-8-sig")
    assert r.status_code == 200 and texte.startswith("CIAT VISION")
    assert cohorte["name"] in texte and "DONNÉES SIMULÉES" in texte


def test_rapport_coherent_avec_tableau_de_bord(client, coordo):
    k = {x["key"]: x["value"] for x in client.get("/api/analytics/kpis", headers=coordo).json()["all"]}
    r = client.post("/api/reports/generate", headers=coordo, json={"report_type": "global", "format": "xlsx"})
    ws = load_workbook(io.BytesIO(r.content))["Synthèse"]
    valeurs = {row[0].value: row[1].value for row in ws.iter_rows() if row[0].value}
    assert valeurs["Candidatures reçues"] == k["applications"]
    assert valeurs["Projets en retard"] == k["delayed"]


def test_commentaire_automatique(client, coordo):
    r = client.post("/api/reports/commentary", headers=coordo, json={"report_type": "global"})
    assert r.status_code == 200
    assert r.json()["mode"] == "automatique" and "Recommandations" in r.json()["commentary"]
