"""Tests : cohérence du jeu de données SIMULÉES (anomalie A6 du journal des tests)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.models import Application, Evaluation, Funding, Milestone, Project


def test_toutes_les_donnees_metier_sont_marquees_simulees(db):
    assert db.scalar(select(Project.id).where(Project.is_simulated.is_(True)).limit(1))
    domaines_attendus = {"Technologies de l'information et du numérique", "Intelligence artificielle", "Agriculture",
                         "Énergie", "Mécanique", "Environnement", "Éducation", "Santé et biomédical"}
    from app.models import Domain
    assert domaines_attendus <= set(db.scalars(select(Domain.name)))


def test_evaluations_avant_la_decision(db):
    for e, a in db.execute(select(Evaluation, Application).join(Application)):
        assert e.evaluated_at >= a.submitted_at
        if a.decision_date:
            assert e.evaluated_at <= a.decision_date


def test_historique_chronologique_et_coherent(db):
    ordre = ["En attente", "En évaluation", "Sélectionné", "En incubation", "En développement", "Prototype réalisé",
             "Terminé"]
    for p in db.scalars(select(Project).where(Project.is_simulated.is_(True))):
        etats = [h.new_status for h in sorted(p.history, key=lambda h: h.changed_at)]
        assert etats[-1] == p.status
        rangs = [ordre.index(s) for s in etats if s in ordre]
        assert rangs == sorted(rangs), (p.id, etats)


def test_regles_metier_respectees(db):
    today = date.today()
    for p in db.scalars(select(Project).where(Project.is_simulated.is_(True))):
        if p.status == "Terminé":
            assert p.progress_pct == 100 and all(m.completed_date for m in p.milestones)
        assert p.application.status == {"Non retenu": "Rejetée", "En attente": "Reçue",
                                        "En évaluation": "En évaluation"}.get(p.status, "Acceptée")
    assert all(m.completed_date <= today for m in db.scalars(select(Milestone).where(Milestone.completed_date.isnot(None))))
    for f in db.scalars(select(Funding)):
        assert 0 <= f.amount_received <= f.amount_granted <= f.amount_requested
        assert f.request_date <= today
