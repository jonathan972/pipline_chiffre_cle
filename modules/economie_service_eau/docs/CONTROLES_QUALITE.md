# Contrôles qualité

## Facture

- [ ] Les lignes sont toutes classées dans une nature autorisée.
- [ ] Redevances et taxes sont séparées.
- [ ] La TVA est isolée.
- [ ] La somme des lignes égale exactement le total TTC de référence à l'arrondi près.
- [ ] Eau + assainissement = total petit cycle si l'usager est raccordé au collectif.
- [ ] Le volume de référence est explicite.

## CARE

- [ ] Le service et l'année sont identifiés.
- [ ] Les produits totaux sont repris du tableau du CARE.
- [ ] Les montants collectivités / organismes publics sont isolés.
- [ ] La somme des postes de coûts égale les charges hors reversements.
- [ ] `produits - reversements - charges = résultat` à l'arrondi près.
- [ ] Les postes agrégés ont une règle documentée.
- [ ] La part du délégataire n'est jamais appelée bénéfice.

## M49

- [ ] Le bon `lbudg` est utilisé pour chaque service.
- [ ] Le bon exercice est filtré.
- [ ] Les flux annuels utilisent `obnetdeb` / `obnetcre`.
- [ ] Les classes 60-68 sont ventilées en fonctionnement.
- [ ] Les classes 20/21/23 sont ventilées en investissement.
- [ ] Les crédits 13, 16, 70, 75, 77 sont ventilés en ressources.
- [ ] Les débits 16 sont isolés en remboursement du capital.
- [ ] Les produits exceptionnels sont marqués non récurrents.

## Millésimes et périmètres

- [ ] Les années facture, CARE et M49 sont affichées.
- [ ] Tout décalage de millésime fait l'objet d'un avertissement.
- [ ] Les périmètres géographiques/contractuels sont identiques ou les différences sont décrites.
- [ ] Une absence de correspondance comptable n'est pas qualifiée d'anomalie sans table de passage.

## Excel

- [ ] Les formules ne contiennent pas `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` ou `#N/A`.
- [ ] Les graphiques ne couvrent pas les tableaux.
- [ ] Les totaux sont visibles.
- [ ] Les sources sont présentes dans l'onglet détail.
- [ ] Les notes méthodologiques sont visibles sans ouvrir une cellule.
