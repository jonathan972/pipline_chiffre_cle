# Ressources d'audit et de reproduction

Ce dossier rassemble les ressources utiles reçues ou produites pendant la construction du pipeline. Il est destiné à rendre l'application auditable par un humain ou une IA sans devoir reconstruire le contexte de projet.

- `source_documents/YYYY/` : PDF RAD/RPQS et rapport 2022 de référence ;
- `text_extracts/YYYY/` : extractions texte recherchables des PDF ;
- `source_csv/YYYY/` : exports bruts BNPE, SISPEA et portail assainissement ;
- `validation/` : classeurs de validation et dictionnaire des indicateurs ;
- `templates/` : template Word et mapping de placeholders ;
- `examples/` : exemples de rapports générés ;
- `MANIFEST.csv/json` : inventaire, taille et SHA-256 de chaque ressource.

Les PDF source sont utilisés par `application.core.rebuild_local_reports()`. Le nom de fichier doit correspondre à `modules/local_reports/config.json`.

Dans le dépôt GitHub, les ressources textuelles/CSV et les manifestes doivent être conservés au minimum. Les PDF volumineux peuvent nécessiter Git LFS ; leur SHA-256 dans le manifeste permet de vérifier qu'un fichier externe est exactement celui utilisé lors de la validation.
