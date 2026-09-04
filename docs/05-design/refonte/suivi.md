# Dossier de refonte — Suivi

> Produit par l'audit-conception du 2026-09-04 : un auditeur a lu le code et les
> contrats, un concepteur a dessiné la page cible, puis **deux lentilles
> adversariales** ont tenté de la réfuter. Les réfutations sont reportées ici
> telles quelles : **ce dossier est une conception à corriger, pas une
> spécification approuvée.** Le lot qui l'implémente applique d'abord le §4.

## 1. Ce que l'audit a mesuré

L'espace Suivi est le plus HONNÊTE des douze sur ses absences et le plus GASPILLEUR sur ses présences. Le catalogue de 17 modules (11 servis, 6 absents à motif fermé) est réel, testé, et la règle « une seule dominante » tient — la chronologie est la seule Card rank=\"dominant\". Mais l'audit champ par champ montre que les deux contrats servis publient beaucoup plus que ce que la page lit : environ 40 champs publiés et jamais affichés. Les six plus rentables, par ordre de valeur : (1) le bloc coverage de l'agenda — events_superseded, events_stale, events_conflicting, revisions_rejected, rejected_reasons, window_truncated — publié entier et ignoré, alors que la carte « Conflits » recompte deux de ces chiffres côté client ; (2) importance.rank + importance_rule.ranks[].description, qui transformeraient le code brut « EARNINGS_POSITION_OR_THESIS » en un rang ordonnable et une phrase publiée ; (3) revisions[].reason, rejected_revisions[].reason et previous_values[], qui donneraient un vrai historique là où l'inspecteur n'affiche aujourd'hui que des dates ; (4) conflict_election_rule, publié sur chaque événement par le worker et parsé NULLE PART dans tout le dépôt web ; (5) age_seconds + freshness_policy sur LES DEUX endpoints — le relais mesure l'âge, l'écrit dans sa docstring comme un défaut corrigé, et l'interface ne l'affiche pas : une file de trois jours se lit comme une file d'une minute ; (6) le bloc coverage de la file de revue — theses_with_instrument, observations_considered, clusters, lookback_seconds — validé fail-closed par l'API et jamais même parsé.\n\nDeux défauts sont bloquants, pas cosmétiques. D'abord un FAUX POSITIF DE COUVERTURE : quand la file de revue ne répond pas, CatalystsPage.tsx:295 substitue un tableau vide et la carte « Thèses sans catalyseur servi » affirme « Chaque thèse déclarée est touchée par au moins un événement servi ». Une source absente devient une affirmation positive — c'est exactement la loi 4. Ensuite un ENDPOINT FANTÔME : catalystsModules.ts:35 déclare GET /api/v1/review-queue, qui n'existe pas (la vraie route est /follow-up/queue), et le test censé le prévenir ne vérifie qu'un préfixe.\n\nCôté forme, la page n'est pas encore Titan Ledger. Il n'y a aucun moteur graphique — seulement trois CensusBars en HTML/CSS —, la « chronologie » n'a ni axe ni échelle temporelle, les trois axes sémantiques de badge (catégorie, statut, lien) rendent tous la même pastille grise faute de règle CSS, les horodatages sont des ISO-8601 bruts dans une interface française, un module tronque silencieusement à six lignes, la seule table n'a pas de caption, la fiche thèse est un role=\"dialog\" sans panneau qui concurrence l'inspecteur du shell, et six modules absents ont un aria-labelledby cassé par les espaces de leur propre titre. S'y ajoutent quatre morts CSS mesurées : .vx-cat-orphans-note, counter-reset: vx-cat, .vx-cat-exposure-list et .vx-cat-timeline-card sans règle, .vx-sheet-head h3 qui ne cible pas le h2 réel.

### 1.1 Champs servis et jamais affichés — 42 relevés

La matière gratuite : déjà calculée par Python, publiée par le contrat, et
jetée par l'interface.

- FollowUpQueueResponse.age_seconds — publié dans TOUS les états datables (apps/api/src/vertex_api/follow_up.py, docstring explicite « son absence faisait passer une file de trois jours pour une file d'une minute »). Jamais lu : ni ReviewQueueSection.tsx, ni followUpView.ts, ni CatalystsPage.tsx. L'âge de la file de revue est donc invisible sur cet espace.
- FollowUpQueueResponse.freshness_policy {budget_seconds, kind, version} — propriété de route servie même sans instantané. Jamais lue par apps/web/src/pages/catalysts/review/ReviewQueueSection.tsx.
- FollowUpQueueResponse.snapshot_version — servi. WindowModule (CatalystsModules.tsx:327) n'affiche QUE la version du snapshot d'agenda ; la version du snapshot de thèses n'apparaît nulle part alors que la carte s'intitule « Deux snapshots ».
- content.ordering.method (= "lexicographic", worker follow_up.py:build_review_queue_content) — jamais parsé par followUpView.ts::queueContentOf.
- content.ordering.note (« new information raises visible urgency… but never rewrites the thesis ») — parsé en orderingNote (followUpView.ts:224) et JAMAIS affiché ; ReviewQueueSection.tsx:151 n'affiche que orderingKeys.
- content.coverage.theses_total — parsé en thesesTotal (followUpView.ts:231), jamais lu par un composant ; ReviewQueueSection.tsx:212 affiche à la place frame.view.theses.length.
- content.coverage.due_count — parsé en dueCount (followUpView.ts:232), jamais lu ; ReviewQueueSection.tsx:148 affiche frame.view.due.length.
- content.coverage.theses_with_new_information — parsé en thesesWithNewInformation (followUpView.ts:233), jamais lu par aucun composant.
- content.coverage.theses_with_instrument — publié et VALIDÉ fail-closed par l'API (_QUEUE_COVERAGE_COUNTS, follow_up.py). Jamais parsé par followUpView.ts.
- content.coverage.observations_considered — idem, jamais parsé par followUpView.ts.
- content.coverage.content_observations — idem, jamais parsé par followUpView.ts.
- content.coverage.clusters — idem, jamais parsé par followUpView.ts.
- content.coverage.lookback_seconds — idem, jamais parsé par followUpView.ts (la fenêtre d'observation qui a produit le contexte d'information est donc invisible).
- content.coverage.content_schema_prefixes — publié par le worker (follow_up.py), jamais parsé par followUpView.ts.
- content.theses[].thesis.portfolio_id — publié par le worker, jamais parsé par followUpView.ts::thesisEntryOf.
- content.theses[].thesis.instrument (objet canonique complet) — publié, jamais parsé ; followUpView.ts ne lit que le raccourci entry.instrument_ticker.
- content.theses[].thesis.review_due_at (échéance de BASE) — parsé en baseReviewDueAt (followUpView.ts:167) et JAMAIS affiché. ThesisSheet.tsx:248 ne montre que l'échéance effective : le lecteur ne voit jamais l'écart entre échéance de base et échéance reportée.
- content.theses[].information_context.clusters[].tickers — publié par le worker (follow_up.py, _cluster_context), jamais parsé par followUpView.ts::clusterOf.
- content.theses[].information_context.clusters[].provenance.member_event_ids — parsé en memberEventIds (followUpView.ts:140) et JAMAIS affiché par ThesisSheet.tsx:343-360.
- content.theses[].information_context.clusters[].provenance.first_published_at — parsé en firstPublishedAt (followUpView.ts:141) et JAMAIS affiché par ThesisSheet.tsx (seul lastReceivedAt est rendu).
- content.due[].last_recorded_at — parsé en DueEntryView.lastRecordedAt (followUpView.ts:202) et JAMAIS affiché par ReviewQueueSection.tsx, alors que c'est la 3e clé de tri documentée de la file.
- content.due[].urgency_reasons[].cluster_id / .last_received_at / .reference_instant — parsés, mais ReviewQueueSection.tsx:190 n'affiche que reason.code. Le détail n'existe que dans ThesisSheet, donc invisible dans la file elle-même.
- CalendarResponse.age_seconds — publié dans tous les états datés (calendar.py, docstring : « un agenda de vingt heures était indiscernable d'un agenda d'une minute »). Jamais lu par CatalystsPage.tsx ni CatalystsModules.tsx.
- CalendarResponse.freshness_policy — jamais lu par cet espace.
- CalendarResponse.importance_rule {version, ranks[{rank, code, description}]} — publié. Jamais lu par pages/catalysts : CatalystTimeline.tsx:200 affiche le code brut (« EARNINGS_POSITION_OR_THESIS ») sans jamais la description publiée qui l'explique. La fonction importanceRuleOf existe pourtant dans calendarView.ts:348 et n'est utilisée que par Calendrier.
- CalendarResponse.categories (compteurs de catégories du snapshot ENTIER) — publié. Jamais lu ; CategorySplitModule recompte localement avec censusOf (CatalystsModules.tsx:66).
- CalendarResponse.statuses (compteurs ESTIMATED/CONFIRMED du snapshot entier) — publié. Jamais lu nulle part sur cet espace : aucune répartition estimé/confirmé n'est montrée.
- CalendarResponse.coverage.observations_considered / events_displayed / events_superseded / events_stale / events_conflicting / revisions_rejected / rejected_revision_reasons / rejected_records / rejected_reasons / window_truncated / max_observations / lookback_seconds — bloc entier publié par le worker (calendar.py:1115) et JAMAIS lu par pages/catalysts. Le module « Conflits de version » recompte events_conflicting et revisions_rejected côté client au lieu de lire les comptes servis.
- CalendarResponse.window.applied — publié. Jamais lu : WindowModule (CatalystsModules.tsx:333) écrit « début non publié → fin non publiée » alors que la vérité servie est que la page N'A PAS DEMANDÉ de fenêtre (useCalendar(null)).
- CalendarResponse.window.max_days — publié (borne 90 jours). Jamais lu.
- CalendarResponse.window.categories / window.statuses (compteurs de ce qui est RÉELLEMENT affiché) — publiés. Jamais lus par pages/catalysts.
- agenda[].conflict_election_rule — publié par le worker sur CHAQUE événement (calendar.py:1063, nommé uniquement quand une valeur a réellement été élue entre versions contestées). N'est parsé NULLE PART dans apps/web/src : absent de calendarView.ts::calendarEventOf. Matière totalement invisible.
- agenda[].importance.rank — parsé par calendarView.ts::importanceOf, JAMAIS affiché par CatalystTimeline.tsx:200-207 qui ne montre que code et rule_version. Le rang est le seul élément ordonnable publié.
- agenda[].revisions[].reason — parsé en RevisionView.reason (calendarView.ts:220), JAMAIS affiché par CatalystInspector.tsx:118-146 qui rend revisedAt, previousStatus et previousEventTimeUtc seulement. La raison de la révision publiée par la source est perdue.
- agenda[].rejected_revisions[] (reason, revised_at, previous_status, previous_event_time_utc) — parsé en rejectedRevisions (calendarView.ts:309). Seule sa LONGUEUR est lue (CatalystsModules.tsx:360) ; aucune raison de refus n'est jamais montrée, ni dans la carte Conflits ni dans l'inspecteur.
- agenda[].previous_values[] (source_event_id, source, as_of, status, event_time_utc des enregistrements supplantés) — parsé en previousValues (calendarView.ts:308). AUCUNE occurrence dans /home/user/vertex-merge/apps/web/src/pages/catalysts. Calendrier l'affiche (EventAgenda.tsx:175), Suivi non.
- agenda[].conflicting_versions[] — seul .length est lu (CatalystTimeline.tsx:227 et CatalystInspector.tsx:151). Le contenu des versions contradictoires (source, as_of, statut, instant) est publié et jamais montré, alors que l'inspecteur affirme « le conflit est montré, pas arbitré ».
- agenda[].delay_status — parsé (calendarView.ts:314). Aucune occurrence dans pages/catalysts, alors que le catalogue catalystsModules.ts:169 DÉCLARE ce champ comme contrat servi du module « Sources et fraîcheur ». Contrat déclaré, champ jamais lu.
- agenda[].scope — parsé (calendarView.ts:303). Jamais lu dans pages/catalysts (Calendrier l'affiche, EventAgenda.tsx:398).
- agenda[].amount, agenda[].currency, agenda[].expiration — champs facultatifs relayés verbatim par le worker (calendar.py:669, clés extra). Parsés par calendarView.ts:333-336, jamais lus dans pages/catalysts : le montant d'un dividende et l'expiration d'options n'apparaissent nulle part sur la chronologie des catalyseurs.
- agenda[].version_state = 'RESOLVED' — publié sur chaque événement non conflictuel. Jamais nommé : le code ne teste que l'égalité avec CONFLICTING_VERSIONS (CatalystsModules.tsx:359, CatalystTimeline.tsx:222). Un événement résolu ne dit pas qu'il l'a été.
- agenda[].event_context.links[] — rendu UNIQUEMENT dans l'inspecteur (CatalystInspector.tsx:186), donc invisible tant qu'aucun catalyseur n'est ouvert ; les liens analysis/{ticker} et option_chain/{ticker} publiés par le worker ne sont jamais des liens cliquables (rendus en <code>, pas en <a>).

### 1.2 Défauts visibles dans le code — 25

- FAUX POSITIF DE COUVERTURE — le plus grave. CatalystsPage.tsx:288 calcule queueView=null quand la file de revue est en chargement, hors ligne ou en erreur, puis passe queueView?.theses ?? [] à selectCatalysts (CatalystsPage.tsx:295). thesesWithoutCatalyst vaut alors [] (tableau vide, pas null), et OrphanThesesModule reçoit un tableau vide avec l'état de l'AGENDA (ready) : CatalystsModules.tsx:392 affiche « Chaque thèse déclarée est touchée par au moins un événement servi. » Une source indisponible est donc présentée comme un fait positif de couverture. Même mécanisme sur UpcomingCountModule (« Thèses orphelines : 0 ») et sur CatalystTimeline.tsx:174 qui étiquette TOUTES les thèses « thèse absente du snapshot de revue » en accusant le snapshot au lieu de dire que la file n'a pas répondu. Aucun test ne couvre ce cas (ni CatalystsPage.test.tsx ni CatalystsComposition.test.tsx).
- PÉRIMÉ SILENCIEUX SUR LES MODULES CROISÉS. CatalystsPage.tsx:288 accepte queueQuery.data.state === 'stale' sans distinction (seul 'empty' est écarté). Les thèses orphelines, le compte d'orphelines et la population de thèses du WindowModule proviennent donc éventuellement d'un instantané périmé, alors que le bandeau « Données périmées » n'existe QUE dans la carte de revue (ReviewQueueSection.tsx:66). Deux modules affichent le même instantané avec deux vérités de fraîcheur différentes.
- ENDPOINT FANTÔME DANS LE CATALOGUE. catalystsModules.ts:35 déclare const QUEUE = 'GET /api/v1/review-queue — content'. Cette route N'EXISTE PAS : routes.py:1101 publie /follow-up/queue. Trois modules servis (upcoming-count, orphan-theses, review) citent donc un contrat inexistant. Le test censé l'empêcher, catalystsModules.test.ts:15 « chaque module servi nomme un contrat API existant », ne vérifie qu'un préfixe /^(GET|POST) \/api\/v1\// : son intitulé sur-revendique.
- CONTRAT DÉCLARÉ ≠ CHAMP LU. catalystsModules.ts:169 déclare le module sources-freshness servi par « source / fresh / delay_status ». delay_status n'est lu nulle part dans pages/catalysts (SourcesFreshnessModule ne compte que source et fresh). Le catalogue promet un champ que le composant ignore.
- TRONCATURE SILENCIEUSE. CatalystsModules.tsx:232 fixe EXPOSURE_LINES = 6 et CatalystsModules.tsx:257 rend exposed.slice(0, 6) sans afficher ni le total ni le fait qu'il y a troncature. Au-delà de six événements touchant une position déclarée, les suivants disparaissent sans mention. Le pied de carte ne dit rien. C'est le seul module de la planche à masquer des lignes servies.
- TEXTE FRANÇAIS DANS LE CANAL <code> (réservé au code serveur), 12 sites : CatalystTimeline.tsx:231-233 (source/droit/qualité « non publiée »), CatalystsModules.tsx:345-346 (populations), ReviewQueueSection.tsx:131-132, ThesisSheet.tsx:317 (cluster « non publié ») et ThesisSheet.tsx:340. Le lecteur ne peut plus distinguer une valeur machine servie d'une phrase d'absence écrite par l'interface, alors que c'est précisément ce que le canal monospace est censé garantir.
- ABSENCE MÉLANGÉE AUX VALEURS SERVIES DANS UN MÊME AXE. CatalystsModules.tsx:285 injecte la chaîne 'source non publiée' comme CLÉ de recensement, à côté des vraies sources ; CatalystsModules.tsx:293 fait de même avec 'fraîcheur non publiée'. Une absence devient une barre de la même nature graphique qu'une source réelle, dans le même classement décroissant.
- FENÊTRE PRÉSENTÉE COMME NON PUBLIÉE ALORS QU'ELLE N'A PAS ÉTÉ DEMANDÉE. CatalystsModules.tsx:333 écrit « début non publié → fin non publiée » parce que la page appelle useCalendar(null). Le champ window.applied (publié, faux ici) le dirait exactement. Le lecteur conclut à un défaut serveur là où il n'y a qu'une absence de requête.
- CHIFFRE D'INTERFACE PRÉSENTÉ COMME UNE DONNÉE. CatalystTimeline.tsx:245 affiche « Catégories couvertes par le libellé : {Object.keys(CATEGORY_LABELS).length} », c'est-à-dire la taille d'un dictionnaire de traduction codé en dur dans le navigateur, posée dans le pied de la carte dominante à côté de comptes réellement servis.
- TROIS AXES SÉMANTIQUES VISUELLEMENT IDENTIQUES. CatalystTimeline.tsx pose data-category (l.183), data-status (l.188) et data-link (l.164) sur des .vx-badge. Aucune règle CSS ne cible ces attributs sur .vx-badge : global.css ne colore que .vx-cal-category[data-category=…] et .vx-cal-status[data-status=…], classes de la page Calendrier. Sur Suivi, catégorie, statut et motif de lien rendent donc TOUS la même pastille grise ; les trois attributs de données sont morts.
- SÉLECTION PORTÉE PAR LA COULEUR SEULE (pour l'œil). global.css:3263 — .vx-cat-item[data-selected='true'] { border-color: var(--vx-signal-soft) } est le seul marqueur visuel de la ligne ouverte : pas d'épaisseur, pas de glyphe, pas de fond. aria-pressed couvre l'assistance technique, pas le lecteur voyant.
- aria-labelledby CASSÉ SUR LES SIX MODULES ABSENTS. AbsentModule.tsx construit id={`vx-absent-${reason}-${title}`} et aria-labelledby identique. Les six titres de cette page contiennent des espaces (« Impact moyen », « Confiance moyenne », « Surprises récentes », « Consensus fourni », « Historique des surprises », « Alertes d'événement »), donc aria-labelledby est lu comme une LISTE de deux références (« vx-absent-NO_SOURCE-Impact » et « moyen »), dont aucune n'existe : le nom accessible n'est pas calculé. S'y ajoute role="status" sur chacune des six sections, soit six régions live simultanées.
- HIÉRARCHIE DE TITRES INCOHÉRENTE DANS LA MÊME GRILLE. Card rend <h2> (Card.tsx:82) pour les 11 modules servis ; AbsentModule rend <h3> pour les 6 absents. Les 17 cellules sont visuellement au même rang mais portent deux niveaux de titre différents. ReviewQueueSection ajoute un <h2> « Revue des thèses » puis ThesisForm un second <h2> « Nouvelle thèse » IMBRIQUÉ à l'intérieur de la même section.
- TABLE SANS CAPTION. ReviewQueueSection.tsx:214 — <table className="vx-fu-theses-table" aria-label="Thèses déclarées et état projeté"> : aucun <caption>. C'est la seule table de l'espace et la seule surface financière dense de la page.
- FICHE THÈSE : DIALOGUE MODAL SANS PANNEAU. ThesisSheet.tsx:193 déclare role="dialog" aria-modal="true" mais global.css:1554 ne donne à .vx-sheet que { display: block } — aucune position, aucun fond, aucune élévation, aucun backdrop. Le « panneau » se rend en flux, au bas de la carte de revue, tout en rendant l'ensemble de la page invisible aux lecteurs d'écran (aria-modal). C'est en outre le SEUL des dix .vx-sheet du dépôt à ne pas être monté dans l'emplacement d'inspecteur du shell : la page peut donc afficher simultanément l'inspecteur de catalyseur (à droite, via InspectorPanel) et la fiche de thèse (en bas, en flux) — deux surfaces de détail concurrentes, contre une action principale par page.
- RÈGLE CSS MORTE : global.css:1568 .vx-sheet-head h3 { font-size: display; font-weight: 650 } ne s'applique jamais à ThesisSheet, dont le titre est un <h2> (ThesisSheet.tsx:202). Les neuf autres sheets utilisent un h3 en .vx-visually-hidden — ThesisSheet est le seul à afficher son titre, et sans le style prévu.
- RÈGLE CSS MORTE : global.css:3274 .vx-cat-orphans-note — cette classe n'apparaît dans aucun .tsx du dépôt.
- DÉCLARATION CSS MORTE : global.css:3284 .vx-cat-list { counter-reset: vx-cat } — aucun counter-increment ni content: counter(vx-cat) n'existe dans global.css. Le compteur est réinitialisé et jamais utilisé.
- CLASSE APPLIQUÉE SANS AUCUNE RÈGLE : .vx-cat-exposure-list (CatalystsModules.tsx:255) n'a aucune règle CSS — seule .vx-cat-exposure-line en a une (global.css:7986). La liste garde donc puces et retrait par défaut du navigateur à l'intérieur d'une carte de la planche.
- CLASSE APPLIQUÉE SANS AUCUNE RÈGLE : .vx-cat-timeline-card (CatalystsPage.tsx:113, passée en className de la Card dominante) n'a aucune règle CSS. Le crochet de composition de la dominante ne sert à rien.
- HORODATAGES MACHINE BRUTS DANS UNE INTERFACE FRANÇAISE. CatalystTimeline.tsx:87 rend l'ISO-8601 complet (« 2026-09-15T13:30:00+00:00 ») comme heure principale de la chronologie dominante, alors que le composant partagé AgendaLine (utilisé DANS la même page par PortfolioExposureModule) sait rendre readableEventTime. Même défaut sur WindowModule (as_of, from_utc, to_utc), ReviewQueueSection (échéances) et ThesisSheet (tous les instants).
- UNITÉ BRUTE NON CONVERTIE. ReviewQueueSection.tsx:181 — « en retard de {entry.overdueSeconds} s (au snapshot) » : overdue_seconds est servi en secondes et affiché tel quel (« en retard de 259200 s »). La valeur est servie, l'affichage est illisible.
- PROSE DUPLIQUÉE À L'IDENTIQUE SUR LA MÊME PAGE. La phrase « Populations séparées, jamais additionnées » apparaît deux fois, dans WindowModule (CatalystsModules.tsx:345) et dans ReviewQueueSection (l.130), avec des paires de populations DIFFÉRENTES (agenda/thèses d'un côté, thèses/contexte d'information de l'autre) : trois populations pour deux cartes qui se lisent pareil.
- DENSITÉ DE RÉGIONS LIVE. role="status" est posé sur SelectionAbsence (CatalystsModules.tsx:47 et 61), sur le compte de filtres (l.199), sur les deux vides d'exposition et d'orphelines, sur CensusBars vide, et sur les six AbsentModule : plus d'une douzaine de régions live simultanées sur une page de 17 modules.
- RISQUE DE DENSITÉ À 1280 px. À 1280 px, rail 136 px, planche à 4 colonnes (global.css:7889) : chaque colonne fait environ 235 px, moins 40 px de padding de carte. UpcomingCountModule y empile trois Metric (« Reliés », « Non reliés », « Thèses orphelines ») dans un .vx-metrics-row en flex-wrap : les trois mesures se replient en colonne et la carte S devient plus haute que ses voisines de la même rangée. Aucun test de composition ne mesure les trois largeurs cibles.

### 1.3 Graphiques actuels

- AUCUN moteur graphique n'est chargé sur cet espace. Vérifié : ni echarts ni lightweight-charts n'apparaissent dans /home/user/vertex-merge/apps/web/src/pages/catalysts (les deux chargeurs paresseux src/charts/echartsLoader.ts et src/charts/lightweightChartsLoader.ts ne sont consommés que par markets, simulator, portfolio/performance et analysis).
- CensusBars (src/components/CensusBars.tsx) — barres horizontales en HTML/CSS pur, largeur = part du plus grand compte (censusWidths), compte écrit à côté de la barre, piste en aria-hidden. TROIS instances sur la page : 1) category-split, répartition par catégorie ; 2) sources-freshness, répartition par source ; 3) sources-freshness, répartition par fraîcheur publiée. Aucun pourcentage n'est écrit (non publié). Aucune jauge circulaire, aucun anneau, conforme au canon.
- La « chronologie » (visuel dominant) n'est PAS un graphique : c'est une liste ordonnée (ol.vx-cat-list) de cartes-événements dans une région défilante bornée à 560 px. Il n'y a aucun axe de temps, aucune échelle, aucune densité temporelle — le mot « timeline » est un nom de composant, pas une représentation temporelle.

### 1.4 Fichiers lus

- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystsPage.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystsModules.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystTimeline.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystInspector.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/catalystsModules.ts`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/catalystsView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/catalystsModules.test.ts`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystsPage.test.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystsComposition.test.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/review/ReviewQueueSection.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/review/ReviewQueueSection.test.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/review/ThesisSheet.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/review/ThesisForm.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/catalysts/review/followUpView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/calendar/calendarView.ts`
- `/home/user/vertex-merge/apps/web/src/components/Card.tsx`
- `/home/user/vertex-merge/apps/web/src/components/Metric.tsx`
- `/home/user/vertex-merge/apps/web/src/components/CensusBars.tsx`
- `/home/user/vertex-merge/apps/web/src/components/AbsentModule.tsx`
- `/home/user/vertex-merge/apps/web/src/components/calendar/AgendaLine.tsx`
- `/home/user/vertex-merge/apps/web/src/shell/inspector.tsx`
- `/home/user/vertex-merge/apps/web/src/api/decisionApi.ts`
- `/home/user/vertex-merge/apps/web/src/api/portfolioApi.ts`
- `/home/user/vertex-merge/apps/web/src/api/hooks.ts`
- `/home/user/vertex-merge/apps/web/src/styles/global.css`
- `/home/user/vertex-merge/apps/web/src/design/one-dominant-per-page.test.ts`
- `/home/user/vertex-merge/apps/web/src/design/no-ambiguous-dash.test.ts`
- `/home/user/vertex-merge/apps/api/src/vertex_api/routes.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/follow_up.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py`
- `/home/user/vertex-merge/apps/worker/src/vertex_worker/follow_up.py`
- `/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py`
- `/home/user/vertex-merge/docs/01-product/pages/09-follow-up.md`
- `/home/user/vertex-merge/docs/01-product/ROUTES.md`
- `/home/user/vertex-merge/docs/05-design/PAGE_ARBITRATION.md`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/types.py`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/enums.py`

## 2. Question, point focal, accent

- **Question** : Qu'est-ce qui a changé sous mes thèses déclarées depuis leur dernière revue ?
- **Visuel dominant** : `thesis-lanes` — « Couloirs de thèses » : un couloir horizontal par thèse déclarée servie, sur un VRAI axe de temps servi, une marque par événement relié, un repère vertical pour `as_of` et deux losanges par couloir pour l'échéance de base et l'échéance effective. Unique `data-rank="dominant"` de la page, unique graphique à moteur (ECharts 6.1.0, chargé paresseusement).
- **Accent** : ambre (`--vx-signal`) — accent de page unique. Violet réservé aux événements de catégorie option, rouge aux versions contestées et révisions refusées, cyan inutilisé sur cette page, vert réservé à une revue enregistrée servie. Une lumière dominante par carte, deux par écran hors rouge/vert.

## 3. Conception proposée

# Suivi — fiche de page

> Route `/catalysts` (inchangée). Titre à l'écran : **Suivi**. `/follow-up` redirige en permanence.
> Planche §10. Accent de page : **ambre**. Desktop uniquement : 1280×800, 1440×900, 1600×1000.

---

## 1. Question de la page

**« Qu'est-ce qui a changé sous mes thèses déclarées depuis leur dernière revue ? »**

Une seule question. Elle absorbe les deux questions concurrentes d'aujourd'hui — celle de la page
(« Quels événements vérifiés peuvent modifier la thèse et quand ? ») et celle du module de revue
(« Quelles thèses, alertes et informations doivent être revues ? ») — sans en perdre la matière :
les événements servis sont la **preuve** du changement, la file de revue est la **décision** qui en
découle.

Frontière avec Calendrier (§11), inchangée : Calendrier sert **tout** l'agenda dans une fenêtre et
son fuseau ; Suivi ne lit que la part reliée à une thèse déclarée ou à une position du registre
manuel. Un seul propriétaire de donnée, deux questions, jamais deux vérités.

## 2. Visuel dominant

`thesis-lanes` — **Couloirs de thèses**. Unique `data-rank="dominant"` de la page et **unique
graphique à moteur** (ECharts 6.1.0, chargé paresseusement par `src/charts/echartsLoader.ts`,
auquel il faut ajouter `ScatterChart`). Tous les autres visuels sont des recensements en barres
HTML/CSS (`CensusBars`) ou des pistes de géométrie (`AgeMeter`).

Un couloir horizontal par thèse déclarée servie, dans l'**ordre servi** (`content.due[].rank`, puis
l'ordre publié de `content.theses[]`). Axe X : temps servi, borné par `window.from_utc` /
`window.to_utc` quand `window.applied` vaut vrai. Une marque par événement relié.

| Canal visuel | Champ servi | Interdit |
|---|---|---|
| Position X | `agenda[].event_time_utc` | aucune interpolation |
| Couloir Y | `agenda[].event_context.theses[].thesis_id` | aucun regroupement inventé |
| Forme de marque | `agenda[].status` — `CONFIRMED` plein, `ESTIMATED` contour | jamais lu comme une probabilité |
| Taille de marque | `agenda[].importance.rank` — échelle **discrète** des rangs publiés | aucune pondération, aucune moyenne |
| Teinte | ambre par défaut · violet si `category` d'expiration d'options · rouge si `version_state = CONFLICTING_VERSIONS` | pas d'arc-en-ciel de catégories |
| Repère vertical | `as_of` servi de l'agenda | jamais l'horloge du navigateur |
| Losange plein | `content.theses[].state.review_due_at` (échéance effective) | — |
| Losange creux | `content.theses[].thesis.review_due_at` (échéance de **base**) | affiché seulement s'il diffère de l'effective |

L'écart base → effective est aujourd'hui **parsé et jamais affiché** (`followUpView.ts:167`) : le
lecteur ne voit jamais qu'une échéance a été reportée. Le dominant le montre.

## 3. Zones

| Zone | Rôle | Colonnes | Modules |
|---|---|---|---|
| La pression du moment | **SIGNAL** | 12 — rangée `3 \| 3 \| 6` | `due-pressure`, `new-information`, `snapshot-age` |
| Ce que les deux instantanés montrent | **PREUVE** | 12 — rangées `12` · `6 \| 3 \| 3` · `3 \| 3 \| 6` · `3 \| 6 \| 3` | `thesis-lanes`, `sources-freshness`, `importance-legend`, `date-certainty`, `category-split`, `filters`, `portfolio-exposure`, `window`, `published-vs-expected`, `weighting` |
| Ce qui conteste la lecture | **RISQUE** | 12 — rangées `6 \| 6` · `3 \| 3 \| 6` | `version-conflicts`, `revision-trail`, `queue-coverage`, `orphan-theses`, `coverage-ledger` |
| Ce qu'il faut revoir | **DÉCISION** | 12 — rangées `12` · `6 \| 3 \| 3` | `review-queue`, `thesis-instruments`, `new-thesis`, `event-alerts` (+ `thesis-revision-history`, hors planche) |

### Grille (12 colonnes, bento asymétrique)

`grid-template-areas` — neuf rangées, aucune répétée deux fois de suite, et la hauteur porte le
reste de l'asymétrie (`grid-auto-rows: minmax(148px, auto)`, dominant sur trois unités, file de
revue sur deux) :

```
due      due      due      newinfo  newinfo  newinfo  age      age      age      age      age      age
lanes    lanes    lanes    lanes    lanes    lanes    lanes    lanes    lanes    lanes    lanes    lanes
sources  sources  sources  sources  sources  sources  rule     rule     rule     dates    dates    dates
catsplit catsplit catsplit filters  filters  filters  exposure exposure exposure exposure exposure exposure
window   window   window   expected expected expected expected expected expected weight   weight   weight
conflict conflict conflict conflict conflict conflict trail    trail    trail    trail    trail    trail
qcov     qcov     qcov     orphans  orphans  orphans  ledger   ledger   ledger   ledger   ledger   ledger
review   review   review   review   review   review   review   review   review   review   review   review
instr    instr    instr    instr    instr    instr    newth    newth    newth    alerts   alerts   alerts
```

Chaque rangée fait exactement douze colonnes ; aucune rangée n'est un `3 3 3 3` régulier. `L = 8`
n'est pas employé sur cette page : aucune rangée de cette composition ne se referme à douze avec
un span de huit, et laisser une colonne morte se lirait comme un défaut, pas comme une intention.

## 4. Modules

| id | titre | question | taille | widget | graphique | donnée | servi | lot bloquant |
|---|---|---|---|---|---|---|---|---|
| `due-pressure` | Revues en retard | Combien de thèses déclarées ont dépassé leur échéance de revue servie ? | S | KpiTile | — | `follow-up/queue` → `content.coverage.due_count`, `content.due[0].overdue_seconds`, `content.coverage.theses_total` | oui | — |
| `new-information` | Information nouvelle | Combien de thèses déclarées ont reçu une information nouvelle depuis leur dernière revue ? | S | KpiTile | — | `content.coverage.theses_with_new_information`, `.theses_total`, `.lookback_seconds` | oui | — |
| `snapshot-age` | Âge des deux instantanés | Depuis combien de temps chacun des deux instantanés lus par cette page a-t-il été publié ? | M | **AgeMeter** ×2 + FreshnessBadge | deux pistes HTML/CSS | `calendar.age_seconds` + `calendar.freshness_policy`, `queue.age_seconds` + `queue.freshness_policy` | oui | — |
| `thesis-lanes` | Couloirs de thèses | Quel événement vérifié touche quelle thèse déclarée, et à quelle date servie ? | XL | Widget `dominant` + **EventLanes** | **couloirs sur axe de temps — ECharts** | `agenda[].event_time_utc / event_context.theses[] / status / importance.rank / category / version_state` × `content.theses[].thesis.review_due_at` / `.state.review_due_at` / `.state.is_due` | oui | — |
| `sources-freshness` | Sources, droits et fraîcheur | D'où viennent les événements servis et dans quel état de fraîcheur sont-ils publiés ? | M | Widget + CensusBars ×3 | trois recensements HTML/CSS | `agenda[].source / .rights / .fresh / .delay_status / .quality` | oui | — |
| `importance-legend` | Règle d'importance | Que signifie chaque rang d'importance publié sur un événement ? | S | Widget + StepList | — | `importance_rule.version`, `importance_rule.ranks[].rank / .code / .description` | oui | — |
| `date-certainty` | Certitude des dates | Combien d'événements servis portent une date confirmée et combien restent estimés ? | S | Widget + CensusBars | recensement HTML/CSS | `window.statuses` et `statuses` | oui | — |
| `category-split` | Répartition par catégorie | Quelles catégories d'événements composent l'agenda servi dans la fenêtre demandée ? | S | Widget + CensusBars | recensement HTML/CSS | `window.categories` et `categories` | oui | — |
| `filters` | Filtres d'affichage | Quels événements servis afficher, par catégorie, par statut de date et par nature de lien ? | S | Widget + StatusChip `aria-pressed` | — | filtre **local** sur `agenda[].category / .status / .event_context` | oui | — |
| `portfolio-exposure` | Positions déclarées touchées | Quelles positions du registre manuel sont touchées par un événement servi, et par lequel ? | M | Widget + **DataTable** | — | `agenda[].event_context.positions[].portfolio_id` × événement servi | oui | — |
| `window` | Fenêtre et instantanés | Sur quelle fenêtre demandée et quels instantanés cette page est-elle lue ? | S | Widget + ProvenanceLine ×2 | — | `window.applied / .from_utc / .to_utc / .events_in_window / .max_days`, `as_of`, `snapshot_version`, `population` ; `queue.as_of`, `queue.snapshot_version`, `content.schema_version`, `content.populations.*` | oui | — |
| `published-vs-expected` | Valeur publiée et valeur attendue | Quelle valeur la source a-t-elle publiée pour l'événement, et quelle valeur était attendue ? | M | AbsentModule `NO_SOURCE` | — | aucune | **non** | LOT 7 sources manquantes |
| `weighting` | Pondération d'impact | Quel poids chaque événement servi porte-t-il sur la thèse qu'il touche ? | S | AbsentModule `NO_SOURCE` | — | aucune | **non** | LOT 10 décision décomposée |
| `version-conflicts` | Versions contestées | Quels événements portent des versions contradictoires et laquelle a été retenue ? | M | Widget + **DataTable** | — | `coverage.events_conflicting`, `agenda[].version_state`, `.conflicting_versions[]`, `.previous_values[]`, `.conflict_election_rule` | oui | — |
| `revision-trail` | Piste des révisions | Qu'est-ce qui a été révisé, pour quelle raison publiée, et qu'est-ce qui a été refusé ? | M | Widget + ActivityFeed | — | `agenda[].revisions[].reason / .revised_at / .previous_status`, `.rejected_revisions[].reason`, `coverage.revisions_rejected`, `coverage.rejected_revision_reasons` | oui | — |
| `queue-coverage` | Couverture de la file de revue | Sur quelle population et quelle fenêtre d'observation la file de revue a-t-elle été construite ? | S | Widget + **DataTable** compacte | — | `content.coverage.*` (les neuf champs) | oui | — |
| `orphan-theses` | Thèses sans catalyseur servi | Quelles thèses déclarées ne sont touchées par aucun événement servi ? | S | Widget + DataStateBoundary **à état joint** | — | `content.theses[].thesis.id` × `agenda[].event_context.theses[].thesis_id`, total = `content.coverage.theses_total` | oui | — |
| `coverage-ledger` | Ce que l'instantané a écarté | Combien d'observations l'agenda a-t-il retenues, supplantées, périmées, écartées ou tronquées ? | M | Widget + **DataTable** | — | `coverage.*` (les douze champs) | oui | — |
| `review-queue` | File de revue | Quelles thèses déclarées doivent être revues, dans quel ordre publié, et pourquoi ? | XL | Widget `support` + **DataTable** avec `caption` | — | `content.due[].*` (les huit champs), `content.theses[].thesis.review_due_at` vs `.state.review_due_at`, `content.ordering.keys / .method / .note` | oui | — |
| `thesis-instruments` | Thèses et instruments | Quelles thèses déclarées nomment un instrument, et lesquelles n'en nomment aucun ? | M | Widget + KpiTile + InstrumentTile + **DataTable** | — | `content.coverage.theses_with_instrument`, `content.theses[].thesis.instrument`, `.thesis.portfolio_id` | oui | — |
| `new-thesis` | Déclarer une thèse | Quelle nouvelle thèse déclarer à la main pour la mettre sous suivi ? | S | Widget `workflow-step` + StepList + action principale | — | `POST /api/v1/theses` | oui | — |
| `event-alerts` | Alertes d'événement | De quels événements servis souhaite-t-on être averti ? | S | AbsentModule `SERVER_CONTRACT_MISSING` | — | aucune | **non** | LOT 13 observabilité et recherche |
| `thesis-revision-history` | Historique des révisions de la thèse | Comment cette thèse a-t-elle été révisée au fil du temps ? | S · hors planche | AbsentModule `SERVER_CONTRACT_MISSING` | — | aucune route de **lecture** des révisions | **non** | LOT 11 résultat et apprentissage |

**Bilan : 23 modules, 19 servis, 4 absents** (contre 17 / 11 / 6 aujourd'hui). Tous les modules
nouvellement servis le sont par des champs **déjà publiés** par Python et jetés par l'interface.

### Ce que la refonte récupère, champ par champ

| Champ servi aujourd'hui ignoré | Module qui le lit désormais |
|---|---|
| `calendar.age_seconds`, `calendar.freshness_policy` | `snapshot-age` |
| `queue.age_seconds`, `queue.freshness_policy` | `snapshot-age` |
| `queue.snapshot_version` | `window` (deux versions d'instantané, plus une seule) |
| `coverage.*` de l'agenda (12 champs) | `coverage-ledger`, `version-conflicts`, `revision-trail` |
| `content.coverage.*` de la file (9 champs) | `queue-coverage`, `due-pressure`, `new-information`, `thesis-instruments`, `orphan-theses` |
| `importance.rank`, `importance_rule.ranks[].description` | `thesis-lanes`, `importance-legend` |
| `revisions[].reason`, `rejected_revisions[].reason`, `previous_values[]` | `revision-trail`, `version-conflicts` |
| `conflict_election_rule` (parsé nulle part dans `apps/web`) | `version-conflicts` |
| `conflicting_versions[]` (contenu, plus la longueur) | `version-conflicts` |
| `version_state = RESOLVED` | `version-conflicts` (un événement résolu le dit) |
| `delay_status`, `scope`, `quality`, `rights` | `sources-freshness` |
| `amount`, `currency`, `expiration` | inspecteur de catalyseur |
| `categories`, `statuses`, `window.categories`, `window.statuses` | `category-split`, `date-certainty` |
| `window.applied`, `window.max_days`, `window.events_in_window` | `window` |
| `thesis.review_due_at` (échéance de base) | `thesis-lanes`, `review-queue` |
| `thesis.instrument`, `thesis.portfolio_id` | `thesis-instruments` |
| `clusters[].tickers`, `.provenance.member_event_ids`, `.first_published_at` | fiche de thèse (inspecteur) |
| `due[].last_recorded_at`, `urgency_reasons[].cluster_id / .last_received_at / .reference_instant` | `review-queue` |
| `ordering.method`, `ordering.note` | légende de `review-queue` |

## 5. Nouvelles primitives exigées

### `AgeMeter`
- **Donnée exigée** : `age_seconds` (entier servi, nullable), `freshness_policy.budget_seconds`,
  `.kind`, `.version`, `state` servi.
- **Rôle** : poser un âge servi sur un budget servi, en une piste horizontale. Les deux nombres
  sont écrits en durée française. La géométrie est la seule opération — même doctrine que
  `censusWidths`.
- **Interdit** : écrire un pourcentage dérivé, colorer un verdict, dessiner un anneau ou une jauge
  circulaire, déclarer « périmé » de son propre chef. **Le verdict vient de `state`.**

### `DataTable`
- **Donnée exigée** : `columns[] { key, label, unit, align, nature: texte | chiffre | instant |
  code | duree }`, `rows[]` **dans l'ordre servi**, `caption` (obligatoire), `emptyLabel`
  (obligatoire), `rowCount` servi, `truncationNote` (obligatoire dès qu'une ligne servie n'est pas
  rendue).
- **Rôle** : la table financière dense de Titan Ledger — chiffres tabulaires, `caption` visible,
  défilement interne borné, colonnes typées.
- **Interdit** : tri client (une en-tête n'est cliquable que sur une clé d'ordre **servie**, et
  alors la clé servie est nommée) ; `slice` muet ; tiret dans une cellule non publiée ; `<code>`
  autour d'une phrase française ; ISO brut dans le texte visible.

### `EventLanes`
- **Donnée exigée** : `lanes[] { id, label, orderKey servi }`, `marks[] { laneId, instantUtc,
  status, importanceRank, category, versionState, eventId }`, `refs[] { laneId, kind: base |
  effective, instantUtc }`, `asOfUtc`, `bounds { fromUtc, toUtc, applied }`, `rankLegend[] { rank,
  code, description }`.
- **Rôle** : le seul axe de temps réel de la page.
- **Accessibilité** : `role="img"` + `aria-label` construit sur des valeurs servies, **plus** une
  table équivalente obligatoire dépliée par un bouton réel, dont chaque ligne porte le bouton
  d'ouverture de l'inspecteur.
- **Interdit** : interpolation, courbe de tendance, second axe de valeur, 3D, animation d'entrée
  sous `prefers-reduced-motion`, couleur brute hors jetons (`no-raw-colors`).

## 6. Textes d'absence (exacts, sans aucun chiffre)

| Module | Texte affiché |
|---|---|
| `due-pressure` | La file de revue n'a publié aucun instantané : le nombre de thèses en retard de revue n'est pas connu. |
| `new-information` | La file de revue n'a publié aucun instantané : aucune information nouvelle ne peut être dénombrée. |
| `snapshot-age` | Aucun instantané daté n'a été publié : il n'y a pas d'âge à mesurer, seulement le budget de la route. |
| `thesis-lanes` | Aucun événement servi ne nomme une thèse déclarée : aucun couloir ne peut être tracé. |
| `sources-freshness` | Les événements servis ne portent ni source ni état de fraîcheur publiés : aucun recensement de provenance n'est possible. |
| `importance-legend` | L'agenda publié ne porte pas sa règle d'importance : les rangs affichés n'ont pas de définition servie. |
| `date-certainty` | L'agenda publié ne porte pas ses compteurs de statut de date : la part de dates confirmées n'est pas connue. |
| `category-split` | L'agenda publié ne porte pas ses compteurs de catégorie : la composition des événements n'est pas connue. |
| `filters` | Aucun événement n'est servi : il n'y a rien à filtrer. |
| `portfolio-exposure` | Aucun événement servi ne nomme une position du registre manuel : il n'y a pas d'exposition à montrer. |
| `window` | Aucun instantané n'a été publié : ni la fenêtre appliquée ni la version d'instantané ne peuvent être nommées. |
| `published-vs-expected` | Le contrat d'agenda ne porte ni valeur publiée, ni valeur attendue, ni consensus : rien ne permet de dire qu'un résultat a dépassé ou manqué une attente. |
| `weighting` | Aucun contrat servi ne publie de poids d'événement : le rang d'importance ordonne, il ne pondère pas, et une moyenne de rangs ne serait pas une mesure. |
| `version-conflicts` | L'agenda publié ne porte pas d'état de version : les événements contestés ne peuvent pas être nommés. |
| `revision-trail` | Aucune révision n'est publiée sur les événements servis : il n'y a pas de piste à afficher. |
| `queue-coverage` | La file de revue n'a publié aucun bloc de couverture : sa population et sa fenêtre d'observation ne sont pas connues. |
| `orphan-theses` | L'un des deux instantanés n'a pas répondu : le croisement des thèses et des événements n'est pas possible, et aucune couverture n'est affirmée. |
| `coverage-ledger` | L'agenda publié ne porte pas son bloc de couverture : ce qui a été écarté n'est pas connu. |
| `review-queue` | La file de revue n'a publié aucun instantané : aucune thèse ne peut être ordonnée pour la revue. |
| `thesis-instruments` | La file de revue n'a publié aucun instantané : le rattachement des thèses à un instrument n'est pas connu. |
| `new-thesis` | Le contrat de déclaration de thèse n'est pas joignable : aucune thèse ne peut être déclarée maintenant. |
| `event-alerts` | Aucun contrat servi ne porte de règle d'alerte d'événement ; une préférence enregistrée dans le navigateur ne serait ni servie ni notifiée. |
| `thesis-revision-history` | Aucun contrat de lecture ne publie l'historique des révisions d'une thèse : cette fiche ne peut en afficher aucun. |

Aucun de ces textes ne contient de chiffre, aucun ne suggère que la valeur existerait ailleurs,
aucun ne promet de date de livraison.

## 7. États dégradés attendus

Le vocabulaire est celui de `ModuleState` (onze états, pas huit) : `ready`, `refreshing`,
`loading`, `empty`, `stale`, `partial`, `delayed`, `offline`, `error`, `auth-required`, `closed`.

**Règle d'état joint (bloquante).** Tout module lisant **les deux** instantanés — `thesis-lanes`,
`orphan-theses`, `thesis-instruments`, `window`, `snapshot-age` — calcule un `joinedState` :
le pire des deux états, avec un `stateDetail` qui **nomme lequel** des deux instantanés est en
cause. Il ne substitue **jamais** un tableau vide à une source absente. C'est la correction du
faux positif de couverture (`CatalystsPage.tsx:295`).

**Règle de périmé propagé.** Un `queue.state === 'stale'` marque `stale` **tous** les modules qui
lisent la file, pas seulement la carte de revue. Deux modules ne peuvent pas afficher le même
instantané avec deux vérités de fraîcheur différentes.

| État | Cadre de page | Modules d'agenda | Modules de file | Dominant |
|---|---|---|---|---|
| `loading` | squelette de grille, aucune valeur | `DataStateBoundary` par module, aucun zéro | idem | aucun axe tracé, aucune légende |
| `refreshing` | contenu conservé, `LiveBadge` en cours | valeurs conservées, surbrillance de version | idem | axe conservé, marques mises à jour |
| `empty` | grille tenue | phrase de `reason` serveur relayée | phrase d'absence du module | « aucun couloir ne peut être tracé » |
| `partial` (`degraded` serveur) | bandeau de zone | `stateDetail` = raison serveur ; les compteurs servis restent servis | idem | axe tracé, mention « couverture incomplète signalée par le serveur » |
| `delayed` (population `DELAYED`) | population écrite dans `window` | chaque carte porte sa population servie | idem | légende porte la population |
| `stale` | bandeau de zone **et** de module | `AgeMeter` montre le dépassement, `state` servi porte le verdict | **tous** les modules de file, pas seulement `review-queue` | axe tracé, repère `as_of` étiqueté périmé |
| `offline` | rien n'est reconstruit | « L'API locale est injoignable — aucun événement affiché. » | « L'API locale est injoignable — aucune thèse affichée. » | aucun axe |
| `error` (`rejected`, `not_entitled`, réponse invalide) | échec fermé | rien n'est affiché, la cause serveur est nommée | idem | aucun axe |
| `auth-required` | `AuthRequiredNotice` à la place de la planche | — | — | — |
| `closed` | code servi affiché tel quel | code servi affiché tel quel | idem | aucun axe |

**Fenêtre.** Le sélecteur de fenêtre (`PeriodTabs` en tête de page) est borné par `window.max_days`
servi. Une fenêtre qui ne sélectionne rien renvoie `empty_window` : la page l'affiche comme
« la fenêtre demandée ne sélectionne aucun événement publié », **jamais** comme un agenda vide.

## 8. Parcours clavier

1. Lien d'évitement → `h1` « Suivi ».
2. En-tête de page : `PeriodTabs` de fenêtre — `tabindex` glissant, `←`/`→` pour changer,
   `Home`/`End` aux bornes, `Entrée`/`Espace` pour appliquer. Une seule requête par application.
3. La planche suit l'ordre du DOM, qui est l'ordre de lecture : **SIGNAL → PREUVE → RISQUE →
   DÉCISION**. Aucune carte ne prend le focus ; seuls ses contrôles réels le prennent.
4. `thesis-lanes` : le canevas n'est pas focalisable. Tabulation → action de tête → bouton
   « Table équivalente des couloirs » (`aria-expanded`) → lignes de la table, chacune portant un
   bouton « Ouvrir l'événement » qui monte l'inspecteur du shell.
5. `filters` : deux `role="group"` nommés ; boutons `aria-pressed` **indépendants**, donc
   tabulation entre eux (pas de `tabindex` glissant). Après bascule, l'unique région live de la
   page annonce le nombre de lignes affichées sur le nombre de lignes servies.
6. `review-queue` : la table est dans un `role="region"` `tabindex="0"` avec `aria-label`, avec
   `caption` visible. Le titre de chaque thèse est un `button` qui ouvre la fiche de thèse dans
   l'emplacement d'inspecteur du shell. `Échap` ferme l'inspecteur et **rend le focus au bouton
   d'origine**.
7. **Une seule surface de détail.** Ouvrir la fiche de thèse ferme l'inspecteur de catalyseur, et
   réciproquement. La fiche cesse d'être un `role="dialog" aria-modal="true"` rendu en flux au bas
   d'une carte : elle est montée dans l'emplacement d'inspecteur du shell, comme les neuf autres
   `.vx-sheet` du dépôt, et son titre est un `h3` (le style `.vx-sheet-head h3` cesse d'être mort).
8. `new-thesis` : l'action principale unique de la page ouvre le formulaire dans le **même**
   emplacement d'inspecteur. Plus de `h2` imbriqué dans une section qui en porte déjà un.
9. **Une seule région live** (`aria-live="polite"`) au niveau de la page. Les modules absents
   passent de `role="status"` à `role="note"` : douze régions live simultanées deviennent une.
10. Aucun vol de focus, aucun défilement automatique, aucun `autofocus`.

## 9. Corrections obligatoires de la refonte

**Bloquantes.**
1. `catalystsModules.ts:35` — `GET /api/v1/review-queue` **n'existe pas**. La constante devient
   `GET /api/v1/follow-up/queue — content`. Le test `catalystsModules.test.ts:15` cesse de vérifier
   un préfixe `/^(GET|POST) \/api\/v1\//` et vérifie l'appartenance au registre de routes réel
   (document OpenAPI), sinon son intitulé sur-revendique.
2. Faux positif de couverture : `orphan-theses`, `due-pressure` et `thesis-lanes` refusent le
   tableau vide de substitution et rendent l'état joint. Trois tests de non-régression :
   file en `loading`, en `offline`, en `error`.
3. Périmé propagé à tous les modules lisant la file.

**Forme et honnêteté.**
4. Aucune phrase française dans `<code>` (12 sites mesurés) : le canal monospace est réservé aux
   valeurs machine servies ; une absence est un `span[data-absent]`.
5. Aucune absence dans un axe de recensement : « source non publiée » et « fraîcheur non publiée »
   quittent les clés de `CensusBars` pour une ligne d'absence distincte, sous le recensement.
6. Aucune troncature muette : `portfolio-exposure` rend la table complète, avec défilement interne
   et nombre de lignes servies écrit ; `EXPOSURE_LINES = 6` disparaît.
7. Aucun ISO brut dans le texte visible : un helper partagé rend l'instant en français et laisse
   l'ISO servi dans `dateTime` et dans l'infobulle.
8. Aucune seconde brute : `overdue_seconds`, `lookback_seconds`, `age_seconds` et
   `budget_seconds` sont rendus en durée française.
9. Aucun chiffre d'interface présenté comme donnée : `Object.keys(CATEGORY_LABELS).length`
   disparaît du pied de la dominante.
10. Trois axes sémantiques distincts : catégorie, statut de date et nature de lien reçoivent trois
    traitements visuels **différents** (`StatusChip` avec `tone` et `data-*` réellement ciblés en
    CSS), pas trois pastilles grises identiques.
11. La sélection d'une ligne ne repose plus sur la seule couleur : épaisseur de filet **et** glyphe
    de sélection, en plus de `aria-pressed`.
12. `AbsentModule` : identifiant **slugifié** (`vx-absent-${reason}-${slug(title)}`) — un titre à
    espaces casse aujourd'hui `aria-labelledby` sur les six modules absents ; et niveau de titre
    unique sur la planche (`h2` partout, comme `Card`).
13. `<caption>` obligatoire sur chaque table (`DataTable` le refuse autrement).
14. Quatre morts CSS supprimées : `.vx-cat-orphans-note`, `counter-reset: vx-cat`,
    `.vx-cat-exposure-list` sans règle, `.vx-cat-timeline-card` sans règle ; `.vx-sheet-head h3`
    redevient vivant en montant la fiche dans l'inspecteur.

**Portes de conception à ajouter** (aux neuf existantes de `apps/web/src/design/`) :
`no-french-in-code-channel`, `absent-heading-and-id`, `no-silent-truncation`,
`served-count-over-local-recount`, `cross-snapshot-state`, `one-live-region-per-page`,
`no-raw-iso-in-text`, `no-raw-seconds`.

## 10. Contrôles de composition

- `one-dominant-per-page` : exactement un `[data-rank='dominant']` — `thesis-lanes`. `review-queue`
  est `XL` **de taille** et `support` **de rang** : la taille n'est pas un rang.
- Un seul moteur graphique chargé, paresseusement, sur cette route.
- Les trois largeurs cibles (1280, 1440, 1600) sont mesurées par un test de composition : aucune
  carte `S` ne doit être plus haute que ses voisines de rangée à 1280 px — c'est le défaut mesuré
  d'`UpcomingCountModule` et ses trois `Metric` en `flex-wrap`, remplacées ici par un `KpiTile`
  unique par carte `S`.
- Aucun défilement horizontal du corps de page ; les tables et le graphique défilent dans leur
  propre conteneur.
- Zéro violation `axe` critique ou sérieuse ; contraste vérifié sur l'ambre d'accent en fond très
  profond.

## 11. Documentation à produire

La planche §10 n'a **aucune** fiche produit aujourd'hui : la seule fiche existante,
`docs/01-product/pages/09-follow-up.md`, se déclare elle-même « plus une destination » et ne décrit
que quatre modules. Le catalogue vit uniquement dans le code.

- Créer `docs/01-product/pages/10-suivi.md` avec le contenu de cette fiche.
- `docs/01-product/pages/09-follow-up.md` devient une redirection documentaire vers celle-ci.
- Mettre à jour `docs/01-product/ROUTES.md` (libellé de navigation « Suivi ») et
  `docs/05-design/PAGE_ARBITRATION.md` (la question unique de la page remplace les deux questions
  concurrentes).

## 4. Réfutations adversariales — 33 à traiter avant implémentation

**Verdict : CORRECTIONS_REQUISES** — Vérification champ par champ des 19 modules « servi: oui » contre /home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py, .../follow_up.py, /home/user/vertex-merge/apps/api/src/vertex_api/calendar.py, .../follow_up.py, .../snapshot_views.py, .../routes.py et le client généré /home/user/vertex-merge/apps/web/src/api/schema.d.ts.

CE QUI TIENT (vérifié, pas supposé). L'essentiel de l'inventaire de la conception est exact et le dépôt le publie vraiment : les 12 champs de `coverage` de l'agenda (calendar.py:1115-1129) ; les 9 champs de `content.coverage` de la file, dont `content_schema_prefixes` (follow_up.py, bloc coverage), validés fail-closed par `_QUEUE_COVERAGE_COUNTS` (api/follow_up.py:141-150) ; `age_seconds` + `freshness_policy{budget_seconds,kind,version}` sur les DEUX routes (schemas.py:118-143, schema.d.ts:1308-1345 et 1585-1604) ; `window.applied/from_utc/to_utc/max_days/events_total/events_in_window/categories/statuses` (CalendarWindow) ; `categories`/`statuses` du snapshot entier ; `importance_rule.version` et `ranks[].rank/.code/.description` (calendar.py:185-215) ; `agenda[].source/.rights/.fresh/.delay_status/.quality/.scope/.version_state/.conflict_election_rule/.conflicting_versions[]/.previous_values[]/.revised` ; `event_context.theses[].thesis_id` et `.positions[].portfolio_id` (calendar.py:717-746), avec un `thesis_id` qui est bien la même clé entière que `content.theses[].thesis.id` (calendar.py:1187 vs follow_up.py) — le croisement est donc joignable ; les 8 champs de `content.due[]` y compris `last_recorded_at` et `urgency_reasons[].code/.cluster_id/.last_received_at/.reference_instant` ; l'écart échéance de base (`thesis.review_due_at`) / échéance effective (`state.review_due_at`) est réel et servi (project_thesis_state : un sommeil expiré déplace l'échéance) ; `content.ordering.method/.keys/.note` ; la route `GET /api/v1/calendar` accepte bien `from`/`to` bornés à 90 jours (routes.py:414-448). La correction bloquante n°1 de la conception est fondée : `catalystsModules.ts:34` déclare `GET /api/v1/review-queue`, route qui n'existe pas — la seule route servie est `/api/v1/follow-up/queue` (routes.py:1100).

CE QUI NE TIENT PAS — 16 violations, dont 3 dures. (1) `rejected_revisions[].revised_at` N'EXISTE PAS : le worker publie `{index, reason, declared_revised_at}` (calendar.py:470-478) ; le parseur actuel lit un sous-objet `revision` inexistant (calendarView.ts:227-229) et rend donc toujours null. (2) L'« identité canonique d'instrument » de `thesis-instruments` n'est pas servie : le seul écrivain est `ThesisInstrumentInput{ticker}` (api/follow_up.py:185-188) — ni type, ni place, ni devise, ni multiplicateur ; et `InstrumentTile` exige un `FlatTicker` du snapshot Marchés, troisième instantané que l'espace déclare ne pas lire. (3) Une contradiction de PORTÉE traverse la planche : la conception impose une fenêtre (`window.applied` vrai) alors que `coverage.*` décrit toujours l'instantané ENTIER — d'où quatre modules qui nomment le mauvais nombre (`version-conflicts`, `coverage-ledger`, `filters` dont le pied cite `coverage.events_displayed` au lieu de `window.events_in_window`, `date-certainty` qui appelle « réellement affiché » un compteur de fenêtre calculé avant tout filtre local), et un faux positif nouveau dans `orphan-theses`, où une thèse dont l'unique événement est hors fenêtre est déclarée « sans catalyseur servi ».

S'y ajoutent : le verdict de fraîcheur de l'agenda qui ne vient PAS de `state` pour `empty`/`not_entitled`/`rejected` (calendar.py:568-576 — la bascule `stale` est conditionnée à trois états seulement) ; `coverage.content_schema_prefixes` posé sous une question de population alors que le dépôt le déclare explicitement comme une capacité de lecture et non une provenance (snapshot_views.py:682-686) ; la liste des champs « exigés » de `new-thesis`, qui présente deux optionnels comme obligatoires et omet `idempotency_key` ; deux chaînes servies rendues « verbatim » qui mettraient de l'anglais et du français sans accents à l'écran (`ordering.note`, follow_up.py:362-366 ; `importance_rule.ranks[].description`, calendar.py:189) ; `overdue_seconds` figé à l'horloge du worker et présenté sans son as_of ; le rang 1 `MACRO_GLOBAL` structurellement invisible dans le dominant (`_event_context` rend des listes vides sans ticker, calendar.py:723-724) alors que la légende de la page le décrit ; et l'auto-contradiction de la porte `served-count-over-local-recount`, qui interdirait `sources-freshness` et `orphan-theses`, deux modules servis de la même planche, faute de compteur servi pour source/droit/retard.

Aucune violation des lois 1, 2 et 5 n'a été trouvée : aucun module ne touche compte, position, solde ou ordre ; le portefeuille n'entre que par `portfolio_id` du registre manuel (`derive_open_position_tickers`, calendar.py:1165-1174) ; aucun module servi n'affiche de probabilité prédictive, et le statut de date `ESTIMATED`/`CONFIRMED` est correctement traité comme un fait publié, pas comme une confiance. Aucune quantité financière (prix, Greek, IV, rendement, ratio, score) ne serait calculée dans le navigateur : les seules opérations client restent des géométries de proportion entre nombres servis, des conversions de durée et des filtres d'affichage. Aucun module « servi: oui » ne dépend d'un lot d'intelligence non livré.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `revision-trail` | Loi 4 (une absence n'est jamais un zéro ni un tiret) et loi 7 (source, as_of) | Champ inexistant. La conception exige `agenda[].rejected_revisions[].revised_at`. Le worker publie exactement `{index, reason, declared_revised_at}` — /home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:470-478 (`_rejected_revision`), aucune clé `revised_at`. Le parseur actuel le confirme en creux : /home/user/vertex-merge/apps/web/src/pages/calendar/calendarView.ts:227-229 lit `revised_at` sur un sous-objet `record['revision']` qui n'existe nulle part dans le contrat — la valeur est donc TOUJOURS null aujourd'hui, et le serait encore après la refonte. `declared_revised_at` n'apparaît dans aucun fichier de apps/web. | Remplacer `.revised_at` par `.declared_revised_at` dans la donnée du module, et le nommer pour ce qu'il est : « instant de révision DÉCLARÉ par la source, refusé et non retenu », nullable par contrat (`declared if isinstance(declared, str) else None`). Quand il vaut null, rendre un `span[data-absent]` « la source n'a déclaré aucun instant lisible », jamais un tiret. Ajouter `.index` servi pour identifier l'entrée refusée. Supprimer la lecture morte de `record['revision']` dans calendarView.ts. |
| `revision-trail` | Loi 7 (chaque grandeur porte sa source et sa méthode) | Provenance fausse dans le pied. Le pied annonce « raisons relayées verbatim depuis la source ». C'est vrai de `revisions[].reason` (relayé tel quel : /home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:532 `accepted.append(dict(entry))`), mais FAUX de `rejected_revisions[].reason`, dont les valeurs sont des codes produits par le WORKER : `REVISION_REASON_NOT_A_LIST`, `REVISION_REASON_NOT_A_MAPPING`, `REVISION_REASON_NOT_DATED`, `REVISION_REASON_IN_THE_FUTURE`, `REVISION_REASON_AFTER_OBSERVATION` (calendar.py, exportés dans `__all__` lignes 137-141). Idem `coverage.rejected_revision_reasons` (calendar.py:1122-1124), qui est un recensement de ces codes worker. | Scinder le flux en deux provenances explicitement étiquetées : (a) « déclaré par la source » pour `revisions[].reason`, texte libre, rendu verbatim ; (b) « refusé par le worker » pour `rejected_revisions[].reason` et `coverage.rejected_revision_reasons`, rendus en `<code>` (valeur machine) avec une phrase française écrite côté interface. Corriger le pied en conséquence. |
| `thesis-instruments` | Loi 4 (absent ≠ valeur théorique) et loi 7 (unité, devise, source) | Le pied revendique une « identité canonique d'instrument servie (symbole, type, place, devise, multiplicateur) ». Aucun de ces champs n'existe hors le symbole : le SEUL écrivain de `thesis.instrument` est `ThesisInstrumentInput` qui ne porte que `ticker` — /home/user/vertex-merge/apps/api/src/vertex_api/follow_up.py:185-188 — et le gateway écrit littéralement `{"ticker": request.instrument.ticker}` (même fichier, `DbFollowUpGateway.create`). Le worker relaie `dict(entry.thesis.instrument)` sans l'enrichir (/home/user/vertex-merge/apps/worker/src/vertex_worker/follow_up.py, bloc `"thesis": {...}`). Ni type, ni place, ni devise, ni multiplicateur ne sont servis. En outre le widget nommé `InstrumentTile` exige un `FlatTicker` du snapshot MARCHÉS et appelle `useAnalysis` — /home/user/vertex-merge/apps/web/src/components/widgets/InstrumentTile.tsx:39-52 — donc un TROISIÈME instantané, que l'espace déclare pourtant ne pas lire (« deux instantanés servis, croisés et jamais fondus »). | Réduire le module à ce qui est servi : `content.coverage.theses_with_instrument` sur `theses_total`, `content.theses[].thesis.instrument.ticker` et `content.theses[].thesis.portfolio_id`. Retirer `InstrumentTile` de la liste des widgets (ou déclarer explicitement le troisième instantané `markets/overview`, son as_of, sa fraîcheur, et l'état des tickers absents de ce snapshot). Réécrire le pied : « symbole d'instrument servi ; type, place, devise et multiplicateur ne sont publiés par aucun contrat de thèse ». |
| `version-conflicts` | Loi 4 (réel ≠ partiel) et loi 7 (portée, méthode) | Contradiction de portée entre le compte servi et les lignes rendues. `coverage.events_conflicting` compte l'instantané ENTIER (/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:1120) et est relayé verbatim, indépendamment de la fenêtre (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py, `coverage=dict(_require_mapping(content.get("coverage")...))`, hors de toute sélection). La table, elle, est construite sur `agenda[]` déjà FILTRÉ par la fenêtre (calendar.py:399-405 `selected = [...]`), fenêtre que la conception IMPOSE (module `window` : « window.applied vaut vrai »). Le module affichera donc « N événements contestés » au-dessus d'une table qui en montre M < N, sans le dire. | Afficher deux nombres nommés séparément : « contestés sur l'instantané entier : `coverage.events_conflicting` » et « contestés dans la fenêtre demandée : nombre de lignes rendues », avec `window.from_utc`/`window.to_utc` écrits. Ne jamais présenter le compte servi comme le compte de la table. |
| `coverage-ledger` | Loi 7 (portée et méthode d'une grandeur) | Même défaut de portée. Les douze champs de `coverage` décrivent l'instantané entier — `observations_considered`, `events_displayed`, `events_superseded`, `events_stale`, `window_truncated`, `max_observations`, `lookback_seconds` (/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:1115-1129) — alors que la page les lit à côté d'un agenda fenêtré dont le compte réel est `window.events_in_window` (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py:344). Le pied « comptes servis par le worker, aucun recompte côté navigateur » est exact mais muet sur la portée, donc `events_displayed` contredira visiblement `window.events_in_window` sur la même planche. | Ajouter au pied et à la légende de la table : « portée = instantané entier, pas la fenêtre demandée ». Poser sur la même ligne `window.events_in_window` et `window.events_total` servis pour que l'écart soit lu comme un fait, pas comme une incohérence. |
| `filters` | Loi 4 (huit états distincts, chacun le dit) et loi 7 | Dénominateur faux. Le pied affirme « le compte servi reste celui de `coverage.events_displayed` ». `coverage.events_displayed` est le nombre d'événements publiés par le WORKER (/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:1117 `len(agenda)`), sans aucune fenêtre. Le compte des lignes réellement servies à la page sous fenêtre appliquée est `window.events_in_window` (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py:344). Sur une page qui impose une fenêtre, le pied nomme donc le mauvais nombre. | Remplacer le dénominateur du pied et de la région live par `window.events_in_window` quand `window.applied` vaut vrai, et par `coverage.events_displayed` seulement quand `window.applied` vaut faux. Annoncer « X lignes affichées sur Y lignes servies dans la fenêtre demandée ». |
| `orphan-theses` | Loi 4 (une absence n'est jamais une absence d'une autre nature) | Faux positif de fenêtre, non couvert par la règle d'état joint. Sous fenêtre appliquée, l'agenda servi est une SÉLECTION (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py:399-405). Une thèse dont le seul événement relié tombe hors de `window.from_utc`/`window.to_utc` sortira du croisement et sera déclarée « sans catalyseur servi » : une absence de FENÊTRE présentée comme une absence absolue. La règle d'état joint proposée ne traite que l'indisponibilité d'un instantané, pas la restriction de fenêtre. De plus le module produit un ensemble-différence CLIENT sans compteur servi, ce que la porte `served-count-over-local-recount` que la conception ajoute elle-même interdit. | Borner la phrase et le titre à la fenêtre : « thèses qu'aucun événement servi DANS LA FENÊTRE DEMANDÉE ne nomme », avec `window.from_utc`/`window.to_utc` écrits et un état visible « fenêtre appliquée ». Déclarer explicitement dans la spécification de la porte `served-count-over-local-recount` l'exception « croisement local sans compteur servi », faute de quoi ce module viole la porte de sa propre planche. |
| `date-certainty` | Loi 4 et loi 7 (une grandeur dit sur quelle population elle porte) | Étiquette fausse dès qu'un filtre est actif. La donnée décrit `window.statuses` comme « les compteurs ESTIMATED/CONFIRMED de ce qui est RÉELLEMENT affiché ». Ces compteurs sont calculés sur la sélection de FENÊTRE uniquement (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py, `_counters(selected)` appelé par `_window_echo`), avant tout filtre local. Le module `filters` de la même planche masque ensuite des lignes sans recompter (par conception). L'étiquette « réellement affiché » devient donc fausse à la première bascule de filtre. | Remplacer l'étiquette par « dans la fenêtre demandée », jamais « réellement affiché ». Le nombre de lignes après filtre local est annoncé par l'unique région live de `filters`, et n'est pas un compteur servi. |
| `snapshot-age` | Loi 4 (huit états distincts) et loi 7 (fraîcheur explicite) | Le verdict de fraîcheur ne vient PAS toujours du champ `state` servi côté agenda, contrairement à ce qu'affirment la donnée, le pied et la spécification d'`AgeMeter`. Dans /home/user/vertex-merge/apps/api/src/vertex_api/calendar.py:568-576, la bascule `stale` n'est appliquée que si l'état courant appartient à `("ok", STATE_DEGRADED, STATE_EMPTY_WINDOW)`. Un agenda `not_entitled`, `rejected` ou `empty` dont l'âge dépasse `CALENDAR_MAX_AGE` conserve son état et ne gagne que la raison `REASON_SNAPSHOT_STALE` en préfixe. Un instantané périmé peut donc être servi sans que `state` le dise, et l'AgeMeter afficherait un dépassement sans verdict. | Écrire dans la spécification d'`AgeMeter` que le verdict de fraîcheur de l'agenda se lit sur `state` UNIQUEMENT pour `ok`, `degraded` et `empty_window` ; pour `empty`, `not_entitled` et `rejected`, le dépassement doit être annoncé depuis le couple servi `age_seconds` vs `freshness_policy.budget_seconds` ET la chaîne `reason` servie, relayée verbatim. La file de revue (`ok\|stale\|empty`) n'a pas ce défaut ; les deux pistes ne peuvent donc pas partager la même règle de verdict. |
| `queue-coverage` | Loi 7 (source d'une valeur, jamais confondue avec une provenance) | `coverage.content_schema_prefixes` est déclaré EXPLICITEMENT dans le dépôt comme une déclaration de capacité de lecture et non une provenance : /home/user/vertex-merge/apps/api/src/vertex_api/snapshot_views.py:682-686 `CAPABILITY_DECLARATION_PATHS = frozenset({"coverage.content_schema_prefixes"})`, avec le commentaire « Une déclaration de capacité dit ce que le consommateur SAIT LIRE. Elle ne dit RIEN de la provenance des observations RETENUES ». La poser sous la question « sur quelle POPULATION la file a-t-elle été construite ? », à côté de `populations.information_context`, la fait lire comme une provenance — le défaut exact que ce garde-fou a été écrit pour fermer. | Séparer la ligne et l'étiqueter : « familles de schéma que le worker SAIT LIRE — déclaration de capacité, pas la provenance des observations retenues ». La population reste portée par `content.populations.information_context` seule, sur une ligne distincte. |
| `new-thesis` | Loi 7 (méthode et version du contrat annoncées exactement) | La carte annonce « la liste servie des champs exigés par le contrat (titre, hypothèses, invalidation, horizon, instrument) ». Le contrat réel est `CreateThesisRequest` — /home/user/vertex-merge/apps/api/src/vertex_api/follow_up.py:190-210 : obligatoires = `title`, `hypotheses`, `invalidation`, `idempotency_key` ; optionnels (valeur par défaut `None`) = `portfolio_id`, `instrument`, `horizon`, `review_due_at`, `note`. La carte présente donc deux champs OPTIONNELS comme exigés et omet le seul autre champ RÉELLEMENT obligatoire. | Écrire la liste exacte : exigés = titre, hypothèses, invalidation, clé d'idempotence ; facultatifs = position déclarée, instrument (symbole), horizon, échéance de revue, note. Nommer `idempotency_key` comme une clé de rejeu du client (un rejeu répond `created=false` sans écrire), et non comme une donnée de la thèse. |
| `review-queue` | Règle de langue de l'interface (tous les textes d'écran en français) et loi 7 (méthode nommée) | La légende doit rendre `content.ordering.keys[]`, `.method` et `.note` « verbatim ». Or ces chaînes servies ne sont pas du français d'interface : `DUE_ORDERING_KEYS` vaut « effective_review_due_at asc (du depuis le plus longtemps d'abord) », « base_review_due_at asc (echeance la plus proche ensuite) » etc. — /home/user/vertex-merge/apps/worker/src/vertex_worker/follow_up.py:103-112, français sans accents mêlé à des identifiants anglais — et `ordering.note` est une phrase entièrement ANGLAISE : « new information raises visible urgency (flag + reasons) but never rewrites the thesis, its revisions or its due instant » (follow_up.py:362-366). `ordering.method` vaut « lexicographic ». | Rendre les clés servies comme valeurs machine (`<code>`, canal monospace) et écrire la légende française côté interface, sans reformuler le contenu servi. Ne pas afficher `ordering.note` verbatim à l'écran : soit la rendre en `<code>` étiquetée « note de contrat servie (en anglais) », soit ouvrir un changement de contrat versionné pour publier une note française. Même traitement pour `ordering.method`. |
| `importance-legend` | Règle de langue de l'interface (textes d'écran en français) | Le module affiche `importance_rule.ranks[].description` « relayée verbatim, jamais reformulée ». Les descriptions servies sont du français sans accents, écrit pour un contrat machine : « evenement macro global » (/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:189), « resultats d'un ticker avec position manuelle ou these declaree », etc. (IMPORTANCE_RULE_RANKS, calendar.py:185-215). | Afficher `rank` et `code` comme valeurs machine servies, et la description servie dans un canal étiqueté « description de la règle servie, v{importance_rule.version} ». Si le français accentué est exigé à l'écran, faire monter `IMPORTANCE_RULE_VERSION` (changement de règle versionné, worker) plutôt que de reformuler côté interface. |
| `thesis-lanes` | Loi 4 (une absence structurelle doit être dite) et loi 6 (la page répond à une question sans mentir sur sa couverture) | Le rang d'importance 1, `MACRO_GLOBAL`, ne peut par construction JAMAIS apparaître dans un couloir. `_event_context` renvoie `{"positions": [], "theses": [], "links": []}` dès que l'événement n'a pas de ticker — /home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:723-724 — et les événements macro sont de scope global sans ticker (`EVENT_SCOPE_GLOBAL`). Le dominant, seule représentation temporelle de la page, exclut donc silencieusement la catégorie que sa propre légende (`importance-legend`, rang 1) présente comme la plus importante ; ces mêmes événements restent pourtant comptés dans `category-split`, `date-certainty`, `sources-freshness` et `coverage-ledger`, qui portent sur l'agenda entier. | Écrire dans la légende du dominant et dans le pied : « un événement macro global ne nomme aucune thèse (aucun ticker servi) : il ne peut porter aucun couloir ». Ajouter une bande « hors couloir » comptant les événements servis sans `event_context.theses[]`, avec son propre nombre, pour que la différence entre la population des couloirs et celle des recensements soit lue comme un fait servi. |
| `due-pressure` | Loi 7 (as_of et méthode obligatoires sur une grandeur critique) | `overdue_seconds` est figé à l'instant du WORKER, pas du lecteur : `"overdue_seconds": max(0, int((now - effective_due).total_seconds()))` — /home/user/vertex-merge/apps/worker/src/vertex_worker/follow_up.py:343 — où `now` est l'horloge de publication de l'instantané. La file peut être servie jusqu'au budget de séance fermée de la politique `news_attention` (/home/user/vertex-merge/apps/api/src/vertex_api/follow_up.py, `FOLLOW_UP_FRESHNESS_POLICY`). Afficher « le retard le plus long » sans dire à quel instant il a été mesuré sous-estime le retard réel de l'âge de l'instantané. Le pied ne nomme pas non plus la méthode qui fait de `due[0]` le plus en retard : c'est la première clé servie de `content.ordering.keys[]` (effective_review_due_at asc), pas une évidence. | Écrire « retard mesuré à l'instantané du {as_of servi} » et poser `age_seconds` de la file à côté, en durée française. Nommer explicitement dans le pied la clé d'ordre servie qui justifie que `content.due[0]` porte le retard le plus long (`content.ordering.method` + première entrée de `content.ordering.keys[]`), au lieu de le supposer. |
| `sources-freshness` | Loi 3 (le navigateur n'établit pas de classement servi) — appliquée à la porte « served-count-over-local-recount » que la conception ajoute elle-même | Aucun compteur servi n'existe pour `source`, `rights`, `fresh`, `delay_status` ni `quality` : le worker ne publie que `categories`, `statuses` et le bloc `coverage` (/home/user/vertex-merge/apps/worker/src/vertex_worker/calendar.py:1109-1129), et l'API n'ajoute que `window.categories`/`window.statuses` (/home/user/vertex-merge/apps/api/src/vertex_api/calendar.py, `_counters`). Les trois recensements de ce module sont donc des dénombrements CLIENT sur `agenda[]` (comme aujourd'hui : /home/user/vertex-merge/apps/web/src/pages/catalysts/CatalystsModules.tsx:285-291 `censusOf(...)`). La conception rend pourtant bloquante une porte `served-count-over-local-recount` sur cette même planche : elle interdit ce que trois de ses propres modules servis font. | Choisir explicitement l'une des deux voies et l'écrire : (a) publier côté worker un recensement `coverage.sources`, `coverage.rights`, `coverage.delay_status` (changement de contrat versionné, à inscrire dans le lot), et le module devient un compteur servi ; ou (b) restreindre la porte `served-count-over-local-recount` aux grandeurs pour lesquelles un compteur servi EXISTE, et étiqueter ces trois recensements « dénombrement des lignes servies rendues, dans la fenêtre demandée », avec la portée écrite. Sans ce choix, le module et sa propre porte se contredisent. |

**Verdict : CORRECTIONS_REQUISES** — J'ai vérifié la conception contre le dépôt avant de juger : la plupart de ses affirmations factuelles sont exactes (le contrat `GET /api/v1/review-queue` est bien mort — catalystsModules.ts:34 — et le faux positif de couverture existe bien, `queueView?.theses ?? []` à CatalystsPage.tsx:293). Ce qu'elle réussit : aucun vocabulaire transactionnel réel, aucune lecture de compte, solde, NAV, P&L ou position courtier (les positions viennent du registre manuel — calendar.py:68 et :743), les deux `AbsentModule NO_SOURCE` refusent correctement de moyenner des rangs (loi 5), les vingt-trois textes d'absence ne contiennent aucun chiffre et ne suggèrent pas que la valeur existe ailleurs (loi 4), et le dominant exclut jauge circulaire, 3D, second axe de valeur et interpolation.

Dix-sept violations subsistent. Trois sont bloquantes. (1) `thesis-lanes` fabrique dans le navigateur une séquence de couloirs en concaténant deux ordonnancements servis distincts — `due[]` lexicographique et `theses[]` trié par identifiant — et la présente comme la hiérarchie d'urgence du visuel dominant : c'est un classement calculé côté TypeScript (loi 3). (2) `orphan-theses` croise deux instantanés d'`as_of` différents sans aucune garde de compatibilité temporelle et en tire une affirmation de couverture : une thèse créée après l'`as_of` de l'agenda devient mécaniquement orpheline (lois 3 et 7). (3) `portfolio-exposure` ne peut pas répondre à sa propre question : le contrat ne publie qu'un entier `portfolio_id` nu, sans libellé, ticker, quantité ni devise.

Trois violations de langue et de mesure sont tout aussi concrètes et vérifiées dans le code : la conception impose de relayer verbatim `ordering.method = "lexicographic"`, une note `ordering.note` entièrement ANGLAISE, des clés de tri mêlant nom de champ anglais et parenthèse française, et des descriptions de rangs d'importance en français désaccentué (« evenement macro global », « resultats d'un ticker … these declaree ») ; et `overdue_seconds` est figé à l'instant de l'instantané et plancherisé à zéro, mais affiché comme un retard courant sans nommer l'instant de mesure.

Viennent ensuite : la teinte seule porteuse de l'état de version contesté, avec collision non arbitrée entre violet (option) et rouge (conflit) sur la même marque ; trois lumières sur la carte dominante alors que la conception s'impose une lumière par carte ; une grille dont les rangées 1, 4 et 7 sont identiques — une périodicité exacte de 3 que l'auto-contrôle « jamais deux fois de suite » ne voit pas — et dont la carte d'aires contredit les spans annoncés ; une action principale (« Déclarer une thèse ») qui ne répond pas à la question de la page, doublée d'un vert réservé à une revue enregistrée qu'aucun module n'affiche ni ne permet ; le titre « Certitude des dates » qui porte un mot de confiance démenti seulement en pied ; quatre chaînes visibles employant « ordre / ordonnée / ordonne » ; cinq `DataTable` à défilement interne sans région focalisable ni parcours clavier déclaré ; un état d'absence de `new-thesis` qu'aucun signal servi ne permet de constater ; une portée de filtrage non déclarée ; le losange de base masqué qui confond « identique » et « non publié » ; et `window.applied` présumé vrai au lieu d'être lu.

Remarque hors loi, mais bloquante à l'implémentation : la conception écrit `Widget rank="dominant"` et `Widget rank="support"`, alors que `Widget` n'expose pas de prop `rank` — le vocabulaire de rang est `variant` sur `Widget` (Widget.tsx:56) et `rank` sur `Card`. Les deux écritures sont comptées par la porte `one-dominant-per-page`, il faut donc trancher laquelle porte le rang avant d'écrire la planche.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `thesis-lanes` | Loi 3 — Python est l'unique autorité de calcul ; le navigateur ne produit jamais un classement | apps/worker/src/vertex_worker/follow_up.py:103 et :359-360 — le worker publie DEUX séquences séparées et incompatibles : `due[]` trié par `due_sort_key` sur `DUE_ORDERING_KEYS` (`ordering.method = "lexicographic"`), et `theses[]` trié par `sorted(projected, key=lambda item: item.thesis.id)` (follow_up.py:285), c'est-à-dire un ordre de création. Aucun contrat ne publie la concaténation. La conception écrit pourtant « ordre des couloirs = content.due[].rank servi puis ordre publié de content.theses[] ». | Supprimer la fusion des deux séquences dans le navigateur. Soit `vertex_core`/le worker publie un bloc `lanes_ordering { method, version, keys[], lanes[] }` que la page relaie tel quel, soit les couloirs suivent UNE seule clé servie (`content.due[].rank` pour les thèses dues, et un second groupe explicitement nommé « thèses non dues, séquence de publication par identifiant » pour le reste, visuellement séparé et jamais lu comme une hiérarchie d'urgence). Interdire dans la légende toute formule laissant croire que le haut de la planche est le plus urgent si aucune clé servie ne le dit. |
| `orphan-theses` | Loi 3 (calcul autoritaire côté navigateur) et Loi 7 (as_of, méthode, version de toute valeur critique) | Aucun champ de couverture croisée n'existe dans les deux contrats : `apps/worker/src/vertex_worker/follow_up.py:369-379` (`coverage` de la file) ne publie aucun croisement avec l'agenda, et `apps/worker/src/vertex_worker/calendar.py:1115` (`coverage` de l'agenda) non plus. La conception fait donc la différence ensembliste dans le navigateur entre deux instantanés d'`as_of` DIFFÉRENTS, et ne pose qu'une garde de disponibilité (« état joint »), jamais de garde de compatibilité temporelle. | Refuser le croisement client. Soit le worker publie le résultat (une liste servie de thèses sans événement relié, avec sa propre méthode et sa version), soit la page exige que l'écart entre les deux `as_of` reste sous un budget SERVI et rend un état dégradé nommé au-delà. Dans tous les cas, afficher les deux `as_of` et l'écart dans la même phrase que le résultat, et écrire que la réponse vaut pour ce couple d'instantanés et pour aucun autre. |
| `portfolio-exposure` | Loi 7 (une valeur critique porte son identité et sa source) et Loi 4 (une identité non publiée n'est pas un identifiant technique affiché tel quel) | apps/worker/src/vertex_worker/calendar.py:743 — `"positions": [{"portfolio_id": pid} for pid in portfolio_ids]`. Le contrat ne publie QUE l'entier `portfolio_id` : ni libellé, ni ticker de position, ni quantité, ni devise. Or les colonnes déclarées par le module (« instant lisible, titre, catégorie, statut, importance ») décrivent toutes l'ÉVÉNEMENT. Le module ne peut donc pas répondre à sa propre question « Quelles positions du registre manuel sont touchées ». | Deux issues, pas de troisième : (a) ajouter au contrat d'agenda un libellé servi de position (`event_context.positions[].label` ou `.ticker`) et n'afficher le module qu'une fois ce champ publié ; (b) en attendant, reformuler la question en « Sur quels tickers servis un événement touche-t-il une position déclarée ? », utiliser `agenda[].ticker` comme identité affichée, et écrire sous la table que l'identité de la position n'est pas publiée par le contrat — jamais montrer un entier nu comme réponse à « quelle position ». |
| `review-queue` | Textes d'interface en français clair (règle de langue) + Loi 7 (méthode et version lisibles) | apps/worker/src/vertex_worker/follow_up.py:360 — `"method": "lexicographic"` ; :362-365 — `"note"` est une phrase entièrement ANGLAISE (« new information raises visible urgency (flag + reasons) but never rewrites the thesis, its revisions or its due instant ») ; :103-108 — `DUE_ORDERING_KEYS` mélange un nom de champ anglais et une parenthèse française (« effective_review_due_at asc (du depuis le plus longtemps d'abord) »). La conception impose d'afficher `ordering.method`, `ordering.note` et `ordering.keys[]` dans la légende de la table. | Ne rien relayer verbatim ici. Publier côté serveur, dans le contrat versionné, un libellé français accentué pour la méthode et la note (montée de version explicite), OU rendre côté page une table de correspondance VERSIONNÉE code → phrase française, en affichant le jeton machine dans `<code>` à côté de la phrase. Aucune phrase anglaise ni aucun nom de champ anglais ne doit apparaître comme prose visible. |
| `importance-legend` | Textes d'interface en français clair | apps/worker/src/vertex_worker/calendar.py:185-223 — `IMPORTANCE_RULE_RANKS[].description` est du français ASCII sans accents : « evenement macro global », « resultats d'un ticker avec position manuelle ou these declaree », « evenement macro non global (defensif) ». Le module impose « description relayée verbatim, jamais reformulée » et le pied répète « relayée verbatim ». | Corriger la source : publier les descriptions en français accentué sous une montée de `IMPORTANCE_RULE_VERSION` (le changement de texte est un changement de règle, il doit se voir dans la version). Tant que la source n'est pas corrigée, afficher le `code` servi dans `<code>` et une phrase française portée par une table de correspondance versionnée côté page, en nommant la version de règle qui la justifie — jamais du texte désaccentué présenté comme la définition officielle. |
| `due-pressure` | Loi 7 (as_of et méthode de la valeur elle-même) et Loi 4 (un zéro servi n'est pas une observation) | apps/worker/src/vertex_worker/follow_up.py:343 — `"overdue_seconds": max(0, int((now - effective_due).total_seconds()))`, où `now` est l'instant de construction de l'instantané, publié comme `as_of` (follow_up.py:~350). Le retard est donc figé à l'instant de l'instantané, et plancherisé à zéro. La conception le rend « en durée française (jours, heures) » sans jamais dire à quel instant il est mesuré : sur un instantané de vingt heures, le retard affiché est faux de vingt heures et se dégrade à l'écran. | Écrire la mesure avec son instant dans la même phrase : « retard mesuré à l'instant de l'instantané ({as_of}) », et ne JAMAIS recalculer depuis l'horloge du navigateur. Déclarer que `0` est un plancher servi, pas un retard nul observé. Si la valeur dépasse le budget de fraîcheur de la route, la carte porte l'état `stale` et le dit avant de montrer la durée. |
| `thesis-lanes` | Couleur seule porteuse d'information + collision de teintes non arbitrée | Table des canaux de la fiche, §2 : la FORME porte `status`, la TAILLE porte `importance.rank`, la TEINTE porte à la fois la catégorie (violet si expiration d'options) ET l'état de version (rouge si `CONFLICTING_VERSIONS`). Un état de version contesté n'a donc AUCUN canal autre que la teinte dans le graphique. De plus, `apps/worker/src/vertex_worker/calendar.py:1054-1065` publie `version_state` et `category` indépendamment : un événement d'expiration d'options en versions contestées reçoit deux teintes exclusives et la conception ne tranche pas. | Donner au conflit de version un canal non chromatique (contour épais + glyphe de conflit sur la marque), réserver la teinte à la seule catégorie, et déclarer explicitement la précédence quand catégorie et conflit coexistent. Répéter l'état en TEXTE dans la ligne correspondante de la table équivalente, et vérifier le contraste des trois teintes sur fond très profond. |
| `thesis-lanes` | Loi 6 (un visuel dominant) et règle d'accent déclarée par la conception elle-même : « une lumière dominante par carte » | Champ `accent` de la conception : « ambre — accent de page unique. Violet réservé aux événements de catégorie option, rouge aux versions contestées ». La carte dominante `thesis-lanes` porte donc ambre + violet + rouge simultanément, sur la carte même qui définit la hiérarchie de lecture de la page. La règle « une lumière dominante par carte » ne comporte aucune exemption au niveau CARTE (l'exemption rouge/vert ne porte que sur le compte par ÉCRAN). | Une seule lumière sur la carte dominante : l'ambre. Déplacer la distinction option/conflit sur la forme et le glyphe (cf. correction précédente), et sortir la lecture chromatique des catégories vers `category-split`, qui est un recensement HTML/CSS où une teinte par barre n'entre pas en concurrence avec la dominante. |
| `thesis-lanes` | Composition asymétrique exigée par le brief Titan Ledger (« bento tetris », surfaces franchement différentes) + cohérence interne de la grille | §3, bloc `grid-template-areas` : les rangées 1, 4 et 7 sont toutes `3 \| 3 \| 6` — une répétition de PÉRIODE EXACTEMENT 3 sur neuf rangées, avec seulement 5 formes distinctes (3\|3\|6 ×3, 6\|3\|3 ×2, 12 ×2, 3\|6\|3, 6\|6). Le contrôle que la conception s'impose (« aucune rangée répétée deux fois de suite ») ne détecte pas cette périodicité. Contradiction supplémentaire : le texte annonce « dominant sur trois unités, file de revue sur deux » alors que la carte d'aires ne donne qu'UNE ligne à `lanes` et une à `review`. | Réécrire la carte d'aires : aucune forme de rangée ne doit réapparaître à intervalle constant, et le nombre de lignes de la carte doit correspondre au span annoncé (trois lignes `lanes`, deux lignes `review`). Ajouter au test de composition une assertion sur la périodicité des formes de rangée, pas seulement sur la répétition immédiate. |
| `new-thesis` | Loi 6 (une seule action principale) + affordance et couleur déclarées sans support servi | La conception nomme `new-thesis` « action principale unique » alors que `PeriodTabs` (§7, §8.2) est une seconde action de niveau page qui re-demande les DEUX instantanés. Par ailleurs le champ `accent` réserve le vert à « une revue enregistrée servie », mais AUCUN module ne lit `content.theses[].state.last_reviewed_at` ni `.last_action` (tous deux publiés — apps/worker/src/vertex_worker/follow_up.py:315-317) et AUCUN module n'offre d'enregistrer une revue, alors que `POST /api/v1/theses/{thesis_id}/revisions` existe (apps/api/src/vertex_api/follow_up.py, `RevisionAction`). | Faire de l'enregistrement d'une revue l'action principale unique de la zone DÉCISION (contrat de révision déjà servi), et rétrograder « Déclarer une thèse » en action secondaire. Déclarer `PeriodTabs` comme contrôle de lecture de la page, pas comme action. Soit un module lit et affiche `state.last_reviewed_at` / `state.last_action` et le vert est justifié, soit la réservation du vert est supprimée du champ `accent`. |
| `date-certainty` | Loi 5 (une classification descriptive le DIT ; une formulation ambiguë est une violation) | Titre affiché « Certitude des dates » et question affichée « Combien d'événements servis portent une date confirmée et combien restent estimés ? ». « Certitude » est du vocabulaire de confiance. Le démenti (« descriptif d'un fait observé, jamais une probabilité ni une confiance ») n'existe QUE dans le pied de carte, sous le chiffre. | Renommer le module « Statut de date publié » et reformuler la question : « Combien d'événements servis portent le statut CONFIRMED et combien le statut ESTIMATED, tels que publiés par la source ? ». Le titre lui-même doit dire que le statut vient de la source ; ne jamais laisser un mot de confiance porter le titre et le démenti porter le pied. |
| `review-queue` | Loi 2 (vocabulaire d'ordre interdit à l'écran ; le doute vaut violation) | Quatre chaînes VISIBLES emploient le lexique interdit : question du module (« dans quel ordre publié »), pied du module (« ordre SERVI ({content.ordering.method}) »), texte d'absence (« aucune thèse ne peut être ordonnée pour la revue »), et texte d'absence de `weighting` (« le rang d'importance ordonne, il ne pondère pas »). Sur un écran alimenté par des données de marché IBKR, « ordre » est exactement le mot ambigu que la loi 2 proscrit. | Remplacer partout dans les textes visibles : « dans quelle séquence publiée », « séquence SERVIE ({méthode servie}) », « aucune thèse ne peut être mise en séquence pour la revue », « le rang d'importance range, il ne pondère pas ». Ajouter une porte de conception `no-order-vocabulary` qui échoue sur ordre/ordonner/acheter/vendre/buy/sell/order/exécuter dans toute chaîne rendue. |
| `portfolio-exposure` | Parcours clavier exigé par module (WCAG 2.1.1 — conteneur à défilement non focalisable) | §8 ne déclare de parcours clavier que pour `PeriodTabs`, `thesis-lanes`, `filters`, `review-queue`, `new-thesis` et l'inspecteur. Or CINQ modules montent une `DataTable` à « défilement interne borné » sans région focalisable déclarée : `portfolio-exposure`, `version-conflicts`, `queue-coverage`, `coverage-ledger`, `thesis-instruments`. Seul `review-queue` reçoit `role="region"` + `tabindex="0"` + `aria-label` (§8.6). | Faire porter la règle par la primitive : toute `DataTable` dont le contenu déborde monte `role="region"` + `tabindex="0"` + `aria-label` construit sur des valeurs servies, et le §8 énumère les cinq modules concernés dans l'ordre de tabulation. Ajouter un test qui échoue si une `DataTable` à défilement est rendue sans région focalisable. |
| `new-thesis` | Loi 4 (un état affiché doit correspondre à un fait observable) et Loi 7 (aucune valeur sans source ni as_of) | Le module déclare le texte d'absence « Le contrat de déclaration de thèse n'est pas joignable : aucune thèse ne peut être déclarée maintenant. » Sa donnée est `POST /api/v1/theses` (apps/api/src/vertex_api/follow_up.py) : une route d'ÉCRITURE, sans instantané, sans `as_of`, sans `state` et sans `freshness_policy`. Rien ne permet à la page de constater cette absence sans sonder la route. | Supprimer cet état d'absence. Le module reste disponible, et l'échec éventuel est rapporté à la SOUMISSION, à partir de la réponse serveur réelle (code d'erreur typé relayé verbatim). Si une indisponibilité doit être connue avant l'action, elle exige une capacité SERVIE et datée — sinon le module ne prétend rien. |
| `filters` | Loi 4 (une vue filtrée ne se présente jamais comme la population servie) | Le module ne nomme AUCUNE des surfaces qu'il masque. Il coexiste avec `thesis-lanes` (marques), `portfolio-exposure` (table) et les recensements servis `category-split` / `date-certainty` qui, eux, comptent l'agenda entier. Rien dans la conception ne lie visuellement le nombre de marques tracées au compte servi : une dominante à quatre marques peut s'afficher à côté d'un recensement annonçant quarante événements servis, sans phrase qui explique l'écart. | Nommer explicitement dans le pied de `filters` les surfaces filtrées, et imposer que chaque surface filtrée porte dans sa propre légende « n marques affichées sur {coverage.events_displayed} servies » dès qu'un filtre est actif. Les recensements servis restent inchangés et le disent (« compteurs servis, non affectés par le filtre d'affichage »). |
| `thesis-lanes` | Loi 4 (absent, égal et non publié sont trois états distincts) | §2 : « Losange creux — échéance de base — affiché seulement s'il diffère de l'effective ». Or `thesis.review_due_at` est NULLABLE : apps/worker/src/vertex_worker/follow_up.py:307 publie `_iso(entry.thesis.review_due_at)` et :144-147 (`due_sort_key`) retombe explicitement sur l'échéance effective « when the thesis has no base review_due_at ». Masquer le losange rend donc « base non publiée » indiscernable de « base identique à l'effective ». | Déclarer trois cas et les rendre distincts : base servie et différente (losange creux + écart écrit), base servie et identique (dit en légende, sans second losange), base NON PUBLIÉE (dit en légende, phrase d'absence, jamais un losange manquant silencieux). Même règle dans la table équivalente et dans `review-queue`, qui met les deux échéances en regard. |
| `window` | Loi 4 / Loi 7 (un champ servi ne se présume pas) | Le module affirme : « La page DEMANDE désormais une fenêtre […] : window.applied vaut vrai et la phrase « début non publié » disparaît. » Or `window.applied` est un champ SERVI (apps/api/openapi.json:1203 et suivants) et l'API publie des états indépendants `empty_window` et `degraded` (apps/api/openapi.json:1039). `EventLanes` prévoit d'ailleurs la branche contraire (« Fenêtre non appliquée : l'axe prend les bornes des instants servis et l'écrit ») — les deux spécifications se contredisent. | Conserver les deux branches dans `window` comme dans `EventLanes` : `window.applied` est lu, jamais présumé. Écrire la branche « fenêtre demandée non appliquée par le serveur » avec sa raison servie, et la branche `empty_window` distincte d'un agenda vide, exactement comme la conception l'exige déjà au §7. |

## 5. Primitives neuves exigées — 3

- **AgeMeter** — Poser un âge SERVI sur un budget SERVI, en une piste horizontale, pour un instantané daté. Remplace l'absence totale de lecture de age_seconds sur les deux endpoints. Ne remplace pas FreshnessBadge, qui dit l'état ; AgeMeter dit la distance au budget.. Donnée exigée : age_seconds (entier servi, nullable), freshness_policy.budget_seconds (entier servi), freshness_policy.kind (nom de politique servi), freshness_policy.version (version servie), state servi ('ok' | 'stale' | 'empty' ou le vocabulaire de la route). Les deux nombres sont écrits en texte, en durée française ; la géométrie est la seule opération, exactement comme censusWidths.. États : servi : piste tracée, âge et budget écrits, politique et version nommées. Budget servi sans instantané : piste tracée vide et phrase « aucun instantané publié », jamais un zéro. Âge servi supérieur au budget : la piste dépasse et le dépassement est écrit, mais le VERDICT reste celui du champ state servi — la primitive ne déclare jamais elle-même « périmé ». Aucun des deux servi : aucune piste, phrase d'absence. Interdit : déduire un pourcentage écrit, une couleur de verdict, une jauge circulaire.
- **DataTable** — LA table financière dense de l'identité Titan Ledger : caption obligatoire, chiffres tabulaires, colonnes typées, défilement interne borné, aucune troncature muette. Utilisée par la file de revue, les positions touchées, les versions contestées, les deux blocs de couverture et les thèses par instrument. Aucune primitive existante ne rend une table ; la seule table de l'espace aujourd'hui est une <table> nue sans caption.. Donnée exigée : columns[] { key, label, unit | null, align, nature: 'texte' | 'chiffre' | 'instant' | 'code' | 'duree' }, rows[] dans l'ORDRE SERVI (aucun tri client, en-têtes cliquables uniquement sur une clé d'ordre servie et alors la clé servie est nommée), caption (obligatoire), rowCount servi ou nombre de lignes servies, emptyLabel (obligatoire), truncationNote (obligatoire dès qu'une ligne servie n'est pas rendue).. États : servi : caption, lignes, comptes. Vide : emptyLabel en phrase, aucune ligne fantôme, aucun tiret. Cellule non publiée : span data-absent avec sa phrase, jamais un tiret ni un zéro. Tronqué : refuse de rendre sans truncationNote (erreur de développement en test). Instant : <time dateTime={ISO servi}> rendu en français lisible, l'ISO restant dans l'attribut. Durée : secondes servies rendues en jours et heures, jamais en secondes brutes. Code : <code> réservé aux valeurs machine servies, jamais à une phrase française.
- **EventLanes** — Le visuel dominant : un VRAI axe de temps. La « chronologie » actuelle est une liste ordonnée sans axe, sans échelle et sans densité temporelle. EventLanes donne à la page sa seule représentation temporelle et consomme d'un coup le rang d'importance, le statut de date, l'état de version, l'échéance de base et l'échéance effective.. Donnée exigée : lanes[] { id, label, orderKey servi } dans l'ordre SERVI (content.due[].rank puis ordre publié de content.theses[]) ; marks[] { laneId, instantUtc servi, status servi, importanceRank servi, category servie, versionState servi, eventId } ; refs[] { laneId, kind: 'base' | 'effective', instantUtc servi } ; asOfUtc servi ; bounds { fromUtc, toUtc, applied } servis ; rankLegend[] { rank, code, description } servi depuis importance_rule.ranks.. États : servi : axe borné par la fenêtre servie, couloirs dans l'ordre servi, légende des rangs avec leur description servie. Fenêtre non appliquée : l'axe prend les bornes des instants servis et l'écrit. Aucune marque : aucun axe tracé, phrase d'absence. Plus de couloirs que la hauteur : défilement vertical interne et nombre de couloirs tracés sur content.coverage.theses_total écrit — jamais de troncature muette. Accessibilité : role="img" avec aria-label servi, plus une table équivalente obligatoire dépliable par un bouton réel, dont chaque ligne porte le bouton d'ouverture de l'inspecteur. Interdit : interpolation, courbe de tendance, second axe de valeur, 3D, animation d'entrée sous prefers-reduced-motion.
