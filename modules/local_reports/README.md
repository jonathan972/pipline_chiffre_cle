# Module RAD / RPQS locaux — v6

Le parseur extrait les données des rapports locaux. La réconciliation territoriale est désormais effectuée ensuite par `modules/perimeters/reconcile_perimeters.py`.

## Points majeurs
- `CAP_NORD_CONTRAT_SME` est un ancien libellé d'extraction et n'est plus utilisé directement dans le référentiel maître.
- Le contrat CAP Nord 2020-2024 est identifié par `CAP_NORD_DSP_2020_2024`.
- Les tableaux détaillés du RAD montrent des secteurs partiels `Robert CN` et `Trinité CN`.
- Les secteurs restants de Robert et Trinité relèvent de `ROBERT_TRINITE_EXSICSM`.
- L'Ex-SICSM complet reste `EX_SICSM_DSP_2015_2027` pour les données hydrauliques non ventilables.
- Les volumes `facturé clientèle`, `facturé hydraulique`, `comptabilisé` et `vendu RPQS` sont distincts.
- Les révisions historiques sont conservées en AUDIT au lieu d'être écrasées.
