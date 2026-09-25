# Moteur de publication Word

`report_builder.build_docx(root, year, out_dir, mode)` produit le rapport annuel à partir du master canonique.

```powershell
py generate_report.py --year 2024 --mode draft   # brouillon, toujours produit
py generate_report.py --year 2024 --mode final   # refusé tant qu'un élément requis manque
```

## Chaîne

1. Reconstruit le master et la certification du millésime (`pipeline.run`, sorties dans `outputs/YYYY/`).
2. Résout chaque valeur **uniquement sur les lignes `PRODUCTION`** : pas de repli vers `VALIDATION`, `DIAGNOSTIC` ou `AUDIT`, et jamais de zéro par défaut.
3. Génère les graphiques (`charts/`) avec matplotlib.
4. Produit le document :
   - **avec template** : si `resources/templates/template_chiffres_cles.docx` existe (chemin modifiable dans `reporting_config.json`), remplace les `{{TOKEN}}` (voir `docs/TEMPLATE_WORD.md`) ;
   - **sans template** : génère un document complet, avec couverture, synthèse, un tableau par domaine (Martinique, CACEM, CAESM, CAP Nord, évolution N-1), les périmètres de service, les graphiques, les cartes, les absences et limites, les sources avec leurs empreintes SHA-256.
5. Écrit `preflight_report_YYYY.csv`, `report_summary_YYYY.json` et copie les contrôles du pipeline dans `quality/`.

## Tokens reconnus dans un template

| Token | Résolution |
|---|---|
| `{{ANNEE}}`, `{{ANNEE_PRECEDENTE}}` | millésime, millésime − 1 |
| `{{EP_019}}` | indicateur, périmètre Martinique |
| `{{EP_019_CACEM}}`, `{{AC_012_CAP_NORD}}` | indicateur × territoire (alias de `referentiel/perimetres.csv`) |
| `{{MAP_…}}` | carte déposée dans `publication/YYYY/assets_manual/` (noms dans `asset_filename_by_token`) |
| `{{CHART_…}}` | graphique déclaré dans `charts` |
| `{{TXT_…}}` | texte dynamique déclaré dans `dynamic_texts` (seuils documentés dans la config) |
| autre (`{{PHOTO_PAGE_24}}`…) | image `assets_manual/<token en minuscules>.png|jpg`, sinon `UNKNOWN_TOKEN` (bloquant) |

Un token seul dans son paragraphe peut être remplacé par une image. Un token coupé entre plusieurs segments de texte par Word est reconstitué avant d'être remplacé.

## Statuts du préflight

| Statut | Signification | Bloque le final |
|---|---|---|
| `OK` | valeur `PRODUCTION` publiée | non |
| `KNOWN_ABSENCE` | absence déclarée (« non produit ») | non |
| `NOT_APPLICABLE`, `REFERENCE` | sans objet / référence externe | non |
| `OPTIONAL_MISSING` | élément facultatif absent | non |
| `MISSING_VALUE` | valeur attendue sans aucune source | **oui** |
| `NOT_PUBLISHABLE` | seules des valeurs non validées, ou valeurs `PRODUCTION` divergentes | **oui** |
| `MAP_MISSING` | carte requise non déposée | **oui** |
| `BLOCKING_ANOMALY` | anomalie bloquante du master | **oui** |
| `UNKNOWN_TOKEN` | token du template non reconnu | **oui** |

## Compléter les valeurs manquantes

Dans l'application : « Exporter gabarit des valeurs manquantes », remplir `value` et mettre `validated=oui` quand la valeur est vérifiée, puis « Importer valeurs complémentaires ». Les lignes sont fusionnées dans `saisie/saisie_locale_YYYY.csv`, que lit le pipeline. Une ligne non validée reste en `VALIDATION`, visible dans les contrôles mais jamais publiée. Si une autre source fournit déjà une valeur `PRODUCTION` différente, le conflit est bloquant : la saisie ne masque jamais silencieusement une source.
