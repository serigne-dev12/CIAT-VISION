"""Schémas Pydantic : validation de toutes les données reçues et forme des réponses de l'API."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.constants import (ACTIVITY_TYPES, FUNDING_SOURCES, GENDERS, LEADER_PROFILES, PARTNER_TYPES,
                           PROJECT_STATUSES, RECOMMENDATIONS, FundingStatus, Role)

Text100 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Text150 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[+\d][\d\s.-]{6,24}$")]
Username = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[a-zA-Z0-9_.-]{3,30}$")]
Amount = Annotated[int, Field(ge=0, le=100_000_000_000)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ authentification et utilisateurs
class LoginIn(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=72)]


class UserOut(ORM):
    id: int
    username: str
    full_name: str
    email: str | None
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class UserCreate(BaseModel):
    username: Username
    full_name: Text100
    email: EmailStr | None = None
    role: Role
    password: Annotated[str, StringConstraints(min_length=8, max_length=72)]


class UserUpdate(BaseModel):
    full_name: Text100 | None = None
    email: EmailStr | None = None
    role: Role | None = None
    is_active: bool | None = None
    new_password: Annotated[str, StringConstraints(min_length=8, max_length=72)] | None = None


class ProfileUpdate(BaseModel):
    full_name: Text100
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    current_password: Annotated[str, StringConstraints(min_length=1, max_length=72)]
    new_password: Annotated[str, StringConstraints(min_length=8, max_length=72)]


# ------------------------------------------------------------------ référentiels
class DomainOut(ORM):
    id: int
    name: str
    description: str | None = None


class CohortIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]
    year: Annotated[int, Field(ge=2000, le=2100)]
    start_date: date
    end_date: date
    description: LongText | None = None

    @field_validator("end_date")
    @classmethod
    def _dates(cls, v: date, info):
        if info.data.get("start_date") and v <= info.data["start_date"]:
            raise ValueError("La date de fin doit être postérieure à la date de début.")
        return v


class CohortOut(ORM):
    id: int
    name: str
    year: int
    start_date: date
    end_date: date
    description: str | None
    is_simulated: bool


class LeaderIn(BaseModel):
    first_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    last_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    gender: Literal[tuple(GENDERS)] | None = None  # type: ignore[valid-type]
    email: EmailStr | None = None
    phone: Phone | None = None
    profile: Literal[tuple(LEADER_PROFILES)]  # type: ignore[valid-type]


class LeaderOut(ORM):
    id: int
    first_name: str
    last_name: str
    gender: str | None
    profile: str
    email: str | None = None   # masqué pour le rôle Analyste
    phone: str | None = None   # masqué pour le rôle Analyste


class PartnerIn(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    type: Literal[tuple(PARTNER_TYPES)]  # type: ignore[valid-type]
    contact_email: EmailStr | None = None


class PartnerOut(ORM):
    id: int
    name: str
    type: str


# ------------------------------------------------------------------ projets
class ProjectCreate(BaseModel):
    name: Text150
    description: LongText | None = None
    domain_id: int
    cohort_id: int
    leader_id: int | None = None
    leader: LeaderIn | None = None
    planned_budget: Amount = 0
    deadline: date | None = None
    submitted_at: date | None = None

    @field_validator("submitted_at")
    @classmethod
    def _not_future(cls, v: date | None):
        if v and v > date.today():
            raise ValueError("La date de dépôt ne peut pas être dans le futur.")
        return v


class ProjectUpdate(BaseModel):
    name: Text150 | None = None
    description: LongText | None = None
    domain_id: int | None = None
    cohort_id: int | None = None
    planned_budget: Amount | None = None
    deadline: date | None = None


class StatusChange(BaseModel):
    status: Literal[tuple(PROJECT_STATUSES)]  # type: ignore[valid-type]
    comment: LongText | None = None


class ProgressUpdate(BaseModel):
    progress_pct: Annotated[int, Field(ge=0, le=100)]
    comment: LongText | None = None


class ProjectListItem(BaseModel):
    id: int
    name: str
    leader: str
    domain: str
    domain_id: int
    cohort: str
    cohort_id: int
    status: str
    progress_pct: int
    planned_budget: int
    funding_obtained: int
    deadline: date | None
    is_delayed: bool
    created_at: datetime
    updated_at: datetime
    is_simulated: bool


class EvaluationIn(BaseModel):
    evaluator: Text100
    score: Annotated[float, Field(ge=0, le=20)]
    recommendation: Literal[tuple(RECOMMENDATIONS)]  # type: ignore[valid-type]
    comment: LongText | None = None
    evaluated_at: date

    @field_validator("evaluated_at")
    @classmethod
    def _not_future(cls, v: date):
        if v > date.today():
            raise ValueError("La date d'évaluation ne peut pas être dans le futur.")
        return v


class EvaluationOut(ORM):
    id: int
    evaluator: str
    score: float
    recommendation: str
    comment: str | None
    evaluated_at: date


class MilestoneIn(BaseModel):
    title: Text100
    due_date: date
    completed_date: date | None = None

    @field_validator("completed_date")
    @classmethod
    def _not_future(cls, v: date | None):
        if v and v > date.today():
            raise ValueError("Un jalon ne peut pas être atteint à une date future.")
        return v


class MilestoneOut(ORM):
    id: int
    title: str
    position: int
    due_date: date
    completed_date: date | None


class HistoryOut(BaseModel):
    old_status: str | None
    new_status: str
    comment: str | None
    changed_at: datetime
    changed_by: str | None


# ------------------------------------------------------------------ financements
class FundingIn(BaseModel):
    project_id: int
    partner_id: int | None = None
    source_type: Literal[tuple(FUNDING_SOURCES)]  # type: ignore[valid-type]
    amount_requested: Amount
    amount_granted: Amount = 0
    amount_received: Amount = 0
    request_date: date
    grant_date: date | None = None
    status: FundingStatus
    notes: LongText | None = None


class FundingOut(BaseModel):
    id: int
    project_id: int
    project_name: str
    cohort: str
    domain: str
    partner_id: int | None
    partner: str | None
    source_type: str
    amount_requested: int
    amount_granted: int
    amount_received: int
    remaining: int
    request_date: date
    grant_date: date | None
    status: str
    notes: str | None
    is_simulated: bool


# ------------------------------------------------------------------ divers
class ActivityIn(BaseModel):
    title: Text150
    type: Literal[tuple(ACTIVITY_TYPES)]  # type: ignore[valid-type]
    activity_date: date
    cohort_id: int | None = None
    participants_count: Annotated[int, Field(ge=0, le=100000)] = 0
    description: LongText | None = None


class SettingsUpdate(BaseModel):
    institution_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)] | None = None
    delay_tolerance_days: Annotated[int, Field(ge=0, le=180)] | None = None
    session_minutes: Annotated[int, Field(ge=15, le=480)] | None = None
    ai_enabled: bool | None = None
    ai_daily_limit: Annotated[int, Field(ge=0, le=1000)] | None = None


class AskIn(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=1000)]


class FiltersIn(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    cohort_ids: list[int] = []
    domain_ids: list[int] = []
    statuses: list[Literal[tuple(PROJECT_STATUSES)]] = []  # type: ignore[valid-type]


ReportType = Literal["global", "projects", "cohorts", "fundings", "performance", "delays"]


class ReportRequest(BaseModel):
    report_type: ReportType
    format: Literal["pdf", "xlsx", "csv"]
    filters: FiltersIn = FiltersIn()
    commentary: Annotated[str, StringConstraints(max_length=6000)] | None = None


class CommentaryRequest(BaseModel):
    report_type: ReportType
    filters: FiltersIn = FiltersIn()
