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

## SESSION 2026-09-03 — LOT P1 : Aujourd'hui et Marchés sur les formes v2

Branche `lot/w2-today-markets-20260903`, partie de `main` à `cd7cb1a` (P4
fusionné). Les deux planches passent aux primitives du socle v2 pour les
familles de données qu'elles servent.

### Ce qui change de forme

- **Breadth** (Marchés et Aujourd'hui) : la part bornée servie prend l'ARC
  gradué (`ArcGauge`), sa couverture prend la JAUGE LINÉAIRE avec son seuil
  (`LinearGauge`), et les trois comptes de sens prennent les BARRES DE
  DÉNOMBREMENT (`CensusBars`). Trois familles de donnée, trois formes.
- **Où vit le seuil.** `coverage_threshold_pct` est un seuil de COUVERTURE.
  Le plan v2 l'écrivait en raccourci sur l'arc de la breadth ; l'y poser
  l'aurait placé sur une autre échelle que la sienne et aurait fait lire
  « 80 % de breadth » là où le serveur dit « 80 % de couverture exigée ». Il
  vit sur la jauge de couverture, à sa place.
- **Une donnée, une forme.** Le module « Marché global » d'Aujourd'hui lisait
  le même bloc servi que la page Marchés et le rendait autrement. Il emprunte
  désormais la forme de son propriétaire (`BreadthPanel`) au lieu de la
  redéclarer. La mesure « Couverture » locale disparaît avec ce partage :
  elle répétait ce que la jauge et la phrase de comptes disent déjà.
- **Santé de la couverture** (Marchés) : trois mesures servies + dénombrement
  des reçus, couverts, écartés et rejetés. Aucun pourcentage n'est fabriqué —
  le contrat publie des comptes, pas un taux de couverture.
- **Capacités** et **statuts de gate** (Aujourd'hui) : recensements en barres.
- **Latent du portefeuille manuel** (Aujourd'hui) : pastille `KpiDelta`, avec
  la MÊME règle de signe que la planche Portefeuille (`signGroupOfText`) —
  la couleur n'apparaît que si la chaîne servie porte son signe. L'ancien
  `signOf` local, qui déduisait « positif » de l'absence de « - », est
  supprimé : deux règles de signe sur deux pages se contredisaient.
- **Écarts et rejets** (Marchés) : chaque raison servie devient une pastille
  nommée (`StatusChip`), jamais un code nu.

### Le piège de placement, une seconde fois

Convertir les modules de Marchés en `Widget` leur donne `data-size`, donc les
règles de span du socle (`.vx-w2[data-size='M'] { grid-column: span 2 }`). À
spécificité égale, `widgets.css` étant importée en dernier, ces spans
écrasaient les zones nommées de `.vx-markets-grid`. C'est exactement le défaut
mesuré au LOT P4 sur les planches Portefeuille et Risques. Le placement de la
planche §2 a donc DÉMÉNAGÉ dans `widgets.css`, après les spans — et la
planche en profite pour remonter ses deux mesures servies en tête.

### Vu sur capture, corrigé

- La jauge de couverture était COUPÉE en plein texte dans la colonne étroite
  d'Aujourd'hui : la grille des figures s'ouvrait sur une largeur de
  VIEWPORT, qui ne dit rien de la largeur de la CELLULE. Elle est passée en
  `auto-fit`, et se replie sur une colonne là où il n'y a pas la place.
- Les bornes d'une jauge se lisaient « 0100 » : la valeur servie prend
  désormais sa propre ligne, les bornes la suivante, chacune à son bord.
- Le seuil était écrit deux fois sous la même jauge.

### Nettoyage

Les règles CSS de l'ancienne `BreadthPanel` (`.vx-breadth-row`, `-bar`,
`-fill`, `-threshold`, `-label`, `-figure`) et de l'ancien recensement
(`.vx-status-census*`) sont retirées : plus aucun fichier `.ts`/`.tsx` ne les
porte. Vérifié par recherche avant retrait, et `pnpm build` repasse.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 87 fichiers, 908 tests, tous verts.
- Playwright `today`, `markets`, `shell-canonical`, `accessibility` aux trois
  viewports desktop : **252 passés, code 0**.
- `bash tools/run_checks.sh` : vert sauf le rouge PRÉEXISTANT
  `test_denylist.py::test_adapter_satisfies_the_port_protocol` (rejoué à
  l'identique sur `origin/main`, Python 3.11.15 local).

### Reste à faire sur ces deux planches

Le module `calendar` d'Aujourd'hui garde sa liste `AgendaLine` : le passage à
`ActivityFeed` perdrait la lecture du temps servi par fuseau, et rien ne le
justifie tant que la primitive ne la porte pas. Les anneaux de poids sectoriel
(`weight_in_sector_pct`) attendent le lot Marchés suivant.

## SESSION 2026-09-03 — LOT P5 : Graphiques, et trois modules qui mentaient

Branche `lot/w2-charts-20260903`, base `main` à `11251d4` (P1 fusionné).

### L'aveu devenu faux

`chartsView.ts` déclarait `overlays`, `rsi` et `macd` **absents**, note à
l'appui : « Aucun calcul … n'est déclaré au registre des calculs ni publié par
un snapshot ». C'était exact avant le LOT-S6. Ça ne l'est plus : le worker
publie `indicators.overlays.{sma, ema, bollinger_bands}` et
`indicators.oscillators.{rsi, macd}`, chacun avec sa série RENDUE en chaînes,
sa méthode, ses paramètres et sa lignée
(`apps/worker/src/vertex_worker/analysis.py:972-977, 1056-1194`). Une absence
qui a cessé d'être vraie n'est plus une prudence : c'est un mensonge.

Test reproducteur écrit ROUGE d'abord (`chartsView.test.ts`) : les trois
modules sont servis par le contrat Analyse. Conséquence exacte sur l'e2e :
`charts.spec.ts` attendait **8** badges d'absence, il en attend **5** — la
même assertion, sur un compte devenu juste.

### Ce qui est livré

- **Lecture des blocs S6** (`indicatorBlockOf`, `indicatorFamilyOf`, huit cas
  de test) : trois formes servies reconnues sans en deviner aucune — série
  simple (`points[{trading_day, value}]`), bandes (`points` + `bands`), lignes
  (`series` + `lines`) — et trois refus relayés tels quels
  (`INSUFFICIENT_SAMPLE` avec son détail, `REFUSED` avec son code, bloc
  amputé déclaré illisible).
- **Un FAIT constaté, jamais corrigé** : `aligned` dit si les lignes d'un bloc
  partagent leurs séances. Les bandes de Bollinger les partagent (une même
  liste de points) et se superposent en `MultiSeriesArea` — **première pose de
  cette primitive**. Les trois lignes du MACD commencent à des séances
  différentes : chacune garde sa figure, parce que les aligner ici produirait
  une comparaison que personne n'a publiée.
- **`PeriodTabs`, première pose** : fenêtres d'affichage (20 / 60 / 120
  séances / tout le servi) bornées par `bars.count` SERVI ; une fenêtre plus
  large que la série est désactivée avec son motif visible. La description de
  la figure dit désormais le compte publié ET le compte affiché.
- **`ArcGauge` sur le RSI** : l'unité SERVIE est `index_0_100` — le serveur
  déclare l'échelle, la valeur servie EST sa position, l'arc n'en dérive
  aucune. Si l'unité change, la forme est refusée plutôt que réinterprétée.
- **`DayBars` sur le volume**, **`SparkFigure` en aire** sur chaque série
  d'indicateur, **planche §8** en aires nommées (elle n'en avait aucune : ni
  `vx-board`, ni `Card`, ni `Widget`), accent `macro` posé, matière v2 étendue.

### Trois défauts de primitive, trouvés parce qu'une planche a enfin servi ces formes

1. **Aucune barre n'était jamais peinte.** `DayBars` posait
   `height: <part>%` sur un enfant d'un conteneur dont la hauteur venait de
   `flex: 1 1 auto` — indéfinie pour la résolution des pourcentages. Le DOM
   portait bien « height: 100% » ; l'écran ne montrait qu'un rail vide. Le
   défaut est resté invisible tant que la seule planche à poser cette forme
   servait des comptes nuls (Risques). La barre est désormais positionnée, et
   résout son pourcentage contre un bloc conteneur de hauteur définie.
2. **« Pas de bande » se lisait « bande non publiée ».** Sans vocabulaire de
   bandes déclaré, chaque barre tombait sur `unknown`, dont la teinte fantôme
   dit une absence — sur une donnée complète, et en la rendant invisible. Une
   bande n'est un manque que si l'appelant a DÉCLARÉ un vocabulaire.
3. **Un signe affirmé sur une mesure qui n'en a pas.** `SparkFigure` exigeait
   un sens financier ; une moyenne mobile ou un RSI n'en ont aucun. Le signe
   est devenu facultatif : sans lui, l'attribut n'existe pas.

Plus deux corrections de lisibilité mesurées sur capture : le chiffre central
de l'arc (un RSI servi fait quatorze caractères) descend d'un cran plutôt que
de déborder — même remède que l'anneau au LOT P4, désormais partagé
(`textDensityOf`, `geometry.ts`) ; et le titre du module de comparaison n'est
plus écrit deux fois l'un sous l'autre.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 87 fichiers, **919 tests**, tous verts.
- `npm run build` : succès.
- Playwright `charts`, `analysis`, `risk`, `shell-canonical`, `accessibility`
  aux trois viewports desktop : **267 passés, code 0**.
- `bash tools/run_checks.sh` : vert sauf le rouge PRÉEXISTANT
  `test_denylist.py::test_adapter_satisfies_the_port_protocol`.

P5 fusionnée en squash (`700355c`, PR #44).

## SESSION 2026-09-03 — LOT T1 : le verre noir de CHAQUE carte

Branche `lot/t1-black-glass-20260903`, base `main` à `700355c` (P5 fusionné).

Ce lot ne touche à aucune donnée, aucune vue, aucun contrat : il ne change que
le SOCLE visuel, et il le change pour tout le produit d'un coup — c'est
précisément la demande « le côté glass black de CHAQUE carte ».

### Ce qui change

- **Jeton `shadow.glass`** (`0 10px 28px rgba(0, 0, 0, 0.34)`) : la profondeur
  de la carte ORDINAIRE, plus courte et plus proche que `panel`, qui reste
  celle d'une planche entière. `tokens.css` régénéré par `npm run tokens:css`.
- **`.vx-card`** : rayon 18 au lieu de 10, et `box-shadow: glass, inset`. Trois
  choses font l'épaisseur du verre et AUCUNE n'est une lumière — un rayon
  large, une arête claire d'un pixel en haut, une ombre portée courte. Pas de
  flou de fond, pas de halo, pas de dégradé de fond plein : ADR-017 les
  interdit, et c'est ce qui sépare un verre noir sobre d'un template SaaS.
- **`.vx-primary-action`** en pilule : l'action principale prend la forme des
  boutons des tableaux de bord de référence, sans changer sa couleur ni son
  unicité par page.
- **`PeriodTabs` en contrôle segmenté** : une piste creuse, des pastilles sans
  bordure, chiffres en `font-mono`, et la seule fenêtre choisie remplie dans la
  famille `signal`. C'est la règle « gradients et lumière : sélection / action
  principale » du design system, appliquée à la seule commande de vue du
  produit.
- **`StatusChip` à hauteur unique** (22 px, `tabular-nums`, `nowrap`) : deux
  chips voisines ne sautent plus d'un pixel selon leur texte.
- **Typographie des mesures généralisée** : `.vx-metric-value` et
  `.vx-metric-label` ne sont plus réservées à cinq planches nommées. Un chiffre
  servi se lit de la même façon partout.

### Ce que ce lot ne fait PAS

Aucune valeur, aucun signe, aucune unité n'est ajoutée, retirée ou reformatée.
Aucune forme n'est posée sur une donnée non servie. Le test
`tokens-css.test.ts` passe de trois à quatre ombres — assertion élargie au fait
nouveau, jamais affaiblie : elle vérifie toujours l'ordre exact des clés ET la
présence de chaque valeur dans le CSS commité.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 87 fichiers, **919 tests**, tous verts.
- `npm run build` : succès.
- Playwright, **suite complète** aux trois viewports desktop : **546 passés**
  (11,6 min), code 0.

**T1 bloquée à la fusion, pour une raison externe.** PR #45 : six checks requis
**T1 a été bloquée à la fusion, pour une raison externe — résolu depuis.** PR #45 : six checks requis
verts sur `353e1fa`, le septième — `supply-chain — audit des dépendances,
SBOM` — meurt sur `ERR_SOCKET_TIMEOUT` vers
`registry.npmjs.org/-/npm/v1/security/audits/quick`, avant tout résultat
d'audit. Le même job est rouge sur `main` au commit `700355c` (run
33839118821), et `pnpm install --frozen-lockfile` réussit dans le même job :
c'est le point de terminaison d'audit qui ne répond pas, pas le dépôt. Un seul
rejeu tenté, même timeout. La porte n'est PAS assouplie : un `|| true` ou un
`--audit-level` abaissé transformerait une panne passagère en trou permanent.

**Suite.** Le point d'audit s'est révélé INTERMITTENT et non durablement en
panne : vert à 06 h 36 et 06 h 50, de nouveau en timeout à 07 h 17, vert
ensuite. T1 est fusionnée en squash (`cd7399f`) dès qu'un rejeu a attrapé une
fenêtre verte. Deux runs coexistaient sur le même SHA — celui du `push` et
celui de la `pull_request` — et la règle de branche exige les DEUX : ne
relancer que celui de la PR laissait la porte rouge sans que rien ne le dise.

## SESSION 2026-09-04 — LOT T2 : la tuile de mesure, et le catalogue d'icônes partagé

Branche `lot/t2-kpi-tile-20260904`, empilée sur T1 tant que #45 ne peut pas
fusionner.

### Deux primitives

- **`Glyph`** — le catalogue SVG approuvé (21 icônes de
  `design-assets/icons/custom/`), extrait de `NavGlyph` qui en masquait dix
  pour le seul rail. Masque en `currentColor` : aucune couleur n'est encodée
  dans l'icône. `aria-hidden`, jamais porteuse seule d'une information.
  `satisfies Record<GlyphName, string>` : ajouter un nom sans son fichier
  casse la COMPILATION, jamais l'écran. `NavGlyph` ne décide plus que d'une
  chose — quelle icône appartient à quelle destination.
- **`KpiTile`** — pastille d'icône, libellé, GRAND chiffre servi, unité,
  variation servie, série optionnelle. C'est la forme la plus répétée des
  tableaux de bord de référence, et Vertex l'assemblait jusqu'ici à la main,
  différemment sur chaque page.

### Ce que la tuile REFUSE, et c'est tout son objet

1. **Sans valeur servie, elle se dépouille** : pas de teinte (teinter, c'est
   qualifier un vide), pas de pastille de variation, pas de figure de série,
   pas même l'unité — une unité seule n'est pas une donnée, c'est le décor
   d'une donnée qui manque. Elle DIT l'absence à la place.
2. **Le signe ne vient jamais de la tuile.** `valueSign` est tiré par
   l'appelant du signe TEXTUEL de la chaîne servie ; sans lui, aucun attribut,
   donc aucune couleur. Le vocabulaire de teintes EXCLUT `positive` et
   `negative` : ils appartiennent au signe financier servi, jamais à une
   pastille d'icône, qui n'a rien à qualifier.

Sept cas de test, dont quatre refus, tous **rouges d'abord**.

### Trois défauts de géométrie, vus seulement en navigateur

1. **Une tuile faisait 160 px de haut pour 55 px de texte.** `.vx-board`,
   `.vx-today-grid` et `.vx-markets-grid` posent `flex-direction: column` sur
   `.vx-metrics-row` : dans cette pile, le `flex: 1 1 160px` de la tuile
   devient une HAUTEUR. Trois dénombrements occupaient 480 px pour 165 px de
   texte. Mesuré par sonde en navigateur, jamais par un test.
2. **Les lignes repliées s'étiraient.** `align-content` vaut `stretch` par
   défaut : dans une carte plus haute que son contenu, l'espace restant était
   distribué ENTRE les lignes. Les mesures se serrent désormais en haut.
3. **La pastille de variation débordait** en colonne étroite : « 74.75 | signe
   non publié | SYN » se centrait sur deux lignes bancales. Elle se replie
   maintenant à gauche et ne dépasse plus sa carte.

### Consommateurs posés

Portefeuille (bande de valorisation, trois devises), Aujourd'hui (les trois
dénombrements d'Opportunités, la valeur du portefeuille manuel).

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 89 fichiers, **929 tests**, tous verts.
- `npm run build` : succès.
- Playwright `today`, `portfolio`, `markets`, `shell-canonical`,
  `accessibility` aux trois viewports desktop : **276 passés**, code 0.

## SESSION 2026-09-04 — LOT T3 : les cartes cessent de faire la même taille

Branche `lot/t3-planches-bento-20260904`, empilée sur T2.

### Le défaut, et pourquoi il était partout

`.vx-board`, `.vx-today-grid` et `.vx-markets-grid` posaient
`align-items: stretch`, et la carte prenait `height: 100%`. Une rangée faisait
donc partout la hauteur de son module le plus haut : un module de trois lignes
se retrouvait dans un cadre de 400 px dont 340 étaient vides. Mesuré sur
capture d'Aujourd'hui, rangée 1 — quatre cartes de hauteur identique, trois
presque vides. C'est exactement la remarque « entre les cartes c'est toujours
la même ».

### Le remède, et sa limite

Une carte prend désormais la HAUTEUR DE SON CONTENU (`align-items: start`).
L'espace restant redevient du fond, pas un cadre vide : c'est la composition
en pavés des tableaux de bord de référence.

Ce qui NE change pas : les aires nommées, l'ordre de lecture, la dominante.
Une planche reste une composition déclarée, jamais un flux.

L'exception est DÉCLARÉE, pas devinée : un module `L` ou `XL` porte une figure
qui a besoin de sa hauteur (courbe, matrice, file). Ceux-là gardent `stretch`,
et c'est `data-size` — publié par le catalogue de la page — qui le dit, jamais
une classe écrite à la main sur une carte.

### Un chiffre coupé en deux, corrigé au passage

La jauge de couverture écrivait « 91,7 % (seuil 80,0 %) » en un seul texte :
dans une carte de 200 px il se coupait, et la seconde ligne ne portait que
« %) ». Deux mesures servies méritent deux textes : la couverture se lit
seule, le seuil vit sur son marqueur, à sa place sur la même échelle. Le
chiffre du seuil n'est ni répété ni perdu. Test rouge d'abord.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 89 fichiers, **929 tests**, tous verts.
- `npm run build` : succès.
- Playwright, **suite complète** : **546 passés** (8,5 min), code 0.

## SESSION 2026-09-04 — LOT T4-0 : le socle de l'absence, et sa porte

Branche `lot/t4a-tiret-ambigu-20260904`, empilée sur T3.

### Le défaut, mesuré

`.claude/rules/frontend.md:21` l'écrit noir sur blanc — « ne jamais remplacer
une donnée absente par `0`, `—` ambigu, une fixture ou une ancienne valeur non
datée ». L'interface le violait **163 fois, sur 33 fichiers**.

Le pire cas :
`<dd className="vx-num">{reference.eventsUpcoming ?? '—'}</dd>`, dans une liste
où les voisins affichent de VRAIS comptes. Un lecteur ne peut pas distinguer
« zéro événement servi » de « compteur non publié ». Ce n'est pas de la
cosmétique : c'est exactement le fait financier que l'invariant protège.

Fait qui donne la stratégie : les quatre planches déjà converties aux
primitives v2 (Aujourd'hui, Marchés, Risques, Graphiques) en portent **zéro**.
Le tiret survit exactement là où la page écrit encore son JSX à la main.

### La règle, et pourquoi ce n'est PAS « aria-label + title »

Première hypothèse : tolérer le tiret s'il porte `aria-label` ET `title`.
Écartée, pour quatre raisons dont une bloquante :

1. **Trivialement satisfaisable** — `aria-label="valeur" title="valeur"` la
   passe. Une porte qui certifie un mensonge finit désactivée.
2. Elle ne vérifie pas que le libellé vient du **serveur**.
3. **Elle bénissait une régression d'accessibilité** : c'est `role="img"` qui
   donne le nom accessible ; sur un `<span>` au rôle implicite `generic`, ARIA
   ignore `aria-label`. Le dépôt le savait déjà — le commentaire d'
   `OptionInspector.tsx` le disait — la porte l'aurait défait.
4. Inapplicable à 95 % des sites : `<code>{x ?? '—'}</code>` naît d'un `??`,
   pas d'un élément portant des attributs.

**La tolérance n'est donc pas une liste d'attributs : c'est un composant
NOMMÉ.** `src/components/absence.tsx` est le seul fichier du dépôt autorisé à
écrire le glyphe, et `AbsentCell` ne peut être posé sans `quoi`, `nature` ET
`reason`. Il n'y a pas de manière astucieuse de passer : il faut regarder ce
qui manque.

### La porte

`src/design/no-ambiguous-dash.test.ts`, trois règles AST :

- **A — égalité EXACTE, sans `trim`.** L'absence de `trim` est le cœur de la
  règle : le dépôt écrit `{' — '}` comme séparateur de prose, avec ses espaces.
  Un substitut n'en a pas. **Les espaces portent l'intention.**
- **B — position de repli, avec `trim`** : anti-contournement de A.
- **C — texte JSX enfant unique** : `<td>—</td>` est un substitut,
  `— <code>{x}</code>` est de la ponctuation.

Jeu de glyphes : cinq variantes de tiret, `?`, `N/A`, `s.o.` — `?` était le
MÊME défaut avec un autre caractère, et le dépôt en portait dix.

**Quatre exclusions, chacune découverte par un faux positif de la première
version** — donc mesurées, pas supposées : littéral comparé
(`pct.startsWith('-')` LIT le signe servi), argument d'appel, élément de
tableau, `import`/`case`. Les points de suspension ont été RETIRÉS du jeu :
leur seul site les ajoute après un libellé tronqué, ils marquent une
troncature, pas une absence.

**La dette est écrite, comptée et décroissante.** `DETTE_T4` liste les 39
fichiers restants avec leur lot ; `ALLOWLIST` ne contient qu'une entrée
permanente. La séparation est le point de conception : une dette déguisée en
exemption ne se rembourse jamais. Cliquet dès ce lot — aucun NOUVEAU tiret ne
peut entrer.

### Ce que la porte a trouvé que je n'avais pas vu

- **Cinq copies** du même composant d'absence, pas deux
  (`OptionChainTable`, `OptionInspector`, `AttentionQueue`, `SnapshotRail`,
  `SourceHealthMatrix`).
- Deux `?? '?'` de plus dans `OptionChainTable` (un `aria-label`, un `title`).
- `calendarView.ts` renvoyant `'?'` comme marqueur de statut inconnu.

### Livré

- `absence.tsx` : `ABSENCE_NATURES` (cinq natures — `not_published`,
  `not_computed`, `not_applicable`, `not_entered`, `not_recognised`),
  `absenceLabel` avec accord en genre, `AbsentCell`. Le code SERVEUR reste
  verbatim dans le libellé : c'est lui la preuve, la traduction est un confort.
- `ProvenanceLine` gagne `schemaVersion`, **obligatoire et nullable** comme ses
  voisines — Opportunités la publiait et la rendait en tiret muet.
- Marquage CSS non-couleur : `.vx-cell-absent[data-absent='true']` prend un
  souligné pointillé. WCAG 1.4.1 — un gris sourd sur fond sombre EST une
  couleur seule.
- `OptionChainTable` migré sur le socle : le cas dense canonique, qui prouve
  le socle de bout en bout et sort de la dette.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 91 fichiers, **948 tests**, tous verts.
- `npm run build` : succès.
- Playwright `options`, `accessibility`, `shell-canonical` aux trois viewports :
  **237 passés**, code 0.
- Sonde navigateur sur la chaîne : 14 cellules d'absence, `role="img"`,
  `data-reason="price_outside_no_arbitrage_bounds"`, souligné effectif.

## SESSION 2026-09-04 — LOT T4-1 : Opportunités, et la ligne à six tirets

Branche `lot/t4-1-opportunites-20260904`, empilée sur T4-0. Dette T4 : **39 → 36**.

### Six tirets dans une seule ligne

`OpportunitiesPage.tsx` rendait la provenance ainsi : `snapshot_version ?? '—'`,
`as_of` → `'—'`, `engineVersion ?? '—'`, `schemaVersion ?? '—'`,
`universeSize ?? '—'`, `observationsConsidered ?? '—'`. Six faits différents,
six glyphes identiques, et aucun ne disait lequel manquait.

**Première pose de `ProvenanceLine`** — la primitive existait depuis le LOT-C0
sans aucun consommateur. Chaque champ absent y est dit à sa place. Les deux
DÉNOMBREMENTS sortent de la ligne : ce ne sont pas des faits de provenance, ils
prennent la forme `Metric`, qui rend nativement « non publié ».

Le conteneur passe de `<p>` à `<div>` : `ProvenanceLine` rend un `<p>`, et un
`<p>` dans un `<p>` est du HTML invalide. Le `data-testid` reste sur le
conteneur, qui porte l'assertion de fraîcheur.

`sources={[]}` est un FAIT, pas un oubli : le contrat Opportunités ne publie
aucune liste de sources, et la primitive le DIT.

### Le pire cas du lot : cinq compteurs

`<dd className="vx-num">{reference.eventsUpcoming ?? '—'}</dd>` — un tiret muet
dans une cellule numérique, **à côté de vrais comptes**. Un lecteur ne pouvait
pas distinguer « zéro événement à venir » — une DONNÉE — de « compteur non
publié ». Les cinq passent par `CountCell`, qui change aussi de classe : un
texte d'absence n'est ni chassé ni aligné comme un chiffre.

**La branche nulle n'avait jamais été exercée.** Test ajouté, et vérifié ROUGE
sur l'ancien code (`git show HEAD:… > fichier`, test rejoué, échec constaté,
fichier restauré) : il exige le mot, refuse le tiret, et vérifie qu'un ZÉRO
SERVI voisin survit — l'aveu ne l'absorbe pas.

### Le piège du lot : « sans objet » n'est pas « non publié »

`OpportunityTable.tsx:262` rendait `<td className="vx-num">—</td>` pour le rang
d'un candidat CONTRADICTOIRE. Ce candidat n'a pas de rang parce qu'il n'entre
pas dans le classement : **le serveur n'a rien omis**. Y écrire « non publié »
lui adresserait un reproche injustifié — un mensonge neuf à la place d'une
ambiguïté. Il prend `nature="not_applicable"`. Le rang d'un qualifié, lui,
peut réellement être non publié, et prend `not_published`.

### Un accord corrigé au passage

`ProvenanceLine` écrivait « sources non publié ». Une faute d'accord fait
douter du reste de la ligne. Le helper `Absent` prend désormais le genre et le
nombre — le français l'exige, et le deviner depuis le mot serait faux.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 91 fichiers, **949 tests**, tous verts.
- `npm run build` : succès.
- Playwright `opportunities`, `accessibility` aux trois viewports :
  **204 passés**, code 0.
- Sonde navigateur : la ligne rend « … · sources non publiées · méthode
  lexicographic · nature SYNTHETIC », aucun tiret.

## SESSION 2026-09-04 — LOT T4-2 : Portefeuille, et un défaut de clé React

Branche `lot/t4-2-portefeuille-20260904`. Dette T4 : **36 → 28**.

### Le tiret n'était pas qu'ambigu : il cassait React

`portfolioView.ts:216` typait `lotId: string` avec `?? '—'` en repli, et le
constructeur des positions invalides posait `lotId: '—'` **EN DUR** — donc
TOUTES les positions invalides partageaient le même identifiant.

Cette valeur servait de clé React (`PortfolioTable.tsx:118`,
`` `${lot.lotId}-${lot.ticker ?? ''}-${lot.reason}` ``). Deux positions
invalides de même ticker et même raison produisaient **deux fois la même clé** :
la réconciliation cassait. Et le tiret s'affichait dans la colonne
« identifiant de lot » comme s'il en était un.

`lotId` devient `string | null`. Une ligne sans identifiant servi prend son
**rang de rendu** dans la clé — un index n'est pas une donnée, c'est une
position, et c'est exactement ce qu'il est.

Test écrit ROUGE d'abord (`expected '—' to be null`).

### Quatre natures d'absence sur une seule page

Le Portefeuille est la destination qui les distingue toutes :

- **`not_published`** — le serveur n'a pas envoyé le champ (quantité, prix,
  instrument d'une écriture du journal).
- **`not_applicable`** — une position INVALIDE n'a pas de lot : elle a été
  rejetée avant d'en devenir un. Une ligne ni compensante ni compensée n'a
  rien à dire sur la compensation. Le serveur n'a rien omis.
- **`not_entered`** — l'aperçu d'import CSV : la case vide vient du fichier de
  l'HUMAIN. Écrire « non publié » y accuserait le serveur d'un vide qu'il n'a
  pas laissé.
- **Liste servie vide** — `incompleteReasons.length === 0` sur un mois
  complet : ce n'est pas une absence, c'est un FAIT. Elle devient « aucune ».
  Confondre les deux est la même faute que T4 corrige, dans l'autre sens.

### Une cellule d'action sans action ne dit rien

`LedgerPanel.tsx` rendait `<span className="vx-cell-absent">—</span>` dans la
colonne d'action des lignes non compensables. Il ne manque aucune valeur : il
n'y a simplement rien à faire sur cette ligne. La cellule est vide.

### Les tables denses gardent leur glyphe, et gagnent son sens

Journal (treize colonnes) et série quotidienne de performance (sept colonnes
numériques) : écrire « non publié » dans chaque cellule les rendrait
illisibles, et une table qu'on ne peut plus lire ne dit rien du tout. Elles
passent par `AbsentCell`, qui garde le tiret mais lui donne un `role="img"`,
un nom accessible qui NOMME le champ manquant, et un souligné pointillé.

Le risque mesuré était le plancher de reflow à 200 % de zoom
(`accessibility.spec.ts`) : il est vert, et `smoke.spec.ts` confirme l'absence
de défilement horizontal à 1024×768.

### Mesuré sur cette machine

- `npx tsc --noEmit` : code 0.
- `npx biome check src` : 1 info préexistante, 0 erreur.
- `npx vitest run` : 91 fichiers, **950 tests**, tous verts.
- `npm run build` : succès.
- Playwright `portfolio`, `portfolio-performance`, `accessibility`, `smoke` :
  **237 passés**, code 0.

## SESSION 2026-09-04 — LOT T4-3 : Catalyseurs, et la thèse écrite par l'humain

Branche `lot/t4-3-catalyseurs-20260904`. Dette T4 : **28 → 21**.

Vingt-cinq tirets sur sept fichiers. La distinction qui structure ce lot :

**Une thèse est RÉDIGÉE PAR L'UTILISATEUR.** `hypotheses`, `invalidation`,
`horizon`, `title` : leur absence ne reproche rien au serveur — c'est une case
du formulaire que personne n'a remplie. `not_entered`, jamais « non publié ».
`{thesis.hypotheses ?? '—'}` remplaçait tout un raisonnement d'investissement
par un glyphe ; il dit maintenant « hypothèses non renseignées ».

**Trois listes servies VIDES** cessent d'être des absences : les clés d'ordre,
les sources et les droits d'un cluster. Une liste vide est un FAIT publié.

**Un booléen servi `false` n'est pas une absence** :
`hasNewInformation === false` signifie « aucune », pas « on ne sait pas ».

**Une thèse peut ne viser AUCUN instrument** — elle porte alors sur un thème.
`not_applicable`, et le serveur n'a rien omis.

`thesisStatusLabel(null)` renvoyait `'—'` depuis la couche vue : le tiret
naissait donc AVANT le rendu, et se propageait partout où la fonction était
appelée. Il renvoie « statut non publié ».

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **950 tests** verts ; `npm run build` succès.
- Playwright `catalysts`, `accessibility` : **210 passés**, code 0.

## SESSION 2026-09-04 — LOT T4-4 : Calendrier, et un point d'interrogation qui ne disait rien

Branche `lot/t4-4-calendrier-20260904`. Dette T4 : **21 → 17**.

Vingt-trois glyphes sur quatre fichiers.

**Le plus instructif : `statusMarkOf` renvoyait `'?'`** pour un statut hors
contrat. Ce marqueur est TOUJOURS posé à côté de `statusLabelOf`, qui relaie
le statut servi verbatim — et sur `AgendaLine`, il est même `aria-hidden`. Le
point d'interrogation n'ajoutait donc rien à une information déjà complète,
et n'atteignait pas le lecteur d'écran. Il renvoie désormais une chaîne vide :
un statut hors contrat n'a pas de marqueur, et c'est juste.

Le reste suit les familles établies : identifiants et versions nommés,
dénombrements en `vx-cell-absent`, instants « non publié ».

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **950 tests** verts ; `npm run build` succès.
- Playwright `calendar`, `catalysts`, `today`, `accessibility` :
  **261 passés**, code 0.

## SESSION 2026-09-04 — LOT T4-5 : Analyse, et une devise remplacée par un tiret

Branche `lot/t4-5-analyse-20260904`. Dette T4 : **17 → 11**.

Vingt-cinq glyphes sur six fichiers, et un cas qui va plus loin qu'une
ambiguïté.

**`AnalysisPage.tsx:119` — `const currency = bars?.currency ?? '—'`.** Cette
devise était ensuite collée juste après la dernière clôture :
« dernière clôture 366.08 — ». Un lecteur pouvait prendre le tiret pour un
symbole monétaire, et **un prix sans son unité n'est pas une mesure**. Les
règles du dépôt exigent l'unité et la devise aux frontières ; le repli les
effaçait en silence.

Le reste : `?? '?'` dans quatre phrases assemblées (`analysisView.ts` et le
résumé de barres), instants « non publié », faits XBRL en table dense sur
`AbsentCell`, et deux `'—'` de branche (`bars === null`, `validUntil === null`)
que la porte a trouvés après la première passe.

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **950 tests** verts ; `npm run build` succès.
- Playwright `analysis`, `simulator`, `accessibility` : **219 passés**, code 0.

## SESSION 2026-09-04 — LOT T4-6 : Options, Marchés, Simulateur, Sources

Branche `lot/t4-6-options-marches-20260904`. Dette T4 : **11 → 3**.

Vingt-cinq glyphes sur huit fichiers, et la **dernière copie** du composant
d'absence (`OptionInspector`) fusionnée sur le socle : ses dix appels passent
de libellés libres à la signature structurée, ce qui force à choisir la nature
de chaque absence. Deux d'entre elles se révèlent `not_recognised` — un `right`
ou un `strike` ILLISIBLE n'est pas un champ manquant, c'est une valeur servie
hors vocabulaire.

**Le cas le plus délicat : `SimResult.EchoModule`.** Ce module montre ce que le
serveur a RÉELLEMENT appliqué, par opposition à ce que le formulaire
contenait. Un tiret y était le pire endroit possible pour une ambiguïté : le
lecteur ne pouvait pas distinguer « le serveur n'a pas renvoyé cette
hypothèse » de « il l'a renvoyée vide ». Les deux sont maintenant distincts,
et une liste renvoyée vide dit « aucune ».

Restent trois fichiers en dette (`AttentionQueue`, `SnapshotRail`,
`SourceHealthMatrix`) : leurs trois copies du composant d'absence, à fusionner
au lot T4-7.

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **950 tests** verts ; `npm run build` succès.
- Playwright `options`, `markets`, `simulator`, `sources-reports`,
  `accessibility`, `smoke` : **261 passés**, code 0.

## SESSION 2026-09-04 — LOT T4-7 : la dette est remboursée

Branche `lot/t4-7-fin-dette-20260904`. Dette T4 : **3 → 0**.

Les trois dernières copies du composant d'absence (`AttentionQueue`,
`SnapshotRail`, `SourceHealthMatrix`) fusionnent sur le socle. **`DETTE_T4` et
les deux tests qui en faisaient un cliquet sont supprimés** : ils n'avaient
d'autre raison d'être que la campagne, et une dette qui survit à son
remboursement devient une exemption déguisée.

### Le test qui m'a rattrapé

`SourceHealthMatrix` rendait « jamais sondé ». Je l'avais converti en
`AbsentCell` avec `nature="not_applicable"`, ce qui écrit « sonde sans
objet » — **c'est faux**. `tested_at === null` signifie qu'aucune sonde n'a
jamais tourné sur cette source : c'est un FAIT servi, pas une absence de
publication. Le test unitaire existant a refusé le changement, et il avait
raison.

C'est exactement la limite n° 3 déclarée dans l'en-tête de la porte : elle ne
juge pas si la NATURE choisie est la bonne. Écrire cette limite plutôt que la
masquer est ce qui a permis de la voir quand elle s'est manifestée.

Le fait se lit désormais en toutes lettres, sans glyphe à expliquer. L'e2e
correspondante passe de `[aria-label="jamais sondé"]` à un compte de texte
VISIBLE, plus une boucle qui vérifie que **tout** glyphe restant de la table
porte un `role="img"` et un nom qui NOMME le champ manquant — un invariant qui
ne dépend d'aucune arithmétique de fixture.

### Bilan de la campagne T4

| Lot | Destinations | Dette |
|---|---|---|
| T4-0 | socle + porte | 39 |
| T4-1 | Opportunités | 36 |
| T4-2 | Portefeuille, Performance | 28 |
| T4-3 | Catalyseurs | 21 |
| T4-4 | Calendrier | 17 |
| T4-5 | Analyse | 11 |
| T4-6 | Options, Marchés, Simulateur, Sources | 3 |
| T4-7 | shell et matrices | **0** |

163 glyphes substitutifs éliminés sur 33 fichiers. Cinq copies du composant
d'absence fusionnées en une. Un défaut de clé React corrigé. Une devise qui se
lisait comme un symbole monétaire. Deux tests qui gelaient un défaut,
resserrés — aucun affaibli.

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **948 tests** verts ; `npm run build` succès.
- Playwright, **suite complète** : **543 passés** (8,9 min), code 0.

Le compte de tests passe de 950 à 948 : les deux tests de gouvernance de la
dette disparaissent avec elle. Aucun test de comportement n'a été retiré.

## SESSION 2026-09-04 — LOT P2a : les oscillateurs servis, enfin affichés sur le dossier

Branche `lot/p2-analyse-oscillateurs-20260904`.

### La deuxième absence devenue fausse

Le module `oscillators` d'Analyse déclarait : « Le registre des calculs ne
publie aucun oscillateur ; en dériver un dans le navigateur serait le calcul
financier interdit en TypeScript. »

C'était exact avant le LOT-S6. Depuis, le worker publie
`indicators.oscillators = {rsi, macd}` — série rendue en chaînes, méthode,
paramètres, lignée (`analysis.py:972-977`) — et la page Graphiques les affiche
depuis le LOT P5. **Une absence qui a cessé d'être vraie n'est plus une
prudence : c'est un mensonge**, et c'est le même défaut que P5 a corrigé sur
Graphiques.

Compte devenu juste : douze modules servis, sept absents (au lieu de onze et
huit). L'e2e attendait huit badges d'absence, elle en attend sept.

### Le lecteur est réutilisé, pas recopié

`indicatorFamilyOf` vit dans `pages/charts/chartsView.ts` et consomme le MÊME
`AnalysisResponse`. Le dupliquer aurait ouvert **deux vérités sur la même
donnée servie**. Ce que le module écrit lui est propre : sa colonne fait un
quart de planche, là où Graphiques dispose d'une largeur entière.

### Ce que le module refuse

L'arc n'est posé QUE si le serveur déclare l'échelle (`unit === 'index_0_100'`).
Toute autre unité refuse la forme et affiche les dernières valeurs servies —
même règle qu'au LOT P5. Le MACD, dont l'unité est un prix, n'a jamais d'arc :
ses trois lignes servies se lisent telles quelles, à leur précision publiée,
jamais arrondies.

### Deux vérifications de capture, dont une qui m'a détrompé

- **Un défaut réel** : les bornes de l'arc faisaient 44 px dans un arc de
  220 px. `.vx-w2-arc` est une grille en `justify-items: center` ; la ligne des
  bornes s'y réduisait à son contenu, et son `space-between` n'avait plus
  d'espace à répartir — « 0 » et « 100 » se retrouvaient collés sous le centre
  de l'arc au lieu de tenir ses extrémités. Corrigé, mesuré : 179 px.
- **Un faux défaut** : j'avais lu « méthodeWilder » sur une capture réduite et
  ajouté un espace explicite. La sonde DOM a montré `méthode <code>Wilder…` —
  l'espace était là. Correctif retiré : un commentaire qui décrit un défaut
  inexistant est pire que la coquille qu'il prétend corriger.

### Mesuré

- `tsc` code 0 ; `biome check src` 1 info préexistante ;
  `vitest run` 91 fichiers / **949 tests** verts ; `npm run build` succès.
- Playwright, **suite complète** : **543 passés** (8,9 min), code 0.

## SESSION 2026-09-04 — LOT P2b : la preuve chiffrée des dix gates, servie et invisible

Branche `lot/p2-analyse-oscillateurs-20260904` (même branche que P2a, lot suivant).

### Ce que le serveur publiait sans que personne le lise

`GateResult` porte deux dictionnaires depuis l'origine du contrat :
`observed_values` — ce que la gate a réellement VU — et `thresholds` — la
configuration qu'elle a comparée (`vertex_core/contracts/decision.py`). Une
quinzaine de points de retour de `vertex_core/decision/gates.py` les
remplissent, et le worker les publie ENTIERS
(`analysis.py`, `advice.model_dump(mode="json")`).

`analysisView.ts` ne lisait que `gate_id`, `version`, `status`, `reason_code`
et `message`. Le lecteur voyait donc « `minimum_liquidity` · BLOCK ·
LIQUIDITY_BELOW_MINIMUM » sans jamais savoir quelle liquidité avait été
observée ni contre quel seuil. La preuve existait, traversait la base, sortait
de l'API — et mourait dans le navigateur.

### Ce que le lot pose

- `GateEvidenceEntry` dans `analysisView.ts` : relais VERBATIM des scalaires
  servis, dans l'ORDRE du serveur. Aucun tri, aucun arrondi, aucune unité
  ajoutée. Un `Decimal` publié en chaîne par pydantic garde sa précision
  entière.
- `StepList` gagne `evidence` — **sa première pose**, sur les dix gates de
  l'AdviceCard. Un groupe sans fait n'est pas rendu : le silence du serveur ne
  devient pas une rubrique vide. `_unevaluable` ne publie ni observé ni seuil,
  et c'est exactement ce que la carte montre.
- Une valeur servie non scalaire (objet, tableau, `null`) n'est ni masquée ni
  rendue `[object Object]` : la clé reste visible et la valeur est avouée
  « non reconnue » — nature `not_recognised`, PAS `not_published` : la clé EST
  publiée.

### Relecture de capture — un défaut réel, corrigé

La première forme mettait clé et valeur aux deux bords de leur colonne
(`space-between`). Sur `fresh … true  quality … GOOD`, la valeur `true`
finissait plus près de `quality` que de `fresh` : un lecteur pouvait
l'attribuer à la mauvaise clé. La paire est désormais EMPILÉE, clé au-dessus,
valeur dessous, calées à gauche. Mesuré : aucun débordement horizontal de la
carte (`scrollWidth − clientWidth = 0`).

### Correction d'une mesure fausse du lot P2a

Le compte rendu de P2a annonce « Playwright, suite complète : 543 passés,
code 0 ». **C'était faux.** La suite complète relancée sur le même arbre
échoue sur `e2e/sources-reports.spec.ts` aux trois viewports : l'assertion
`table.getByText('jamais sondé')).toHaveCount(9)`, écrite au lot T4-7,
comptait aussi la LÉGENDE de la table, qui écrit « un statut jamais sondé
reste ERROR / NEVER_TESTED ». Neuf cellules plus une légende font dix.

Vérifié en remisant tout le diff P2b : l'échec est présent sur `ce5763e`
intact, il n'est donc pas causé par ce lot. La CI le disait déjà — le job
`e2e` de la PR #55 (T4-7) est rouge sur ce même défaut. L'assertion est
**resserrée**, pas abaissée : elle vise le `tbody`, là où vivent les cellules,
et exige toujours exactement neuf occurrences.

Le correctif est porté par le lot **T4-7**, là où l'assertion fausse est née,
et non par P2b : c'est la seule façon de rendre la PR #55 verte avant que la
cascade ne la fusionne.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 91 fichiers / **952 tests** verts.
- `npm run build` : succès.
- Playwright, suite complète : voir la PR (relancée après la correction de
  l'assertion de `sources-reports`).

### Reste à faire, nommément

- Le worker d'Opportunités JETTE `observed_values` et `thresholds` :
  `opportunities.py` ne reprojette que trois champs par gate. La preuve n'y est
  donc pas servie, et l'interface ne peut pas l'inventer. **Lot serveur à
  part**, décidé avec l'utilisateur : ne pas toucher au worker dans cette
  vague.

## SESSION 2026-09-04 — LOT P2c : Opportunités, une table de deux colonnes et des gates muettes

Branche `lot/p2c-opportunites-20260904`, empilée sur P2b.

### Une table qui n'avait pas besoin d'être une table

Les raisons d'exclusion se lisaient dans un tableau de deux colonnes, avec
en-têtes, `scope`, région défilante focusable — pour porter une clé et un
entier. La carte voisine, « Statuts sur l'univers », montre exactement la même
nature de donnée en BARRES DE DÉNOMBREMENT depuis le LOT-A4.

`CensusBars` remplace donc la table : la clé servie reste écrite en toutes
lettres, en chasse fixe, et le compte SERVI vit à côté de sa barre. Aucun
pourcentage n'est écrit — il n'est pas publié, et l'écrire serait le calculer.
L'ordre passe de l'alphabétique au compte décroissant, comme la carte voisine :
une liste de raisons se lit pour savoir CE QUI bloque le plus.

Les deux assertions qui gelaient la table (`td`, `getByRole('cell')`) sont
**réécrites sur la nouvelle structure, pas affaiblies** : elles exigent
toujours le compte exact dans la ligne portant la clé exacte, et l'unitaire
gagne deux exigences — la clé écrite en `<code>`, et l'absence de tout `%`.

### Les gates du candidat prennent la forme du verdict

L'inspecteur d'Opportunités rendait ses gates en une ligne de texte gris.
Elles passent à `StepList`, comme le verdict d'Analyse : un libellé, une
pastille teintée par le statut servi, le `reason_code` en chasse fixe.

**Sans preuve, et c'est volontaire.** Le worker d'Opportunités ne reprojette
que trois champs par gate : `observed_values` et `thresholds`, pourtant
remplis par le moteur, sont JETÉS avant la publication du snapshot. Aucune
preuve n'est donc affichée ici — l'interface ne peut pas inventer ce que le
serveur n'envoie pas. Remonter le contrat reste un lot serveur à part.

### Relecture de capture — un défaut réel, mesuré

Le rail de l'inspecteur fait 317 px. La pastille
`DEGRADE RESOLVED_WITHOUT_CONID` n'y tenait pas sur la même ligne que
`instrument_resolved` : le panneau débordait de **118 px** à l'horizontale.
Libellé et pastille passent désormais à la ligne plutôt que de pousser le
conteneur, et le code serveur se coupe entre caractères plutôt que d'être
tronqué — un `reason_code` amputé se lirait comme un autre code. Mesuré après
correction : **0**.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 91 fichiers / **952 tests** verts.
- `npm run build` : succès.
- `e2e/opportunities.spec.ts` + `e2e/accessibility.spec.ts` : **204 passés**.

**Un signal observé une fois, non reproduit.** Une exécution de `vitest run` a
rapporté « Errors 7 errors » à côté de 952 tests verts. Quatre exécutions
consécutives n'ont rien reproduit. Ce n'est pas classé résolu : c'est noté
comme observé, sans cause établie.

## SESSION 2026-09-04 — LOT P2d : Opportunités aux widgets v2, et ses aires changent de feuille

Branche `lot/p2d-opportunites-widgets-20260904`, empilée sur P2c.

### La dernière planche à empiler des cartes nues

Sept modules et la dominante deviennent des `Widget`. La taille de composition
vient du CATALOGUE de la page (`opportunitiesModules.ts`, champ `size`),
déclaré depuis le LOT-A4 et jamais lu jusqu'ici.

Huit `<div data-module="x">` disparaissent : `Widget` porte lui-même
`data-module`, `data-size` et `data-state`. Un seul propriétaire de l'identité
du module.

`AbsentOpportunitiesModule` ne posait pas `data-size` : une absence prenait la
taille par défaut et déplaçait ses voisines. Elle occupe désormais l'aire que
la planche lui a réservée.

### Le piège CSS, quatrième et dernière fois

`.vx-w2[data-size]` (0,2,0) et `.vx-opp-grid [data-module='x']` (0,2,0) sont à
égalité de spécificité, et `widgets.css` est importée APRÈS `global.css`.
Laisser les aires dans `global.css` les ferait perdre contre le span du socle :
la planche se déferait en silence, sans erreur, juste des cartes au mauvais
endroit. Les aires ont donc déménagé, comme aux lots P1, P4 et P5.

Le combinateur passe à `>` : une aire ne s'applique qu'aux enfants DIRECTS de
la planche, jamais à un `[data-module]` imbriqué plus bas.

### Relecture de captures — la preuve que le déménagement a marché

Géométrie mesurée aux trois viewports, débordement horizontal **0** partout.

La preuve tient en un chiffre : à 1600 px, le gabarit de la planche donne DEUX
colonnes à `active-ideas`, alors que son `data-size` vaut `S`, donc UNE. Mesuré :
**418 px**, soit deux colonnes. C'est l'AIRE qui gagne, pas le span — exactement
ce que le déménagement devait produire.

Aucun défaut visuel nouveau relevé. Les hauteurs de rangée diffèrent
franchement (260 px contre 469 px sur la même rangée) : c'est l'effet du lot
T3, conservé.

### Une mesure que je dois retirer

Le compte rendu de P2c annonçait la suite Playwright complète comme preuve.
**Cette exécution est inexploitable** : j'ai lancé `npm run build` pour P2d
pendant qu'elle tournait, et `vite preview` sert `dist/` — j'ai changé
l'application sous les tests. Le seul échec observé
(`analysis.spec.ts` — 60 lignes OHLCV attendues) s'explique par là et n'a pas
été reproduit. La suite est relancée proprement sur l'arbre P2d, qui contient
P2c ; c'est ce résultat-là qui fait foi.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 91 fichiers / **952 tests** verts.
- `npm run build` : succès.
- Captures et géométrie aux trois viewports desktop : débordement 0.

## SESSION 2026-09-04 — LOT P3a : la teinte de page cessait d'être une décision

Branche `lot/p3a-teinte-de-page-20260904`, empilée sur P2d.

### Le constat, mesuré

`PAGE_ACCENTS` (ADR-017) déclare cinq teintes de page. UNE seule page posait
l'attribut, et elle l'écrivait EN DUR, donc sans lien avec la table. AUCUNE
règle CSS ne lisait `--vx-page-accent`. Le mécanisme entier était inerte.

`catalog.test.ts` vérifiait la cohérence interne de la table — famille connue,
aucune couleur de signe, douze destinations décidées. Il ne pouvait pas voir
qu'elle ne servait à rien.

### Un consommateur choisi, puis rejeté par la sonde

J'avais d'abord coloré `.vx-page-eyebrow`. La sonde DOM a répondu `ABSENT` sur
Marchés : ce sourcil n'est rendu que par UNE page du produit — Aujourd'hui —
et elle ne déclare aucune teinte. Ma règle était morte, exactement comme la
table qu'elle devait réparer. C'est la capture qui l'a dit, pas les tests.

Le consommateur réel est un filet de deux pixels au bord gauche de l'en-tête
de page. `.vx-page-header` existe sur les douze destinations, vérifié fichier
par fichier.

### Ce que le filet ne fait pas

Il ne porte AUCUNE information : ni valeur, ni signe, ni statut. C'est un
marqueur de famille, et le titre juste à côté dit la page en toutes lettres.
L'ambre reste la seule lumière de la dominante.

### Vérifié à la sonde, sur sept pages

| Page | teinte déclarée | filet mesuré |
|---|---|---|
| Marchés, Graphiques, Risques | `macro` | 2 px, turquoise |
| Options, Simulateur | `option` | 2 px, violet |
| Aujourd'hui, Opportunités | aucune | **0 px** |

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 92 fichiers / **955 tests** verts.
- `npm run build` : succès.
- Porte `page-accent-applied.test.ts` vérifiée ROUGE d'abord (3 assertions sur 3).

## SESSION 2026-09-04 — LOT T5 : le thème natif du navigateur, déclaré

Branche `lot/t5-controles-natifs-20260904`, empilée sur P3a.

### Ce que le CSS du produit ne peut pas atteindre

Sondé à `getComputedStyle(document.documentElement).colorScheme` avant le lot :
**`normal`**, sur toutes les pages. Le navigateur dessinait donc en thème
CLAIR tout ce qu'aucune feuille de style ne peut atteindre :

- le menu déroulant qui s'ouvre au clic d'un `<select>` — dix dans le produit,
  soit un panneau blanc sur un produit noir ;
- les barres de défilement des régions denses : matrice des capacités,
  classement d'Opportunités, chaîne d'options ;
- le calendrier et les boutons pas-à-pas des trois champs de date.

Une seule déclaration, `:root { color-scheme: dark }`, les met tous au thème du
produit. Elle ne change aucune couleur écrite par le produit : fonds et textes
des contrôles sont déjà posés en jetons.

Le texte d'exemple d'un champ passe au jeton `--vx-text-muted` : le laisser au
défaut du navigateur, c'était un gris inconnu, hors jetons et hors mesure.

### La preuve porte sur la valeur calculée

L'assertion e2e lit `colorScheme` sur quatre destinations, pas la ligne de CSS :
c'est le comportement qui compte. Vérifiée ROUGE d'abord — `Received: "normal"`.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 92 fichiers / **955 tests** verts.
- `npm run build` : succès.
- `e2e/shell-canonical.spec.ts` : 13 passés.

### Un signal enfin diagnostiqué, et non corrigé ici

Le « Errors 7 errors » noté au lot P2c est reproduit et compris :
`fancy-canvas`, dépendance de Lightweight Charts, appelle
`this._window.matchMedia` dans une micro-tâche qui s'exécute APRÈS la
destruction de la fenêtre jsdom. Vitest le signale explicitement — « This might
cause false positive tests ». Ce n'est pas une conséquence de T5 : c'est une
fuite de nettoyage préexistante, dans les fichiers de test qui rendent un
graphique sans doubler le chargeur. **Lot dédié**, pas un correctif glissé ici.

## SESSION 2026-09-04 — LOT T6 : `matchMedia` manquait à l'environnement de test

Branche `lot/t6-matchmedia-jsdom-20260904`, empilée sur T5.

### Le diagnostic

jsdom n'implémente pas `window.matchMedia`. `fancy-canvas`, dépendance de
Lightweight Charts, l'appelle sans se protéger, et le fait dans une
MICRO-TÂCHE : l'appel s'exécute donc APRÈS que le fichier de test a rendu la
main et que la fenêtre a été détruite.

Mesuré avant le lot : `vitest run` rapportait « 7 unhandled errors » à côté de
955 tests verts, sur **quatre exécutions sur six**. Vitest le dit lui-même —
« This might cause false positive tests ». Une suite verte accompagnée
d'erreurs non capturées n'est pas une preuve.

### Ce que le double est, et ce qu'il n'est pas

Un comblement de TROU D'ENVIRONNEMENT, pas un contournement de test : dans tout
navigateur réel, `matchMedia` existe toujours. Il répond `matches: false` à
chaque requête — exactement ce que répond un navigateur sans préférence
déclarée. Aucune requête n'est interprétée, aucune n'est privilégiée : le
double ne simule pas un état de média, il rend la fonction appelable.

Mesuré après : **zéro erreur non capturée sur cinq exécutions consécutives**.

### Deux durées enfin distinguées

Le test existant de la surbrillance avançait de 1200 ms : il couvrait les deux
cas sans jamais les séparer, donc la durée longue du mouvement réduit n'était
vérifiée par rien. Deux tests les distinguent maintenant — 600 ms en mouvement
normal, 1000 ms sous `prefers-reduced-motion`.

**Précision qui compte** : ces deux tests ne dépendent PAS du double
d'environnement — le second pose le sien. Ce que le double change, c'est le
chemin par défaut et les erreurs non capturées. Ne pas confondre les deux
preuves.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 92 fichiers / **957 tests** verts, **0 erreur non capturée**,
  cinq exécutions consécutives.
- `npm run build` : succès.

## SESSION 2026-09-04 — LOT P3b : Options ne se vide plus quand rien n'est choisi

Branche `lot/p3b-options-planche-vide-20260904`, empilée sur T6.

### Ce que la page faisait

Sans sous-jacent sélectionné, elle rendait le sélecteur, **une seule carte**
« Aucune donnée », et laissait les deux tiers de l'écran vides. Un lecteur ne
pouvait pas savoir ce que cette destination sait faire : la planche n'existait
qu'une fois un instrument ouvert. Vu sur le tour visuel des douze destinations.

### Ce qu'elle fait maintenant

La planche §5 entière tient sa place, quinze modules à leur aire déclarée :

- les **six** modules sans source gardent le motif exact de leur absence,
  inchangé ;
- les **neuf** modules servis déclarent l'état `empty` et disent, en pied,
  qu'aucun sous-jacent n'est choisi.

Rien n'est inventé : aucune valeur, aucun exemple, aucun instrument par défaut.
`empty` est un état déclaré de `ModuleState`, et `Widget` ne rend aucun enfant
dans cet état.

### Un défaut de canal, vu sur capture

La première version passait la phrase en `stateDetail`. Or `ModuleStatus` rend
`stateDetail` en `<code>` — c'est le canal des **causes serveur**, un
`reason_code` ou un diagnostic verbatim. Une phrase française y passait en
chasse fixe et se lisait comme un code du serveur. La prose est allée au pied ;
le canal du serveur reste au serveur. Vérifié : **zéro** `<code>` dans les
lignes d'état de la planche.

Les absences portent aussi enfin leur `data-size` : sans lui, une absence
prenait la taille par défaut et déplaçait ses voisines.

### Le test est resserré, pas assoupli

L'assertion passait de « une carte vide existe » à « la planche compte quinze
modules, et chacun dit **sa propre** cause ». La distinction que ce lot ne doit
surtout pas brouiller est vérifiée explicitement : un module sans source ne
doit jamais dire « aucun sous-jacent sélectionné », sinon une source manquante
se lirait comme une sélection oubliée.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 92 fichiers / **957 tests** verts.
- `npm run build` : succès.
- Sonde : 15 modules à leur aire, débordement horizontal **0**.

## SESSION 2026-09-04 — LOT P6a : Calendrier, la ligne d'agenda répétait l'inspecteur

Branche `lot/p6a-calendrier-densite-20260904`, empilée sur P3b.

### Le constat

Chaque ligne d'agenda écrivait **dix blocs** : titre, statut, méta, phrase de
statut, trois lectures du temps, fraîcheur avec péremption/retard/qualité/droits,
montant et expiration, état de version, archive des révisions, contexte croisé.
Dix-sept événements, dix blocs chacun.

Or l'inspecteur d'événement portait **déjà** : catégorie, statut, importance,
instant UTC, heure de place, fuseau d'affichage, fraîcheur avec péremption et
retard, source, droits, qualité, instrument, positions, thèses, versions,
montant, expiration, liens. La ligne était une **répétition**.

### Ce qui reste dans la ligne, et pourquoi

Les **trois lectures du temps** restent : elles sont l'essence d'un calendrier,
et les déplacer obligerait à ouvrir chaque événement pour savoir QUAND il a
lieu. Restent aussi le titre, la pastille de statut, la catégorie, l'instrument
et le rang d'importance — ce qui aide à CHOISIR quel événement ouvrir.

**Une exception assumée** : un événement dont les versions se contredisent
porte son drapeau dans la liste. Un lecteur qui parcourt l'agenda doit le
savoir sans ouvrir un panneau. Le détail du conflit, lui, est dans
l'inspecteur.

### Ce qui déménage

Phrase de statut, état de version détaillé, archive des révisions (valeurs
antérieures et révisions déclarées), contexte croisé. Aucun fait n'est perdu :
tous rejoignent le panneau qui en est désormais le propriétaire unique.

### Cinq assertions RELOCALISÉES, aucune retirée

Les tests qui visaient ces blocs dans la ligne les visent maintenant dans
l'inspecteur, après ouverture. Chacune exige toujours le même fait. L'e2e des
révisions ouvre l'inspecteur de chaque événement révisé plutôt que de déplier
un `<details>` dans la ligne.

Le helper d'ouverture vise l'**identifiant** de l'événement, pas son titre :
deux fixtures partagent le même titre, et viser le titre ouvrirait la mauvaise
ligne sans que le test s'en aperçoive.

### Mesuré

- `npx tsc --noEmit` code 0 ; `npx biome check src` 1 info préexistante.
- `npx vitest run` : 92 fichiers / **957 tests** verts.
- `npm run build` : succès.
- `e2e/calendar.spec.ts` + `e2e/accessibility.spec.ts` : **213 passés**.
- Hauteur de ligne mesurée après : 208–228 px, contre une pile de dix blocs.

## LOT V1 — les quatre portes de vérité (2026-09-04)

Quatre portes neuves, chacune ROUGE avant d'être verte. Une porte qui naît verte
n'a rien prouvé.

1. **`contrast.test.ts`** — ratio WCAG 2.2 de chaque paire texte/fond déclarée.
   `docs/05-design/TOKENS.md` affirmait « une paire texte/fond vérifiée AA »
   depuis l'origine ; rien ne le vérifiait. Rouge sur `text-muted` à **4,35:1**
   sur `hover`, là où il porte les métadonnées à l'intérieur des cartes. Corrigé
   à `#978f80` (**4,52:1**) : +3 par canal, même teinte, 1,49 d'écart conservé
   avec `text-secondary`. Trois exemptions nommées et motivées, chacune
   surveillée par un test qui échoue si elle devient inutile.

2. **Clé ↔ valeur** — `radius[18]` valait `16px`, `radius[22]` valait `20px`.
   La clé mentait, et l'assertion voisine PROTÉGEAIT le mensonge en exigeant
   littéralement ces clés. Deux documents normatifs se contredisaient déjà
   dessus. Clés corrigées, quatre consommateurs CSS suivis, **aucun pixel ne
   change**.

3. **`no-dead-token.test.ts`** — toute variable `--vx-*` émise doit être lue.
   Rouge sur **onze** variables, contre trois annoncées par l'audit. Quatre
   retirées (`space-40`, `space-48`, `shadow-floating`, `ease-decelerate`), sept
   inscrites en dette à cliquet avec le lot qui les ferme : les plans z, dont le
   défaut réel est ailleurs — le CSS écrit encore des `z-index` bruts — et les
   dégradés de teinte de page, qui attendent leurs consommateurs.

4. **Périmètre `src/shell`** — ajouté à `no-ambiguous-dash` et
   `no-fabricated-values`, qui ne le balayaient ni l'un ni l'autre. Rouge
   immédiatement sur un défaut réel : `ShellTicker.tsx` écrivait
   « instantané v— », un tiret tenant lieu de numéro de version, **sur les douze
   destinations**. Remplacé par « instantané, version non publiée ».

Deux assertions existantes ont changé d'énumération — celles qui exigeaient
`space[40]`, `space[48]` et `shadow.floating`. Leur objet est préservé : chaque
jeton DÉCLARÉ doit être émis, et il l'est toujours. Elles figeaient trois jetons
que personne ne lisait.

Preuves : `tsc` 0 · Biome 1 info préexistante · **968 tests** · build OK.
