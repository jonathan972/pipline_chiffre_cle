# Roadmap — produire les rapports 2023 et 2024 avec l'application

## Stratégie générale

Ne pas développer directement contre 2023 ou 2024. Utiliser 2022 comme **jeu étalon de non-régression** puisque le rapport publié et ses valeurs sont connus.

## Phase 1 — rapport 2022 reproductible

Objectif : à partir du référentiel 2022, régénérer un rapport dont toutes les valeurs, tableaux, graphiques et emplacements de cartes correspondent à la logique du rapport publié.

Travaux :

1. stabiliser le template Word 36 pages ;
2. finaliser le mapping `indicator_id -> placeholder -> format -> page` ;
3. remplacer automatiquement les valeurs ;
4. générer les graphiques historiques à partir de N-2/N-1/N ;
5. gérer les blocs optionnels et les absences ;
6. générer des textes dynamiques simples lorsque le commentaire dépend des données ;
7. comparer le DOCX/PDF régénéré au rapport 2022 de référence.

Critère de sortie : aucun remplacement manuel nécessaire pour les valeurs certifiées.

## Phase 2 — rapport 2023

Objectif : première production réelle avec la nouvelle chaîne.

1. exécuter le pipeline 2023 ;
2. inventorier automatiquement les sources manquantes ;
3. demander les RAD/RPQS nécessaires ;
4. valider les anomalies connues (P301.3, révisions historiques, périmètres CAP Nord / Ex-SICSM) ;
5. générer les graphiques ;
6. générer ou déposer les cartes ;
7. produire DOCX/PDF ;
8. effectuer une revue métier finale.

Livrable : dossier annuel 2023 complet et reproductible.

## Phase 3 — rapport 2024

Même processus, avec prise en compte explicite des absences documentaires connues :

- CACEM : pas de bilan/RAD 2024 ;
- CAESM : pas de RPQS ANC 2024.

Ces absences doivent apparaître dans le manifeste et les règles du template. Elles ne doivent jamais devenir des zéros.

Livrable : dossier annuel 2024 complet et reproductible.

## Phase 4 — industrialisation cartographique

Après audit des MXD :

1. inventorier couches, sources, jointures, symbologie et mises en page ;
2. corriger/normaliser les chemins et identifiants ;
3. documenter l'origine métier de chaque couche ;
4. déplacer les données annuelles vers une base ou un GeoPackage/PostGIS normalisé ;
5. migrer les projets vers ArcGIS Pro ou QGIS selon la décision d'architecture ;
6. automatiser les exports par variable de millésime.

Cartes pilotes prioritaires :

- captages AEP et volumes prélevés ;
- parc des STEU publiques ;
- répartition AC/ANC par commune.

## Phase 5 — application Windows

Construire l'interface uniquement lorsque les moteurs ligne de commande sont stables.

Parcours cible :

1. choisir le millésime ;
2. lancer la collecte automatique ;
3. afficher les sources réussies/absentes ;
4. demander les documents manuels nécessaires ;
5. lancer certification ;
6. générer cartes et graphiques ;
7. afficher les contrôles restant à valider ;
8. générer le rapport.

Technologie envisagée : Python + PySide6 + PyInstaller. Le moteur SIG peut rester un composant externe détecté sur le poste de production.

## Ordre de priorité actuel

1. moteur Word 2022 reproductible ;
2. graphiques automatiques ;
3. rapport 2023 ;
4. rapport 2024 ;
5. audit et normalisation SIG ;
6. cartes automatisées ;
7. interface desktop ;
8. packaging exécutable.
