# Rapport de contrôle canonique

Ce module produit un DOCX de contrôle à partir du master et de la couverture du
nouveau pipeline. Il ne reproduit pas encore la maquette éditoriale du rapport
ODE 2022 : le template Word original n'a pas été transmis.

Règles non négociables :

- seules les lignes `PRODUCTION` sont affichées comme valeurs ;
- les lignes `VALIDATION`, `DIAGNOSTIC` et `AUDIT` apparaissent uniquement dans
  le préflight sous la forme « à valider » ;
- le mode final est bloqué tant que la certification est `NOT_CERTIFIED` ;
- toutes les cellules attendues reçoivent une ligne dans le préflight.

Le moteur est appelé par `application.core.build_report()`.
