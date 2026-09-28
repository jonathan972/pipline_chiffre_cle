# Dictionnaire des données

## `project.json`

| Champ | Type | Description |
|---|---|---|
| `territoire` | texte | Nom du territoire / EPCI |
| `collectivite` | texte | Nom court de la collectivité |
| `delegataire` | texte | Nom court du délégataire |
| `annee_facture` | entier | Millésime de la facture type |
| `annee_comptable` | entier | Millésime CARE / M49 |
| `volume_reference_m3` | nombre | Volume de référence, généralement 120 m³ |
| `budget_eau` | texte | Valeur `lbudg` de la balance M49 pour l'eau |
| `budget_assainissement` | texte | Valeur `lbudg` pour l'assainissement |
| `source_facture` | texte | Référence documentaire |
| `source_care` | texte | Référence documentaire |
| `source_m49` | texte | Référence de la balance |

## `facture.csv`

Séparateur recommandé : `;`.

| Colonne | Description |
|---|---|
| `service` | `Eau` ou `Assainissement` |
| `categorie` | bénéficiaire ou nature lisible |
| `sous_categorie` | détail de la ligne |
| `nature` | `delegataire`, `collectivite`, `redevance`, `taxe`, `tva` |
| `montant_eur` | montant additif utilisé dans le camembert |
| `source_note` | référence page / ligne facultative |

**Contrainte** : la somme de `montant_eur` doit être égale au TTC de la facture type.

## `care_resume.csv`

| Colonne | Description |
|---|---|
| `service` | Eau / Assainissement |
| `total_produits` | Produits totaux du CARE |
| `reversements_publics` | Collectivités et autres organismes publics |
| `charges_hors_reversements` | Charges du contrat hors reversements publics |
| `resultat_avant_impot` | Résultat avant impôt |

## `care_couts.csv`

| Colonne | Description |
|---|---|
| `service` | Eau / Assainissement |
| `poste` | Catégorie de coût lisible |
| `montant_eur` | Montant annuel |
| `source_note` | Ligne / page / règle d'agrégation |

La somme des postes d'un service doit être égale à `charges_hors_reversements` à l'arrondi près.

## Sorties M49 de `prepare_m49.py`

### `m49_fonctionnement.csv`

`service;poste;montant_eur`

### `m49_investissement.csv`

`service;poste;montant_eur`

### `m49_ressources.csv`

`service;poste;montant_eur;role`

### `m49_indicateurs.csv`

`service;indicateur;montant_eur`

Contient au minimum :

- fonctionnement classe 6 ;
- investissement classe 2 ;
- remboursement capital classe 16.
