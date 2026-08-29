# État courant

```yaml
phase: douze_pages_livrees_ci_et_infra_posees_qualification_a_venir
lot: vague 5 corrigée (4e audit en cours) + CI 15 portes + infrastructure locale
branch: claude/vertex-connection-kgkntr
status: quatrieme_audit_adversarial_en_cours
last_good_commit: 2c5f540
completed:
  - vagues_1_a_4: fondation, sources, décision, 10 routes (PR #1 et #2 fusionnées)
  - vague_5: calendrier, opportunités, Vertex IA — 13 routes sur 13 réelles
  - audits_1_a_3: TROIS audits adversariaux, tous REJECT, chaque défaut reproduit par exécution
  - correctifs_3e_audit: P1-A/B/C/D (frontière IA par appartenance), P1-E/F (calendrier),
      P1-G (relais validés), P2-H/I/J/K/L/M/N — test reproducteur rouge avant chaque correctif
  - ci: .github/workflows/ci.yml — 6 jobs, 15 portes, actions épinglées par SHA de commit,
      images par digest immuable ; run 48f307d TOUT VERT
  - supply_chain: uv.lock 60 paquets exacts + 1035 hachages ; pip-audit et pnpm audit
      sans vulnérabilité ; SBOM CycloneDX 1.6 (53 composants)
  - securite: tools/check_secrets.py + allowlist auditée (l'allowlist ne peut pas cacher un secret)
  - infra: compose durci (loopback seul, non-root, lecture seule, digests) ;
      sauvegarde chiffrée à RESTAURATION VÉRIFIÉE (cycle complet exécuté vert)
  - worker: point d'entrée de production `python -m vertex_worker` (il n'en avait aucun)
checks_locaux:
  - "pytest 2257 passed / 0 failed"
  - "intégration PostgreSQL : 96 + 17 + 53 passed (SÉRIELLE obligatoire — base partagée)"
  - "vitest 254 passed ; tsc 0 erreur ; build OK"
  - "run_checks.sh TOUT VERT (8 portes locales) ; OpenAPI et client TS régénérés"
checks_ci:
  - "run 48f307d : garde-fous, unitaires 3.13, intégration PostgreSQL 18, web Node 24,
     e2e Chromium, supply-chain — 6 jobs sur 6 au vert"
pages_reelles: [/today, /markets, /system, /auth, /options, /analysis, /simulator, /portfolio, /follow-up, /performance, /calendar, /opportunities, /ai]
pages_non_implementees: []
reste_a_faire:
  - "4e audit adversarial : verdict attendu avant toute fusion"
  - "portes CI absentes : python-quality (ruff/mypy), web-quality (biome), migrations,
     performance, build d'images, provenance et signature"
  - "nettoyage ruff : 1256 violations, config posée mais AUCUNE porte ne l'applique"
  - "research/ (dossier 05) : walk-forward, calibration — absent"
  - "LOT-23 qualification : mutation, charge, chaos, Firefox/WebKit"
  - "LOT-24 release : machine cible, TWS réel, restauration, rollback, soak 5 séances"
  - "assainissement des chaînes relayées : résidu ouvert sur les 7 relais (DEBT.md)"
  - "AUCUNE donnée réelle n'a jamais été vue : tout est SYNTHETIC étiqueté, IBKR jamais contacté"
blocker: "B-02..B-05 (BLOCKERS.md) : inventaire donneur, Cloudflare, licence options, fournisseur IA"
next_command: "attendre le 4e audit — puis FUSIONNE LA VAGUE 5 s'il lève le rejet"
```
