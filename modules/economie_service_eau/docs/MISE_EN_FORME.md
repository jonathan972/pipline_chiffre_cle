# Spécification de mise en forme Excel

Cette spécification constitue le contrat visuel du livrable.

## Palette

| Usage | Couleur |
|---|---|
| Titre principal | `#123B5D` |
| Section | `#DCEAF5` |
| En-tête tableau | `#4F81BD` |
| Sous-total | `#EAF2F8` |
| Note méthodologique | `#FFF2CC` |
| KPI | `#E2F0D9` |
| Texte note | `#7F6000` |

## Typographie

- titres : 16 pt, gras, blanc ;
- sections : 12 pt, gras ;
- corps : taille standard Excel ;
- notes : italique, retour à la ligne ;
- alignement vertical centré.

## Formats numériques

- facture : `#,##0.00 €` ;
- M49 : `#,##0.00 €` ;
- grands totaux CARE : `#,##0 €` ;
- pourcentages : `0.0%` ;
- lecture « sur 100 € » : `0.0`.

## Séquence visuelle

### Feuille 1 — Facture

Deux camemberts :

1. **Sur 100 € payés : qui reçoit quoi ?**
2. **Eau potable vs assainissement**

Le premier utilise exactement cinq familles : délégataire, collectivité, redevances, taxes hors TVA, TVA.

### Feuille 2 — CARE

Deux camemberts :

1. structure des coûts Eau ;
2. structure des coûts Assainissement.

### Feuille 3 — Budget M49

Quatre camemberts :

1. fonctionnement Eau ;
2. fonctionnement Assainissement ;
3. ressources hors produits du service Eau ;
4. ressources hors produits du service Assainissement.

Les tableaux d'investissement restent visibles à proximité, même s'ils ne sont pas obligatoirement représentés en camembert.

## Placement

- données et commentaires à gauche ;
- graphiques à droite ;
- légende des camemberts à droite ;
- aucun graphique sur les zones de données ;
- figer les volets sous les titres.

## Noms des feuilles

Les noms doivent conserver l'ordre numérique pour forcer un parcours de lecture :

- `0_Parcours`
- `1_Facture_<annee>`
- `2_CARE_<delegataire>_<annee>`
- `3_Budget_<collectivite>_<annee>`
- `4_Detail_sources`
- `5_Texte_public`
