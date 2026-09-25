# Module portail assainissement (DEAL / national)

Ce module ingère les exports annuels `export-portail_assainissement_YYYY.csv`.

Le fichier contient à la fois des STEU de nature **Urbain** et **Privé**. Dans le rapport Chiffres clés :

- les lignes `Urbain` alimentent / contrôlent les indicateurs de stations publiques (`AC_003` à `AC_009`) ;
- les lignes `Privé` alimentent les indicateurs de stations privées du chapitre ANC (`ANC_005`, `ANC_006`, `ANC_007`, `ANC_008`).

`ANC_009` n'est pas considéré comme directement disponible : l'export n'a pas de champ explicite « propriétaire ayant transmis ses données de conformité ». Le module produit `ANC_009_CANDIDATE` en diagnostic, à valider avant publication.

Le rattachement EPCI est lu dans `modules/perimeters/epci_communes.csv`, jamais codé en dur.
