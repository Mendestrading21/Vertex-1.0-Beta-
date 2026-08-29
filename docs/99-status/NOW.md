# État courant

```yaml
phase: foundation_plus_first_pages
lot: vague 2 terminée (auth, chaîne de données, 3 pages réelles, E2E)
folder: "00-14 socles + pages 15 (Aujourd'hui), 17 (Marchés), 26/System livrées"
branch: claude/vertex-connection-kgkntr
status: paused_awaiting_human
last_good_commit: b89f100
completed:
  - vague_1_fondation: vertex_core (contrats, 25 calculs, décision, qualité, fusion), persistance append-only + outbox, edge IBKR info-only, ingress TradingView, API fail-closed, shell web Black Glass
  - vague_2_T1_auth: passkey WebAuthn réelle, sessions hachées, CSRF, clone sign_count révoqué (217 tests)
  - vague_2_T2_worker: chaîne outbox->fusion->snapshot attention, générateur SYNTHETIC gardé (90 tests)
  - vague_2_T3_api: routes attention/capabilities/SSE signal-only (107 tests)
  - vague_2_T4T5T6_web: pages /system /today /auth réelles, client généré, E2E Playwright pipeline réel + WebAuthn virtuel (87 vitest, 29 e2e)
  - vague_2_T7_markets: page /markets bout-en-bout, ECharts lazy, breadth fail-closed (42 e2e au total)
checks:
  - "pytest 1519 passed + 106 intégration PostgreSQL réelle"
  - "vitest 105/105 ; tsc strict 0 erreur ; bundle initial 109,5 Ko gzip"
  - "playwright 42/42 (1280/1440/1600 + smoke 1024, axe 0 critique/sérieuse)"
  - "check_financial_boundary OK ; verify_blueprint OK"
pages_reelles: [/today, /markets, /system, /auth]
pages_non_implementees: [/calendar, /opportunities, /analysis, /options, /simulator, /portfolio, /follow-up, /performance, /ai]
blocker: "B-01..B-05 (BLOCKERS.md) inchangés — fusion PR, revue inventaire, Cloudflare, licence options, fournisseur IA"
environment_deviations:
  - "Python 3.11 / PostgreSQL 16 / Node 22 locaux (cibles 3.13 / 18-digest / 24 LTS) ; CI Actions SHA à poser sur machine cible"
next_command: "AUDITE LA PR #1 PUIS FUSIONNE (squash) — puis CONTINUE pour les pages Options/Analyse/Simulateur"
```
