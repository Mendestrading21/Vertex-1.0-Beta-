# État courant

```yaml
phase: foundation
lot: fondation multi-lots sur branche de travail unique (autorisation nuit du 2026-08-28)
folder: "00,01,02,03,04(socle),06(socle),08(noyau),10-12(socles),13-14(socle) livrés ; 07 et durcissement P2 en cours"
branch: claude/vertex-connection-kgkntr
status: running
last_good_commit: 9f25660
completed:
  - blueprint_imported
  - parcours_complet_plan_valide
  - dossier_00: ADR-014, enums alignées, denylist unifiée manifeste, BLOCKERS humains
  - vertex_core_contrats_et_moteurs: 926 tests (contracts, market, portfolio/perf/risk, options, decision, data)
  - options_durci: P0+4P1+P2 audits corrigés, oracle américain FD + 5 golden littérature
  - fusion_noyau: dédup 5 niveaux déterministe, relevance gates+budgets sync manifeste (112 tests)
  - persistance: observations/snapshots/outbox/ledger manuel + alembic sur PostgreSQL réel (91 tests, P1 bail outbox + unicité compensates corrigés)
  - api_socle: FastAPI fail-closed AUTH_NOT_IMPLEMENTED, advice/preview via l'unique AdviceEngine, OpenAPI déterministe (43 tests)
  - edge_ibkr_socle: port 13 méthodes, machine d'état epochs, pacing 38msg/s, sonde entitlement manifeste, readonly+StartupFetch(0) (93 tests)
  - web_shell: Vite/React19/TS strict, tokens Black Glass source unique, 12 routes honnêtes, 8 états (56 tests, bundle 98.6Ko gzip)
checks:
  - "python3 -m pytest -> 1251 passed (suite complète)"
  - "tests_integration PostgreSQL 16.13 -> verts"
  - "tsc --noEmit 0 erreur ; vitest 56/56 ; build 98584 o gzip"
  - "check_financial_boundary OK ; verify_blueprint OK ; compileall OK"
in_progress:
  - ingress_tradingview_socle (worker JS testé par fakes, orchestrateur revalidation IBKR, pack Pine v1)
  - persistance_durcissement_P2 (triggers snapshots, redaction last_error, DSN prod/test séparés, garde downgrade)
blocker: "B-01..B-05 (BLOCKERS.md) — fusion PR, revue inventaire, Cloudflare, licence options, fournisseur IA : humain"
environment_deviations:
  - "Python 3.11 local (cible CI 3.13) ; PostgreSQL 16 local (cible 18 par digest) ; Node 22 (cible 24 LTS) ; CI GitHub Actions à épingler SHA sur machine cible (lookup dépôts actions hors périmètre de session)"
next_command: "AUDITE LA PR #1 PUIS FUSIONNE (squash) — ou EXÉCUTE DOSSIER suivant sur cette branche"
```
