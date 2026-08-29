# ADR-005 — Ingress TradingView public isolé

- Statut : Accepté
- Date : 2026-08-28
- Portée : alertes Pine, Cloudflare Worker, Queue, edge local

## Contexte

TradingView doit envoyer des alertes vers une URL publique avec une réponse rapide. Le runtime Vertex reste privé et ne doit pas être directement exposé. TradingView ne fournit pas une signature HMAC de bout en bout que Vertex pourrait considérer comme une preuve cryptographique native.

## Décision

Le flux est TradingView vers Worker Cloudflare, puis Queue avec DLQ, puis agent local en pull sortant.

- Le Worker accepte uniquement POST JSON sur une route secrète dédiée.
- Il applique taille maximale, schéma strict, fenêtre temporelle, identifiant d’alerte, déduplication, rate limit et allowlist IP officielle.
- Le secret est comparé en temps constant ; il réduit le risque mais n’est pas présenté comme une signature TradingView.
- Le Worker écrit dans Queue avant de retourner 202 et n’exécute aucun calcul financier.
- L’agent local s’authentifie au service de pull, valide à nouveau le schéma et accuse réception après commit PostgreSQL.
- Une alerte déclenche une reprise de quote IBKR fraîche et une évaluation complète ; elle n’est ni un prix canonique ni un verdict.
- Les messages invalides ou épuisés vont en DLQ avec métadonnées expurgées et alertes.

## Conséquences

### Positives

- Aucun port entrant sur le poste Vertex.
- Absorption des pointes, retries et indisponibilités locales.
- Contrôle de replay et preuve de commit avant suppression.

### Coûts et contraintes

- Dépendance à Cloudflare pour les nouvelles alertes.
- Livraison au moins une fois : tous les consommateurs doivent être idempotents.
- Deux plans d’observabilité et un runbook DLQ sont nécessaires.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Webhook direct vers FastAPI local | Exposerait le runtime privé |
| Tailscale Funnel | Ouvrirait publiquement un service local |
| Croire à une signature native TradingView | Contrôle inexistant |
| Calculer ou décider dans le Worker | Créerait une seconde autorité |
| Accuser avant écriture durable | Risque de perte silencieuse |

## Critères de réexamen

Le fournisseur d’ingress peut changer si les mêmes propriétés sont prouvées : isolation publique, validation stricte, stockage durable, DLQ, pull sortant, idempotence et aucune donnée de portefeuille.
