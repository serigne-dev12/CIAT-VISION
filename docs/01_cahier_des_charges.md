# INSTITUT SUPÉRIEUR D'ENSEIGNEMENT PROFESSIONNEL
## ISEP AMADOU TRAWARÉ DE DIAMNIADIO
### Évaluation pratique en intelligence artificielle générative

# CAHIER DES CHARGES – CIAT VISION
### Plateforme intelligente de pilotage et d'analyse décisionnelle du CIAT

> *Le pilotage intelligent de l'innovation par la donnée.*

| | |
|---|---|
| **Projet** | Projet 3 – Tableau de bord décisionnel du CIAT |
| **Établissement** | ISEP Amadou Trawaré de Diamniadio |
| **Structure bénéficiaire** | Centre d'Innovation, d'Application et de Transfert (CIAT) |
| **Réalisateur** | Étudiant en informatique – Analyse de performance digitale |
| **Année académique** | 2026-2027 |
| **Version** | 1.2 – voir § 20 « Historique des versions » |
| **Statut** | Validé (points V1 à V5 acceptés ; V6 et V7 en attente d'éléments externes) |

---

## 1. Présentation générale du projet

### 1.1. Contexte
Le Centre d'Innovation, d'Application et de Transfert (CIAT) de l'ISEP Amadou Trawaré de Diamniadio a pour
mission de promouvoir l'innovation ainsi que le développement, l'application et le transfert de technologies.
Il accompagne les porteurs de projets et les entrepreneurs à travers son incubateur.

Dans le cadre de ses activités, le CIAT doit suivre des informations relatives aux candidatures, aux projets
accompagnés, aux cohortes, aux financements, aux partenariats et aux résultats obtenus. La centralisation et
l'analyse de ces informations constituent un enjeu important pour le suivi des activités et la prise de décision.

### 1.2. Présentation de la solution
CIAT VISION est une application web décisionnelle qui centralise, analyse et visualise les données des
activités du CIAT. Elle permet aux responsables de consulter les indicateurs clés de performance, de suivre
l'évolution des projets, de comparer les cohortes et de produire des rapports.

La plateforme intègre un assistant intelligent, **CIAT AI Analyst**, qui répond en langage naturel à partir des
données réelles de la base, en indiquant les chiffres utilisés et les limites de l'analyse.

### 1.3. Problématique
Comment mettre à la disposition des responsables du CIAT une solution numérique permettant de centraliser les
données, de suivre les performances des projets, d'analyser les activités de l'incubateur et de faciliter la
prise de décision grâce à l'intelligence artificielle générative ?

### 1.4. Justification
- Centraliser des informations aujourd'hui dispersées.
- Améliorer le suivi des projets incubés et identifier tôt les retards et difficultés.
- Disposer d'indicateurs fiables, définis une fois pour toutes et calculés automatiquement.
- Comparer les résultats entre cohortes.
- Produire des rapports sans ressaisie.
- Rendre l'analyse des données accessible à des non-spécialistes grâce à l'IA générative.

### 1.5. Existant
Le CIAT ne dispose pas d'outil dédié accessible au projet. Un **prototype exploratoire** (Streamlit + SQLite) a
été réalisé en amont pour valider les indicateurs et le fonctionnement de l'assistant IA. CIAT VISION le remplace
par une architecture professionnelle (React, FastAPI, PostgreSQL) ; seules les définitions d'indicateurs et la
logique de génération des données de démonstration en seront reprises.

---

## 2. Objectifs du projet

### 2.1. Objectif général
Concevoir et développer une plateforme web décisionnelle intelligente permettant de suivre, analyser et
visualiser les performances des activités du CIAT afin de faciliter la prise de décision.

### 2.2. Objectifs spécifiques
1. Centraliser les informations relatives aux projets et aux activités du CIAT.
2. Développer un tableau de bord interactif.
3. Mettre en place des indicateurs clés de performance (KPI) aux définitions précises.
4. Analyser l'évolution des candidatures et des projets.
5. Comparer les performances des cohortes.
6. Suivre les financements et les partenariats.
7. Identifier les projets en retard.
8. Intégrer un assistant IA d'analyse des données.
9. Générer des rapports statistiques en PDF, Excel et CSV.
10. Importer des données externes (Excel, CSV) de manière contrôlée.

---

## 3. Périmètre du projet

### 3.1. Périmètre fonctionnel
Dix modules : authentification et utilisateurs ; tableau de bord général ; gestion des projets ; analyse des
performances ; gestion des cohortes ; suivi des financements ; assistant CIAT AI Analyst ; rapports et exports ;
administration ; importation des données.

### 3.2. Hors périmètre (version 1)
- Dépôt de candidature en ligne par les porteurs eux-mêmes (les candidatures sont saisies ou importées par le CIAT).
- Gestion documentaire (pièces jointes des dossiers).
- Envoi de courriels et de notifications.
- Comptabilité détaillée des dépenses des projets.
- Application mobile native (l'interface web est responsive).

### 3.3. Public cible
Coordonnateur du CIAT, responsables de l'incubateur, analystes de données, administrateurs de la plateforme.

### 3.4. Limites
Le développement est réalisé avec des **données simulées**, les données institutionnelles du CIAT n'étant pas
accessibles. Elles servent uniquement aux tests et à la démonstration. La plateforme est conçue pour que ces
données soient remplacées par les données réelles (voir § 11).

---

## 4. Utilisateurs et gestion des droits

### 4.1. Profils
| Profil | Rôle |
|---|---|
| **Administrateur** | Gère les comptes, les rôles, les paramètres et consulte les journaux. Accès à tous les modules. |
| **Coordonnateur du CIAT** | Pilote l'activité : gère les projets, cohortes, candidatures et financements, importe les données, produit les rapports. |
| **Analyste** | Consulte et analyse les données, produit des synthèses et des exports. Ne modifie pas les données. |

### 4.2. Matrice des droits
Le prompt et la version 1.0 ne précisaient pas qui peut **modifier** les données ; la matrice ci-dessous le fixe.

| Action | Administrateur | Coordonnateur | Analyste |
|---|:-:|:-:|:-:|
| Consulter le tableau de bord, les analyses, les cohortes, les financements | ✅ | ✅ | ✅ |
| Rechercher et filtrer les projets | ✅ | ✅ | ✅ |
| Créer / modifier un projet, une cohorte, une candidature, un financement | ✅ | ✅ | ❌ |
| Supprimer un projet (avec confirmation) | ✅ | ✅ | ❌ |
| Voir les coordonnées des porteurs (e-mail, téléphone) | ✅ | ✅ | ❌ |
| Importer des données (Excel, CSV) | ✅ | ✅ | ❌ |
| Générer les rapports et exports | ✅ | ✅ | ✅ |
| Utiliser l'assistant IA | ✅ | ✅ | ✅ |
| Consulter l'historique IA de tous les utilisateurs | ✅ | ❌ | ❌ |
| Gérer les utilisateurs et les rôles | ✅ | ❌ | ❌ |
| Gérer les paramètres de l'application | ✅ | ❌ | ❌ |
| Consulter le journal d'audit | ✅ | ❌ | ❌ |
| Purger les données simulées | ✅ | ❌ | ❌ |

Les droits sont vérifiés **côté serveur** sur chaque route de l'API. Le masquage des boutons dans l'interface ne
sert qu'au confort d'utilisation et ne constitue pas une protection.

---

## 5. Règles de gestion

### 5.1. Candidatures et projets
- Une **candidature** (`applications`) est le dossier déposé par un porteur pour une cohorte. Statuts :
  `Reçue` → `En évaluation` → `Acceptée` ou `Rejetée`.
- Un **projet** est créé en même temps que sa candidature. Son statut suit le cycle de vie ci-dessous.
- Une candidature ne peut être `Acceptée` ou `Rejetée` qu'après au moins une évaluation enregistrée.

### 5.2. Cycle de vie d'un projet
```
En attente ─► En évaluation ─┬─► Sélectionné ─► En incubation ─► En développement ─► Prototype réalisé ─► Terminé
                             └─► Non retenu
              (depuis En incubation, En développement ou Prototype réalisé) ◄─► Suspendu
```
| Statut | Signification |
|---|---|
| En attente | Candidature reçue, non encore examinée |
| En évaluation | Candidature en cours d'examen par le comité |
| **Non retenu** | Candidature rejetée *(statut ajouté – à valider, voir § 19)* |
| Sélectionné | Retenu par le comité, incubation pas encore démarrée |
| En incubation | Accompagnement démarré (validation du besoin, modèle économique) |
| En développement | Réalisation de la solution en cours |
| Prototype réalisé | Prototype fonctionnel livré |
| Terminé | Parcours d'incubation achevé |
| Suspendu | Accompagnement interrompu (peut reprendre) ; possible uniquement à partir de « En incubation » |

Règles :
- Seules les transitions du schéma sont autorisées ; toute transition est tracée dans le journal d'audit.
- `Sélectionné` exige une candidature `Acceptée` ; `Non retenu` exige une candidature `Rejetée`.
- `Terminé` impose une progression de 100 %.
- La progression (0 à 100 %) est saisie et ne peut pas diminuer sans justification enregistrée.
- La date limite doit être postérieure à la date de création.

### 5.3. Jalons
Chaque projet sélectionné reçoit des jalons (`milestones`) avec une date prévue et une date réelle (vide tant que
le jalon n'est pas atteint). Jalons par défaut : Validation du besoin, Modèle économique, Prototype, Test pilote,
Lancement. Une date réelle ne peut pas être future.

### 5.4. Financements
- Un financement est toujours associé à un projet et à une source (partenaire ou type de source).
- Montants en FCFA, entiers positifs ; contrôle : **reçu ≤ accordé ≤ demandé**.
- Statuts : `Demandé`, `Accordé`, `Partiellement reçu`, `Reçu`, `Refusé`.
- Le « financement obtenu » d'un projet n'est pas saisi : il est **calculé** à partir de ses financements, ce qui
  évite les incohérences.

### 5.5. Suppressions
La suppression d'un projet est une **suppression logique** (le projet est archivé et disparaît des listes et des
indicateurs). Seul l'administrateur peut le restaurer. Cela protège contre les erreurs et préserve l'historique.

---

## 6. Description des fonctionnalités

### 6.1. Module 1 – Authentification et utilisateurs
- Connexion par identifiant et mot de passe ; déconnexion.
- Session par jeton JWT à durée limitée (60 min), renouvelée tant que l'utilisateur est actif.
- Blocage temporaire du compte après 5 échecs de connexion consécutifs.
- Consultation et modification du profil ; changement du mot de passe.
- Redirection vers la connexion à l'expiration de la session.

### 6.2. Module 2 – Tableau de bord général
Huit indicateurs, tous calculés par le backend à partir de PostgreSQL (définitions au § 7) :
total des projets ; candidatures reçues ; projets sélectionnés ; projets en incubation ; prototypes réalisés ;
projets terminés ; projets en retard ; montant total des financements.

Filtres combinables : **période**, **cohorte**, **domaine**, **statut**. Chaque indicateur est cliquable et
ouvre la liste des projets correspondants. Une mention « Données simulées » s'affiche tant que la base en contient.

### 6.3. Module 3 – Gestion des projets
- Liste paginée avec recherche (nom, porteur, description) et filtres (domaine, cohorte, statut, retard).
- Fiche projet : informations, porteur, candidature et évaluations, jalons, financements, historique des statuts.
- Création, modification, suppression logique avec confirmation.
- Changement de statut selon les règles du § 5.2 ; mise à jour de la progression.

Attributs d'un projet : identifiant ; nom ; description ; porteur ; domaine ; cohorte ; date de création ;
statut ; progression (%) ; budget prévisionnel (FCFA) ; financement obtenu (calculé) ; date limite ;
date de dernière mise à jour (automatique).

### 6.4. Module 4 – Analyse des performances
| Analyse | Graphique |
|---|---|
| Évolution mensuelle des candidatures (reçues, acceptées, rejetées) | Courbes |
| Répartition des projets par domaine | Barres |
| Répartition des projets par statut | Circulaire (anneau) |
| Comparaison des cohortes | Barres groupées |
| Évolution des financements (accordés, reçus) | Courbes / aires |
| Financements par domaine et par source | Barres |
| Taux de sélection, d'achèvement et de retard par cohorte | Courbes |
| Progression des projets actifs | Histogramme |

Tous les graphiques sont alimentés par l'API, réagissent aux filtres et affichent une info-bulle détaillée.

### 6.5. Module 5 – Gestion des cohortes
Création, modification, consultation (projets de la cohorte), comparaison de plusieurs cohortes.
Indicateurs par cohorte : nombre de projets, projets terminés, projets en retard, taux de réussite,
progression moyenne, financement moyen par projet.

### 6.6. Module 6 – Suivi des financements
Enregistrement, modification et consultation des financements ; association à un projet ; identification des
sources. Pour chaque projet et en synthèse : budget prévisionnel, montant demandé, montant accordé, montant reçu,
**reste à recevoir** (accordé − reçu) et **besoin non couvert** (budget prévisionnel − accordé).

### 6.7. Module 7 – Assistant CIAT AI Analyst
**Fonctionnement :**
1. L'utilisateur pose une question en français.
2. Le modèle d'IA choisit, parmi une **liste fermée de fonctions d'analyse** exposées par le backend, celles qui
   répondent à la question (mécanisme d'appel d'outils).
3. Le backend vérifie les paramètres, exécute la fonction avec les droits de l'utilisateur et renvoie les résultats.
4. Le modèle rédige la réponse uniquement à partir de ces résultats.
5. L'interface affiche la réponse, **les chiffres et fonctions utilisés**, et les limites éventuelles.

**Fonctions d'analyse autorisées (version 1) :**
| Fonction | Rôle |
|---|---|
| `indicateurs_cles(filtres)` | Les KPI du § 7 sur un périmètre filtré |
| `repartition_projets(dimension, filtres)` | Effectifs par domaine, statut, cohorte ou mois |
| `projets_en_retard(filtres, limite)` | Liste des projets en retard et ampleur du retard |
| `comparer_cohortes(cohortes)` | Indicateurs côte à côte par cohorte |
| `synthese_financements(regroupement, filtres)` | Montants demandés, accordés, reçus par source, domaine ou période |
| `projets_a_surveiller(limite)` | Projets cumulant retard, faible progression ou besoin de financement non couvert |
| `evolution_candidatures(periode)` | Candidatures reçues, acceptées et rejetées par mois |

**Règles impératives :**
- L'IA **n'exécute jamais de SQL** : ni du SQL écrit par l'utilisateur, ni du SQL généré par le modèle.
- Aucun chiffre ne peut apparaître dans une réponse sans provenir d'une fonction d'analyse.
- Les recommandations sont présentées comme des **propositions** à examiner, distinctes des constats chiffrés.
- Si l'information n'existe pas dans la base, l'assistant le dit explicitement.
- Tant que la base contient des données simulées, chaque réponse le rappelle.
- **Protection des données :** les noms et coordonnées des porteurs ne sont jamais transmis au fournisseur d'IA.
- L'historique des échanges est conservé ; chacun voit le sien, l'administrateur voit tout.
- Sans clé d'API ou en cas d'indisponibilité du service, l'assistant reste utilisable en **mode dégradé** :
  questions guidées appelant directement les fonctions d'analyse, sans rédaction par l'IA.

### 6.8. Module 8 – Rapports et exportations
Six rapports : global des activités ; projets ; cohortes ; financements ; performances ; retards.
Formats : **PDF** (ReportLab), **Excel** (OpenPyXL), **CSV**.

Contenu d'un rapport PDF : logo CIAT VISION ; titre ; période et filtres appliqués ; indicateurs principaux ;
graphiques ; commentaires analytiques (rédigés par l'IA à partir des indicateurs, puis relus et modifiables par
l'utilisateur avant export) ; date de génération ; mention « Données simulées » le cas échéant ; numéros de page.

### 6.9. Module 9 – Administration
Création, modification et désactivation des comptes ; attribution des rôles ; consultation et export du journal
d'audit ; paramètres de l'application (seuil de tolérance des retards, durée de session, nom affiché de
l'institution, activation de l'assistant IA). Les clés d'API ne sont **jamais** saisies dans l'interface : elles
sont définies dans la configuration du serveur.

### 6.10. Module 10 – Importation des données
Formats : `.xlsx` et `.csv` (UTF-8, séparateur `;` ou `,`), 5 Mo maximum. Entités importables : projets et
porteurs, candidatures, financements, cohortes.

Étapes :
1. Téléchargement d'un **modèle de fichier** pour chaque entité.
2. Dépôt du fichier ; vérification des colonnes obligatoires.
3. Contrôle ligne par ligne : types, formats de date, valeurs autorisées, montants, références existantes
   (domaine, cohorte).
4. Détection des doublons dans le fichier et par rapport à la base.
5. **Prévisualisation** : lignes valides, lignes en erreur avec le motif, doublons.
6. Confirmation explicite, puis import en **une seule transaction** (tout ou rien).
7. Rapport d'import téléchargeable et trace dans le journal d'audit.

---

## 7. Indicateurs clés de performance

### 7.1. Définitions de base
- **Projets actifs** : statut `Sélectionné`, `En incubation`, `En développement` ou `Prototype réalisé`.
- **Projets incubés** : projets ayant atteint au moins `En incubation`, c'est-à-dire au statut `En incubation`,
  `En développement`, `Prototype réalisé`, `Terminé` ou `Suspendu`.
- **Projet en retard** : projet **actif** dont la date limite est dépassée, ou dont au moins un jalon non atteint
  a une date prévue dépassée de plus de *N* jours (*N* = seuil de tolérance paramétrable, 0 par défaut).
- Les projets **suspendus** ne sont jamais comptés en retard ; ils font l'objet d'un indicateur distinct.
- Les projets archivés (supprimés logiquement) sont exclus de tous les indicateurs.

### 7.2. Formules
| Indicateur | Formule |
|---|---|
| Total des projets | Projets dont la candidature n'est pas rejetée (hors `Non retenu`) |
| Candidatures reçues | Nombre de candidatures déposées |
| Projets sélectionnés | Candidatures `Acceptée` |
| Projets en incubation | Projets actifs au statut `En incubation` ou `En développement` |
| Prototypes réalisés | Projets au statut `Prototype réalisé` ou `Terminé` (un projet terminé a réalisé son prototype) |
| Projets terminés | Projets au statut `Terminé` |
| Projets en retard | Voir § 7.1 |
| Projets suspendus | Projets au statut `Suspendu` |
| Montant total des financements | Σ montants **reçus** (le montant accordé est affiché à côté) |
| Taux de sélection | Acceptées ÷ (acceptées + rejetées) × 100 |
| Taux d'achèvement | Terminés ÷ projets incubés × 100 |
| Taux de retard | Projets en retard ÷ projets actifs × 100 |
| Taux de réussite (cohorte) | Taux d'achèvement calculé sur la cohorte |
| Progression moyenne | Moyenne des progressions des projets actifs |
| Financement moyen | Σ montants accordés ÷ nombre de projets financés |

### 7.3. Règles de calcul
- Un dénominateur nul donne « Non calculable » (affiché « — »), jamais 0 % ni une erreur.
- Les taux sont arrondis à une décimale ; les montants en FCFA sont affichés avec séparateur de milliers.
- Chaque indicateur affiche sa définition au survol.
- Les définitions sont codées **une seule fois** dans le backend ; le tableau de bord, les rapports et
  l'assistant IA les réutilisent, ce qui garantit des chiffres identiques partout.

---

## 8. Exigences non fonctionnelles

### 8.1. Performance
| Exigence | Cible |
|---|---|
| Affichage du tableau de bord (jeu de 1 000 projets, serveur démarré) | < 2 s |
| Réponse des API d'indicateurs (95 % des requêtes) | < 500 ms |
| Réponse de l'assistant IA | < 30 s, avec indicateur de progression |
| Génération d'un rapport PDF | < 10 s |

Moyens : index sur les clés étrangères et les colonnes filtrées, agrégations calculées en SQL, pagination des listes.

### 8.2. Sécurité
- Mots de passe hachés avec **bcrypt** ; politique : 8 caractères minimum, majuscules, minuscules et chiffres.
- Jetons JWT signés, durée limitée ; secret stocké en variable d'environnement.
- Contrôle des rôles sur chaque route de l'API.
- Validation de toutes les entrées avec Pydantic (types, longueurs, plages de valeurs).
- Requêtes exclusivement via l'ORM ou des requêtes paramétrées (protection contre l'injection SQL).
- CORS limité au domaine du frontend ; HTTPS en production.
- Clés d'API dans les variables d'environnement, jamais dans le code ni dans le dépôt Git.
- Journal d'audit des connexions, modifications, suppressions, imports, exports et changements de droits.
- Sauvegarde de la base : export régulier (`pg_dump`) documenté dans le guide d'exploitation.

### 8.3. Protection des données personnelles
Les données des porteurs (noms, e-mails, téléphones) sont des données à caractère personnel au sens de la
**loi sénégalaise n° 2008-12 sur la protection des données à caractère personnel**. Mesures retenues :
minimisation des données collectées, accès aux coordonnées réservé aux rôles qui en ont besoin, aucune donnée
personnelle transmise au service d'IA, journalisation des accès. Une déclaration auprès de la CDP (Commission de
protection des données personnelles) devra être examinée avant toute mise en service avec des données réelles.

### 8.4. Ergonomie et accessibilité
- Responsive : téléphone (≥ 360 px), tablette (≥ 768 px), ordinateur (≥ 1 280 px).
- Contraste des textes conforme au niveau AA des WCAG (voir § 9.2).
- Navigation au clavier ; libellés sur tous les champs ; messages d'erreur explicites, en français.
- Retour visible pour chaque action (succès, erreur, chargement).

### 8.5. Fiabilité
Données persistantes dans PostgreSQL ; contraintes d'intégrité en base ; transactions pour les opérations
multiples (import) ; gestion centralisée des erreurs côté API et côté interface.

### 8.6. Maintenabilité
Code organisé par module, typé (TypeScript, annotations Python), commenté ; schéma de base versionné par
migrations (Alembic) ; tests automatisés ; documentation d'installation et d'exploitation.

---

## 9. Identité visuelle et charte graphique

### 9.1. Palette
| Couleur | Code | Utilisation |
|---|---|---|
| Marron foncé | `#4C311F` | Barre de navigation, boutons principaux |
| Beige doré | `#CA9871` | Éléments actifs, accents, surlignages |
| Marron profond | `#362316` | Titres et textes forts |
| Blanc | `#FFFFFF` | Fond des cartes et des pages |
| Gris clair | `#F5F5F5` | Arrière-plan secondaire |

### 9.2. Règles de contraste (vérifiées)
| Combinaison | Contraste | Usage autorisé |
|---|---|---|
| Blanc sur marron foncé `#4C311F` | 11,9 : 1 | ✅ Tout texte |
| Marron profond `#362316` sur beige `#CA9871` | 5,9 : 1 | ✅ Tout texte (boutons beige) |
| Beige `#CA9871` sur marron foncé `#4C311F` | 4,7 : 1 | ✅ Élément actif de la navigation |
| **Blanc sur beige `#CA9871`** | **2,5 : 1** | ❌ **Interdit** : illisible |
| Beige `#CA9871` sur blanc | 2,5 : 1 | ❌ Interdit pour du texte ; décoratif uniquement |

Les boutons beige portent donc un texte marron profond, jamais blanc.

### 9.3. Graphiques
Une seule couleur (marron) quand le graphique ne compare qu'une série. Pour plusieurs séries, palette catégorielle
complémentaire distinguable par les daltoniens, attribuée de façon fixe à chaque catégorie (un statut garde la
même couleur dans tous les graphiques). Fonds blancs, grilles discrètes.

### 9.4. Logo
Le logo **CIAT VISION fourni par le réalisateur** est utilisé sans déformation, en trois versions : horizontale
(en-tête), compacte (barre latérale repliée), page de connexion. Aucun logo officiel de l'ISEP n'est créé ni
imité. *Le fichier du logo reste à fournir (voir § 19).*

### 9.5. Style
Interface de type logiciel SaaS institutionnel : barre latérale, cartes à coins arrondis (8 px) et ombres
discrètes, police Inter, icônes Lucide, animations légères (≤ 200 ms) désactivées si l'utilisateur a demandé une
réduction des animations dans son système.

---

## 10. Architecture technique

### 10.1. Technologies
| Composant | Technologie |
|---|---|
| Frontend | React 19, TypeScript 7, Vite 8 |
| Style | Tailwind CSS 4 |
| Graphiques | Recharts 3 |
| Icônes | Lucide React |
| Navigation | React Router 7 |
| Backend | Python 3.12+ (testé en 3.14), FastAPI |
| ORM et migrations | SQLAlchemy 2, Alembic |
| Validation | Pydantic 2 |
| Base de données | PostgreSQL 16 |
| Authentification | JWT, bcrypt |
| IA générative | API Claude (Anthropic), modèle Claude Opus 5.5, appel d'outils |
| Export | ReportLab (PDF), OpenPyXL (Excel), CSV natif |
| Tests | pytest (backend), Vitest (frontend) |
| Déploiement | Render (API et frontend statique), PostgreSQL hébergé |

Versions minimales dans `backend/requirements.txt` ; versions exactes du frontend figées dans `frontend/package-lock.json`.

### 10.2. Architecture en trois couches
```
┌──────────────────────────┐   HTTPS + JWT   ┌───────────────────────────────┐   SQL   ┌──────────────┐
│ Présentation             │ ──────────────► │ Traitement (API FastAPI)      │ ──────► │ Données      │
│ React / TypeScript       │ ◄────── JSON ── │ auth · droits · KPI · exports │ ◄────── │ PostgreSQL   │
│ tableaux de bord, formul.│                 │ import · fonctions d'analyse  │         └──────────────┘
└──────────────────────────┘                 └──────────────┬────────────────┘
                                                            │ question + résultats agrégés (sans données personnelles)
                                                            ▼
                                                   ┌──────────────────┐
                                                   │ API IA (Claude)  │
                                                   └──────────────────┘
```
Le frontend ne contient **aucune donnée ni aucun calcul d'indicateur** : tout vient de l'API.

---

## 11. Données de démonstration et passage aux données réelles

### 11.1. Jeu de données simulées
Généré par un script reproductible (même graine, mêmes données), cohérent dans le temps :
- 4 cohortes (2023 à 2026), environ 250 candidatures et 120 projets incubés ;
- les 8 domaines : Technologies de l'information et du numérique ; Intelligence artificielle ; Agriculture ;
  Énergie ; Mécanique ; Environnement ; Éducation ; Santé et biomédical ;
- des évaluations, jalons, financements et partenaires fictifs ;
- des projets terminés, en cours, en retard et suspendus, dans des proportions réalistes.

Tous les noms de personnes, de projets et de partenaires sont inventés.

### 11.2. Identification et remplacement
- Chaque enregistrement simulé porte l'indicateur `is_simulated = vrai` en base.
- Un bandeau « Données simulées – non officielles » s'affiche sur toutes les pages, rapports et réponses de
  l'IA tant qu'il reste au moins un enregistrement simulé.
- Passage aux données réelles : l'administrateur **purge les données simulées** (action confirmée et journalisée),
  puis importe les données du CIAT via le module 10. Les comptes utilisateurs et les paramètres sont conservés.

---

## 12. Modélisation des données (vue d'ensemble)

| Table | Contenu |
|---|---|
| `users` | Comptes, rôle, hachage du mot de passe, état actif |
| `project_leaders` | Porteurs de projet (données personnelles) |
| `domains` | Domaines d'activité |
| `cohorts` | Cohortes (nom, année, dates) |
| `applications` | Candidatures (porteur, cohorte, date de dépôt, statut de décision) |
| `evaluations` | Notes et avis du comité sur les candidatures |
| `projects` | Projets (champs du § 6.3), liés à une candidature |
| `milestones` | Jalons des projets |
| `partners` | Partenaires et bailleurs |
| `fundings` | Financements (projet, partenaire ou source, montants demandé, accordé, reçu, statut) |
| `activities` | Activités du CIAT (formations, ateliers, événements, mentorat) et leurs participants |
| `audit_logs` | Journal d'audit |

Tables techniques ajoutées : `project_status_history` (historique des statuts), `ai_conversations`
(historique de l'assistant), `settings` (paramètres), `import_batches` (traçabilité des imports).

Toutes les tables ont une clé primaire, des clés étrangères avec règles de suppression explicites, des
contraintes de domaine (statuts, montants, dates), les champs `created_at` et `updated_at`, et l'indicateur
`is_simulated` pour les données métier. Le modèle détaillé et le dictionnaire des données sont produits en phase 3.

---

## 13. Contraintes

### 13.1. Humaines
Projet réalisé individuellement (le sujet prévoit des équipes de trois) : organisation **à faire valider par
l'enseignant**. Le périmètre est priorisé en conséquence (§ 14).

### 13.2. Techniques
Connexion Internet pour l'IA et le déploiement ; disponibilité de PostgreSQL ; gestion sécurisée des clés d'API.
Les offres d'hébergement gratuites mettent les services en veille après une période d'inactivité (premier
chargement lent) : la plateforme sera « réveillée » avant chaque présentation au jury.

### 13.3. Données
Données réelles non disponibles : les analyses de démonstration ne doivent pas être interprétées comme des
résultats institutionnels.

### 13.4. Financières
Technologies open source et offres gratuites ou peu coûteuses. Le coût de l'API d'IA est maîtrisé par un
plafond de requêtes par utilisateur et par jour (paramétrable) et un suivi de la consommation.

---

## 14. Priorisation (méthode MoSCoW)

| Priorité | Contenu |
|---|---|
| **Indispensable** | Authentification et rôles ; tableau de bord et filtres ; gestion des projets ; cohortes ; financements ; graphiques d'analyse ; assistant IA ; exports PDF et Excel ; données simulées ; déploiement |
| **Important** | Importation Excel/CSV ; rapports des six types ; journal d'audit ; administration des utilisateurs ; export CSV |
| **Souhaitable** | Historique des statuts affiché en frise ; paramètres avancés ; mode sombre |
| **Exclu (v1)** | Voir § 3.2 |

---

## 15. Planification

Conforme à la méthode imposée : une phase n'est commencée qu'après validation de la précédente.

| Phase | Contenu | Livrable de fin de phase |
|---|---|---|
| 1 | Analyse des besoins | Cahier des charges validé |
| 2 | Architecture logicielle, diagrammes UML (cas d'utilisation, classes, séquence, déploiement) | Dossier d'architecture |
| 3 | Modélisation de la base | Modèle conceptuel, schéma PostgreSQL, dictionnaire des données |
| 4 | Maquettes UI/UX (ordinateur et téléphone) | Maquettes des écrans principaux |
| 5 | Initialisation du frontend et du backend | Squelettes fonctionnels, base connectée |
| 6 | Authentification et utilisateurs | Module 1 + administration des comptes |
| 7 | Projets et cohortes | Modules 3 et 5 |
| 8 | Indicateurs et graphiques | Modules 2, 4 et 6 |
| 9 | Assistant IA | Module 7 |
| 10 | Rapports et importation | Modules 8 et 10 |
| 11 | Tests et corrections | Rapport de tests et journal des anomalies |
| 12 | Déploiement et documentation | Lien public, guides, rapport final |

Les dates seront fixées selon le calendrier de l'évaluation.

---

## 16. Tests et critères d'acceptation

### 16.1. Tests prévus
Connexion et déconnexion ; permissions par rôle ; création, modification et suppression d'un projet ;
gestion des cohortes ; calcul des KPI ; filtres ; graphiques ; exports PDF, Excel et CSV ; importation ;
assistant IA. Tests automatisés (pytest, Vitest) et scénarios de démonstration manuels. Les anomalies sont
consignées dans un journal (description, cause, correction, vérification).

### 16.2. Critères d'acceptation
| Module | Le module est accepté si… |
|---|---|
| Authentification | Un mauvais mot de passe est refusé ; un Analyste qui appelle une route de modification reçoit une erreur 403 |
| Tableau de bord | Chaque KPI est identique au résultat d'une requête SQL de contrôle sur le même périmètre |
| Filtres | Changer un filtre met à jour tous les indicateurs et graphiques de la page |
| Projets | Création, modification et suppression sont visibles immédiatement dans les listes et les KPI ; une transition de statut interdite est refusée avec un message |
| Financements | La saisie d'un montant reçu supérieur au montant accordé est refusée |
| Assistant IA | Sur 20 questions de référence, chaque chiffre cité correspond à la base ; une question hors données reçoit une réponse « information indisponible » ; aucune requête SQL n'est exécutée par le modèle |
| Rapports | Le PDF contient logo, titre, période, KPI, graphiques, date et mention « simulées » ; les chiffres sont identiques au tableau de bord |
| Importation | Un fichier contenant une colonne manquante, une date invalide et un doublon produit trois erreurs signalées et rien n'est importé sans confirmation |
| Responsive | Toutes les pages sont utilisables à 360 px de largeur sans défilement horizontal |
| Données simulées | Après purge, le bandeau disparaît et les KPI valent 0 ou « — » |

---

## 17. Risques

| Risque | Probabilité | Impact | Mesure |
|---|---|---|---|
| Charge de travail élevée pour un réalisateur seul | Élevée | Élevé | Priorisation MoSCoW, phases validées une à une |
| L'IA cite un chiffre erroné | Moyenne | Élevé | Fonctions d'analyse fermées, chiffres affichés, jeu de questions de référence testé |
| Indisponibilité ou coût de l'API d'IA | Moyenne | Moyen | Mode dégradé sans IA, plafond de requêtes |
| Mise en veille de l'hébergement gratuit | Élevée | Moyen | Réveil avant la démonstration ; vidéo de démonstration en secours |
| Fuite de données personnelles | Faible | Élevé | Droits par rôle, aucune donnée personnelle envoyée à l'IA, journal d'audit |
| Données réelles de structure différente | Moyenne | Moyen | Modèles d'import documentés, contrôles à l'import |

---

## 18. Livrables

| N° | Livrable | Description |
|---|---|---|
| 1 | Cahier des charges | Le présent document, validé |
| 2 | Maquettes | Interfaces ordinateur et téléphone |
| 3 | Application fonctionnelle | Version opérationnelle et testable |
| 4 | Code source | Organisé, commenté, documenté, versionné avec Git |
| 5 | Base de données | Schéma, migrations et dictionnaire des données |
| 6 | Rapport | 5 à 10 pages |
| 7 | Guide utilisateur | Par profil (administrateur, coordonnateur, analyste) |
| 8 | Journal des prompts | Prompts, résultats obtenus et corrections apportées |
| 9 | Vidéo de démonstration | Parcours des fonctionnalités principales |
| 10 | Lien de déploiement | Application accessible au jury, avec comptes de démonstration |
| — | Guide d'installation et de configuration | Installation locale, variables d'environnement, déploiement, sauvegarde |

---

## 19. Points soumis à validation

| N° | Point | Proposition |
|---|---|---|
| V1 ✅ | Représenter les candidatures rejetées | Ajouter le statut de projet **« Non retenu »** (absent de la liste du prompt) |
| V2 ✅ | Droits de l'Analyste | Lecture, analyses et exports seulement, sans accès aux coordonnées des porteurs (§ 4.2) |
| V3 ✅ | Définition d'un projet en retard | Date limite dépassée **ou** jalon en retard, seuil de tolérance paramétrable (§ 7.1) |
| V4 ✅ | Montant total des financements | Somme des montants **reçus**, avec le montant accordé affiché à côté (§ 7.2) |
| V5 ✅ | Fournisseur d'IA | API Claude (Anthropic) avec appel d'outils ; mode dégradé sans clé |
| V6 ⏳ | Logo CIAT VISION | Fichier à fournir ; logo provisoire en place, remplaçable sans modifier le code (guide d'installation § 8) |
| V7 ⏳ | Réalisation individuelle | À confirmer auprès de l'enseignant |

---

## 20. Historique des versions

| Version | Modifications |
|---|---|
| 1.0 | Version initiale rédigée par le réalisateur |
| 1.1 | Ajout : matrice des droits (§ 4.2) ; règles de gestion et cycle de vie des statuts (§ 5) ; statut « Non retenu » proposé ; définitions précises des projets actifs, incubés et en retard (§ 7.1) ; distinction des montants demandé, accordé et reçu, reste à recevoir et besoin non couvert ; liste fermée des fonctions d'analyse de l'IA, interdiction de tout SQL généré (§ 6.7) ; mode dégradé sans IA ; mécanisme de purge des données simulées (§ 11.2) ; protection des données personnelles, loi n° 2008-12 (§ 8.3) ; contrastes vérifiés de la palette (§ 9.2) ; cibles de performance chiffrées ; priorisation MoSCoW ; critères d'acceptation ; analyse des risques ; hors périmètre ; planification alignée sur les 12 phases du prompt. |
| 1.2 | Propositions V1 à V5 validées par le réalisateur (« fais tout ce qui a été demandé ») ; suspension limitée aux projets incubés (rend le taux d'achèvement non ambigu, décidé en phase 2) ; versions techniques réelles (§ 10.1). |

---

---

## 21. Conclusion
CIAT VISION vise à doter le CIAT de l'ISEP Amadou Trawaré de Diamniadio d'un outil de pilotage fiable :
centralisation des données, indicateurs définis sans ambiguïté, visualisation des performances, suivi des
retards et des financements, et assistant IA qui ne répond qu'à partir des données réelles. Le projet met en
œuvre des compétences en développement web, Business Intelligence, analyse de données, bases de données et
intelligence artificielle générative.

**Fin du cahier des charges – CIAT VISION – ISEP Amadou Trawaré de Diamniadio**
