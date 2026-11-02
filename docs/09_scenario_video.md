# Scénario de la vidéo de démonstration (livrable 9)

**Durée cible : 7 à 8 minutes.** Enregistrement d'écran (par ex. OBS Studio ou la Barre de jeux Windows `Win + G`)
en 1 920 × 1 080, micro activé. Avant l'enregistrement : ouvrir l'application (et la « réveiller » si elle est
hébergée gratuitement), fermer les autres onglets, utiliser le fichier `docs/exemples/exemple_import_projets.xlsx` (modèle complété avec
une ligne valide, une ligne avec une date invalide et un doublon).

| Temps | Écran | Action | Commentaire à dire |
|---|---|---|---|
| 0:00 | Connexion | Afficher la page | « CIAT VISION est la plateforme de pilotage du Centre d'Innovation, d'Application et de Transfert de l'ISEP Amadou Trawaré. Toutes les données présentées sont simulées. » |
| 0:20 | Connexion | Se connecter en `analyste` | « Trois profils existent. Je commence par l'analyste, qui peut consulter mais pas modifier. » |
| 0:35 | Tableau de bord | Montrer les 8 indicateurs, survoler « Projets en retard » | « Chaque indicateur est calculé par le serveur à partir de PostgreSQL ; sa définition s'affiche au survol. » |
| 1:00 | Tableau de bord | Filtrer sur une cohorte | « Les filtres mettent à jour indicateurs et graphiques ensemble. » |
| 1:20 | Fiche projet | Ouvrir un projet en retard | « Le retard est expliqué : jalon manqué. Les coordonnées du porteur sont masquées pour l'analyste. » |
| 1:40 | Analyses | Défiler | « Les neuf analyses demandées, toutes interactives. » |
| 2:10 | Assistant | Poser « Quelle cohorte présente les meilleurs résultats ? » puis déplier « Données utilisées » | « L'IA n'exécute aucune requête SQL : elle choisit parmi sept fonctions d'analyse autorisées. Chaque chiffre est vérifiable ici. » |
| 2:50 | Assistant | Poser « Quel est le chiffre d'affaires des projets ? » | « Une information absente de la base est signalée, jamais inventée. » |
| 3:10 | Connexion | Se déconnecter, se connecter en `coordo` | |
| 3:20 | Projets | Créer un projet | « Le projet démarre en attente. » |
| 3:45 | Fiche projet | Tenter « Sélectionné » sans évaluation → erreur ; ajouter une évaluation ; sélectionner ; passer en incubation | « Les règles de gestion sont appliquées : évaluation obligatoire, jalons créés automatiquement. » |
| 4:30 | Financements | Saisir un montant reçu supérieur à l'accordé → refus ; corriger | « Les incohérences financières sont refusées, jusque dans la base de données. » |
| 5:00 | Rapports | Rapport global → « Proposer un commentaire » → modifier une phrase → PDF ; ouvrir le PDF | « Le PDF contient le logo, la période, les indicateurs, les graphiques et le commentaire relu. » |
| 5:50 | Importation | Déposer `docs/exemples/exemple_import_projets.xlsx` | « La prévisualisation signale la date invalide et le doublon ; rien n'est enregistré avant confirmation. » |
| 6:20 | Importation | Importer la ligne valide | |
| 6:35 | Connexion | Se connecter en `admin` → Administration → Journal | « Toutes les actions précédentes sont tracées. » |
| 6:55 | Administration → Données | Montrer (sans l'exécuter) la purge | « Pour passer aux données réelles : purge des données simulées, puis importation. » |
| 7:10 | Téléphone | Outils de développement du navigateur, mode téléphone, tableau de bord et menu | « L'interface s'adapte au téléphone. » |
| 7:30 | — | Conclusion | « CIAT VISION : des indicateurs fiables, une IA encadrée, des données protégées. » |
