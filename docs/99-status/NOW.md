# État courant

```yaml
phase: lot_24a_fusionne_sonde_entitlements_executable
lot: LOT-24b (sonde IBKR exécutable) + LOT-24c (fraîcheur au relais, P0)
branch: claude/vertex-connection-kgkntr
status: plus_aucun_relais_ne_sert_une_valeur_sans_dire_son_age
last_good_commit: 37a7097 (= origin/main, PR #6 fusionnée)
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
  - "SEPT chiffres de ce registre se sont révélés faux, dont un trois fois ;
     deux affirmations de sécurité ont été démenties par exécution. Le
     septième est le compte d'interdictions non prouvées ci-dessous : il
     disait 5, la porte dit 6 depuis la rétrogradation de
     EXCEPTION-JAMAIS-QUALIFIED"
fraicheur_au_relais:
  etat: "P0 FERMÉ — les 10 relais publient age_seconds dans tous les états
     datables ; 8 ne le faisaient pas"
  proprietaire_unique: "apps/api/src/vertex_api/freshness.py — calcul, budget et
     vocabulaire. Il MESURE et renvoie ; il ne décide pas, parce que calendar et
     opportunities ne décident pas pareil"
  budgets: "TTL de séance FERMÉE du registre versionné vertex_core.data.freshness.
     Aucun TTL n'est écrit dans l'API. Politique par relais LUE dans le worker :
     attention et review_queue -> news_attention, markets_overview, analysis et
     performance -> daily_bar, option_chain -> option_surface, portfolio ->
     portfolio_mark"
  capacites: "publient leur âge SANS budget — aucune politique du registre ne
     couvre cette famille, et la péremption d'une capacité appartient au
     expires_at de la sonde, champ par champ. Inventer un TTL ici aurait été la
     valeur non justifiée que ce dépôt refuse ailleurs"
  ce_qui_reste_ouvert: "la gate INTERNE au dossier affirme encore
     FRESH_AND_COHERENT à +71 h alors que sa fenêtre vaut 48 h. Le dossier n'est
     plus SILENCIEUX — il porte ses 255 600 secondes — mais il se CONTREDIT.
     EXCEPTION-JAMAIS-QUALIFIED reste donc NOT_YET_PROVEN, avec un critère de
     fermeture RESSERRÉ : promouvoir l'entrée sur son ancien critère aurait été
     gagner contre ma propre formulation, pas contre la règle"
sonde_entitlements:
  commande: "python3 tools/probe_entitlements.py --symbol <SYMBOLE> --dry-run"
  etat: "LIVRÉE et prouvée contre un port SIMULÉ — 16 tests. JAMAIS exécutée
     contre un vrai TWS : aucun TWS dans ce conteneur, aucun droit IBKR"
  ce_qu_elle_ferme: "vertex_edge_ibkr.probe implémentait la sonde complète
     depuis le LOT-04 et AUCUNE commande ne permettait de la lancer"
  refus_verifies: "identité ambiguë (2 contrats qualifiés) → arrêt, jamais
     « le premier » ; échéance, strike ou couple exchange/trading_class absent
     de la chaîne → refus ; option incomplètement nommée → refus ;
     client_id nul → refus par l'adaptateur ; --dry-run n'ouvre AUCUNE ligne
     de données ; erreur fournisseur 10197 → ERROR, jamais NOT_ENTITLED ;
     sans --persist rien n'est écrit"
  aucune_option_host: "il n'en existe pas — ne pas offrir le réglage est plus
     fort que le valider"
demarrage_local:
  commande: "bash tools/start_local.sh (après tools/bootstrap_local.py)"
  mesure: "API /api/v1/health → alive ; capabilities sans session → 401
     AUTH_REQUIRED ; interface → 200 ; depuis l'adresse non-loopback de la
     machine, les deux ports REFUSENT la connexion"
  semis: "48 enveloppes, 46 quotes, 12 chaînes, 4 barres, 21 événements,
     490 messages traités, 10 familles de snapshots publiées — tout SYNTHETIC"
  refus_verifies: "aucun DSN → code 2 ; base contenant déjà un journal → refus
     nommant la table et le compte ; base au nom de test → refus"
mesures_reelles:
  bundle_initial_gzip: "118 317 octets (budget 307 200)"
  moteurs_de_graphes: "hors charge initiale — ECharts 205 ko, Lightweight 53 ko"
  accessibilite: "168 cas de test verts, 14 chemins × 3 viewports (Chromium)"
  navigateurs: "Chromium, Firefox et WebKit VERTS — 665 passed, 2 skipped"
checks_locaux:
  - "pytest 3559 passed, 4 skipped, 0 failed (les 4 sautés exigent
     PostgreSQL réel : bootstrap local)"
  - "intégration PostgreSQL : 96 (persistance) + 32 (worker, dont 15 chaos)
     + 65 (api) — exécution SÉRIELLE obligatoire, base partagée. TOUS VERTS"
  - "vitest 386 passed ; tsc 0 erreur ; biome 0 violation (125 fichiers).
     Le 384 précédent était FAUX : mesuré à 383 sur le tree d'avant ce lot,
     huitième chiffre erroné de ce registre"
  - "playwright 405 passed sur les 4 profils desktop (dont 168 d'accessibilité)"
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
  - "Firefox et WebKit : VERTS (nightly 33314910817, 665 passed, 2 skipped)"
  - "provenance et signature de release : NON FAISABLES ici, déclarées absentes"
  - "mutation testing : TENTÉ deux fois avec mutmut, 6 017 mutants tous
     ignorés — la copie mutée n'est pas celle qu'importent les tests dans un
     workspace uv éditable. Outil retiré, cause écrite dans DEBT.md, score
     réel toujours INCONNU"
  - "6 interdictions absolues sur 30 ne sont pas prouvées par un test (24/30 prouvées) —
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
prochaine_commande: "Allumer TWS et lancer python3 tools/probe_entitlements.py --symbol <SYMBOLE> --dry-run"
```
