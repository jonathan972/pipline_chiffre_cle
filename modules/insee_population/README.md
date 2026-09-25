# Module INSEE — Population

Source cible : **API Melodi**, jeu `DS_POPULATIONS_REFERENCE`, mesure `PMUN` (population municipale).

La population municipale est utilisée pour les ratios statistiques car elle évite les doubles comptes. Le module conserve séparément :
- le millésime de population officiel ;
- l'année de l'indicateur eau ;
- un statut explicite lorsque la dernière population officielle disponible est utilisée faute de millésime N.

## Exécution locale

```bash
python insee_population_etl.py --start-year 2019 --end-year 2024
```

## Mise à jour annuelle via Melodi

```bash
python insee_population_etl.py --refresh --start-year 2019 --end-year 2025
```

`--refresh` récupère le dernier millésime disponible pour la Martinique et les trois EPCI. Tant que la population N n'est pas publiée, `latest_official` conserve le dernier millésime officiel dans la table résolue, avec le statut `DERNIERE_OFFICIELLE_DISPONIBLE`.

## Contrôles

- somme CACEM + CAESM + CAP Nord = Martinique ;
- contrôle du millésime utilisé ;
- validation 2022 : 21 041 846 m³ / 361 019 habitants / 365 = 159,68 L/j/hab, arrondi à 160 L/j/hab.
