# État courant

```yaml
phase: douze_pages_livrees_portes_ci_completees_lot_23_entame
lot: LOT-23 — qualité, politique, performance, chaos, accessibilité
branch: claude/vertex-connection-kgkntr
status: batterie_locale_TOUT_VERT_ci_verte_sur_5a40bc8
last_good_commit: 5a40bc8
completed:
  - vagues_1_a_5: 13 routes sur 13 réelles (PR #1, #2 et #3 fusionnées)
  - ci: 7 jobs, 25 portes nommées — VERTE sur 5a40bc8 ; actions épinglées par SHA de COMMIT
      (l'objet-tag annoté est refusé), images par digest, permissions
      read-all, timeout sur chaque job
  - portes_ajoutees_cette_session:
      - "web-quality (Biome) — 451 violations ramenées à 0, trois défauts
         d'accessibilité réels corrigés au passage"
      - "python-quality (ruff + mypy --strict) — 0 violation, 115 fichiers
         sans erreur de typage"
      - "policy — SHA d'actions, permissions, timeouts, pull_request_target,
         runners, digests d'images, dépendances épinglées, verrous, et le
         CÂBLAGE des portes elles-mêmes"
      - "release/notices — inventaire des 245 composants tiers, licences
         SPDX, fraîcheur des notices"
      - "performance — budgets MESURÉS, jamais déclarés"
      - "traceability — chaque interdiction absolue reliée à sa preuve :
         25 prouvées sur 30, 5 écarts écrits, datés et imprimés"
  - supply_chain: uv.lock exact + hachages ; pip-audit et pnpm audit sans
      vulnérabilité ; SBOM CycloneDX produite PAR LA CI
  - infra: compose durci (loopback seul, digests) ; sauvegarde chiffrée à
      restauration exécutée ; moindre privilège à trois rôles
  - research: walk-forward purgé, embargo effectif, calibration avec règle
      d'abstention, frontière anti-runtime testée
audits:
  - "HUIT audits adversariaux indépendants, TOUS conclus REJECT"
  - "chaque défaut reproduit par exécution, chaque correctif précédé d'un
     reproducteur rouge"
  - "la campagne chaos a trouvé une RÉGRESSION P0 pendant son écriture :
     isinstance(envelope, DataEnvelope[Any]) — une paramétrisation générique
     Pydantic est une classe distincte, toute l'ingestion était cassée"
  - "SIX chiffres de ce registre se sont révélés faux, dont un trois fois ;
     deux affirmations de sécurité ont été démenties par exécution"
mesures_reelles:
  bundle_initial_gzip: "118 291 octets (budget 307 200)"
  moteurs_de_graphes: "hors charge initiale — ECharts 205 ko, Lightweight 53 ko"
  accessibilite: "168 cas de test verts, 14 chemins × 3 viewports (Chromium seul)"
checks_locaux:
  - "pytest 3433 passed / 0 failed"
  - "intégration PostgreSQL : 96 (persistance) + 29 (worker, dont 12 chaos)
     + 65 (api) — exécution SÉRIELLE obligatoire, base partagée"
  - "vitest 337 passed ; tsc 0 erreur ; biome 0 violation"
  - "playwright Chromium 402 passed (dont 168 d'accessibilité)"
  - "playwright 3 moteurs (nightly 33312346908) : 659 passed, 3 failed —
     passkey CDP intestable hors Chromium, export WebKit à 1 fichier sur 2"
  - "ruff : All checks passed ; mypy --strict : 115 fichiers, 0 erreur"
  - "worker Cloudflare : 53 tests de contrat"
  - "run_checks.sh TOUT VERT"
pages_reelles: [/today, /markets, /system, /auth, /options, /analysis, /simulator, /portfolio, /follow-up, /performance, /calendar, /opportunities, /ai]
pages_non_implementees: []
ecarts_declares:
  - "WCAG 1.4.10 (reflow) NON CONFORME : plancher min-width 1024px, 384 px de
     débordement mesurés à 200 % de zoom — épinglé par test, inscrit à DEBT.md"
  - "revue lecteur d'écran par une personne : NON FAITE"
  - "latence API : AUCUNE mesure — p95 exige 1 000 échantillons, p99 en exige
     10 000, et le profil de référence n'existe pas avant LOT-24"
  - "tables non virtualisées : le budget de 160 lignes rendues n'est pas
     atteignable en l'état"
  - "Firefox et WebKit : workflow nocturne écrit, JAMAIS exécuté"
  - "provenance et signature de release : NON FAISABLES ici, déclarées absentes"
  - "mutation testing : TENTÉ deux fois avec mutmut, 6 017 mutants tous
     ignorés — la copie mutée n'est pas celle qu'importent les tests dans un
     workspace uv éditable. Outil retiré, cause écrite dans DEBT.md, score
     réel toujours INCONNU"
  - "5 interdictions absolues sur 30 ne sont pas prouvées par un test —
     détail dans manifests/traceability.yaml, imprimé à chaque exécution"
  - "AUCUNE donnée réelle n'a jamais été observée — IBKR jamais contacté,
     Cloudflare non déployé, Compose jamais exécuté (pas de démon Docker)"
blocages_humains:
  - "B-02 : revue de l'inventaire du dépôt donneur"
  - "B-03 : projet Cloudflare"
  - "B-04 : licence des données historiques d'options"
  - "B-05 : fournisseur d'IA (l'IA reste DISABLED, gabarit déterministe)"
  - "connecteur MCP Interactive_Brokers_IBKR : autorisation OAuth à faire
     depuis les réglages de connecteurs claude.ai (session non interactive)"
prochaine_commande: "AUDITE LOT 23"
```
