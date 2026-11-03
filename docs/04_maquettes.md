# Phase 4 – Maquettes des interfaces (ordinateur et téléphone)

**Objectif de la phase :** définir l'organisation de chaque écran, la navigation et l'adaptation au téléphone,
dans le respect de la charte (§ 9 du cahier des charges).

Les maquettes ci-dessous sont **haute fidélité** : ce sont des captures de l'application réelle, prises
automatiquement (Playwright + Microsoft Edge) à 1 440 px (ordinateur) et 390 px (téléphone), sur les données
simulées. Elles garantissent que ce qui est présenté au jury correspond exactement à ce qui fonctionne.

## 1. Principes de conception

| Principe | Application |
|---|---|
| Navigation | Barre latérale marron (`#4C311F`) repliable sur ordinateur ; menu coulissant sur téléphone |
| Hiérarchie | Titre de page → filtres → indicateurs (cartes) → graphiques → tableaux |
| Cartes | Fond blanc, coins arrondis 8 px, ombre discrète, liseré gauche marron (alerte : orange) |
| Couleurs | Une seule couleur (marron) pour une série ; couleur **fixe par statut** dans tous les graphiques |
| Contraste | Boutons beige à texte marron profond (5,9 : 1) ; jamais de texte blanc sur beige (2,5 : 1) |
| Typographie | Inter ; chiffres tabulaires pour l'alignement des montants |
| Responsive | Grilles 4 → 2 colonnes, tableaux transformés en cartes, filtres repliables sur téléphone |
| Retours | Notifications (succès / erreur), indicateurs de chargement, états vides explicites |
| Transparence | Bandeau « Données simulées » sur toutes les pages tant que la base en contient |
| Accessibilité | Libellés sur tous les champs, navigation clavier, définition des KPI au survol et pour les lecteurs d'écran |

## 2. Logo

Le **logo officiel CIAT VISION** fourni par le réalisateur est utilisé sans aucune déformation ni recoloration.
Son fond blanc a été rendu **transparent** (bords adoucis conservés, sans liseré) et le trait vertical qui séparait
l'emblème du texte a été retiré, à la demande du réalisateur ; les trois versions sont de simples
recadrages, proportions conservées. Original : `docs/logo/ciat_vision_logo_original.png` ; version transparente :
`docs/logo/ciat_vision_logo_transparent.png` ; préparation reproductible : `scripts/preparer_logo.py`.

| Version | Fichier | Usage |
|---|---|---|
| Horizontale (emblème + « CIAT VISION ») | `frontend/public/logo/logo-horizontal.png` | Barre latérale, menu mobile, panneau de la page de connexion |
| Compacte (emblème seul) | `frontend/public/logo/logo-compact.png`, `favicon.png` | Barre latérale repliée, en-tête téléphone, icône d'onglet |
| Complète (avec « ISEP AMADOU TRAWARÉ ») | `frontend/public/logo/logo-complet.png` | Formulaire de connexion |
| PDF | `backend/app/assets/logo.png` | En-tête de tous les rapports PDF |

Le logo étant conçu pour un fond clair (texte « CIAT » marron foncé), il est toujours posé sur une **surface
claire** : la zone du logo en haut de la barre latérale est blanche et prolonge la barre supérieure, et l'en-tête des
rapports PDF est blanc, souligné de deux filets marron et beige.

## 3. Écrans

| N° | Écran | Ordinateur | Téléphone |
|---|---|---|---|
| 1 | Connexion | ![](maquettes/01_connexion_ordinateur.png) | ![](maquettes/01_connexion_telephone.png) |
| 2 | Tableau de bord | ![](maquettes/02_tableau_de_bord_ordinateur.png) | ![](maquettes/02_tableau_de_bord_telephone.png) |
| 3 | Projets | ![](maquettes/03_projets_ordinateur.png) | ![](maquettes/03_projets_telephone.png) |
| 4 | Fiche projet | ![](maquettes/04_fiche_projet_ordinateur.png) | ![](maquettes/04_fiche_projet_telephone.png) |
| 5 | Analyses | ![](maquettes/05_analyses_ordinateur.png) | ![](maquettes/05_analyses_telephone.png) |
| 6 | Cohortes | ![](maquettes/06_cohortes_ordinateur.png) | ![](maquettes/06_cohortes_telephone.png) |
| 7 | Financements | ![](maquettes/07_financements_ordinateur.png) | ![](maquettes/07_financements_telephone.png) |
| 8 | CIAT AI Analyst | ![](maquettes/08_assistant_ordinateur.png) | ![](maquettes/08_assistant_telephone.png) |
| 9 | Rapports | ![](maquettes/09_rapports_ordinateur.png) | ![](maquettes/09_rapports_telephone.png) |
| 10 | Importation | ![](maquettes/10_importation_ordinateur.png) | ![](maquettes/10_importation_telephone.png) |
| 11 | Administration | ![](maquettes/11_administration_ordinateur.png) | ![](maquettes/11_administration_telephone.png) |
| 12 | Menu (téléphone) | — | ![](maquettes/12_menu_telephone.png) |

## 4. Description des écrans

1. **Connexion** – panneau institutionnel (slogan, logo) et formulaire ; affichage du mot de passe ; messages d'erreur
   explicites ; comptes de démonstration repliés.
2. **Tableau de bord** – filtres (période, cohorte, domaine, statut) ; 8 indicateurs cliquables (ouvrent la liste
   des projets correspondants) ; 4 taux ; évolution mensuelle des candidatures ; anneau des statuts ; projets en retard.
3. **Projets** – recherche plein texte, filtre « en retard », tri, pagination ; tableau sur ordinateur, cartes sur
   téléphone ; création par formulaire validé.
4. **Fiche projet** – statut, retard, actions (statut selon les transitions autorisées, progression, modification,
   suppression) ; financement (budget, demandé, accordé, reçu, reste, besoin non couvert) ; jalons (marquer atteint) ;
   candidature et évaluations ; historique des statuts.
5. **Analyses** – les 9 analyses du prompt + financements par domaine/source et projets terminés par domaine.
6. **Cohortes** – sélection des cohortes à comparer, tableau comparatif, graphiques, détail par cohorte.
7. **Financements** – 6 indicateurs financiers, évolution, répartition par source, liste filtrable et modifiable.
8. **CIAT AI Analyst** – conversation, questions suggérées, détail dépliable des fonctions et chiffres utilisés,
   mode (IA ou dégradé), liste des fonctions autorisées.
9. **Rapports** – choix parmi 6 rapports, commentaire analytique proposé puis relu, export PDF / Excel / CSV.
10. **Importation** – modèles téléchargeables, dépôt par glisser-déposer, prévisualisation ligne par ligne,
    confirmation.
11. **Administration** – onglets Utilisateurs, Paramètres, Journal d'activité, Données (purge, restauration).

## 5. Vérifications automatiques réalisées lors des captures

- Aucune erreur JavaScript dans la console sur les 12 écrans, à 1 440 px et à 390 px.
- Aucun défilement horizontal de la page à 390 px (critère « responsive » du § 16.2).
