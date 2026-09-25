# Spécification fonctionnelle — application desktop « Chiffres clés »

## But

Fournir un exécutable Windows utilisable chaque année par un agent sans connaissance Python pour produire le référentiel, les contrôles, les graphiques, les cartes puis le rapport annuel.

## Parcours utilisateur cible

### 1. Choix du millésime

L'utilisateur choisit N et un dossier de travail.

### 2. Collecte automatique

L'application affiche pour chaque source : `OK`, `À contrôler`, `Indisponible`, `Non applicable`.

Sources prévues : INSEE, BNPE, ARS/Hub'Eau, ERU/STEU, SISPEA selon les possibilités techniques.

### 3. Documents locaux

L'application déduit les documents attendus selon le millésime et les territoires : RAD, RPQS, inventaires, exports locaux. Elle permet le dépôt par glisser-déposer et reconnaît le type de document lorsque possible.

Une absence connue doit pouvoir être qualifiée : `NON_PRODUIT_DECLARE`, `NON_RECU`, `NON_APPLICABLE`.

### 4. Contrôle / certification

Afficher :

- indicateurs `PRODUCTION` ;
- diagnostics ;
- audits ;
- gaps ;
- anomalies bloquantes ;
- comparaisons N/N-1 ;
- sources retenues et révisions.

La génération finale doit respecter la certification.

### 5. Assets du rapport

- graphiques générés par le moteur de reporting ;
- cartes générées par le moteur SIG si disponible ;
- photos/illustrations éditoriales sélectionnées ou conservées ;
- textes dynamiques générés et prévisualisables.

### 6. Publication

Bouton final : `Générer le rapport`.

Sorties :

```text
YYYY/
├── data/
├── quality/
├── charts/
├── maps/
├── assets/
├── Chiffres_cles_YYYY.docx
├── Chiffres_cles_YYYY.pdf
└── run_manifest.json
```

## Architecture logicielle recommandée

- Python 3.11+ ;
- PySide6 pour l'interface ;
- PyInstaller pour l'exécutable ;
- `python-docx` ou moteur DOCX équivalent pour le reporting ;
- PostgreSQL/PostGIS comme cible de données partagée ;
- moteur SIG externe : ArcGIS Pro/`arcpy.mp` ou QGIS/PyQGIS après audit.

Ne pas embarquer une installation QGIS/ArcGIS complète dans l'exécutable initial. Détecter le moteur SIG installé et appeler le script correspondant.

## Architecture interne

```text
ui/
services/
  data_collection/
  local_documents/
  validation/
  reporting/
  gis/
models/
config/
assets/
```

L'interface ne doit contenir aucune règle métier. Les règles doivent rester dans les services/configurations testables en ligne de commande.

## États importants

La GUI doit distinguer :

- une source inaccessible temporairement ;
- une source structurellement absente ;
- une donnée incomplète ;
- une donnée révisée ;
- une donnée non publiable ;
- un document volontairement non produit.

## Journalisation

Chaque exécution doit produire un `run_manifest.json` avec : millésime, date, versions du logiciel, sources, hashes, documents déposés, règles appliquées, valeurs retenues, assets produits, statut de certification et erreurs.

## MVP

Le premier MVP desktop ne doit pas automatiser tout le SIG. Il doit savoir :

1. choisir N ;
2. lancer le pipeline ;
3. demander les documents locaux ;
4. afficher la certification ;
5. générer le rapport Word avec valeurs et graphiques ;
6. accepter des cartes PNG déposées manuellement dans les placeholders.

L'automatisation SIG vient ensuite sans casser ce parcours.
