# Blocages

Décisions strictement humaines, en attente. Aucune n'est contournée par Claude.

| ID | Décision attendue | Dossier | Impact tant que non tranchée |
|---|---|---|---|
| ~~B-01~~ | ~~Auditer puis fusionner la PR #1 (bootstrap)~~ — **LEVÉ le 2026-09-05** | 00 | *Sans objet.* `main` porte 87 commits et 68 PR fusionnées ; il n'est plus au commit initial depuis longtemps. Cette ligne affirmait le contraire et n'avait pas été relue. |
| B-02 | Valider humainement `MIGRATION_INVENTORY.csv` (colonne `reviewed_by`) | 00 | Les vagues d'extraction donneur restent `planned`, aucune extraction de code donneur n'est exécutée |
| B-03 | Approuver le projet Cloudflare isolé (Workers/Queues Free) | 07 | L'ingress TradingView reste non déployé ; contrats et tests locaux seulement |
| B-04 | Licence des chaînes d'options historiques (coût) | 05 | Tout backtest options est étiqueté « simulation théorique » |
| B-05 | Choix du fournisseur IA et budget | 24 (LOT-21) | `VERTEX_AI_PROVIDER=disabled` ; gabarit déterministe seul |

**Pourquoi B-01 est barré plutôt que supprimé.** Un blocage levé garde sa
trace : sa disparition pure ferait croire qu'il n'a jamais existé, et rien
n'expliquerait pourquoi les lots 00 à 04 ont pu avancer. La mesure qui le lève
est vérifiable en une commande — `git log --oneline origin/main | wc -l`.

**Une liste de blocages périmée coûte plus qu'elle ne protège** : elle fait
croire bloqué ce qui ne l'est plus, et détourne d'un blocage réel. Relire cette
table à chaque fin de lot.

Les choix coût/licence restent volontairement différés aux lots qui en ont
besoin ; ils ne bloquent pas la fondation (dossiers 00–04, 10–12).
