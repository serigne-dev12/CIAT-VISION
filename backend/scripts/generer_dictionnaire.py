"""Génère docs/03_base_de_donnees.md à partir des modèles SQLAlchemy (le document ne peut pas diverger du code).

Usage (depuis backend/) :  python -m scripts.generer_dictionnaire
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import CheckConstraint, Index

from app import models  # noqa: F401
from app.database import Base

SORTIE = Path(__file__).resolve().parents[2] / "docs" / "03_base_de_donnees.md"

TABLES = {
    "users": "Comptes des utilisateurs de la plateforme et leur rôle.",
    "domains": "Domaines d'activité des projets (référentiel).",
    "cohorts": "Promotions annuelles d'incubation.",
    "project_leaders": "Porteurs de projet. **Données personnelles** : jamais transmises à l'IA ; coordonnées masquées pour le rôle Analyste.",
    "partners": "Partenaires et bailleurs du CIAT.",
    "applications": "Candidatures déposées par les porteurs pour une cohorte.",
    "evaluations": "Évaluations des candidatures par le comité de sélection.",
    "projects": "Projets accompagnés (un projet par candidature).",
    "project_status_history": "Historique des changements de statut (traçabilité).",
    "milestones": "Jalons (étapes) de chaque projet incubé.",
    "fundings": "Financements demandés, accordés et reçus par les projets.",
    "activities": "Activités du CIAT : formations, ateliers, événements, mentorat.",
    "audit_logs": "Journal d'audit : connexions, modifications, exports, imports, changements de droits.",
    "ai_conversations": "Historique des questions posées à l'assistant IA.",
    "settings": "Paramètres modifiables par l'administrateur (clé / valeur).",
    "import_batches": "Traçabilité des importations de fichiers.",
}

COMMUNS = {
    "id": "Identifiant unique (clé primaire, auto-incrémentée).",
    "created_at": "Date et heure de création (automatique).",
    "updated_at": "Date et heure de dernière modification (automatique).",
    "is_simulated": "Vrai pour les données de démonstration SIMULÉES (purgeables par l'administrateur).",
}

COLONNES = {
    "users.username": "Identifiant de connexion (unique, 3 à 30 caractères).",
    "users.full_name": "Nom complet affiché.",
    "users.email": "Adresse e-mail professionnelle.",
    "users.role": "Rôle : admin, coordinator ou analyst (matrice des droits § 4.2 du cahier des charges).",
    "users.password_hash": "Hachage bcrypt du mot de passe (le mot de passe n'est jamais stocké).",
    "users.is_active": "Compte actif (un compte désactivé ne peut plus se connecter).",
    "users.failed_attempts": "Nombre d'échecs de connexion consécutifs.",
    "users.locked_until": "Fin du blocage temporaire après 5 échecs.",
    "users.last_login_at": "Date de la dernière connexion réussie.",
    "domains.name": "Nom du domaine (unique).",
    "domains.description": "Description du domaine.",
    "cohorts.name": "Nom de la cohorte (unique), ex. « Cohorte 2026 ».",
    "cohorts.year": "Année de la cohorte.",
    "cohorts.start_date": "Début de l'incubation.",
    "cohorts.end_date": "Fin de l'incubation (postérieure au début).",
    "cohorts.description": "Description libre.",
    "project_leaders.first_name": "Prénom du porteur.",
    "project_leaders.last_name": "Nom du porteur.",
    "project_leaders.gender": "Femme, Homme ou non renseigné.",
    "project_leaders.email": "E-mail du porteur (donnée personnelle).",
    "project_leaders.phone": "Téléphone du porteur (donnée personnelle).",
    "project_leaders.profile": "Étudiant ISEP, Diplômé ISEP ou Externe.",
    "partners.name": "Nom du partenaire (unique).",
    "partners.type": "Technique, Financier, Institutionnel, Académique ou Commercial.",
    "partners.contact_email": "E-mail de contact.",
    "applications.leader_id": "Porteur ayant déposé la candidature.",
    "applications.cohort_id": "Cohorte visée.",
    "applications.domain_id": "Domaine du projet proposé.",
    "applications.project_title": "Intitulé du projet proposé.",
    "applications.submitted_at": "Date de dépôt (sert au filtre « période »).",
    "applications.status": "Reçue, En évaluation, Acceptée ou Rejetée.",
    "applications.decision_date": "Date de la décision du comité.",
    "evaluations.application_id": "Candidature évaluée.",
    "evaluations.evaluator": "Membre du comité ou expert.",
    "evaluations.score": "Note sur 20.",
    "evaluations.recommendation": "Favorable, Réservé ou Défavorable.",
    "evaluations.comment": "Commentaire de l'évaluateur.",
    "evaluations.evaluated_at": "Date de l'évaluation (antérieure à la décision).",
    "projects.application_id": "Candidature d'origine (relation 1-1).",
    "projects.name": "Nom du projet (unique au sein d'une cohorte).",
    "projects.description": "Description du projet.",
    "projects.leader_id": "Porteur du projet.",
    "projects.domain_id": "Domaine d'activité.",
    "projects.cohort_id": "Cohorte.",
    "projects.status": "Statut (cycle de vie § 5.2) : En attente … Terminé, Suspendu, Non retenu.",
    "projects.progress_pct": "Progression de 0 à 100 % (100 % obligatoire si Terminé).",
    "projects.planned_budget": "Budget prévisionnel en FCFA.",
    "projects.deadline": "Date limite du projet (sert au calcul des retards).",
    "projects.is_archived": "Suppression logique : le projet est exclu des listes et des indicateurs.",
    "projects.archived_at": "Date de la suppression logique.",
    "project_status_history.project_id": "Projet concerné.",
    "project_status_history.old_status": "Statut précédent.",
    "project_status_history.new_status": "Nouveau statut.",
    "project_status_history.comment": "Justification éventuelle.",
    "project_status_history.changed_by": "Utilisateur auteur du changement.",
    "project_status_history.changed_at": "Date du changement.",
    "milestones.project_id": "Projet concerné.",
    "milestones.title": "Intitulé du jalon.",
    "milestones.position": "Ordre du jalon.",
    "milestones.due_date": "Date prévue.",
    "milestones.completed_date": "Date réelle d'atteinte (vide = non atteint ; jamais dans le futur).",
    "fundings.project_id": "Projet financé.",
    "fundings.partner_id": "Partenaire / bailleur (facultatif).",
    "fundings.source_type": "Subvention, Prêt d'honneur, Prix de concours, Investisseur, Fonds propres ou Partenaire.",
    "fundings.amount_requested": "Montant demandé (FCFA).",
    "fundings.amount_granted": "Montant accordé (FCFA) ≤ demandé.",
    "fundings.amount_received": "Montant effectivement reçu (FCFA) ≤ accordé.",
    "fundings.request_date": "Date de la demande.",
    "fundings.grant_date": "Date de l'accord (≥ date de demande).",
    "fundings.status": "Demandé, Accordé, Partiellement reçu, Reçu ou Refusé (cohérent avec les montants).",
    "fundings.notes": "Remarques.",
    "activities.title": "Intitulé de l'activité.",
    "activities.type": "Formation, Atelier, Événement ou Mentorat.",
    "activities.activity_date": "Date de l'activité.",
    "activities.cohort_id": "Cohorte concernée (facultatif).",
    "activities.participants_count": "Nombre de participants.",
    "activities.description": "Description.",
    "audit_logs.user_id": "Utilisateur auteur de l'action.",
    "audit_logs.username": "Identifiant (conservé même si le compte est supprimé, ou tenté si inconnu).",
    "audit_logs.action": "Code de l'action (CONNEXION, CREATION_PROJET, EXPORT_RAPPORT, IMPORT…).",
    "audit_logs.entity": "Type d'objet concerné.",
    "audit_logs.entity_id": "Identifiant de l'objet concerné.",
    "audit_logs.details": "Détails lisibles de l'action.",
    "audit_logs.ip_address": "Adresse IP de l'utilisateur.",
    "ai_conversations.user_id": "Utilisateur ayant posé la question.",
    "ai_conversations.question": "Question posée.",
    "ai_conversations.answer": "Réponse fournie.",
    "ai_conversations.tools_used": "Fonctions d'analyse appelées, paramètres et résultats (JSON).",
    "ai_conversations.mode": "IA (Claude) ou dégradé (sans IA générative).",
    "settings.key": "Nom du paramètre (clé primaire).",
    "settings.value": "Valeur du paramètre.",
    "import_batches.user_id": "Auteur de l'importation.",
    "import_batches.entity": "Type de données importées (projects, fundings, cohorts).",
    "import_batches.filename": "Nom du fichier importé.",
    "import_batches.rows_imported": "Lignes enregistrées.",
    "import_batches.rows_skipped": "Lignes ignorées (erreurs, doublons).",
}


def main() -> None:
    l = ["# Phase 3 – Base de données PostgreSQL et dictionnaire des données", "",
         "**Objectif de la phase :** modéliser des données structurées, cohérentes et protégées par des contraintes.",
         "", "> Document **généré automatiquement** à partir du code (`backend/scripts/generer_dictionnaire.py`) : "
         "il reflète exactement le schéma réel. Le schéma est créé par la migration Alembic "
         "`backend/alembic/versions/*_schema_initial_ciat_vision.py`.", "",
         "## 1. Modèle conceptuel (diagramme entité-association)", "", "```mermaid", "erDiagram"]
    for t in Base.metadata.sorted_tables:
        for fk in t.foreign_keys:
            parent = "|o" if fk.parent.nullable else "||"  # FK facultative : zéro ou un parent
            enfant = "o|" if fk.parent.unique else "o{"     # FK unique : relation 1-1
            l.append(f"    {fk.column.table.name} {parent}--{enfant} {t.name} : \"{fk.parent.name}\"")
    l += ["```", "", "## 2. Conventions", "",
          "- Clé primaire `id` (entier auto-incrémenté) sur toutes les tables (sauf `settings` : clé texte).",
          "- `created_at` / `updated_at` renseignés automatiquement par PostgreSQL.",
          "- `is_simulated` sur les tables métier : identifie les données de démonstration (purge en un clic).",
          "- Montants en **FCFA** (entiers 64 bits), dates au format ISO.",
          "- Les valeurs autorisées (statuts, rôles, montants, ordre des dates) sont contrôlées **en base** par des "
          "contraintes `CHECK`, en plus de la validation Pydantic de l'API : une donnée incohérente ne peut pas être "
          "enregistrée, même par un script.",
          "- Suppression des projets : **logique** (`is_archived`), pour préserver l'historique.", "",
          "## 3. Dictionnaire des données", ""]
    for t in Base.metadata.sorted_tables:
        l += [f"### `{t.name}`", "", TABLES.get(t.name, ""), "",
              "| Colonne | Type | Obligatoire | Clé | Description |", "|---|---|:-:|---|---|"]
        for c in t.columns:
            cle = "PK" if c.primary_key else ""
            if c.foreign_keys:
                fk = next(iter(c.foreign_keys))
                cle = f"FK → `{fk.column.table.name}` ({fk.ondelete or 'NO ACTION'})"
            if c.unique:
                cle = (cle + " · " if cle else "") + "unique"
            desc = COLONNES.get(f"{t.name}.{c.name}") or COMMUNS.get(c.name, "")
            l.append(f"| `{c.name}` | {str(c.type).replace('VARCHAR', 'texte ').replace('INTEGER', 'entier')} "
                     f"| {'non' if c.nullable and not c.primary_key else 'oui'} | {cle} | {desc} |")
        checks = [c for c in t.constraints if isinstance(c, CheckConstraint)]
        if checks:
            l += ["", "Contraintes :"] + [f"- `{c.name}` : `{c.sqltext}`" for c in checks]
        idx = [i for i in t.indexes if isinstance(i, Index)]
        if idx:
            l += ["", "Index : " + ", ".join(f"`{i.name}` ({', '.join(col.name for col in i.columns)})" for i in idx)]
        l.append("")
    l += ["## 4. Index et performances", "",
          "Les colonnes utilisées par les filtres du tableau de bord (cohorte, domaine, statut, date de dépôt, "
          "archivage) et toutes les clés étrangères sont indexées. Les indicateurs sont calculés par des agrégations "
          "SQL (`COUNT … FILTER`, `SUM`, `date_trunc`) exécutées par PostgreSQL, sans charger les lignes en mémoire.", "",
          "## 5. Sauvegarde", "", "```bash", "pg_dump --format=custom --file=ciat_vision_$(date +%F).dump \"$DATABASE_URL\"",
          "pg_restore --clean --if-exists --dbname=\"$DATABASE_URL\" ciat_vision_AAAA-MM-JJ.dump", "```", ""]
    SORTIE.write_text("\n".join(l), encoding="utf-8")
    print(f"Écrit : {SORTIE} ({len(Base.metadata.tables)} tables)")


if __name__ == "__main__":
    main()
