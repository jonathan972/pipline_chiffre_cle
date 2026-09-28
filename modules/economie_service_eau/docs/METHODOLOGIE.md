# Méthodologie détaillée

## 1. Pourquoi trois sources ?

Une facture, un CARE et une balance M49 ne répondent pas à la même question.

### Facture type

Question : **qui reçoit l'argent payé par l'usager ?**

La facture permet de distinguer :

- la rémunération contractuelle du délégataire ;
- la part de la collectivité ;
- les redevances ;
- les taxes ;
- la TVA.

La représentation grand public doit être additive : les parts affichées doivent sommer exactement au TTC de la facture type.

### CARE

Question : **à quoi servent les recettes du contrat délégué ?**

Le Compte annuel de résultat de l'exploitation est un document du délégataire. Il présente l'économie du contrat : produits, charges directes, charges indirectes, charges calculées et résultat.

Il ne faut pas confondre :

- **part du délégataire sur la facture** ;
- **chiffre d'affaires / produits du contrat** ;
- **résultat du contrat**.

La part délégataire finance le fonctionnement du service et ne constitue donc pas un bénéfice.

### Balance M49

Question : **que finance la collectivité et quelles sont ses autres ressources ?**

La balance retrace la comptabilité publique du service. Elle permet notamment d'analyser :

- charges de fonctionnement ;
- investissements ;
- remboursement du capital ;
- produits du service ;
- subventions ;
- emprunts nouveaux ;
- produits exceptionnels.

## 2. Construction de la facture pédagogique

La facture est reconstruite sur une base commune en euros :

`Total TTC = délégataire HT + collectivité HT + redevances + taxes hors TVA + TVA`

Chaque ligne source est classée dans l'une des natures suivantes :

- `delegataire`
- `collectivite`
- `redevance`
- `taxe`
- `tva`

### Pourquoi séparer redevances et taxes ?

Une redevance est liée à une politique ou mission de l'eau et possède une logique d'affectation spécifique. Une taxe est un prélèvement fiscal. Dans la présentation publique, l'octroi de mer et la TVA doivent donc apparaître séparément des redevances.

## 3. Lecture du CARE

Le niveau de synthèse repose sur quatre grandeurs :

1. `total_produits`
2. `reversements_publics`
3. `charges_hors_reversements`
4. `resultat_avant_impot`

Contrôle :

`total_produits - reversements_publics - charges_hors_reversements = resultat_avant_impot` à l'arrondi près.

Les coûts sont ensuite agrégés en catégories lisibles. Exemple de catégories :

- personnel ;
- énergie ;
- achats d'eau ;
- traitement, matières, analyses ;
- sous-traitance / travaux ;
- renouvellement ;
- créances / contentieux ;
- services centraux / recherche ;
- impôts locaux / charges d'investissement ;
- autres dépenses.

L'agrégation doit être documentée et fondée sur les lignes du CARE, jamais sur une estimation non sourcée.

## 4. Lecture de la balance M49

### Flux à utiliser

Pour l'analyse annuelle, utiliser en priorité :

- `obnetdeb` : opérations budgétaires nettes au débit ;
- `obnetcre` : opérations budgétaires nettes au crédit.

Les champs `sd` et `sc` sont des soldes de fin de période et répondent à d'autres questions patrimoniales.

### Fonctionnement

| Préfixe | Catégorie |
|---|---|
| 60 | Achats et fournitures |
| 61 | Services extérieurs |
| 62 | Autres services extérieurs |
| 63 | Impôts et taxes |
| 64 | Personnel et charges sociales |
| 65 | Autres charges de gestion |
| 66 | Charges financières |
| 67 | Charges exceptionnelles |
| 68 | Dotations aux amortissements / provisions |

### Investissement

| Préfixe | Catégorie |
|---|---|
| 20 | Immobilisations incorporelles |
| 21 | Immobilisations corporelles |
| 23 | Immobilisations en cours / avances |

### Ressources

| Préfixe / sens | Catégorie |
|---|---|
| 70 crédit | Produits du service |
| 75 crédit | Autres produits de gestion |
| 77 crédit | Produits exceptionnels |
| 13 crédit | Subventions d'investissement |
| 16 crédit | Emprunts nouveaux |
| 16 débit | Remboursement du capital |

## 5. Ce que signifie « combien coûte réellement le service »

Il faut distinguer au minimum trois lectures :

- **coût d'exploitation du délégataire** : CARE ;
- **dépenses de fonctionnement de la collectivité** : M49 classes 6 ;
- **effort d'investissement de la collectivité** : M49 classes 2.

Ces trois valeurs ne doivent pas être additionnées mécaniquement pour annoncer un coût complet, car elles peuvent contenir des écritures comptables, des amortissements, des temporalités et des périmètres différents.

## 6. D'où vient l'argent en dehors de la facture ?

Pour la collectivité, distinguer :

- produits du service ;
- autres produits de gestion ;
- produits exceptionnels ;
- subventions d'investissement ;
- emprunts nouveaux.

Les produits exceptionnels doivent être explicitement signalés comme non récurrents sauf preuve contraire.

## 7. Millésimes

Le meilleur cas est un triplet de sources du même millésime. Si ce n'est pas possible, le décalage doit apparaître dans :

- le titre des feuilles ;
- l'encadré méthodologique ;
- le texte public.

## 8. Rédaction grand public

Le texte final suit le même ordre que les graphiques :

1. montant de la facture type et prix au m³ ;
2. répartition sur 100 € ;
3. explication de la part du délégataire ;
4. explication de la part de la collectivité ;
5. autres sources de financement ;
6. limites et différence de périmètre entre les sources.
