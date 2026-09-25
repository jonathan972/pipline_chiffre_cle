# SIG — préparation de l'automatisation cartographique

## État actuel

Les cartes historiques sont dans des projets **ArcMap MXD**. Les projets ne sont pas rangés dans une structure normalisée et certains chemins de couches peuvent être cassés ou pointer vers des emplacements locaux anciens.

Le chantier SIG est volontairement différé jusqu'à ce que les MXD soient ouverts dans ArcGIS et audités avec le responsable métier.

## Ce qu'il faudra relever pour chaque MXD

- nom du projet et version ArcGIS ;
- data frames ;
- système de coordonnées ;
- ordre des couches ;
- état des sources ;
- chemin et type de chaque source ;
- requêtes de définition ;
- jointures/relations ;
- champs de symbologie ;
- type de symbologie ;
- étiquettes et expressions ;
- plages d'échelle ;
- transparence ;
- fonds ;
- éléments de mise en page ;
- titres, crédits, logos, légendes ;
- paramètres d'export ;
- scripts ou ModelBuilder éventuels ;
- Data Driven Pages éventuelles.

## Provenance métier des couches

Le propriétaire métier expliquera pour chaque couche annuelle :

- organisme producteur ;
- fichier/base source ;
- fréquence de mise à jour ;
- identifiant stable ;
- champ du millésime ;
- transformations avant cartographie ;
- jointures nécessaires ;
- saisies manuelles ;
- règle de validation.

Cette provenance doit être documentée avant toute automatisation : la carte n'est qu'une vue d'un jeu de données dont la chaîne de production doit être comprise.

## Cartes pilotes

1. `MAP_CAPTAGES_AEP` — captages et volumes prélevés ;
2. `MAP_STEU_PUBLIQUES` — parc des STEU publiques ;
3. `MAP_AC_ANC_COMMUNES` — répartition AC/ANC communale.

## Architecture cible

```text
données sources
    |
normalisation / contrôle
    |
PostgreSQL/PostGIS ou GeoPackage maître
    |
vue du millésime N
    |
projet cartographique maître
    |
layout stable
    |
export PNG/PDF
    |
placeholder Word
```

Les données métiers ne doivent pas être dupliquées dans les dossiers des projets cartographiques.

## Choix technologique à décider après audit

### ArcGIS Pro / `arcpy.mp`

À privilégier si la chaîne de production dispose durablement d'ArcGIS Pro et de la licence nécessaire. Avantage : continuité Esri et import des MXD vers APRX.

### QGIS / PyQGIS

À privilégier pour une chaîne plus portable et indépendante d'une licence ArcGIS. Une reconstruction/migration des styles et layouts sera nécessaire une fois.

### ArcMap / `arcpy.mapping`

À conserver uniquement comme source historique de compréhension. Ne pas retenir ArcMap/MXD comme cible nouvelle d'automatisation annuelle.

## Structure cible du dossier SIG

```text
sig/
├── projects/
│   ├── captages/
│   ├── steu/
│   └── ac_anc/
├── styles/
├── layouts/
├── scripts/
├── exports/
│   └── YYYY/
└── README_SIG.md
```

## Critère de réussite

Pour une année N, un script doit pouvoir sélectionner N, rafraîchir les données, appliquer la symbologie, mettre à jour titre/légende/crédits, exporter l'image avec un nom déterministe et enregistrer les sources/paramètres dans le manifeste sans modification manuelle du projet.