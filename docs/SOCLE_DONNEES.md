# Socle de données — master unique et certification

Branche `refonte-socle-donnees`, 25 septembre 2026. Ce document décrit le nouveau socle qui remplace `master_pipeline*.py` et l'ancien orchestrateur.

## Commande

```powershell
py update_observatoire.py --year 2024
py -m unittest tests.test_pipeline -v
```

Sorties dans `outputs/YYYY/` (non versionnées) :

| Fichier | Contenu |
|---|---|
| `fact_indicateur_master_YYYY.csv` | Toutes les valeurs du millésime, en identifiants canoniques, avec rôle, statuts, source, fichier et page |
| `couverture_YYYY.csv` | Une ligne par cellule attendue indicateur × périmètre, avec son statut et l'explication |
| `statut_indicateurs_YYYY.csv` | Une ligne par indicateur de publication (80) |
| `anomalies_YYYY.csv` | Anomalies bloquantes et avertissements |
| `certification_YYYY.json` | Statut global |
| `run_manifest.json` | Modules lus, fichiers sources et SHA-256 |

## Le référentiel (`referentiel/`)

Tout ce qui relève d'une décision métier est dans des CSV éditables, jamais dans le code.

| Fichier | Rôle |
|---|---|
| `indicateurs.csv` | Les 80 indicateurs du dictionnaire + 15 variables support (`POP_001`, `VAR_…`). Colonne `agregation_martinique` : `SOMME_EPCI` si le total Martinique est la somme des trois EPCI |
| `correspondance_codes.csv` | Code de chaque source → identifiant canonique. Colonnes `record_role_force` / `quality_status_force` pour les décisions de rôle (ex. `RES_007` en DIAGNOSTIC). Un code absent de cette table est une anomalie **bloquante** |
| `perimetres.csv` | Périmètres canoniques et leurs alias (`CACEM` → `CACEM_EPCI`, `Martinique` → `MARTINIQUE`…) |
| `services_sispea.csv` | Service SISPEA → périmètre, avec période de validité |
| `attentes.csv` | Ce qui doit exister pour un millésime : indicateur × périmètre × période. Initialisé depuis la feuille `Validation_2022` du dictionnaire |
| `lacunes_declarees.csv` | Absences décidées au grain indicateur (année, indicateur ou `*`, périmètre ou `*`, `LACUNE` ou `NON_APPLICABLE`) |
| `parametres.json` | Paramètres : nombre de SPANC attendus dans SISPEA, rôle d'une population INSEE non millésimée, tolérance de la somme EPCI |

Les absences de documents par territoire et domaine restent dans `modules/perimeters/known_absences.csv`. Une absence CACEM rend aussi le total Martinique incalculable pour les indicateurs additifs : il devient une lacune déclarée, pas un manquant.

### Identifiants : plus de suffixes

Les anciens codes `P104.3_CONTRACT`, `P104.3_REVISED`, `D301.0_LOCAL`… mélangeaient indicateur, périmètre et statut. Ils sont maintenant exprimés ainsi :

| Ancien code | Nouveau |
|---|---|
| `P104.3_CONTRACT` (EX_SICSM) | `EP_019` + `perimeter_id=EX_SICSM_DSP_2015_2027` |
| `P104.3` 51,53 % (CAP Nord 2023, AUDIT) et `P104.3_REVISED` 53,17 % (PRODUCTION) | deux lignes `EP_019` sur `CAP_NORD_DSP_2020_2024`, l'une AUDIT, l'autre PRODUCTION |
| `EP_ABONNES`, `AC_ABONNES`, `POP_MUNICIPALE` | `EP_005`, `AC_014`, `POP_001` |
| `QUAL_MICROBIO_CONFORMITE` (ARS) et `P101.1_LOCAL` (RAD) | deux lignes `EP_003`, l'une DIAGNOSTIC (ARS), l'autre PRODUCTION (RAD) |

Le code d'origine reste dans la colonne `code_source` pour la traçabilité.

## Règles du master (`pipeline/master.py`)

1. Chaque module est lu par un adaptateur (`pipeline/sources.py`) : INSEE, BNPE, SISPEA, ERU/STEU, portail assainissement, RAD/RPQS réconciliés, ARS, entrées manuelles historiques, saisie contrôlée `saisie/saisie_locale_YYYY.csv`.
2. Toutes les lignes sont conservées. Il ne peut exister qu'**une** valeur PRODUCTION par indicateur × périmètre ; sinon `CONFLIT_PRODUCTION` (bloquant).
3. Calculs dérivés déclarés dans `RATIOS` et `SOMMES` : le résultat n'est PRODUCTION que si toutes ses entrées le sont.
4. Le total Martinique d'un indicateur additif est calculé si les trois EPCI sont présents. S'il existe déjà, la somme sert de contrôle (`INCOHERENCE_SOMME_EPCI`).

## Certification (`pipeline/certification.py`)

Chaque cellule attendue reçoit un statut : `PRODUCTION`, `LACUNE_DECLAREE`, `NON_APPLICABLE`, `A_VALIDER` (seulement DIAGNOSTIC/VALIDATION), `MANQUANT`, ou `REFERENCE_ONLY` / `REFERENCE_EXTERNE`.

- `NOT_CERTIFIED` : anomalie bloquante, cellule `A_VALIDER` ou `MANQUANT`, ou aucune valeur PRODUCTION (millésime vide) ;
- `CERTIFIED_WITH_GAPS` : tout est PRODUCTION ou explicitement déclaré ;
- `CERTIFIED` : tout est PRODUCTION.

Le moteur de publication ne doit lire que `couverture_YYYY.csv` / les lignes PRODUCTION.

## Résultat au 25 septembre 2026

| Millésime | Statut | Cellules PRODUCTION | Lacunes déclarées | À valider | Manquantes |
|---:|---|---:|---:|---:|---:|
| 2022 | NOT_CERTIFIED | 33 / 125 | 3 | 16 | 73 |
| 2023 | NOT_CERTIFIED | 44 / 125 | 3 | 8 | 70 |
| 2024 | NOT_CERTIFIED | 17 / 125 | 33 | 4 | 71 |
| année vide | NOT_CERTIFIED | 0 / 125 | 0 | 0 | 125 |

Ces chiffres ne traduisent pas une régression : l'ancienne certification ne regardait que les lignes présentes. Les manques principaux viennent de sources non encore traitées pour ces millésimes (SISPEA et ERU seulement en 2022, BNPE jusqu'en 2023, tarifs, portail assainissement, inventaires patrimoniaux) et d'indicateurs jamais collectés (EP_011 à EP_016, EP_018, AC_017, ANC_004…).

## Écarts révélés par la régénération 2022

| Indicateur | Pipeline | Rapport 2022 | Commentaire |
|---|---:|---:|---|
| EP_020 CACEM | 31,9 | 21 | Valeur SISPEA du service 196862 : à expliquer |
| AC_004 par EPCI | 17 / 25 / 27 | 15 / 28 / 25 | Snapshot ERU révisé (déjà connu) |
| AC_005 | 345 361 | 351 866 | Snapshot ERU révisé ; le rapport lui-même donne 347 911 p. 4 |
| RES_007 / 008 | 29 / 13 | 35 / 20 | BNPE non exhaustive (lacune déclarée) |
| ANC_003 / ANC_011 | 56 255 / 388 | 73 000 / 591 | SISPEA incomplet : 2 SPANC sur 3 |

## ARS

Les agrégats ARS 2022–2024 ont été réagrégés hors ligne à partir des `fact_ars_samples_YYYY.csv` avec le rattachement de `epci_communes.csv` :

```powershell
py modules/ars_quality/ars_quality_etl.py --year 2024 --out modules/ars_quality/outputs/2024 --from-samples modules/ars_quality/outputs/2024/fact_ars_samples_2024.csv
```

Le total Martinique ne change pas. Les effectifs par EPCI changent fortement (ex. 2024, CAESM : 218 → 135 prélèvements ; CAP Nord : 360 → 431).

## Ce qui n'est pas encore fait

- gabarit de saisie RAD/RPQS généré par le pipeline (l'adaptateur `saisie` lit déjà `saisie/saisie_locale_YYYY.csv`) ;
- exécution de SISPEA, ERU et BNPE pour 2023–2024 ;
- test des placeholders du template Word (le moteur `modules/reporting/` n'est pas dans le dépôt) ;
- branchement de l'application desktop sur ce socle : elle lit encore `outputs_v3/v2/v1` et doit être gelée d'ici là.
