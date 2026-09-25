# Inventaire des données et snapshots

## Contenu versionné

Le dépôt conserve les exports SISPEA 2022, les exports BNPE utilisés, les jeux d'essai ARS, les matrices et classeurs de validation, les fichiers de périmètres, les sorties normalisées et les résultats certifiés 2022–2024.

Les rapports RAD/RPQS complets utilisés lors de l'analyse initiale ne sont pas tous présents dans le miroir local. Leurs extractions structurées, la matrice de couverture et les faits vérifiés sont conservés dans `modules/local_reports/`, `modules/perimeters/` et `docs/Validation_RAD_RPQS_2023_2024.xlsx`. Pour une nouvelle vérification page à page, il faudra remettre les PDF originaux à disposition.

## Snapshots Hub'Eau non versionnés

Les JSON bruts ci-dessous sont régénérables et dupliquaient environ 355 Mo. Ils sont exclus de Git, mais leurs sorties dérivées restent versionnées.

| Fichier local historique | Octets | SHA-256 |
|---|---:|---|
| `outputs/2022/raw_hubeau_ars_2022.json` | 71 638 505 | `E9C305291FEAB6A7D480DD52232058CC60E6A0223A7B62D16B1425A8998DECD2` |
| `outputs/2023/raw_hubeau_ars_2023.json` | 69 050 667 | `2E748983B90E4281D2F18246D19D6A6106C1A476B3F2AA1F7945E3AEE11A5EBB` |
| `outputs/2024/raw_hubeau_ars_2024.json` | 71 938 063 | `23D78727B0A9266732033359B8DF35F8C8876B7634B51AC74F07938FF3D326E2` |
| `outputs/reel_2022/raw_hubeau_ars_2022.json` | 71 638 505 | identique au snapshot 2022 ci-dessus |
| `outputs/reel_2024/raw_hubeau_ars_2024.json` | 71 938 063 | identique au snapshot 2024 ci-dessus |

Pour reconstituer un snapshot courant :

```powershell
py modules/ars_quality/ars_quality_etl.py --year YYYY --out modules/ars_quality/outputs/YYYY
```

Un snapshot re-téléchargé ultérieurement peut légitimement avoir une autre empreinte : il doit être traité comme une nouvelle version de source, pas comme une reproduction binaire garantie.
