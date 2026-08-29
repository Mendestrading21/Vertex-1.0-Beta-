# État courant

```yaml
phase: groupes_decider_et_piloter_livres
lot: vague 4 terminée (Portefeuille, Suivi, Performance)
branch: claude/vertex-connection-kgkntr (PR #2 brouillon)
status: paused_awaiting_human
last_good_commit: HEAD
completed:
  - vague_4_T1: thèses/revues append-only, projection pure (migration 0006)
  - vague_4_T2: valorisation FIFO fail-closed, journal, compensation net-nul, import CSV signé par hash
  - vague_4_T3: review_queue sans écriture de thèse, TWR/XIRR/drawdown quotidiens brut/net, population SYNTHETIC_MARKS_REAL_LEDGER
  - vague_4_web: /portfolio /follow-up /performance réelles + 60 E2E
  - incident_resolu: faux positifs scanner sur commentaires (reformulés, scan non affaibli)
checks:
  - "pytest 1740 passed + intégrations vertes ; vitest 200/200 ; tsc 0 erreur"
  - "playwright 156/156 ; bundle initial 110,2 Ko gzip ; axe 0 critique/sérieuse"
  - "boundary OK (0 finding) ; blueprint OK"
pages_reelles: [/today, /markets, /system, /auth, /options, /analysis, /simulator, /portfolio, /follow-up, /performance]
pages_non_implementees: [/calendar, /opportunities, /ai]
blocker: "B-02..B-05 inchangés (BLOCKERS.md)"
next_command: "AUDITE LA PR #2 PUIS FUSIONNE — ou CONTINUE pour Calendrier/Opportunités/Vertex IA (vague finale)"
```
