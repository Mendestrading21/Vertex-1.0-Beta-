# État courant

```yaml
phase: reference_canonique_et_skill_audit_complet_prets_a_revue
lot: LOT-10 — système visuel complet Titanium Ledger
branch: lot/10-obsidian-theme-refresh
status: ready_for_human_review
last_good_commit: 940e3a7 (= origin/main, baseline locale web verte)
active_work:
  - "décision utilisateur verrouillée : la capture Black Glass avec symbole
     facetté argent, rail gauche fin, ticker supérieur et panneaux graphite
     translucides est l'unique référence de style ; aucune autre variante"
  - "skill Titanium Ledger étendu : la commande ANALYSE déclenche désormais un
     audit intégral en lecture seule (Git, architecture, données, calculs,
     intégrations, sécurité, 12 pages, accessibilité, performance, CI et ops)"
  - "assets du skill : capture canonique et six planches couvrant Aujourd'hui,
     Marchés, Opportunités, Analyse, Options, Simulateur, Portefeuille,
     Graphiques, Risques, Catalyseurs, Calendrier et Sources & Rapports"
  - "direction finale : Titanium Ledger Black Glass conforme exclusivement à la
     capture canonique verrouillée par SHA-256 ; graphite gris-vert, fond noir
     pétrole discret, titane et ambre rare"
  - "périmètre : identité, tokens, shell et langage des objets, tableaux,
     graphiques et widgets des 12 pages ; aucun contrat API, calcul financier,
     gate ou source de données modifié"
  - "implémentation actuelle à reconstruire : monogramme VX et anciennes routes
     restent présents ; le script les signale comme écarts sans les modifier"
  - "validation finale locale : Biome 0 violation, TypeScript 0 erreur,
     Vitest 390/390, build Vite vert ; bundle initial gzip 124072 octets,
     moteurs graphiques hors fermeture initiale"
  - "E2E/captures non exécutés localement : PostgreSQL jetable et Chromium
     absents ; exécution attendue en CI avant validation humaine"
  - "skill maître ajouté : vertex-titanium-ledger route l'audit, la recherche
     officielle, l'identité, les objets, graphiques, douze compositions, QA,
     performance et livraison GitHub"
  - "ordre cible : Aujourd'hui, Marchés, Opportunités, Analyse, Options,
     Simulateur, Portefeuille, Graphiques, Risques, Catalyseurs, Calendrier,
     Sources & Rapports ; Alertes reste globale"
  - "validation du skill : quick_validate PASS, ruff PASS, py_compile PASS ;
     inventaire non mutant opérationnel et statut TARGET_GAPS attendu avant
     reconstruction (Catalyseurs absent, 4 routes à arbitrer, logo VX à retirer)"
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
         24 prouvées sur 30, 6 écarts écrits, datés et imprimés. Les 67
         citations nomment un test précis (58 pointaient un fichier entier),
         la correspondance est exacte, et le champ `text` est confronté mot
         pour mot à la règle (14 entrées divergeaient)"
      - "release/notices --verify — chaque licence relue chez le
         distributeur : 245 relues, 0 injoignable, 0 divergence. Le blanchiment
         LGPL-3.0-only → MIT par deux `sed` cohérents est détecté"
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
  - "NEUVIÈME audit : six contournements de plus, tous reproduits puis fermés
     — allowlist de secrets non balayée, licence jamais reconfrontée à sa
     source, bundle 32x au-dessus du budget accepté par la porte, matrice
     comptant des déclarations, deux mutants survivants, profil à autorité
     absolue sans métadonnées"
  - "SIX chiffres de ce registre se sont révélés faux, dont un trois fois ;
     deux affirmations de sécurité ont été démenties par exécution"
mesures_reelles:
  bundle_initial_gzip: "118 317 octets (budget 307 200)"
  moteurs_de_graphes: "hors charge initiale — ECharts 205 ko, Lightweight 53 ko"
  accessibilite: "168 cas de test verts, 14 chemins × 3 viewports (Chromium)"
  navigateurs: "Chromium, Firefox et WebKit VERTS — 665 passed, 2 skipped"
checks_locaux:
  - "pytest 3501 passed / 0 failed"
  - "intégration PostgreSQL : 96 (persistance) + 32 (worker, dont 15 chaos)
     + 65 (api) — exécution SÉRIELLE obligatoire, base partagée"
  - "vitest 384 passed ; tsc 0 erreur ; biome 0 violation (125 fichiers)"
  - "playwright Chromium 402 passed (dont 168 d'accessibilité)"
  - "playwright 3 moteurs (nightly 33314910817) : 665 passed, 2 skipped,
     0 failed en 11,2 min — Chromium, Firefox et WebKit. Première mesure
     verte hors Chromium ; les 2 sautés sont la passkey, intestable hors CDP"
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
prochaine_commande: "PLAN LOT 11 — RECONSTRUCTION TITANIUM LEDGER"
```
