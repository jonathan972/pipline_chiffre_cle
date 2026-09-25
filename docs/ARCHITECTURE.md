# Objectifs et architecture

## Objectif

Le projet vise à rendre reproductible l'actualisation annuelle des chiffres clés Eau & Assainissement de l'Observatoire de l'Eau Martinique, tout en conservant la traçabilité de chaque valeur : millésime, source, snapshot, définition, territoire administratif, périmètre de service, statut de couverture et rôle de publication.

Le livrable final doit pouvoir alimenter Excel, QGIS, PostgreSQL/PostGIS et une datavisualisation, sans supprimer le contrôle humain nécessaire aux sources locales.

## Modèle conceptuel

Le grain central est `année × indicateur × territoire administratif × périmètre de service`. Une ligne conserve notamment : valeur, unité, source principale et détail, fichier/page, statut de couverture, statut qualité, rôle de l'enregistrement, millésime de population, définition et note.

Trois rôles sont essentiels :

- `PRODUCTION` : valeur publiable et utilisée dans les agrégats ;
- `DIAGNOSTIC` : résultat utile, encore à valider ou non publiable automatiquement ;
- `AUDIT` : valeur historique, erronée ou remplacée, conservée pour la traçabilité.

## Modules

| Module | Fonction |
|---|---|
| `sispea` | imports AEP, AC et ANC ; indicateurs réglementaires et services |
| `bnpe` | prélèvements par ouvrage et usage ; contrôles surface/souterrain |
| `steu` | stations ERU, capacités, conformité, boues et géographie |
| `insee_population` | populations municipales et millésimes officiels |
| `local_reports` | données extraites des RAD/RPQS locaux |
| `perimeters` | EPCI, contrats, secteurs partiels et anomalies SISPEA |
| `ars_quality` | qualité sanitaire via Hub'Eau/SISE-Eaux |
| `master` | fusion et calcul des faits par millésime |
| `orchestrator` | consolidation, rapport qualité, manifeste et certification |

## Base cible

Le schéma `modules/orchestrator/sql/00_global_schema.sql` prépare `dim_perimeter`, `source_snapshot`, `fact_indicator` et `run_log`. Le `docker-compose.yml` fournit PostgreSQL/PostGIS. Le chargement automatique n'est pas encore la voie de production : la séquence validée reste Python → CSV → contrôle → base.

## Décision structurante CAP Nord

CAP Nord compte 18 communes, mais Robert et La Trinité sont partagées entre des secteurs du contrat CAP Nord et le contrat Ex-SICSM. Les rendements ou indices calculés sur l'ensemble Ex-SICSM ne peuvent pas être ré-étiquetés Robert–Trinité ou CAESM. Les fichiers de `modules/perimeters/` matérialisent ce découpage.
