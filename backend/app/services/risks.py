"""Module 6 (V2) – Analyse des risques fondée sur des RÈGLES TRANSPARENTES.

Ce n'est PAS une prédiction scientifique : chaque point de risque correspond à un constat vérifiable dans les données
(échéance dépassée, retard de progression, jalons manqués, absence de mise à jour, financement insuffisant,
suspension). Le score et ses raisons sont toujours affichés ensemble.

Architecture : un « modèle de risque » est un objet qui implémente `evaluer(db, filtres)`. Le modèle actif est choisi
par le paramètre `risk_model` (par défaut « regles »). Un modèle prédictif entraîné sur des données historiques
pourra être ajouté au registre `MODELES` sans modifier les écrans ni l'API, à condition de renvoyer la même structure
(score, niveau, facteurs explicatifs).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ACTIVE_STATUSES, ProjectStatus
from app.models import Application, Funding, Milestone, Project
from app.services import kpi
from app.services.common import get_int_setting, get_setting

NIVEAUX = ["Élevé", "Modéré", "Faible"]
SEUIL_ELEVE, SEUIL_MODERE = 50, 25
JOURS_SANS_MISE_A_JOUR = 60
STATUTS_EVALUES = [*ACTIVE_STATUSES, ProjectStatus.SUSPENDED]

AVERTISSEMENT = ("Analyse fondée sur des règles explicites appliquées aux données enregistrées. Ce n'est pas une "
                 "prédiction scientifique : le score signale des projets à examiner, il ne décide de rien.")


@dataclass
class Facteur:
    code: str
    libelle: str
    points: int
    detail: str


@dataclass
class Evaluation:
    project_id: int
    name: str
    domain: str
    cohort: str
    responsible: str | None
    status: str
    progress_pct: int
    expected_pct: float | None
    score: int
    level: str
    factors: list[Facteur] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class ModeleRisque(Protocol):
    code: str
    nom: str
    description: str

    def evaluer(self, db: Session, f: kpi.Filters, today: date | None = None) -> list[Evaluation]: ...


def niveau(score: int) -> str:
    return "Élevé" if score >= SEUIL_ELEVE else ("Modéré" if score >= SEUIL_MODERE else "Faible")


def progression_attendue(p: Project, today: date) -> float | None:
    """Même définition que kpi.expected_progress_expr (part du délai écoulé), calculée en Python."""
    debut = p.cohort.start_date
    fin = p.deadline or p.cohort.end_date
    duree = (fin - debut).days
    if duree <= 0:
        return None
    return max(0.0, min(1.0, (today - debut).days / duree))


class ModeleRegles:
    code = "regles"
    nom = "Règles transparentes (version 1)"
    description = (
        f"Échéance dépassée : +40 ; progression inférieure de plus de 30 points à l'attendu : +30 (10 à 30 points : "
        f"+15) ; jalon en retard : +10 chacun (max. +20) ; aucune mise à jour depuis {JOURS_SANS_MISE_A_JOUR} jours : "
        f"+10 ; financement accordé < 50 % du budget : +15 (< 100 % : +5) ; projet suspendu : +30. Score plafonné à "
        f"100. Niveau : Élevé ≥ {SEUIL_ELEVE}, Modéré ≥ {SEUIL_MODERE}, Faible en dessous.")

    def evaluer(self, db: Session, f: kpi.Filters, today: date | None = None) -> list[Evaluation]:
        today = today or date.today()
        tolerance = get_int_setting(db, "delay_tolerance_days")
        projets = db.scalars(
            select(Project).join(Application, Application.id == Project.application_id)
            .where(*f.conditions(), Project.status.in_(STATUTS_EVALUES))).all()
        ids = [p.id for p in projets]
        if not ids:
            return []
        accorde = dict(db.execute(select(Funding.project_id, func.sum(Funding.amount_granted))
                                  .where(Funding.project_id.in_(ids)).group_by(Funding.project_id)).all())
        jalons: dict[int, list[Milestone]] = {}
        for m in db.scalars(select(Milestone).where(Milestone.project_id.in_(ids), Milestone.completed_date.is_(None))):
            if (today - m.due_date).days > tolerance:
                jalons.setdefault(m.project_id, []).append(m)

        resultats = []
        for p in projets:
            fx: list[Facteur] = []
            if p.status == ProjectStatus.SUSPENDED:
                fx.append(Facteur("suspendu", "Projet suspendu", 30, "L'accompagnement est interrompu."))
            if p.deadline and p.deadline < today and p.status != ProjectStatus.SUSPENDED:
                fx.append(Facteur("echeance", "Échéance dépassée", 40,
                                  f"Date limite du {p.deadline:%d/%m/%Y} dépassée de {(today - p.deadline).days} jours."))
            attendu = progression_attendue(p, today)
            if attendu is not None and p.status in ACTIVE_STATUSES:
                ecart = p.progress_pct - attendu * 100
                if ecart < -30:
                    fx.append(Facteur("progression", "Progression très insuffisante", 30,
                                      f"{p.progress_pct} % réalisés pour {attendu:.0%} du délai écoulé."))
                elif ecart < -10:
                    fx.append(Facteur("progression", "Progression en retard", 15,
                                      f"{p.progress_pct} % réalisés pour {attendu:.0%} du délai écoulé."))
            if jalons.get(p.id):
                n = len(jalons[p.id])
                fx.append(Facteur("jalons", "Jalons en retard", min(20, 10 * n),
                                  f"{n} jalon(s) non atteint(s) après la date prévue (premier : "
                                  f"« {jalons[p.id][0].title} »)."))
            if p.updated_at and (today - p.updated_at.date()).days >= JOURS_SANS_MISE_A_JOUR:
                fx.append(Facteur("mise_a_jour", "Aucune mise à jour récente", 10,
                                  f"Dernière mise à jour le {p.updated_at:%d/%m/%Y} "
                                  f"({(today - p.updated_at.date()).days} jours)."))
            if p.planned_budget > 0:
                a = int(accorde.get(p.id) or 0)
                taux = a / p.planned_budget
                if taux < 0.5:
                    fx.append(Facteur("financement", "Financement insuffisant", 15,
                                      f"{a:,} FCFA accordés pour un budget de {p.planned_budget:,} FCFA "
                                      f"({taux:.0%}).".replace(",", " ")))
                elif taux < 1:
                    fx.append(Facteur("financement", "Financement partiel", 5,
                                      f"{taux:.0%} du budget prévisionnel couvert."))
            score = min(100, sum(x.points for x in fx))
            resultats.append(Evaluation(
                project_id=p.id, name=p.name, domain=p.domain.name, cohort=p.cohort.name,
                responsible=p.responsible.full_name if p.responsible else None, status=p.status,
                progress_pct=p.progress_pct, expected_pct=round(attendu * 100, 1) if attendu is not None else None,
                score=score, level=niveau(score), factors=fx))
        resultats.sort(key=lambda e: e.score, reverse=True)
        return resultats


MODELES: dict[str, ModeleRisque] = {ModeleRegles.code: ModeleRegles()}


def modele_actif(db: Session) -> ModeleRisque:
    return MODELES.get(get_setting(db, "risk_model"), MODELES["regles"])


def analyser(db: Session, f: kpi.Filters, today: date | None = None) -> dict:
    modele = modele_actif(db)
    evaluations = modele.evaluer(db, f, today)
    frequence: dict[str, int] = {}
    for e in evaluations:
        for x in e.factors:
            frequence[x.libelle] = frequence.get(x.libelle, 0) + 1
    return {
        "modele": {"code": modele.code, "nom": modele.nom, "methode": modele.description},
        "avertissement": AVERTISSEMENT,
        "total": len(evaluations),
        "par_niveau": {n: sum(1 for e in evaluations if e.level == n) for n in NIVEAUX},
        "facteurs_frequents": sorted(({"facteur": k, "projets": v} for k, v in frequence.items()),
                                     key=lambda x: x["projets"], reverse=True),
        "projets": [e.to_dict() for e in evaluations],
    }
