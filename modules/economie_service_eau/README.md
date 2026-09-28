# Analyse économique du service de l'eau

Module reproductible pour transformer trois familles de sources — **facture type**, **CARE du délégataire** et **balance comptable M49 de la collectivité** — en un même livrable Excel pédagogique destiné au grand public.

## Objectif

Répondre dans cet ordre à quatre questions simples :

1. **Qui reçoit les 100 € payés par l'usager ?**
2. **À quoi sert la part du délégataire ?**
3. **À quoi sert la part de la collectivité ?**
4. **D'où vient l'argent en dehors de la facture ?**

Le résultat attendu est un classeur Excel avec des tableaux audités, des camemberts successifs et un texte grand public. Le cas CAESM 2023/2024 sert d'exemple de référence.

## Principe essentiel

Les trois sources ne décrivent **pas le même périmètre comptable** :

- la **facture type** répartit ce que paie l'usager ;
- le **CARE** décrit l'économie du contrat exploité par le délégataire ;
- la **balance M49** décrit la comptabilité publique du service porté par la collectivité.

On les fait donc **se suivre**, mais on ne les force jamais à se réconcilier euro pour euro sans table de passage explicitement démontrée.

## Arborescence

```text
modules/economie_service_eau/
├── README.md
├── AGENTS.md
├── config/
│   ├── m49_mapping.csv
│   └── project.example.json
├── docs/
│   ├── CONTROLES_QUALITE.md
│   ├── DICTIONNAIRE_DONNEES.md
│   ├── METHODOLOGIE.md
│   └── MISE_EN_FORME.md
├── scripts/
│   ├── build_workbook_artifact_tool.py
│   ├── prepare_m49.py
│   └── validate_inputs.py
├── templates/
│   ├── care_couts.csv
│   ├── care_resume.csv
│   └── facture.csv
└── examples/caesm_2023_2024/
    ├── Analyse_prix_eau_CAESM_facture_CARE_M49.xlsx
    ├── care_couts.csv
    ├── care_resume.csv
    ├── facture.csv
    ├── project.json
    └── texte_public.md
```

## Réutiliser la méthode sur une autre année ou un autre territoire

### 1. Préparer le dossier projet

Copier `templates/` dans un nouveau dossier, puis renseigner :

- `facture.csv` à partir de la facture type 120 m³ ;
- `care_resume.csv` et `care_couts.csv` à partir du CARE ;
- le JSON de balance M49 ou les agrégats M49 produits par `prepare_m49.py` ;
- un fichier `project.json` dérivé de `config/project.example.json`.

### 2. Extraire la balance M49

```bash
python scripts/prepare_m49.py \
  --json /chemin/balance.json \
  --year 2024 \
  --water-budget EAU-COLLECTIVITE \
  --sanitation-budget ASST-COLLECTIVITE \
  --out-dir /chemin/projet/m49
```

Le mapping de comptes est dans `config/m49_mapping.csv` et peut être adapté si la nomenclature ou les comptes utilisés diffèrent.

### 3. Contrôler les entrées

```bash
python scripts/validate_inputs.py \
  --project /chemin/projet/project.json \
  --facture /chemin/projet/facture.csv \
  --care-resume /chemin/projet/care_resume.csv \
  --care-couts /chemin/projet/care_couts.csv
```

Les contrôles portent notamment sur :

- la somme de la facture ;
- la séparation **redevances / taxes / TVA** ;
- la cohérence du CARE : produits - charges - reversements = résultat ;
- la somme des postes de coûts du CARE ;
- l'alignement ou le décalage des millésimes.

### 4. Générer le classeur

Le script `build_workbook_artifact_tool.py` reconstruit le même parcours, les mêmes feuilles, la même palette et les mêmes familles de graphiques dans un environnement disposant de `artifact_tool`.

```bash
python scripts/build_workbook_artifact_tool.py \
  --project /chemin/projet/project.json \
  --facture /chemin/projet/facture.csv \
  --care-resume /chemin/projet/care_resume.csv \
  --care-couts /chemin/projet/care_couts.csv \
  --m49-dir /chemin/projet/m49 \
  --output /chemin/projet/analyse_prix_service.xlsx
```

Le classeur de référence `examples/caesm_2023_2024/Analyse_prix_eau_CAESM_facture_CARE_M49.xlsx` sert de **golden master visuel**.

## Règles de publication grand public

- Dire **« part du délégataire »**, jamais « bénéfice du délégataire ».
- Séparer les **redevances** des **taxes** : l'octroi de mer et la TVA ne sont pas des redevances.
- Ne pas présenter les produits exceptionnels comme une ressource annuelle normale.
- Ne pas additionner mécaniquement fonctionnement, investissement et remboursement du capital pour annoncer un « coût complet ».
- Toujours afficher les millésimes des sources, surtout s'ils diffèrent.
- Conserver un onglet de détail des sources et des calculs pour l'audit.

---

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

---

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

---

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
