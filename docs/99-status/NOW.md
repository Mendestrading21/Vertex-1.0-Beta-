# État courant

```yaml
phase: rattrapage_complet_autorise
lot: LOT-04 (CI verte), LOT-05 (marque canonique), LOT-06 (arbitrage des pages),
     LOT-07 (/system → /sources-reports), LOT-08 (/performance → Portefeuille),
     LOT-09 (conformité du shell), LOT-10 (création de Catalyseurs),
     LOT-11 (inspecteur contextuel du shell), LOT-12 (/ai → inspecteur),
     LOT-13 et LOT-13b (motif d'inspecteur unifié : plus aucun dialogue modal),
     LOT-14 (ticker du shell, point 4 de l'anatomie canonique)
branch: codex/vertex-rattrapage-complet-20260831
status: ci_reparee_puis_execution_en_cours_sans_fusion_automatique
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
     écart unique = 'charts' à créer (Risques installée le 2026-09-01). AUCUNE route historique ne
     reste à arbitrer : les quatre lignes de la table sont exécutées"
  - "falsification LOT-07 : `Navigate` sans `replace` fait rougir
     routes.test.tsx avec `expected 'PUSH' to be 'REPLACE'`"
  - "falsification LOT-09 : retirer les guillemets de `url()` dans BrandMark
     fait rougir shell-canonical.spec.ts avec `Expected: not \"none\"`"

active_work:
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
                /calendar, /markets, /portfolio, /risks, /catalysts,
                /sources-reports, plus /auth hors rail]
pages_non_implementees: []
destinations_cibles_manquantes: [charts]
# Graphiques reste bloquée par un CONTRAT SERVEUR absent : la comparaison de
# séries rebasées n'est pas dérivable sans calculer un rendement dans le
# navigateur, ce qui est interdit. Raisonnement dans PAGE_ARBITRATION.md.
#
# RISQUES A ÉTÉ INSTALLÉE le 2026-09-01, et son contrat a été CRÉÉ plutôt
# qu'attendu : `risk.correlation` déclaré au registre des calculs, publié par
# `vertex_worker.risk` dans `risk_matrix/global`, relayé par
# `GET /api/v1/risk/matrix`. La matrice arrive RENDUE EN CHAÎNES et les
# bandes de couleur arrivent sous forme de NOMS — le navigateur ne calcule ni
# n'arrondit ni ne reclasse rien.
#
# ELLE N'EST PAS FINIE POUR AUTANT. Le blueprint décrit « la matrice des
# risques avec exposition, horizon, SÉVÉRITÉ et preuve » ; ce qui est livré
# est la matrice de CORRÉLATION. La sévérité par risque suppose un barème,
# c'est-à-dire une décision d'utilisateur — comme le périmètre et l'indice de
# référence, elle sera DÉCLARÉE, jamais devinée par le code.
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
  - "Cloudflare non déployé, Compose jamais exécuté (pas de démon Docker)"
  - "IBKR A ÉTÉ CONTACTÉ le 2026-08-31 depuis la machine de bureau, en API
     lecture seule sur loopback : sonde de droits, découverte scanner puis
     remplissage historique. 36 864 observations réelles, 153 instruments.
     Détail mesuré dans `affichage_reel_mesure` plus bas. La ligne qui
     précédait affirmait le contraire et n'avait pas été relue : ce dépôt
     refuse qu'un écran affirme ce qu'il n'a pas mesuré, son propre
     document d'état se doit la même règle."
  - "RIEN de ces données réelles n'existe en intégration continue : la
     collecte dépend de TWS, qui tourne sur la machine de l'utilisateur.
     Toute population observée en CI reste SYNTHETIC."
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
prochaine_commande: "PR #11 (brouillon) porte LOT-07 a LOT-13b et attend une
   VALIDATION HUMAINE : aucune fusion automatique. Risques est installee depuis
   le 2026-09-01 avec la matrice de correlation, son contrat serveur ayant ete
   CREE plutot qu'attendu. Deux choses restent, et ce sont des DECISIONS
   d'utilisateur, pas du code : le bareme de SEVERITE que le blueprint attend
   pour Risques, et le perimetre affiche (huit indices mondiaux aujourd'hui,
   declares dans profiles.RISK_PERIMETER). Graphiques reste bloquee par un
   contrat serveur absent : une serie rebasee exigerait un rendement calcule
   dans le navigateur. Le travail non bloque qui reste est la refonte Titanium
   Ledger des onze destinations contre la capture canonique, aux viewports
   1280, 1440 et 1600"
```

## REPRISE 2026-09-01 — etat mesure en fin de session

### Corrige et pousse

**`_CODE_RE` admet le `$`** (`apps/api/src/vertex_api/snapshot_views.py`).
IBKR News encastre l'`article_id` du fournisseur dans l'`event_id`, et cet
article_id porte un `$` (`DJ-RT$1e0664c8`). Mesure : 6108 observations
concernees, 1207 valeurs refusees sur 170 tetes publiees, soit **72 reponses
HTTP en 500** (1 `attention`, 71 des 162 dossiers `analysis`).

Verification : tetes servies **91/163 avant, 162/163 apres**. La seule encore
refusee est `analysis/GNL PRE`, dont le caractere fautif est l'ESPACE — et
elle est inatteignable de toute facon (`UNDERLYING_PATTERN` la refuse en 422).
NE PAS annoncer « zero identifiant hors forme ».

Test reproducteur ecrit AVANT le correctif (`.claude/rules/testing.md`) :
17 rouges, puis verts. Il porte des identifiants RELEVES en base. Le defaut de
fond etait que tout le corpus de test est frappe par Vertex
(`synthetic-dev:{seed}:{index:04d}`) : aucune identite de fournisseur reelle
n'avait jamais traverse le relais.

**Page Risques installee** (`LEDGER 09`), avec `risk.correlation` declare au
registre des calculs, publie par `vertex_worker.risk` et relaye par
`GET /api/v1/risk/matrix`. Mesure sur donnees reelles : 8 indices, 242
rendements, du 2025-09-02 au 2026-08-31.

**Acces local ouvert** (`VERTEX_AUTH_OPEN_LOCAL=1`, pose dans
`~/.vertex/env.live`) : Vertex ne demande plus de passkey. FERME PAR DEFAUT —
sans la variable, 401 partout, verifie sur sept routes.

### Reste casse — MESURE, a corriger

**Huit etiquettes de population qui mentent.** Le bandeau `population` est
juste ; c'est le texte autour qui ment.

| Emplacement | Texte | Verdict |
|---|---|---|
| `apps/web/src/pages/markets/MarketsPage.tsx:99` | « Carte des marches synthetiques » | faux (`population='REAL'`, 0/161 synthetic) |
| `MarketsPage.tsx:119` | « `synthetic-dev` via snapshot worker » | faux (source `ibkr`) |
| `MarketsPage.tsx:83` | repli « Carte des marches synthetiques » | faux, latent |
| `MarketsPage.tsx:202` | « Poids = parts descriptives des clotures (synthetiques) » | faux |
| `MarketsPage.tsx:206` | « Limites : donnees SYNTHETIQUES de developpement » | faux |
| `apps/worker/src/vertex_worker/markets.py:362` | « Sur N instruments synthetiques attendus » | faux, PERSISTE dans le contenu |
| `apps/worker/src/vertex_worker/portfolio.py:117` et `:825` | `MARK_POPULATION_SYNTHETIC` ecrit inconditionnellement | faux (marques issues de `markets_overview` en `REAL`) |
| `apps/worker/src/vertex_worker/performance.py:136` et `:810` | `marks = "SYNTHETIC"` | faux, meme cause (`ledger: USER_DECLARED` est juste) |

**`data_state='partial'` trompeur sur Marches.** `markets.py:581` declenche
`partial` sur `rejected_records`, alimente par 3 cotations `GNL PRE` — des
observations EN TROP, hors univers, pas un trou de couverture. L'ecran affiche
« Donnees partielles » puis « 161 couverts sur 161, 0 ecartes » : un texte qui
se refute lui-meme. Confusion entre `discarded` (attendu manquant) et
`rejected_records` (non demande). Meme pollution sur `performance/1`.

**500 latent sur Risques.** `value` est dans `_DECIMAL_KEYS`
(`snapshot_views.py:890`, classe NON SIGNEE) alors que
`extremes.most_opposed.value` vaut `-0.803` — une correlation « la plus
opposee » est negative par definition. La route rend 200 aujourd'hui parce que
`risk.py:300` appelle son propre validateur `checked_risk_content`. Toute
uniformisation qui la brancherait sur le garde commun la mettrait en 500.
Correction : deplacer `"value"` vers `_SIGNED_DECIMAL_KEYS` (`:896`). COMMIT
SEPARE — `value` sert aussi a `breadth.value` (`:1649`).

**Trou E2E.** `apps/web/e2e/analysis.spec.ts` et `today.spec.ts` sont passes
au vert pendant que les deux routes rendaient 500 : le semis
(`e2e/seed_synthetic.py`) ne produit aucun identifiant de fournisseur. Semer
au moins un cluster de presse en forme reelle
`ibkr:news:<provider>:<provider>$<hex>`.

### Decisions d'UTILISATEUR qui bloquent la suite

Aucune ne se deduit du code :

1. **Bareme de severite** de la page Risques. Le blueprint decrit « la matrice
   des risques avec exposition, horizon, SEVERITE et preuve » ; seule la
   matrice de correlation est livree.
2. **Perimetre affiche** : huit indices mondiaux aujourd'hui
   (`profiles.RISK_PERIMETER`). Comparer les 161 titres ferait tomber
   l'intersection des calendriers, et une grille 161x161 n'est pas un ecran.
3. **Fenetre et date de base** de la page Graphiques, non installee.

### Non verifie

- `calendar/global` et `option_chain/*` n'ont aucun instantane publie : leurs
  relais n'ont JAMAIS ete exerces sur donnees reelles.
- `ai_explain._INTRA_WORD_SEPARATOR` normalise `- . _ * + ~ / \ | : ; '` mais
  ni `$` ni `@` : `a$c$h$e$t$e$z` echappe a `detect_forbidden_language`.
  Defaut reel, anterieur, a ouvrir separement.


---

## SESSION 2026-09-01 (suite) — phase « affichage d'abord »

### Ce qui a ete decide avec l'utilisateur

Quatre planches canoniques fixent DOUZE pages. Consigne explicite : livrer la
COMPOSITION d'abord, les branchements ensuite, avec une capture a chaque lot.

Cet ordre n'est legitime qu'a une condition, et c'est ce que LOT-A0 installe :
un module non branche montre sa GEOMETRIE reelle et NOMME son absence ; il
n'affiche jamais un chiffre de maquette, jamais un rectangle gris muet.
Article 17 de la Constitution.

### LOT-A0 — le socle (commit `812320d`)

- `apps/web/src/components/AbsentModule.tsx` : vocabulaire FERME de quatre
  motifs (`AUCUNE SOURCE`, `ABONNEMENT REQUIS`, `CONTRAT SERVEUR ABSENT`,
  `DECISION EN ATTENTE`). Le corps du module ne porte AUCUN chiffre, et un
  test le refuse.
- `apps/web/src/design/no-fabricated-values.test.ts` : balayage AST de
  `src/pages/**` refusant tout litteral en forme de valeur financiere.
  Quatre exemptions NOMMEES une par une, motif ecrit.

### LOT-A1 — points 4 et 5 de l'anatomie du shell

Les planches posent nature, fraicheur et heure UTC a l'extremite DROITE de la
bande de ticker. Livre :

- `servedClockOf()` : l'heure affichee est l'`as_of` SERVI, jamais
  `Date.now()`. Une horloge murale qui avance a cote d'un instantane fige
  fabrique une impression de courant. Sans `as_of`, AUCUNE heure n'est rendue.
- Le deplacement a droite est VISUEL, par placement de grille CSS. L'ordre du
  DOM reste l'ordre de lecture, et il place la DEGRADATION (`PERIME`,
  `COUVERTURE PARTIELLE`) AVANT les cours qu'elle qualifie.

**Defaut trouve par la campagne, pas par la revue.** La premiere version
laissait le bloc de droite imposer sa largeur maximale au shell : le plancher
desktop declare a 1024 px passait a 1088 px, et **51 tests sur 450** l'ont dit.
La campagne d'accessibilite epingle ce plancher AU PIXEL exactement pour cela.
Corrige par un retour a la ligne du bloc (`flex-wrap`) : a 1024 px la bande
fait deux lignes — une degradation VISIBLE, jamais une donnee escamotee.

**Piege de lecture, deuxieme occurrence.** Le premier lancement a ete rapporte
« exit 0 » par l'outillage alors que Playwright sortait en **1** : le 0 etait
celui du `tail` final de la commande composee. Le code reel se lit dans la
sortie (`CODE REEL : 1`), le total se confronte a `--list` (450) et a
`.last-run.json` (`status: failed`, 51 identifiants). Regle deja consignee a
`DEBT.md`, re-verifiee ici.

### Ce qui reste

Phase 1 : LOT-A2 (creation de `Graphiques`, 12e destination), puis A3 a A8
(composition page par page), puis A9 (refonte Titanium Ledger).
Phase 2 : branchements, dans l'ordre de valeur.

**Correction d'une affirmation fausse de cette session.** J'ai ecrit que les
fondamentaux exigeaient un abonnement IBKR payant. C'est FAUX : la PR #12
livre des adaptateurs SEC EDGAR / FRED / OpenFIGI / BCE / BNS, et la PR #13 la
normalisation point-in-time de SEC Company Facts. Les fondamentaux passent de
« abonnement requis » a « contrat de calcul manquant ». FRED debloque aussi le
taux sans risque de la chaine d'options ; dividende, `style` et `settlement`
restent a trancher.

---

## SESSION 2026-09-02 — refonte visuelle Titanium Ledger (V2 → V6)

Consigne utilisateur : refonte visuelle uniquement. Aucune API, aucun contrat
Python, aucune integration IBKR/TradingView, aucune fusion dans `main`.

Six lots pousses sur `claude/snapshots-confirmation-20260901`. Le plan complet
et l'avancement mesure vivent dans
`docs/05-design/REFONTE_TITANIUM_LEDGER.md`.

Ce qu'il faut retenir pour la session suivante :

1. **Le theme n'etait pas un systeme.** 443 classes `.vx-*` declarees,
   89 atteintes par la couche thematique, via 15 listes de selecteurs
   enumerees a la main. Un module ajoute n'heritait de RIEN. La primitive
   `Card` et deux portes remplacent la discipline par une garantie.
2. **Une valeur redeclaree trois fois** (largeur du rail) est le symptome a
   chercher en premier quand un changement de CSS « ne fait rien ».
3. **Regarder la capture** : deux defauts reels — treemap rogne, poids a
   28 decimales — n'ont ete vus par AUCUN des 486 tests unitaires ni des
   459 tests e2e. L'image, oui.
4. **Attendre un temoin de CONTENU dans une sonde**, jamais `main` visible :
   sinon on mesure le squelette de chargement et on conclut faux. Erreur
   commise et corrigee dans cette session.

Reste : Portefeuille a 4971 px porte douze modules pour « trois a cinq » au
contrat — decision d'architecture d'information, pas de style ; V7-V8
(migration JSX des surfaces restantes) ; V9 (retrait des 15 enumerations).
