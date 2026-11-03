"""Module 4 (V2) – Centre d'alertes intelligentes.

Chaque règle ne se déclenche que si les données nécessaires EXISTENT (une échéance n'est évaluée que si une date
limite est renseignée, etc.) : aucune alerte n'est fabriquée à partir de données absentes. L'absence d'une donnée
utile fait elle-même l'objet d'une alerte « Données manquantes » de niveau Information.

Cycle de vie : une alerte est OUVERTE tant que sa condition est vraie. À chaque génération, les alertes dont la
condition a disparu sont RÉSOLUES et passent dans l'historique. Une clé (type + objet) évite les doublons.
"""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import ACTIVE_STATUSES, ProjectStatus
from app.models import Alert, AppSetting, Funding, Milestone, Project
from app.services import kpi, objectives, risks
from app.services.common import get_setting

TYPES = {
    "retard": "Projet en retard",
    "echeance": "Échéance proche",
    "progression": "Progression insuffisante",
    "financement": "Financement insuffisant",
    "objectif": "Objectif non atteint",
    "donnees": "Données manquantes",
    "risque": "Risque de non-achèvement",
}
NIVEAUX = ["Critique", "Élevé", "Moyen", "Information"]
DELAI_REGENERATION = timedelta(minutes=10)
INCUBES_ACTIFS = [ProjectStatus.INCUBATION, ProjectStatus.DEVELOPMENT, ProjectStatus.PROTOTYPE]


def _det(key, type_, level, titre, probleme, explication, action, project_id=None, objective_id=None) -> dict:
    return {"key": key, "type": TYPES[type_], "level": level, "title": titre, "problem": probleme,
            "explanation": explication, "recommended_action": action, "project_id": project_id,
            "objective_id": objective_id}


def detecter(db: Session, today: date | None = None) -> list[dict]:
    """Applique les 7 règles sur les données actuelles et renvoie les alertes à afficher."""
    today = today or date.today()
    out: list[dict] = []
    tous = kpi.Filters()

    # 1. Projets en retard (définition officielle du KPI « Projets en retard »)
    retards = {r["id"]: r for r in kpi.delayed_projects(db, tous, today=today)}
    for r in retards.values():
        niveau = "Critique" if r["days_late"] > 90 else "Élevé"
        cause = (f"jalon « {r['first_late_milestone']} » non atteint" if r["first_late_milestone"]
                 else "date limite dépassée")
        out.append(_det(f"retard:{r['id']}", "retard", niveau, f"{r['name']} : retard de {r['days_late']} jours",
                        f"Le projet accuse {r['days_late']} jours de retard ({cause}).",
                        f"{r['late_milestones']} jalon(s) en retard ; date limite "
                        f"{'dépassée' if r['deadline_passed'] else 'non dépassée'} ; progression {r['progress_pct']} %.",
                        "Programmer un point de suivi avec le porteur, identifier les blocages et réviser le calendrier "
                        "des jalons.", project_id=r["id"]))

    projets = db.scalars(select(Project).where(Project.is_archived.is_(False),
                                               Project.status.in_([*ACTIVE_STATUSES, ProjectStatus.SUSPENDED]))).all()
    accorde = dict(db.execute(select(Funding.project_id, func.sum(Funding.amount_granted))
                              .group_by(Funding.project_id)).all())
    avec_jalons = set(db.scalars(select(Milestone.project_id).distinct()))

    for p in projets:
        actif = p.status in ACTIVE_STATUSES
        # 2. Échéance proche (uniquement si une date limite est renseignée)
        if actif and p.deadline and today <= p.deadline <= today + timedelta(days=30) and p.progress_pct < 90 \
                and p.id not in retards:
            jours = (p.deadline - today).days
            niveau = "Élevé" if jours <= 7 and p.progress_pct < 70 else "Moyen"
            out.append(_det(f"echeance:{p.id}", "echeance", niveau, f"{p.name} : échéance dans {jours} jour(s)",
                            f"Date limite le {p.deadline:%d/%m/%Y} avec une progression de {p.progress_pct} %.",
                            "Il reste moins de 30 jours et plus de 10 % du travail à réaliser.",
                            "Vérifier avec le porteur que le reste à faire est réalisable avant l'échéance ; à défaut, "
                            "décider d'un report formalisé.", project_id=p.id))
        # 3. Progression insuffisante par rapport au temps écoulé
        attendu = risks.progression_attendue(p, today)
        if actif and attendu is not None and p.progress_pct - attendu * 100 < -30:
            out.append(_det(f"progression:{p.id}", "progression", "Élevé", f"{p.name} : progression insuffisante",
                            f"Progression de {p.progress_pct} % alors que {attendu:.0%} du délai est écoulé.",
                            "Écart de plus de 30 points entre la progression réelle et la progression attendue "
                            "(niveau de performance « Faible »).",
                            "Analyser les causes avec le responsable de suivi et renforcer l'accompagnement "
                            "(mentorat, appui technique).", project_id=p.id))
        # 4. Financement insuffisant (uniquement si un budget est renseigné)
        if p.status in INCUBES_ACTIFS and p.planned_budget > 0:
            a = int(accorde.get(p.id) or 0)
            if a < p.planned_budget * 0.5:
                out.append(_det(f"financement:{p.id}", "financement", "Moyen", f"{p.name} : financement insuffisant",
                                f"{a:,} FCFA accordés pour un budget prévisionnel de {p.planned_budget:,} FCFA "
                                f"({a / p.planned_budget:.0%}).".replace(",", " "),
                                "Moins de la moitié du budget prévisionnel est couverte par des financements accordés.",
                                "Orienter le projet vers les partenaires financiers et les appels à projets en cours.",
                                project_id=p.id))
        # 6. Données manquantes utiles au suivi
        manques = []
        if not p.deadline:
            manques.append("date limite")
        if p.planned_budget <= 0:
            manques.append("budget prévisionnel")
        if p.status in INCUBES_ACTIFS and p.id not in avec_jalons:
            manques.append("jalons")
        if p.responsible_id is None:
            manques.append("responsable de suivi")
        if manques:
            out.append(_det(f"donnees:{p.id}", "donnees", "Information", f"{p.name} : données manquantes",
                            "Information(s) non renseignée(s) : " + ", ".join(manques) + ".",
                            "Sans ces données, certains indicateurs et contrôles (retards, échéances, financement) "
                            "ne peuvent pas être calculés pour ce projet.",
                            "Compléter la fiche du projet.", project_id=p.id))

    # 7. Risque de non-achèvement (score de risque élevé, règles transparentes)
    for e in risks.analyser(db, tous, today)["projets"]:
        if e["level"] == "Élevé":
            raisons = " ; ".join(f["libelle"] + f" (+{f['points']})" for f in e["factors"])
            out.append(_det(f"risque:{e['project_id']}", "risque", "Critique",
                            f"{e['name']} : risque élevé de non-achèvement (score {e['score']}/100)",
                            f"Score de risque {e['score']}/100.", "Facteurs : " + raisons + ". " + risks.AVERTISSEMENT,
                            "Décider en comité d'un plan de redressement (objectifs revus, appui renforcé) ou d'une "
                            "suspension.", project_id=e["project_id"]))

    # 5. Objectifs non atteints ou en retard sur le rythme prévu
    for o in objectives.lister(db, today):
        if o["status"] in ("Non atteint", "En retard", "En dessous de la cible"):
            niveau = "Élevé" if o["status"] == "Non atteint" else "Moyen"
            realisation = f"{o['realization_rate']:.0%}" if o["realization_rate"] is not None else "—"
            out.append(_det(f"objectif:{o['id']}", "objectif", niveau,
                            f"Objectif « {o['label']} » : {o['status'].lower()}",
                            f"Réalisé : {o['current']:,.0f} pour une cible de {o['target']:,.0f} ({realisation})."
                            .replace(",", " "),
                            f"{o['definition']} {o['elapsed_rate']:.0%} de la période est écoulée.",
                            "Réexaminer les moyens alloués à cet objectif ou en ajuster la cible en comité.",
                            objective_id=o["id"]))
    return out


def generer(db: Session, today: date | None = None) -> dict:
    """Synchronise les alertes ouvertes avec les détections (création, mise à jour, résolution)."""
    maintenant = datetime.now(UTC)
    detections = {d["key"]: d for d in detecter(db, today)}
    ouvertes = {a.key: a for a in db.scalars(select(Alert).where(Alert.resolved_at.is_(None)))}
    crees = majs = resolues = 0
    for cle, d in detections.items():
        a = ouvertes.get(cle)
        if a is None:
            db.add(Alert(**d, detected_at=maintenant, last_seen_at=maintenant))
            crees += 1
        else:
            for champ in ("type", "level", "title", "problem", "explanation", "recommended_action"):
                setattr(a, champ, d[champ])
            a.last_seen_at = maintenant
            majs += 1
    for cle, a in ouvertes.items():
        if cle not in detections:
            a.resolved_at = maintenant
            resolues += 1
    reglage = db.get(AppSetting, "alerts_generated_at")
    if reglage:
        reglage.value = maintenant.isoformat()
    else:
        db.add(AppSetting(key="alerts_generated_at", value=maintenant.isoformat()))
    db.flush()
    return {"creees": crees, "mises_a_jour": majs, "resolues": resolues, "ouvertes": len(detections)}


def generer_si_necessaire(db: Session) -> bool:
    """Régénère au plus toutes les 10 minutes (appelée à la consultation des alertes)."""
    derniere = get_setting(db, "alerts_generated_at")
    try:
        if derniere and datetime.now(UTC) - datetime.fromisoformat(derniere) < DELAI_REGENERATION:
            return False
    except ValueError:
        pass
    generer(db)
    return True
