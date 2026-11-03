"""Modèle de données PostgreSQL (SQLAlchemy 2).

Conventions :
- chaque table a une clé primaire `id`, `created_at` et `updated_at` ;
- les tables métier ont `is_simulated` (données de démonstration, cahier des charges § 11) ;
- les valeurs autorisées (statuts, montants, dates) sont aussi contrôlées EN BASE par des contraintes CHECK.
Le dictionnaire des données est dans docs/03_base_de_donnees.md.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (ACTIVITY_TYPES, FUNDING_SOURCES, GENDERS, LEADER_PROFILES, PARTNER_TYPES,
                           PROJECT_STATUSES, RECOMMENDATIONS, ApplicationStatus, FundingStatus, Role)
from app.database import Base


def _in(col: str, values) -> str:
    vals = ", ".join("'" + str(v).replace("'", "''") + "'" for v in values)
    return f"{col} IN ({vals})"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now(), nullable=False)


class SimulatedMixin:
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False,
                                               index=True)


# ------------------------------------------------------------------ utilisateurs
class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(_in("role", [r.value for r in Role]), name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ------------------------------------------------------------------ référentiels
class Domain(TimestampMixin, Base):
    __tablename__ = "domains"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Cohort(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "cohorts"
    __table_args__ = (CheckConstraint("end_date > start_date", name="ck_cohorts_dates"),
                      CheckConstraint("year BETWEEN 2000 AND 2100", name="ck_cohorts_year"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class ProjectLeader(TimestampMixin, SimulatedMixin, Base):
    """Porteur de projet – DONNÉES PERSONNELLES (jamais transmises à l'IA)."""
    __tablename__ = "project_leaders"
    __table_args__ = (CheckConstraint(_in("gender", GENDERS) + " OR gender IS NULL", name="ck_leaders_gender"),
                      CheckConstraint(_in("profile", LEADER_PROFILES), name="ck_leaders_profile"))
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))
    email: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    profile: Mapped[str] = mapped_column(String(30), nullable=False)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Partner(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "partners"
    __table_args__ = (CheckConstraint(_in("type", PARTNER_TYPES), name="ck_partners_type"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(120))


# ------------------------------------------------------------------ candidatures et projets
class Application(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        CheckConstraint(_in("status", [s.value for s in ApplicationStatus]), name="ck_applications_status"),
        CheckConstraint("decision_date IS NULL OR decision_date >= submitted_at", name="ck_applications_dates"),
        Index("ix_applications_cohort_domain", "cohort_id", "domain_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    leader_id: Mapped[int] = mapped_column(ForeignKey("project_leaders.id", ondelete="RESTRICT"), nullable=False,
                                           index=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="RESTRICT"), nullable=False)
    project_title: Mapped[str] = mapped_column(String(150), nullable=False)
    submitted_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ApplicationStatus.RECEIVED.value)
    decision_date: Mapped[date | None] = mapped_column(Date)

    leader: Mapped[ProjectLeader] = relationship()
    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="application", cascade="all, delete-orphan",
                                                         order_by="Evaluation.evaluated_at")


class Evaluation(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "evaluations"
    __table_args__ = (CheckConstraint("score BETWEEN 0 AND 20", name="ck_evaluations_score"),
                      CheckConstraint(_in("recommendation", RECOMMENDATIONS), name="ck_evaluations_reco"))
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), nullable=False,
                                                index=True)
    evaluator: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[date] = mapped_column(Date, nullable=False)

    application: Mapped[Application] = relationship(back_populates="evaluations")


class Responsable(TimestampMixin, SimulatedMixin, Base):
    """Responsable de suivi du CIAT (chargé d'accompagnement) : suit plusieurs projets (V2)."""
    __tablename__ = "responsables"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    function: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)


class Project(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(_in("status", PROJECT_STATUSES), name="ck_projects_status"),
        CheckConstraint("progress_pct BETWEEN 0 AND 100", name="ck_projects_progress"),
        CheckConstraint("planned_budget >= 0", name="ck_projects_budget"),
        CheckConstraint("status <> 'Terminé' OR progress_pct = 100", name="ck_projects_completed_100"),
        Index("ix_projects_filters", "cohort_id", "domain_id", "status"),
        Index("ix_projects_active", "is_archived", "status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="RESTRICT"), unique=True,
                                                nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    leader_id: Mapped[int] = mapped_column(ForeignKey("project_leaders.id", ondelete="RESTRICT"), nullable=False,
                                           index=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="RESTRICT"), nullable=False)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id", ondelete="RESTRICT"), nullable=False)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("responsables.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(25), nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    planned_budget: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", nullable=False)
    deadline: Mapped[date | None] = mapped_column(Date)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    application: Mapped[Application] = relationship()
    leader: Mapped[ProjectLeader] = relationship()
    domain: Mapped[Domain] = relationship()
    cohort: Mapped[Cohort] = relationship()
    responsible: Mapped[Responsable | None] = relationship()
    milestones: Mapped[list[Milestone]] = relationship(back_populates="project", cascade="all, delete-orphan",
                                                       order_by="Milestone.position")
    fundings: Mapped[list[Funding]] = relationship(back_populates="project", cascade="all, delete-orphan",
                                                   order_by="Funding.request_date")
    history: Mapped[list[ProjectStatusHistory]] = relationship(back_populates="project", cascade="all, delete-orphan",
                                                               order_by="ProjectStatusHistory.changed_at")


class ProjectStatusHistory(Base):
    __tablename__ = "project_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    old_status: Mapped[str | None] = mapped_column(String(25))
    new_status: Mapped[str] = mapped_column(String(25), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project: Mapped[Project] = relationship(back_populates="history")
    user: Mapped[User | None] = relationship()


class Milestone(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "milestones"
    __table_args__ = (Index("ix_milestones_open", "project_id", "completed_date", "due_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    completed_date: Mapped[date | None] = mapped_column(Date)

    project: Mapped[Project] = relationship(back_populates="milestones")


class Funding(TimestampMixin, SimulatedMixin, Base):
    __tablename__ = "fundings"
    __table_args__ = (
        CheckConstraint(_in("status", [s.value for s in FundingStatus]), name="ck_fundings_status"),
        CheckConstraint(_in("source_type", FUNDING_SOURCES), name="ck_fundings_source"),
        CheckConstraint("amount_requested >= 0 AND amount_granted >= 0 AND amount_received >= 0",
                        name="ck_fundings_positive"),
        CheckConstraint("amount_received <= amount_granted AND amount_granted <= amount_requested",
                        name="ck_fundings_order"),
        CheckConstraint("grant_date IS NULL OR grant_date >= request_date", name="ck_fundings_dates"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    partner_id: Mapped[int | None] = mapped_column(ForeignKey("partners.id", ondelete="SET NULL"), index=True)
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_requested: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount_granted: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    amount_received: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    grant_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(25), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="fundings")
    partner: Mapped[Partner | None] = relationship()


class Activity(TimestampMixin, SimulatedMixin, Base):
    """Activités du CIAT : formations, ateliers, événements, mentorat."""
    __tablename__ = "activities"
    __table_args__ = (CheckConstraint(_in("type", ACTIVITY_TYPES), name="ck_activities_type"),
                      CheckConstraint("participants_count >= 0", name="ck_activities_participants"))
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    cohort_id: Mapped[int | None] = mapped_column(ForeignKey("cohorts.id", ondelete="SET NULL"))
    participants_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text)


# ------------------------------------------------------------------ technique
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    username: Mapped[str | None] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False,
                                                 index=True)


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    tools_used: Mapped[list | None] = mapped_column(JSON)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # "IA" ou "dégradé"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False,
                                                 index=True)

    user: Mapped[User] = relationship()


class AppSetting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now(), nullable=False)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity: Mapped[str] = mapped_column(String(30), nullable=False)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    rows_imported: Mapped[int] = mapped_column(Integer, nullable=False)
    rows_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ------------------------------------------------------------------ V2 : alertes et objectifs
ALERT_LEVELS = ["Critique", "Élevé", "Moyen", "Information"]


class Alert(Base):
    """Alerte détectée par les règles du centre d'alertes. Une alerte est « ouverte » tant que resolved_at est vide ;
    lorsque la condition disparaît, elle est résolue et passe dans l'historique."""
    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint(_in("level", ALERT_LEVELS), name="ck_alerts_level"),
        Index("ix_alerts_open", "key", "resolved_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(80), nullable=False)  # ex. « retard:42 » (déduplication)
    type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    objective_id: Mapped[int | None] = mapped_column(ForeignKey("objectives.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    project: Mapped[Project | None] = relationship()


class AlertRead(Base):
    """Marquage « lu » d'une alerte, propre à chaque utilisateur."""
    __tablename__ = "alert_reads"
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


OBJECTIVE_INDICATORS = ["projets_accompagnes", "projets_termines", "financements_mobilises", "prototypes",
                        "taux_achevement"]


class Objective(TimestampMixin, SimulatedMixin, Base):
    """Objectif fixé par les responsables (V2) sur une période, éventuellement limité à une cohorte ou un domaine."""
    __tablename__ = "objectives"
    __table_args__ = (
        CheckConstraint(_in("indicator", OBJECTIVE_INDICATORS), name="ck_objectives_indicator"),
        CheckConstraint("target_value > 0", name="ck_objectives_target"),
        CheckConstraint("end_date > start_date", name="ck_objectives_dates"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    indicator: Mapped[str] = mapped_column(String(40), nullable=False)
    target_value: Mapped[float] = mapped_column(Numeric(16, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    cohort_id: Mapped[int | None] = mapped_column(ForeignKey("cohorts.id", ondelete="SET NULL"))
    domain_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id", ondelete="SET NULL"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    cohort: Mapped[Cohort | None] = relationship()
    domain: Mapped[Domain | None] = relationship()
