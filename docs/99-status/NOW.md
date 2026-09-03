# État courant

```yaml
phase: post_merge_requalification_r2
lot: VERTEX-RATTRAPAGE R2 (R1 actualisé)
branch: lot/r2-requalification-20260902
status: r2_matrice_documentee_trois_pr_brouillon_attente_revue_codex_aucune_fusion
last_known_good_commit: "a5b7d205388e58f4e2716deeba5ecbea0ca9af21 (= état avant fusion #14, CI 7/7 verte)"
main_head_observed: "ecc50c1027314dd3ed594410430d41a3b1189ebf (= squash #20 après #17 c3f2400, base R2, observé le 2026-09-02 ; inchangé pendant tout R2)"
security_state:
  - "ruleset main-required 22076309 actif ; main protégée ; squash seul ; sept checks et branche à jour obligatoires"
  - "dépôt maintenu public par décision humaine ; risque historique résiduel accepté, sans autorisation de réécriture"
  - "PR #14 fusionnée après le gel R0 : 44 commits source, 123 fichiers, squash 505d4654 ; aucun rollback destructif"
  - "HEAD fusionné de PR #14 ef47b11a : CI #159 verte ; conformité architecturale encore à requalifier"
  - "PR #18 fusionnée pendant la validation R0 : 2 fichiers, HEAD b8a0d4d6, CI #165 verte, squash beb24988 ; ajoutée au même audit"
  - "les 23 commits classés et les 13 commits post-gel deviennent une matrice d'audit du code déjà présent dans main"
r2_state:
  - "matrice de requalification : docs/99-status/R2_REQUALIFICATION.md — 8 vagues instruites, 5 contre-vérifiées (A, B, C, F, J) ; D, E, G KEEP sur rapport unique"
  - "R2-A ADAPT (A1 performance marks, A2 conclusion Marchés, A3 export CSV) ; R2-B ADAPT (B2 porte de l'indice, B1 force relative) ; R2-C ADAPT (C1 collecte de presse inopérante sur main) ; R2-F ADAPT (F1, F2, F3) ; R2-J scindée (CSS KEEP, passation → R2-I)"
  - "R2-D, R2-E, R2-G KEEP ; R2-H HOLD maintenu ; R2-I REWRITE/DROP maintenu"
  - "PR 23 brouillon : lot/r2c-presse-hachage-20260902 @ b27d277 — C1 corrigé depuis main, reproducteur rouge sur ecc50c1 puis vert ; C2 retiré"
  - "PR #21 brouillon : lot/r2-pr19-demarrage-20260902 @ 6d05603 — reprise bornée de #19, NOW.md écarté, CI 7/7 verte"
  - "aucune fusion automatique ; aucune modification du chantier graphique (J3, F6 transmis au propriétaire de global.css) ; IBKR information-only"
ci_state_r1:
  - "ci run 33601777661 sur main@beb24988 : succès, sept checks requis inclus"
  - "ci sur PR #17 @ 5f25dab : succès"
nightly_state_r1:
  - "nightly run 33605890223 sur main@beb24988 : ÉCHEC — 753 réussis, 2 échoués, 2 ignorés, projet firefox-1440x900 seul"
  - "options.spec.ts:187 et today.spec.ts:94 : même assertion expect(sorti).toBe(true) — le Tab ne sort pas de l'inspecteur sous Firefox"
  - "la nightly n'est pas un check requis du ruleset : dette qualité, pas blocage de fusion ; hors périmètre R1 (code applicatif)"
pr_19_r2: "reprise EXÉCUTÉE en PR #21 (brouillon) depuis ecc50c1 : 4 fichiers, hunk NOW.md écarté, 12 tests, six portes documentaires, CI 7/7 ; #19 à fermer après fusion humaine de #21"
commits_claude_post_pr18_r1:
  - "732f7e5 PRESSE time_unzoned : ADAPT EXÉCUTÉ — PR 23, cherry-pick -x depuis main + test_news_hashing_chain.py (rouge sur ecc50c1 : CanonicalizationError) ; le test collecte → base (C3) reste à écrire"
  - "f9af140 PASSATION locale : DROP confirmé — ses quatre faits utiles sont réécrits dans R2_REQUALIFICATION.md §5, sans chemin ni secret"
  - "HEAD Claude relevé f9af140, 50 commits en avance ; jamais absorbé en bloc"
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
                /calendar, /markets, /charts, /portfolio, /risks, /catalysts,
                /sources-reports, plus /auth hors rail]
pages_non_implementees: []
destinations_cibles_manquantes: []
# GRAPHIQUES A ÉTÉ INSTALLÉE le 2026-09-02 (LOT-A2, `TL / 08`), SANS nouveau
# contrat et sans façade : la planche §8 est rendue en entier, sa dominante lit
# le contrat Analyse (même DTO, même client, même composant que /analysis), et
# chaque module sans source est DÉCLARÉ absent avec un motif du vocabulaire
# fermé d'AbsentModule. La comparaison base 100 reste `CONTRAT SERVEUR ABSENT` :
# `market.rebased_series` est approuvé et implémenté, mais relayé par aucune
# route ni snapshot — la brancher est un lot SERVEUR. Voir PAGE_ARBITRATION.md.
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
ancienne_prochaine_commande_lot_14: "PR #11 (brouillon) porte LOT-07 a LOT-13b et attend une
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
ancienne_prochaine_commande_lot_26: "VALIDE PR #13 — relire humainement LOT-26 puis décider de sa
   fusion. Après validation seulement, ouvrir LOT-27 pour FRED/ALFRED PIT. Les
   clés, identifiants et droits fournisseurs restent exclusivement locaux."
ancienne_prochaine_commande_r0: "AUDITE MAIN POST-FUSION #14 ET #18 — requalifier beb24988
   contre a5b7d205 et le plan R0, sans rollback ni réécriture destructive."
prochaine_commande: "ATTENDRE LA REVUE CODEX DE R1 (PR #17). Aucune fusion, aucun
   démarrage de R2. Après validation humaine de #17 seulement : PR #19 reprise
   par nouvelle PR bornée, puis R2 selon la matrice de récupération."
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

### Reste casse — REQUALIFIE le 2026-09-02 sur main@ecc50c1

La table des « huit etiquettes qui mentent » (mesuree sur la branche Claude,
entree dans main par le squash #14) est REQUALIFIEE par
`docs/99-status/R2_REQUALIFICATION.md` (vague R2-A, contre-verifiee) :

| Emplacement | Verdict R2 sur `main` |
|---|---|
| `MarketsPage.tsx` (cinq libelles « synthetiques ») | CORRIGE — libelles par recensement de nature (`censusOfNature`/`provenanceSentence`) |
| `portfolio.py` `MARK_POPULATION_SYNTHETIC` inconditionnel | CORRIGE — `MarksView.population` suit la source (`portfolio.py:293-307`) |
| `markets.py:362` « Sur N instruments synthetiques attendus » | RESTE FAUX — ecart A2, persiste dans le contenu publie ; PR bornee a ouvrir |
| `performance.py:136` et `:811` `marks = "SYNTHETIC"` | RESTE FAUX — ecart A1, persiste ; exige d'abord une decision de contrat (`POPULATION_LABELS`) |

Nouveau, hors table d'origine : `MarketsTable.tsx:125` nomme l'export
« marches-synthetiques.csv » quelle que soit la population (ecart A3).

**`data_state='partial'` sur Marches** : CORRIGE dans main (`markets.py:595-598`,
intention presente et testee — R2-A).

**« 500 latent sur Risques »** : PERIME. A `ecc50c1`, `"value"` est sous
`_SIGNED_DECIMAL_KEYS` (`snapshot_views.py:977`) ; `risk.py` passe par
`checked_risk_content`. Aucune correction de code a faire (ecart F5, clos).

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

---

## SESSION 2026-09-02 — LOT-A2 : Graphiques, la douzième destination (`TL / 08`)

Consigne utilisateur : après fusion de #21 et #22 (déléguées, squash, CI 7/7
chacune), « démarrer le nouveau visuel selon les exigences » du skill
`vertex-titanium-ledger`. L'inventaire du skill ne signalait qu'un écart cible :
`charts`. Base : `main@6e416d8` (squash #22). Branche `lot/a2-graphiques-20260902`.

Ce qui existe désormais :

- `apps/web/src/pages/charts/` — `ChartsPage.tsx` (dominante = espace
  graphique servi par `GET /api/v1/analysis/{instrument}` ; `CandleChart`,
  `OhlcvTable` et `IndicatorsPanel` réutilisés, les deux derniers désormais
  exportés d'`AnalysisPage.tsx`), `chartsView.ts` (catalogue des douze modules
  de la planche : trois servis, neuf déclarés absents avec motif et note).
- `AbsentModule` a son premier consommateur réel ; sa tête passe en
  `flex-wrap` (défaut vu SUR CAPTURE à 1280 px : badges tronqués en colonne
  étroite — aucun test ne le voyait).
- Rail : groupe Observer = Calendrier, Marchés, Graphiques. `LEDGER_CODE_BY_PAGE`
  et `--vx-page-ledger` portent `08` ; les tests épinglent les douze codes.
- Inspecteur : définition de la série (devise, base, qualité, fraîcheur,
  référence, snapshot/moteur, exclusions) ; une absence est dite « non
  publié », jamais un tiret.

Mesuré sur cette machine, codes de sortie relus :

- `audit_titanium_ledger.py` : `status: PASS`, `target_gaps: []`, `errors: []`
  (avant le lot : `TARGET_GAPS`, « destinations cibles sans équivalent
  détecté: charts »).
- `tsc --noEmit` 0 ; `biome check` 0 sur 12 fichiers.
- `vitest run` : 40 fichiers, 535 tests, 0 échec (521 sur `main` + 14).
- Playwright Chromium, tous viewports : `charts + shell-canonical +
  accessibility` = 231 passés / 231 déclarés / `.last-run.json` passed ;
  `charts.spec` rejoué après le correctif CSS = 15 / 15.
- Captures `charts-desktop-{1280x800,1440x900,1600x1000}.png`, relues.
- `tools/run_checks.sh` sur l'arbre définitif : **onze portes vertes**
  (rôle, blueprint, frontière, registre, secrets, policy, traçabilité,
  notices, verrou, compilation, Cloudflare, Biome, budgets, ruff, mypy), puis
  **UN échec** en suite Python :
  `apps/edge-ibkr/tests/test_denylist.py::test_adapter_satisfies_the_port_protocol`.
  Reproduit **à l'identique sur `main@6e416d8` intact**, avec le python
  système ET le venv verrouillé — tous deux en **3.11.15**. Le même fichier
  passe **6/6** sur un venv verrouillé **Python 3.13** (la cible de la CI,
  `uv sync … --python ${PYTHON_VERSION}`), et la CI est verte sur ce même
  arbre (run `33655158621`). Divergence 3.11/3.13 de `isinstance` sur un
  `Protocol` `runtime_checkable` (`port.py:496`), dernier commit sur
  l'adaptateur : `ecc50c1` (#20). **Aucun fichier Python n'est touché par ce
  lot** ; le test n'est ni modifié ni sauté. Suite Python complète rejouée sur
  3.13 : voir la PR. Conséquence pour le poste : un venv 3.11 ne reproduit
  pas la CI — `uv sync --locked --all-extras --python 3.13`, comme
  `start_local.sh` le demande déjà.

Transmis, non corrigé ici (hors des fichiers du lot) :

- `IndicatorsPanel` affiche l'ATR avec seize décimales (`4.413571428571428`) :
  c'est la chaîne publiée par le serveur, relayée telle quelle, identique sur
  `/analysis`. La précision est à déclarer côté contrat, pas à arrondir en TS.
- `ChartsPage` importe `AnalysisPage.tsx` pour deux composants : à extraire
  dans un module partagé (lot de suivi).
- Brancher la comparaison base 100 = producteur + relais de
  `market.rebased_series` (lot serveur).

Prochaine commande recommandée : revue humaine de la PR LOT-A2, puis
`EXÉCUTE J3` (régression `aria-pressed` de V12, reproducteur Playwright déjà
cadré) — ou le lot serveur `market.rebased_series` si la comparaison prime.


## SESSION 2026-09-02 — LOT-A3 : Aujourd'hui et Marchés composées sur leurs planches (§1, §2)

Consigne utilisateur : « fait ça le plus beau possible et le mieux possible,
que tous les graphiques s'affichent correctement, utilise des données
fictives pour montrer le résultat final ». Données fictives = population
`SYNTHETIC` du pipeline e2e, étiquetée à l'écran ; jamais présentée comme
réelle.

Branche `lot/a3-aujourdhui-marches-20260902` depuis `main@6e416d8`, PR
brouillon, aucune fusion.

### Ce qui est livré

- **Aujourd'hui** : la planche §1 en entier — onze modules. Huit SERVIS par
  des contrats existants, chacun lu par le hook de sa page propriétaire (file
  d'attention en dominante ; marché global et carte sectorielle depuis
  `markets_overview` ; catalyseur suivant et calendrier depuis `calendar` ;
  santé des sources ; opportunités ; portefeuille manuel). Trois ABSENTS avec
  motif mesuré (`AbsentModule`) : régime (le moteur publie lui-même « no
  regime assessment exists for this population »), volatilité, risques
  actifs. L'inspecteur est TOUJOURS occupé : l'item ouvert, sinon la vérité du
  snapshot (l'ancien rail). La file est bornée (région défilante, `tabIndex`).
- **Marchés** : la planche §2 en entier — douze modules. Cinq SERVIS par
  `markets_overview` (carte en dominante, largeur de marché, santé de la
  couverture, carte sectorielle, écartés et rejets), sept ABSENTS (sessions,
  indices, volatilité, taux — `CONTRAT SERVEUR ABSENT` : l'adaptateur FRED
  vit dans `apps/edge-official`, aucune route ni snapshot ne relaie une
  courbe —, devises, corrélation, structure de volatilité). Sélection d'un
  instrument depuis une tuile, une puce sectorielle ou une ligne de table →
  inspecteur avec les chaînes publiées et la LIGNÉE du calcul.
- Primitives réutilisables : `moduleStateOf()` (état d'un module depuis SON
  snapshot), `Metric` (bloc de mesure), `SectorGrid` (partagée).

### Ce qui a été vu SUR CAPTURE, pas par un test

1. Cinq colonnes à 1440 donnaient des cellules de **135 px** : l'inspecteur
   est monté en permanence sur ces pages, la zone de travail fait ~730 px.
   Quatre colonnes ; cinq seulement à 1600.
2. Badges d'absence tronqués (« AUCUNE SOURC ») dans une colonne étroite ;
   bandeau santé et barres de breadth coupés ; horodatage en corps
   d'affichage cassé caractère par caractère. Tous corrigés, captures
   régénérées.
3. Le module « Indices » manquait au DOM : le test de composition (douze
   témoins `data-module`) l'a dit avant la capture — c'est le test qui a
   rattrapé celui-là.
4. CI rouge à la première tête (`7fc6289`, e2e 1440 seul) : le test du shell
   « point 6 » visitait `/today` en supposant l'inspecteur masqué — vrai avant
   ce lot, faux par conception depuis (la vérité du snapshot y est montée).
   L'assertion ne tenait plus que par une course avec le chargement : verte
   quand elle précédait les données, rouge quand elles arrivaient d'abord.
   Témoin déplacé sur Sources & Rapports, qui ne monte aucun panneau ; la
   propriété testée est la même, sans course. 6/6 aux trois viewports.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check` : 0 violation.
- `vitest run` : **42 fichiers, 551 tests, 0 échec** (521 sur `main` + 30).
- `audit_titanium_ledger.py` : `TARGET_GAPS` avec le seul écart `charts` —
  attendu sur cette branche, issue de `main` où Graphiques n'est pas encore
  fusionnée (PR #25) ; ce lot n'ajoute ni ne retire aucun écart.
- Playwright (today, markets, shell-canonical, accessibility, 1280/1440/1600) :
  **228 passés / 228 déclarés**, `.last-run.json` passed, code 0 ; passe finale
  today + markets après les derniers correctifs : **36 / 36**, code 0.
- `tools/run_checks.sh` (racine, seul) : toutes les portes vertes dont la
  performance (après correction d'un `INEFFECTIVE_DYNAMIC_IMPORT` : la
  fonction d'état d'Opportunités vit désormais dans sa vue pure), ruff et
  mypy ; puis le seul rouge déjà connu, `test_denylist.py::
  test_adapter_satisfies_the_port_protocol` sur Python 3.11 — pas ce lot,
  aucun fichier Python touché, établi dans la PR #25.
- Deux passes lancées EN PARALLÈLE (e2e et porte performance) ont reconstruit
  `dist/` en même temps : un test e2e a échoué une fois pour cette seule
  raison. Rejouées seules, les deux sont vertes. Règle consignée : jamais deux
  builds web concurrents dans le même worktree.

### Deuxième passe, sur demande : « plus aéré, mieux espacé, mieux cadré »

Appliqué le haut de chaque bande canonique : 16 px entre modules, 20 px entre
rangées, 20 px d'espace interne, arête haute plus claire sur chaque panneau
(« titane froid, plus clair au bord supérieur »), têtes et pieds filetés,
mesures empilées séparées d'un filet (de front quand la carte est large),
inspecteur à faits filetés, dominante de Marchés recadrée. Rangées
rééquilibrées d'après les captures : régime et risques empilés à gauche de la
file (même hauteur), opportunités et portefeuille empilés à côté de la carte
sectorielle, courbe des taux/corrélation et devises/structure empilées à côté
de la carte sectorielle de Marchés, santé et refus de front. Trois passes de
capture ; 36/36 à chaque fois. Reste : à 1280, les puces sectorielles
n'entrent qu'une par ligne dans une tuile de 340 px — lisible, pas élégant.

### Troisième passe, sur demande : des widgets « instrument » (références de widgets financiers)

Une rangée « Instruments suivis » sur Aujourd'hui et Marchés — prix en grand,
variation 1 j en pastille signée, mini-courbe des clôtures et barres de
volume, fraîcheur en haut à droite. TOUT est servi : clôture, devise et
rendement du snapshot Marchés (chaînes verbatim) ; série et fraîcheur du
dossier d'analyse (`GET /api/v1/analysis/{instrument}`). La liste vient des
candidats du snapshot Opportunités dont `bars_status` est `OK` — un dossier
existe pour eux — dans l'ordre publié, bornée à quatre ; sans dossier, la
rangée le dit. Aucun calcul (géométrie des clôtures publiées, comme la
treemap ; base pointillée = première clôture de la fenêtre, un repère ; sens
= signe publié, jamais la pente). Ce que les références montrent et que
Vertex ne fera pas : boutons d'achat, jauges circulaires, valeurs de
maquette. Mesuré : `tsc` 0, Biome 0, vitest 44 fichiers / 560 tests / 0
échec, e2e today + markets 36/36 (deux passes), captures relues aux trois
viewports.

### Transmis, non corrigé ici

- `NOW.md` et `docs/05-design/REFONTE_TITANIUM_LEDGER.md` sont modifiés en
  fin de fichier par la PR #25 ET par ce lot : la seconde fusion demandera
  une résolution triviale (garder les deux sections).
- Le régime, la volatilité et les risques actifs n'auront une source que par
  un lot SERVEUR (calcul au registre + snapshot) ; rien à faire côté interface.

Prochaine commande recommandée : revue humaine de la PR LOT-A3, puis
`EXÉCUTE A4` (Opportunités, Analyse — planches §3, §4).

## SESSION 2026-09-03 — LOT-A4 : Opportunités et Analyse composées sur leurs planches (§3, §4)

Consigne utilisateur : « continue toutes les autres pages » — même motif que
LOT-A3, page par page. Branche `lot/a4-opportunites-analyse-20260903`
EMPILÉE sur `lot/a3-aujourdhui-marches-20260902` (`c56d59a`) : `main` n'a
pas encore `Metric`, `moduleState`, `Sparkline` ni les grilles ; la PR a pour
base la branche A3 et sera reciblée sur `main` après la fusion humaine de
#26 (merge de `main` dans la branche, jamais de rebase). Aucune fusion par
Claude.

### Ce qui est livré

- **Opportunités** : la planche §3 en entier — quatorze modules. Huit SERVIS
  par le seul snapshot `opportunities/global` : le classement en dominante
  (les deux groupes, jamais mélangés, filtre LOCAL par statut publié,
  bouton « Inspecter » par ligne), candidats évalués, répartition des
  directions et statuts sur l'univers (barres de dénombrement), profil,
  raisons d'exclusion, provenance des catalyseurs, limites. Six ABSENTS avec
  motif mesuré : score moyen, biais global, rendement attendu, nuage
  score/rendement, contribution des facteurs (le moteur ne publie AUCUN
  score — son ordre est lexicographique et le dit : « aucun score opaque »),
  activité récente (`CONTRAT SERVEUR ABSENT` : un seul snapshot relayé).
  Inspecteur : le candidat ouvert (admission, exclusion publiée, gates,
  preuves requises présentes/absentes, lien vers le dossier), sinon la
  vérité du snapshot.
- **Analyse** : la planche §4 en entier — dix-neuf modules. Onze SERVIS :
  en-tête instrument (clôture publiée du dossier, variation 1 j du snapshot
  Marchés, mini-série des clôtures et volumes), identité (secteur, devise,
  population ; industrie, capitalisation, bêta DITS « non publié »),
  chandeliers en dominante (cadre allégé : verdict, evidence et scénarios
  en sortent pour leurs propres cartes), indicateurs (+ force relative
  publiée par `market.relative_strength`), **faits officiels SEC** — premier
  relais client de la route déjà typée `GET
  /api/v1/sources/sec/{instrument}/fundamentals`, verbatim, seul le domaine
  officiel devient un lien, aucun ratio —, verdict, scénarios, catalyseurs de
  l'instrument (agenda publié filtré par ticker), risques déclarés, pairs du
  secteur, evidence. Huit ABSENTS : oscillateurs, régime, qualité
  fondamentale, valorisation, confiance du modèle, révisions d'analystes
  (`AUCUNE SOURCE`), niveaux, contradictions (`CONTRAT SERVEUR ABSENT`).
  Inspecteur : le dossier ouvert (version, instant, âge, population,
  référence, couverture, fraîcheur, thèse et invalidation « non publiées »,
  limites) ; l'explication IA reste le second panneau.
- **Primitives partagées** extraites pour les lots suivants : `ModuleStatus`,
  `AgendaLine` (+ `readableEventTime`), `CensusBars` (barres horizontales de
  COMPTES entiers — le remplacement de tous les donuts des planches ; aucun
  pourcentage écrit, il n'est pas publié), `SnapshotFacts`, et la classe de
  composition `.vx-board` (grille par zones, panneaux du même matériau).
- `OhlcvTable` et `IndicatorsPanel` vivent dans leurs fichiers et restent
  ré-exportés depuis `AnalysisPage.tsx` : la page Graphiques (PR #25) les
  importe d'ici.
- Relais SEC : `getSecFundamentals` (client), `useSecFundamentals` (hook,
  clé `sec_fundamentals/<instrument>` ajoutée aux préfixes SSE, comme le
  serveur le signale), `secView.ts` (lecture défensive).

### Tests adaptés, jamais affaiblis

- `AnalysisPage.test.tsx` : le cadre porte la référence d'observation —
  assertion portée au cadre (l'inspecteur la relaie aussi) ; routes
  `/calendar` et `/sources/sec` servies explicitement dans le double de
  `fetch` (sinon elles recevaient un corps d'ANALYSE).
- `OpportunitiesPage.test.tsx` et `opportunities.spec.ts` : les statuts sur
  l'univers sont des barres de dénombrement, le compte publié reste vérifié
  tel quel (`.vx-census-count`).
- `AiExplanationPanel.test.tsx` : Analyse monte désormais deux panneaux ;
  le test attend celui de l'EXPLICATION.

### Ce qui a été vu SUR CAPTURE, pas par un test

1. La grille d'Opportunités n'était pas une grille : la classe de composition
   manquait, tout s'empilait sur une colonne. Les tests de composition ne
   voient pas le CSS ; la capture, si. Corrigé, régénérée.
2. Le libellé d'une barre de dénombrement (`INSUFFICIENT_DATA`) et la clé
   d'une raison d'exclusion se coupaient lettre à lettre dans une cellule de
   175 px à 1280 et 1440. Libellé sur sa ligne, barre et compte dessous ;
   raisons d'exclusion sur deux colonnes, table à largeur de contenu qui
   défile dans sa région. Deux passes de capture.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check src e2e` : 0 violation (188 fichiers).
- `vitest run` : **50 fichiers, 598 tests, 0 échec** (551 sur A3 + 47) ;
  portes de design rejouées après la passe CSS : 65 / 65.
- Playwright (opportunities, analysis, shell-canonical, accessibility ;
  1280/1440/1600) : **237 passés / 237 déclarés** (`--list`), `.last-run.json`
  passed, code 0 — passe finale après les correctifs de capture ; passes
  intermédiaires 45 / 45 puis 16 / 16 et 8 / 8 (Opportunités seule).
- `tools/run_checks.sh` (racine, seul, après la fin des e2e) : toutes les
  portes vertes dont la performance, Biome, ruff et mypy ; puis le seul rouge
  déjà connu, `test_denylist.py::test_adapter_satisfies_the_port_protocol`
  sur Python 3.11 — pas ce lot, aucun fichier Python touché, établi dans la
  PR #25.

### Transmis, non corrigé ici

- PR empilée : après la fusion de #26, recibler la PR A4 sur `main` (merge de
  `main` dans la branche). `NOW.md` et `REFONTE_TITANIUM_LEDGER.md` sont
  modifiés en fin de fichier par #25, #26 et ce lot : garder toutes les
  sections.
- Aucun snapshot SEC n'est semé par le pipeline synthétique : le module
  « Faits officiels » y montre son état vide honnête ; le cas servi est
  couvert par les tests unitaires (fixture SYNTHÉTIQUE).
- La table des exclus et la grille de scénarios défilent en largeur dans leur
  cellule : lisible, pas élégant.

Prochaine commande recommandée : revue humaine de la PR LOT-A4, puis
`EXÉCUTE A5` (Options, Simulateur — planches §5, §6).

## SESSION 2026-09-03 — LOT-A5 : Options et Simulateur composés sur leurs planches (§5, §6)

Consigne utilisateur : « Continue » après LOT-A4 — lot suivant du plan
A4→A8 accepté. Branche `lot/a5-options-simulateur-20260903` EMPILÉE sur
`lot/a4-opportunites-analyse-20260903` (`7a03081`) ; base de PR = branche
A4, à recibler après chaque fusion humaine. Aucune fusion par Claude.

### Ce qui est livré

- **Options** : la planche §5 en entier — quinze modules. Neuf SERVIS : le
  sous-jacent (widget de Marchés : clôture, variation 1 j, mini-série), la
  série du dossier d'analyse, le snapshot de chaîne (références, version,
  âge, couverture, budget de lignes, population), le spot observé, le taux
  et le dividende SUPPOSÉS par le calcul d'IV (hypothèses publiées, jamais
  un dividende observé), le **sourire d'IV** du groupe affiché et la
  **structure par échéance** en petits multiples — géométrie des IV
  THÉORIQUES publiées par contrat, calls pleins et puts cerclés, aucun point
  de référence choisi (choisir un strike ATM serait une décision de
  calcul) —, la chaîne en dominante (groupes jamais fusionnés, inchangée).
  Six ABSENTS : mouvement attendu et IV de référence (`CONTRAT SERVEUR
  ABSENT` : dérivables, non publiés), rang d'IV et métriques de stratégie
  (`AUCUNE SOURCE`), composeur et profil de payoff (`DÉCISION EN ATTENTE` :
  ils vivent sur Simulateur, joints par l'unique action de l'inspecteur —
  pas une seconde saisie). Inspecteur par défaut « Chaîne publiée » ; le
  contrat ouvert (LOT-13) le remplace, Échap y revient.
- **Simulateur** : la planche §6 en entier — quatorze modules. Neuf SERVIS :
  structure et hypothèses déclarées (composeur scindé en deux cartes,
  libellés intacts), payoff en dominante APRÈS calcul seulement (à vide,
  aucune dominante : la lumière n'est donnée qu'à un résultat réellement
  calculé), résultats certifiés (gain et perte max sur la grille, breakevens,
  risque défini), **grille de scénarios** rendue (spot × temps, chaînes
  verbatim — publiée par le serveur, jamais montrée jusqu'ici), écho des
  hypothèses, méthode (lignée des calculs, nature, avertissements),
  catalyseurs du sous-jacent transféré (aucune requête sans sous-jacent
  déclaré), sources et provenance. Cinq ABSENTS : Monte-Carlo, probabilité
  de profit, chocs (`AUCUNE SOURCE` : rien de probabiliste n'est publié),
  sensibilités et impact portefeuille (`CONTRAT SERVEUR ABSENT`).
  Inspecteur « Étude » : contrat, bornes, origine, puis nature, risque
  défini, avertissements.
- Primitive : `components/options/IvSmile.tsx` (+ `ivSmileSeriesOf`, testée
  sans DOM).

### Tests adaptés, jamais affaiblis

- `OptionsPage.test.tsx` : routes `/analysis/` et `/calendar` servies dans
  le double de `fetch` (sinon un corps de CHAÎNE arrivait au widget du
  sous-jacent). Ce cas a révélé que `barsViewOf` tombait sur un `bars`
  `undefined` : garde ajoutée, absent = absent.
- `SimulatorPage.test.tsx` et `simulator.spec.ts` : le résultat est réparti
  en modules ; les mêmes chaînes serveur sont assérées à leur nouvelle place
  (`sim-kpi`, `sim-echo`, `sim-method`) ; la dominante garde `sim-result`.
- `no-fabricated-values.test.ts` : le libellé exempté du champ de
  volatilité suit son fichier (`SimComposer.tsx`), même texte, même motif.

### Ce qui a été vu SUR CAPTURE, pas par un test

1. Rien à corriger sur les six captures (Options et Simulateur à 1280, 1440
   et 1600) : les deux grilles sont composées, chaque cellule porte son
   module, la chaîne et la grille de scénarios défilent dans leur cellule,
   le sourire d'IV et les petits multiples se lisent avec leurs bornes en
   texte. Première fois depuis A3 qu'une relecture de capture ne déclenche
   aucune passe CSS.
2. Vu par un test, pas par une capture : le locateur e2e `getByLabel('Sens')`
   trouvait aussi la région « Sensibilités » (module absent, `aria-labelledby`)
   — un nom de module partageait le préfixe d'un libellé de champ. Locateur
   resserré sur le rôle `combobox` au nom exact ; aucun libellé changé.
3. Le worker de la session a redémarré pendant la première passe e2e
   (PostgreSQL à relancer) ; toutes les passes citées ci-dessous ont été
   rejouées entièrement après ce redémarrage.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check src e2e` : 0 violation (202 fichiers).
- `vitest run` : **55 fichiers, 622 tests, 0 échec** (598 sur A4 + 24) ;
  portes de design incluses (`one-dominant-per-page`, `no-fabricated-values`,
  `no-raw-colors`, `no-authoritative-calculation`).
- Playwright (options, simulator, shell-canonical, accessibility ;
  1280/1440/1600) : **231 passés / 231 déclarés** (`--list`), code 0, 2,9 min —
  passe finale ; passes intermédiaires 228 / 231 (les trois rouges = le seul
  locateur du point 2) puis 18 / 18 (Simulateur seul, après correction).
- `tools/run_checks.sh` (racine, seul, après la fin des e2e) : toutes les
  portes vertes — rôle du dépôt, blueprint, frontière financière, registre
  des calculs, secrets, policy, traçabilité (entrée `NOT_YET_PROVEN` connue,
  hors lot), notices, uv.lock, compilation, Worker Cloudflare, Biome,
  performance, ruff et mypy ; puis le seul rouge déjà connu,
  `test_denylist.py::test_adapter_satisfies_the_port_protocol` sur Python
  3.11 — pas ce lot, aucun fichier Python touché, établi dans la PR #25.
  Code de sortie 1 pour cette seule raison.

### Transmis, non corrigé ici

- PR empilée : après la fusion de #27, recibler la PR A5 sur `main` (merge de
  `main` dans la branche, jamais de rebase). `NOW.md` et
  `REFONTE_TITANIUM_LEDGER.md` sont modifiés en fin de fichier par #25, #26,
  #27 et ce lot : garder toutes les sections.
- Mouvement attendu et IV de référence sont dérivables d'une IV ATM et d'une
  maturité : c'est un contrat serveur à écrire dans `vertex_core`, jamais une
  géométrie TypeScript. Tant qu'il n'existe pas, les deux modules restent
  déclarés absents.
- La chaîne d'options et la grille de scénarios défilent en largeur dans leur
  cellule : lisible, pas élégant.

Prochaine commande recommandée : revue humaine de la PR LOT-A5, puis
`EXÉCUTE A6` (Portefeuille, Risques — planches §7, §9).

## SESSION 2026-09-03 — LOT-A6 : Portefeuille et Risques composés sur leurs planches (§7, §9)

Consigne utilisateur : « Continue tout » après LOT-A5 — enchaîner A6, A7
puis A8 sans attendre entre les lots, une PR brouillon par lot, aucune
fusion. Branche `lot/a6-portefeuille-risques-20260903` EMPILÉE sur
`lot/a5-options-simulateur-20260903` (`d56360f`) ; base de PR = branche A5,
à recibler après chaque fusion humaine. Aucune fusion par Claude.

### Ce qui est livré

- **Portefeuille** : la planche §7 en entier — dix-huit modules. Dix SERVIS :
  la valorisation publiée (carte, badge de marques, `as_of`, méthode,
  moteur, espèces dites absentes à leur place), la performance totale (TWR
  et XIRR brut/net du snapshot de performance), le module Performance entier
  (absorbé au LOT-08, corps inchangé, matériau de carte par la grille), la
  **concentration par ticker en DOMINANTE** — elle répond à la question de
  la page (`REFONTE_TITANIUM_LEDGER.md` §4) —, l'exposition par devise
  (valeur totale marquée par devise, verbatim, aucune conversion), les lots
  valorisés et exclus (bouton « Détail » par lot), les **dividendes déclarés
  au journal** (kind `DIVIDEND` : lignes listées, montants verbatim, jamais
  sommés — la planche les mettait en widget ; le journal les publie déjà),
  le journal, la déclaration d'un fait passé et l'import CSV (sections
  conservées telles quelles dans leurs cellules). Huit ABSENTS : performance
  du jour, benchmark, exposition par pays, attribution (`AUCUNE SOURCE`),
  espèces, allocation, exposition par secteur (`CONTRAT SERVEUR ABSENT` —
  le secteur existe par ticker dans Marchés, pas par lot ; sommer des poids
  par secteur ici serait un calcul de concentration hors de son
  propriétaire), alertes de concentration (`DÉCISION EN ATTENTE` : aucun
  seuil déclaré). Inspecteur « Valorisation publiée » par défaut ; le lot
  ouvert le remplace (provenance manuelle, poids publié, faits du journal
  et corrections, catalyseurs publiés du ticker, lien Analyse).
- **Risques** : la planche §9 en entier — dix-neuf modules. Sept SERVIS : la
  matrice de corrélation en DOMINANTE (en-têtes de ligne devenus boutons
  d'inspection, `aria-pressed`), les paires extrêmes et l'avertissement de
  synchronicité, la couverture (périmètre déclaré et retenu, séances,
  fenêtre, seuils, unité, retour en arrière — champs publiés jusqu'ici non
  lus), le coût de l'alignement (séances perdues et séances par instrument),
  les instruments écartés (et enregistrements rejetés), puis la
  **concentration du registre** (poids et Herfindahl de la valorisation,
  barres sans table) et le **drawdown** (snapshot de performance), lus par
  les hooks des pages propriétaires — vues pures importées, jamais les
  pages. Douze ABSENTS : score de risque, VaR, risque relatif, liquidité,
  chocs, facteurs, budget de risque, radar, journal d'alertes (`AUCUNE
  SOURCE`), volatilité, rotation, registre des risques (`CONTRAT SERVEUR
  ABSENT` — `PAGE_ARBITRATION.md` : aucune source ne publie sévérité ni
  horizon par risque). Aucun score global : le contrat l'interdit. En
  `empty`, la planche reste composée et la dominante porte l'aveu.
  Inspecteur « Matrice publiée » par défaut ; l'instrument ouvert le
  remplace (coefficients avec chacun et bande publiée, séances, motif d'écart).
- Primitives : `ConcentrationBars` (corps réutilisable des barres de poids),
  `riskView.ts` étendu au contrat déjà publié (population, état des données,
  moteur, schéma, unité, périmètre, rejetés, séances par instrument,
  observations, retour en arrière).

### Tests adaptés, jamais affaiblis

- `PortfolioPage.test.tsx` : inchangé — tous les `pf-*`, la table des lots,
  la section des exclus, les barres, le journal, les 422/409 verbatim
  passent sur la page recomposée. Le cas « valorisation vide » exigeait une
  seule occurrence de la raison serveur : elle n'est écrite qu'une fois
  (module « Valorisation publiée »), les autres modules renvoient vers elle.
- `RiskPage.test.tsx` : inchangé — ses seize cas exigent notamment
  `queryByRole('table')` nul en refus et hors ligne, une seule `note`, une
  seule occurrence de la conclusion et de « Aucun instantané publié » :
  la concentration du registre est rendue en barres (aucune table sur
  Risques hors la matrice), la conclusion n'est pas répétée dans
  l'inspecteur, les modules non servis disent « Matrice non publiée ».
- `shell-canonical.spec.ts` : témoin de dominante `/portfolio` →
  `.vx-pf-concentration` (le résumé n'est plus la dominante).
- Nouveaux : `portfolioModules.test.ts`, `riskModules.test.ts`,
  `PortfolioComposition.test.tsx`, `RiskComposition.test.tsx`,
  `e2e/risk.spec.ts` (première spec e2e de Risques : composition, matrice
  = API, inspecteur au clavier, axe, capture, hors ligne), test de
  composition dans `e2e/portfolio.spec.ts`.

### Ce qui a été vu SUR CAPTURE, pas par un test

1. Portefeuille à 1280 : le module Performance (courbe, métriques, heatmap,
   points, export, conventions) occupait trois colonnes sur deux rangées ;
   ses voisins « Benchmark » et « Exposition par devise » s'étiraient en
   cartes vides de plusieurs écrans. Performance prend désormais une rangée
   entière ; la valorisation ne s'étire plus sur deux rangées, les absents
   de la première ligne se rangent sur la seconde. Deux passes de capture.
2. Risques à 1280 : la matrice sur deux rangées se vidait sous sa légende.
   Une rangée, les paires extrêmes à sa droite, la couverture (la plus
   haute) sur deux rangées en bas. À 1600, le module des écartés s'étirait
   seul sur deux rangées : le registre des risques prend sa place.
3. Vu par un test, pas par une capture : `AiExplanationPanel.test.tsx`
   attendait « le » titre `Inspecteur…` sur `/portfolio` ; la page en monte
   désormais deux (explication IA, valorisation publiée). Locateur nommé
   exactement (`Inspecteur — explication`), comme déjà fait pour Analyse au
   LOT-A4. Aucune assertion retirée.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check src e2e` : 0 erreur (213 fichiers,
  une information préexistante sur `OptionsModules.tsx`, hors lot).
- `vitest run` : **59 fichiers, 647 tests, 0 échec** (622 sur A5 + 25) ;
  portes de design incluses.
- Playwright (portfolio, portfolio-performance, risk, shell-canonical,
  accessibility ; 1280/1440/1600) : **252 passés / 252 déclarés** (`--list`),
  code 0, 4,0 min — première passe, avant la correction des grilles ; puis
  portfolio + risk rejoués deux fois après chaque passe CSS : 39 / 39 et
  39 / 39, et Risques seul à 1600 après la dernière retouche : 5 / 5.
- `tools/run_checks.sh` (racine, seul, après la fin des e2e) : toutes les
  portes vertes — rôle du dépôt, blueprint, frontière financière, registre
  des calculs, secrets, policy, traçabilité (entrée `NOT_YET_PROVEN` connue,
  hors lot), notices, uv.lock, compilation, Worker Cloudflare, Biome,
  performance, ruff et mypy ; puis le seul rouge déjà connu,
  `test_denylist.py::test_adapter_satisfies_the_port_protocol` sur Python
  3.11 — pas ce lot, aucun fichier Python touché, établi dans la PR #25.
  Code de sortie 1 pour cette seule raison.

### Transmis, non corrigé ici

- Ordre utilisateur reçu en fin de lot : « pousse tout, fusionne tout et
  continue » — la chaîne #25 → #26 → #27 → #28 → A6 est fusionnée en squash
  dans cet ordre, chaque PR empilée reciblée sur `main` avant sa fusion ;
  A7 et A8 partent ensuite de `main`.
- Portefeuille reste la page la plus haute des douze : le module Performance
  garde son corps entier (courbe, métriques, heatmap, points, export,
  conventions) dans une rangée pleine ; le rendre plus compact serait un
  autre lot, pas une composition.
- La valeur exacte de l'indice de Herfindahl (jusqu'à vingt-huit décimales)
  se replie sur deux lignes dans le module Risques : chaîne serveur
  verbatim, jamais arrondie.
- La matrice n'est pas rafraîchie pendant une session e2e
  (`run_worker.py` sans `risk_config`) : `risk.spec.ts` lit la matrice semée.

Prochaine commande recommandée : fusion de la chaîne A2 → A6 (ordre reçu),
puis `EXÉCUTE A7` (Catalyseurs, Calendrier — planches §10, §11) depuis `main`.

## SESSION 2026-09-03 — LOT-A7 : Catalyseurs et Calendrier composés sur leurs planches (§10, §11)

Consigne utilisateur : « pousse tout, fusionne tout et continue » — la
chaîne A2 → A6 est fusionnée en squash pendant ce lot (chaque PR empilée
reciblée sur `main`, CI verte exigée par la protection de branche) ; A7
part de la tête d'A6 et sera réaligné sur `main` (merge, jamais de rebase)
avant sa fusion. Branche `lot/a7-catalyseurs-calendrier-20260903`.

### Ce qui est livré

- **Catalyseurs** : la planche §10 en entier — dix-sept modules. Onze SERVIS :
  les événements reliés (reliés, non reliés, thèses orphelines — comptes du
  croisement publié), les révisions (drapeau et détail, deux champs
  distincts), les **filtres locaux** (catégorie et nature du lien, chips
  `aria-pressed` : un filtre masque, il ne reclasse pas), la **chronologie
  en DOMINANTE** (corps LOT-10 inchangé, `cat-unlinked` et `cat-missing-widget`
  conservés), la répartition par catégorie et les sources/fraîcheur en
  barres de dénombrement, l'exposition du registre aux événements (positions
  déclarées nommées par le contexte croisé), la fenêtre et les deux
  snapshots (`cat-populations` y vit désormais), les conflits de version, les
  thèses sans catalyseur servi (section LOT-10 devenue module), la revue des
  thèses (module LOT-10 entier, inchangé, matériau de carte par la grille).
  Six ABSENTS : impact moyen, confiance, surprises, historique des surprises,
  consensus (`AUCUNE SOURCE` — l'importance servie est un rang et un code
  de règle, jamais une mesure pondérable), alertes d'événement (`CONTRAT
  SERVEUR ABSENT`). Aucun inspecteur par défaut : le témoin « aucune colonne
  morte » du shell (`shell-canonical.spec.ts:544`) l'exige, et l'inspecteur
  LOT-10 s'ouvre depuis la chronologie.
- **Calendrier** : la planche §11 en entier — treize modules. Onze SERVIS :
  la fenêtre et les filtres (libellés intacts, URL inchangée), le **fuseau
  d'affichage** (param `tz` : UTC, fuseau du navigateur s'il est résolu,
  fuseaux de place publiés par les événements servis — conversion IANA
  explicite, jamais devinée ; la troisième lecture du temps de chaque
  événement le suit), l'**agenda en DOMINANTE** (région bornée LOT-V3
  conservée, bouton « Inspecter » par événement), l'exposition du registre
  par jour et la densité (dénombrements par journée UTC), le prochain
  événement (premier de l'ordre publié, SANS compte à rebours), les
  compteurs, la règle d'importance, la provenance, les révisions et les
  conflits. Deux ABSENTS : rappels, changements depuis la dernière visite
  (`CONTRAT SERVEUR ABSENT`). `BlockedAgenda` (droit manquant, refus)
  reste l'état de la dominante ; les autres modules disent l'absence.
  Inspecteur « Snapshot publié » par défaut ; l'événement ouvert le
  remplace (statut, importance, trois lectures du temps, fraîcheur, source
  et droits, instruments, positions déclarées, thèses, versions et
  révisions ; les « chiffres » de la planche — actuel, consensus, précédent,
  surprise — sont dits non publiés).
- Extraction : `CalendarModules.tsx` (`BlockedAgenda`, `ImportanceRuleModule`,
  `CountersModule`, `ProvenanceModule`, `applyFilters` sortis de la page, +
  fuseau, densité, exposition, prochain événement, révisions, conflits),
  `EventInspector.tsx`, `CatalystsModules.tsx`, catalogues et tests.

### Tests adaptés, jamais affaiblis

- `CatalystsPage.test.tsx` (20) et `ReviewQueueSection.test.tsx` (14) :
  inchangés. Deux collisions de texte réglées côté page : la raison serveur
  n'est écrite qu'une fois (dans la dominante) ; le libellé de métrique
  « Révisions refusées » devenait une fausse alerte pour
  `queryByText(/refusée/)` — renommé « Révisions rejetées ».
- `CalendarPage.test.tsx` (23) : inchangé — tous les `cal-*`, les deux
  libellés de statut strictement distincts, les compteurs liste/snapshot,
  la fenêtre refusée, l'agenda bloqué passent sur la page recomposée.
- `shell-canonical.spec.ts` : témoins `/catalysts` (`.vx-fu-queue`,
  `cat-unlinked`, inspecteur masqué) et `/calendar` (`.vx-cal-agenda`)
  inchangés.
- Nouveaux : `catalystsModules.test.ts`, `calendarModules.test.ts`,
  `CatalystsComposition.test.tsx`, `CalendarComposition.test.tsx`, tests de
  composition dans `e2e/catalysts.spec.ts` et `e2e/calendar.spec.ts`.

### Ce qui a été vu SUR CAPTURE, pas par un test

1. Calendrier à 1280 et 1440 : les compteurs (deux colonnes) s'étiraient
   sur la hauteur de l'agenda ; la densité et l'exposition par jour, hautes,
   étiraient leurs voisines. Grille rebalancée : conflits à droite de
   l'agenda, exposition · densité · compteurs sur une rangée, révisions ·
   rappels · changements · provenance sur la suivante, la règle d'importance
   sur trois colonnes en bas. Deux passes de capture.
2. Calendrier à 1440 : la table des compteurs et celle de la règle
   d'importance gardaient `min-width: max-content` (héritage de la page
   pleine largeur) : légende coupée en plein mot, troisième colonne cachée
   derrière un défilement horizontal. Dans la planche, les deux tables
   tiennent la largeur de leur carte et replient leurs cellules. Recapture
   relue après correction.
3. Vu par axe, pas par une capture : `AgendaLine` (un `<li>`) rendue dans un
   `<li>` du module « Prochain événement » — violation `listitem`. Corrigé
   par une liste imbriquée.
4. Vu par un test, pas par une capture : les comptages hors ligne de
   `catalysts.spec.ts` et `calendar.spec.ts` lisent `[data-state="offline"]`
   sur la frontière de page ; `ModuleStatus` posait le même attribut sur
   chaque module. Les absences par module sont désormais des phrases
   (`MODULE_STATE_LABELS`), sans attribut concurrent.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check src e2e` : 0 erreur.
- `vitest run` : **63 fichiers, 670 tests, 0 échec** (647 sur A6 + 23) ;
  portes de design incluses.
- Playwright (catalysts, calendar, shell-canonical, accessibility ;
  1280/1440/1600) : première passe **243 passés, 12 échoués sur 255**
  (`listitem`, `data-state` par module, deux textes en double) — tous
  corrigés côté page, aucune assertion retirée ; puis catalysts + calendar
  rejoués après chaque passe : **63 / 63** et **63 / 63**, code 0 ; enfin
  calendar seul après le repli des tables, puis après la levée de la borne
  de hauteur des compteurs : **33 / 33** et **33 / 33**, code 0.
- `tools/run_checks.sh` (racine, seul, après la fin des e2e) : toutes les
  portes vertes (rôle, blueprint, frontière, registre, secrets, policy,
  traçabilité — entrée `NOT_YET_PROVEN` connue, hors lot —, notices,
  uv.lock, compilation, Worker, Biome, performance, ruff, mypy) ;
  seul rouge connu `test_denylist.py::test_adapter_satisfies_the_port_protocol`
  sur Python 3.11, hors lot, aucun fichier Python touché.

### Transmis, non corrigé ici

- La chaîne #25 → #26 → #27 → #28 → #29 est fusionnée en squash pendant ce
  lot ; A7 est réaligné sur `main` par merge avant sa propre fusion.
- `/catalysts` n'a pas d'inspecteur par défaut (témoin du shell) : la vérité
  du snapshot vit dans le module « Fenêtre et snapshots ». Décision
  documentée, pas un oubli.
- Le fuseau du navigateur n'est proposé que s'il est résolu par
  `Intl.DateTimeFormat` ; sous Playwright il l'est (« UTC (navigateur) »).

Prochaine commande recommandée : `EXÉCUTE A8` (Sources & Rapports — planche
§12) depuis la tête d'A7, puis fusion de la chaîne.

## SESSION 2026-09-03 — LOT-A8 : Sources & Rapports composée sur sa planche (§12)

Dernier lot de la vague A (« Continue tout »). Branche
`lot/a8-sources-rapports-20260903`, partie de la tête d'A7 ; réalignée sur
`main` par merge (jamais de rebase) après la fusion de la chaîne.

### Ce qui est livré

- La planche §12 en entier — dix-sept modules. Huit SERVIS : les statuts
  testés (dénombrement par statut sondé, jamais une disponibilité
  supposée), la fraîcheur (âges publiés des snapshots attention et
  capacités, dernier snapshot du worker), la dernière vérification
  (`checked_at`, `as_of`, âge publié), les versions et le flux SSE, le
  **registre des sources en DOMINANTE** — la matrice LOT-01 inchangée (six
  en-têtes, filtres persistés dans l'URL, région défilante focusable) sur
  une rangée entière, un bouton « Détail » par capacité —, les exports
  réellement servis par l'API (journal du registre, points de performance,
  manifeste d'audit — trois routes, aucun rapport généré), la santé des
  composants (section LOT-01 conservée, matériau de carte par la grille),
  les sondes hors manifeste. Neuf ABSENTS : santé globale (`AUCUNE
  SOURCE` — un pourcentage calculé sur des sondes partielles serait un faux
  vert), couverture des champs, taux d'erreur, qualité des champs (`AUCUNE
  SOURCE`), incidents, lignée, journal d'audit, rapports, sauvegardes
  (`CONTRAT SERVEUR ABSENT`). Rien de simulé.
- Inspecteur de capacité sur sélection SEULEMENT (identifiant, famille,
  mode déclaré, description du manifeste — publiée mais jamais affichée
  dans la matrice —, statut, raison, instant de sonde ; champs, licence et
  historique dits non publiés) : le témoin « aucune colonne morte » du
  shell lit `/sources-reports` sans sélection, l'inspecteur y reste masqué.
- Extraction : `pages/sources/{sourcesModules.ts, SourcesModules.tsx,
  CapabilityInspector.tsx}` ; `SourceHealthMatrix.tsx` perd son
  `data-rank` (le seul littéral vit dans la page) et gagne `selected` /
  `onInspect` ; `HealthPanel` sort de la page vers les modules.

### Tests adaptés, jamais affaiblis

- `SourceHealthMatrix.test.tsx` (6) et `SourcesReportsPage.test.tsx` :
  inchangés — rôles, légende, six en-têtes exacts, `AbsentCell role="img"`.
- `shell-canonical.spec.ts` : témoin `/sources-reports` (`.vx-health`
  visible, `#vx-inspector-slot` masqué) inchangé.
- `sources-reports.spec.ts` : capture renommée `sources-reports`
  (héritage `system`), test de composition ajouté ; le libellé de la barre
  de dénombrement (« Capacités par statut testé ») entrait en collision
  avec `getByLabel('Statut testé')` du filtre — renommé « Dénombrement par
  statut sondé » côté page, locateur intact.
- Nouveaux : `sourcesModules.test.ts`, `SourcesComposition.test.tsx`.

### Ce qui a été vu SUR CAPTURE, pas par un test

1. À 1440, le registre sur trois colonnes ne montrait que quatre de ses six
   colonnes (défilement horizontal) ; un premier repli des cellules coupait
   `market_data` et `INFORMATION_ONLY` lettre à lettre. Le registre prend
   une rangée entière ; seule la colonne « Raison » replie (plancher de
   largeur, coupure aux soulignés), l'identifiant, le statut et l'instant
   restent d'un tenant ; marge des cellules resserrée. Quatre passes de
   capture. À 1280, la dernière colonne reste derrière un court défilement
   dans sa région focusable — six colonnes ne tiennent pas en 1 000 px.
2. Les routes d'export replient dans leur carte au lieu de déborder.
3. La santé des composants prend une rangée entière : ses cinq faits sur
   une ligne au lieu d'une grille creuse.

### Mesuré sur cette machine (codes relus)

- `tsc --noEmit` : 0 erreur ; `biome check` (fichiers du lot) : 0 erreur.
- `vitest run` : **65 fichiers, 681 tests, 0 échec** (670 sur A7 + 11) ;
  portes de design incluses.
- Playwright (sources-reports, shell-canonical, accessibility ;
  1280/1440/1600) : première passe **201 passés, 3 échoués sur 204**
  (collision de libellé `Statut testé` entre la barre de dénombrement et le
  filtre — corrigée côté page) ; sources-reports rejoué après chaque passe
  CSS : **12 / 12** cinq fois, code 0.
- `tools/run_checks.sh` (racine, seul, après la fin des e2e) : toutes les
  portes vertes (rôle, blueprint, frontière, registre, secrets, policy,
  traçabilité — entrée `NOT_YET_PROVEN` connue, hors lot —, notices,
  uv.lock, compilation, Worker, Biome, performance, ruff, mypy) ; seul
  rouge connu `test_denylist.py::test_adapter_satisfies_the_port_protocol`
  sur Python 3.11, hors lot, aucun fichier Python touché. Code de sortie 1
  pour cette seule raison.

### Transmis, non corrigé ici

- Ordre utilisateur : la chaîne #28 → #29 → #30 → #31 est fusionnée en
  squash dans cet ordre, chaque PR réalignée sur `main` par merge avant
  sa fusion ; puis #23, #24 et #9 sont évaluées.
- Graphiques (§8) n'est pas recomposée au motif A3 : composée au LOT-A2
  (#25 fusionnée), sa retouche serait un lot à part.
- À 1280, la sixième colonne du registre reste derrière un court
  défilement horizontal dans sa région focusable.

Prochaine commande recommandée : fusion de la chaîne #29 → #30 → #31, puis
`STATUT`.

## LOT C0 — canon Titanium Ledger v2 (2026-09-03)

Branche `lot/w2-c0-canon-v2-20260903`, base `main@4fc901a`, worktree
`/home/elio/vertex-c0`. Décision de l'utilisateur du 2026-09-03 (« pour chaque
widget trouve toujours le meilleur, crée tes propres visuels au max, que ça
affiche au max ») consignée en
`docs/09-adr/017-titanium-ledger-v2-formes-widgets.md`.

### Ce qui change

- ADR-017 : formes admises **uniquement sur des données servies** — anneaux à
  chiffre central, quatuor d'anneaux, jauges en arc graduées (position
  servie), aires à dégradé sous une série, sparklines en aire, rails derrière
  les barres, matrices de bandes, listes groupées par jour, teinte sémantique
  secondaire par page (`macro`, `option`, `warning` ; `positive` retiré après
  la revue adverse, voir « Corrections » ci-dessous). Interdits
  maintenus écrits (halo, noir pur, carte floue, couleur seule, compte à
  rebours ou horloge client, radar sans dimension servie, dégradé de fond
  plein, pulsation, valeur abrégée, toute forme sur une valeur non servie).
  Empreinte de la capture canonique inchangée.
- Documents mis en cohérence, chacun citant ADR-017 : DESIGN_SYSTEM,
  CHART_STANDARD, WIDGET_LIBRARY, TOKENS, TITANIUM_LEDGER_VISUAL_SYSTEM,
  VERTEX_ONE_VISUAL_DIRECTION, DASHBOARD_COMPOSITION,
  MOTION_AND_MICROINTERACTIONS ; références du skill canonical-visual,
  visual-identity, component-system, charts ; `manifests/widget-catalog.yaml`
  (arc gradué admis, `v2_forms`, interdits).
- Tokens (`tokens.ts`, `tokens.css` régénéré) : `motionDuration[600]`, douze
  `<famille>-gradient-start/-end` (fin à alpha 0), `pageAccent` et blocs
  `[data-page-accent]` émis par `generate-css.ts` sans valeur par défaut.
  Script d'audit : tokens de dégradé ajoutés aux tokens requis.
- Tests : `tokens-css.test.ts` étendu (rien retiré), `canon-v2-docs.test.ts`
  nouveau (formulations levées absentes, invariants non levés présents,
  citation d'ADR-017 par chaque document, catalogue cohérent).
- Plan directeur : `docs/05-design/WIDGETS_V2_PLAN.md` (lots, ordre, formes
  par famille de donnée, socle L0, plan des douze pages).

### Mesuré sur cette machine (codes relus)

- `pnpm tokens:css` puis `git diff --exit-code -- src/design/tokens.css`
  après le commit des tokens : aucune dérive.
- `pnpm lint` : 0 erreur (1 info préexistante, `OptionsModules.tsx:204`,
  fragment redondant, hors lot).
- `pnpm typecheck` : 0 erreur.
- `pnpm exec vitest run src/design` : 7 fichiers, 71 tests, 0 échec.
- `pnpm exec vitest run --no-file-parallelism` : **68 fichiers, 705 tests,
  0 échec** (88,6 s). Avec le parallélisme par défaut (28 workers) sur ce
  poste chargé (load average 18,7 ; pile live et autres lots en marche),
  29 puis 49 échecs par dépassement de délai jsdom ; le `main` intact
  (4fc901a) en produit 9 dans les mêmes fichiers → contention
  d'environnement, pas le lot.
- `pnpm exec vite build --manifest` : ✓ built in 550ms, manifeste présent.
- `audit_titanium_ledger.py --strict-target` : `PASS`, 0 erreur, 0 écart,
  empreinte `eb2eb0fc…c7ace`, aucun token requis manquant.
- `tools/verify_blueprint.py` : ok (fences Markdown, YAML, lots).
- `tools/run_checks.sh` (venv du worktree créé par
  `uv sync --locked --all-extras --python 3.13`, sans `env.live`, aucun
  `VERTEX_*` exporté) : toutes les portes vertes (rôle, blueprint, frontière, registre,
  secrets, policy, traçabilité — entrée `NOT_YET_PROVEN` connue, hors lot —,
  notices, uv.lock, compilation, Worker, Biome, performance, ruff, mypy) ;
  pytest : 4075 marqueurs de résultat comptés dans la sortie `-q` (4071 réussis,
  4 ignorés, 0 échec ; la configuration n'imprime pas de résumé chiffré) ;
  « TOUT VERT », code de sortie 0.

### Transmis, non corrigé ici

- `apps/web/src/components/CensusBars.tsx:1-7` : l'en-tête cite encore
  « pas d'anneau » de `charts.md` ; à réécrire au lot L0 avec `RingShares`.
- `apps/web/src/pages/markets/BreadthPanel.tsx:5` (« jamais circulaire ») et
  `apps/web/src/styles/global.css:6935` (« remplacent les donuts ») : même
  catégorie de commentaires périmés, relevés par la revue adverse ; code non
  touché, à réécrire au lot L0.
- `docs/05-design/DASHBOARD_COMPOSITION.md:78` (« gradient argent→violet »),
  kicker 10 px vs plancher 13 px, « 3–5 modules » vs 11–19 composés : tensions
  du canon non tranchées par ADR-017.
- Teintes secondaires proposées par page (`WIDGETS_V2_PLAN.md` §2) : à
  confirmer dans chaque catalogue au lot P.
- Aucune capture d'écran : ce lot ne touche aucun rendu de page (tokens et
  blocs `[data-page-accent]` sans consommateur avant L0).

### Corrections après revue adverse (2026-09-03)

Verdict de la revue : changements requis (deux corrections de texte/tokens),
le reste approuvé. Commits `bce6762`, `9fa1f72`, `b39c98d`, empilés sur
`203462f` (aucun amend, aucun push).

- Requis 1 — `bce6762` : ADR-017 :43 contredisait `DESIGN_SYSTEM.md:73`
  (« gradients : sélection/action principale ») et le shell en vigueur
  (`global.css` : tranche `signal-bright → signal-deep` :4538/:5271, action
  principale `signal-bright → signal` :4772, liseré `signal-bright →
  transparent` :4448). L'ADR nomme désormais trois familles de dégradé
  (matériau ; sélection/action principale et tranche ambre, famille `signal`,
  précédents cités ; aire sous une série servie) ; « jamais entre deux
  teintes » ne porte plus que sur l'aire de série ; « jamais un fond plein de
  carte, jamais décoratif » vaut pour les trois.
- Requis 2 — `9fa1f72` : `positive` retiré de `pageAccent` (`tokens.ts`),
  `tokens.css` régénéré (bloc `[data-page-accent="positive"]` disparu) ;
  `tokens-css.test.ts` resserré à `['macro', 'option', 'warning']` et refuse
  `positive`/`negative` explicitement ; `canon-v2-docs.test.ts` : catalogue à
  trois familles, `excluded` étendu, nouveau test « aucune teinte de page ne
  porte un signe financier » (ADR + documents du canon), deux invariants
  gardés de plus (VERTEX_ONE « exclusivement financiers », plan « Vert/rouge
  … servi »). Textes mis à jour : ADR :38/:42, DESIGN_SYSTEM,
  TITANIUM_LEDGER_VISUAL_SYSTEM, WIDGET_LIBRARY, VERTEX_ONE :23/:92, TOKENS,
  WIDGETS_V2_PLAN, canonical-visual, charts, visual-identity,
  widget-catalog.yaml (`excluded_reason`), commentaire de `tokens.ts`.
- Réserves 3–5 — `b39c98d` : consignées comme contraintes du lot L0 dans
  ADR-017 (Coûts : `warning` #f0c36a ≈ `signal-bright` #f2c76b, ≤ 4/255 par
  canal → distinguabilité mesurée sur capture ou retrait de `warning`, aucune
  page ne le déclare avant ; Preuves : `catalog.test.ts` avant tout
  consommateur — sans déclaration `--vx-page-accent` est invalide et un `fill`
  SVG tombe au noir, sans erreur). `ICON_SYSTEM.md` gagne une ligne citant
  ADR-017 (ses règles régissent les icônes ; la teinte de page colore les
  formes, jamais un statut d'icône) et entre dans `CANON_DOCS` et
  `KEPT_INVARIANTS` ; `TOKENS.md`, plan §2 (les trois propositions `warning`
  suspendues à la réserve) et §3.6. Nouveau test « consigne les réserves de
  la revue C0 comme contraintes du lot L0 ».
- Réserve 6 : commentaires périmés ajoutés à « Transmis » ci-dessus.

Mesuré après les trois commits (codes relus) :

- `pnpm tokens:css` puis `git diff --exit-code -- src/design/tokens.css` :
  aucune dérive, code 0.
- `pnpm lint` : `Checked 237 files in 81ms. No fixes applied. Found 1 info.`,
  code 0 (info préexistante `OptionsModules.tsx:204`).
- `pnpm typecheck` : code 0.
- `pnpm exec vitest run src/design` : 7 fichiers, **73 tests, 0 échec**
  (71 → 73 : deux tests ajoutés).
- `pnpm exec vitest run --no-file-parallelism` : **68 fichiers, 707 tests,
  0 échec**, 78,37 s (load average 0,32 au lancement).
- `pnpm exec vite build --manifest` : ✓ built in 465ms, manifeste 7033 o.
- `audit_titanium_ledger.py --strict-target` : `PASS`, `errors []`,
  `target_gaps []`, `missing_color_tokens []`, empreinte `eb2eb0fc…c7ace`
  inchangée.
- `tools/verify_blueprint.py` : `ok true`, `errors []`.
- `tools/run_checks.sh` (venv `.venv` Python 3.13.15 activé par
  `source .venv/bin/activate`, sans `env.live`, 0 variable `VERTEX_*`) :
  `== TOUT VERT ==`, code 0 en 67 s ; ruff `All checks passed!`, `OK mypy` ;
  pytest `-q` : 4075 marqueurs (4071 réussis, 4 ignorés, 0 échec). Sans le
  venv activé, le script s'arrête sur `/usr/bin/python3: No module named
  pytest` (code 1) : activer le venv avant l'appel.
- Aucune capture : aucun rendu modifié ; e2e non lancés (règle du poste).

Prochaine commande recommandée : relecture des commits de correction
(`bce6762`, `9fa1f72`, `b39c98d` et le commit NOW.md qui suit), puis lot L0
(`lot/w2-l0-socle-20260903`, empilé sur C0).

## SESSION 2026-09-03 — LOT SRV-S0 : la file d'attention affamée par les cotations instantanées

Lot SERVEUR. Branche `lot/srv-s0-attention-fenetre-20260903`, base
`origin/main` = `4fc901a`, worktree `/home/elio/vertex-srv-s0`. Aucun push,
aucune PR par l'implémenteur (l'orchestrateur s'en charge). Cinq commits :
S0-A (reproducteurs, rouge), S0-B (correctif), puis — après la revue
adverse (verdict APPROUVÉ, quatre réserves non bloquantes) — S0-C
(reproducteurs des réserves 3 et 4, rouge), S0-D (correctifs) et S0-E
(cette documentation).

### Ce qui a été mesuré (base de test, jamais `vertex_live`)

- `today/attention` : 20 dépêches `ibkr.news-headline/1` valides sur quatre
  instruments réels, puis 600 cotations instantanées PLUS RÉCENTES
  (`ibkr.quote/1`, `ibkr.daily-quote/1`, sans titre) → **0 item**,
  `content_observations: 0`, `observations_considered: 500`. La fenêtre de
  500 était bornée AVANT le filtre de famille : elle ne contenait plus que
  des instantanées. Même famine pour le contexte d'information de la file
  de revue (même chargeur).
- Opportunités : 3 dépêches de GOOG plus anciennes que 520 dépêches de
  MSFT → la page Analyse (fenêtre cadrée par instrument) voyait 3 grappes,
  la page Opportunités (fenêtre globale) **aucune**.
- Réserve 4 de la revue : `LIKE 'demo_news/%'` sans échappement acceptait
  `demoXnews/1.0` et `demo-news/1.0` (3 lignes chargées sur 1 attendue) ;
  `LIKE 'demo%%'` acceptait tout ce qui commence par `demo`.
- Réserve 3 de la revue : **7 lectures** de `observations` pour un
  `opportunities.refresh` sur six instruments à barres (1 pour les barres
  + 1 PAR instrument), chacune parcourant la plage `as_of` du lookback
  faute d'index sur `instrument_ref`.

### Ce qui est livré

- `CONTENT_SCHEMA_PREFIXES` (`handlers.py`) : les familles de CONTENU
  admises, deny by default — `synthetic-news/`, `ibkr.news-headline/` ;
  `FusionConfig.content_schema_prefixes` (déclaration vide ou mal formée
  refusée) ; `load_recent_observation_records(schema_prefixes=…)`
  obligatoire, appliqué AVANT la borne ; couverture publiée
  (`content_schema_prefixes`) sur la file d'attention et la file de revue.
- Préfixes LITTÉRAUX : `_schema_family_filter` émet
  `LIKE :préfixe || '%' ESCAPE '/'` (`%`, `_` et `/` échappés).
- Opportunités cadrée par instrument comme Analyse, et en UNE lecture pour
  tous les candidats : `load_recent_observation_records_by_instrument`
  (`row_number() OVER (PARTITION BY instrument_ref ORDER BY as_of DESC, id
  DESC)`, borne PAR instrument, même ordre que le chargeur unitaire) ; un
  instrument sans barre garde la fenêtre globale, chargée une fois ;
  `build_opportunities_content` accepte `Mapping[ticker, fenêtre]` — un
  ticker absent n'a aucune preuve, jamais celles d'un autre.
- Contrat écrit : `docs/03-domain/ATTENTION_AND_RELEVANCE_ENGINE.md`,
  section « Fenêtre d'observation : familles déclarées avant la borne ».

### Tests (rouge d'abord, jamais affaiblis)

- Reproducteurs S0-A (rouge sur l'assertion mesurée, re-prouvés par la
  revue sur `origin/main`) : `test_attention_real_chain.py` (attention,
  revue), `test_opportunities_real_chain.py` (preuves chassées).
- Reproducteurs S0-C : `test_observation_window_families.py` (souligné,
  pourcent ; le séparateur `/` vert avant comme après),
  `test_opportunities_real_chain.py::test_les_preuves_de_tous_les_candidats_sont_lues_sans_une_requete_par_instrument`
  (7 → 2 lectures).
- Gardes S0-D : équivalence par instrument contre PostgreSQL (borne PAR
  instrument, familles, ordre, hors fenêtre et futur exclus, référence
  sans ligne → liste vide, référence non demandée absente, doublon lu une
  fois) ; refus unitaire d'une demande vide ou mal formée.
- Témoin S0-E : `test_calendar_events_are_served_by_their_own_page_not_by_the_queue`.
- Ajustés, assertions intactes : `test_real_profile_chain.py` (dépêche
  DÉRIVÉE `ibkr.news-headline/1`, la seule qui porte un titre),
  `test_worker_failure_paths.py` (déclare `demo-news/` pour sa fixture).

### Mesuré sur cette machine (codes relus, venv du worktree, sans `env.live`)

- `ruff check .` : All checks passed ; `mypy` : 0 erreur, 143 fichiers.
- `pytest apps/worker/tests` : 378 passed.
- `pytest -p no:xdist apps/worker/tests_integration` (sous
  `flock /tmp/vertex_test.lock`) : 53 passed.
- `pytest apps/api/tests` : 1287 passed (relais inchangé : la couverture
  reste `FrozenStrMapping`, aucun fichier `apps/api` touché, OpenAPI
  intact).
- `tools/check_financial_boundary.py` et `tools/check_calculation_registry.py` :
  ok, 0 finding (aucun calcul financier nouveau).

### Comportement changé en développement, DÉCLARÉ

- `synthetic-calendar-event/` (porte un titre) n'entre plus dans la file
  d'attention ni dans le contexte d'information de la revue ; la page
  Calendrier et Catalyseurs les servent toujours. Cohérent avec la
  politique `news_attention` ; réintroduire les catalyseurs dans la file est
  une décision de produit, qui passe par `CONTENT_SCHEMA_PREFIXES`.
- `observations_considered` (attention, revue) ne compte plus que les
  familles déclarées ; `population` vaut `EMPTY` (et non `REAL`) quand
  seules des cotations sont en fenêtre.

### Transmis, non corrigé ici

- `observations` n'a d'index que sur `as_of` : un index
  `(instrument_ref, as_of)` et/ou `(schema_version text_pattern_ops,
  as_of)` est un lot de migration dédié (`DEBT.md`, « Trouvé au lot
  SRV-S0 »). Analyse exécute toujours une lecture par instrument à barres.
- Six autres chargeurs émettent `LIKE '<préfixe>%'` sur des CONSTANTES du
  code (aucune ne porte `%` ni `_`) ; à unifier sur `_schema_family_filter`.
- Non vérifié sur données réelles : la mesure « 0 item à 08:40 UTC » est
  reproduite en base de test, pas rejouée sur `vertex_live` ; la présence
  de lignes `ibkr.news-headline/1` en base vivante n'a pas été interrogée
  (sans elles, la file reste vide — honnêtement) ; fusion combinée avec L1
  (`ibkr.quote/1`, PR #32) non testée sur branche combinée, les deux
  préfixes sont couverts par le reproducteur.

Prochaine commande recommandée : pousser `lot/srv-s0-attention-fenetre-20260903`
et ouvrir la PR (orchestrateur), puis lot de migration `0008` pour l'index
`(instrument_ref, as_of)` avec mesure `EXPLAIN` avant/après sur une copie
de `vertex_live`.

## SESSION 2026-09-03 — LOT SRV-S0-F : le rail de preuves affamé par sa propre déclaration

Même branche, même worktree. Correction d'une RÉGRESSION introduite par S0-B
et détectée par la CI GitHub (exécution 33750177958, tâche « e2e — Chromium,
3 viewports desktop, axe », trois échecs identiques sur les trois viewports) :

    ✘ e2e/ai-inspector.spec.ts:89 › extraits externes
    > 122 |     expect(answer.external_excerpts.length).toBeGreaterThanOrEqual(1);
    Expected: >= 1
    Received:    0

### Cause exacte

S0-B a cadré le rail de preuves sur `CONTENT_SCHEMA_PREFIXES` — les trois
appels du chargeur qui l'alimentent portent aujourd'hui la déclaration
corrigée : `apps/worker/src/vertex_worker/analysis.py:1261`,
`apps/worker/src/vertex_worker/opportunities.py:940` (fenêtres par
instrument) et `:956` (fenêtre globale de repli). Or, dans la
population de démonstration, les dépêches synthétiques parlent des tickers
`SYN1`..`SYN9` (`vertex_core/synthetic/generator.py:317`) et JAMAIS d'un
ticker de l'univers : les seules observations titrées rattachées à
`SYN-TECH-01` sont ses événements de calendrier
(`synthetic-calendar-event/1.0`, `vertex_core/synthetic/events.py:156`,
`instrument_id = ticker`). `_build_evidence`
(`apps/worker/src/vertex_worker/analysis.py:726`) ne retenant que les
observations titrées de l'instrument, le rail est passé de plusieurs grappes
à `clusters: []`, `considered: 0`. Les extraits externes de l'explication IA
n'ont qu'une source — `evidence.clusters[].title`, lu par
`apps/api/src/vertex_api/ai_explain.py:1658` — donc le bloc « Contenu externe
non vérifié » est devenu vide, sans erreur ni journal.

### Ce qui est livré

- `EVIDENCE_SCHEMA_PREFIXES` (`handlers.py:178`) : la déclaration du RAIL —
  `CONTENT_SCHEMA_PREFIXES` + `CALENDAR_EVENT_SCHEMA_PREFIXES`. Explicite,
  deny by default, jamais une liste vide ni un retour à « toutes les
  familles » : les familles de marché (sans titre) restent dehors.
- Les DEUX consommateurs du rail la déclarent : `AnalysisHandler`
  (page Analyse) et `OpportunitiesHandler` (deux appels : fenêtres par
  instrument et fenêtre globale de repli).
- Les DEUX consommateurs de la file (attention, revue) sont inchangés :
  ils lisent toujours `content_schema_prefixes`, sans les événements de
  calendrier.

### Tests (rouge d'abord)

- `apps/worker/tests_integration/test_evidence_rail_families.py` (nouveau,
  rouge avant) : semis SYNTHETIC réel (barres + événements) → VRAI worker
  drainé → `analysis/SYN-TECH-01` porte au moins une grappe titrée ;
  `opportunities/global` cite les mêmes ; la file d'attention reste VIDE
  sur la même base (témoin du partage).
- `apps/api/tests_integration/test_ai_explain_e2e.py` (fixture élargie aux
  événements de calendrier, test ajouté, rouge avant) :
  `POST /api/v1/ai/explain` rend au moins un extrait externe, chacun
  rattaché à une grappe réellement publiée, étiqueté `EXTERNAL_UNVERIFIED`
  et absent des affirmations. C'est l'assertion e2e, au niveau serveur.
- `apps/worker/tests/test_evidence_rail_declaration.py` (nouveau, garde) :
  une famille titrée du semis qu'aucun consommateur du rail ne déclare est
  refusée, ET un préfixe synthétique déclaré que le semis ne produit pas
  l'est aussi. Rejoué avec la déclaration d'avant le correctif : 3 tests
  sur 5 échouent — la garde aurait attrapé la régression.

### Non vérifié ici

Les parcours e2e Playwright ne sont pas lancés sur cette machine (ports 8000
et 4173 servent la pile vivante de l'utilisateur) : c'est la CI GitHub qui
jugera `e2e/ai-inspector.spec.ts`.

## SESSION 2026-09-03 — LOT P4 : Portefeuille et Risques sur les formes v2

Branche `lot/w2-portfolio-risks-20260903`. Les deux planches passent aux
primitives du socle v2 (ADR-017) et à la matière des cartes recomposées. Ce
qui suit est ce que les CAPTURES ont montré, puis ce qui a été corrigé.

### Ce que la capture a trouvé, que les tests ne voyaient pas

1. **Le bloc `@media (min-width: 1600px)` de la planche Portefeuille n'était
   jamais fermé.** Tout ce qui le suivait dans `widgets.css` — le rayon, la
   surface, l'ombre, la taille des chiffres, la géométrie de la
   concentration — n'était appliqué qu'au-delà de 1600 px. Les deux planches
   étaient plates à 1280 et 1440. Détecté par `biome check` (« expected `}`
   but instead the file ends ») une fois le fichier relu, jamais par un test
   de rendu.
2. **La table des lots perdait deux colonnes.** Dix colonnes sur trois quarts
   de largeur : « Valeur marquée » et « P&L latent » sortaient du cadre et ne
   se lisaient qu'au défilement horizontal. La table prend la largeur entière
   de la planche.
3. **Le chiffre central de l'anneau traversait l'anneau.** Le Herfindahl servi
   fait 29 caractères ; écrit à la taille d'affichage dans une boîte aussi
   large que le module, il débordait des deux côtés. Ni arrondi (ce serait une
   valeur que le serveur n'a pas servie) ni tronqué (ce serait cacher des
   décimales) : la primitive DIT la densité du texte servi (`data-density`) et
   la feuille de style lui donne le cran typographique qui le fait tenir
   ENTIER dans le creux, replié.
4. **La matrice de corrélation n'avait aucune bande visible.**
   `--vx-signal-soft` (0,15) et `--vx-signal-faint` (0,065) ne se distinguaient
   pas d'une cellule à l'autre, et les pastilles de la légende étaient rendues
   à zéro pixel. Deux jetons de tension ajoutés (`signal-strong`,
   `macro-strong`), échelle à quatre crans, pastilles dimensionnées. La teinte
   ne porte jamais seule : le coefficient est écrit dans la case, la bande est
   nommée dans la légende et répétée dans `data-band`.
5. **La pastille d'état de la matrice affichait « ok ok »** : le libellé et le
   code servis étaient la même chaîne. Un code n'est plus montré que s'il dit
   autre chose.

### Un zéro fabriqué, corrigé rouge d'abord

`PortfolioSummary` écrivait « (0 événement(s) de trésorerie au journal) »
quand le serveur ne publiait AUCUN compte (`coverage.cash_events` absent).
Un zéro fabriqué est un fait de journal inventé. Test reproducteur écrit
avant le correctif (`PortfolioPage.test.tsx`, « compte d'événements de
trésorerie NON publié ») : rouge sur le code d'avant, vert après ; la
phrase dit maintenant « nombre d'événements de trésorerie non publié » et
ne contient plus aucun chiffre.

### Ce qui est livré

- **Valorisation publiée** : bande de trois mesures (`Metric`), chiffres
  serveur verbatim avec leur devise, tuiles alignées en grille. Le SIGNE ne
  vient que du serveur (`signGroupOfText`, socle v2) : une chaîne positive
  publiée sans « + » n'a pas de signe publié, donc pas de couleur. Une seule
  règle de signe sur la page.
- **Concentration** (dominante) : anneau de parts servies à chiffre central +
  bande de parts + table équivalente ; l'anneau et sa légende ont la place de
  leur chaîne exacte.
- **Corrélations** (dominante Risques) : `CellGrid` pleine largeur, cases à la
  taille d'une case, échelle de bandes lisible, légende à pastilles.
- Planche Portefeuille recomposée : bande de mesures en tête, dominante
  ensuite, table pleine largeur, puis journal, écritures et absences
  déclarées ; variante à cinq colonnes au-delà de 1600 px.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info (préexistante, `OptionsModules.tsx`), 0 erreur.
- `npx vitest run` : 87 fichiers, 908 tests, tous verts.
- Playwright, cinq spécifications aux trois viewports desktop
  (`portfolio`, `portfolio-performance`, `risk`, `shell-canonical`,
  `accessibility`) : **276 passés, code 0**.
- `bash tools/run_checks.sh` : toutes les portes vertes SAUF
  `apps/edge-ibkr/tests/test_denylist.py::test_adapter_satisfies_the_port_protocol`,
  rouge PRÉEXISTANT — rejoué sur le checkout `origin/main` (`b22ea20`) avec
  le même Python 3.11.15 local : même échec, hors de ce lot.

### Dette laissée, nommée

Les règles CSS `.vx-riskmatrix-*` (ancien composant `CorrelationMatrix`,
supprimé) sont mortes mais dispersées dans `global.css` : elles ne sont pas
retirées ici pour ne pas mêler un nettoyage large à ce lot.
