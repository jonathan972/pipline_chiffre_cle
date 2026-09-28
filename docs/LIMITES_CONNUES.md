# Limites connues et priorités

## Priorité 1 — Captages et PPC

`RES_007/008/009` ne peuvent pas être certifiés automatiquement avec la BNPE seule. Construire un référentiel patrimonial ODE–ARS des captages, de leur type (prise en rivière, source, forage) et de leur protection. C'est la lacune répétitive principale.

## Priorité 2 — Tarifs

Le module `modules/sispea_tariffs/` importe les exports tarifaires officiels,
filtre les lignes de Martinique et pondère `D102.0`/`D204.0` par
`D101.0`/`D201.0`. Les prix et montants 2023 confirmés sont en PRODUCTION.
Les données 2024 restent en VALIDATION car SISPEA les marque « Publié non
vérifié ». Les décompositions `TAR_004` et `TAR_008` restent également en
VALIDATION jusqu'à certification du mapping des redevances ODE et de l'ODM.

## Priorité 3 — Patrimoine local

Réservoirs, stockage, postes de refoulement, matériaux, ANC communal/privé et inventaire STEU privé nécessitent encore des sources locales et des contrôles humains.

## ARS

La collecte Hub'Eau est opérationnelle, mais l'agrégation doit encore être comparée systématiquement à `P101.1/P102.1`, aux RPQS/RAD et aux publications ARS avant passage en production.

## Orchestration

La commande V1/v8 consolide les masters présents et peut rafraîchir l'ARS. Elle ne déclenche pas encore automatiquement tous les collecteurs SISPEA, BNPE, INSEE, ERU et l'ingestion documentaire. Un nouveau millésime sans master préparé serait incomplet ; utiliser `--strict` et suivre la procédure annuelle.

## Définitions et séries

- la conformité ERU change de définition à partir de 2023 ;
- les snapshots SISPEA historiques peuvent être révisés ;
- les populations officielles ont un décalage de publication ;
- les rendements et indices linéaires ne sont pas additionnables ;
- la donnée STEU privée est incomplète ;
- les boues du portail ERU ne reproduisent pas seules le rapport 2022.

## Déploiement

Le schéma PostgreSQL/PostGIS est prêt, mais le chargement et les vues QGIS/Excel/WordPress restent à industrialiser. La source de vérité courante est le CSV certifié et son manifeste.
