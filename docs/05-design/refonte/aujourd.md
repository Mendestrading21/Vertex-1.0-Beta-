# Dossier de refonte — Aujourd'hui

> Produit par l'audit-conception du 2026-09-04 : un auditeur a lu le code et les
> contrats, un concepteur a dessiné la page cible, puis **deux lentilles
> adversariales** ont tenté de la réfuter. Les réfutations sont reportées ici
> telles quelles : **ce dossier est une conception à corriger, pas une
> spécification approuvée.** Le lot qui l'implémente applique d'abord le §4.

## 1. Ce que l'audit a mesuré

L'espace Aujourd'hui compte 12 modules catalogués dans apps/web/src/pages/todayView.ts : 9 servis par un contrat nommé, 3 absents avec un motif NO_SOURCE mesuré (régime, volatilité, risques actifs) — plus un treizième bloc hors catalogue, SnapshotRail, qui occupe l'inspecteur par défaut. La page appelle 7 routes GET réellement, jusqu'à 11 requêtes avec les 4 dossiers d'analyse de la rangée « Instruments suivis ». Elle ne calcule aucune valeur financière : les seules opérations locales sont des dénombrements de drapeaux, la géométrie des tracés et une soustraction de deux horodatages serveur.

Le résultat central de l'audit est ailleurs : la page est riche en contrats et pauvre en affichage. Le point le plus lourd est POST /api/v1/advice/preview — l'unique autorité de verdict, avec ses gates chiffrées, ses observed_values, ses thresholds, ses limitations et sa date de validité — publié, validé, testé côté Python, et appelé par ZÉRO fichier de apps/web/src. Sur le contrat de la dominante elle-même, freshness_policy n'est lu nulle part (la file affiche donc un âge sans son échelle), age_seconds ne sert que dans les phrases d'état dégradé, et 9 des 14 clés de couverture publiées — dont la répartition exacte réel/généré et le compte de contradictions de polarité — sont exclues par la liste fermée de SnapshotRail.tsx:35-41. Plus en amont, le worker calcule puis le relais jette : priority_class (la raison même de l'ordre de la file), age_seconds, source_tier et quality par item, le tableau conflicts[] complet avec ses règles et ses rationales, le détail de chaque rejet (filtered_reason, failed_gates réduits à un simple entier), et les trois versions de méthode du snapshot. Conséquence directe et mesurable : le navigateur recalcule en Date.parse (AttentionQueue.tsx:43) un âge que le worker avait déjà produit. Sur les contrats empruntés, le gisement est du même ordre — data_state 'partial' ignoré alors que le ticker du shell le lit, synthetic par instrument jamais lu par SectorGrid ni InstrumentTile, poids sectoriels servis et non utilisés, primaryExclusionReason servi pendant que le module écrit « avec sa raison publiée » sans jamais l'afficher, health.attention_snapshot publié et invisible sur la page dont c'est la dominante.

Côté forme, la page porte encore une dette déclarée (AttentionQueue.tsx et SnapshotRail.tsx sont nommément dans DETTE_T4 du garde anti-tiret ambigu), une violation WCAG 1.4.1 nette (le marqueur d'absence n'a que sa couleur, faute de data-absent), un aria-labelledby cassé sur 2 des 3 modules absents, de la prose anglaise en canal <code> dans des cellules de 200 px sans overflow-wrap, deux règles CSS mortes, deux règles écrasées dont les commentaires affirment l'inverse de ce qui s'applique, et une dominante reléguée en troisième bande derrière une rangée pleine largeur de quatre tuiles à prix et sparkline. Enfin, la page déclare size et variant pour ses 12 modules — sous garde automatique — et aucun de ses rendus ne les lit : Aujourd'hui est la seule des planches composées à être restée sur Card et sur des grid-area écrites à la main, hors du socle Widget v2.

### 1.1 Champs servis et jamais affichés — 34 relevés

La matière gratuite : déjà calculée par Python, publiée par le contrat, et
jetée par l'interface.

- AttentionSnapshotResponse.freshness_policy {kind, budget_seconds, version} — publié dans TOUS les états (snapshot_views.py:1672 et 1692, schemas.py:191). AUCUN fichier de apps/web/src ne le lit : grep ne le trouve que dans api/schema.d.ts et test/fixtures.ts. La file affiche donc un âge (FreshnessBadge) sans jamais publier l'échelle qui le juge — c'est exactement le manque que le commentaire de freshness.py:109-118 dit avoir corrigé côté serveur. Ignoré par TodayPage.tsx et SnapshotRail.tsx.
- AttentionSnapshotResponse.age_seconds — lu UNIQUEMENT dans degradedDetailOf (TodayPage.tsx:84) pour composer une phrase d'état 'stale'/'delayed'. Dans l'état nominal 'ok' l'âge publié du snapshot dominant n'apparaît nulle part, et SnapshotRail.tsx ne le reçoit même pas en prop (SnapshotRailProps, SnapshotRail.tsx:15-22).
- coverage.synthetic_observations et coverage.non_synthetic_observations — publiés par le worker (handlers.py:727-728), relayés verbatim dans coverage (snapshot_views.py:1684), et EXCLUS de la liste fermée COVERAGE_FIELDS de SnapshotRail.tsx:35-41. La répartition exacte réel/généré des observations de la file n'atteint jamais l'écran.
- coverage.polarity_conflicts — publié (handlers.py:733), exclu de COVERAGE_FIELDS (SnapshotRail.tsx:35-41). Le nombre de contradictions de polarité détectées dans la fusion est servi et invisible.
- coverage.rejected, coverage.content_observations, coverage.non_content_observations, coverage.max_items, coverage.lookback_seconds, coverage.content_schema_prefixes — publiés (handlers.py:721-735), tous exclus de COVERAGE_FIELDS (SnapshotRail.tsx:35-41). Au total 9 des 14 clés de couverture publiées ne sont jamais affichées ; seules observations_considered, clusters, ranked, published_items et truncated_ranked le sont.
- AttentionItem.provenance.instrument_ref — servi (snapshot_views.py:1647) et rendu en <code> INERTE par AttentionQueue.tsx:215-219. La fiche produit docs/01-product/pages/01-today.md déclare pourtant « Action principale : ouvrir le dossier de l'élément prioritaire », et la route /analysis/{instrument} existe et est déjà liée ailleurs (TodayModules.tsx:291). L'action principale de la page n'est pas câblée alors que le champ qui la permet est publié.
- AttentionSnapshotResponse.snapshot_version, .population, .as_of, .coverage, .rejected_count — servis et affichés SEULEMENT tant qu'aucun item n'est ouvert : SideSheet remplace SnapshotInspector (AttentionQueue.tsx:317-321, fallbackInspector passé en TodayPage.tsx:191). La provenance de la file disparaît exactement au moment où l'on inspecte un de ses éléments.
- AttentionItem.relevance_reasons — le serveur tronque DÉJÀ à 3 (snapshot_views.py:1643 reasons[:3], et schemas.py:165 Field(max_length=3)) ; AttentionQueue.tsx:306 retranche .slice(0, 3) une seconde fois. Code mort qui masquerait un changement de contrat.
- WORKER → RELAIS, jeté avant le contrat : items[].priority_class (classe lexicographique 1..7, handlers.py:687 et relevance.py:245/327-340). C'est LA raison publiée de l'ordre de la file. _attention_item (snapshot_views.py:1629-1650) ne la lit pas et AttentionItem (schemas.py:151-167) ne la porte pas. La file dit « ordre publié par le worker » (TodayPage.tsx:182) sans jamais pouvoir dire pourquoi un item est en tête.
- WORKER → RELAIS, jeté : items[].age_seconds, items[].source_tier, items[].quality (handlers.py:689-691, depuis RelevanceSubscores, relevance.py:213-231). Conséquence directe : AttentionQueue.tsx:43-53 (snapshotAgeSeconds) RECALCULE dans le navigateur, par Date.parse, un âge que le worker avait déjà calculé et que le relais a jeté.
- WORKER → RELAIS, jeté : conflicts[] complet — kind, scope (INTRA_CLUSTER/CROSS_CLUSTER), cluster_id, member_event_ids, rule_id, rule_version, rationale, reversible (handlers.py:611-627, 712). build_attention_response (snapshot_views.py:1652-1700) ne lit pas content['conflicts']. Les contradictions nommées par le moteur ne quittent jamais la base.
- WORKER → RELAIS, jeté : rejected[] détaillé — item_id, filtered_reason, failed_gates (handlers.py:715-720). Le relais n'en garde que le compte (rejected_count=len(rejected_raw), snapshot_views.py:1698). Le « pourquoi » de chaque exclusion de la file est calculé, persisté, puis réduit à un entier.
- WORKER → RELAIS, jeté : schema_version, policy_version, fusion_ruleset_version du snapshot d'attention (handlers.py:706-710). La version de méthode de la dominante n'est pas publiable, alors que la loi 7 l'exige pour toute valeur critique.
- MarketsOverviewResponse.data_state ('ok' | 'partial' | 'stale') — servi, lu par ShellTicker.tsx:159 et par les pages Risques, JAMAIS par GlobalMarketModule ni SectorsModule (TodayModules.tsx:44 et 313 n'utilisent que moduleStateOf sur data.state). Un snapshot Marchés annoncé 'partial' s'affiche sur Aujourd'hui comme complet, pendant que le ticker du shell, lui, dit « partiel ».
- MarketsTicker.synthetic — publié par instrument (schema.d.ts, MarketsTicker). Grep : le mot 'synthetic' n'apparaît NI dans components/markets/SectorGrid.tsx NI dans components/widgets/InstrumentTile.tsx. Sur Aujourd'hui, un instrument généré affiche son prix en corps d'affichage et sa puce sectorielle avec exactement le même statut visuel qu'un instrument réel.
- MarketsTicker.weight_in_sector_pct, weight_global_pct, weight_in_sector, weight_global — servis en chaînes déjà rendues par le worker. SectorGrid.tsx dessine des puces de taille identique et ne lit aucun poids : la « carte sectorielle » ne porte aucune notion de taille alors que la pondération est servie prête à l'emploi.
- MarketsTicker.calculation (lignée : engine_version, input_hash, result_hash, method, status) — servi pour chaque instrument, lu par MarketsInspector.tsx:96 sur la page Marchés, jamais sur Aujourd'hui (ni SectorGrid.tsx ni InstrumentTile.tsx).
- MarketsCoverage.received, .lookback_seconds, .observations_considered, .discarded_tickers[] (ticker + raison), .rejected_records[] — servis ; TodayModules.tsx:82 n'imprime que covered/expected/discarded. Les tickers écartés et LEUR RAISON sont publiés et jamais montrés.
- MarketsOverviewResponse.age_seconds, .freshness_policy, .engine_version, .unit, .display_unit, .snapshot_version — servis ; le pied de GlobalMarketModule (TodayModules.tsx:57) n'écrit que as_of et population.
- MarketsBreadth.calculation, .value (valeur non-pct), .coverage_threshold (seuil non-pct), .covered_count/.universe_size (utilisés seulement en phrase) — BreadthPanel.tsx ne lit que value_pct, coverage_pct, coverage_threshold_pct, status, reason et les 3 comptes.
- CalendarEventView : importance.rank et importance.ruleVersion (calendarView.ts:166, 193-200) — seul importance.code est affiché (TodayModules.tsx:131). Le rang d'importance publié et la version de la règle qui le produit sont ignorés par les deux modules calendrier de la page.
- CalendarEventView : fresh, staleAfter, delayStatus, quality, source, rights, sourceEventId (calendarView.ts:179-185) — tous servis, aucun n'est lu par AgendaLine.tsx (qui n'utilise que eventTimeUtc, exchangeTimezone, ticker, title, status, synthetic) ni par NextCatalystModule. Le « catalyseur suivant » est affiché sans fraîcheur, sans qualité, sans droit et sans statut de retard.
- CalendarEventView : amount, currency, expiration, previousValues[], revised, revisions[], rejectedRevisions[], versionState, conflictingVersions[], context, category, scope, eventTimeLocal (calendarView.ts:158-190) — servis, aucun affiché sur Aujourd'hui. Le montant et la valeur précédente d'un événement macro sont exactement la matière qui rendrait le module « catalyseur » concret.
- CalendarResponse.categories, .statuses, .coverage, .importance_rule, .window, .age_seconds, .freshness_policy, .snapshot_version (schema.d.ts CalendarResponse) — servis ; NextCatalystModule n'imprime que snapshot_version et as_of, CalendarModule aucun des deux. De plus useCalendar(null) (decisionApi.ts:64, 93) ne demande AUCUNE fenêtre, alors que la fiche produit demande « la fenêtre des prochaines 24 heures » et que window.applied est servi pour l'attester.
- SystemHealth.attention_snapshot {present, version, as_of, age_seconds} — servi (schemas SnapshotHealth) et JAMAIS affiché : SourceHealthModule (TodayModules.tsx:162-199) ne lit que health.db.status et health.worker.*. C'est la santé du snapshot QUI ALIMENTE LA DOMINANTE de cette page même.
- SystemHealth.capabilities_snapshot {present, version, as_of, age_seconds} — servi, jamais lu par TodayModules.tsx.
- SystemCapabilitiesResponse.unknown_probed_capability_ids, .checked_at, .age_seconds, .freshness_policy — servis, jamais lus par SourceHealthModule. Une capacité sondée mais inconnue du manifeste est publiée et passe inaperçue.
- CapabilityStatusEntry.capability_id, .family, .declared_mode, .description, .reason, .tested_at — servis pour chaque entrée ; capabilityStatusCensus (todayView.ts:178-186) ne conserve QUE tested_status pour en faire un compte. La raison d'un statut dégradé et la date du test sont publiées et perdues avant l'écran.
- CandidateView.primaryExclusionReason {gateId, reasonCode} et .exclusion (opportunitiesView.ts:123-124) — servis et jetés par opportunitiesSummaryOf (todayView.ts:198-207). Le module écrit pourtant, mot pour mot, « chaque candidat est fermé par une gate, avec sa raison publiée » (TodayModules.tsx:274) puis n'affiche qu'un dénombrement de statuts : la promesse est faite avec un champ servi qu'on refuse de lire.
- CandidateView.rank, .sector, .gates[], .degradedGates, .missingEvidence, .requiredEvidence, .evidenceClusterIds, .scenarioIds, .scenariosStatus, .population (opportunitiesView.ts:108-124) — servis, tous jetés par opportunitiesSummaryOf (todayView.ts:198-207). barsStatus n'est lu que par focusView.ts:41 pour filtrer.
- AdviceView.adviceId, .asOf, .validUntil, .engineVersion (opportunitiesView.ts:127-138) — servis par candidat ; TodayModules.tsx:295 n'affiche que status, direction et horizon. La date de validité d'un avis et la version du moteur qui l'a produit ne sont jamais montrées sur la page décisionnelle.
- ValuationContentView.marks {status, reason, snapshotVersion, asOf, tickersMarked}, .lotMethod, .engineVersion, .valuedLots[], .excludedLots[] (portfolioView.ts:139-149) — servis, jetés par portfolioSummaryOf (todayView.ts:217-224). La source des marques de valorisation et le nombre de tickers réellement marqués sont publiés et invisibles.
- CurrencyBlockView.totalRealized, .realizedFees, .realizedStatus, .realizedReason, .herfindahl, .weights[], .unrealizedCalculation, .realizedCalculation, .concentrationCalculation (portfolioView.ts:101-118) — servis ; ManualPortfolioModule n'affiche que totalValue et totalUnrealized. Le Herfindahl et les poids de concentration sont calculés côté Python, servis, et jamais montrés.
- AdviceResult complet (routes.py:209-236) : gates[] avec observed_values/thresholds/evidence_ids/reason_code/version, status, direction, horizon, risk_summary, limitations[], explanation_facts[], probability_evidence, valid_until, engine_version, input_snapshot_id, supersedes. POST /api/v1/advice/preview est publié, validé, testé — et n'est appelé par AUCUN fichier de apps/web/src. L'intégralité du contrat de l'unique autorité de verdict est de la matière gratuite pour cet espace.

### 1.2 Défauts visibles dans le code — 16

- TIRET AMBIGU, dette officielle et non payée. AttentionQueue.tsx:57-67 (AbsentValue) et SnapshotRail.tsx:43-49 (AbsentCoverageValue) rendent « — » comme substitut de valeur. Les deux fichiers figurent nommément dans DETTE_T4 de src/design/no-ambiguous-dash.test.ts:145-146 (lot T4-7). Sur la dominante de la page, « cluster inconnu », « aucun événement membre publié », « as_of absent » et les 5 champs de couverture s'affichent tous comme le même cadratin muet.
- COULEUR SEULE PORTEUSE D'INFORMATION (WCAG 1.4.1). global.css:1196 donne à .vx-cell-absent un simple gris ; le souligné pointillé qui distingue le marqueur du contenu vit sur .vx-cell-absent[data-absent='true'] (global.css:1200-1211, dont le commentaire dit explicitement pourquoi). Or ni AttentionQueue.tsx:63 ni SnapshotRail.tsx:45 ne posent data-absent. Sur Aujourd'hui, l'absence se distingue par la seule couleur.
- TEXTE SERVEUR BRUT EN ANGLAIS À L'ÉCRAN, sur une interface française. Les relevance_reasons rendues en badges (AttentionQueue.tsx:306-310) sont les codes de vertex_core/fusion/relevance.py:122-132 : MANUAL_POSITION, SECURITY_OR_QUALITY_INCIDENT, RECENTLY_ANALYZED_INSTRUMENT, GLOBAL_MARKET_EVENT, FRESHNESS. Idem item.sources.join(', ') et item.rights.join(', ') (AttentionQueue.tsx:186-191, 296), les libellés de CensusBars (TodayModules.tsx:185-189 et 262-266) et la population imprimée telle quelle en pied (TodayModules.tsx:57).
- IDENTIFIANT TECHNIQUE PRÉSENTÉ COMME LIBELLÉ. TodayModules.tsx:170 écrit « Worker · {data.health.worker.method} », soit « Worker · heartbeat_proxy » à l'écran. Le champ est un constant du contrat (WorkerHealth.method), pas un texte d'interface.
- PROSE ANGLAISE DANS LE CANAL <code>, ET DÉBORDEMENT. reason est une phrase anglaise complète : freshness.py:56-60 (« snapshot older than its freshness budget: age {age} s for a budget of {budget} s ({policy}@{version} closed-session TTL); the worker published nothing newer ») et snapshot_views.py:215 (« no snapshot published »). ModuleStatus.tsx:24-29 l'enferme dans <code> pour les 5 modules quiet, et TodayPage.tsx:86-92 et 235-237 l'incrustent dans une phrase française. Dans une cellule S de ~200 px (grid-template-columns: repeat(4, minmax(0,1fr)), global.css:5775), une phrase de ~150 caractères en chasse fixe déborde : .vx-module-state (global.css:5527-5533) ne déclare ni overflow-wrap ni word-break, contrairement à .vx-inspector-lineage qui, lui, pose overflow-wrap: anywhere.
- aria-labelledby CASSÉ SUR LES MODULES ABSENTS. AbsentModule.tsx:70-73 construit id={`vx-absent-${reason}-${title}`}. aria-labelledby est une LISTE d'identifiants séparés par des espaces : pour « Régime de marché » et « Risques actifs », le navigateur cherche trois puis deux identifiants inexistants et la section role="status" se retrouve sans nom accessible. 2 des 3 modules absents de cette page sont concernés.
- RÈGLES CSS MORTES. .vx-today-layout (global.css:1357-1363, redéclarée 4205-4207 et 4882) et .vx-queue-summary (global.css:1351-1355) : grep sur tout apps/web/src (hors dist/) ne trouve aucun consommateur — la page utilise .vx-today-grid depuis LOT-A3.
- RÈGLE CSS SILENCIEUSEMENT ÉCRASÉE, ET SON COMMENTAIRE DEVENU FAUX. global.css:1529-1540 pose .vx-queue-item-meta { flex-wrap: nowrap; max-width: 58% } avec le commentaire « un badge relégué à la ligne double la hauteur de l'élément sans rien ajouter à la lecture ». global.css:5966-5970 pose .vx-today-primary .vx-queue-item-meta { flex-wrap: wrap; max-width: 50% } — plus spécifique, donc toujours gagnante sur la SEULE page qui rend la file (AttentionQueue n'est importée que par TodayPage.tsx:11). La règle de base et son intention sont mortes.
- ADAPTATION RESPONSIVE MORTE. Dans @media (max-width: 1279px), global.css:4209-4214 pose .vx-snapshot-rail { position: static; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)) }. global.css:5730-5734 repose .vx-snapshot-rail { display: flex; flex-direction: column } SANS media query et PLUS BAS dans la feuille : à spécificité égale, la dernière gagne partout. Le grid-template-columns du bloc laptop ne s'applique jamais.
- DOMINANTE NOYÉE PAR LA COMPOSITION. grid-template-areas (global.css:5776-5782) place la file — seule carte rank="dominant" — en TROISIÈME bande. Au-dessus d'elle, la bande 2 est occupée sur toute la largeur par « focus », qui rend 4 InstrumentTile portant chacune un prix en corps d'affichage, une pastille de variation colorée et une Sparkline. À sa gauche dans la même bande, le module « global-market » empile un ArcGauge, une LinearGauge et 3 barres de dénombrement. one-dominant-per-page.test.ts ne compte que les rank="dominant" littéraux par FICHIER (1 ici) et son propre docstring reconnaît cette limite : elle ne voit pas cette concurrence.
- LE CATALOGUE DE COMPOSITION EST DÉCLARÉ PUIS IGNORÉ. todayView.ts:22-25 déclare size (S/M/L/XL) et variant pour les 12 modules, et components/widgets/catalog.test.ts en fait une porte. Aucun rendu de la page ne les lit : ni TodayPage.tsx ni TodayModules.tsx ne passent module.size, contrairement à RiskModules.tsx:68/92 qui le passe à la primitive Widget. Le placement est réécrit à la main en grid-area dans global.css:5796-5807 — exactement la dérive que le docstring de catalog.test.ts:6-11 décrit. Aujourd'hui est encore sur Card, pas sur le socle Widget v2.
- PERTE DE LA PROVENANCE À L'OUVERTURE D'UN ITEM. AttentionQueue.tsx:317-321 : SideSheet REMPLACE le fallbackInspector. Version du snapshot, as_of, population, items rejetés et couverture (SnapshotRail) disparaissent précisément quand l'utilisateur inspecte un élément de ce snapshot.
- FAIL-OPEN SUR LA NATURE GÉNÉRÉE. TodayModules.tsx:364 ne pose le badge « MARQUES SYNTHÉTIQUES » que si markPopulation === 'SYNTHETIC'. Les autres natures générées du vocabulaire fermé (DEMO, SIMULATED, THEORETICAL) et une étiquette inconnue passent sans aucun marqueur — l'inverse exact de SyntheticBanner.tsx:104-118, propriétaire fail-closed de ce vocabulaire, utilisé seulement par le module attention (TodayPage.tsx:173).
- TITRE ANNONCÉ DEUX FOIS DANS L'INSPECTEUR. inspector.tsx:104-106 rend <h2>Inspecteur — {subject}</h2> avec subject = item.title (AttentionQueue.tsx:146), et AttentionQueue.tsx:149-151 ajoute immédiatement un <h3 className="vx-visually-hidden">{item.title}</h3> dont l'id (titleId) n'est référencé par rien.
- AUCUNE TABLE SUR LA PAGE — le grief « table sans caption » ne s'applique pas ici : SnapshotRail utilise <dl>, la file <ol>, les dénombrements <ul>. À noter comme point conforme, pas comme défaut.
- PUCES SECTORIELLES INERTES. SectorGrid est appelé sans onSelect (TodayModules.tsx:328) : les puces sont des <span> (SectorGrid.tsx:63-64). La carte sectorielle de la page décisionnelle n'ouvre rien, alors que la même primitive sait devenir sélectionnable sur Marchés.

### 1.3 Graphiques actuels

- Sparkline — SVG inline (components/markets/Sparkline.tsx, WIDTH 120 × LINE_HEIGHT 40) : ligne des 30 dernières clôtures + barres des 14 derniers volumes, 4 instances dans la rangée « Instruments suivis » (InstrumentTile.tsx:117-127). Géométrie seule, valeurs servies en chaînes.
- ArcGauge — SVG inline demi-arc (components/widgets/ArcGauge.tsx, RADIUS 70, ARC_PATH dérivé) : la breadth globale, dans le module « Marché global » (BreadthPanel.tsx:75-84). Forme admise par ADR-017 car la valeur est bornée, servie en pourcentage avec son statut ; refus explicite si status INVALID.
- LinearGauge — jauge linéaire + marqueur de seuil servi (components/widgets/LinearGauge.tsx) : couverture de la breadth avec « seuil exigé » (BreadthPanel.tsx:85-102).
- CensusBars — barres CSS de dénombrement (components/CensusBars.tsx), 3 instances sur la page : hausses/baisses/inchangés (BreadthPanel.tsx:42-55), statuts testés des capacités (TodayModules.tsx:184-193), statuts de gate des candidats (TodayModules.tsx:261-270). Choisi explicitement CONTRE l'anneau, aucun pourcentage n'étant publié.
- AUCUN moteur graphique lourd sur Aujourd'hui : ni ECharts 6.1.0 ni Lightweight Charts 5.2.1. Grep de charts/echartsLoader.ts et charts/lightweightChartsLoader.ts : les seuls consommateurs sont pages/markets/MarketMap.tsx, pages/simulator/PayoffChart.tsx, pages/portfolio/performance/MonthlyHeatmap.tsx et PerformanceChart.tsx, pages/analysis/CandleChart.tsx. La page ne charge donc aucun bundle de graphique.
- Aucune jauge circulaire ni anneau sur la page : le seul objet radial est le demi-arc ArcGauge, admis par ADR-017 sur une valeur bornée servie avec ses bornes.

### 1.4 Fichiers lus

- `/home/user/vertex-merge/apps/web/src/pages/todayView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/TodayPage.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/TodayModules.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/AttentionQueue.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/SnapshotRail.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/focusView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/todayView.test.ts`
- `/home/user/vertex-merge/apps/web/src/pages/TodayPage.test.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/InstrumentTile.tsx`
- `/home/user/vertex-merge/apps/web/src/components/markets/SectorGrid.tsx`
- `/home/user/vertex-merge/apps/web/src/components/markets/marketsView.ts`
- `/home/user/vertex-merge/apps/web/src/components/markets/Sparkline.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/markets/BreadthPanel.tsx`
- `/home/user/vertex-merge/apps/web/src/components/calendar/AgendaLine.tsx`
- `/home/user/vertex-merge/apps/web/src/components/CensusBars.tsx`
- `/home/user/vertex-merge/apps/web/src/components/Card.tsx`
- `/home/user/vertex-merge/apps/web/src/components/AbsentModule.tsx`
- `/home/user/vertex-merge/apps/web/src/components/ModuleStatus.tsx`
- `/home/user/vertex-merge/apps/web/src/components/moduleState.ts`
- `/home/user/vertex-merge/apps/web/src/components/FreshnessBadge.tsx`
- `/home/user/vertex-merge/apps/web/src/components/SyntheticBanner.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/ArcGauge.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/LinearGauge.tsx`
- `/home/user/vertex-merge/apps/web/src/shell/inspector.tsx`
- `/home/user/vertex-merge/apps/web/src/api/client.ts`
- `/home/user/vertex-merge/apps/web/src/api/hooks.ts`
- `/home/user/vertex-merge/apps/web/src/api/decisionApi.ts`
- `/home/user/vertex-merge/apps/web/src/api/schema.d.ts`
- `/home/user/vertex-merge/apps/web/src/pages/opportunities/opportunitiesView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/portfolio/portfolioView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/calendar/calendarView.ts`
- `/home/user/vertex-merge/apps/web/src/styles/global.css`
- `/home/user/vertex-merge/apps/web/src/design/one-dominant-per-page.test.ts`
- `/home/user/vertex-merge/apps/web/src/design/no-ambiguous-dash.test.ts`
- `/home/user/vertex-merge/apps/web/src/components/widgets/catalog.test.ts`
- `/home/user/vertex-merge/apps/api/src/vertex_api/routes.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/schemas.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/snapshot_views.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/freshness.py`
- `/home/user/vertex-merge/apps/worker/src/vertex_worker/handlers.py`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/fusion/relevance.py`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/`
- `/home/user/vertex-merge/docs/01-product/pages/01-today.md`

## 2. Question, point focal, accent

- **Question** : Qu'est-ce qui mérite réellement mon attention maintenant ?
- **Visuel dominant** : La file d'attention rendue en table ledger pleine largeur (bande 1, XL, `rank="dominant"`) — seule carte de la page à porter la tranche ambre, seule surface au-dessus de la ligne de flottaison à 1280 × 800, et seul module dont l'action ouvre un dossier.
- **Accent** : Ambre — mais PAS en teinte secondaire de page. ADR-017 rend `signal` (ambre) inéligible à `pageAccent` : l'ambre est la lumière de marque de la dominante. Aujourd'hui ne déclare donc AUCUN `data-page-accent` ; l'ambre reste réservé à la tranche `[data-rank='dominant']`, au kicker de la dominante, à l'action principale, à l'instrument actif et aux états de prudence (retard, périmé, généré). Vert et rouge restent au signe financier SERVI (`return_1d`, `total_unrealized`) ; violet et cyan sont absents de cette page, qui n'a ni domaine options ni série technique.

## 3. Conception proposée

# Page 01 — Aujourd'hui `/today` — fiche de conception Titan Ledger

## 1. Question de la page

**Qu'est-ce qui mérite réellement mon attention maintenant ?**

Une seule question, une seule action principale : **ouvrir le dossier de l'élément
prioritaire** (`/analysis/{provenance.instrument_ref}`). Toutes les autres
interactions sont des liens de tête de module (« Toutes les sources », « Tous les
candidats », « Agenda complet ») ou l'ouverture d'une puce sectorielle ; aucune
n'est présentée comme l'action de la page.

## 2. Visuel dominant

**La file d'attention en table ledger pleine largeur**, bande 1, taille XL,
`rank="dominant"`, seule carte de la page à porter la tranche ambre.

Trois décisions la protègent :

1. elle passe **en première bande**. Aujourd'hui elle est en troisième, derrière
   une rangée pleine largeur de quatre tuiles à prix en corps d'affichage et
   sparkline : la dominante était noyée par des modules de soutien ;
2. la rangée « Instruments suivis » descend en **PREUVE, taille M**, et ses
   tuiles perdent le corps d'affichage — un prix de soutien s'écrit en corps de
   texte ;
3. le seul objet radial de la page, le demi-arc de largeur de marché, vit dans un
   module de soutien de la bande 2, sous la dominante et jamais à côté d'elle.

`one-dominant-per-page.test.ts` compte les `rank="dominant"` littéraux par
fichier ; son propre docstring reconnaît qu'il ne voit pas la concurrence de
composition. La règle est donc tenue **par la composition**, pas par la porte :
une seule bande pleine largeur avant la ligne de flottaison.

## 3. Accent

**Ambre — et aucune teinte secondaire de page.**

ADR-017 rend `signal` (ambre) **inéligible** à `pageAccent` : l'ambre est la
lumière de marque de la dominante, pas une teinte d'écran. Aujourd'hui ne pose
donc **aucun `data-page-accent`**.

| Rôle | Teinte | Où exactement |
|---|---|---|
| Lumière de marque | ambre `signal` | tranche `[data-rank='dominant']::before`, kicker de la dominante, action principale, ligne active de la table, instrument suivi ouvert |
| Prudence, retard, périmé, généré | ambre `warning` | `FreshnessBadge`, `StatusChip` de nature, bandeau `SyntheticBanner`, états `partial`/`delayed`/`stale` |
| Signe financier servi | vert / rouge | `KpiDelta`, `return_1d`, `total_unrealized`, puces sectorielles — **uniquement** sur un signe publié |
| Neutre | titane / argent | tout le reste, rails de barres, bordures presque invisibles |

Violet (options) et cyan (technique) sont **absents** : cette page n'a ni domaine
options ni série technique. Une lumière dominante par carte, deux par écran hors
rouge/vert.

## 4. Grille et bandes

Socle : `.vx-board` du widget v2 (aucune surface redéclarée), avec une variante
de page.

```css
.vx-board--today { grid-template-columns: repeat(12, minmax(0, 1fr)); }
.vx-board--today > [data-size='S']  { grid-column: span 3; }
.vx-board--today > [data-size='M']  { grid-column: span 6; }
.vx-board--today > [data-size='L']  { grid-column: span 8; }
.vx-board--today > [data-size='XL'] { grid-column: span 12; }

/* Deux bandes franchement asymétriques : L(8) + S aligné au bord droit.
   La colonne 9 reste vide — c'est la respiration du bento, jamais une carte
   manquante ni un module absent qu'on aurait retiré. */
.vx-board--today > [data-module='manual-portfolio'],
.vx-board--today > [data-module='opportunities'] { grid-column: 10 / span 3; }
```

`data-size` et `data-module` viennent **du catalogue** `TODAY_MODULES`, comme sur
Risques. Aucun `grid-area` écrit à la main, aucune classe `.vx-today-*` : la
place d'un module est une donnée du catalogue, pas une ligne de feuille de style.

| Bande | Zone | Composition | Modules |
|---|---|---|---|
| 1 | SIGNAL | `12` | `attention` |
| 2 | SIGNAL | `6 + 3 + 3` | `market-pulse` · `regime` · `volatility` |
| 3 | PREUVE | `8 + [9 vide] + 3` | `sectors` · `manual-portfolio` |
| 4 | PREUVE | `6 + 3 + 3` | `focus` · `snapshot-provenance` · `coverage` |
| 5 | PREUVE | `6 + 3 + 3` | `calendar` · `next-catalyst` · `nature-census` |
| 6 | RISQUE | `6 + 3 + 3` | `conflicts` · `rejected` · `attention-order` |
| 7 | RISQUE | `6 + 3 + 3` | `source-health` · `active-risks` · `discarded-tickers` |
| 8 | DÉCISION | `8 + [9 vide] + 3` | `decision-gates` · `opportunities` |

Cibles desktop **1280 × 800, 1440 × 900, 1600 × 1000** : les mêmes douze
colonnes et les mêmes spans aux trois largeurs ; seuls la gouttière et le
rembourrage respirent à 1600. À 1280 × 800, la bande 1 et le haut de la bande 2
sont au-dessus de la ligne de flottaison. Pas de rendu téléphone : `LATER`.

À ≤ 1279 px (hors cible, conservé pour ne pas casser la page) : `S → span 6`,
`M/L/XL → span 12`, l'ordre de lecture inchangé, la dominante toujours première.
**Une seule règle par sélecteur** : le défaut actuel — un bloc `@media` laptop
écrasé plus bas par une règle sans media query — est supprimé, pas contourné.

## 5. Modules

Vingt modules : **quatorze servis** (contre neuf aujourd'hui), **six absents**
avec leur motif et leur lot. La table défile horizontalement dans son conteneur.

| id | titre | question | taille | widget | graphique | donnée | servi | lot bloquant |
|---|---|---|---|---|---|---|---|---|
| `attention` | File d'attention | Qu'est-ce qui mérite réellement mon attention maintenant ? | XL (dominant) | Widget + **LedgerTable** + StatusChip + FreshnessBadge + AbsentCell + SyntheticBanner | table ledger, aucun moteur | `today/attention → items[].{id, title, sources, rights, relevance_reasons, synthetic, provenance.*}` | oui | — |
| `market-pulse` | Pouls du marché | Le marché couvert progresse-t-il, et sur quelle largeur de l'univers déclaré ? | M | Widget + ArcGauge + LinearGauge + CensusBars + StatusChip | demi-arc gradué + jauge à seuil + barres sur rail, SVG interne | `markets/overview → breadth.*, data_state, conclusion, unit, display_unit, engine_version` | oui | — |
| `regime` | Régime de marché | Dans quel régime observé le marché évolue-t-il, et avec quelle participation ? | S | AbsentModule | — | aucun champ | **non** | LOT 9 |
| `volatility` | Volatilité | La volatilité réalisée du marché couvert est-elle élevée ? | S | AbsentModule | — | aucun champ | **non** | LOT 9 |
| `sectors` | Carte sectorielle | Quels secteurs portent la séance, et quel poids chaque instrument y pèse-t-il ? | L | Widget + SectorGrid étendu + StatusChip | puces dimensionnées par un pourcentage servi, CSS | `markets/overview → sectors[].tickers[].{weight_in_sector_pct, weight_global_pct, return_1d_pct, synthetic, quality, calculation}` | oui | — |
| `manual-portfolio` | Portefeuille déclaré | Que vaut le portefeuille déclaré aux marques publiées, et d'où viennent ces marques ? | S | Widget + KpiTile + KpiDelta + SyntheticBanner + ProvenanceLine | aucun | `portfolio → valuation.content.{marks.*, lot_method, engine_version, coverage.*, positions_by_currency[].*}` | oui | — |
| `focus` | Instruments suivis | Que font les instruments dont un dossier d'analyse est publié ? | M (rail) | Widget + InstrumentTile ×4 + Sparkline | sparkline SVG interne (ligne + micro-barres de volume) | `analysis/{instrument}.bars` + `markets/overview → tickers[].{last_close, return_1d_pct, quality, synthetic, calculation}` | oui | — |
| `snapshot-provenance` | Provenance de la file | D'où vient la file affichée, et contre quel budget son âge est-il jugé ? | S | Widget + ProvenanceLine + Metric + FreshnessBadge + AbsentCell | aucun (jauge âge/budget **refusée**) | `today/attention → snapshot_version, as_of, age_seconds, freshness_policy.{kind, budget_seconds, version}, population, rejected_count` | oui | — |
| `coverage` | Couverture de la file | Combien d'observations la file a-t-elle considérées, groupées, classées puis publiées ? | S | Widget + CensusBars + `<dl>` + AbsentCell | barres de dénombrement sur rail | `today/attention → coverage.*` (les **douze** clés relayées + clé inconnue rendue visible) | oui | — |
| `calendar` | Agenda des prochaines heures | Quels événements publiés arrivent dans la fenêtre réellement appliquée par le serveur ? | M | Widget + ActivityFeed + StatusChip | journal groupé par jour servi | `calendar?from&to → agenda[].*, window.applied, importance_rule, categories, statuses, coverage` | oui | — |
| `next-catalyst` | Prochain catalyseur | Quel est le premier événement publié de la fenêtre, et dans quel état arrive-t-il ? | S | Widget + KpiTile + StatusChip + Metric | aucun | `calendar → agenda[0].{importance.rank, importance.rule_version, amount, currency, previous_values[0], fresh, delay_status, quality, source, rights}` | oui | — |
| `nature-census` | Réel ou généré | Combien d'observations de la file sont générées, et combien sont observées ? | S | Widget + CensusBars + SyntheticBanner | deux barres de dénombrement | `today/attention → coverage.{synthetic_observations, non_synthetic_observations}, population` | oui | — |
| `conflicts` | Contradictions nommées | Quelles contradictions de polarité la fusion a-t-elle détectées, et sur quels événements ? | M | AbsentModule (→ Widget + LedgerTable) | — | `conflicts[].{kind, scope, cluster_id, member_event_ids, rule_id, rule_version, rationale, reversible}` non publiés | **non** | LOT 13 |
| `rejected` | Exclusions de la file | Pourquoi chaque élément écarté n'entre-t-il pas dans la file ? | S | AbsentModule (→ Widget + LedgerTable) | — | `rejected[].{item_id, filtered_reason, failed_gates}` non publiés | **non** | LOT 13 |
| `attention-order` | Ordre de la file | Pourquoi un élément de la file passe-t-il devant un autre ? | S | AbsentModule (→ Widget + CensusBars) | — | `items[].{priority_class, source_tier, age_seconds, quality}` non publiés | **non** | LOT 13 |
| `source-health` | Santé des sources | Les sources sont-elles testées, autorisées, et l'instantané qui alimente cette page est-il vivant ? | M | Widget + CensusBars + StepList + StatusChip + AbsentCell | barres de dénombrement + liste d'étapes | `system/capabilities → capabilities[].{family, declared_mode, tested_status, tested_at, reason}, unknown_probed_capability_ids, health.{db, attention_snapshot, capabilities_snapshot, worker}` | oui | — |
| `active-risks` | Risques actifs | Quels risques nommés pèsent sur le contexte, et à quelle intensité ? | S | AbsentModule | — | aucun champ | **non** | LOT 12 |
| `discarded-tickers` | Instruments écartés | Quels instruments de l'univers sont sortis de l'instantané de marché, et pour quel motif ? | S | Widget + **LedgerTable** (2 colonnes) + StatusChip | table ledger dense | `markets/overview → coverage.{discarded_tickers[].{ticker, reason}, rejected_records[], expected, received, covered, discarded}` | oui | — |
| `decision-gates` | Verdict décomposé | Quelles portes le moteur a-t-il fermées sur l'instrument en tête de file, et sur quelles valeurs observées ? | L | Widget + StepList (StepEvidence) + StatusChip + ProvenanceLine | aucun | `analysis/{instrument} → advice.{status, direction, horizon, valid_until, engine_version, input_snapshot_id, risk_summary, gates[].{gate_id, version, status, reason_code, message, observed_values, thresholds}, limitations[], explanation_facts[]}` | oui | — |
| `opportunities` | Candidats et portes | Combien de candidats passent les portes, et quelle porte ferme chacun des autres ? | S | Widget + CensusBars + StepList + StatusChip | barres de dénombrement | `opportunities → coverage.*, ordering.method, candidates.qualified[].{ticker, rank, sector, advice.*}, candidates.excluded[].primary_exclusion_reason.{gate_id, reason_code}` | oui | — |

### Colonnes de la table dominante

| Colonne | Source | Nature d'absence | Note |
|---|---|---|---|
| Élément | `items[].title` — `<th scope="row">` portant le `<button>` d'ouverture | `not_published` | l'action principale de la page |
| Instrument | `provenance.instrument_ref` | `not_applicable` | un élément de portée marché n'a pas d'instrument ; il n'est pas ouvrable et son titre n'est pas un bouton |
| Nature | `items[].synthetic` + `population` | `not_recognised` | vocabulaire fermé de `SyntheticBanner`, fail-closed |
| Âge au snapshot | `as_of` − `provenance.first_published_at` (deux horodatages serveur) | `not_published` | à remplacer par `items[].age_seconds` dès le LOT 13 ; le pied nomme le lot |
| Sources | `items[].sources[]` | `not_published` | libellé français + code serveur en pastille |
| Droits | `items[].rights[]` | `not_published` | idem |
| Raisons de pertinence | `items[].relevance_reasons[]` (le serveur tronque déjà à trois — le `.slice(0, 3)` du client est **supprimé**, c'était du code mort qui masquerait un changement de contrat) | `not_published` | libellé français + code serveur |
| Rang publié | `items[].priority_class` | `not_published` | colonne **conservée**, cellules « non publié », lot LOT 13 nommé au pied |

### Traduction des codes serveur

Le code reste affiché **verbatim** en pastille : il est la preuve. Le français le
précède, il ne le remplace jamais. Cette page est en français ; aujourd'hui elle
affiche `MANUAL_POSITION`, `heartbeat_proxy` et des phrases anglaises complètes
dans un canal `<code>`.

| Code servi | Libellé affiché |
|---|---|
| `SECURITY_OR_QUALITY_INCIDENT` | incident de sécurité ou de qualité |
| `MANUAL_POSITION` | position déclarée |
| `ACTIVE_THESIS_OR_ALERT` | thèse ou alerte active |
| `WATCHLIST` | liste de suivi |
| `RECENTLY_ANALYZED_INSTRUMENT` | instrument analysé récemment |
| `GLOBAL_MARKET_EVENT` | événement de portée marché |
| `NOVELTY` | nouveauté |
| `FRESHNESS` | fraîcheur |
| `heartbeat_proxy` | vivacité établie par l'âge du plus frais instantané — aucun battement direct n'est observé |

Le champ `reason` du serveur est une **phrase anglaise complète**. Elle n'entre
plus dans `<code>` : elle est rendue en texte dans `stateDetail`, avec
`overflow-wrap: anywhere` sur `.vx-module-state`. Seul le **code** d'un motif
reste en `<code>`.

## 6. Nouvelle primitive exigée

Une seule.

### `LedgerTable`

**Rôle.** La table financière dense de l'identité Titan Ledger. `<caption>`
obligatoire, `<thead>` à `scope="col"`, chiffres tabulaires
(`font-variant-numeric: tabular-nums`), rail neutre derrière les lignes,
défilement **dans son propre conteneur** (la page ne défile jamais
horizontalement), une action réelle par ligne rendue en `<button>` dans le
`<th scope="row">`, une cellule d'absence **typée par colonne**.

**Ce qu'elle refuse.** Elle ne trie jamais — l'ordre est l'ordre servi, et le
pied le dit. Elle ne totalise pas, ne dérive aucune colonne, n'abrège aucun
nombre (« 12.4K » est interdit) et n'écrit aucun rang calculé.

**Donnée exigée.** Des lignes servies dans l'ordre publié. Chaque **colonne**
déclare son libellé français, son code serveur, son unité s'il y en a une, et la
nature d'absence de ses cellules dans le vocabulaire fermé de `absence.tsx`
(`not_published`, `not_computed`, `not_applicable`, `not_entered`,
`not_recognised`). Chaque **ligne** déclare un identifiant servi, sa nature
servie et, si elle est ouvrable, la cible servie de son action.

**États.** Les onze `ModuleState`. `loading` : squelette **par lignes**, sans
chiffre ni cadratin. `empty` : la phrase déclarée, aucune ligne fantôme. Cellule
sans valeur : `AbsentCell` avec `data-absent="true"`. Ligne générée :
`data-population` + pastille de nature ; nature inconnue → avertissement, jamais
silence. Colonne non encore publiée : en-tête conservé, cellules « non publié »,
lot nommé au pied. Ligne sans action servie : titre en texte, jamais un bouton
mort.

**Consommateurs.** `attention` (dominante), `discarded-tickers`, et `rejected`
au branchement du LOT 13.

Aucune autre primitive n'est créée : `SectorGrid` est **étendu** (largeur de puce
par pourcentage servi, `data-synthetic`, `onSelect`), tout le reste réutilise
Widget, KpiTile, KpiDelta, Metric, CensusBars, StepList, StatusChip,
ProvenanceLine, FreshnessBadge, InstrumentTile, ArcGauge, LinearGauge,
ActivityFeed, AbsentModule, AbsentCell, SyntheticBanner, DataStateBoundary.

## 7. Textes d'absence

Aucun chiffre. Aucune promesse de date. Aucune suggestion que la valeur serait
disponible ailleurs.

| Module | Texte exact |
|---|---|
| `regime` | Aucune source ne publie de régime de marché, et aucun calcul de régime n'existe au registre : ce module tient sa place sans rien affirmer. |
| `volatility` | Aucun instantané ne publie de volatilité réalisée ni d'indice de volatilité : rien ne la collecte aujourd'hui. |
| `active-risks` | Aucune source ne nomme un risque actif ni son intensité : rien n'est publié qui permette de désigner ce qui pèse sur le contexte. |
| `conflicts` | Le contrat de la file ne publie aucune contradiction nommée : ni la règle qui l'aurait détectée, ni les événements qu'elle opposerait. |
| `rejected` | Le contrat de la file ne publie aucune raison d'exclusion : une exclusion arrive sans motif et sans porte fermée. |
| `attention-order` | Le contrat de la file ne publie aucune classe de priorité : rien n'explique pourquoi un élément passe devant un autre. |
| `attention` (vide) | Aucun instantané d'attention n'est publié : rien n'a été classé, et rien n'est affiché à la place. |
| `attention` (publié, sans élément) | Rien ne demande votre attention dans l'instantané publié. |
| `market-pulse` (refus) | La largeur du marché n'est pas calculable : le moteur refuse de la publier et donne sa raison ; aucun arc, aucun repère et aucune valeur ne sont dessinés à sa place. |
| `sectors` | Aucun secteur n'est couvert dans l'instantané publié : la carte reste vide et ne dessine aucune puce. |
| `manual-portfolio` | Aucun lot n'est déclaré ou aucun n'a pu être marqué : le moteur publie son refus et sa raison, aucune valeur n'est composée à la place. |
| `focus` | Aucun dossier d'analyse n'est publié : il n'y a aucun instrument suivi à montrer. |
| `snapshot-provenance` | Aucun instantané d'attention n'est publié : il n'y a ni version, ni horodatage, ni budget de fraîcheur à montrer. |
| `coverage` | La couverture n'est pas publiée avec cet instantané : aucun dénombrement n'est relayé, et aucun n'est reconstitué. |
| `calendar` | Aucun événement n'est publié dans la fenêtre appliquée par le serveur : l'agenda est vide, et aucune ligne n'est inventée pour le remplir. |
| `next-catalyst` | Aucun événement n'ouvre la fenêtre appliquée : il n'y a pas de prochain catalyseur à nommer. |
| `nature-census` | La nature des observations n'est pas publiée avec cet instantané : la répartition entre observé et généré ne peut pas être affirmée. |
| `source-health` | Aucune capacité n'est déclarée au manifeste : il n'y a ni statut testé ni famille à recenser. |
| `discarded-tickers` | Aucun instrument n'a été écarté dans cet instantané : la table reste vide et ne remplace aucune ligne. |
| `decision-gates` | Aucun élément de la file ne désigne d'instrument, ou aucun dossier d'analyse n'est publié pour lui : il n'y a pas de verdict à décomposer. |
| `opportunities` | Aucun candidat n'est publié dans cet instantané : ni qualifié, ni exclu — il n'y a rien à recenser. |

**Cellule absente**, partout : `AbsentCell` avec `quoi` nommé, sa nature et
`data-absent="true"`. Le cadratin nu disparaît de la page ;
`AttentionQueue.tsx` et `SnapshotRail.tsx` sortent de `DETTE_T4` **parce qu'ils
n'existent plus** — la file devient `LedgerTable`, le rail devient le module
`snapshot-provenance`.

## 8. Ce que cette conception récupère

Chaque ligne est un champ **déjà servi par Python** et jeté par l'écran
aujourd'hui.

| Champ servi et invisible | Devient |
|---|---|
| `freshness_policy.{kind, budget_seconds, version}` | `snapshot-provenance` — l'âge cesse d'être affiché sans son échelle |
| `age_seconds` en état nominal | `snapshot-provenance` (aujourd'hui : seulement dans une phrase d'état dégradé) |
| 9 des 14 clés de couverture, dont `synthetic_observations`, `non_synthetic_observations`, `polarity_conflicts`, `rejected`, `max_items`, `lookback_seconds` | `coverage` + `nature-census` |
| `provenance.instrument_ref` rendu en `<code>` inerte | l'**action principale** de la page |
| provenance du snapshot perdue à l'ouverture d'un élément | `snapshot-provenance`, module permanent — l'inspecteur ne porte plus que le détail de l'élément |
| `advice.gates[].{observed_values, thresholds, reason_code, version}`, `limitations`, `valid_until`, `engine_version` | `decision-gates` |
| `MarketsOverviewResponse.data_state` | état de `market-pulse`, `sectors`, `discarded-tickers` — un instantané `partial` ne se lira plus « complet » pendant que le ticker du shell dit « partiel » |
| `MarketsTicker.synthetic` | pastille de nature sur chaque puce et chaque tuile |
| `weight_in_sector_pct`, `weight_global_pct` | largeur des puces sectorielles |
| `MarketsTicker.calculation` (lignée) | pied de `focus` et de `sectors` |
| `coverage.discarded_tickers[]` + `rejected_records[]` | `discarded-tickers` |
| `breadth.calculation`, `value`, `coverage_threshold`, `conclusion`, `engine_version`, `unit`, `display_unit` | `market-pulse` |
| `importance.rank`, `importance.rule_version`, `amount`, `currency`, `previous_values[]`, `fresh`, `stale_after`, `delay_status`, `quality`, `source`, `rights` | `next-catalyst` et `calendar` |
| `CalendarResponse.window.applied`, `categories`, `statuses`, `coverage`, `importance_rule` | `calendar` — et la fenêtre est enfin **demandée** |
| `health.attention_snapshot`, `health.capabilities_snapshot`, `unknown_probed_capability_ids`, `capabilities[].{reason, tested_at, family, declared_mode}` | `source-health` |
| `primary_exclusion_reason.{gate_id, reason_code}`, `rank`, `sector`, `advice.valid_until`, `advice.engine_version` | `opportunities` — la promesse « avec sa raison publiée » est enfin tenue |
| `marks.{status, reason, snapshot_version, as_of, tickers_marked}`, `lot_method`, `engine_version` | `manual-portfolio` |

**Fenêtre du calendrier.** `useCalendar` reçoit désormais
`{from: attention.as_of, to: as_of + PT24H}` : la fenêtre est ancrée sur un
**instant servi**, jamais sur l'horloge du navigateur. L'addition ne sert qu'à
**former la requête** ; ce qui est **affiché** est `window.applied`, verbatim. Si
`as_of` est nul, aucune fenêtre n'est transmise et le module affiche la fenêtre
par défaut appliquée par le serveur.

**Deux refus explicites, à ne pas défaire.**

1. **`POST /api/v1/advice/preview` n'est pas appelé.** Cette route exige que
   l'appelant compose lui-même les entrées certifiées des portes : le navigateur
   deviendrait l'**auteur des entrées** de l'unique autorité de verdict. Le même
   `AdviceResult` est servi en lecture par `GET /api/v1/analysis/{instrument}`,
   avec ses `observed_values` et ses `thresholds` — c'est cette route que
   `decision-gates` consomme.
2. **Aucune jauge âge/budget.** `age_seconds` et `budget_seconds` sont servis,
   mais la **position en pourcentage** ne l'est pas. La dériver serait un ratio
   calculé dans le navigateur (ADR-017 exige des coordonnées serveur). Les deux
   grandeurs sont écrites en clair.
3. **Herfindahl et poids de concentration ne montent pas ici.** Ils sont servis,
   mais ils répondent à la question de Risques et de Portefeuille. Une page, une
   question.

**Aucun moteur graphique n'est chargé sur cette page.** Ni ECharts 6.1.0, ni
Lightweight Charts 5.2.1. Toutes les formes — demi-arc, jauge linéaire, barres
sur rail, sparkline, table ledger — sont SVG ou CSS internes, rendues dans
l'environnement de test et porteuses de leur table équivalente. C'est un budget
de performance tenu, pas un manque.

## 9. Contrats appelés

| Route | Appels | Modules |
|---|---|---|
| `GET /api/v1/today/attention` | 1 | `attention`, `snapshot-provenance`, `coverage`, `nature-census` |
| `GET /api/v1/markets/overview` | 1 (dédoublonné par la clé React Query) | `market-pulse`, `sectors`, `focus`, `discarded-tickers` |
| `GET /api/v1/calendar?from&to` | 1 | `calendar`, `next-catalyst` |
| `GET /api/v1/system/capabilities` | 1 | `source-health` |
| `GET /api/v1/opportunities` | 1 | `opportunities`, sélection de `focus` |
| `GET /api/v1/portfolio` | 1 | `manual-portfolio` |
| `GET /api/v1/analysis/{instrument}` | ≤ 4 (`FOCUS_LIMIT`) + 1 pour `decision-gates`, dédoublonné si c'est le même instrument | `focus`, `decision-gates` |

Sept routes, au plus onze requêtes — inchangé par rapport à aujourd'hui, pour
cinq modules servis de plus. Budget : p95 API ≤ 250 ms sur instantané préparé.

## 10. États dégradés

Chaque module porte **son propre** état, dérivé de faits servis et jamais du seul
succès HTTP. Le cadre de page ne couvre que la dominante.

| État | Page (dominante) | Module de soutien |
|---|---|---|
| `loading` | squelette **par lignes** de la table ledger ; le reste de la planche garde sa géométrie | squelette de la carte, aucun chiffre, aucun cadratin |
| `refreshing` | contenu conservé, `LiveBadge` en cours, surbrillance unique d'une valeur dont `snapshot_version` a changé (`--vx-motion-600`, 0 ms sous `prefers-reduced-motion`) | idem |
| `empty` | deux cas distingués : **aucun instantané publié** → `DataStateBoundary` + `reason` serveur en texte ; **instantané publié sans élément** → « Rien ne demande votre attention dans l'instantané publié », la provenance reste affichée | phrase d'absence du module, jamais une ligne fantôme |
| `partial` | `data_state = "partial"` servi → l'état du module le dit ; la couverture est affichée à côté | `market-pulse`, `sectors`, `discarded-tickers` basculent en `partial` sur le `data_state` servi |
| `delayed` | `population = "DELAYED"` → bandeau : ces observations ne décrivent pas le marché à cet instant ; âge publié écrit | pastille de nature + pied |
| `stale` | `state = "stale"` → **même contenu**, marqué périmé, avec l'âge publié et le budget publié côte à côte, plus la raison serveur en texte français | `FreshnessBadge` en avertissement + `stateDetail` |
| `offline` | « L'API locale est injoignable — la file d'attention ne peut pas être affichée » ; aucune valeur en cache n'est présentée comme fraîche | carte en état `offline`, contenu non rendu |
| `error` | « Réponse invalide ou inattendue de l'API — aucune file affichée » | idem, avec le motif servi s'il existe |
| `auth-required` | `AuthRequiredNotice`, échec fermé, aucune information sur l'existence de la ressource | idem |
| `closed` | séance fermée déclarée par la politique servie ; jamais confondu avec `empty` | idem |

**Règle transversale.** Dans tout état qui ne montre pas de contenu, les enfants
ne sont **pas rendus** : pas de zéro de remplacement, pas de cadratin, pas de
valeur ancienne non datée. Les huit natures — absent, zéro, retardé, périmé,
estimé, théorique, simulé, réel — restent visuellement distinctes et **le disent
chacune à l'écran**.

## 11. Parcours clavier

1. **Lien d'évitement** → conteneur de la planche.
2. `h1` « Aujourd'hui » puis la question de la page (texte, non focusable).
3. **Dominante.** Le conteneur défilant de `LedgerTable` est focusable
   (`tabIndex={0}`, `role="region"`, `aria-label="File d'attention, table
   défilante"` — axe `scrollable-region-focusable`, seuil zéro). `Flèche bas` /
   `Flèche haut` y font défiler la table sans déplacer le focus.
4. `Tab` entre ensuite dans la table : **un arrêt par ligne ouvrable**, le
   `<button>` du `<th scope="row">`. Une ligne sans `instrument_ref` n'a pas de
   bouton et n'est pas un arrêt — jamais un bouton mort.
5. `Entrée` ou `Espace` ouvre le dossier dans l'inspecteur du shell.
   `aria-expanded` décrit exactement ce que fait le bouton. Le focus **entre**
   dans le panneau dès l'attachement du nœud (ref de rappel, pas
   `useEffect([])` : le panneau est monté par portail).
6. **Panneau non modal** : aucun piège de focus. Depuis le dernier élément du
   panneau, `Tab` **continue** vers le reste de la page.
7. `Échap` referme le panneau depuis n'importe lequel de ses éléments et
   **restitue le focus au déclencheur**.
8. `Tab` poursuit ensuite, bande par bande, dans l'ordre du DOM — qui est l'ordre
   de lecture SIGNAL → PREUVE → RISQUE → DÉCISION. Le DOM n'est jamais réordonné
   par la grille.
9. Dans `sectors`, chaque puce est un `<button>` : `Entrée` ouvre
   `/analysis/{ticker}`. Les puces ne sont plus des `<span>` inertes.
10. Les liens de tête de module (« Toutes les sources », « Tous les candidats »,
    « Agenda complet ») sont des arrêts normaux, après le contenu de leur carte.

**Accessibilité, défauts corrigés au passage.**

- `AbsentModule` construit son `id` avec `useId()`. L'`id` actuel
  `` `vx-absent-${reason}-${title}` `` contient des espaces ; `aria-labelledby`
  étant une **liste** d'identifiants, deux des trois modules absents de la page
  n'ont aujourd'hui **aucun nom accessible**.
- L'absence ne se distingue plus par la couleur seule (WCAG 1.4.1) :
  `data-absent="true"` est **posé**, ce qui active le souligné pointillé de
  `.vx-cell-absent[data-absent='true']`, et le libellé nomme le champ manquant.
- Le titre n'est plus annoncé deux fois dans l'inspecteur : le `<h3>` visuellement
  masqué, dont l'`id` n'était référencé par rien, est supprimé —
  `InspectorPanel` porte déjà le sujet.
- `.vx-module-state` reçoit `overflow-wrap: anywhere`, comme
  `.vx-inspector-lineage` : une phrase serveur de cent cinquante caractères en
  chasse fixe ne déborde plus d'une cellule S.
- Zéro violation axe critique ou sérieuse ; contraste, zoom 200 %, focus visible
  et revue lecteur d'écran sur le parcours « ouvrir le dossier de l'élément
  prioritaire ».

## 12. Dette de forme réglée par cette conception

| Défaut mesuré | Résolution |
|---|---|
| Cadratin ambigu dans `AttentionQueue.tsx` et `SnapshotRail.tsx` (`DETTE_T4`) | les deux fichiers disparaissent ; `LedgerTable` et `snapshot-provenance` n'écrivent que par `AbsentCell` |
| Absence portée par la seule couleur | `data-absent="true"` posé partout |
| Codes serveur anglais à l'écran | table de traduction française, code conservé en pastille |
| `heartbeat_proxy` affiché comme libellé | phrase française nommant la limitation, code en provenance |
| Prose anglaise en canal `<code>`, débordement | `stateDetail` en texte + `overflow-wrap: anywhere` |
| `aria-labelledby` cassé sur les modules absents | `useId()` |
| `.vx-today-layout` et `.vx-queue-summary` mortes | supprimées ; la page passe sur `.vx-board--today` |
| `.vx-queue-item-meta` écrasée, commentaire devenu faux | règle unique, plus de surcharge par page |
| Adaptation responsive morte (`.vx-snapshot-rail`) | le rail n'existe plus ; une seule règle par sélecteur |
| Dominante en troisième bande, noyée | dominante en bande 1, seule, pleine largeur |
| `size` et `variant` déclarés puis ignorés | `Widget` lit le catalogue ; `data-size`/`data-module` pilotent la grille |
| Provenance perdue à l'ouverture d'un élément | `snapshot-provenance` est un module permanent |
| Fail-open sur la nature générée (badge seulement si `SYNTHETIC`) | vocabulaire fermé de `SyntheticBanner` sur `manual-portfolio`, `focus`, `sectors`, `calendar` |
| Puces sectorielles inertes | `onSelect` branché sur `/analysis/{ticker}` |
| `.slice(0, 3)` en double sur `relevance_reasons` | supprimé côté client ; le serveur tronque déjà |
| Âge recalculé en `Date.parse` | conservé tant que `items[].age_seconds` n'est pas relayé, avec le lot LOT 13 nommé au pied de la colonne |
| Aucune table sur la page | `LedgerTable` avec `<caption>`, `scope`, chiffres tabulaires — point conforme transformé en identité |

## 4. Réfutations adversariales — 25 à traiter avant implémentation

**Verdict : CORRECTIONS_REQUISES** — J'ai vérifié dans le dépôt chacun des quatorze modules déclarés « servi: oui », contre packages/python/vertex_core/src/vertex_core/contracts/, apps/api/src/vertex_api/ (schemas.py, snapshot_views.py, calendar.py, opportunities.py, portfolio.py, routes.py), apps/worker/src/vertex_worker/ (handlers.py, markets.py, calendar.py, opportunities.py, portfolio.py, analysis.py, ingest.py) et le client généré apps/web/src/api/schema.d.ts. Verdict : CORRECTIONS_REQUISES — douze violations, dont deux P0.

CE QUI TIENT (vérifié, à ne pas défaire). La totalité des champs d'attention existe : `items[].{id, title, sources, rights, relevance_reasons, synthetic, provenance}` (snapshot_views.py:1630-1649, l'API tronque déjà `relevance_reasons` à trois — le `.slice(0,3)` client est bien du code mort). Les quatorze clés de couverture existent verbatim (handlers.py:723-737), y compris `synthetic_observations` et `non_synthetic_observations` : le partage douze + deux entre `coverage` et `nature-census` est exact. Les sept clés de provenance de cluster existent (handlers.py:692-701). `freshness_policy.{kind, budget_seconds, version}` et `age_seconds` sont publiés dans tous les états datables (schemas.py:118-143). `MarketsBreadth` publie bien `value, value_pct, coverage_pct, coverage_threshold, coverage_threshold_pct, above_count, down_count, flat_count, covered_count, universe_size, status, reason, calculation` (schemas.py:243-271). `MarketsCoverage` publie `discarded_tickers[].{ticker, reason}` et `rejected_records[]` (schemas.py:291-302). `SystemCapabilitiesResponse` publie tout ce que `source-health` demande, et son `freshness_policy` est TOUJOURS nul par décision documentée — la fiche a raison de l'écrire. `AdviceResult` publie `gates[].{gate_id, version, status, reason_code, message, observed_values, thresholds}`, `limitations`, `explanation_facts`, `probability_evidence`, `supersedes` (contracts/decision.py:36-79). Le vocabulaire fermé des huit `relevance_reasons` de la table de traduction correspond exactement à `_REASON_BY_FLAG` + `_REASON_FRESHNESS` (fusion/relevance.py:121-131). `PAGE_ACCENTS.today === null` et ADR-017 rend bien `signal` inéligible : la doctrine d'accent de la fiche est conforme. Les deux refus explicites sont fondés : `POST /api/v1/advice/preview` existe bien (routes.py:210) et exigerait que le navigateur compose les entrées certifiées ; et la jauge âge/budget est bien un ratio non servi. Enfin `CensusBars` était déjà tranché par le dépôt (components/CensusBars.tsx) : la géométrie d'un dénombrement entier n'est pas un calcul financier — je ne la retiens pas contre la fiche.

LES DEUX P0. (1) L'ACTION PRINCIPALE de la page est cassée : `provenance.instrument_ref` porte le `con_id` IBKR (ingest.py:101) alors que `/api/v1/analysis/{instrument}` est clé par TICKER (routes.py:371-373). Le dépôt le dit lui-même mot pour mot (analysis.py:557-571). Un con_id numérique passe `UNDERLYING_PATTERN`, ne déclenche aucun 422, renvoie 200 `state=\"empty\"` — et la page affiche « aucun dossier d'analyse n'est publié » alors que le dossier existe. Une absence FABRIQUÉE sur la seule action de la page, et le même défaut frappe `decision-gates` qui sélectionne son instrument par le même champ. (2) `manual-portfolio` nomme six champs inexistants : `positions_by_currency[].{total_unrealized, unrealized_status, unrealized_reason, total_value}` (les vrais chemins sont sous `unrealized.*` et, pour `total_value`, sous `concentration.*` — le bloc que la fiche §8 déclare hors sujet) et `marks.{snapshot_version, as_of}` (vrais chemins `marks.source.*`).

LE RESTE. `window.applied` est un booléen, pas un objet à `.from`/`.to` — et surtout, la « fenêtre réellement appliquée par le serveur » est en fait l'ÉCHO verbatim de la fenêtre composée par le navigateur (`as_of + PT24H`) : une grandeur calculée côté client présentée comme servie, avec une branche de repli qui invoque une « fenêtre par défaut du serveur » qui n'existe pas. « Prochain catalyseur » affirme une futurité que la donnée ne porte pas : l'agenda est trié par heure croissante, donc `agenda[0]` est le plus ANCIEN événement de la fenêtre, et cette fenêtre est ancrée sur un `as_of` qui peut être périmé de plusieurs jours. `amount`/`currency` sont des clés conditionnelles recopiées de la charge source, sans lignée ni unité : elles n'ont pas leur place en corps d'affichage. Tous les chemins d'`opportunities` sont faux d'un niveau (`content.qualified[]`, pas `candidates.qualified[]`) et l'état `clock_inconsistent` manque au tableau des états. `markets/overview → tickers[]` n'existe pas (c'est `sectors[].tickers[]`). La colonne « Âge au snapshot » mesure une grandeur DIFFÉRENTE de l'`age_seconds` du moteur qu'elle promet de remplacer. Enfin, sept des blocs sur lesquels la fiche appuie ses colonnes sont typés `{[key: string]: unknown}` dans le client généré : les clés existent, mais rien ne les garantit au contrat — la fiche doit déclarer, par module, la porte de narrowing fail-closed qui les admet, en généralisant la règle « clé de couverture non reconnue » qu'elle a déjà écrite pour `coverage`.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `attention` | Loi 4 (absence n'est pas une valeur) + Loi 7 (source/méthode) | apps/worker/src/vertex_worker/ingest.py:101 `instrument_ref=envelope.instrument_id` ; apps/worker/src/vertex_worker/analysis.py:557-571 (docstring `instrument_ref_de`) : « Les observations portent le `con_id` en `instrument_ref` tandis que les pages parlent en TICKER : la correspondance n'est nulle part ailleurs, et l'inventer serait deviner. » ; apps/api/src/vertex_api/routes.py:371-373 `reader.current(kind=SNAPSHOT_KIND_ANALYSIS, key=instrument)` (clé = TICKER) ; apps/api/src/vertex_api/routes.py:153 `UNDERLYING_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"` (les chiffres passent). | L'ACTION PRINCIPALE de la page est bâtie sur un champ qui n'est pas la clé de l'instrument. `provenance.instrument_ref` est le `con_id` IBKR de l'observation ; `/api/v1/analysis/{instrument}` est clé par ticker. Un con_id numérique passe le motif de route, ne déclenche AUCUN 422, renvoie 200 `state="empty"` — et la page affiche « aucun dossier d'analyse n'est publié » alors que le dossier existe : un fail-open déguisé en absence honnête, sur la seule action de la page. Correction : la colonne « Instrument » n'est PAS ouvrable tant qu'un ticker n'est pas SERVI. Les seuls tickers servis sont `opportunities → content.qualified[].ticker` / `content.excluded[].ticker` et `markets/overview → sectors[].tickers[].ticker`. Soit l'ouverture est conditionnée à une correspondance exacte avec un ticker servi par un autre contrat (résolution servie, jamais devinée), soit la colonne reste en texte avec `AbsentCell nature="not_applicable"` et le pied nomme le LOT 13 qui doit publier `items[].instrument_ticker`. |
| `decision-gates` | Loi 4 + Loi 7 | Même preuve que `attention` : apps/worker/src/vertex_worker/analysis.py:557-571 ; apps/api/src/vertex_api/routes.py:371-373. La fiche : « L'instrument vient de `today/attention → items[].provenance.instrument_ref` ». | Second consommateur du même chemin cassé : le module qui décompose le VERDICT choisit son instrument par un con_id envoyé à une route clé par ticker. Il affichera systématiquement son texte d'absence « aucun dossier d'analyse n'est publié pour lui » — une absence FABRIQUÉE. Correction : sélectionner l'instrument depuis `opportunities → content.qualified[0].ticker` (ordre servi, `ordering.method = "lexicographic"`), ou depuis l'instrument ouvert dans l'inspecteur quand celui-ci porte un ticker servi ; jamais depuis `instrument_ref`. |
| `manual-portfolio` | Loi 4 (champ nommé inexistant) | apps/worker/src/vertex_worker/portfolio.py:820-827 : `by_currency.append({"currency": currency, "unrealized": unrealized_block, "realized": realized_block, "concentration": concentration_block})` ; blocs construits lignes 690-818. | Quatre champs nommés par la fiche n'existent pas : `positions_by_currency[].total_unrealized`, `.unrealized_status`, `.unrealized_reason`, `.total_value`. Les chemins réels sont `positions_by_currency[].unrealized.{status, reason, total_unrealized, lots[], calculation}`. Pire pour `total_value` : il n'existe QUE dans `positions_by_currency[].concentration.total_value` (portfolio.py:805-818), et seulement quand `concentration.status == "OK"` — c'est-à-dire dans le bloc que la fiche §8 déclare explicitement hors sujet sur cette page (« Herfindahl et poids de concentration ne montent pas ici »). La conception prend son chiffre de tête dans un bloc qu'elle refuse, et sans sa lignée `calculation`. Correction : renommer les chemins, rendre `unrealized.total_unrealized` avec son `unrealized.calculation` (lignée obligatoire, loi 7), et RETIRER `total_value` de cette page ou l'assumer explicitement comme la valeur marquée du bloc `concentration`, avec sa lignée et le refus `concentration.status=ABSENT`/`reason` quand il est fermé. |
| `manual-portfolio` | Loi 7 (source, as_of, version) | apps/worker/src/vertex_worker/portfolio.py:832-853 : `marks_block = {"status", "reason", "source": {"kind", "key", "snapshot_version", "as_of"}, "tickers_marked", "invalid_mark_tickers"}`. | Le pied « marques : <marks.status> depuis l'instantané v<marks.snapshot_version> au <marks.as_of> » nomme deux champs qui n'existent pas à ce niveau : ce sont `marks.source.snapshot_version` et `marks.source.as_of`, et ils sont `None` quand `marks.status == "ABSENT"`. La fiche ignore aussi `marks.invalid_mark_tickers` — la liste des instruments dont la marque a été REFUSÉE, exactement la preuve que la loi 4 exige de montrer. Correction : corriger les deux chemins, rendre le couple version/as_of via `AbsentCell nature="not_published"` quand `marks.source` est nul, et ajouter le dénombrement de `invalid_mark_tickers` à côté de `coverage.lots_excluded`. |
| `calendar` | Loi 4 (champ nommé inexistant) | apps/api/src/vertex_api/calendar.py:215-231 `class CalendarWindow` : `applied: bool ; from_utc: UtcDatetime \| None ; to_utc: UtcDatetime \| None ; max_days ; events_total ; events_in_window ; categories ; statuses` ; construction apps/api/src/vertex_api/calendar.py:332-350 `_window_echo` → `applied=window is not None`. | `window.applied` est un BOOLÉEN, pas un objet. Le pied « fenêtre appliquée <window.applied.from> → <window.applied.to> » nomme deux champs inexistants ; les bornes sont `window.from_utc` et `window.to_utc`, et elles sont `null` quand `applied` est `false`. Correction : `window.applied ? <window.from_utc> → <window.to_utc> : AbsentCell("fenêtre", not_applicable)`, plus l'affichage de `window.events_total` / `window.events_in_window` qui sont, eux, la vraie couverture de la sélection. |
| `calendar` | Loi 3 (aucun calcul dans le navigateur) + Loi 7 | apps/api/src/vertex_api/calendar.py:332-350 `_window_echo` renvoie VERBATIM les bornes reçues en query ; apps/api/src/vertex_api/routes.py:430-447 `get_calendar(window_from=Query(alias="from"), window_to=Query(alias="to"))` puis `validate_window(...)` ; apps/api/src/vertex_api/calendar.py:532-540 : `if window is None: selected = events`. | La fiche promet « la fenêtre RÉELLEMENT APPLIQUÉE par le serveur » et « ce qui est affiché est `window.applied`, verbatim ». Or le serveur n'applique aucune fenêtre propre : il ÉCHO celle que le navigateur lui a envoyée, dont la borne haute est `as_of + PT24H`, une addition faite dans le navigateur. La page afficherait donc une grandeur composée côté client en la présentant comme servie. Et la branche de repli est fausse : sans fenêtre transmise (`as_of` nul), `applied=false`, `from_utc=to_utc=null` et l'agenda ENTIER est renvoyé — la « fenêtre par défaut appliquée par le serveur » annoncée par la fiche §8 n'existe nulle part. Correction : écrire à l'écran que la borne haute est une fenêtre DEMANDÉE par l'interface (24 h après l'instantané servi), pas une décision du moteur ; et dans la branche sans fenêtre, dire « aucune fenêtre appliquée — agenda complet de l'instantané », jamais « fenêtre par défaut du serveur ». |
| `next-catalyst` | Loi 4 (passé, présent et à venir sont distincts) + Loi 5 (descriptif, jamais prédictif) | apps/worker/src/vertex_worker/calendar.py:1017-1020 : `entries = sorted(latest_by_stable_id.values(), key=lambda item: (item[1]["event_time_utc_parsed"], item[1]["stable_id"]))` — tri croissant ; apps/api/src/vertex_api/calendar.py:532-540 la sélection préserve l'ordre ; la fenêtre est ancrée sur `attention.as_of`, qui peut être en état `stale` (apps/api/src/vertex_api/snapshot_views.py:1687-1699). | `agenda[0]` est le PLUS ANCIEN événement de la fenêtre, pas le prochain. La fenêtre étant ancrée sur `attention.as_of` — qui peut être périmé de plusieurs jours — le module intitulé « Prochain catalyseur » affichera un événement PASSÉ comme s'il était à venir. Aucun champ servi ne dit « à venir » : ni `fresh` (qui compare `now` à `stale_after` de l'observation, pas à l'heure de l'événement), ni `status` (ESTIMATED/CONFIRMED). Correction : renommer le module « Premier événement de la fenêtre » et écrire `event_time_utc` avec sa timezone servie, sans aucun libellé relatif ; ou ne le rendre que lorsque `attention.state == "ok"` et afficher explicitement l'écart entre `window.from_utc` et l'heure de l'événement en tant que fait servi. |
| `next-catalyst` | Loi 7 (valeur, unité, devise, méthode, version) | apps/worker/src/vertex_worker/calendar.py:669-673 : `"extra": {key: payload[key] for key in ("amount", "currency", "expiration") if key in payload}` ; apps/worker/src/vertex_worker/calendar.py:1080 `item.update(event["extra"])`. | `amount` et `currency` sont des clés CONDITIONNELLES recopiées telles quelles de la charge source : absentes si la source ne les publie pas, sans `calculation`, sans méthode, sans version de moteur, sans unité déclarée. Les rendre en `KpiTile` (la mesure de tête du module) présente une valeur brute de source comme une grandeur d'autorité. Correction : rendre `amount` en preuve textuelle à côté de sa `source` et de ses `rights`, jamais en corps d'affichage ; `AbsentCell nature="not_published"` dès que la clé manque ; et refuser d'écrire un montant sans `currency` du même événement (une somme sans devise n'est pas une somme). |
| `opportunities` | Loi 4 (champ nommé inexistant) | apps/worker/src/vertex_worker/opportunities.py:817-855 : le contenu publie `"qualified": qualified` et `"excluded": excluded` À PLAT, avec `"ordering"`, `"coverage"`, `"exclusion_reasons"`, `"limitations"`, `"profile_ref"`, `"calendar_ref"` ; garde du relais apps/api/src/vertex_api/opportunities.py:682-683 : `content.get("qualified")` / `content.get("excluded")` ; enveloppe apps/api/src/vertex_api/opportunities.py:377-384 : `state, snapshot_version, as_of, age_seconds, freshness_policy, content, reason`. | Il n'existe aucun objet `candidates`. Les chemins réels sont `content.qualified[]`, `content.excluded[]`, `content.coverage.*`, `content.ordering.method` — tout est sous `content`, que la fiche omet à chaque ligne. Trois conséquences non traitées : (a) `rank` n'est posé QUE sur les qualifiés (opportunities.py:783-784) — un exclu n'a pas de rang ; (b) `content.coverage` publie aussi `population_counts`, `observations_considered` et `lookback_seconds`, que la fiche jette ; (c) l'état `clock_inconsistent` (quatrième valeur de `state`, `content = None`) n'apparaît dans aucun des dix états de la fiche §10 — un verdict non datable serait rendu comme un `empty` ordinaire. Correction : corriger les chemins, ne rendre `rank` que sur le groupe qualifié, et ajouter `clock_inconsistent` au tableau des états avec son propre texte. |
| `focus` | Loi 4 (chemin nommé inexistant) | apps/api/src/vertex_api/schemas.py:304-341 `MarketsOverviewResponse` : `sectors: tuple[MarketsSector, ...]`, `breadth`, `coverage` — aucun `tickers` racine ; apps/web/src/api/schema.d.ts, `MarketsOverviewResponse` et `MarketsSector` (les `MarketsTicker` ne sont accessibles que par `sectors[].tickers[]`). | La fiche écrit « `GET /api/v1/markets/overview → tickers[].{last_close, previous_close, ...}` » pour la cotation des quatre tuiles. Ce chemin n'existe pas : les instruments sont imbriqués dans `sectors[].tickers[]`. Le même défaut se répète dans la §8 (« `MarketsTicker.synthetic` », « `MarketsTicker.calculation` »). Correction : nommer `sectors[].tickers[]` partout et déclarer explicitement l'aplatissement (un parcours de tableau, pas un calcul) ; l'utilitaire `flattenTickers` de apps/web/src/pages/markets/marketsView.ts fait déjà exactement cela et doit être réutilisé plutôt que redit. |
| `attention` | Loi 7 (une grandeur, une méthode, une version) | packages/python/vertex_core/src/vertex_core/fusion/relevance.py:292-300 `_age_seconds` : base = `observation.published_at` sinon `observation.received_at` du REPRÉSENTATIF, mesuré contre `as_of` ; packages/python/vertex_core/src/vertex_core/fusion/dedup.py:858 : `first_published_at=min(published) if published else None` (le plus ancien membre du CLUSTER, nullable) ; apps/worker/src/vertex_worker/handlers.py:688 `"age_seconds": ranked.subscores.age_seconds` (produit, puis jeté par le relais). | La colonne « Âge au snapshot » calcule `as_of − provenance.first_published_at`, qui n'est PAS la grandeur que la fiche promet de lui substituer au LOT 13. `items[].age_seconds` du moteur se mesure sur le `published_at` du représentatif (repli `received_at`) ; `first_published_at` est le minimum sur TOUS les membres du cluster, et vaut `null` quand aucun membre ne porte de `published_at`. Deux définitions différentes sous une seule étiquette, dont l'une changerait de valeur sans changer de nom le jour du branchement. Correction : nommer la colonne pour ce qu'elle mesure vraiment — « Depuis la première publication du groupe » — écrire sa méthode au pied, et créer une colonne DISTINCTE (en-tête conservé, cellules « non publié », LOT 13 nommé) pour l'âge du moteur ; ne jamais présenter l'une comme le remplacement provisoire de l'autre. |
| `attention` | Loi 7 (contrat, version) | apps/web/src/api/schema.d.ts : `AttentionItem.provenance: { [key: string]: unknown }` ; `AttentionSnapshotResponse.coverage: { [key: string]: unknown } \| null` ; `PortfolioValuationView.content: { [key: string]: unknown } \| null` ; apps/api/src/vertex_api/schemas.py:151-168 et 170-197 (`FrozenStrMapping`) ; idem `AnalysisResponse.advice`, `CalendarResponse.agenda`, `OpportunitiesResponse.content`, `MarketsTicker.calculation`, `MarketsBreadth.calculation`. | Sept des blocs sur lesquels la fiche appuie ses colonnes et ses pieds sont typés `{[key: string]: unknown}` dans le client généré : les clés existent bien côté worker (vérifié), mais AUCUNE n'est garantie par le contrat OpenAPI ni vue par le compilateur. Une clé retirée côté Python passerait en `undefined` silencieux et la cellule tomberait sur l'absence — ce qui, sur `coverage` ou `advice.gates[].thresholds`, est exactement l'absence fabriquée que la loi 4 interdit. Correction : chaque lecture d'un bloc opaque passe par un narrowing NOMMÉ et fail-closed, qui distingue « clé absente du contrat » (→ avertissement, lot nommé) de « valeur nulle publiée » (→ `AbsentCell nature="not_published"`) ; la fiche doit cesser de présenter ces clés comme des champs de contrat et déclarer, par module, la porte de narrowing qui les admet — la règle « clé de couverture non reconnue » du module `coverage` est la bonne, elle doit être généralisée aux six autres blocs. |

**Verdict : CORRECTIONS_REQUISES** — Treize violations retenues sur la conception d'« Aujourd'hui », dont quatre graves.

CE QUI TIENT. Aucun mot d'ordre transactionnel imperatif (acheter, vendre, buy, sell, passer/annuler un ordre) n'apparait. Aucune lecture de compte, solde, NAV, position IBKR, P&L courtier ou execution : le seul module de portefeuille consomme GET /api/v1/portfolio, alimente par des lots declares a la main. Aucun texte d'absence ne contient de chiffre, aucun ne promet de date, aucun ne suggere que la valeur existe ailleurs — les vingt et une phrases du paragraphe 7 sont propres. Une seule carte rank=dominant, et l'ambre n'est pas declaree en teinte de page : PAGE_ACCENTS declare deja today: null (apps/web/src/components/widgets/pageAccent.ts), la conception est donc exacte et conforme a ADR-017. Le demi-arc de market-pulse n'est pas un cadran decoratif : ADR-017 l'admet et breadth.value_pct est bien une position servie (apps/web/src/api/schema.d.ts, MarketsBreadth). Aucun moteur graphique charge, aucune forme 3D, aucun double axe. La composition est franchement asymetrique (8 + colonne 9 vide + 3 aux bandes 3 et 8). Trois defauts reels du depot sont correctement diagnostiques et corriges : l'identifiant casse d'AbsentModule (AbsentModule.tsx:70-73, espaces dans un aria-labelledby), le cadratin ambigu, et le refus d'appeler POST /api/v1/advice/preview.

LES QUATRE GRAVES. (1) decision-gates lit probability_evidence : la porte no-uncalibrated-probability.test.ts:26 l'interdit a tout module web, son ALLOWLIST est vide, le champ est un mapping non type, et la conception ne nomme que QUATRE des CINQ conditions obligatoires — la version manque. (2) La colonne « Age au snapshot » de la table dominante est composee par le navigateur a partir de deux horodatages serveur, sans methode ni version, et n'est pas la meme grandeur que items[].age_seconds du worker (handlers.py:690, un sous-score de pertinence) : le pied promet une equivalence fausse. (3) L'etat closed est mal decrit : moduleState.ts:63 replie tout etat servi hors ok/stale/empty sur un seul libelle « Etat serveur fermé », ce qui ecrase quatre etats distincts du calendrier — un refus de DROITS (not_entitled) s'afficherait comme une seance fermee. (4) La fenetre du calendrier est ancree sur attention.as_of, qui peut etre stale : les titres « prochaines heures » et « Prochain catalyseur » nommeraient alors des evenements passes.

LE RESTE. Le mot « ordre » apparait six fois a l'ecran, dont un titre de module — arbitrage a trancher, le depot exemptant deliberement le nom descriptif dans ai_explain.py:505. manual-portfolio pose la question de l'espace Portefeuille, alors que la conception refuse Herfindahl au nom de « une page, une question ». Les six modules absents ne declarent aucun motif type du vocabulaire ferme d'AbsentModule, et nomment un lot de livraison que ce meme composant interdit. La largeur des puces sectorielles porterait weight_in_sector_pct sans texte. Le conteneur defilant focusable n'est declare que pour la table dominante alors que LedgerTable en a deux, et brancher onSelect ajoute jusqu'a ~161 arrets de tabulation sans contournement. focus filtre et tronque en silence, la ou le code existant divulgue deja sa troncature. Les codes de sources et de droits n'ont ni traduction ni comportement declare hors table. nature-census attribue a « la file » des comptes qui portent sur toute la fenetre de collecte. Enfin focus se contredit sur sa propre primitive.

Aucune de ces corrections ne remet en cause la structure de la conception : la file en table ledger pleine largeur en bande 1, les quatre zones SIGNAL / PREUVE / RISQUE / DECISION et la primitive LedgerTable restent valides.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `decision-gates` | Loi 5 — aucune probabilité sans calibration, horizon, population et validation hors échantillon publiées | apps/web/src/design/no-uncalibrated-probability.test.ts:26 (« RÈGLE. Aucun module web ne LIT `probability_evidence` ») et :54 (`const ALLOWLIST … = []`, exemption vide exigeant une décision écrite citant le test qui prouve les CINQ champs) ; apps/web/src/api/schema.d.ts:897 (`probability_evidence` typé `{[key: string]: unknown} \| null`, donc invérifiable). La conception écrit : « `probability_evidence` n'est rendu que si calibration, horizon, population et validation hors échantillon sont tous servis » — QUATRE conditions, alors que CLAUDE.md, .claude/rules/financial-safety.md et le docstring de la porte en exigent CINQ : la VERSION est omise. | Retirer toute lecture de `probability_evidence` de `decision-gates`. La carte n'affiche que `advice.limitations[]` servi, en clair et en français, et le champ reste réservé. Si le module doit un jour le lire, cela exige d'abord un contrat TYPÉ (les cinq champs nommés dans le schéma, pas un mapping `unknown`), puis une entrée nommée dans l'ALLOWLIST de la porte, motif écrit et test cité. |
| `attention` | Loi 4 — une absence n'est jamais une valeur composée ; Loi 7 — toute valeur critique porte méthode et version | Colonne « Âge au snapshot » de la table dominante : « `as_of` − `provenance.first_published_at` (deux horodatages serveur) ». Valeur PRODUITE PAR LE NAVIGATEUR, sans méthode ni version servies. Trois faits mesurés : (1) apps/worker/src/vertex_worker/handlers.py:690 publie `"age_seconds": ranked.subscores.age_seconds` — un sous-score du moteur de pertinence, PAS la différence de deux horodatages : le pied qui promet « à remplacer par `items[].age_seconds` dès le LOT 13 » affirme une équivalence fausse ; (2) apps/web/src/api/schema.d.ts:1192 (`AttentionItem`) ne publie pas ce champ ; (3) docs/09-adr/017-titanium-ledger-v2-formes-widgets.md, tableau des formes, ligne « Liste groupée par jour », déclare `first_published_at` connu-nullable (« pas `first_published_at` lorsqu'il vaut `null` »). | Supprimer le calcul. Conserver l'en-tête de colonne et rendre TOUTES ses cellules `not_published` via `AbsentCell`, exactement comme la colonne « Rang publié » du même tableau. La conception applique déjà cette règle à `coverage` (« aucun pourcentage écrit : l'écrire serait le calculer ») et à la jauge âge/budget refusée : appliquer la même règle ici. |
| `calendar` | Loi 4 — absent, retardé, périmé, sans droit sont des états distincts et chacun le DIT à l'écran | apps/web/src/components/moduleState.ts:63 (`if (state !== null && state !== 'ok') return 'closed'`) et :41 (`closed: 'État serveur fermé'`). CalendarResponse.state publie SEPT valeurs (apps/api/openapi.json : ok, empty, not_entitled, rejected, stale, empty_window, degraded) : QUATRE d'entre elles — `not_entitled`, `rejected`, `empty_window`, `degraded` — sont écrasées dans le seul état `closed`. La conception décrit pourtant `closed` comme « séance fermée déclarée par la politique servie » : un refus de DROITS s'afficherait comme une séance fermée. La conception ne déclare par ailleurs qu'UNE phrase d'absence pour le module, qui confond `empty`, `empty_window`, `not_entitled` et `rejected`. | Déclarer les sept états servis un par un, avec une phrase française distincte chacun (notamment : « droits absents sur les enregistrements considérés » pour `not_entitled`, « la fenêtre demandée ne sélectionne aucun événement publié » pour `empty_window`, « instantané antérieur à un champ du contrat courant » pour `degraded`). Ne pas s'appuyer sur `moduleStateOf` pour le calendrier tant qu'il replie ces états, ou l'étendre et corriger sa table de libellés. |
| `next-catalyst` | Loi 4 — réel, retardé et périmé ne partagent jamais le même statut ; Loi 7 — as_of et fraîcheur obligatoires | Titres « Agenda des prochaines heures » et « Prochain catalyseur » ; fenêtre ancrée sur `attention.as_of` (§8 : « `{from: attention.as_of, to: as_of + PT24H}` »). Or `AttentionSnapshotResponse.state` publie `stale` (apps/web/src/api/schema.d.ts, bloc AttentionSnapshotResponse) et la conception le prévoit explicitement au §10. Un `as_of` périmé de trois jours produit une fenêtre entièrement PASSÉE : `agenda[0]` serait un événement déjà survenu, nommé « prochain catalyseur », et l'agenda serait titré « prochaines heures ». | Titrer par la fenêtre servie, pas par une promesse temporelle : « Agenda de la fenêtre appliquée » et « Premier événement de la fenêtre appliquée ». Refuser les deux modules quand `today/attention.state = "stale"` — ils ne transmettent alors aucune fenêtre et disent pourquoi — et afficher `window.applied` verbatim à côté du titre dans tous les cas. |
| `attention-order` | Loi 2 — le vocabulaire « acheter / vendre / ordre / buy / sell / order » est interdit à l'écran | Le mot « ordre » apparaît à l'écran au moins six fois dans la conception : titre de module « Ordre de la file » ; pied de `attention` « ordre publié par le worker » ; pied de `discarded-tickers` « ordre servi » ; pied de `opportunities` « méthode d'ordre <ordering.method> » ; spécification `LedgerTable` « l'ordre affiché est l'ordre servi, et le pied le dit ». Arbitrage nécessaire, non tranché : apps/api/src/vertex_api/ai_explain.py:505-506 exempte DÉLIBÉRÉMENT le nom descriptif (« French transaction VERBS (an order given), never the descriptive nouns "achat"/"vente"/"ordre" of financial vocabulary ») et le dépôt l'emploie déjà à l'écran (apps/web/src/pages/opportunities/OpportunitiesPage.tsx:138, catalysts/CatalystsPage.tsx:127). La loi 2 telle qu'énoncée ne porte pas cette exemption ; sous doute par défaut, l'emploi est une violation. | Remplacer le mot à l'écran : titre « Rang publié dans la file » ; pieds « suite publiée par le worker, aucun reclassement local », « suite servie », « méthode de classement publiée <ordering.method> ». Si l'exemption du nom descriptif doit être maintenue, la faire trancher par une ADR qui la nomme et l'étend à la porte de vocabulaire, au lieu de la laisser implicite dans un commentaire Python. |
| `manual-portfolio` | Loi 6 — une page répond à UNE question | Question déclarée du module : « Que vaut le portefeuille déclaré aux marques publiées, et d'où viennent ces marques ? » — c'est la question de l'espace Portefeuille, pas « Qu'est-ce qui mérite mon attention maintenant ? ». La conception applique elle-même ce critère au §8, refus 3 : « Herfindahl et poids de concentration ne montent pas ici. Ils sont servis, mais ils répondent à la question de Risques et de Portefeuille. Une page, une question. » Le même test appliqué à la valorisation et au `total_unrealized` donne le verdict inverse sans motif écrit. | Soit retirer la valorisation de la page, soit reformuler le module en preuve de la file, sans valeur de portefeuille : « Combien d'éléments de la file touchent un lot déclaré » (compte servi, aucune somme, aucun `total_value`, aucun `total_unrealized`). Écrire le motif de la décision retenue à côté du refus Herfindahl, pour que les deux se lisent sous la même règle. |
| `regime` | Loi 4 — la nature de l'absence doit être DITE à l'écran (motif typé), et aucune promesse de livraison | Les six modules absents (`regime`, `volatility`, `conflicts`, `rejected`, `attention-order`, `active-risks`) déclarent une phrase libre et un `lotBloquant`, mais AUCUN ne déclare le motif typé exigé par le composant : apps/web/src/components/AbsentModule.tsx:24-46 impose `reason: AbsenceReason` dans le vocabulaire FERMÉ `NO_SOURCE` / `SUBSCRIPTION_REQUIRED` / `SERVER_CONTRACT_MISSING` / `DECISION_PENDING` — trois natures qui « appellent des actions différentes » (docstring, point 2). Inversement, le pied prescrit nomme « LOT 9 », « LOT 12 », « LOT 13 », ce que le même composant interdit explicitement en AbsentModule.tsx:21 : « Aucune promesse. Le motif dit ce qui manque, pas quand ce sera livré. » | Déclarer pour chacun son motif typé (`regime`, `volatility`, `active-risks` → `NO_SOURCE` ; `conflicts`, `rejected`, `attention-order` → `SERVER_CONTRACT_MISSING`, puisque le worker les produit et que seul le contrat ne les publie pas — cf. handlers.py:689-691 et le bloc `conflicts`/`rejected` du même instantané). Retirer le numéro de lot de la surface visible ; il reste dans le catalogue `TODAY_MODULES` et dans la fiche. |
| `sectors` | Loi 4 / ADR-017 — aucune information portée par la seule géométrie ou la seule couleur | La conception pilote la LARGEUR de chaque puce par `weight_in_sector_pct` servi, mais ne déclare nulle part que ce pourcentage est ÉCRIT sur la puce. apps/web/src/components/markets/SectorGrid.tsx:50-60 n'écrit aujourd'hui que le ticker, le glyphe de signe et `return_1d_pct` : le poids serait donc porté par la seule largeur. docs/09-adr/017-titanium-ledger-v2-formes-widgets.md, section « Décision », règle « Texte toujours présent » : « Chaque anneau, arc, barre ou cellule porte sa valeur servie en texte, son unité et sa période ; la couleur n'est jamais seule. » | Écrire `weight_in_sector_pct` en texte sur la puce, avec son unité, à côté de `return_1d_pct` — ou, si la puce devient illisible, renoncer à piloter la largeur par le poids et le publier dans la table équivalente du module. Une largeur sans chiffre est une valeur sans texte. |
| `discarded-tickers` | Parcours clavier et accessibilité — chaque module déclare le sien ; zéro violation axe critique/sérieuse | Le §11 ne déclare le conteneur défilant focusable (`tabIndex={0}`, `role="region"`, `aria-label`, axe `scrollable-region-focusable` à seuil zéro) que pour la table DOMINANTE. `discarded-tickers` emploie la MÊME `LedgerTable` avec, par spécification, « défilement horizontal ET vertical DANS son propre conteneur » — et `rejected` l'emploiera au LOT 13. Deux, puis trois conteneurs défilants non focusables. Par ailleurs le parcours déclaré place `sectors` à l'étape 9, alors que son rang DOM est la bande 3, immédiatement après la dominante ; et brancher `onSelect` transforme chaque instrument couvert en bouton, soit jusqu'à ~161 arrêts de tabulation (univers déclaré) entre la dominante et les bandes 4 à 8, sans mécanisme de contournement — un seul lien d'évitement est prévu, vers le conteneur de la planche. | Faire porter le conteneur focusable, son `role="region"` et son `aria-label` par `LedgerTable` elle-même, pour tous ses consommateurs. Corriger l'ordre du parcours déclaré pour qu'il suive le DOM (bande 3 avant bande 4). Ajouter un mécanisme de contournement par bande (SIGNAL / PREUVE / RISQUE / DÉCISION) ou rendre les puces sectorielles atteignables par un seul arrêt et une navigation par flèches à l'intérieur du groupe. |
| `focus` | Loi 7 — population et méthode obligatoires ; Loi 4 — ne jamais laisser croire que l'on montre le tout | Le module filtre côté navigateur sur `bars_status = "OK"` (champ servi, apps/web/src/pages/focusView.ts:5) puis tronque à quatre (`FOCUS_LIMIT`), et son pied ne dit NI le filtre NI la troncature. La conception condamne pourtant exactement ce geste ailleurs : elle supprime le `.slice(0, 3)` sur `relevance_reasons` comme « code mort qui masquerait un changement de contrat ». Le code existant divulgue déjà la troncature ailleurs sur la même page : apps/web/src/pages/TodayModules.tsx:439 écrit « {lines.length} premiers sur {data.agenda.length} publiés, ordre du worker ». La conception régresse par rapport à l'existant. | Le pied de `focus` écrit la population réelle et la méthode de sélection : « 4 premiers des N candidats publiés dont les barres sont servies (`bars_status = OK`), ordre publié — M candidats publiés au total ». Les trois nombres viennent du contrat servi ; aucun n'est recomposé. |
| `attention` | Loi 7 — tout texte d'interface en français clair ; un code servi ne se lit jamais seul | La table de traduction du §5 ferme NEUF entrées (huit codes de pertinence + `heartbeat_proxy`), mais la table dominante rend aussi `items[].sources[]` et `items[].rights[]` en « libellé français + code serveur en pastille ». Aucun libellé français n'est déclaré pour ces deux vocabulaires, et aucun comportement n'est déclaré pour un code hors table. Le résultat par défaut est le code anglais ou opaque, seul à l'écran — exactement le défaut que le §12 prétend régler (« Codes serveur anglais à l'écran »). Le contrat ne borne pas ces vocabulaires : apps/web/src/api/schema.d.ts, `AttentionItem.sources: string[]` et `rights: string[]`. | Fermer les deux vocabulaires (sources et droits) dans une table de traduction versionnée, et déclarer le comportement hors table : rendre `not_recognised` — code servi en pastille PLUS une phrase française nommant l'inconnu (« code de source non reconnu par cette version de l'interface ») — jamais le code seul. Même règle pour les codes d'exclusion de `opportunities` et les `reason_code` de `decision-gates`. |
| `nature-census` | Loi 7 — la population d'une mesure doit être exacte ; Loi 4 — ne pas attribuer à un objet un dénombrement qui porte sur un autre | apps/worker/src/vertex_worker/handlers.py:728-729 : `"synthetic_observations": synthetic_count` et `"non_synthetic_observations": len(records) - synthetic_count` comptent sur `records`, c'est-à-dire TOUTES les observations de la fenêtre `lookback_seconds`, et non sur `published_items` (ligne 734). La question déclarée du module est pourtant « Combien d'observations DE LA FILE sont générées, et combien sont observées ? », et sa phrase d'absence parle de « la nature des observations » de l'instantané. | Reformuler la question et le pied sur la population réelle : « Combien d'observations CONSIDÉRÉES dans la fenêtre sont générées, et combien sont observées ? », en écrivant `lookback_seconds` et `observations_considered` à côté des deux barres, et en distinguant explicitement ce compte de `published_items`. |
| `focus` | Cohérence de spécification — une formulation ambiguë est une violation | Le champ « widget » du module dit « Sparkline (ligne seule) » et le champ « graphique » du même module dit « ligne des clôtures servies + micro-barres de volume » : deux représentations, contradiction interne. De plus le §6 affirme « Aucune autre primitive n'est créée » et énumère les primitives réutilisées — `Sparkline` (apps/web/src/components/markets/Sparkline.tsx) et `SparkFigure` n'y figurent pas, alors que `focus` en emploie une ; `SectorGrid` non plus, alors qu'il est « étendu ». Enfin apps/web/src/components/widgets/SparkFigure.tsx:19-20 réserve explicitement les volumes à `Sparkline` « comme l'exige l'anatomie v2 » : le choix de primitive change la forme admise et doit être nommé. | Nommer une seule primitive et une seule représentation : `Sparkline` (clôtures + volumes servis, tuile d'instrument) OU `SparkFigure` variante `line` (clôtures seules, avec `windowLabel` servi obligatoire). Compléter la liste des primitives réutilisées du §6 avec la primitive retenue et avec `SectorGrid`, et corriger l'affirmation « SectorGrid est étendu pour `onSelect` » : `onSelect` existe déjà (SectorGrid.tsx:23) — seule la page ne le passait pas. |

## 5. Primitives neuves exigées — 1

- **LedgerTable** — La table financière dense de l'identité Titan Ledger : `<caption>` obligatoire, `<thead>` à `scope="col"`, chiffres tabulaires (`font-variant-numeric: tabular-nums`), lignes zébrées par un rail neutre, défilement horizontal ET vertical DANS son propre conteneur (la page ne défile jamais horizontalement), une action réelle par ligne rendue en `<button>` dans la cellule d'en-tête de ligne (`scope="row"`), et une cellule d'absence typée par colonne. Elle ne trie JAMAIS : l'ordre affiché est l'ordre servi, et le pied le dit. Elle ne totalise pas, ne dérive aucune colonne, n'abrège aucun nombre et n'écrit aucun rang calculé. Elle est le socle des trois tables de la page (file d'attention, instruments écartés, et — au branchement — exclusions de la file).. Donnée exigée : Un tableau de lignes SERVIES dans l'ordre publié par le serveur. Chaque colonne déclare : son libellé français, son code serveur (affiché verbatim en pastille quand le contenu est un code), son unité s'il y en a une, et la NATURE d'absence de ses cellules dans le vocabulaire fermé de `absence.tsx` (`not_published`, `not_computed`, `not_applicable`, `not_entered`, `not_recognised`). Chaque ligne déclare : un identifiant servi (`key`), sa nature (`population`/`synthetic` servi) et, si elle est ouvrable, la cible SERVIE de son action (par exemple `provenance.instrument_ref`). Aucune colonne dérivée, aucune agrégation, aucun total, aucun pourcentage non servi.. États : Les onze `ModuleState` du socle v2. `empty` : la phrase servie ou déclarée, AUCUNE ligne fantôme, aucun squelette persistant. `loading` : squelette PAR LIGNES (jamais par blocs), sans chiffre ni cadratin. Cellule sans valeur : `AbsentCell` avec `data-absent="true"` — le souligné pointillé et le libellé nommé portent l'information, jamais la couleur seule. Ligne générée : `data-population="<nature servie>"` + pastille de nature du vocabulaire fermé de `SyntheticBanner` ; une nature inconnue bascule en avertissement, jamais en silence. Colonne dont le contrat ne publie encore rien : l'en-tête est CONSERVÉ, les cellules disent « non publié », et le pied nomme le lot bloquant. Ligne sans action servie : le titre reste un `<th scope="row">` en texte, jamais un bouton mort.
