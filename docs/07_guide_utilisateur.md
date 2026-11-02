# Guide utilisateur – CIAT VISION

*Le pilotage intelligent de l'innovation par la donnée.*

## 1. Se connecter

1. Ouvrir l'adresse de la plateforme.
2. Saisir l'identifiant et le mot de passe, puis **Se connecter**.
3. Après 5 échecs consécutifs, le compte est bloqué 15 minutes.
4. La session dure 60 minutes ; elle est prolongée automatiquement tant que vous utilisez l'application.
5. **Se déconnecter** : bouton en haut à droite. **Mon profil** : clic sur votre nom (modifier vos informations,
   changer votre mot de passe).

> Le bandeau jaune **« Données simulées – non officielles »** signale que les chiffres proviennent du jeu de
> démonstration. Il disparaît lorsque les données réelles du CIAT ont été chargées.

## 2. Ce que chaque profil peut faire

| | Analyste | Coordonnateur | Administrateur |
|---|:-:|:-:|:-:|
| Consulter tableau de bord, analyses, projets, cohortes, financements | ✅ | ✅ | ✅ |
| Interroger CIAT AI Analyst, générer des rapports | ✅ | ✅ | ✅ |
| Voir l'e-mail et le téléphone des porteurs | ❌ | ✅ | ✅ |
| Créer, modifier, supprimer projets, cohortes, financements | ❌ | ✅ | ✅ |
| Importer des fichiers | ❌ | ✅ | ✅ |
| Gérer les comptes, les paramètres, consulter le journal, purger les données simulées | ❌ | ❌ | ✅ |

## 3. Filtrer les données

La barre de filtres (période de dépôt, cohorte, domaine, statut) est commune au tableau de bord, aux analyses,
aux projets, aux financements et aux rapports : un filtre choisi sur une page reste actif sur les autres.
**Réinitialiser** supprime tous les filtres. Sur téléphone, touchez **Filtres** pour les afficher.

## 4. Tableau de bord

- **8 indicateurs** : total des projets, candidatures, sélectionnés, en incubation, prototypes, terminés, en retard,
  financements reçus. Survolez une carte pour lire sa définition ; cliquez pour ouvrir la liste des projets concernés.
- **4 taux** : sélection, achèvement, retard, progression moyenne.
- Graphiques : évolution mensuelle des candidatures, répartition par statut.
- **Projets en retard** : les plus en retard d'abord (cliquez pour ouvrir la fiche).

**Qu'est-ce qu'un projet en retard ?** Un projet actif dont la date limite est dépassée, ou dont un jalon n'a pas
été atteint à sa date prévue (au-delà du seuil de tolérance fixé par l'administrateur). Un projet suspendu n'est
jamais compté en retard.

## 5. Gérer les projets (coordonnateur, administrateur)

**Créer** : Projets → **Nouveau projet** → nom, domaine, cohorte, budget, date limite, porteur (nouveau ou
existant). Le projet démarre au statut **En attente**.

**Faire avancer un projet** (fiche projet → **Changer le statut**) — seules les étapes autorisées sont proposées :
```
En attente → En évaluation → Sélectionné → En incubation → En développement → Prototype réalisé → Terminé
                           ↘ Non retenu          (En incubation / développement / prototype) ⇄ Suspendu
```
- Ajouter au moins une **évaluation** (note sur 20) avant de sélectionner ou de refuser une candidature.
- Au passage **En incubation**, 5 jalons sont créés automatiquement ; marquez-les **Atteint** au fur et à mesure.
- **Progression** : curseur de 0 à 100 % ; une baisse doit être justifiée. « Terminé » fixe la progression à 100 %.
- **Supprimer** : le projet est archivé (l'administrateur peut le restaurer).

## 6. Cohortes

Cochez les cohortes à comparer : tableau (projets, terminés, en retard, taux de réussite, sélection, progression,
financement moyen) et graphiques. **Détail** affiche les projets et activités d'une cohorte.
**Nouvelle cohorte** / crayon : créer ou modifier.

## 7. Financements

Six indicateurs : budget prévisionnel, demandé, accordé, reçu, **reste à recevoir** (accordé − reçu) et **besoin non
couvert** (budget − accordé). **Enregistrer un financement** : la plateforme refuse un montant reçu supérieur à
l'accordé, ou un statut incohérent avec les montants (ex. « Reçu » alors que rien n'a été versé).

## 8. CIAT AI Analyst

Posez une question en français, par exemple : *« Quelle cohorte présente les meilleurs résultats ? »*,
*« Quels projets nécessitent une attention particulière ? »*.
- La réponse indique les chiffres utilisés et ses limites.
- **Données utilisées** (dépliable) : fonction d'analyse appelée et résultats bruts, pour vérifier chaque chiffre.
- L'assistant ne voit jamais les noms ni les coordonnées des porteurs et n'invente pas de statistiques : si une
  information n'existe pas dans la plateforme, il le dit.
- Les recommandations sont des propositions à discuter, pas des décisions.
- **Mode dégradé** (sans IA générative) : les questions sont reconnues par mots-clés et les réponses sont
  produites par des gabarits à partir des mêmes fonctions d'analyse.

## 9. Rapports

1. Choisir les filtres, puis le type de rapport (global, projets, cohortes, financements, performances, retards).
2. Facultatif : **Proposer un commentaire** (rédigé par l'IA ou généré automatiquement), le relire et le corriger.
3. Exporter en **PDF**, **Excel** ou **CSV**. Les chiffres sont identiques à ceux du tableau de bord.

## 10. Importer des données (coordonnateur, administrateur)

1. Choisir le type (cohortes, projets et porteurs, financements) et télécharger le **modèle** (Excel ou CSV).
   L'onglet « Aide » du modèle décrit chaque colonne.
2. Déposer le fichier : la plateforme vérifie colonnes, formats, valeurs autorisées et doublons, **sans rien enregistrer**.
3. Lire la prévisualisation : lignes valides (vert), en erreur (rouge, avec le motif), doublons (jaune).
4. **Importer** puis confirmer. Seules les lignes valides sont enregistrées, en une seule opération.
Ordre conseillé : cohortes → projets → financements.

## 11. Administration (administrateur)

- **Utilisateurs** : créer un compte, changer de rôle, désactiver, réinitialiser un mot de passe.
- **Paramètres** : nom de l'institution, seuil de tolérance des retards, durée de session, activation de l'IA,
  nombre de questions par jour.
- **Journal d'activité** : connexions, modifications, exports, imports, filtrable par action.
- **Données** : purge des données simulées (saisir `PURGER`), restauration des projets supprimés.

## 12. Questions fréquentes

| Question | Réponse |
|---|---|
| « Votre session a expiré » | Reconnectez-vous ; la session expire après 60 min d'inactivité. |
| Un indicateur affiche « — » | Il n'est pas calculable sur ce périmètre (division par zéro), par ex. un taux d'achèvement sans projet incubé. |
| Je ne vois pas le bouton « Nouveau projet » | Votre rôle (Analyste) ne permet pas de modifier les données. |
| L'assistant répond « mode dégradé » | Aucune clé d'IA n'est configurée sur le serveur ; les chiffres restent exacts. |
