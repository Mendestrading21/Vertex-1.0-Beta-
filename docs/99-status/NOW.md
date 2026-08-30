# État courant

```yaml
phase: douze_pages_livrees_boucle_audit_correctif_en_cours
lot: 8e audit adversarial — correctifs en cours
branch: claude/vertex-connection-kgkntr
status: huitieme_audit_REJECT_correctifs_dispatches
last_good_commit: 0a83699
completed:
  - vagues_1_a_5: 13 routes sur 13 réelles (PR #1 et #2 fusionnées)
  - ci: 16 portes, 6 jobs, actions épinglées par SHA de commit, images par digest
      — VERTE sur les versions cibles Python 3.13 / Node 24 / PostgreSQL 18.6
  - supply_chain: uv.lock 60 paquets exacts + 1035 hachages ; pip-audit et
      pnpm audit sans vulnérabilité ; SBOM CycloneDX produite PAR LA CI
  - infra: compose durci (loopback seul, digests) ; sauvegarde chiffrée à
      restauration exécutée ; point d'entrée de production du worker
  - research: walk-forward purgé, embargo effectif, calibration avec règle
      d'abstention, frontière anti-runtime testée
audits:
  - "HUIT audits adversariaux indépendants, TOUS conclus REJECT"
  - "chaque défaut reproduit par exécution, chaque correctif précédé d'un
     reproducteur rouge"
  - "deux défauts du 7e audit et un du 8e étaient des RÉGRESSIONS de mes
     propres correctifs — la porte de frontière financière a été contournée
     trois fois de suite"
  - "SIX chiffres de ce registre se sont révélés faux, dont un trois fois ;
     deux affirmations de sécurité ont été démenties par exécution"
checks_locaux:
  - "pytest 3063 passed / 0 failed"
  - "intégration PostgreSQL : 96 (persistance) + 17 (worker) + 65 (api)
     — exécution SÉRIELLE obligatoire, base partagée"
  - "vitest 337 passed ; tsc 0 erreur ; playwright 234 passed"
  - "worker Cloudflare : 53 tests de contrat (branchés depuis le 6e audit)"
  - "run_checks.sh TOUT VERT"
pages_reelles: [/today, /markets, /system, /auth, /options, /analysis, /simulator, /portfolio, /follow-up, /performance, /calendar, /opportunities, /ai]
pages_non_implementees: []
en_cours:
  - "8e audit : P0 alias d'import contournant la frontière financière"
  - "8e audit : fusion de titres opposés à travers un symbole monétaire ou une espace"
  - "8e audit : feuilles numériques du contenu relayé sous aucun contrat"
  - "8e audit : rôle d'exécution propriétaire des tables — append-only auto-contournable"
  - "8e audit : verify-restore.sh estampille sans vérifier la restitution"
reste_a_faire:
  - "portes CI absentes : ruff/mypy, biome, migrations, performance, images, signature"
  - "nettoyage ruff : 1634 violations, config posée mais AUCUNE porte ne l'applique,
     et ruff n'est épinglé nulle part donc le compte n'est pas reproductible"
  - "LOT-23 qualification : mutation, charge, chaos, Firefox/WebKit"
  - "LOT-24 release : machine cible, TWS réel, restauration, rollback, soak"
  - "AUCUNE donnée réelle n'a jamais été vue : tout est SYNTHETIC étiqueté"
blocker: "B-02..B-05 (BLOCKERS.md) : inventaire donneur, Cloudflare, licence options, fournisseur IA"
next_command: "attendre les correctifs du 8e audit, puis 9e audit avant toute fusion"
```
