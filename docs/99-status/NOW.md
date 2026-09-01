# État courant

```yaml
phase: rattrapage_complet_autorise
lot: LOT-04 (CI verte), LOT-05 (marque canonique), LOT-06 (arbitrage des pages),
     LOT-07 (/system → /sources-reports), LOT-08 (/performance → Portefeuille),
     LOT-09 (conformité du shell), LOT-10 (création de Catalyseurs),
     LOT-11 (inspecteur contextuel du shell), LOT-12 (/ai → inspecteur),
     LOT-13 et LOT-13b (motif d'inspecteur unifié : plus aucun dialogue modal),
     LOT-14 (ticker du shell, point 4 de l'anatomie canonique),
     LOT-25 (bord lecture seule des sources officielles),
     LOT-26 (SEC EDGAR point-in-time jusqu'au snapshot et à l'API)
branch: lot/26-sec-edgar-pit
status: lot_26_pr_13_ci_107_verte_7_sur_7
last_good_commit: bdf9f306 (= origin/main, CI 7/7 verte)
lots_de_cette_session:
  - "LOT-04 — la purge de session effaçait l'erreur 401 qu'elle devait laisser
     voir. CI ROUGE à l'arrivée sur b09b3785 : 3 échecs e2e/auth.spec.ts sur les
     trois viewports. Cause : `previous !== 'unauthenticated'` était vrai dès le
     PREMIER 401 puisque l'état initial est 'unknown'. Corrigé en
     `previous === 'authenticated'`. Reproducteur écrit avant le correctif."
  - "LOT-05 — le rail portait le monogramme VX, nommément interdit par
     references/canonical-visual.md, et un texte adjacent que l'anatomie
     canonique interdit aussi. Remplacés par un polyèdre facetté SVG héritant
     de currentColor. L'écart a disparu des target_gaps du script d'audit."
  - "LOT-06 — table d'arbitrage actuel → cible → décision, exigée par le skill
     avant tout renommage ou fusion. Décision humaine : ABSORBER."
  - "LOT-07 — première ligne de la table exécutée : la destination `system`
     devient Sources & Rapports. Renommage complet (clé, routes, glyphe, CSS,
     composant, spec e2e, libellés docs) plus une redirection permanente
     /system → /sources-reports. La route API /v1/system/capabilities n'a PAS
     bougé : règle 2 de l'arbitrage. Le volet ÉTENDRE (lignage, incidents,
     rapports) n'est ni livré ni simulé."
  - "LOT-08 — deuxième absorption : le module Performance entier rejoint
     Portefeuille et /performance est redirigée. Le rail passe à ONZE
     destinations réelles ; l'écart aux douze est journalisé, jamais comblé
     par une façade. Contradiction trouvée dans le skill maître : son script
     d'inventaire normalisait performance->charts et follow-up->risks, ce que
     son propre contrat des douze pages contredit. Script corrigé, contrat
     inchangé."
  - "LOT-09 — conformité du shell à l'anatomie canonique, mesurée dans un vrai
     navigateur. Cinq écarts, tous invisibles aux 399 tests existants :
     (1) le rail portait une plaque (dégradé + bordure + ombre) que le point 2
     interdit ; (2) chaque icône portait une pastille et l'item actif une barre
     latérale au lieu de la capsule ambre du point 3 ; (3) la marque était une
     tuile dégradée argent→ambre ombrée, barrée d'une diagonale ambre vif, avec
     un glyphe NOIR — le point 1 demande un glyphe facetté argent ; (4) le
     cartouche VERTEX 1.0 BETA du point 7 avait sa règle CSS mais AUCUN
     composant ne le rendait, et l'édition occupait le haut à droite que le
     point 5 réserve au mode, à la cloche et à la fraîcheur ; (5) le masque de
     la marque était SILENCIEUSEMENT invalide — `url()` non guillemeté sur une
     data URI — donc calculé à `none`, et le carré se remplissait entièrement.
     Le point 5 n'est PAS livré : ni cloche, ni badge de mode, ni fraîcheur de
     shell n'ont de propriétaire canonique, et les dessiner sans source serait
     une façade."
  - "LOT-10 — création de la DOUZIÈME destination, Catalyseurs, et absorption
     de /follow-up. Elle n'ajoute aucun endpoint : elle croise deux snapshots
     déjà servis — calendar/global, dont chaque événement porte déjà son
     event_context (thèses et positions touchées), et review_queue/global.
     Le croisement ne crée aucune donnée : une thèse citée par un événement
     mais absente de la file est DITE absente, jamais complétée, et les
     événements non reliés sont comptés, jamais masqués. Les deux requêtes
     restent indépendantes : hors ligne, chacune affiche SON état, avec un
     message distinct — un seul bandeau partagé masquerait le cas où une
     seule des deux sources tombe. Le widget « consensus fourni » que le
     contrat §10 nomme n'a AUCUN champ dans le contrat d'agenda : il est
     déclaré absent à l'écran, pas approximé."
  - "LOT-11 — l'inspecteur contextuel du shell, point 6 de l'anatomie
     canonique, existait dans la capture et nulle part dans le code. Il est
     désormais un EMPLACEMENT du shell rempli PAR LA PAGE, jamais un composant
     qui lirait les données lui-même. Deux propriétés le tiennent : aucune
     colonne morte (l'aside n'occupe la grille que si une page y a monté un
     panneau — une colonne vide en permanence serait de la chrome
     décorative), et aucun panneau ne survit à la page qui l'a monté.
     Premier remplissage : Catalyseurs, dont le contrat §10 fixe exactement le
     contenu — source, fuseau, historique, instruments liés, incertitude. Les
     cinq sont relayés verbatim. L'« incertitude » est FACTUELLE (statut
     estimé/confirmé, révisions, conflits, fraîcheur déclarée), jamais une
     probabilité : le contrat d'agenda n'en publie aucune, et une probabilité
     sans calibration est interdite. L'inspecteur le DIT à l'écran."
  - "LOT-12 — dernière absorption : /ai quitte le rail. Le contrat serveur ne
     connaît que TROIS sujets explicables, qui sont exactement les dossiers
     d'Analyse et de Portefeuille : l'explication est donc montée dans
     l'inspecteur de ces deux pages, et le sélecteur de sujet est remplacé par
     les dossiers RÉELLEMENT ouverts sur la page hôte — l'ancien laissait
     choisir un sujet qu'aucune page n'affichait. Défaut RÉVÉLÉ par
     l'absorption et corrigé dans le même lot : une réponse hors contrat
     faisait planter ClaimsBlock sur « catalog is not iterable », et l'erreur
     remontait jusqu'à la frontière de route — un panneau accessoire faisait
     disparaître la PAGE ENTIÈRE, dossier financier compris. Garde de forme
     ajoutée, testée et falsifiée. Le rail passe à DIX destinations, et AUCUNE
     route historique ne reste à arbitrer."
  - "LOT-13 — DEUX motifs d'inspecteur coexistaient : le panneau persistant du
     shell livré au LOT-11, et deux dialogues MODAUX hérités sur Aujourd'hui et
     Options, qui portaient les mêmes noms de classes. L'anatomie canonique
     n'en décrit qu'un — « le shell reste identique sur les douze
     destinations » — et la capture montre une colonne persistante. Le motif
     est tranché en faveur du panneau du shell ; Aujourd'hui est converti.
     LE PIÈGE DE FOCUS EST RETIRÉ, ET C'EST LA CORRECTION, PAS UN
     AFFAIBLISSEMENT : un piège n'est correct que pour un dialogue modal, où le
     reste de la page est justement inerte. Sur un panneau NON modal, il
     enfermerait l'utilisateur hors de sa propre page. Les deux assertions qui
     l'exigeaient sont remplacées par leur contrepartie CORRECTE — depuis le
     dernier élément du panneau, la tabulation SORT vers le reste de la page —
     et le focus entrant, `Échap` et la restitution du focus sont conservés.
     Deux défauts introduits par la conversion, trouvés et corrigés : le focus
     n'entrait plus dans le panneau (monté par PORTAIL, le nœud d'accueil n'est
     pas résolu au premier rendu, donc un `useEffect([])` ne trouve rien à
     focaliser — remplacé par une ref de rappel) ; et `.vx-sheet` restait une
     surcouche `position: fixed` pleine hauteur, ombrée et floutée, que la
     couche Titanium Ledger lui redonnait EN PLUS."
  - "LOT-13b — Options convertie avec la même recette. Il ne reste plus AUCUN
     `role=\"dialog\"` ni `aria-modal` dans le rendu : les seules occurrences
     restantes sont des commentaires qui expliquent pourquoi ils ont disparu.
     La conversion s'est réduite au composant et à ses assertions, parce que
     les deux défauts d'Aujourd'hui étaient déjà corrigés à la racine — la ref
     de rappel vit dans le composant, la règle `.vx-sheet` dans la feuille
     partagée. Rien de nouveau ici : la première conversion avait payé le coût."
  - "LOT-14 — point 4 de l'anatomie canonique, le ticker horizontal. Il était
     déclaré OUVERT dans DEBT.md au motif qu'il « exige […] un contrat ».
     C'était FAUX : `/api/v1/markets/overview` publie `MarketsTicker` depuis la
     première vague — ticker, dernier cours, rendement 1 j, devise, qualité,
     drapeau synthétique, jour de séance — TOUS calculés et formatés par le
     worker. Dixième affirmation erronée de ce registre, et la MÊME erreur
     qu'au LOT-10 sur Catalyseurs : une capacité déclarée « sans contrat »
     l'était par défaut de vérification. Ce qui restait vraiment était une
     décision de charge réseau ; elle est prise et bornée — même clé de
     requête que la page Marchés (donc une seule requête sur /markets) et
     `staleTime: Infinity`, donc aucun trafic de fond. La bande n'affiche
     AUCUN chiffre qu'elle ne peut qualifier : hors ligne, sans session, sans
     instantané ou en erreur, elle dit ce qui manque. Elle ne trie pas
     (l'ordre est celui du worker), elle ne bouge pas, et elle porte SA
     population et SA fraîcheur — les poser en haut à droite (point 5) leur
     donnerait une portée applicative qu'aucune source ne publie, `population`
     étant un champ PAR instantané. Le point 5 reste donc vide, et c'est
     désormais argumenté."
mesures_de_cette_session:
  - "playwright : 405 passed après LOT-07 (le job CI qui était rouge), puis
     399 passed après LOT-08. La baisse de 6 est intégralement expliquée dans
     PAGE_ARBITRATION.md : -12 contrôles d'accessibilité sur une route devenue
     une redirection (le même DOM est balayé via /portfolio), +6 tests de
     redirection permanente. Aucun test supprimé. Puis 417 après LOT-09 :
     +18 = six mesures d'anatomie canonique x trois viewports, dans le nouveau
     e2e/shell-canonical.spec.ts. Puis 432 après LOT-10, +15 décomposés :
     +9 la timeline de Catalyseurs (3 tests x 3 viewports) ; -6 les deux
     tests de redirection sortis de portfolio-performance.spec.ts ; +12 le
     nouveau e2e/legacy-redirects.spec.ts (4 x 3), qui couvre les TROIS
     redirections au lieu de deux. Aucun test supprimé : follow-up.spec.ts
     est devenu catalysts.spec.ts, ses 6 tests intacts (27 = 9 x 3). Puis
     435 après LOT-11 (+3 = une mesure d'inspecteur x 3 viewports), puis 429
     après LOT-12 : -12 les quatre contrôles d'accessibilité sur /ai devenue
     une redirection (le même DOM est balayé via /analysis et /portfolio),
     +3 la redirection /ai -> /analysis, +3 l'invariant « jamais d'explication
     sans le bandeau B-05 ». Aucun test supprimé : ai.spec.ts est devenu
     ai-inspector.spec.ts. Puis 432 après LOT-13, +3 décomposés : le test
     unique « panneau latéral accessible au clavier (Entrée, piège de focus,
     Échap) » d'Aujourd'hui est SCINDÉ en deux — « inspecteur accessible au
     clavier (Entrée, focus entrant, Échap) » et « le panneau n'est PLUS modal
     et ne piège plus le clavier » — soit +1 test x 3 viewports. LOT-13b ne
     déclare AUCUN test nouveau : il ne change que les assertions
     d'options.spec.ts, donc 432 inchangé."
  - "vitest : 424 passed / 31 fichiers ; tsc 0 ; biome 0 (135 fichiers) — mesuré
     après LOT-13b"
  - "pytest : 3766 passed, 4 skipped — mesuré sur 35d48cb"
  - "run_checks.sh : TOUT VERT"
  - "audit_titanium_ledger.py après LOT-10 : empreinte canonique vérifiée,
     écart unique = 'charts, risks' à créer. AUCUNE route historique ne
     reste à arbitrer : les quatre lignes de la table sont exécutées"
  - "falsification LOT-07 : `Navigate` sans `replace` fait rougir
     routes.test.tsx avec `expected 'PUSH' to be 'REPLACE'`"
  - "falsification LOT-09 : retirer les guillemets de `url()` dans BrandMark
     fait rougir shell-canonical.spec.ts avec `Expected: not \"none\"`"

active_work:
  - "LOT-26 — SEC EDGAR : contrats Filing/FundamentalFact, disponibilité PIT,
     corrections et conflits sans élection silencieuse, ingestion append-only,
     snapshot par instrument, relais API protégé et runner one-shot. Aucun
     branchement AdviceEngine/Analyse/Opportunités."
  - "Qualification LOT-26 : 3797 tests Python collectés, 4 intégrations
     PostgreSQL ignorées hors base ; run_checks.sh atteint == TOUT VERT == ;
     Biome 142 fichiers, mypy strict 139 sources, Vitest 434/434, build Vite
     et budget Chromium verts."
  - "CI #106 sur b338fec : garde-fous, Ruff/mypy, unitaires et supply-chain
     verts ; job web rouge uniquement parce que schema.d.ts n'avait pas été
     régénéré après OpenAPI. Reproducteur exact : pnpm gen:api puis git diff
     --exit-code -- src. Fichier généré ajouté au correctif."
  - "CI #107 sur 747db7b : 7 jobs sur 7 verts après correctif — garde-fous,
     Ruff/mypy strict, unitaires Python, intégration PostgreSQL 18, web,
     supply-chain et E2E Chromium sur trois viewports avec axe."
  - "LOT-25 — PR brouillon #12 : adaptateurs HTTPS bornés pour SEC EDGAR,
     FRED/ALFRED, OpenFIGI, BCE et BNS, plus configuration locale et sonde live
     explicite. FMP et ORATS restent désactivés ; WSH reste dans l'adaptateur
     IBKR existant. Aucun secret ni payload réel n'a été poussé."
  - "Publication autorisée et effectuée sur lot/25-official-source-adapters,
     empilée sur codex/vertex-rattrapage-complet-20260831. Aucune fusion
     automatique."
  - "commande utilisateur reçue : EXÉCUTE VERTEX RATTRAPAGE COMPLET"
  - "autorité canonique extraite du commit 72d55629 sans reprendre sa branche
     divergée comme base de code"
  - "capture canonique et six planches de pages intégrées au skill maître"
  - "ordre d'exécution : fermer les P0, stabiliser données/runtime, reconstruire
     le shell, puis traiter les douze pages et la qualification finale"
  - "aucune fusion ni publication automatique ; recette TWS/IBKR réelle différée
     au poste utilisateur avec données de marché exclues de Git"
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
pages_reelles: [/today, /opportunities, /analysis, /options, /simulator,
                /calendar, /markets, /portfolio, /catalysts,
                /sources-reports, plus /auth hors rail]
pages_non_implementees: []
destinations_cibles_manquantes: [charts, risks]
# Bloquées par un CONTRAT SERVEUR absent, pas par une décision d'interface.
# Vérifié le 2026-09-01 contre les 30 routes du contrat OpenAPI : ni `charts`
# ni `risks`, et ni la comparaison de séries (Graphiques) ni la sévérité par
# risque (Risques) ne sont dérivables sans calculer un rendement ou un score
# dans le navigateur — tous deux interdits. Raisonnement complet dans
# docs/05-design/PAGE_ARBITRATION.md.
redirections_permanentes: ["/system -> /sources-reports", "/performance -> /portfolio",
                           "/follow-up -> /catalysts", "/ai -> /analysis"]
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
lot_25_validation_locale:
  pr: "https://github.com/Mendestrading21/Vertex-1.0-Beta-/pull/12"
  commit_distant_avant_correctif_ci: "90685bae172187995dec63b0e97a6db4dd1e636d"
  controles_verts:
    - "compilation Python du nouveau package"
    - "tests du bord officiel : 14/14"
    - "ruff : 0 violation"
    - "mypy --strict : 144 fichiers, 0 erreur"
    - "uv lock --check --offline"
    - "verify_blueprint : OK, 26 lots"
    - "policy : OK"
    - "secrets : 0 secret sur 781 fichiers suivis"
    - "frontière financière : 0 appel interdit"
    - "notices et traceability : OK"
  ci_98:
    resultat: "6 jobs verts sur 7 ; seul Ruff rouge"
    cause: "RUF022 sur l'ordre de __all__ et RUF100 sur un noqa devenu inutile"
    correction: "les deux lignes sont corrigées et revalidées localement avant push"
  ci_99:
    commit: "3a8df77bdb3895c641e96bd0eb557522bcfe9961"
    resultat: "7 jobs sur 7 verts"
    preuves: "Ruff et mypy strict, tests unitaires Python, PostgreSQL 18, web,
       garde-fous, supply chain et E2E Chromium sur trois viewports"
  note_environnement_local: "la suite pytest complète a rencontré uniquement le
     proxy SOCKS injecté par l'environnement sur un test HTTP localhost ; le test
     isolé repasse vert avec les variables proxy retirées. Le job unitaire CI #98,
     sans cette particularité, était déjà vert."
prochaine_commande: "VALIDE PR #13 — relire humainement LOT-26 puis décider de sa
   fusion. Après validation seulement, ouvrir LOT-27 pour FRED/ALFRED PIT. Les
   clés, identifiants et droits fournisseurs restent exclusivement locaux."
```
