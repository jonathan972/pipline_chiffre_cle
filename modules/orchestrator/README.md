# Orchestrateur annuel

Depuis la racine du projet, utiliser le point d'entrée V1/v8 :

```powershell
py update_observatoire.py --year 2024
```

Avec ARS : ajouter `--refresh-ars`. Avec contrôle d'entrée strict : ajouter `--strict`.

Sorties : référentiel maître, rapport qualité, manifeste d'exécution et `certification_YYYY.json`.

Le script interne reste disponible pour un usage avancé :

```powershell
py modules/orchestrator/update_observatoire.py --year 2024 --root . --out modules/orchestrator/outputs/2024
```
