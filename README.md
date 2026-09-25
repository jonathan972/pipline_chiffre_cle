# Chiffres clés Eau & Assainissement — ODE Martinique

## Socle de données (branche `refonte-socle-donnees`)

Le master et la certification sont désormais construits par `pipeline/` à partir du référentiel canonique `referentiel/` :

```powershell
py update_observatoire.py --year 2024
py -m unittest tests.test_pipeline -v
```

Un seul master, des identifiants canoniques (ceux du dictionnaire des 80 indicateurs), une certification qui compare ce qui existe à ce qui est attendu. Voir [docs/SOCLE_DONNEES.md](docs/SOCLE_DONNEES.md).

`modules/master/master_pipeline*.py` et `modules/orchestrator/update_observatoire.py` sont conservés pour l'historique mais ne sont plus utilisés. L'application desktop vérifie désormais uniquement le master canonique `outputs/YYYY/fact_indicateur_master_YYYY.csv`. La génération Word est assurée par `modules/reporting/` (voir son README) : elle utilise le template Word s'il est déposé dans `resources/templates/`, sinon elle génère un document complet.

## Version 1.0.0 — application de production 2023/2024

Cette V1 assemble le référentiel d'indicateurs, les règles métier, les sources automatiques et manuelles et le moteur Word afin de produire les rapports annuels **Les chiffres clés de l'eau potable et de l'assainissement en Martinique**.

Objectifs immédiats : produire les rapports 2023 et 2024 ; le SIG automatisé est volontairement différé jusqu'à l'audit des anciens MXD. Les cartes peuvent déjà être déposées manuellement dans l'application et insérées dans le rapport.

## Lancer l'application

Sous Windows avec Python :

```powershell
py launch_app.py
```

ou double-cliquer `run_app.bat`.

Parcours utilisateur : choisir le millésime → préparer/contrôler les sources → actualiser ARS si nécessaire → déposer RAD/RPQS/CSV complémentaires → ajouter les cartes → générer un brouillon → corriger le préflight → générer la version finale.

Le mode **final** est bloqué tant qu'un placeholder obligatoire est réellement manquant ou repose seulement sur une donnée diagnostique. Une absence n'est jamais transformée en zéro.

## Sources et règles

- INSEE : population ;
- BNPE : prélèvements ;
- ARS / SISE-Eaux via Hub'Eau : microbiologie et physico-chimie ;
- portail assainissement : STEU publiques et stations privées ;
- RAD/RPQS : données locales de service et SPANC ;
- périmètres CAP Nord / Robert-Trinité / Ex-SICSM : référentiel contractuel distinct des EPCI ;
- SISPEA : contrôle/complément lorsque définition et périmètre sont validés ;
- valeurs complémentaires : CSV importé dans `saisie/saisie_locale_YYYY.csv` ; seules les lignes `validated=oui` sont publiées, et un désaccord avec une autre source est bloquant.

Absences connues 2024 : aucun bilan/RAD CACEM ; aucun RPQS ANC CAESM. Elles restent explicitement manquantes.

## Ressources d'audit

Le dossier `resources/` rassemble les fichiers transmis et les validations nécessaires pour comprendre ou reproduire le projet : PDF RAD/RPQS, exports CSV, extractions texte, dictionnaire, classeurs de validation, template Word et exemples de sortie. `resources/MANIFEST.csv` et `.json` enregistrent taille + SHA-256 de chaque fichier.

## Ligne de commande

```powershell
py generate_report.py --year 2023 --mode draft
py generate_report.py --year 2024 --mode draft
```

Le mode `final` applique les mêmes contrôles que l'interface.

## Tests

```powershell
py -m unittest discover -s tests -v
```

Ils contrôlent notamment la présence des sources normalisées, l'alignement des noms de cartes avec le template, la complétude du corpus RAD/RPQS et la génération des brouillons 2023/2024.

## Exécutable Windows

Localement : `build_windows.bat`.

Dans GitHub : le workflow **Build Windows application** exécute les tests, construit `ChiffresClesMartinique.exe`, puis publie un dossier portable contenant les modules, données, docs et ressources d'audit.

## SIG

Quatre emplacements sont déjà gérés manuellement : captages AEP, STEU publiques, part AC par commune, répartition AC/ANC. L'automatisation sera branchée après audit des MXD et normalisation des couches/sources.

## Répertoires

```text
application/                   GUI et orchestration
data/source_inbox/YYYY/        dépôts annuels utilisateur
modules/ars_quality/           Hub'Eau / ARS
modules/assainissement_portal/ STEU publiques + privées
modules/local_reports/         RAD/RPQS
modules/reporting/             moteur Word, graphiques, préflight
resources/                     corpus d'audit/reproduction
publication/YYYY/              sorties DOCX/PDF et préflights
tests/                         tests de non-régression
```
