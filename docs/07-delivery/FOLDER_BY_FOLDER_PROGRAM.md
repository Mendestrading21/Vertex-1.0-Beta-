# Programme dossier par dossier

## Règle

Un dossier logique est planifié, implémenté, audité et accepté avant le suivant.
Chaque dossier possède un propriétaire, des dépendances, une source donneuse
éventuelle, des tests, un benchmark et un rollback. Les imports temporaires
entre donneur et cible sont interdits.

Les numéros ci-dessous décrivent les dossiers de capacité. Les lots restent les
unités de PR ; un lot peut contenir plusieurs petits dossiers seulement s'ils
ont le même propriétaire et la même preuve.

## Ordre de construction

| Dossier | Cible dans Beta | Donneur à auditer | Sortie obligatoire |
|---:|---|---|---|
| 00 | `.claude/`, `docs/00-foundation/`, `docs/09-adr/`, `manifests/` | `.claude/`, `CLAUDE.md`, tests d'invariants | autorité unique, rôles repo et inventaire validés |
| 01 | `contracts/` | `vertex/domain`, `vertex/data_sources/models.py`, `vertex/visualization/schemas.py` | schémas versionnés, exemples et compatibilité |
| 02 | `packages/python/vertex_core/identity/` | `vertex/domain/instruments.py` | identité instrument/exchange/devise exacte |
| 03 | `packages/python/vertex_core/data/` | qualité, provenance, réconciliation, temporal evidence | observations point-in-time et états honnêtes |
| 04 | `packages/python/vertex_core/calculations/` | fonctions pures options/risque/performance | oracles, propriétés, unités et précision |
| 05 | `research/` | `vertex/research`, `vertex/validation` | protocole walk-forward/calibration sans fuite |
| 06 | `apps/edge-ibkr/` | adapters IBKR market-data-only | entitlement probe, pacing et zéro capacité interdite |
| 07 | `apps/ingress-tradingview/` | webhook/store TradingView | signature, anti-replay, Pine non-repaint et ACK durable |
| 08 | `packages/python/vertex_core/fusion/` | news, événements, entreprises, secteurs | déduplication, droits et moteur de pertinence |
| 09 | `packages/python/vertex_core/options/` | `vertex/options`, anomalies et moteurs associés | chaîne, IV/Greeks, liquidité, anomalies honnêtes |
| 10 | `packages/python/vertex_core/decision/` | profils, packets, moteurs de décision comme référence | gates et `AdviceEngine` unique avec abstention |
| 11 | stockage et migrations | `vertex/storage`, positions/portfolio manuels | PostgreSQL/outbox, journal et migration idempotente |
| 12 | `apps/api/`, `apps/worker/` | routes/services/jobs utiles comme référence | OpenAPI, jobs durables, observabilité et budgets |
| 13 | `packages/typescript/ui/`, `charts/`, `design-assets/` | tokens, chart spec et captures sélectionnées | design Black Glass bureau, icônes et widgets |
| 14 | `apps/web/src/shell/` | shell/navigation comme comportement seulement | shell bureau accessible, aucun calcul financier |
| 15 | `apps/web/src/pages/today/` | briefing/current changes | page Aujourd'hui complète |
| 16 | `apps/web/src/pages/calendar/` | calendrier/events | page Calendrier complète |
| 17 | `apps/web/src/pages/markets/` | market/regime/sectors | page Marchés complète |
| 18 | `apps/web/src/pages/opportunities/` | scanner/funnel | page Opportunités complète |
| 19 | `apps/web/src/pages/analysis/` | analysis/evidence/chart | page Analyse complète |
| 20 | `apps/web/src/pages/options/` | options pages/widget lab | page Options complète |
| 21 | `apps/web/src/pages/simulator/` | scenario pricer/multileg lab | page Simulateur complète |
| 22 | `apps/web/src/pages/portfolio/` | portefeuille/positions manuels | page Portefeuille complète |
| 23 | `apps/web/src/pages/follow-up/`, `performance/` | tracking/performance | Suivi et Performance sans mélange réel/théorique |
| 24 | `apps/web/src/pages/vertex-ai/`, `system/` | AI gateway/health/audits | explication sourcée et page Sources & Rapports exhaustive |
| 25 | `tests/`, `infra/`, release | tests et scripts donneurs sélectionnés | qualification, restauration, soak et RC bureau |

## Cycle de chaque dossier

```text
PLAN -> DONOR AUDIT -> CONTRACT -> TESTS RED -> IMPLEMENT -> TESTS GREEN
-> MUTATION/PERF -> VISUAL QA si UI -> REVIEW -> ACCEPTED
```

Le statut vit dans `docs/99-status/NOW.md`. Un dossier `BLOCKED` n'est pas
contourné en commençant le suivant.

## Paquet de preuve

Chaque dossier rend :

- dépôt/branche/commit cible et commit donneur ;
- chemins ajoutés, adaptés et refusés ;
- contrat public et propriétaire ;
- tests réellement exécutés avec codes de sortie ;
- couverture et mutation applicables ;
- benchmark avant/après ou mention non applicable ;
- droits/licences et scan frontière ;
- captures bureau si interface ;
- migration/rollback ;
- risque restant et une seule prochaine commande.

## Règles UI phase 1

- bureau/laptop uniquement ;
- références de validation : 1280×800, 1440×900 et 1600×1000 ;
- pas de bottom navigation, `MobileActionBar`, breakpoint téléphone ou capture
  390 px ;
- navigation clavier, zoom 200 %, contraste et reduced motion restent requis ;
- les composants gardent une structure sémantique qui permettra un futur lot
  mobile, sans le construire maintenant.

