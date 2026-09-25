# Référentiel Eau & Assainissement — ODE Martinique

État sauvegardé de la **V1 opérationnelle / v8** du pipeline qui consolide les chiffres clés Eau & Assainissement de Martinique. Le dépôt contient le code, les données sources redistribuables utilisées par les prototypes, les sorties de référence 2022–2024, les règles métier et un guide de reprise conçu pour un humain ou une IA.

## Nouvelle orientation : de la donnée au rapport annuel complet

Le projet ne s'arrête plus au référentiel d'indicateurs. La cible est désormais une **chaîne annuelle de publication** capable de produire automatiquement ou semi-automatiquement le rapport « Les chiffres clés de l'eau potable et de l'assainissement en Martinique », ses graphiques et, à terme, ses cartes.

La cible utilisateur est une application Windows qui, pour un millésime N :

1. récupère automatiquement les sources disponibles (INSEE, BNPE, ARS/Hub'Eau, ERU/STEU, SISPEA lorsque possible) ;
2. indique les documents locaux attendus et demande leur dépôt lorsqu'ils sont nécessaires (RAD, RPQS, inventaires, fichiers complémentaires) ;
3. contrôle les périmètres, définitions, révisions et absences connues ;
4. calcule puis certifie les indicateurs ;
5. génère les graphiques ;
6. met à jour les données SIG puis génère les cartes à partir de modèles cartographiques ;
7. remplit un template Word à placeholders ;
8. produit le DOCX et le PDF annuels avec manifeste de traçabilité.

Le **rapport 2022 est le jeu étalon** : la première validation du moteur de publication consiste à régénérer 2022 à partir du référentiel et à comparer le résultat au rapport publié. Ensuite la cible métier est de produire **le rapport + les cartes 2023**, puis **le rapport + les cartes 2024** avec la même application.

Le chantier SIG est temporairement différé. Les cartes historiques ont été réalisées dans des projets **ArcMap MXD** dont les chemins de couches peuvent être cassés ou dispersés. Ils seront audités une fois ouverts dans ArcGIS : couches, sources, jointures, symbologie, étiquettes, mises en page et provenance métier. Après cet audit, la cible d'automatisation sera choisie entre ArcGIS Pro/`arcpy.mp` et QGIS/PyQGIS. Les MXD servent de référence, pas de cible technique pérenne.

Voir :

- [Vision de publication automatisée](docs/PUBLICATION_AUTOMATISEE.md)
- [Feuille de route rapports 2023–2024](docs/ROADMAP_RAPPORTS_2023_2024.md)
- [Contrat du template Word](docs/TEMPLATE_WORD.md)
- [Préparation de l'automatisation SIG](docs/SIG_AUTOMATISATION.md)
- [Spécification de l'application desktop](docs/APP_DESKTOP_SPEC.md)

## Résultat actuel

- 80 indicateurs recensés dans le dictionnaire métier ;
- 21 indicateurs en classe A (automatiques validés) ;
- 32 en classe B (automatiques avec contrôle) ;
- 24 en classe C (semi-automatiques ou source locale) ;
- 3 en classe D (manuels ou de référence) ;
- 53/80, soit 66,2 %, techniquement automatisables ;
- certifications 2022, 2023 et 2024 : `CERTIFIED_WITH_GAPS`, sans anomalie bloquante de production ;
- prototype de template Word 36 pages créé avec placeholders stables ;
- moteur V1 de remplacement des valeurs depuis `fact_indicateur_master_YYYY.csv` testé sur 2022 ;
- emplacements prévus pour cartes, graphiques, photos et textes dynamiques.

| Année | Lignes | Production | Diagnostic | Audit | Gaps | Blocages |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 50 | 32 | 17 | 0 | 3 | 0 |
| 2023 | 99 | 81 | 16 | 2 | 3 | 0 |
| 2024 | 58 | 38 | 17 | 3 | 4 | 0 |

Les trois gaps 2022–2023 concernent l'inventaire patrimonial des captages (`RES_007/008/009`). Les quatre gaps 2024 sont les absences documentaires déclarées : AEP, AC et ANC CACEM, puis ANC CAESM.

## Démarrage rapide

Prérequis : Python 3.11 ou plus récent. Le cœur hors ligne utilise la bibliothèque standard. Les dépendances facultatives sont listées dans `requirements.txt`.

```powershell
py -m unittest discover -s tests -v
py update_observatoire.py --year 2024
```

La seconde commande écrit dans `modules/orchestrator/outputs/annual_2024/` :

- `fact_indicateur_master_2024.csv` ;
- `quality_report_2024.csv` ;
- `run_manifest.json` ;
- `certification_2024.json`.

Pour rafraîchir les données ARS/Hub'Eau :

```powershell
py update_observatoire.py --year 2024 --refresh-ars
```

Utiliser `--strict` pour faire échouer l'exécution si le master de base est absent. Ne pas lancer un nouveau millésime en supposant que tous les collecteurs sont orchestrés : la V1 consolide encore des masters préparés en amont.

## Architecture cible

```text
INSEE ─┐
SISPEA ├─> collecte / normalisation ─> master certifié ─┬─> graphiques
BNPE ──┤                                               ├─> textes dynamiques
ERU ───┤                                               ├─> base SIG ─> cartes
ARS ───┤                                               └─> template DOCX ─> PDF
RAD/RPQS ─> dépôt manuel guidé ────────────────────────────────┘
                    ^
                    └─ application desktop annuelle
```

Les modules de données restent séparés par source : `sispea`, `bnpe`, `steu`, `insee_population`, `local_reports`, `perimeters`, `ars_quality`, `master` et `orchestrator`. Un nouveau domaine fonctionnel `reporting` porte le contrat de publication Word, puis accueillera les graphiques et assets.

## Documentation de référence

- [Objectifs et architecture](docs/ARCHITECTURE.md)
- [Règles métier](docs/REGLES_METIER.md)
- [Méthodologie et sources](docs/METHODOLOGIE.md)
- [Tests et certification 2022–2024](docs/TESTS_2022_2024.md)
- [Limites connues et priorités](docs/LIMITES_CONNUES.md)
- [Procédure annuelle](docs/PROCEDURE_ANNUELLE.md)
- [Guide de reprise IA](docs/REPRISE_IA.md)
- [Inventaire des données et snapshots](docs/INVENTAIRE_DONNEES.md)
- [Publication automatisée](docs/PUBLICATION_AUTOMATISEE.md)
- [Roadmap 2023–2024](docs/ROADMAP_RAPPORTS_2023_2024.md)

## Principe de prudence

Une valeur n'est jamais forcée pour « coller » à un rapport. Les écarts, changements de définition, révisions de source et différences de périmètre sont historisés. Une absence connue reste une absence explicite, jamais un zéro. Le moteur de publication ne doit jamais masquer une donnée manquante : il doit soit afficher un bloc explicitement géré, soit empêcher la publication de l'élément concerné selon les règles du template.