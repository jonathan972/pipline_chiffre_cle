# Pipelines maîtres historiques

Le pipeline canonique courant est désormais **`pipeline/`** à la racine du dépôt et s'exécute via :

```powershell
py update_observatoire.py --year 2024
```

Les scripts de ce dossier sont conservés uniquement pour la traçabilité et la reproduction des prototypes historiques.

| Script | Rôle historique | Sorties | Statut |
|---|---|---|---|
| `master_pipeline.py` | Millésime 2022 : SISPEA, portail ERU et `manual_inputs/` | `outputs/` | **À conserver** pour reproduire 2022 |
| `master_pipeline_v3.py` | Prototype 2023–2024 : population INSEE, RAD/RPQS réconciliés, BNPE | `outputs_v3/` | Historique / contrôle, non utilisé par la chaîne canonique |
| `master_pipeline_v2.py` | Version intermédiaire remplacée par v3 | `outputs_v2/` | **Obsolète — supprimée** |

## Règle actuelle

Aucun consommateur de production ne doit sélectionner automatiquement un fichier dans `outputs/`, `outputs_v2/` ou `outputs_v3/`.

Le seul master de production est :

```text
outputs/YYYY/fact_indicateur_master_YYYY.csv
```

Il est construit par `pipeline/master.py` à partir de la nomenclature et des attentes de `referentiel/`.

Les anciens masters restent utiles comme **snapshots de comparaison** et pour documenter la genèse des règles métier, mais ils ne constituent plus une source de publication.
