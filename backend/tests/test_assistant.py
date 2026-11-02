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
        "repartition_projets": {"dimension": "domaine", "filtres": None},
        "projets_en_retard": {"filtres": None, "limite": 5},
        "comparer_cohortes": {"cohortes": None},
        "synthese_financements": {"regroupement": "source", "filtres": None},
        "projets_a_surveiller": {"limite": 5},
        "evolution_candidatures": {"filtres": None},
    }
    assert set(appels) == analysis.TOOL_NAMES
    for nom, args in appels.items():
        assert analysis.run(db, nom, args)["donnees"] is not None


@pytest.mark.parametrize("question, fonction", [
    ("Combien de projets avons-nous enregistrés ?", "indicateurs_cles"),
    ("Quel domaine possède le plus de projets ?", "repartition_projets"),
    ("Combien de projets sont actuellement en retard ?", "projets_en_retard"),
    ("Quelle cohorte présente les meilleurs résultats ?", "comparer_cohortes"),
    ("Quel est le montant total des financements ?", "synthese_financements"),
    ("Quel est le taux de réussite des projets ?", "indicateurs_cles"),
    ("Quels projets nécessitent une attention particulière ?", "projets_a_surveiller"),
    ("Quelles recommandations peut-on proposer pour améliorer les performances ?", "projets_a_surveiller"),
])
def test_mode_degrade_questions_du_cahier_des_charges(client, analyste, question, fonction):
    r = client.post("/api/assistant/ask", headers=analyste, json={"question": question})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "dégradé" and body["tools"][0]["name"] == fonction
    assert "données simulées" in body["answer"] and "Limites" in body["answer"]


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
                               content=[SimpleNamespace(type="text", text="La meilleure cohorte est… Limites : test.")])


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
                                                       "date_debut": None, "date_fin": None}})
                return SimpleNamespace(stop_reason="tool_use", content=[b])
            retour = kw["messages"][-1]["content"][0]
            assert retour["is_error"] is True and "inconnu" in retour["content"]
            return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Corrigé.")])

    monkeypatch.setattr(svc, "client_factory", lambda: Faux())
    assert svc.ask_ai(db, "test", [])["answer"] == "Corrigé."


def test_historique(client, analyste):
    h = client.get("/api/assistant/history", headers=analyste).json()
    assert h and all(x["user"] == "analyste" for x in h)
