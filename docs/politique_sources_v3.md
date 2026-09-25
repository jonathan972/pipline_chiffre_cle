# Politique de sources v3 — périmètres et contrats

## 1. Géographie administrative
BANATIC/INSEE déterminent la composition des EPCI. En 2023-2024 : CACEM = 4 communes, CAESM = 12 communes, CAP Nord = 18 communes.

## 2. Géographie de service
La géographie de service est distincte de la géographie administrative. Pour CAP Nord AEP 2023-2024 :
- `CAP_NORD_DSP_2020_2024` = 16 communes pleines + secteurs partiels `Robert CN` et `Trinité CN` ;
- `ROBERT_TRINITE_EXSICSM` = autres secteurs de Robert et Trinité relevant de l'Ex-SICSM ;
- `EX_SICSM_DSP_2015_2027` = 12 communes CAESM + secteurs Ex-SICSM de Robert/Trinité.

## 3. Priorité des sources
- périmètre administratif : BANATIC ;
- périmètre contractuel et bilan hydraulique : RAD ;
- total EPCI et validation : RPQS ;
- qualité microbiologique et physico-chimique : ARS / SISE-Eaux via l'ETL Hub'Eau du projet ;
- ANC : CSV métier ODE du millésime en priorité, RPQS/RAD pour validation et compléments, SISPEA en contrôle ou secours ;
- prélèvements et volumes par ouvrage : BNPE ;
- SISPEA : données utiles mais soumises à contrôle renforcé sur CAP Nord/Robert-Trinité et sur la complétude ANC.

## 4. Qualité AEP
Le reporting utilise les sorties annuelles :

`modules/ars_quality/outputs/YYYY/fact_ars_quality_YYYY.csv`

Les champs canoniques sont `QUAL_MICROBIO_CONFORMITE` et `QUAL_PC_CONFORMITE`. La sélection est faite au bon territoire. Les résultats RAD/RPQS/SISPEA restent des contrôles secondaires.

## 5. ANC
Les CSV ANC métier fournis par l'ODE deviennent l'entrée de référence du reporting ANC. Ils devront être normalisés vers une table/fichier canonique conservant au minimum : indicateur, année, territoire, périmètre, valeur, unité, numérateur, dénominateur, fichier source et statut qualité.

Le mapping des colonnes ne doit pas être supposé : il est établi à partir des CSV réels. Les RPQS/RAD sont utilisés pour expliquer, contrôler et compléter les valeurs lorsque nécessaire. SISPEA ne doit pas écraser une valeur issue du CSV métier.

## 6. Non-additivité
P104.3, P105.3 et P106.3 ne sont ni sommés ni moyennés. Ils restent attachés au `perimeter_id` du bilan qui les produit.

## 7. Historisation
Une correction publiée en N+1 n'écrase jamais la valeur publiée en N. Exemple : le P104.3 CAP Nord 2023 passe de 51,53 % dans le RAD 2023 à 53,17 % dans l'historique du RAD 2024. Les deux versions sont conservées.

## 8. Volumes
Les notions suivantes restent distinctes : volume facturé clientèle, volume facturé utilisé dans le bilan hydraulique, volume comptabilisé, volume vendu RPQS. Elles ne sont fusionnées qu'après preuve d'équivalence méthodologique.
