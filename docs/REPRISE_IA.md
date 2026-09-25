# Guide de reprise pour une IA

## Mission générale

Continuer l'industrialisation du Référentiel Eau & Assainissement de l'ODE Martinique **et de sa chaîne de publication annuelle** sans perdre la traçabilité ni fabriquer de données.

Lire d'abord :

1. `README.md` ;
2. `PROJECT_STATUS.json` ;
3. `docs/REGLES_METIER.md` ;
4. `docs/LIMITES_CONNUES.md` ;
5. `docs/PUBLICATION_AUTOMATISEE.md` ;
6. `docs/ROADMAP_RAPPORTS_2023_2024.md` ;
7. `docs/TEMPLATE_WORD.md` ;
8. `docs/SIG_AUTOMATISATION.md`.

## État fiable à considérer

- la conception V1/v8 du référentiel est stabilisée ;
- les résultats 2022–2024 sont les jeux de régression ;
- `CERTIFIED_WITH_GAPS` ne signifie pas que les valeurs de production sont fausses ;
- les vraies lacunes répétitives sont notamment les captages/PPC ;
- les périmètres CAP Nord, Robert–Trinité et Ex-SICSM sont déjà réconciliés et ne doivent pas être simplifiés en listes de communes exclusives ;
- les fichiers de `docs/` et les sorties certifiées font partie de la preuve méthodologique ;
- le projet vise désormais la **production automatique du rapport annuel complet** et pas seulement du CSV maître ;
- le rapport publié 2022 sert de jeu étalon pour le moteur de publication ;
- la cible métier est de produire avec l'application le rapport + cartes 2023 puis le rapport + cartes 2024 ;
- un prototype de template Word 36 pages avec placeholders a été créé ;
- un moteur V1 de remplacement des valeurs depuis `fact_indicateur_master_YYYY.csv` a été testé sur 2022 ;
- le SIG est volontairement différé jusqu'à audit des projets ArcMap MXD ouverts dans ArcGIS.

## Première session recommandée

1. Cloner le dépôt et exécuter `py -m unittest discover -s tests -v`.
2. Exécuter hors ligne les trois années avec `py update_observatoire.py --year YYYY`.
3. Comparer les nouvelles certifications aux attentes 3/3/4 gaps et 0 blocage.
4. Lire les `run_manifest.json` et vérifier les empreintes des entrées.
5. Lire la documentation `reporting` et vérifier le contrat de placeholders.
6. Régénérer un rapport test 2022 à partir du master 2022.
7. Avant toute évolution, ajouter un test de régression qui protège le cas métier concerné.

## Garde-fous données

- ne jamais convertir une absence en zéro ;
- ne jamais écraser une valeur historique révisée ;
- ne jamais promouvoir `DIAGNOSTIC` en `PRODUCTION` sans source et justification ;
- ne jamais agréger des pourcentages/rendements par addition ou moyenne simple ;
- ne jamais attribuer un indicateur Ex-SICSM à Robert–Trinité seul ;
- séparer année de référence, millésime de population et date du snapshot ;
- conserver numérateur et dénominateur lorsque disponibles ;
- privilégier une modification minimale et documentée plutôt qu'une refonte silencieuse.

## Garde-fous publication

- le template ne doit afficher que des valeurs autorisées par les règles de publication ;
- un placeholder obligatoire non résolu doit provoquer un contrôle explicite ;
- les cartes/graphiques doivent être reproductibles et enregistrés dans le manifeste ;
- les textes éditoriaux dépendants des données doivent être générés par règles testables ;
- préserver les IDs stables d'indicateurs dans les tokens ;
- ne pas coder les valeurs directement dans le DOCX ;
- conserver le rapport 2022 comme référence visuelle et métier, mais ne pas forcer artificiellement les données pour obtenir la même valeur.

## SIG : état et reprise

Les projets historiques sont des MXD ArcMap potentiellement mal rangés et avec des sources cassées. Ne pas migrer à l'aveugle.

Lorsque le responsable métier ouvre les MXD dans ArcGIS :

1. inventorier couches, chemins, jointures, filtres, symbologie, étiquettes et layouts ;
2. demander/consigner la provenance des données de chaque couche ;
3. distinguer donnée métier et mise en forme cartographique ;
4. proposer une structure propre de stockage ;
5. seulement ensuite choisir ArcGIS Pro/`arcpy.mp` ou QGIS/PyQGIS.

ArcMap/MXD est une référence historique, pas la cible pérenne.

## Prochaines tâches conseillées

1. Stabiliser le module `reporting` et versionner le contrat de placeholders.
2. Rendre la reproduction 2022 mesurable page par page.
3. Générer automatiquement les graphiques du rapport.
4. Produire le rapport 2023 avec cartes déposées manuellement si nécessaire.
5. Produire le rapport 2024 avec gestion explicite des absences CACEM/CAESM ANC.
6. Auditer ensuite les MXD et automatiser les trois cartes pilotes.
7. Construire l'interface desktop seulement quand les moteurs CLI sont stables.
8. Continuer en parallèle le référentiel captages/PPC et le module tarifs.

## Format de compte rendu attendu

Pour chaque changement, consigner : objectif, sources utilisées, périmètre, règles appliquées, fichiers modifiés, tests exécutés, résultats avant/après, limites restantes et décision de publication.
