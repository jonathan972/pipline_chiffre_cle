# État du projet — 24 septembre 2026

## Décision d'orientation

Le projet ne vise plus uniquement à automatiser la collecte des indicateurs. La cible est désormais une **chaîne complète de production annuelle du rapport « Les chiffres clés de l'eau potable et de l'assainissement en Martinique »**, avec génération du DOCX/PDF, des graphiques et, dans un second temps, des cartes.

L'objectif métier immédiat est de produire, avec la même application :

1. un rapport 2022 régénéré servant de test étalon ;
2. le rapport 2023 complet ;
3. le rapport 2024 complet ;
4. les cartes 2023 et 2024 lorsque le chantier SIG aura été normalisé.

## État acquis

Le socle données est considéré comme suffisamment stabilisé pour démarrer la chaîne de publication :

- dictionnaire de 80 indicateurs ;
- règles de source, périmètre et révision ;
- séparation `PRODUCTION / DIAGNOSTIC / AUDIT` ;
- certification 2022–2024 en `CERTIFIED_WITH_GAPS`, sans erreur bloquante de production ;
- référentiel des périmètres CAP Nord / Ex-SICSM, y compris les secteurs partiels du Robert et de La Trinité ;
- intégration INSEE, BNPE, SISPEA, ERU/STEU, RAD/RPQS et ARS/Hub'Eau selon les modules existants ;
- commande annuelle et logique de contrôle qualité déjà en place.

## Orientation reporting

Un **template Word technique de 36 pages** a été créé pour reproduire la structure fonctionnelle du rapport 2022. Il ne cherche pas à reproduire immédiatement la PAO pixel par pixel : son rôle est de servir de contrat stable entre le référentiel de données et le moteur de publication.

Les placeholders suivent des identifiants stables liés au dictionnaire, par exemple :

```text
{{ANNEE}}
{{RES_014}}
{{EP_005_MARTINIQUE}}
{{EP_019_CACEM}}
{{AC_012}}
{{ANC_013}}
{{TAR_001}}
```

Les assets graphiques suivent le même principe :

```text
{{MAP_CAPTAGES_AEP}}
{{MAP_STEU_PUBLIQUES}}
{{MAP_AC_ANC_COMMUNES}}
{{CHART_RENDEMENT_ILP}}
{{CHART_BOUES_HIST}}
```

Le moteur V1 de remplacement de valeurs a été testé sur le master 2022. L'étape suivante est de rendre le rapport 2022 reproductible de bout en bout : valeurs, tableaux, graphiques, blocs optionnels, textes dynamiques et emplacements de cartes.

## Décision temporaire sur le SIG

Le chantier SIG est **volontairement différé**, pas abandonné.

Les cartes historiques sont dans des projets **ArcMap MXD** et les projets/données ne sont pas encore organisés dans une arborescence fiable. Les chemins de couches peuvent donc être absolus, cassés ou dispersés.

Le propriétaire du projet ouvrira les MXD dans ArcGIS afin de permettre un audit fonctionnel. Lors de cet audit, il expliquera également la provenance métier des données utilisées pour chaque couche.

Avant toute automatisation cartographique, il faudra documenter pour chaque carte :

- MXD et Data Frame ;
- couches ;
- source physique de chaque couche ;
- jointures/relations ;
- filtres et définition de requête ;
- champs utilisés ;
- symbologie ;
- étiquettes ;
- mise en page ;
- échelle/emprise ;
- provenance métier et fréquence d'actualisation de la donnée.

Après cet audit, il faudra choisir la cible durable :

- **ArcGIS Pro + `arcpy.mp`**, si l'environnement ESRI est retenu ;
- ou **QGIS + PyQGIS**, si l'on privilégie une chaîne plus portable.

Les MXD doivent être considérés comme **références historiques de mise en page**, pas comme cible technique pérenne.

## Priorité actuelle

Tant que le SIG n'est pas audité, l'ordre de travail est :

1. finaliser le mapping des 80 indicateurs vers le template ;
2. rendre le rapport 2022 reproductible ;
3. automatiser les graphiques ;
4. gérer les textes dynamiques dépendant des données ;
5. gérer les absences documentaires et blocs optionnels ;
6. produire le rapport 2023 ;
7. produire le rapport 2024 ;
8. reprendre le chantier SIG ;
9. automatiser les cartes ;
10. intégrer l'ensemble dans l'application desktop Windows.

## Règle de conception importante

Le contenu du rapport est séparé en trois catégories :

### 1. Contenu éditorial stable

Texte explicatif qui peut rester dans le template tant que le cadre réglementaire/méthodologique ne change pas.

### 2. Contenu dynamique déterministe

Valeurs, pourcentages, tableaux, graphiques, année, sources, cartes et éléments calculés directement depuis le référentiel.

### 3. Texte dynamique métier

Commentaires dépendant des tendances de données, par exemple « augmentation depuis deux ans ». Ces textes doivent progressivement être produits par des règles explicites et testables, jamais par génération libre non contrôlée.

## Cible applicative

La future application Windows doit guider un utilisateur non développeur :

```text
choix du millésime
  -> collecte automatique
  -> état des sources
  -> demande des RAD/RPQS/fichiers locaux manquants
  -> contrôles et certification
  -> génération des graphiques
  -> génération ou dépôt des cartes
  -> génération DOCX/PDF
  -> manifeste final
```

Elle doit pouvoir distinguer clairement :

- source non disponible ;
- document officiellement non produit ;
- valeur présente mais diagnostique ;
- valeur révisée ;
- anomalie de source ;
- valeur certifiée pour publication.

Aucune absence ne doit être transformée en zéro.

## Consigne de reprise pour une IA

Si une IA reprend ce projet plus tard, elle doit commencer par lire :

1. `README.md` ;
2. `docs/ETAT_PROJET_2026-09-24.md` ;
3. `docs/ROADMAP_RAPPORTS_2023_2024.md` ;
4. `docs/PUBLICATION_AUTOMATISEE.md` ;
5. `docs/REGLES_METIER.md` ;
6. `docs/REPRISE_IA.md`.

Elle ne doit pas reprendre le chantier SIG avant d'avoir reçu l'audit des MXD et les explications sur la provenance des couches.
