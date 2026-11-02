# Phase 2 – Architecture logicielle et diagrammes UML

**Objectif de la phase :** définir l'organisation du code, les composants, leurs échanges et les principaux
scénarios avant d'écrire la moindre ligne de code.

Les diagrammes sont écrits en Mermaid : ils s'affichent directement dans GitHub, GitLab et VS Code
(extension « Markdown Preview Mermaid Support »).

---

## 1. Vue d'ensemble

```mermaid
flowchart LR
    subgraph Client["Navigateur (ordinateur, tablette, téléphone)"]
        SPA["Application React + TypeScript<br/>Vite · Tailwind · Recharts · Lucide"]
    end
    subgraph Serveur["API FastAPI (Python)"]
        AUTH["Authentification<br/>JWT · bcrypt · rôles"]
        CRUD["Gestion<br/>projets · cohortes · financements"]
        KPI["Moteur d'indicateurs<br/>(définitions uniques)"]
        ANA["Fonctions d'analyse<br/>autorisées (liste fermée)"]
        IA["Assistant CIAT AI Analyst"]
        REP["Rapports<br/>ReportLab · OpenPyXL · CSV"]
        IMP["Importation<br/>contrôle · prévisualisation"]
        AUD["Journal d'audit"]
    end
    DB[("PostgreSQL 16")]
    LLM["API Claude<br/>(Anthropic)"]

    SPA -- "HTTPS / JSON + jeton JWT" --> AUTH
    SPA --> CRUD & KPI & IA & REP & IMP
    CRUD & KPI & REP & IMP & AUD --> DB
    ANA --> KPI
    IA -- "appelle uniquement" --> ANA
    IA -- "question + résultats agrégés<br/>(aucune donnée personnelle)" --> LLM
    REP --> KPI
```

Principes :
1. **Le frontend n'affiche que ce que l'API renvoie** : aucune statistique n'est codée ou calculée dans l'interface.
2. **Une seule définition par indicateur** (`app/kpi.py`), utilisée par le tableau de bord, les rapports et l'IA.
3. **L'IA n'accède jamais à la base** : elle choisit des fonctions d'analyse ; le backend les exécute.
4. **Les droits sont vérifiés côté serveur** sur chaque route (dépendance FastAPI `require_roles`).

---

## 2. Organisation du code

```
CIAT_VISION/
├── backend/
│   ├── app/
│   │   ├── main.py            Application FastAPI, CORS, gestion des erreurs, routes
│   │   ├── config.py          Paramètres lus dans les variables d'environnement
│   │   ├── database.py        Connexion SQLAlchemy, session par requête
│   │   ├── models.py          Tables (SQLAlchemy 2)
│   │   ├── schemas.py         Schémas d'entrée/sortie (Pydantic 2)
│   │   ├── security.py        Hachage bcrypt, JWT, contrôle des rôles
│   │   ├── constants.py       Statuts, transitions autorisées, rôles
│   │   ├── services/          Règles métier (projets, KPI, analyses, IA, rapports, import, audit)
│   │   ├── routers/           Une route par module (auth, projects, cohorts, fundings…)
│   │   ├── seed.py            Génération des données SIMULÉES
│   │   └── assets/            Logo utilisé dans les PDF
│   ├── alembic/               Migrations du schéma
│   ├── tests/                 Tests pytest
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/               Client HTTP typé
│   │   ├── auth/              Contexte d'authentification, garde de routes
│   │   ├── components/        Composants réutilisables (cartes KPI, filtres, tableaux, modales…)
│   │   ├── pages/             Une page par module
│   │   └── lib/               Formatage, couleurs, permissions
│   └── package.json
├── docs/                      Livrables (cahier des charges, architecture, base, maquettes, guides, rapport)
├── docker-compose.yml         PostgreSQL local
└── render.yaml                Déploiement Render
```

---

## 3. Diagramme de cas d'utilisation

```mermaid
flowchart LR
    AN(["👤 Analyste"])
    CO(["👤 Coordonnateur"])
    AD(["👤 Administrateur"])

    subgraph S["CIAT VISION"]
        UC1(("Se connecter / gérer son profil"))
        UC2(("Consulter le tableau de bord et filtrer"))
        UC3(("Analyser les performances"))
        UC4(("Consulter projets, cohortes, financements"))
        UC5(("Interroger l'assistant IA"))
        UC6(("Générer un rapport PDF / Excel / CSV"))
        UC7(("Créer, modifier, supprimer un projet"))
        UC8(("Changer le statut, suivre la progression et les jalons"))
        UC9(("Gérer cohortes, candidatures, évaluations, financements"))
        UC10(("Importer des données Excel / CSV"))
        UC11(("Gérer les utilisateurs et les rôles"))
        UC12(("Gérer les paramètres"))
        UC13(("Consulter le journal d'audit"))
        UC14(("Purger les données simulées / restaurer un projet"))
    end

    AN --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6
    CO --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10
    AD --- UC1 & UC2 & UC3 & UC4 & UC5 & UC6 & UC7 & UC8 & UC9 & UC10 & UC11 & UC12 & UC13 & UC14
```

---

## 4. Diagramme de classes (modèle métier)

```mermaid
classDiagram
    direction LR
    class User {
        id; username; full_name; email
        role: admin|coordinator|analyst
        password_hash; is_active
        failed_attempts; locked_until
    }
    class ProjectLeader {
        id; first_name; last_name
        gender; email; phone; profile
    }
    class Domain { id; name; description }
    class Cohort { id; name; year; start_date; end_date }
    class Application {
        id; project_title; submitted_at
        status: Reçue|En évaluation|Acceptée|Rejetée
        decision_date
    }
    class Evaluation { id; evaluator; score_0_20; recommendation; comment; evaluated_at }
    class Project {
        id; name; description; status
        progress_pct; planned_budget; deadline
        is_archived; created_at; updated_at
        +funding_obtained() calculé
        +is_delayed() calculé
    }
    class Milestone { id; title; due_date; completed_date; position }
    class StatusHistory { id; old_status; new_status; comment; changed_at }
    class Partner { id; name; type }
    class Funding {
        id; source_type; status
        amount_requested; amount_granted; amount_received
        request_date; grant_date
    }
    class Activity { id; title; type; date; participants_count }
    class AuditLog { id; action; entity; entity_id; details; created_at }
    class AIConversation { id; question; answer; tools_used; mode }

    ProjectLeader "1" -- "*" Application : dépose
    Cohort "1" -- "*" Application
    Domain "1" -- "*" Application
    Application "1" -- "*" Evaluation : est évaluée par
    Application "1" -- "1" Project : donne lieu à
    Project "1" -- "*" Milestone
    Project "1" -- "*" StatusHistory
    Project "1" -- "*" Funding
    Partner "0..1" -- "*" Funding : finance
    Cohort "0..1" -- "*" Activity
    User "1" -- "*" AuditLog
    User "1" -- "*" AIConversation
    User "1" -- "*" StatusHistory : modifie
```

---

## 5. Diagrammes de séquence

### 5.1. Connexion et appel protégé
```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant F as Frontend React
    participant A as API FastAPI
    participant D as PostgreSQL
    U->>F: identifiant + mot de passe
    F->>A: POST /api/auth/login
    A->>D: lecture du compte
    alt compte bloqué (5 échecs)
        A-->>F: 423 Compte temporairement bloqué
    else mot de passe correct (bcrypt)
        A->>D: remise à zéro des échecs + journal « CONNEXION »
        A-->>F: jeton JWT (60 min) + profil
        F->>A: GET /api/projects (Authorization: Bearer …)
        A->>A: vérification du jeton et du rôle
        A-->>F: 200 données
    else mot de passe incorrect
        A->>D: échecs + 1, journal « CONNEXION_ECHEC »
        A-->>F: 401 Identifiants incorrects
    end
```

### 5.2. Question posée à l'assistant IA
```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant F as Frontend
    participant A as API /api/assistant
    participant FN as Fonctions d'analyse
    participant D as PostgreSQL
    participant L as API Claude
    U->>F: « Quelle cohorte a les meilleurs résultats ? »
    F->>A: POST /api/assistant/ask
    A->>L: question + description des 7 fonctions autorisées
    L-->>A: demande d'appel : comparer_cohortes()
    A->>A: validation des paramètres (Pydantic)
    A->>FN: comparer_cohortes()
    FN->>D: requêtes agrégées (ORM)
    D-->>FN: résultats
    FN-->>A: indicateurs par cohorte (sans données personnelles)
    A->>L: résultats de la fonction
    L-->>A: réponse rédigée (chiffres issus des résultats)
    A->>D: historique + journal
    A-->>F: réponse + fonctions utilisées + chiffres + mention « données simulées »
```
Sans clé d'API, l'étape « API Claude » est remplacée par une **reconnaissance de mots-clés** qui appelle
directement la fonction d'analyse correspondante (mode dégradé).

### 5.3. Importation d'un fichier
```mermaid
sequenceDiagram
    actor C as Coordonnateur
    participant F as Frontend
    participant A as API /api/imports
    participant D as PostgreSQL
    C->>F: dépose projets.xlsx
    F->>A: POST /preview (fichier, entité)
    A->>A: colonnes, formats, valeurs, doublons
    A->>D: recherche des doublons existants
    A-->>F: lignes valides / en erreur / doublons
    F-->>C: prévisualisation
    C->>F: confirme l'importation
    F->>A: POST /commit (même fichier)
    A->>A: nouvelle validation complète
    A->>D: insertion en UNE transaction + journal
    A-->>F: rapport d'importation
```

---

## 6. Diagramme d'états d'un projet

```mermaid
stateDiagram-v2
    [*] --> EnAttente
    EnAttente: En attente
    EnEvaluation: En évaluation
    NonRetenu: Non retenu
    Selectionne: Sélectionné
    EnIncubation: En incubation
    EnDeveloppement: En développement
    Prototype: Prototype réalisé
    Termine: Terminé
    Suspendu: Suspendu

    EnAttente --> EnEvaluation
    EnEvaluation --> Selectionne: ≥ 1 évaluation, candidature acceptée
    EnEvaluation --> NonRetenu: ≥ 1 évaluation, candidature rejetée
    Selectionne --> EnIncubation: jalons créés
    EnIncubation --> EnDeveloppement
    EnDeveloppement --> Prototype
    Prototype --> Termine: progression = 100 %
    EnIncubation --> Suspendu
    EnDeveloppement --> Suspendu
    Prototype --> Suspendu
    Suspendu --> EnIncubation: reprise
    Suspendu --> EnDeveloppement: reprise
    Suspendu --> Prototype: reprise
    NonRetenu --> [*]
    Termine --> [*]
```
La suspension n'est possible qu'à partir de « En incubation » : un projet suspendu est donc toujours un projet
incubé, ce qui rend le taux d'achèvement sans ambiguïté.

---

## 7. Diagramme de déploiement

```mermaid
flowchart TB
    subgraph Render["Render (HTTPS)"]
        STATIC["Site statique<br/>frontend compilé (Vite)"]
        WEB["Service web Python<br/>uvicorn + FastAPI"]
        PG[("PostgreSQL hébergé")]
    end
    NAV["Navigateur du jury / du CIAT"] -->|HTTPS| STATIC
    NAV -->|HTTPS /api| WEB
    WEB -->|connexion chiffrée| PG
    WEB -->|HTTPS| CLAUDE["API Claude"]
```
Variables d'environnement du service web : `DATABASE_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY` (facultative),
`CORS_ORIGINS`. Aucune n'est écrite dans le code.

---

## 8. Choix techniques justifiés

| Choix | Justification |
|---|---|
| FastAPI | Validation automatique (Pydantic), documentation OpenAPI générée (`/docs`), performances |
| SQLAlchemy 2 + Alembic | Requêtes paramétrées (anti-injection), migrations versionnées |
| PostgreSQL | Contraintes d'intégrité riches, agrégations rapides, hébergement disponible sur Render |
| JWT sans état | Pas de session serveur à stocker ; durée limitée ; renouvellement par `/api/auth/refresh` |
| Jeton en `sessionStorage` | Effacé à la fermeture de l'onglet ; l'application n'insère jamais de HTML non échappé (React) |
| Appel d'outils pour l'IA | Le modèle ne peut que choisir des fonctions validées : pas de SQL généré, chiffres traçables |
| ReportLab (graphiques intégrés) | PDF vectoriels sans dépendance graphique lourde |
| Recharts | Graphiques React déclaratifs, interactifs, responsives |
