# Instructions pour une IA / un agent de génération

Ce dossier est conçu pour qu'une autre IA puisse reproduire le livrable sans réinventer la méthode.

## Mission

À partir d'un territoire, d'une année de facture type, d'un CARE et d'une balance M49 :

1. produire les tables normalisées décrites dans `docs/DICTIONNAIRE_DONNEES.md` ;
2. exécuter les contrôles de `docs/CONTROLES_QUALITE.md` ;
3. générer un classeur Excel conforme à `docs/MISE_EN_FORME.md` ;
4. rédiger un texte grand public conforme à `docs/METHODOLOGIE.md` ;
5. conserver les sources, hypothèses et années dans l'onglet de détail.

## Ordre d'analyse obligatoire

### Niveau 1 — Facture

Construire un total **additif** qui somme exactement au TTC de la facture de référence :

- délégataire hors TVA ;
- collectivité hors TVA ;
- redevances ;
- taxes hors TVA (ex. octroi de mer) ;
- TVA.

Ne jamais regrouper taxes et redevances.

### Niveau 2 — CARE

Le CARE est l'économie du contrat du délégataire, pas le budget de la collectivité.

- reprendre le total des produits ;
- reprendre les montants « collectivités et autres organismes publics » ;
- isoler les charges hors reversements publics ;
- reprendre le résultat avant impôt ;
- agréger les postes de coûts dans des catégories lisibles sans inventer de données.

Vérifier :

`total_produits - reversements_publics - charges_hors_reversements ≈ resultat_avant_impot`.

### Niveau 3 — M49

Utiliser les mouvements budgétaires de l'exercice (`obnetdeb` / `obnetcre`) et non les seuls soldes de fin d'année.

Pour les dépenses de fonctionnement : classes 60 à 68.
Pour l'investissement : classes 20, 21 et 23.
Pour les ressources : classes 70, 75, 77, 13 et crédits de classe 16.
Pour le remboursement du capital : débits de classe 16.

Le mapping canonique est dans `config/m49_mapping.csv`.

## Mise en forme à reproduire

- titre bleu foncé `#123B5D`, blanc, gras ;
- titres de section bleu clair `#DCEAF5` ;
- en-têtes de tableaux `#4F81BD` ;
- notes méthodologiques jaune pâle `#FFF2CC` ;
- KPI vert pâle `#E2F0D9` ;
- montants en euros avec 2 décimales pour la facture/M49, sans décimales pour grands totaux CARE ;
- pourcentages à 1 décimale ;
- graphiques en camembert, légende à droite ;
- graphiques placés à droite des tables, jamais par-dessus les données.

## Feuilles du livrable

1. `0_Parcours`
2. `1_Facture_<année>`
3. `2_CARE_<délégataire>_<année>`
4. `3_Budget_<collectivité>_<année>`
5. `4_Detail_sources`
6. `5_Texte_public`

## Cas de millésimes différents

Ne pas masquer le décalage. Ajouter un encadré :

> Les graphiques se suivent pour expliquer les mécanismes, mais ne constituent pas une réconciliation comptable euro pour euro lorsque les sources ne portent pas sur le même millésime.

## Interdictions

- ne pas interpréter la part délégataire comme du bénéfice ;
- ne pas déduire une causalité à partir d'une simple corrélation ;
- ne pas inventer la destination d'un compte M49 ambigu ;
- ne pas confondre encours/dette de bilan avec flux d'emprunt de l'exercice ;
- ne pas qualifier une recette exceptionnelle de récurrente.
