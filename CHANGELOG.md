# Changelog

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
