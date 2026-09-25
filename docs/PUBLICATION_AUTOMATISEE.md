# Vision — publication automatisée des Chiffres clés

## Objectif

Transformer le pipeline de données en chaîne complète de production annuelle du rapport **« Les chiffres clés de l'eau potable et de l'assainissement en Martinique »**.

Le système cible doit, pour un millésime N :

1. récupérer les sources automatisables ;
2. signaler les documents locaux requis et permettre leur dépôt ;
3. calculer et certifier les indicateurs ;
4. générer les graphiques ;
5. actualiser les données SIG et produire les cartes ;
6. injecter valeurs et assets dans un template Word ;
7. générer DOCX, PDF et manifeste de traçabilité.

## Livrables métier prioritaires

- reproduction du rapport 2022 comme test étalon ;
- rapport + cartes 2023 ;
- rapport + cartes 2024.

La réussite sur 2022 prouve que la chaîne de publication peut reconstituer un rapport connu à partir des données. Les millésimes 2023 et 2024 deviennent ensuite les premières productions réelles de l'application.

## Chaîne cible

```text
Sources automatiques             Documents locaux
INSEE / BNPE / ARS / ERU         RAD / RPQS / inventaires / fichiers
          \                         /
           \                       /
            collecte + normalisation
                      |
                      v
             référentiel certifié
                      |
          +-----------+-----------+
          |           |           |
      graphiques   données SIG  textes dynamiques
          |           |           |
          +-----------+-----------+
                      |
                template DOCX
                      |
                  DOCX + PDF
                      |
                 run_manifest
```

## Principes

- aucune absence n'est remplacée par zéro ;
- seules les valeurs autorisées par les règles de publication sont injectées ;
- une révision historique reste traçable ;
- les périmètres administratifs, contractuels et hydrauliques restent distincts ;
- les graphiques et cartes doivent être reproductibles à partir d'une source versionnée ;
- le rapport généré doit conserver la référence des sources et du millésime ;
- les éléments éditoriaux stables restent dans le template ;
- les commentaires dépendant des données doivent progressivement devenir des textes dynamiques contrôlés.

## Répartition des responsabilités

### Pipeline de données

Produit `fact_indicateur_master_YYYY.csv`, le rapport qualité et la certification.

### Reporting

Transforme les indicateurs certifiés en valeurs formatées, tableaux, graphiques, textes et assets Word.

### SIG

Transforme les données géographiques du millésime en cartes exportées selon une mise en page stable.

### Application desktop

Orchestre les étapes et guide un utilisateur non développeur : collecte, dépôts manuels, validation, cartographie, génération du rapport.

## Critère final de réussite

Pour N=2023 puis N=2024, un utilisateur doit pouvoir produire le dossier annuel complet sans modifier le code :

```text
YYYY/
├── donnees/
├── controle_qualite/
├── graphiques/
├── cartes/
├── Chiffres_cles_YYYY.docx
├── Chiffres_cles_YYYY.pdf
└── run_manifest.json
```
