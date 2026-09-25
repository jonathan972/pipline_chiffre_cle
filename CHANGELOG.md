# Changelog

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
