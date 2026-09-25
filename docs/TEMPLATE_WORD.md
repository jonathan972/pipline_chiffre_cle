# Template Word — contrat de publication

## Rôle

Le document Word devient le squelette éditorial du rapport annuel. Il conserve la mise en page, les textes stables, les titres, les emplacements d'illustrations et les styles. Les valeurs et assets dépendants du millésime sont remplacés par un moteur de publication.

Le prototype V1 reprend la structure du rapport 2022 en 36 pages. Il ne cherche pas à reproduire pixel par pixel la PAO historique ; il fournit une maquette fonctionnelle automatisable.

## Syntaxe des placeholders

Convention : `{{TOKEN}}`.

Exemples :

```text
{{ANNEE}}
{{RES_014}}
{{EP_003_MARTINIQUE}}
{{EP_019_CACEM}}
{{AC_012}}
{{ANC_013}}
{{TAR_001}}
```

Assets :

```text
{{MAP_CAPTAGES_AEP}}
{{MAP_STEU_PUBLIQUES}}
{{MAP_AC_ANC_COMMUNES}}
{{CHART_BOUES_HIST}}
{{CHART_RENDEMENT_ILP}}
{{PHOTO_PAGE_24}}
{{TXT_BOUES_TREND}}
```

## Types de placeholder

- `year` : millésime ;
- `value` : valeur d'indicateur formatée ;
- `map` : carte exportée du moteur SIG ;
- `chart` : graphique généré automatiquement ;
- `photo` : asset éditorial stable ou fourni manuellement ;
- `image` : illustration ou QR code ;
- `dynamic_text` : texte généré selon des règles métier ;
- `technical_only` : indicateur présent dans le dictionnaire mais non affiché isolément.

## Clé de résolution d'une valeur

Une valeur affichée doit être recherchée avec au minimum :

```text
indicator_id
territoire
année de référence
périmètre si nécessaire
record_role
```

Le rapport public lit exclusivement les lignes `PRODUCTION`, via
`pipeline.publication`. Il n'existe aucun mécanisme de repli vers
`VALIDATION`, `DIAGNOSTIC` ou `AUDIT`.

Lorsqu'aucune ligne `PRODUCTION` n'existe, le placeholder reçoit l'état
« donnée non disponible / à valider ». Les autres rôles restent visibles dans
les écrans et fichiers de contrôle, jamais dans le document public.

## Formats

Le manifeste associe à chaque token un format :

- `int_space` ;
- `m3_int` ;
- `km0` ;
- `pct0`, `pct1`, `pct2` ;
- `decimal2` ;
- `euro2`, `euro_m3` ;
- `kg_abonne` ;
- `distribution` ;
- `text`.

Le formatage doit être centralisé dans le moteur, jamais recodé dans chaque page.

## Gestion des absences

Trois comportements doivent être configurables :

1. `required` : empêcher la publication du bloc ;
2. `optional` : masquer le bloc ou laisser une mention configurée ;
3. `known_absence` : afficher une formulation contrôlée et l'inscrire au manifeste.

Jamais de zéro par défaut.

## Textes dynamiques

Les phrases dépendant des données ne doivent pas rester figées. Exemple : évolution des boues.

Une règle peut produire :

```text
si tendance > 0 : « La production de boues augmente sur la période. »
si tendance < 0 : « La production de boues diminue sur la période. »
si variation faible : « La production de boues est globalement stable. »
```

Chaque texte dynamique doit être testable et documenter les seuils utilisés.

## Validation 2022

Le moteur V1 a déjà été testé sur le master 2022 et remplace les valeurs disponibles sans casser la pagination cible de 36 pages. La prochaine étape est de compléter graphiques/assets et d'établir une comparaison systématique page par page avec le rapport publié.

## Implémentation

Le moteur est `modules/reporting/report_builder.py`, configuré par `modules/reporting/reporting_config.json` (formats par unité, graphiques, cartes, textes dynamiques, chemin du template). Le template DOCX est attendu dans `resources/templates/template_chiffres_cles.docx` ; en son absence, le moteur génère un document complet. Détail des tokens et des statuts du préflight : `modules/reporting/README.md`.
