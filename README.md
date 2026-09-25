# Référentiel Eau & Assainissement — ODE Martinique

État sauvegardé de la **V1 opérationnelle / v8** du pipeline qui consolide les chiffres clés Eau & Assainissement de Martinique. Le dépôt contient le code, les données sources redistribuables utilisées par les prototypes, les sorties de référence 2022–2024, les règles métier et un guide de reprise conçu pour un humain ou une IA.

## Résultat actuel

- 80 indicateurs recensés dans le dictionnaire métier ;
- 21 indicateurs en classe A (automatiques validés) ;
- 32 en classe B (automatiques avec contrôle) ;
- 24 en classe C (semi-automatiques ou source locale) ;
- 3 en classe D (manuels ou de référence) ;
- 53/80, soit 66,2 %, techniquement automatisables ;
- certifications 2022, 2023 et 2024 : `CERTIFIED_WITH_GAPS`, sans anomalie bloquante de production.

| Année | Lignes | Production | Diagnostic | Audit | Gaps | Blocages |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 50 | 32 | 17 | 0 | 3 | 0 |
| 2023 | 99 | 81 | 16 | 2 | 3 | 0 |
| 2024 | 58 | 38 | 17 | 3 | 4 | 0 |

Les trois gaps 2022–2023 concernent l'inventaire patrimonial des captages (`RES_007/008/009`). Les quatre gaps 2024 sont les absences documentaires déclarées : AEP, AC et ANC CACEM, puis ANC CAESM.

## Démarrage rapide

Prérequis : Python 3.11 ou plus récent. Le cœur hors ligne utilise la bibliothèque standard. Les dépendances facultatives sont listées dans `requirements.txt`.

```powershell
py -m unittest discover -s tests -v
py update_observatoire.py --year 2024
```

La seconde commande écrit dans `modules/orchestrator/outputs/annual_2024/` :

- `fact_indicateur_master_2024.csv` ;
- `quality_report_2024.csv` ;
- `run_manifest.json` ;
- `certification_2024.json`.

Pour rafraîchir les données ARS/Hub'Eau :

```powershell
py update_observatoire.py --year 2024 --refresh-ars
```

Utiliser `--strict` pour faire échouer l'exécution si le master de base est absent. Ne pas lancer un nouveau millésime en supposant que tous les collecteurs sont orchestrés : la V1 consolide encore des masters préparés en amont.

## Architecture

```text
INSEE ─┐
SISPEA ├─> modules/master ─> modules/orchestrator ─> CSV certifié
BNPE ──┤          ^                    │
ERU ───┤          │                    └─> PostgreSQL/PostGIS (schéma prêt)
ARS ───┤     périmètres contractuels
RAD/RPQS ─────────┘
```

Les modules sont séparés par source : `sispea`, `bnpe`, `steu`, `insee_population`, `local_reports`, `perimeters`, `ars_quality`, `master` et `orchestrator`.

## Documentation de référence

- [Objectifs et architecture](docs/ARCHITECTURE.md)
- [Règles métier](docs/REGLES_METIER.md)
- [Méthodologie et sources](docs/METHODOLOGIE.md)
- [Tests et certification 2022–2024](docs/TESTS_2022_2024.md)
- [Limites connues et priorités](docs/LIMITES_CONNUES.md)
- [Procédure annuelle](docs/PROCEDURE_ANNUELLE.md)
- [Guide de reprise IA](docs/REPRISE_IA.md)
- [Inventaire des données et snapshots](docs/INVENTAIRE_DONNEES.md)

## Principe de prudence

Une valeur n'est jamais forcée pour « coller » à un rapport. Les écarts, changements de définition, révisions de source et différences de périmètre sont historisés. Une absence connue reste une absence explicite, jamais un zéro.
