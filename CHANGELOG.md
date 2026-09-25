# Changelog

## 1.1.0 — 2026-09-25

- moteur de publication `modules/reporting/` : rapport Word depuis le master canonique, avec ou sans template, tableaux par domaine et par EPCI, évolution N-1, graphiques, cartes, textes dynamiques, absences et limites, traçabilité SHA-256 ;
- préflight détaillé (`preflight_report_YYYY.csv`) ; le mode final ne produit aucun document tant qu'un élément requis manque ou n'est pas validé ;
- valeurs complémentaires : import fusionné dans `saisie/saisie_locale_YYYY.csv`, lu par le pipeline ; seules les lignes `validated=oui` sont publiées ;
- gabarit des valeurs manquantes généré au format de saisie, avec les périmètres canoniques ;
- application : résumé lisible après génération ; extraction RAD/RPQS exécutée dans le processus (l'EXE ne se relance plus lui-même) ;
- build Windows : dépendances des scripts chargés dynamiquement déclarées pour PyInstaller ;
- `.gitignore` : `outputs/` ne masque plus les sorties des modules (`modules/*/outputs/`) ; `publication/` ignoré ;
- tests `tests/test_reporting.py` et import des valeurs complémentaires ;
- les tests n'exigent plus les PDF RAD/RPQS : ils vérifient que chaque source est extraite et tracée par son SHA-256.

## Socle de données — 2026-09-25 (branche refonte-socle-donnees)

- nomenclature canonique unique : `referentiel/indicateurs.csv` (80 indicateurs + variables support) et table `correspondance_codes.csv` ; un code source non mappé est bloquant ;
- master unique `pipeline/` paramétré par année, remplaçant `master_pipeline.py`, `_v2`, `_v3` et l'orchestrateur qui choisissait le premier fichier présent ;
- matrice des attentes `referentiel/attentes.csv` (indicateur × périmètre × période), initialisée depuis la validation 2022 ;
- nouvelle certification contre les attentes : une année vide est `NOT_CERTIFIED`, chaque indicateur reçoit un statut explicite ;
- réagrégation hors ligne des résultats ARS 2022–2024 avec le rattachement communes → EPCI de `epci_communes.csv` (`--from-samples`) ;
- `update_observatoire.py` appelle désormais le nouveau pipeline ;
- tests `tests/test_pipeline.py` (année vide, exhaustivité des 80 indicateurs, nomenclature, conflits, régénération de valeurs 2022, absence de codes communes en dur).
- frontière de publication `pipeline/publication.py` : seules les lignes `PRODUCTION` sont exposées au reporting ;
- application desktop alignée sur le chemin du master canonique, sans repli sur v1/v2/v3 ;
- validation au chargement du référentiel (attentes, identifiants, périmètres, doublons et périodes).

## 1.0.0 — 2026-09-25

- ajout de l'application desktop guidée pour les millésimes 2023/2024 ;
- ajout du moteur de publication Word avec préflight bloquant en mode final ;
- intégration ARS/Hub'Eau, portail assainissement, RAD/RPQS, périmètres CAP Nord / Ex-SICSM ;
- ajout des imports de valeurs complémentaires auditées ;
- ajout du dépôt manuel des quatre cartes tant que le chantier MXD/SIG est différé ;
- ajout des tests de non-régression et du workflow Windows/PyInstaller ;
- ajout d'un corpus `resources/` avec manifestes SHA-256 pour faciliter l'audit et la reprise IA ;
- correction de la cartographie commune→EPCI du module ARS : le rattachement est lu depuis `modules/perimeters/epci_communes.csv` ;
- les anciens agrégats ARS par EPCI produits avant cette correction doivent être réagrégés depuis les fichiers `fact_ars_samples_YYYY.csv` ou retéléchargés.

## Historique

Les versions précédentes ont construit progressivement le dictionnaire des 80 indicateurs, les modules SISPEA/BNPE/STEU/INSEE/RAD-RPQS, le référentiel des périmètres contractuels et la certification 2022–2024.
