# Blocages

Décisions strictement humaines, en attente. Aucune n'est contournée par Claude.

| ID | Décision attendue | Dossier | Impact tant que non tranchée |
|---|---|---|---|
| B-01 | Auditer puis fusionner la PR #1 (bootstrap) et les commits suivants de la branche `claude/vertex-connection-kgkntr` | 00 | `main` reste au commit initial ; tout le travail vit sur la branche de travail |
| B-02 | Valider humainement `MIGRATION_INVENTORY.csv` (colonne `reviewed_by`) | 00 | Les vagues d'extraction donneur restent `planned`, aucune extraction de code donneur n'est exécutée |
| B-03 | Approuver le projet Cloudflare isolé (Workers/Queues Free) | 07 | L'ingress TradingView reste non déployé ; contrats et tests locaux seulement |
| B-04 | Licence des chaînes d'options historiques (coût) | 05 | Tout backtest options est étiqueté « simulation théorique » |
| B-05 | Choix du fournisseur IA et budget | 24 (LOT-21) | `VERTEX_AI_PROVIDER=disabled` ; gabarit déterministe seul |

Les choix coût/licence restent volontairement différés aux lots qui en ont
besoin ; ils ne bloquent pas la fondation (dossiers 00–04, 10–12).
