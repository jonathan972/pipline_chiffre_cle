# Module périmètres et contrats — v6

Ce module corrige une faiblesse structurelle : un EPCI administratif n'est pas nécessairement un périmètre hydraulique/contractuel homogène.

## Conclusion CAP Nord

CAP Nord compte 18 communes. En 2023-2024, l'AEP repose sur deux ensembles contractuels qui se chevauchent au niveau communal mais pas au niveau des secteurs desservis :

- la DSP CAP Nord 2020-2024 dessert les 16 communes hors Robert/Trinité **et des secteurs partiels** de Robert et Trinité, explicitement nommés `Robert CN` et `Trinité CN` dans le RAD ;
- la DSP Ex-SICSM 2015-2027 dessert les 12 communes de la CAESM et d'autres secteurs de Robert et Trinité.

Il est donc interdit de modéliser ces contrats par une simple liste de communes exclusives. `bridge_perimetre_commune.csv` distingue `FULL_COMMUNE` et `PARTIAL_COMMUNE`.

## Règle de source

- BANATIC : périmètre administratif EPCI ;
- RAD : vérité opérationnelle/contractuelle et périmètre des bilans hydrauliques ;
- RPQS CAP Nord : contrôle et total EPCI ;
- SISPEA : source d'indicateurs, mais les périmètres Robert-Trinité/CAP Nord sont soumis à contrôles renforcés.

Le rapport d'activité Plan Eau DOM signale explicitement des incohérences SISPEA en Martinique, notamment des données Robert-Trinité identiques à la CAESM.

## Indicateurs non additifs

Les rendements et indices linéaires (P104.3, P105.3, P106.3) restent attachés à leur périmètre de calcul. Le RAD Ex-SICSM indique que certains de ces indicateurs ne sont calculables qu'à l'échelle du contrat complet : ils ne doivent pas être ré-étiquetés automatiquement `Robert-Trinité`.
