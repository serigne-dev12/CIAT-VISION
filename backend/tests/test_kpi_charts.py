"""Tests : chaque indicateur est comparé à un calcul INDÉPENDANT (Python sur les lignes brutes),
conformément au critère d'acceptation « chaque KPI est identique au résultat d'une requête de contrôle »."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import Application, Cohort, Funding, Milestone, Project
from app.services import kpi

ACTIFS = {"Sélectionné", "En incubation", "En développement", "Prototype réalisé"}
INCUBES = {"En incubation", "En développement", "Prototype réalisé", "Terminé", "Suspendu"}


def _attendu(db, cohort_ids=None, domain_ids=None, statuses=None, d1=None, d2=None):
    """Recalcul « à la main » des indicateurs, sans passer par le moteur SQL."""
    today = date.today()
    lignes = []
    for p, a in db.execute(select(Project, Application).join(Application, Application.id == Project.application_id)):
        if p.is_archived or (cohort_ids and p.cohort_id not in cohort_ids) or (domain_ids and p.domain_id not in domain_ids):
            continue
        if (statuses and p.status not in statuses) or (d1 and a.submitted_at < d1) or (d2 and a.submitted_at > d2):
            continue
        lignes.append((p, a))
    ids = {p.id for p, _ in lignes}
    jalons_retard = {m.project_id for m in db.scalars(select(Milestone)) if m.completed_date is None and m.due_date < today}
    retard = [p for p, _ in lignes if p.status in ACTIFS and ((p.deadline and p.deadline < today) or p.id in jalons_retard)]
    acc = sum(1 for _, a in lignes if a.status == "Acceptée")
    rej = sum(1 for _, a in lignes if a.status == "Rejetée")
    incubes = sum(1 for p, _ in lignes if p.status in INCUBES)
    actifs = [p for p, _ in lignes if p.status in ACTIFS]
    fin = [f for f in db.scalars(select(Funding)) if f.project_id in ids]
    return {
        "applications": len(lignes),
        "total_projects": sum(1 for p, _ in lignes if p.status != "Non retenu"),
        "selected": acc,
        "in_incubation": sum(1 for p, _ in lignes if p.status in ("En incubation", "En développement")),
        "prototypes": sum(1 for p, _ in lignes if p.status in ("Prototype réalisé", "Terminé")),
        "completed": sum(1 for p, _ in lignes if p.status == "Terminé"),
        "delayed": len(retard),
        "funding_received": sum(f.amount_received for f in fin),
        "funding_granted": sum(f.amount_granted for f in fin),
        # Un filtre de statut ne garde que des dossiers d'un statut donné : taux non calculable (dénominateur biaisé)
        "selection_rate": round(acc / (acc + rej), 4) if acc + rej and not statuses else None,
        "completion_rate": round(sum(1 for p, _ in lignes if p.status == "Terminé") / incubes, 4) if incubes else None,
        "delay_rate": round(len(retard) / len(actifs), 4) if actifs else None,
        "avg_progress": round(sum(p.progress_pct for p in actifs) / len(actifs), 1) if actifs else None,
    }


def _compare(db, f: kpi.Filters):
    calc = kpi.compute_kpis(db, f)
    att = _attendu(db, f.cohort_ids, f.domain_ids, f.statuses, f.start_date, f.end_date)
    for k, v in att.items():
        assert calc[k] == v, f"{k} : moteur={calc[k]} contrôle={v} ({f})"


def test_kpi_sans_filtre(db):
    _compare(db, kpi.Filters())


def test_kpi_par_cohorte_et_domaine(db):
    cohortes = list(db.scalars(select(Cohort.id)))
    for c in cohortes:
        _compare(db, kpi.Filters(cohort_ids=[c]))
    _compare(db, kpi.Filters(domain_ids=[1, 3]))
    _compare(db, kpi.Filters(statuses=["Terminé", "Prototype réalisé"]))


def test_kpi_par_periode(db):
    annee = date.today().year
    _compare(db, kpi.Filters(start_date=date(annee - 1, 1, 1), end_date=date(annee - 1, 12, 31)))


def test_denominateur_nul_non_calculable(db):
    f = kpi.Filters(start_date=date(1999, 1, 1), end_date=date(1999, 12, 31))
    k = kpi.compute_kpis(db, f)
    assert k["applications"] == 0
    assert k["selection_rate"] is None and k["completion_rate"] is None and k["delay_rate"] is None
    assert kpi.format_value("selection_rate", None) == "non calculable"


def test_suspendus_jamais_en_retard(db):
    retards = kpi.delayed_projects(db, kpi.Filters())
    assert retards and all(r["status"] in ACTIFS for r in retards)


def test_seuil_de_tolerance(client, admin, db):
    avant = kpi.compute_kpis(db, kpi.Filters())["delayed"]
    client.put("/api/admin/settings", headers=admin, json={"delay_tolerance_days": 180})
    with type(db)(bind=db.get_bind()) as s2:
        apres = kpi.compute_kpis(s2, kpi.Filters())["delayed"]
    client.put("/api/admin/settings", headers=admin, json={"delay_tolerance_days": 0})
    assert apres <= avant


def test_api_kpis_filtres(client, analyste, db):
    c = list(db.scalars(select(Cohort.id).order_by(Cohort.year)))[0]
    tout = client.get("/api/analytics/kpis", headers=analyste).json()
    filtre = client.get(f"/api/analytics/kpis?cohort_id={c}", headers=analyste).json()
    v = lambda r, k: next(x["value"] for x in r["all"] if x["key"] == k)  # noqa: E731
    assert v(filtre, "applications") < v(tout, "applications")
    assert len(tout["dashboard"]) == 10  # tableau de bord stratégique V2
    assert "Cohortes" in filtre["perimetre"]


def test_graphiques_coherents_avec_kpi(client, analyste):
    ch = client.get("/api/analytics/charts", headers=analyste).json()
    k = {x["key"]: x["value"] for x in client.get("/api/analytics/kpis", headers=analyste).json()["all"]}
    assert sum(s["count"] for s in ch["by_status"]) == k["applications"]
    assert sum(m["received"] for m in ch["applications_monthly"]) == k["applications"]
    assert sum(d["projects"] for d in ch["by_domain"]) == k["total_projects"]
    assert sum(x["received"] for x in ch["fundings_by_source"]) == k["funding_received"]
    assert sum(x["count"] for x in ch["progress_distribution"]) == k["active"]
    assert ch["cohorts"] and all("success_rate" in c for c in ch["cohorts"])


@pytest.mark.parametrize("periode", [(date.today() - timedelta(days=60), date.today())])
def test_graphique_periode(client, analyste, periode):
    d1, d2 = periode
    ch = client.get(f"/api/analytics/charts?start_date={d1}&end_date={d2}", headers=analyste).json()
    assert all(d1.strftime("%Y-%m") <= m["month"] <= d2.strftime("%Y-%m") for m in ch["applications_monthly"])
