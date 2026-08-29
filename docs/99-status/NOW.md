# État courant

```yaml
phase: douze_pages_livrees_qualification_a_venir
lot: vague 5 terminée (Calendrier, Opportunités, Vertex IA) — 13 routes sur 13 réelles
branch: claude/vertex-connection-kgkntr
status: awaiting_third_audit_verdict
last_good_commit: e704b62
completed:
  - vagues_1_a_4: fondation, sources, décision, 10 routes (PR #1 et #2 fusionnées)
  - vague_5_backend: calendrier (révisions estimé/confirmé), opportunités (AdviceEngine + profil versionné), Vertex IA (gabarit déterministe, fournisseur désactivé B-05)
  - vague_5_audits: TROIS audits adversariaux ; 4 P0 et une vingtaine de P1/P2 corrigés avec reproducteur rouge d'abord
  - vague_5_web: /calendar /opportunities /ai réelles
  - registre_calculs: 23 entrées complétées, 22 APPROVED, garde-fou branché dans run_checks
checks:
  - "pytest 2059 passed"
  - "integration PostgreSQL 166 passed (execution SERIELLE obligatoire — base partagee)"
  - "vitest 254 passed ; tsc 0 erreur ; bundle initial 110,35 Ko gzip"
  - "playwright 234 passed (3 viewports + smoke 1024, axe 0 critique/serieuse)"
  - "run_checks.sh TOUT VERT ; OpenAPI et client TS coherents (aucun diff apres regeneration)"
pages_reelles: [/today, /markets, /system, /auth, /options, /analysis, /simulator, /portfolio, /follow-up, /performance, /calendar, /opportunities, /ai]
pages_non_implementees: []
reste_a_faire:
  - "CI GitHub Actions : AUCUN workflow n'existe — les 15 portes du blueprint ne tournent nulle part"
  - "infra/ : compose, sauvegarde, restauration — absent"
  - "research/ (dossier 05) : walk-forward, calibration — absent"
  - "LOT-23 qualification : mutation, charge, chaos, supply-chain (SBOM, signature, scans), Firefox/WebKit"
  - "LOT-24 release : installation machine cible, TWS reel, restauration, rollback, soak 5 seances"
  - "AUCUNE donnee reelle n'a jamais ete vue : tout est SYNTHETIC etiquete, IBKR jamais contacte"
blocker: "B-02..B-05 (BLOCKERS.md) : inventaire donneur, Cloudflare, licence options, fournisseur IA"
next_command: "AUDITE PUIS FUSIONNE LA VAGUE 5 — ou CONTINUE pour CI + infrastructure"
```
