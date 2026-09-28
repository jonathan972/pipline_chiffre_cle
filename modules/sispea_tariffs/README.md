# Tarifs SISPEA

Ce module traite les fichiers tarifaires annuels publies par SISPEA. Les
classeurs nationaux (environ 60 Mo pour deux millesimes) restent hors du depot.
Seules les lignes du departement 972, leur URL officielle et l'empreinte SHA-256
du fichier national sont versionnees.

## Regles de production

- `D102.0` (eau potable) est pondere par `D101.0`.
- `D204.0` (assainissement collectif) est pondere par `D201.0`.
- un millesime n'est `PRODUCTION` que si toutes les lignes utiles sont
  completes et portent le statut SISPEA « Confirme / publie » ;
- « Publie non verifie » reste `VALIDATION` et n'alimente jamais le reporting ;
- `TAR_004` et `TAR_008` restent en `VALIDATION` jusqu'a certification du
  mapping detaille des redevances ODE et de l'ODM.

Les fichiers peuvent etre regeneres avec :

```powershell
python modules/sispea_tariffs/sispea_tariffs_etl.py extract --year 2023 --aep tarifs_AEP_2023.xls --ac tarifs_AC_2023.xls --data-dir modules/sispea_tariffs/data
python modules/sispea_tariffs/sispea_tariffs_etl.py build --year 2023
```

Source : <https://services.eaufrance.fr/pro/telechargement>
