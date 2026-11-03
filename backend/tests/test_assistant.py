"""Tests de l'assistant : fonctions autorisées, mode dégradé, boucle d'appel d'outils (client Claude simulé)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import analysis
from app.services import assistant as svc


def test_fonction_non_autorisee_refusee(db):
    with pytest.raises(analysis.AnalysisError):
        analysis.run(db, "executer_requete_sql", {"requete": "DROP TABLE projects"})


def test_parametres_invalides(db):
    with pytest.raises(analysis.AnalysisError, match="inconnu"):
        analysis.run(db, "indicateurs_cles", {"filtres": {"cohortes": ["Cohorte 1890"], "domaines": None,
                                                          "statuts": None, "date_debut": None, "date_fin": None}})


def test_aucune_donnee_personnelle(db):
    for nom, args in [("projets_en_retard", {"filtres": None, "limite": 50}), ("projets_a_surveiller", {"limite": 30})]:
        texte = str(analysis.run(db, nom, args))
        assert "leader" not in texte and "@" not in texte and "+221" not in texte


def test_resultats_identiques_au_tableau_de_bord(client, analyste, db):
    k = {x["key"]: x["value"] for x in client.get("/api/analytics/kpis", headers=analyste).json()["all"]}
    r = analysis.run(db, "indicateurs_cles", {"filtres": None})
    assert r["donnees"]["Projets en retard"]["valeur"] == k["delayed"]
    assert r["donnees_simulees"] is True


def test_toutes_les_fonctions_s_executent(db):
    appels = {
        "indicateurs_cles": {"filtres": None},
        "repartition_projets": {"dimension": "performance", "filtres": None},
        "projets_en_retard": {"filtres": None, "limite": 5},
        "comparer_cohortes": {"cohortes": None},
        "comparer": {"dimension": "responsable", "elements": None, "filtres": None},
        "synthese_financements": {"regroupement": "mois", "filtres": None},
        "classement_projets": {"ordre": "meilleurs", "filtres": None, "limite": 5},
        "analyse_risques": {"filtres": None, "limite": 5},
        "projets_a_surveiller": {"limite": 5},
        "alertes_actives": {"niveau": "Critique", "limite": 5},
        "suivi_objectifs": {},
        "evolution_candidatures": {"filtres": None},
    }
    assert set(appels) == analysis.TOOL_NAMES and len(appels) == 12
    for nom, args in appels.items():
        r = analysis.run(db, nom, args)
        assert r["donnees"] is not None and "periode_analysee" in r and "perimetre" in r


# Les 8 questions du prompt V2 (§ 8) et la fonction attendue en mode dégradé
@pytest.mark.parametrize("question, fonction", [
    ("Quels sont les projets les plus performants ?", "classement_projets"),
    ("Quels projets sont en retard ?", "projets_en_retard"),
    ("Quel domaine présente les meilleurs résultats ?", "comparer"),
    ("Quel est le taux d'achèvement cette année ?", "indicateurs_cles"),
    ("Quels projets nécessitent une intervention ?", "analyse_risques"),
    ("Comment évoluent les financements ?", "synthese_financements"),
    ("Quelles sont les principales difficultés ?", "analyse_risques"),
    ("Quelles actions recommandes-tu ?", "analyse_risques"),
    ("Combien de projets avons-nous enregistrés ?", "indicateurs_cles"),
    ("Quelle cohorte présente les meilleurs résultats ?", "comparer_cohortes"),
    ("Où en sont nos objectifs ?", "suivi_objectifs"),
    ("Quelles sont les alertes critiques ?", "alertes_actives"),
])
def test_mode_degrade_questions(client, analyste, question, fonction):
    r = client.post("/api/assistant/ask", headers=analyste, json={"question": question})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "dégradé" and body["tools"][0]["name"] == fonction, body["answer"][:300]
    # Trois niveaux d'analyse + période et indicateurs + mention des données simulées
    for marque in ("**Diagnostic**", "**Explication**", "**Recommandations**", "Période et indicateurs"):
        assert marque in body["answer"]
    assert "données simulées" in body["answer"]


def test_taux_achevement_cette_annee_applique_la_periode(client, analyste):
    from datetime import date
    body = client.post("/api/assistant/ask", headers=analyste,
                       json={"question": "Quel est le taux d'achèvement cette année ?"}).json()
    filtres = body["tools"][0]["arguments"]["filtres"]
    assert filtres["date_debut"] == f"{date.today().year}-01-01"


def test_filtres_actifs_pris_en_compte(client, analyste, db):
    from sqlalchemy import select
    from app.models import Cohort
    c = db.scalars(select(Cohort).order_by(Cohort.year)).first()
    body = client.post("/api/assistant/ask", headers=analyste, json={
        "question": "Combien de projets avons-nous enregistrés ?", "filters": {"cohort_ids": [c.id]}}).json()
    assert body["filters"] and c.name in body["filters"]
    assert body["tools"][0]["arguments"]["filtres"]["cohortes"] == [c.name]
    assert c.name in body["tools"][0]["result"]["perimetre"]


def test_question_hors_perimetre(client, analyste):
    body = client.post("/api/assistant/ask", headers=analyste, json={"question": "Quelle est la météo demain ?"}).json()
    assert body["tools"] == [] and "pas reconnu" in body["answer"]


class _FauxClaude:
    """Simule l'API : 1er tour → demande comparer_cohortes ; 2e tour → réponse rédigée à partir du résultat."""

    def __init__(self):
        self.appels = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kw):
        self.appels.append(kw)
        if len(self.appels) == 1:
            bloc = SimpleNamespace(type="tool_use", id="t1", name="comparer_cohortes", input={"cohortes": None})
            return SimpleNamespace(stop_reason="tool_use", content=[bloc])
        resultat = kw["messages"][-1]["content"][0]["content"]
        assert "Cohorte" in resultat  # le modèle reçoit bien les vrais résultats
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="text", text="**Diagnostic** – … Limites : test.")])


def test_boucle_ia_avec_client_simule(db, monkeypatch):
    faux = _FauxClaude()
    monkeypatch.setattr(svc, "client_factory", lambda: faux)
    res = svc.ask_ai(db, "Quelle cohorte présente les meilleurs résultats ?", [])
    assert res["mode"] == "IA" and res["tools"][0]["name"] == "comparer_cohortes"
    assert res["tools"][0]["error"] is None
    premier = faux.appels[0]
    assert premier["model"] == "claude-opus-5-5" and {t["name"] for t in premier["tools"]} == analysis.TOOL_NAMES
    assert "Cohorte" in premier["system"]  # référentiel transmis


def test_ia_erreur_de_fonction_renvoyee_au_modele(db, monkeypatch):
    class Faux(_FauxClaude):
        def create(self, **kw):
            self.appels.append(kw)
            if len(self.appels) == 1:
                b = SimpleNamespace(type="tool_use", id="t1", name="indicateurs_cles",
                                    input={"filtres": {"cohortes": ["Cohorte 1800"], "domaines": None, "statuts": None,
                                                       "responsables": None, "date_debut": None, "date_fin": None}})
                return SimpleNamespace(stop_reason="tool_use", content=[b])
            retour = kw["messages"][-1]["content"][0]
            assert retour["is_error"] is True and "inconnu" in retour["content"]
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Corrigé.")])

    monkeypatch.setattr(svc, "client_factory", lambda: Faux())
    assert svc.ask_ai(db, "test", [])["answer"] == "Corrigé."


def test_historique(client, analyste):
    h = client.get("/api/assistant/history", headers=analyste).json()
    assert h and all(x["user"] == "analyste" for x in h)


def test_systeme_ia_contient_les_filtres_actifs(db, monkeypatch):
    from app.services import kpi
    from sqlalchemy import select
    from app.models import Domain
    d = db.scalars(select(Domain)).first()
    faux = _FauxClaude()
    monkeypatch.setattr(svc, "client_factory", lambda: faux)
    svc.ask_ai(db, "Quelle cohorte présente les meilleurs résultats ?", [], kpi.Filters(domain_ids=[d.id]))
    systeme = faux.appels[0]["system"]
    assert "FILTRES ACTIFS" in systeme and d.name in systeme
    assert "**Diagnostic**" in systeme and "Hypothèse" in systeme
