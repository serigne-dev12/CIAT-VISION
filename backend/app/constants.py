"""Référentiels métier : rôles, statuts et transitions autorisées (cahier des charges § 4 et § 5)."""
from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    COORDINATOR = "coordinator"
    ANALYST = "analyst"


ROLE_LABELS = {Role.ADMIN: "Administrateur", Role.COORDINATOR: "Coordonnateur du CIAT", Role.ANALYST: "Analyste"}

# Rôles autorisés à modifier les données métier
EDITORS = (Role.ADMIN, Role.COORDINATOR)


class ProjectStatus(StrEnum):
    PENDING = "En attente"
    EVALUATION = "En évaluation"
    NOT_RETAINED = "Non retenu"
    SELECTED = "Sélectionné"
    INCUBATION = "En incubation"
    DEVELOPMENT = "En développement"
    PROTOTYPE = "Prototype réalisé"
    COMPLETED = "Terminé"
    SUSPENDED = "Suspendu"


PROJECT_STATUSES = [s.value for s in ProjectStatus]

# Transitions autorisées (diagramme d'états, docs/02_architecture.md § 6)
TRANSITIONS: dict[ProjectStatus, set[ProjectStatus]] = {
    ProjectStatus.PENDING: {ProjectStatus.EVALUATION},
    ProjectStatus.EVALUATION: {ProjectStatus.SELECTED, ProjectStatus.NOT_RETAINED},
    ProjectStatus.SELECTED: {ProjectStatus.INCUBATION},
    ProjectStatus.INCUBATION: {ProjectStatus.DEVELOPMENT, ProjectStatus.SUSPENDED},
    ProjectStatus.DEVELOPMENT: {ProjectStatus.PROTOTYPE, ProjectStatus.SUSPENDED},
    ProjectStatus.PROTOTYPE: {ProjectStatus.COMPLETED, ProjectStatus.SUSPENDED},
    ProjectStatus.SUSPENDED: {ProjectStatus.INCUBATION, ProjectStatus.DEVELOPMENT, ProjectStatus.PROTOTYPE},
    ProjectStatus.NOT_RETAINED: set(),
    ProjectStatus.COMPLETED: set(),
}

# Ensembles utilisés par les indicateurs (cahier des charges § 7.1)
ACTIVE_STATUSES = [ProjectStatus.SELECTED, ProjectStatus.INCUBATION, ProjectStatus.DEVELOPMENT, ProjectStatus.PROTOTYPE]
INCUBATED_STATUSES = [ProjectStatus.INCUBATION, ProjectStatus.DEVELOPMENT, ProjectStatus.PROTOTYPE,
                      ProjectStatus.COMPLETED, ProjectStatus.SUSPENDED]
SELECTED_OR_LATER = [ProjectStatus.SELECTED, *INCUBATED_STATUSES]


class ApplicationStatus(StrEnum):
    RECEIVED = "Reçue"
    EVALUATION = "En évaluation"
    ACCEPTED = "Acceptée"
    REJECTED = "Rejetée"


class FundingStatus(StrEnum):
    REQUESTED = "Demandé"
    GRANTED = "Accordé"
    PARTIAL = "Partiellement reçu"
    RECEIVED = "Reçu"
    REFUSED = "Refusé"


FUNDING_SOURCES = ["Subvention", "Prêt d'honneur", "Prix de concours", "Investisseur", "Fonds propres", "Partenaire"]
PARTNER_TYPES = ["Technique", "Financier", "Institutionnel", "Académique", "Commercial"]
LEADER_PROFILES = ["Étudiant ISEP", "Diplômé ISEP", "Externe"]
GENDERS = ["Femme", "Homme"]
ACTIVITY_TYPES = ["Formation", "Atelier", "Événement", "Mentorat"]
RECOMMENDATIONS = ["Favorable", "Réservé", "Défavorable"]

DEFAULT_MILESTONES = ["Validation du besoin", "Modèle économique", "Prototype", "Test pilote", "Lancement"]

# Paramètres modifiables par l'administrateur (valeurs par défaut)
DEFAULT_SETTINGS = {
    "institution_name": "ISEP Amadou Trawaré de Diamniadio",
    "delay_tolerance_days": "0",
    "session_minutes": "60",
    "ai_enabled": "true",
    "ai_daily_limit": "50",
    "risk_model": "regles",
    "alerts_generated_at": "",
}
