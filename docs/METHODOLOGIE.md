# Méthodologie et sources

## Cycle de traitement

1. Archiver la source brute et son contexte de téléchargement.
2. Séparer année de référence, date du snapshot et date d'import.
3. Normaliser sans corriger silencieusement.
4. Rattacher au bon territoire et au bon périmètre contractuel.
5. Calculer les indicateurs dérivés en conservant numérateur et dénominateur.
6. Comparer aux RAD/RPQS et au rapport ODE connu.
7. Attribuer `coverage_status`, `quality_status` et `record_role`.
8. Consolider, dédupliquer par priorité de rôle et produire le manifeste SHA-256.
9. Certifier le millésime selon les règles de `REGLES_METIER.md`.

## Sources nationales

### SISPEA

Les exports AEP, AC et ANC sont importés au niveau service. Les exports historiques peuvent être révisés longtemps après leur exercice ; la date et l'empreinte du snapshot sont obligatoires. SISPEA reste soumis à contrôle renforcé pour les périmètres Robert–Trinité/CAP Nord.

### BNPE

La BNPE est la référence pour les volumes prélevés par ouvrage. Elle ne constitue pas un inventaire patrimonial exhaustif des captages ; elle ne doit pas servir seule pour `RES_007/008/009`.

### ERU/STEU

Les stations `Urbain` de capacité strictement positive reproduisent les 103 STEU publiques du rapport 2022. La définition de conformité change à partir de 2023 et doit rester versionnée. Les petites stations et le parc privé nécessitent des sources locales complémentaires.

### ARS/Hub'Eau

L'API renvoie plusieurs analyses par prélèvement. L'ETL déduplique d'abord par `code_prelevement`, puis agrège la conformité microbiologique et physico-chimique. Ces résultats restent `DIAGNOSTIC / TO_VALIDATE_AGAINST_RPQS` jusqu'à validation complète.

### INSEE

La population municipale est utilisée pour éviter les doubles comptes. Si le millésime N n'est pas encore publié, le dernier millésime officiel est conservé avec un statut explicite de décalage.

## Sources locales

Les RAD et RPQS sont la vérité prioritaire pour les périmètres contractuels, certains volumes, le patrimoine et les méthodes spécifiques. Une extraction locale doit toujours conserver le nom du document, la page, la définition et les éventuelles limites de ventilation.

## Reproductibilité

Les fichiers `run_manifest.json` enregistrent les sources utilisées, leurs empreintes, le nombre de lignes par rôle et les alertes. Les gros snapshots Hub'Eau ne sont pas dans Git ; leurs empreintes sont inventoriées et les données dérivées sont versionnées.
