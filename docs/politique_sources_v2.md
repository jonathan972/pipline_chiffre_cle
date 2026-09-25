# Politique de source v2 — Référentiel ODE Martinique

| Domaine | Source primaire | Source de contrôle / complément | Règle |
|---|---|---|---|
| Population municipale | INSEE — Melodi `DS_POPULATIONS_REFERENCE`, PMUN | Publications Insee | Utiliser le millésime N ; sinon dernière officielle disponible avec statut explicite. |
| Prélèvements, usages, volumes par ouvrage | BNPE | SISPEA / ODE | BNPE pour les volumes, pas pour l'inventaire exhaustif des captages. |
| Inventaire captages AEP | SISPEA / ODE / ARS | BNPE | Les coordonnées BNPE AEP peuvent être approchées. |
| Qualité sanitaire AEP | ARS | SISPEA | Conserver le millésime sanitaire exact. |
| Abonnés, réseaux, rendement, ILP, renouvellement | SISPEA | RPQS/RAD | Ne jamais moyenner simplement les pourcentages territoriaux. |
| Volumes produits/facturés lorsque SISPEA diverge | RPQS/RAD/ODE | SISPEA | Les définitions doivent être documentées. |
| STEU, capacité, conformité ERU | Portail national assainissement | DEAL / ODE / RPQS | Historiser les révisions et les changements de définition de conformité. |
| Boues AC | SISPEA / RPQS-RAD | Portail assainissement | Contrôle croisé. |
| ANC P301.3 | SISPEA si couverture complète | SPANC / RPQS | Bloquer la publication territoriale si tous les SPANC ne sont pas couverts. |
| Parc privé / patrimoine local | ODE / DEAL / RPQS-RAD | Sources nationales | Référentiel local millésimé. |

## Population

La population municipale est le dénominateur par défaut des ratios par habitant. Elle est stockée avec son propre millésime. Une valeur `DERNIERE_OFFICIELLE_DISPONIBLE` peut être utilisée opérationnellement lorsque N n'est pas encore publié, mais elle doit rester distinguée d'une population officielle de millésime N.
