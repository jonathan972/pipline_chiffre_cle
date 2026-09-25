# Module SISPEA — ODE Martinique v2

Ce module importe les exports annuels SISPEA EP / AC / ANC et les transforme en tables auditables pour le référentiel de l'Observatoire de l'Eau.

## Nouveautés de la v2

- testée sur les **vrais exports 2022 fournis le 24/09/2026** ;
- lecture native des fichiers **ODS** et des anciens **XLS BIFF8** sans LibreOffice ;
- import de la feuille officielle **Données consolidées**, à privilégier pour les valeurs Martinique lorsqu'elle existe ;
- séparation entre **année de référence** (2022) et **date du snapshot SISPEA** (24/09/2026) ;
- contrôle de complétude des données ANC ;
- comparaison automatisée avec le rapport ODE 2022 ;
- aucune correction silencieuse d'un écart.

## Exécution

```bash
python sispea_etl_v2.py \
  --year 2022 \
  --ep data/raw/SISPEA_extraction_2022_AEP.ods \
  --ac data/raw/SISPEA_extraction_2022_AC.xls \
  --anc data/raw/SISPEA_extraction_2022_ANC.xls \
  --out outputs
```

Pour les années futures, **ODS est recommandé** pour les trois compétences. Le support XLS est conservé pour les historiques SISPEA.

## Sorties

- `dim_service_YYYY.csv`
- `fact_sispea_service_YYYY.csv`
- `fact_sispea_consolidee_YYYY.csv`
- `services_EP_YYYY.csv`
- `services_AC_YYYY.csv`
- `services_ANC_YYYY.csv`
- `validation_rapport_YYYY.csv`
- `data_quality_issues_YYYY.csv`
- `summary_YYYY.json`

## Règle de source retenue

SISPEA ne doit pas être utilisé indistinctement pour tous les chiffres du rapport.

- **SISPEA prioritaire** : abonnés, linéaires, rendement, renouvellement, boues AC, indicateurs réglementaires lorsque la complétude est suffisante.
- **ARS prioritaire** : qualité sanitaire du rapport.
- **BNPE prioritaire** : prélèvements.
- **RAD / RPQS / ODE** : certains volumes produits/facturés et patrimoine local lorsque SISPEA ne reproduit pas la définition éditoriale.
- **SPANC / ODE** : ANC lorsque des champs SISPEA sont incomplets.

## Point critique — données révisées

Les exports portent sur l'exercice 2022 mais ont été générés le **24/09/2026**. Certaines valeurs 2022 ont donc été révisées depuis la publication du rapport. Le référentiel conserve systématiquement la date du snapshot et le hash SHA-256 du fichier source.
