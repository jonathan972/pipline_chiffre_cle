# ETL STEU Martinique — prototype v1

Ce module transforme un export CSV du **Portail national de l'assainissement collectif** en tables normalisées prêtes à être chargées dans PostgreSQL/PostGIS et produit une validation automatique contre le rapport ODE 2022.

## 1. Exécution sur le fichier fourni

```bash
python steu_etl.py \
  --input "/mnt/data/export-as-telechargement(2).csv" \
  --out outputs \
  --config config.json \
  --reference reference_ode_2022.json
```

L'année de référence est déduite des colonnes dynamiques telles que `Etat du STEU en 2022`. On peut la forcer avec `--year 2022`.

## 2. Sorties

- `raw_normalized_steu_2022.csv` : copie normalisée des 111 champs de la source, sans perte d'information.
- `dim_steu.csv` : identité et géographie des stations.
- `fact_steu_2022.csv` : mesures, capacités, filières, conformité, boues, masse d'eau et rejet.
- `fact_agglo_2022.csv` : une ligne par agglomération d'assainissement.
- `data_quality_issues_2022.csv` : anomalies détectées, sans correction silencieuse.
- `validation_rapport_2022.csv` : comparaison pipeline / chiffres ODE.
- `summary_2022.json` : synthèse de l'import et empreinte SHA-256 du fichier source.

## 3. Règles métier du prototype

### Parc public

La source distingue `Nature du STEU = Urbain` et `Privé`. Pour reproduire l'inventaire public du rapport, le prototype considère une station publique comme :

- `Nature du STEU = Urbain` ;
- capacité nominale strictement positive.

Ce filtre retrouve 103 stations sur le fichier fourni.

### Seuil de taille

Le rapport écrit « plus de 200 EH ». Le prototype applique donc strictement :

```text
capacite_nominale_eh > 200
```

Il calcule également le diagnostic `>= 200 EH` dans le JSON de synthèse, afin d'identifier les écarts liés au seuil.

### Conformité

La source contient des conformités à deux niveaux. Elles sont conservées séparément :

- agglomération : équipement, performance, collecte temps sec, globale ;
- STEU : équipement ERU, performance globale ERU.

Le champ `conformite_station_reconstituee` est un calcul **expérimental** :

```text
collecte agglo = Oui
AND équipement STEU = Oui
AND performance STEU = Oui
```

Il ne remplace pas le statut réglementaire source et sert uniquement à tester la définition employée dans le rapport.

### Boues

Le champ `Prod boues sans réactif (tMS/an)` est importé tel quel. Le total actuel ne reproduit pas le total du rapport 2022 : la source doit donc être utilisée comme contrôle ou enrichissement, tandis que SISPEA/RPQS-RAD restera la source prioritaire pour l'indicateur annuel de boues.

## 4. Robustesse

Le script :

- vérifie le nombre de colonnes de chaque ligne ;
- supporte des en-têtes d'année dynamiques ;
- traite `0000-00-00` comme anomalie, pas comme date valide ;
- ne remplace jamais une valeur manquante par zéro, sauf dans les agrégations explicitement documentées ;
- détecte les codes STEU dupliqués ;
- archive une empreinte SHA-256 de la source ;
- externalise les chiffres ODE 2022 dans `reference_ode_2022.json` afin de garder le code générique.

## 5. PostgreSQL/PostGIS

`sql/01_schema.sql` fournit le schéma minimal :

- `ode_ref.dim_steu`
- `ode_fact.fact_steu`
- `ode_fact.fact_agglo_assainissement`
- `ode_etl.data_quality_issue`

Le chargement direct PostgreSQL sera ajouté lorsque le modèle global SISPEA + BNPE + STEU aura été validé.

## 6. Points restant à trancher avant industrialisation

1. Définition exacte du parc « STEU publiques > 200 EH » utilisé dans le rapport 2022 : le snapshot actuel ne retrouve pas exactement 68 stations.
2. Définition exacte de la conformité du graphique ODE p.20/p.21 : les statuts actuels ont été révisés après 2022.
3. Source prioritaire des boues : la colonne du portail ne restitue pas les 1 622 tMS du rapport.
4. Exhaustivité des STEU privées : l'export fourni est très inférieur aux 177 stations privées indiquées dans le rapport.

Ces écarts sont volontairement conservés comme contrôles qualité et ne doivent pas être « corrigés » dans le code pour coller au PDF.
