# Règles métier

## Hiérarchie des sources

- EPCI et communes : BANATIC/INSEE ;
- périmètres contractuels et bilans hydrauliques : contrats, RAD puis RPQS ;
- indicateurs de service : SISPEA après contrôle du périmètre ;
- prélèvements et volumes par ouvrage : BNPE ;
- inventaire des captages et PPC : futur référentiel patrimonial ODE/ARS ;
- qualité de l'eau distribuée : **contrôle sanitaire ARS / SISE-Eaux via le module Hub'Eau du projet** ;
- stations privées rattachées au chapitre ANC : **exports annuels du portail assainissement DEAL/national**, complétés par les RPQS/RAD et inventaires locaux ;
- autres indicateurs ANC (population, dispositifs, contrôles SPANC, P301.3) : RPQS/RAD SPANC puis SISPEA après contrôle de couverture ;
- STEU publiques et conformité ERU : portail national, avec contrôle des définitions par millésime ;
- population : population municipale INSEE avec millésime explicite.

## Qualité AEP — règle de publication

Les indicateurs de conformité microbiologique et physico-chimique du rapport (`EP_003`, `EP_004`) sont alimentés par le programme Python `modules/ars_quality/ars_quality_etl.py`.

Pour un millésime `YYYY`, la couche reporting doit lire en priorité :

`modules/ars_quality/outputs/YYYY/fact_ars_quality_YYYY.csv`

Les identifiants canoniques produits sont :

- `QUAL_MICROBIO_CONFORMITE` ;
- `QUAL_PC_CONFORMITE`.

La valeur du rapport est sélectionnée au bon territoire (`Martinique`, `CACEM`, `CAESM`, `CAP_NORD`). Le rattachement commune → EPCI est lu dans `modules/perimeters/epci_communes.csv` et ne doit jamais être codé en dur. Les valeurs issues des RAD/RPQS ou de SISPEA sont des contrôles secondaires et ne doivent pas remplacer silencieusement la sortie ARS/Hub'Eau lorsqu'elle existe.

## ANC — règle de publication

Les exports `export-portail_assainissement_YYYY.csv` contiennent à la fois des STEU de nature `Urbain` et `Privé`. Ils ne couvrent donc **pas tout l'ANC**, mais constituent la source de référence pour le sous-bloc « stations en gestion privée » du rapport :

- `ANC_005` : nombre de stations privées ;
- `ANC_006` : capacité cumulée des stations privées ;
- `ANC_007` : capacité privée rapportée à la capacité des STEU publiques > 200 EH ;
- `ANC_008` : part des stations privées de moins de 500 EH.

Le module `modules/assainissement_portal/assainissement_portal_etl.py` normalise ces exports.

`ANC_009` (« propriétaires ayant transmis leurs données de conformité ») n'est pas considéré comme directement disponible : l'export ne contient pas un champ portant explicitement cette définition. Le module produit seulement `ANC_009_CANDIDATE` en `DIAGNOSTIC` jusqu'à validation métier.

Pour `ANC_001` à `ANC_004` et `ANC_010` à `ANC_013`, utiliser les RPQS/RAD SPANC comme source principale, puis SISPEA comme contrôle ou secours lorsque la couverture est démontrée. `P301.3` n'est pas calculé lorsque `D302.0 < 100`. La ligne doit alors porter une valeur nulle, `NOT_CALCULABLE` et `NOT_APPLICABLE`.

## Périmètres et agrégations

Ne jamais confondre territoire administratif, exploitant, contrat et périmètre hydraulique. Les indicateurs non additifs (`P104.3`, `P105.3`, `P106.3`) restent attachés au périmètre où numérateur et dénominateur ont été calculés.

Les volumes suivants sont distincts : produit, importé, exporté, mis en distribution, consommé autorisé, comptabilisé, facturé clientèle, facturé hydraulique et vendu RPQS.

## Révisions historiques

La dernière valeur officiellement révisée devient `PRODUCTION`. La valeur publiée antérieurement reste `AUDIT`. Les statuts `REVISED_SNAPSHOT` et `REVISED_BY_LATER_SOURCE` sont non bloquants.

Exemple CAP Nord ANC 2023 : le RPQS publiait 28 %, mais `4 801 / 18 322 = 26,20 %`, valeur confirmée dans le RPQS 2024. La valeur 28 % est conservée en audit ; 26,20 % est la valeur de production.

## Anomalie Robert–Trinité

Un `P104.3` attribué à Robert–Trinité alors que le RAD indique un calcul Ex-SICSM complet est conservé en `AUDIT` avec `SOURCE_ERROR_SUSPECTED`. Il ne bloque pas la certification car il est exclu de la production.

## Absence et zéro

Une source non produite ou une donnée manquante n'est jamais remplacée par zéro. Les absences connues sont versionnées dans `modules/perimeters/known_absences.csv` avec `NON_PRODUIT_DECLARE`.

## Certification

- `CERTIFIED` : aucune anomalie bloquante de production et aucune lacune déclarée ;
- `CERTIFIED_WITH_GAPS` : aucune anomalie bloquante, mais une source manuelle ou une donnée attendue non produite ;
- `NOT_CERTIFIED` : valeur `PRODUCTION` incohérente, invalide ou non résolue.

Une erreur présente uniquement en `AUDIT` ne rend pas le millésime non certifié.
