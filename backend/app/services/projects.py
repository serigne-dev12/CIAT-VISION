"""Règles métier des projets, candidatures, jalons et financements (cahier des charges § 5)."""
from __future__ import annotations

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_MILESTONES, TRANSITIONS, ApplicationStatus, FundingStatus, ProjectStatus
from app.models import (Application, Cohort, Domain, Funding, Milestone, Partner, Project, ProjectLeader,
                        ProjectStatusHistory, User)


def http_error(message: str, code: int = 422) -> HTTPException:
    return HTTPException(code, message)


def get_project(db: Session, project_id: int, include_archived: bool = False) -> Project:
    p = db.get(Project, project_id)
    if p is None or (p.is_archived and not include_archived):
        raise http_error("Projet introuvable.", status.HTTP_404_NOT_FOUND)
    return p


def check_references(db: Session, domain_id: int, cohort_id: int) -> Cohort:
    if db.get(Domain, domain_id) is None:
        raise http_error("Domaine inconnu.")
    cohort = db.get(Cohort, cohort_id)
    if cohort is None:
        raise http_error("Cohorte inconnue.")
    return cohort


def check_duplicate_name(db: Session, name: str, cohort_id: int, exclude_id: int | None = None) -> None:
    q = select(Project.id).where(func.lower(Project.name) == func.lower(name.strip()), Project.cohort_id == cohort_id,
                                 Project.is_archived.is_(False))
    if exclude_id:
        q = q.where(Project.id != exclude_id)
    if db.scalar(q):
        raise http_error("Un projet portant ce nom existe déjà dans cette cohorte.", status.HTTP_409_CONFLICT)


def create_project(db: Session, data, user: User) -> Project:
    """Crée le porteur (si nouveau), la candidature (« Reçue ») et le projet (« En attente »)."""
    check_references(db, data.domain_id, data.cohort_id)
    check_duplicate_name(db, data.name, data.cohort_id)
    submitted = data.submitted_at or date.today()
    if data.deadline and data.deadline <= submitted:
        raise http_error("La date limite doit être postérieure à la date de dépôt.")

    if data.leader_id:
        leader = db.get(ProjectLeader, data.leader_id)
        if leader is None:
            raise http_error("Porteur de projet inconnu.")
    elif data.leader:
        leader = ProjectLeader(**data.leader.model_dump())
        db.add(leader)
        db.flush()
    else:
        raise http_error("Indiquez un porteur existant ou les informations d'un nouveau porteur.")

    app_ = Application(leader_id=leader.id, cohort_id=data.cohort_id, domain_id=data.domain_id,
                       project_title=data.name.strip(), submitted_at=submitted, status=ApplicationStatus.RECEIVED)
    db.add(app_)
    db.flush()
    p = Project(application_id=app_.id, name=data.name.strip(), description=data.description, leader_id=leader.id,
                domain_id=data.domain_id, cohort_id=data.cohort_id, status=ProjectStatus.PENDING, progress_pct=0,
                planned_budget=data.planned_budget, deadline=data.deadline)
    db.add(p)
    db.flush()
    db.add(ProjectStatusHistory(project_id=p.id, old_status=None, new_status=p.status, changed_by=user.id,
                                comment="Création du projet"))
    return p


def create_default_milestones(db: Session, p: Project, start: date | None = None) -> None:
    """Crée les 5 jalons standard, répartis régulièrement entre le début et la fin de la cohorte."""
    if p.milestones:
        return
    debut = start or max(p.cohort.start_date, date.today())
    fin = p.deadline or p.cohort.end_date
    if fin <= debut:
        fin = p.cohort.end_date if p.cohort.end_date > debut else debut.replace(year=debut.year + 1)
    pas = (fin - debut) / len(DEFAULT_MILESTONES)
    for i, titre in enumerate(DEFAULT_MILESTONES, start=1):
        p.milestones.append(Milestone(title=titre, position=i, due_date=debut + pas * i,
                                      is_simulated=p.is_simulated))


def change_status(db: Session, p: Project, new: str, user: User, comment: str | None = None) -> None:
    """Applique une transition en vérifiant les règles du § 5.2 et synchronise la candidature."""
    try:
        cible, actuel = ProjectStatus(new), ProjectStatus(p.status)
    except ValueError:
        raise http_error("Statut inconnu.") from None
    if cible == actuel:
        return
    if cible not in TRANSITIONS[actuel]:
        autorises = ", ".join(s.value for s in TRANSITIONS[actuel]) or "aucune (statut final)"
        raise http_error(f"Transition interdite : « {actuel.value} » → « {cible.value} ». "
                         f"Transitions possibles : {autorises}.")

    app_ = p.application
    if cible in (ProjectStatus.SELECTED, ProjectStatus.NOT_RETAINED) and not app_.evaluations:
        raise http_error("Au moins une évaluation de la candidature doit être enregistrée avant la décision.")

    if cible == ProjectStatus.EVALUATION:
        app_.status = ApplicationStatus.EVALUATION
    elif cible == ProjectStatus.SELECTED:
        app_.status, app_.decision_date = ApplicationStatus.ACCEPTED, date.today()
    elif cible == ProjectStatus.NOT_RETAINED:
        app_.status, app_.decision_date = ApplicationStatus.REJECTED, date.today()
    elif cible == ProjectStatus.INCUBATION:
        create_default_milestones(db, p)
    elif cible == ProjectStatus.COMPLETED:
        p.progress_pct = 100  # « Terminé » impose une progression de 100 %

    db.add(ProjectStatusHistory(project_id=p.id, old_status=actuel.value, new_status=cible.value, changed_by=user.id,
                                comment=comment))
    p.status = cible.value


def update_progress(p: Project, value: int, comment: str | None) -> None:
    if not 0 <= value <= 100:
        raise http_error("La progression doit être comprise entre 0 et 100 %.")
    if p.status == ProjectStatus.COMPLETED and value != 100:
        raise http_error("Un projet terminé a une progression de 100 %.")
    if value < p.progress_pct and not (comment and comment.strip()):
        raise http_error("Une baisse de la progression doit être justifiée par un commentaire.")
    p.progress_pct = value


def archive(p: Project) -> None:
    p.is_archived, p.archived_at = True, datetime.now(UTC)


def restore(db: Session, p: Project) -> None:
    check_duplicate_name(db, p.name, p.cohort_id, exclude_id=p.id)
    p.is_archived, p.archived_at = False, None


# ------------------------------------------------------------------ financements
def validate_funding(db: Session, data) -> None:
    """Contrôles du § 5.4 (également garantis par des contraintes CHECK en base)."""
    if not (data.amount_received <= data.amount_granted <= data.amount_requested):
        raise http_error("Les montants doivent respecter : reçu ≤ accordé ≤ demandé.")
    if data.grant_date and data.grant_date < data.request_date:
        raise http_error("La date d'accord ne peut pas précéder la date de demande.")
    if data.request_date > date.today():
        raise http_error("La date de demande ne peut pas être dans le futur.")
    s = FundingStatus(data.status)
    coherent = {
        FundingStatus.REQUESTED: data.amount_granted == 0,
        FundingStatus.REFUSED: data.amount_granted == 0,
        FundingStatus.GRANTED: data.amount_granted > 0 and data.amount_received == 0,
        FundingStatus.PARTIAL: 0 < data.amount_received < data.amount_granted,
        FundingStatus.RECEIVED: data.amount_granted > 0 and data.amount_received == data.amount_granted,
    }[s]
    if not coherent:
        raise http_error(f"Le statut « {s.value} » ne correspond pas aux montants saisis.")
    if data.partner_id is not None and db.get(Partner, data.partner_id) is None:
        raise http_error("Partenaire inconnu.")
