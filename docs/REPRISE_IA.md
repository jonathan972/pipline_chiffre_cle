# Guide de reprise pour une IA

## Mission

Continuer l'industrialisation du Référentiel Eau & Assainissement de l'ODE Martinique sans perdre la traçabilité ni fabriquer de données. Commencer par lire `README.md`, `REGLES_METIER.md`, `LIMITES_CONNUES.md`, puis les README des modules concernés.

## État fiable à considérer

- la conception V1/v8 est stabilisée ;
- les résultats 2022–2024 sont les jeux de régression ;
- `CERTIFIED_WITH_GAPS` ne signifie pas que les valeurs de production sont fausses ;
- les vraies lacunes répétitives sont les captages/PPC ;
- les périmètres CAP Nord, Robert–Trinité et Ex-SICSM sont déjà réconciliés et ne doivent pas être simplifiés en listes de communes exclusives ;
- les fichiers de `docs/` et les sorties certifiées font partie de la preuve méthodologique.

## Première session recommandée

1. Cloner le dépôt et exécuter `py -m unittest discover -s tests -v`.
2. Exécuter hors ligne les trois années avec `py update_observatoire.py --year YYYY`.
3. Comparer les nouvelles certifications aux attentes 3/3/4 gaps et 0 blocage.
4. Lire les `run_manifest.json` et vérifier les empreintes des entrées.
5. Avant toute évolution, ajouter un test de régression qui protège le cas métier concerné.

## Garde-fous

- ne jamais convertir une absence en zéro ;
- ne jamais écraser une valeur historique révisée ;
- ne jamais promouvoir `DIAGNOSTIC` en `PRODUCTION` sans source et justification ;
- ne jamais agréger des pourcentages/rendements par addition ou moyenne simple ;
- ne jamais attribuer un indicateur Ex-SICSM à Robert–Trinité seul ;
- séparer année de référence, millésime de population et date du snapshot ;
- conserver numérateur et dénominateur lorsque disponibles ;
- privilégier une modification minimale et documentée plutôt qu'une refonte silencieuse.

## Prochaines tâches conseillées

1. Construire le référentiel patrimonial captages/PPC ODE–ARS.
2. Certifier le module tarifs.
3. Orchestrer automatiquement SISPEA, BNPE, INSEE et ERU avant le master.
4. Ajouter des tests unitaires par module et une validation de schéma CSV.
5. Charger le master certifié dans PostgreSQL/PostGIS et produire des vues stables pour QGIS et Excel.
6. Documenter et tester le changement d'exploitant CAP Nord à partir de 2025.

## Format de compte rendu attendu

Pour chaque changement, consigner : objectif, sources utilisées, périmètre, règles appliquées, fichiers modifiés, tests exécutés, résultats avant/après, limites restantes et décision de publication.
