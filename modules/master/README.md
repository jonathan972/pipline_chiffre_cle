# Pipeline maître v6

Utiliser `master_pipeline_v3.py`.

Il fusionne : population INSEE, faits RAD/RPQS réconciliés par périmètre de service, et BNPE lorsque le millésime est disponible.

Chaque ligne contient désormais `perimeter_id` afin de ne pas confondre EPCI administratif, contrat, ancien syndicat et secteur infra-communal.

```bash
python master_pipeline_v3.py --root <projet> --year 2024 --out outputs_v3
```

Les absences de documents connues sont enregistrées comme `NON_PRODUIT_DECLARE`, jamais comme valeur zéro et jamais comme simple oubli de collecte.
