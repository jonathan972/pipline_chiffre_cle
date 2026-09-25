# Procédure annuelle

## 1. Préparer le millésime

Créer une branche `millesime-YYYY`, noter les dates de téléchargement et archiver les sources brutes hors Git si elles sont volumineuses. Ne jamais remplacer un snapshot ancien sans conserver son empreinte.

Rassembler : exports SISPEA AEP/AC/ANC, BNPE, portail ERU/STEU, population INSEE, RAD/RPQS reçus, absences formellement confirmées et éventuels changements de contrats/périmètres.

## 2. Mettre à jour les modules

Exécuter chaque ETL selon son README. Vérifier d'abord les périmètres, puis les faits. Pour toute source non produite, ajouter une ligne dans `modules/perimeters/known_absences.csv`. Pour tout changement de contrat, mettre à jour `service_perimeters.csv` et `service_commune_bridge.csv` avec dates de validité.

## 3. Construire le master

```powershell
py modules/master/master_pipeline_v3.py --root . --year YYYY --out modules/master/outputs_v3
```

Contrôler les volumes, les totaux EPCI, les valeurs non additives et les ruptures N/N-1. Ne pas promouvoir automatiquement une donnée `DIAGNOSTIC`.

## 4. Consolider et certifier

Hors ligne :

```powershell
py update_observatoire.py --year YYYY --strict
```

Avec rafraîchissement ARS :

```powershell
py update_observatoire.py --year YYYY --refresh-ars --strict
```

Examiner les quatre livrables, puis comparer les indicateurs sentinelles aux documents sources.

## 5. Décider la publication

- `CERTIFIED` : publiable ;
- `CERTIFIED_WITH_GAPS` : publier les valeurs validées et documenter les lacunes ;
- `NOT_CERTIFIED` : corriger ou exclure toute valeur de production bloquante avant publication.

Les lignes `AUDIT` ne sont jamais publiées comme valeurs courantes. Les lignes `DIAGNOSTIC` exigent une décision explicite.

## 6. Archiver

Versionner le code, les petits fichiers sources, les résultats, les manifestes, la certification et l'inventaire des gros snapshots. Créer un tag `millesime-YYYY` seulement après revue humaine.
