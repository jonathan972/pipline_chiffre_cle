# Historique

## Orientation publication automatisée — 2026-09-24

- extension de la cible : le référentiel ne sert plus seulement à consolider les indicateurs mais devient le socle d'une chaîne annuelle de publication ;
- objectif fonctionnel : application Windows capable de récupérer automatiquement les sources disponibles, demander les RAD/RPQS et autres documents locaux, certifier les indicateurs, générer graphiques et cartes, puis produire le DOCX/PDF annuel ;
- rapport 2022 retenu comme jeu étalon de reproduction ;
- objectif métier fixé : produire avec l'application le rapport + cartes 2023 puis le rapport + cartes 2024 ;
- prototype de template Word 36 pages créé avec placeholders stables reliés au dictionnaire des indicateurs ;
- moteur V1 de remplacement depuis `fact_indicateur_master_YYYY.csv` testé sur 2022 ;
- emplacements réservés pour cartes, graphiques, photos et textes dynamiques ;
- cartographie différée jusqu'à audit des projets historiques ArcMap MXD ; chemins de couches potentiellement cassés/dispersés ;
- après audit, choix de la cible entre ArcGIS Pro/`arcpy.mp` et QGIS/PyQGIS ; ArcMap/MXD conservé comme référence historique, pas comme cible pérenne.

## V1 / v8 — sauvegarde 2026-09-24

- point d'entrée annuel à la racine ;
- certification métier séparant production, diagnostic et audit ;
- jeux de régression 2022–2024 ;
- documentation des objectifs, de l'architecture, des règles, de la méthode, des limites et de la reprise IA ;
- inventaire des snapshots Hub'Eau volumineux non versionnés ;
- conservation du code et des résultats des modules v1 à v7 ayant conduit à la V1 stabilisée.
