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
ingestion_ibkr_continue:
  statut: "IMPLEMENTEE ET TESTEE — JAMAIS EXECUTEE CONTRE UN TWS REEL"
  pourquoi: "apps/edge-ibkr avait l'adaptateur, la machine a etats, le pacing et
     la sonde, mais AUCUN point d'entree : rien ne les faisait tourner en boucle.
     Les pages ne pouvaient donc jamais quitter population=SYNTHETIC, par absence
     de processus et non par choix de conception."
  fichiers_ajoutes:
    - "apps/edge-ibkr/src/vertex_edge_ibkr/universe.py — univers borne (24 max),
       con_id exacts obligatoires, toute ambiguite arrete l'ingestion"
    - "apps/edge-ibkr/src/vertex_edge_ibkr/runner.py — EdgeIbkrRunner ; decouple
       de SQLAlchemy derriere le protocole ObservationSink"
    - "tools/run_edge_ibkr.py — point d'entree + puits PostgreSQL reel. Place
       dans tools/ et NON dans le paquet : l'y mettre imposait des dependances
       vertex-persistence/vertex-worker qui tiraient SQLAlchemy, numpy et scipy
       dans la fermeture de l'adaptateur et modifiaient uv.lock au-dela de
       l'intention (mesure : 8 wheels greenlet retirees). Motif repris de
       tools/probe_entitlements.py — zero dependance ajoutee, verrou intact."
  preuves:
    - "40 tests unitaires avec fakes : reconnexion, epochs, 1101/1102/1300/502,
       plafond de lignes, refus de file, annulation dans un finally, arret propre"
    - "4 tests d'integration contre PostgreSQL REEL : provenance ibkr conservee,
       travail de fusion mis en file, rejeu idempotent, epoch perime jamais ecrit"
    - "suite ajoutee a la porte --integration de run_checks.sh (4 suites au lieu de 3)"
    - "ruff : All checks passed ; mypy --strict : 122 fichiers, 0 erreur"
    - "frontiere financiere : 0 appel interdit, {ok: true, findings: []}"
  non_prouve:
    - "AUCUNE execution contre un TWS reel, ni Paper ni Live"
    - "le plafond de lignes (defaut 2) n'est PAS une mesure du droit reel du
       compte : il est volontairement conservateur et l'elever exige de mesurer"
    - "aucune donnee de marche reelle n'a transite par ce processus"
trois_regimes_de_collecte:
  pourquoi: "IBKR impose trois contraintes de NATURE differente. Le temps reel est
     borne par les LIGNES de donnees (~100 par compte), l'historique par le TEMPS
     (60 requetes / 10 min), la decouverte par la CADENCE (1 scan/s). Une seule
     commande ne peut pas les couvrir : Vertex en a trois, avec trois client_id
     distincts (71, 72, 73) — deux clients API partageant un identifiant se
     deconnectent mutuellement."
  temps_reel:
    commande: "tools/run_edge_ibkr.py (client_id 71)"
    portee: "quelques dizaines d'instruments — plafond MAX_UNIVERSE_SIZE = 24"
    limite: "une ligne de donnees de marche par instrument"
  profondeur:
    commande: "tools/run_edge_history.py (client_id 72)"
    portee: "des MILLIERS — plafond MAX_HISTORICAL_UNIVERSE_SIZE = 5000"
    limite: "60 requetes / 10 min glissantes, soit 6/min. ~2 h 50 pour 1000 titres"
    consomme_des_lignes: false
    reprenable: "oui — ingest_envelope est idempotent sur event_id"
  largeur:
    commande: "tools/run_edge_discovery.py (client_id 73)"
    portee: "tout le marche, classement calcule chez IBKR"
    limite: "50 lignes par scan, 1 scan/s, une ligne de donnees a la fois"
    nature: "DECLENCHEUR, jamais un verdict — ni prix canonique, ni decision"
  impossible: "des milliers d'instruments en TEMPS REEL simultane. Le plafond de
     lignes d'IBKR l'interdit — chez tout le monde, pas seulement ici."
  preuves:
    - "SlidingWindowPacer : 14 tests, dont le debit soutenable de 6/min"
    - "HistoryBackfiller : 16 tests, dont un qui VERIFIE que les ~2 h 50
       annoncees pour 1000 titres sont bien ce que le code produit"
    - "ScannerDiscovery : 14 tests, dont la ligne toujours relachee sur erreur"
    - "ruff : All checks passed ; mypy --strict : 126 fichiers, 0 erreur"
    - "frontiere financiere : 0 appel interdit"
  non_prouve:
    - "les regimes TEMPS REEL et DECOUVERTE n'ont jamais tourne contre un TWS reel"
    - "le regime HISTORIQUE, lui, a tourne : 251 barres quotidiennes GOOG ingerees"
affichage_reel_mesure:
  date: "2026-08-31, base vertex_live, VERTEX_FUSION_PROFILE=real"
  pages_en_population_REAL:
    - "Marches : v251, GOOG cloture 342.88, recus 1/1"
    - "Aujourd'hui : v253"
    - "Analyse : 251 barres du 2025-08-29 au 2026-08-28, 0 ecartee"
    - "Opportunites : 1 candidate examinee, 0 qualifiee (BLOCKED)"
  pages_sans_donnees:
    - "Options : aucun collecteur de chaine COTEE n'existe. L'adaptateur ne
       produit que la DEFINITION de chaine (echeances, strikes), jamais les
       contrats cotes que la page exige. Et le droit de cotation d'option
       reste NON CONCLUANT : la sonde a tourne marche ferme"
    - "Calendrier : `calendar.py` n'admet que `synthetic-calendar-event/`
       alors que l'adaptateur emet `ibkr.corporate-events/1` ; et Wall Street
       Horizon est un abonnement payant distinct. Prefixe NON declare
       deliberement : rien n'a pu etre verifie contre une donnee reelle"
    - "Systeme : aucun snapshot de capacites, la sonde n'a jamais tourne
       avec --persist"
    - "Portefeuille / Performance : aucune transaction saisie (donnee
       utilisateur, absence normale)"
  honnetete_verifiee:
    - "Analyse publie fresh=false a 3,5 j : vendredi etait la derniere seance,
       la page l'avoue au lieu de paraitre a jour"
    - "Opportunites publie BLOCKED : la porte d'adequation au portefeuille
       exige des positions reelles, jamais satisfaite par declaration"
  defauts_reveles_et_corriges:
    - "`analysis.py` n'admettait que `synthetic-daily-bars/` : 251 barres
       reelles en base, ZERO lue. Page vide sans message, sans erreur, sans
       journal. Corrige par le schema derive `ibkr.daily-bars/1`, dont la
       forme est verifiee contre le validateur REEL du consommateur"
    - "`profiles.py` placait des con_id dans les univers d'Analyse, Options,
       Calendrier et Opportunites, alors que ces pages comparent un TICKER
       porte par la charge utile (analysis.py:676, options.py:603). Aucune
       n'aurait jamais pu apparier une donnee. Un test gravait ce defaut au
       lieu de le detecter"
    - "la fenetre d'Opportunites restait a 72 h : la cloture de vendredi a
       83 h le lundi, donc INSUFFICIENT_DATA chaque debut de semaine"
    - "les cinq raccourcis du bureau sourcaient .vertex/env (base SYNTHETIQUE)
       au lieu de .vertex/env.live ; scans.json et univers-large.json
       n'existaient pas. Aucun raccourci n'aurait produit d'affichage reel"
sonde_ibkr_reelle:
  date: "2026-08-31, session TWS Live sur 7496, client_id 71, GOOG con_id 208813720"
  droits_PROUVES:
    - "actions US carnet haut : bid, ask, last, volume — temps reel (type 1)"
    - "Greeks options en direct : delta, gamma, vega, theta, implied_volatility (tick 13)"
    - "volatilite historique 30j (23), volatilite implicite 30j (24)"
    - "volume moyen d'options (87), volume de l'option (8)"
    - "definition de chaine : 20 bourses, 17 echeances, 107 strikes"
  non_concluants: "bid/ask/last de l'option, open interest, volume call/put du
     sous-jacent — marche US ferme au moment de la sonde, AUCUN tick recu"
  not_entitled: "AUCUN. Aucun droit manquant n'a ete demontre."
  defaut_revele_et_corrige: "le code IBKR 2104 (« Market data farm connection is
     OK », une NOTICE) etait classe comme une erreur et masquait NO_OBSERVATION.
     Plage 2100-2200 declaree au manifeste, 20 tests de non-regression."
outillage_cloudflare:
  wrangler: "4.127.1 epingle exactement dans apps/ingress-tradingview/worker,
     licence MIT OR Apache-2.0, 31 paquets installes, toutes licences permissives"
  ecart: "tools/check_notices.py n'inventorie que uv.lock et apps/web/pnpm-lock.yaml :
     le verrou du Worker n'est PAS couvert par la porte release/notices.
     Ecart ecrit dans THIRD_PARTY_NOTICES.md plutot que laisse silencieux."
  deploiement: "AUCUN — B-03 en attente"
prochaine_commande: "Redemarrer la pile pour que le worker charge le code
   corrige (le processus en cours date d'avant la correction), puis, avec
   l'accord explicite de l'utilisateur, probe_entitlements.py --persist
   pour que /system cesse d'afficher NEVER_TESTED"
```
