# Carte du futur dépôt

| Zone | Chemins principaux | Responsabilité |
|---|---|---|
| Applications | `apps/api`, `apps/worker`, `apps/edge-ibkr`, `apps/edge-official`, `apps/web`, `apps/ingress-tradingview` | Processus déployables et composition |
| Cœur Python | `packages/python/vertex_core` | contrats, instruments, données, calculs, gates, décision et cas d'usage |
| Web partagé | `packages/typescript/api-client`, `ui`, `charts` | client OpenAPI généré, design system et adaptateurs visuels |
| Contrats | `contracts/json-schema`, `events`, `examples`, `openapi` | formats versionnés indépendants du transport |
| Recherche | `research/notebooks`, `pipelines`, `benchmarks`, `datasets-manifest` | expériences hors runtime, point-in-time |
| Infrastructure | `infra/compose`, `cloudflare`, `tailscale`, `monitoring`, `backup` | exécution locale, ingress et exploitation |
| Fixtures | `fixtures/synthetic`, `contracts`, `golden` | données testables sans donnée privée |
| Tests | `tests/unit`, `property`, `contract`, `integration`, `e2e`, `visual`, `performance`, `security`, `resilience` | preuves de correction et de robustesse |
| Documentation | `docs/00-foundation` à `docs/99-status` | décisions, spécifications, livraison et état |

L'arborescence applicative est créée au LOT-01. Les dossiers de documentation présents dans ce kit sont la spécification, pas du code de production.
