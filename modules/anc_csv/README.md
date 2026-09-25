# Module ANC — CSV métier ODE

## Rôle

Ce module normalisera les fichiers CSV ANC utilisés comme source métier de référence pour les rapports annuels « Chiffres clés ».

Les CSV bruts sont prioritaires pour les indicateurs ANC. Les RPQS/RAD SPANC servent de contrôle, d'explication et de complément. SISPEA est une source secondaire/de secours et ne doit pas écraser une valeur issue du CSV métier.

## Organisation cible

```text
modules/anc_csv/
├── input/
│   ├── 2023/
│   └── 2024/
├── outputs/
│   ├── 2023/fact_anc_csv_2023.csv
│   └── 2024/fact_anc_csv_2024.csv
├── anc_csv_etl.py
└── README.md
```

## Sortie canonique

La sortie normalisée conservera au minimum :

- `annee_reference`
- `indicator_id`
- `territoire`
- `perimeter_id`
- `value`
- `unit`
- `numerator`
- `denominator`
- `source_file`
- `source_detail`
- `coverage_status`
- `quality_status`
- `record_role`
- `definition`
- `note`

## Mapping

Le mapping exact des colonnes des CSV bruts vers `ANC_001` à `ANC_015` sera établi après analyse des fichiers réels. Aucun nom de champ ni aucune formule n'est inventé avant cette analyse.

Règle déjà figée : `P301.3` n'est pas calculé lorsque `D302.0 < 100` ; dans ce cas la valeur reste nulle avec `NOT_CALCULABLE` / `NOT_APPLICABLE`.
