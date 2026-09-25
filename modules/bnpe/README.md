# Module BNPE

Import et contrôle des prélèvements en eau pour le Référentiel ODE Martinique.

## Entrées attendues

Un dossier d'export BNPE contenant au minimum :
- `prelevements.csv`
- `synthese_usage.csv`
- `synthese_type_eau.csv`
- `synthese_evolution_temporelle.csv`
- `synthese_geographique.csv`

Le détail `prelevements.csv` est la source de calcul principale ; les fichiers `synthese_*` servent de contrôles croisés.

## Exécution

```bash
python bnpe_etl.py \
  --input-dir data/raw \
  --year 2022 \
  --out outputs \
  --config config.json \
  --reference reference_ode_2022.json
```

## Principes méthodologiques

- Les volumes sont stockés au grain `année × ouvrage × usage`.
- Les parts surface/souterrain du rapport sont recalculées **uniquement sur l'AEP** à partir du détail, pas depuis `synthese_type_eau.csv` qui porte sur tous les usages.
- La part « Lézarde + Rivière Blanche » est fondée sur une liste versionnée de codes d'ouvrages dans `config.json`.
- BNPE est une source de volumes, mais **pas un inventaire exhaustif des captages**. Les nombres de captages sont à prendre dans SISPEA / ODE / ARS.
- Les versions historiques sont conservées par empreinte SHA-256 : le rapport 2022 et le snapshot BNPE téléchargé en 2026 peuvent différer sans qu'aucune valeur ne soit écrasée.
