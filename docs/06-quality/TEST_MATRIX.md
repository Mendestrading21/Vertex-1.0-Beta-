# Matrice de tests

| Surface | Unitaires | Propriétés/oracle | Contrats/intégration | E2E/visuel | Résilience/sécurité |
|---|---|---|---|---|---|
| Identité/temps/unités | parsing et règles | round-trip, DST, bornes | JSON Schema + DB | — | entrées malicieuses |
| Ingestion IBKR | mapping/états | ordre/idempotence | TWS simulé + PostgreSQL réel | santé Système | reconnexion, pacing, denylist |
| TradingView | validation/dédoublonnage | replay/hors ordre | Worker/Queue/edge | import utilisateur | rate limit, DLQ, anti-rejeu |
| Data Fusion | liens/clusters/ranking | stabilité/dédup | sources partielles | news/calendrier | droits et conflits |
| Options/quant | formules/limites | QuantLib + invariants | snapshots cohérents | chaîne/simulateur | NaN, extrêmes, stale |
| Portefeuille | lots/flux/FX | conservation/agrégation | ledger PostgreSQL | saisie/réconciliation | correction et restore |
| Décision | gates/transitions | déterminisme/calibration | provenance complète | AdviceResult affiché | fail-closed |
| API/jobs | services/permissions | idempotence | PostgreSQL/outbox/OpenAPI | SSE/reconnexion | auth, panne DB |
| PWA/pages | hooks/composants | — | client généré | 12 parcours × 3 tailles | axe, offline, stale |
| IA | schéma/citations | — | gateway mock strict | réponses/indisponibilité | injection, fuite, timeout |
| Release | — | reproductibilité | install/migrations | smoke complet | SBOM, backup, rollback, soak |

## Jeux de données

- `synthetic` : scénarios minimaux, aucun droit externe ;
- `contracts` : enveloppes valides/invalides versionnées ;
- `golden` : vecteurs numériques dérivés indépendamment et revus ;
- `replay` : événements synthétiques dupliqués, retardés et hors ordre ;
- jamais de donnée de compte, de secret ou d'article sous droits dans Git.

## Politique d'échec

Un test critique instable est un défaut produit : il bloque la PR. Aucun retry global ne masque une course. Les tests dépendant d'un abonnement réel sont des probes contrôlées sur la machine cible ; leurs résultats alimentent la matrice de capacités sans être requis dans une CI GitHub non autorisée.

