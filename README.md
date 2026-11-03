# CIAT VISION

**Plateforme intelligente de pilotage et d'analyse décisionnelle du CIAT**
*Le pilotage intelligent de l'innovation par la donnée.*
ISEP Amadou Trawaré de Diamniadio · Centre d'Innovation, d'Application et de Transfert

> ⚠️ Les données livrées avec l'application sont **SIMULÉES** et ne constituent pas des statistiques officielles.
> Elles peuvent être purgées et remplacées par les données réelles (Administration → Données, puis Importation).

## Fonctionnalités
- **Tableau de bord** : 8 indicateurs clés et 4 taux calculés par PostgreSQL, filtres par période, cohorte, domaine, statut.
- **Projets** : recherche, filtres, cycle de vie contrôlé, évaluations, jalons, progression, suppression logique.
- **Analyses** : 12 graphiques interactifs (Recharts).
- **Cohortes** et **financements** (demandé, accordé, reçu, reste à recevoir, besoin non couvert).
- **CIAT AI Analyst** : questions en français ; l'IA (Claude) n'accède aux données que par 7 fonctions d'analyse
  autorisées, sans SQL ni données personnelles ; chaque chiffre est vérifiable ; mode dégradé sans clé d'API.
- **Rapports** PDF / Excel / CSV (6 types), **importation** Excel / CSV avec prévisualisation et confirmation.
- **Sécurité** : JWT, bcrypt, 3 rôles contrôlés côté serveur, journal d'audit, contraintes d'intégrité en base.

## Démarrage rapide
```bash
docker compose up -d                                   # PostgreSQL 16 (ou voir le guide pour les autres options)
cd backend && python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt && copy .env.example .env   # compléter DATABASE_URL et JWT_SECRET
alembic upgrade head && uvicorn app.main:app --reload
cd ../frontend && npm install && npm run dev           # http://localhost:5173
```
Comptes de démonstration : `admin` / `Admin@2026`, `coordo` / `Coordo@2026`, `analyste` / `Analyste@2026`.

## Tests
```bash
cd backend && python -m pytest     # 80 tests sur une base PostgreSQL de test
cd frontend && npm test            # 8 tests
```

## Documentation (livrables)
| N° | Livrable | Fichier |
|---|---|---|
| 1 | Cahier des charges | [docs/01_cahier_des_charges.md](docs/01_cahier_des_charges.md) |
| — | Architecture et UML | [docs/02_architecture.md](docs/02_architecture.md) |
| 5 | Base de données et dictionnaire | [docs/03_base_de_donnees.md](docs/03_base_de_donnees.md) |
| 2 | Maquettes | [docs/04_maquettes.md](docs/04_maquettes.md) |
| — | Tests et anomalies | [docs/05_tests_et_anomalies.md](docs/05_tests_et_anomalies.md) |
| — | Installation, configuration, déploiement | [docs/06_guide_installation.md](docs/06_guide_installation.md) |
| 7 | Guide utilisateur | [docs/07_guide_utilisateur.md](docs/07_guide_utilisateur.md) |
| 6 | Rapport | [docs/08_rapport.md](docs/08_rapport.md) |
| 9 | Scénario de la vidéo | [docs/09_scenario_video.md](docs/09_scenario_video.md) |
| 8 | Journal des prompts | [docs/journal_des_prompts.md](docs/journal_des_prompts.md) |
| 3, 4 | Application et code source | `backend/`, `frontend/` |
| 10 | Déploiement | [render.yaml](render.yaml) |

**Versions PDF** de tous les livrables (diagrammes dessinés, prêtes pour la remise) : [docs/pdf/](docs/pdf/).
Pour les régénérer après une modification : `python scripts/generer_pdf_livrables.py` (voir l'en-tête du script).
Test de charge reproductible (1 000 projets) : `backend/scripts/mesurer_performances.py`.

## Structure
```
backend/   API FastAPI : app/ (modèles, routes, services), alembic/ (migrations), tests/
frontend/  React + TypeScript : src/pages, src/components, public/logo (logos remplaçables)
docs/      Livrables, maquettes, exemple de fichier d'import
```
