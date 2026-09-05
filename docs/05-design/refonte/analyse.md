# Dossier de refonte — Analyse (+ Graphiques)

> Produit par l'audit-conception du 2026-09-04 : un auditeur a lu le code et les
> contrats, un concepteur a dessiné la page cible, puis **deux lentilles
> adversariales** ont tenté de la réfuter. Les réfutations sont reportées ici
> telles quelles : **ce dossier est une conception à corriger, pas une
> spécification approuvée.** Le lot qui l'implémente applique d'abord le §4.

## 1. Ce que l'audit a mesuré

L'espace tient en deux moitiés qui ne se connaissent pas. Graphiques (`/charts`) est une destination de premier niveau, pas une sous-vue : deux sélecteurs d'instrument, deux inspecteurs, aucun lien, et pourtant un seul DTO (`GET /api/v1/analysis/{instrument}`) chargé deux fois par deux hooks distincts. Graphiques est passée aux widgets v2 et à la matière P4 ; Analyse est restée sur Card v1 et n'est même pas dans la liste de sélecteurs de widgets.css:1428 — les deux planches du même espace n'ont pas la même surface.

Le point central de l'audit est la matière servie et jamais montrée, et elle est considérable. Le plus grave n'est pas un oubli mais une CONTRADICTION : `analysisModules.ts:73-80` déclare encore le module « Oscillateurs » absent pour motif NO_SOURCE — « le registre des calculs ne publie aucun oscillateur » — alors que le worker publie `indicators.oscillators.rsi` et `.macd` dans chaque dossier (analysis.py:976-977) et que `chartsView.ts:112-119` a explicitement qualifié cette absence de « mensonge » en la corrigeant pour /charts. Dans le même DTO déjà chargé dorment aussi `indicators.overlays.{sma, ema, bollinger_bands}` et `indicators.rebased_comparison`, invisibles sur Analyse.

Trois séries glissantes complètes — volatilité réalisée, ATR, force relative, une valeur par séance avec méthode et lignée (`indicators.*.series`) — ne sont tracées par AUCUNE page : `IndicatorsPanel.tsx` n'affiche que la valeur ponctuelle, et `chartsView.ts:indicatorFamilyOf` ne connaît que les familles `overlays` et `oscillators`. Côté verdict, la preuve chiffrée des dix gates est servie et invisible : `gates[].observed_values` et `gates[].thresholds` n'apparaissent nulle part dans `apps/web/src` hors du schéma généré, et `advice.{instrument_id, input_snapshot_id, evidence_ids, scenario_ids, probability_evidence, supersedes}` ne sont même pas lus. Cinq champs sont lus puis jetés à l'affichage : `advice.advice_id`, `gates[].version`, `bars.observed_as_of`, `evidence.clusters_total`, `scenarios.value_nature` (le badge THÉORIQUE est codé en dur) et `scenarios.calculation.input_hash`. Enfin `freshness_policy {budget_seconds, kind, version}`, publié dans tous les états, n'est lu par aucune des deux pages : l'âge est affiché sans son échelle.

Le worker calcule aussi puis jette : `_calculation_meta` (analysis.py:500-508) ne persiste que 6 des 15 champs du `CalculationRecord`, donc `code_sha`, `source_event_ids`, `assumptions`, `parameters`, `started_at`/`completed_at` et `warnings` disparaissent à chaque indicateur. Les trois hypothèses exactes du repricing de scénarios sont construites (analysis.py:1880-1884) puis perdues — et `ScenarioPanel.tsx` les réécrit approximativement à la main. Le spot de référence, le taux, le rendement de dividende et la maturité qui construisent la grille ne sont pas publiés dans `basis`.

Côté défauts visuels, la passe T4-5 sur les tirets ambigus a atterri pendant l'audit (les six fichiers d'Analyse ont quitté la liste de dette de `no-ambiguous-dash.test.ts`), mais elle a laissé deux textes cassés — « âge publié non s. » (AnalysisPage.tsx:133) et « nombre non publié d' événement(s) » (EvidenceRail.tsx:26) — et elle n'a pas vu les deux absences converties en zéro que la porte ne sait pas détecter : « 0 barre(s) valides » et « 0 observation(s) considérée(s) ». Restent trois défauts structurels : la mini-série de l'en-tête superpose 30 clôtures et 14 volumes sur la même largeur, donc associe chaque barre de volume à la mauvaise séance ; les trois panneaux Verdict, Scénarios et Evidence affichent leur titre deux fois (défaut déjà diagnostiqué et corrigé côté Graphiques) ; et l'`id` d'`AbsentModule` contient des espaces, ce qui casse `aria-labelledby` sur huit modules absents. Enfin la fiche produit exige une action principale — « enregistrer ou mettre à jour une thèse » — que la page n'expose pas : l'inspecteur se contente d'écrire « Thèse : non publiée ».

### 1.1 Champs servis et jamais affichés — 53 relevés

La matière gratuite : déjà calculée par Python, publiée par le contrat, et
jetée par l'interface.

- advice.instrument_id — publié par AdviceResult (contracts/decision.py:65) ; adviceViewOf (analysisView.ts:143-195) ne le lit pas. Aucun croisement possible entre l'instrument du verdict et celui de la route.
- advice.input_snapshot_id — decision.py:68, l'observation EXACTE sur laquelle le verdict a été rendu. Jamais lu (analysisView.ts:182-194). L'écran montre bars.source_event_id, qui n'est pas la même chose.
- advice.evidence_ids — decision.py:73. Jamais lu. Le rail Evidence et le verdict ne peuvent donc pas être reliés à l'écran.
- advice.scenario_ids — decision.py:75. Jamais lu par Analyse (opportunitiesView.ts:204 le lit, analysisView.ts non). La grille de scénarios n'est pas rattachée au verdict.
- advice.probability_evidence — decision.py:76. Jamais lu, alors que le module « Confiance du modèle » est déclaré absent NO_SOURCE : c'est ce champ qui trancherait.
- advice.supersedes — decision.py:79. Jamais lu. La fiche 05-analysis.md exige « avis expiré » ; le champ qui dit qu'un avis en remplace un autre est ignoré.
- advice.advice_id — LU dans analysisView.ts:183 (AdviceView.adviceId) puis rendu NULLE PART : ni AdviceCard.tsx, ni AnalysisInspector.tsx, ni KeyRisksModule.
- advice.gates[].version — LU dans analysisView.ts:169 (GateView.version) puis rendu NULLE PART. AdviceCard.tsx:86-96 affiche gate_id, status, reason_code, message ; jamais la version de la gate.
- advice.gates[].observed_values — decision.py:49, « the real evidence the gate saw ». JAMAIS lu : aucune occurrence hors api/schema.d.ts:1655 dans tout apps/web/src. C'est la preuve CHIFFRÉE des dix gates, servie et invisible.
- advice.gates[].thresholds — decision.py:50. Idem : jamais lu (schema.d.ts:1662 seulement). Sans seuil, un BLOCK n'est pas relisible.
- advice.gates[].evidence_ids — decision.py:48. Jamais lu.
- freshness_policy {budget_seconds, kind, version} — schemas.py:118-143, publié dans TOUS les états d'AnalysisResponse (snapshot_views.py:2194). Aucune occurrence dans pages/analysis/ ni pages/charts/. FreshnessBadge.tsx n'affiche que l'âge : « il y a 3 j » sans dire si le budget daily_bar est de 72 h ou de 2 h.
- coverage.rejected_records[] — worker analysis.py:2167, chaque enregistrement refusé avec son event_id et son motif typé. AnalysisInspector.tsx:27-31 ne lit que observations_considered.
- coverage.lookback_seconds — worker analysis.py:2168. Jamais lu : la fenêtre d'observation du dossier n'est nulle part à l'écran.
- bars.age_seconds — worker analysis.py:2010, âge PROPRE aux barres, distinct de l'âge du relais. barsViewOf (analysisView.ts:94-108) ne le lit pas.
- bars.observed_as_of — LU dans analysisView.ts:105 (BarsView.observedAsOf) puis rendu NULLE PART. L'instant d'OBSERVATION de la série n'apparaît sur aucune des deux pages ; seul as_of du snapshot est montré.
- bars.discarded[] {index, reason} — worker analysis.py:1991+2013. analysisView.ts:106 n'en garde que la LONGUEUR. L'écran dit « 3 barre(s) écartée(s) » sans jamais dire lesquelles ni pourquoi, alors que le motif typé est servi.
- indicators.realized_volatility.series {status, window, unit, sessions, first_trading_day, last_trading_day, points[], calculation} — worker analysis.py:921 + 712-744. Série glissante COMPLÈTE, une valeur par séance. Aucune page ne la trace : IndicatorsPanel.tsx n'affiche que la valeur ponctuelle, et chartsView.ts:indicatorFamilyOf ne connaît que 'overlays' et 'oscillators'.
- indicators.atr.series — worker analysis.py:968 + 805-829. Idem : jamais tracée nulle part.
- indicators.relative_strength.series — worker analysis.py:1405 + 1454-1481. Idem : jamais tracée nulle part.
- indicators.*.unit ('annualized_ratio', 'price', 'ratio') — servi par le worker (analysis.py:738, 824, 1401). IndicatorsPanel.tsx:118-131 CODE EN DUR « % », la devise et « (ratio) » au lieu de lire l'unité publiée.
- indicators.*.available_bars — worker analysis.py:872, 930, le compte RÉEL disponible lors d'un INSUFFICIENT_SAMPLE. IndicatorsPanel.tsx:94-96 n'affiche que 'detail'.
- indicators.relative_strength.common_sessions — worker analysis.py:1475. Jamais lu : le nombre de séances communes avec l'indice n'est pas montré.
- indicators.*.calculation.{calculation_id, engine_version, input_hash, result_hash, status} — _calculation_meta publie 6 champs (worker analysis.py:500-508) ; IndicatorsPanel.tsx:60-66 n'en lit QUE 'method'. Cinq champs de lignée servis et jetés à l'affichage.
- indicators.overlays.{sma, ema, bollinger_bands} — servis à chaque dossier (worker analysis.py:976) et JAMAIS lus sur /analysis. La dominante CandleChart.tsx dessine « aucun overlay (0 sur les 2 admis) » alors que trois séries alignées sur les mêmes séances sont dans le DTO déjà chargé.
- indicators.oscillators.{rsi, macd} — servis (worker analysis.py:977) et jamais lus sur /analysis, où analysisModules.ts:73-80 les déclare encore absents NO_SOURCE avec un motif faux.
- indicators.rebased_comparison — servi (worker analysis.py:2042) et jamais lu sur /analysis ; seul /charts le rend.
- evidence.source ('fusion') — worker analysis.py:1755. Jamais lu.
- evidence.clusters_total — LU dans analysisView.ts:268 (EvidenceView.clustersTotal) puis rendu NULLE PART. EvidenceRail.tsx montre les clusters retenus sans jamais dire combien la fusion en a formés.
- evidence.considered — LU, mais affiché UNIQUEMENT dans la branche « aucun cluster » (EvidenceRail.tsx:12). Dès qu'un cluster existe, le nombre d'observations considérées disparaît.
- evidence.clusters[].rights — worker analysis.py:1745. Jamais lu : le droit d'usage de chaque preuve n'est pas à l'écran.
- evidence.clusters[].member_event_ids — worker analysis.py:1747. Jamais lu ; seul member_count l'est. Aucune preuve n'est ouvrable.
- scenarios.value_nature ('THEORETICAL') — LU dans analysisView.ts:342 (ScenariosView.valueNature) puis rendu NULLE PART : ScenarioPanel.tsx:29 CODE EN DUR le badge « THÉORIQUE ». L'étiquette de nature n'est pas celle que le serveur publie.
- scenarios.basis.multiplier — worker analysis.py:1897. Jamais lu par scenariosViewOf (analysisView.ts:315-325). Une grille de P&L d'option sans son multiplicateur.
- scenarios.basis.currency — worker analysis.py:1898. Jamais lu : les cellules de la table de scénarios n'ont AUCUNE devise à l'écran.
- scenarios.basis.iv — worker analysis.py:1901. Jamais lu, alors que ScenarioPanel.tsx:34 écrit « IV inchangée » sans jamais dire laquelle.
- scenarios.basis.con_id — worker analysis.py:1892. Jamais lu.
- scenarios.basis.chain_snapshot_version — worker analysis.py:1902. Jamais lu : impossible de savoir de quelle chaîne d'options vient la base.
- scenarios.iv_scenarios — worker analysis.py:1906. Jamais lu.
- scenarios.grid[1..] — ScenarioPanel.tsx:26 prend `scenarios.grid[0] ?? []`. Tout scénario d'IV supplémentaire serait silencieusement perdu.
- scenarios.calculation.input_hash — LU dans analysisView.ts:348 (ScenariosView.inputHash) puis rendu NULLE PART ; seul calculation_id l'est.
- markets/overview sectors[].tickers[].last_close et .previous_close et .previous_trading_day — schemas.py:219-220, 218. Jamais lus sur Analyse : l'en-tête n'a aucune clôture de référence de la veille.
- markets/overview ...tickers[].return_1d (variation ABSOLUE) — schemas.py:222. Jamais lu ; seul return_1d_pct l'est. La variation en devise n'existe pas à l'écran.
- markets/overview ...tickers[].currency — schemas.py:221. Jamais lu sur Analyse.
- markets/overview ...tickers[].weight_in_sector_pct et .weight_global_pct — schemas.py:225, 227. Jamais lus : le module Pairs classe sans jamais dire le poids.
- markets/overview ...tickers[].quality et .synthetic et .calculation — schemas.py:228-230. Jamais lus sur Analyse ; l'en-tête affiche une variation dont la qualité et la nature ne sont pas dites.
- SEC facts[].available_at et facts[].accession — LUS dans secView.ts:110-111 (SecFactView) puis rendus NULLE PART : la table de AnalysisModules.tsx:252-286 n'a que 4 colonnes. Un fait point-in-time sans sa date de disponibilité perd sa nature PIT.
- SEC coverage.published_filings, .published_facts, .truncated_facts, .conflicting_fact_keys, .corrections_observed — LUS dans secView.ts:124-129 (SecCoverageView) puis SEUL observationsConsidered est rendu (AnalysisModules.tsx:294). truncated_facts est justement ce qui dirait que la table de 12 lignes cache le reste.
- SEC conflicts[] — seule la LONGUEUR est utilisée (secView.ts:122). Le contenu des conflits de faits n'est jamais montré.
- SEC age_seconds, freshness_policy, population — schemas.py:413-418. Jamais lus par FinancialsModule.
- WORKER — CE QUI EST CALCULÉ PUIS JETÉ : make_calculation_record construit un CalculationRecord de 15 champs (contracts/calculation.py:40-53) ; _calculation_meta (worker analysis.py:500-508) n'en persiste que 6. code_sha, source_event_ids, assumptions, parameters, random_seed, started_at, completed_at, warnings et result sont calculés à chaque indicateur puis jetés — jamais persistés, donc hors d'atteinte de l'interface.
- WORKER — scenarios : les hypothèses EXACTES du repricing sont construites (analysis.py:1880-1884 : « premium side ASK », « single scenario: implied volatility unchanged », « P&L before declared costs ») puis jetées par _calculation_meta. ScenarioPanel.tsx les réécrit à la main en français au lieu de les recevoir.
- WORKER — scenarios : picked['spot'], picked['rate'], picked['dividend_yield'], picked['maturity_years'] servent à construire la grille (analysis.py:1849-1859) et NE SONT PAS publiés dans le bloc basis. Le spot de référence de la grille n'existe nulle part dans le contrat servi.

### 1.2 Défauts visibles dans le code — 26

- ABSENCE CONVERTIE EN ZÉRO (loi 4) — AnalysisPage.tsx:196 : `${bars.count ?? 0} barre(s) valides`. Un compte non publié s'affiche « 0 barre(s) valides » à côté d'un graphique qui en dessine soixante. La porte no-ambiguous-dash ne le voit pas (ce n'est pas un glyphe).
- ABSENCE CONVERTIE EN ZÉRO — EvidenceRail.tsx:12 : `{evidence.considered ?? 0} observation(s) considérée(s)`. « 0 observation considérée » se lit comme un fait mesuré alors que le compteur n'est pas publié.
- PHRASE FRANÇAISE CASSÉE (introduite par la passe T4-5 en cours) — AnalysisPage.tsx:133-134 : `âge publié ${data.age_seconds ?? 'non'} s.` rend « âge publié non s. » dans l'état stale.
- PHRASE FRANÇAISE CASSÉE — EvidenceRail.tsx:26-27 : `{cluster.memberCount ?? 'nombre non publié d’'}{' '}événement(s)` rend « nombre non publié d’ événement(s) » : élision suivie d'une espace.
- MINI-SÉRIE MAL ALIGNÉE (défaut de donnée, pas de style) — AnalysisModules.tsx:32-33 puis 122-133 : LINE_WINDOW = 30 clôtures et VOLUME_WINDOW = 14 volumes sont passés au MÊME Sparkline. Sparkline.tsx:66-68 étale les 30 clôtures sur toute la largeur et Sparkline.tsx:69 pose barSlot = WIDTH / volumes.length, donc les 14 barres de volume s'étalent AUSSI sur toute la largeur. Chaque barre de volume est visuellement associée à la mauvaise séance.
- DÉFORMATION DE LA MINI-SÉRIE — Sparkline.tsx:75-76 : viewBox 120×40 avec preserveAspectRatio="none", rendu par global.css:7358 à height 64px dans une carte de 2 colonnes sur 4 (≈ 560 px à 1280). Le trait est protégé par vector-effect: non-scaling-stroke (global.css:6639), mais le point de fin `<circle r={1.6}>` (Sparkline.tsx:96) devient une ellipse écrasée d'environ 4,7 : 1.6.
- TITRE AFFICHÉ DEUX FOIS — AnalysisPage.tsx:294-306, 308-320, 336-348 : la Card porte le titre du catalogue (« Verdict analytique », « Scénarios », « Evidence » en h2) et le composant enfant réaffiche immédiatement le même titre en h3 (AdviceCard.tsx:23 « Verdict analytique (AdviceEngine, autorité unique) », ScenarioPanel.tsx:29 « Scénarios », EvidenceRail.tsx:8 « Evidence (clusters de fusion) »). RebasedComparison.tsx:22-24 documente exactement ce défaut et l'a corrigé côté Graphiques ; il subsiste sur Analyse.
- aria-labelledby CASSÉ — AbsentModule.tsx:69 et 73 : `id={`vx-absent-${reason}-${title}`}` avec un titre contenant des espaces. Un id ne peut pas contenir d'espace et aria-labelledby est une LISTE d'ids séparés par des espaces : le nom accessible est perdu pour « Qualité fondamentale », « Confiance du modèle », « Révisions d'analystes », « Niveaux clés » sur Analyse, et pour « Graphiques synchronisés », « Objet sélectionné », « Alertes liées », « Études sauvegardées » sur Graphiques.
- TREIZE RÉGIONS LIVE SIMULTANÉES — AbsentModule.tsx:66 pose role="status" sur chaque module absent. Analyse en monte 8 et Graphiques 5 au chargement : autant d'annonces aria-live polite pour un contenu purement statique.
- TEXTE FRANÇAIS DANS UN CANAL DE CODE — publishedOr (SnapshotFacts.tsx:33) renvoie « non publié », inséré dans `<code>` par AnalysisInspector.tsx:44, 52, 60, 65 ; publie() (ChartsPage.tsx:110-115) fait de même dans ChartsPage.tsx:277-292 et AnalysisModules.tsx:222, 235, 238. `<code>non publié</code>` présente une phrase française comme un identifiant technique.
- PLANCHE ANALYSE HORS DU SOCLE v2 — widgets.css:1428-1451 énumère à la main .vx-risk-grid, .vx-pf-grid, .vx-markets-grid, .vx-today-grid et .vx-charts-grid pour le radius 22, la surface-1, l'ombre de panneau et la surface distincte de la dominante. .vx-analysis-grid n'y figure PAS (sa seule définition est global.css:7156). Les deux moitiés du même espace n'ont donc pas la même matière : c'est exactement la « seizième liste de sélecteurs énumérée à la main » que Card.tsx:12-23 déclare refuser.
- PLANCHE ANALYSE NON BENTO — global.css:7156-7166 : 8 rangées sur une grille 4 colonnes dont trois rangées entières de cellules identiques (regime/quality/valuation/confidence, puis peers/evidence/levels/contradictions). Tous les modules hors dominante sont en Card rank="quiet" : une seule surface, aucune différence franche de taille. La cible « tetris » n'est pas atteinte sur Analyse alors qu'elle l'est sur Graphiques.
- TAILLE ET VARIANTE DÉCLARÉES PUIS IGNORÉES — analysisModules.ts:29-31 déclare size (S/M/XL) et variant pour les 19 modules ; AnalysisPage.tsx ne les lit JAMAIS (aucun data-size, aucun Widget), la géométrie vient uniquement des grid-template-areas. Sur Graphiques, ChartsPage.tsx:310 pose data-size mais aucune règle CSS ne cible .vx-charts-grid [data-size] : l'attribut est inerte des deux côtés.
- ANALYSE N'EST PAS SUR LES WIDGETS v2 — Graphiques utilise Widget (11 états, provenance servie, surbrillance de version) ; Analyse utilise encore Card v1. Deux anatomies de module dans le même espace.
- TABLES SANS CAPTION — OhlcvTable.tsx:11, ScenarioPanel.tsx:47, AnalysisModules.tsx:252 (faits SEC), RebasedComparison.tsx:114 : quatre tables financières portent un aria-label mais aucun <caption>. Le titre n'est pas dans le flux du document et disparaît à l'impression et pour un lecteur en mode tableau.
- GRILLE DE SCÉNARIOS SANS UNITÉ NI DEVISE — ScenarioPanel.tsx:47-77 : les en-têtes disent « spot <valeur> » et « Temps restant (années) », les cellules sont des P&L nus. Ni la devise (basis.currency, servie), ni le multiplicateur (basis.multiplier, servi) n'apparaissent. Loi 7 non tenue sur une valeur critique.
- TABLE OHLCV NON PLAFONNÉE SUR GRAPHIQUES — ChartsPage.tsx:239 passe `bars` COMPLET à OhlcvTable alors que le graphique n'affiche que la fenêtre choisie (`affichees`). La table et la figure ne montrent pas le même périmètre, et global.css:7209 ne borne la hauteur que sous .vx-analysis-grid : sur Graphiques la table défile sans max-height.
- PeriodTabs SANS EFFET SUR LA TABLE NI SUR LES MODULES — ChartsPage.tsx:226-231 : le choix de fenêtre ne s'applique qu'à CandleChart. Volume (10 séances fixes), overlays, RSI, MACD et comparaison gardent leur propre fenêtre servie. Un seul contrôle apparent, cinq périmètres différents à l'écran.
- RANGÉE VIDE À 1280 ET 1440 — widgets.css:1325 : dernière rangée `'saved saved . .'`, la moitié droite de la planche Graphiques reste vide sous 1600 px.
- MOTIF D'ABSENCE FAUX À L'ÉCRAN — analysisModules.ts:79 affiche « Le registre des calculs ne publie aucun oscillateur » alors que le worker publie indicators.oscillators.rsi et .macd dans le MÊME DTO que la page a déjà chargé. C'est le défaut le plus grave de cet espace : une absence déclarée contre le contrat servi.
- COMMENTAIRE DE TEST PÉRIMÉ — ChartsPage.test.tsx:2-3 annonce « trois servis... neuf déclarés absents » ; chartsView.ts en compte désormais 7 servis et 5 absents.
- AUCUN PONT ENTRE LES DEUX MOITIÉS — aucune occurrence de `to="/charts` dans pages/analysis/ ni de `/analysis` dans pages/charts/. Deux sélecteurs d'instrument indépendants (AnalysisPage.tsx:61-88, ChartsPage.tsx:53-80) : ouvrir AAPL sur Analyse puis vouloir ses overlays impose de re-choisir AAPL sur Graphiques.
- AUCUNE ACTION PRINCIPALE — la fiche 05-analysis.md exige « enregistrer ou mettre à jour une thèse ». AnalysisPage.tsx n'expose aucun bouton ; l'inspecteur affiche « Thèse : non publiée » et « Invalidation : non publiée ». La page a zéro action principale au lieu d'une.
- COULEUR SEULE — non constaté. Les deux pages accompagnent systématiquement la teinte d'un glyphe et d'un texte : signSymbolOf (marketsView.ts:57) ▲/▼/= plus GROUP_LABELS_FR en vx-visually-hidden, gate.status écrit en toutes lettres à côté de vx-gate-status, MultiSeriesArea.tsx:31 pose un motif de trait par série.
- JAUGE CIRCULAIRE — non constaté. La seule jauge de l'espace est ArcGauge sur le RSI (ChartsModules.tsx:289-300), forme admise par ADR-017 et WIDGET_LIBRARY.md:98, bornée par l'unité SERVIE index_0_100 avec refus explicite si l'unité change. Réserve : elle est posée avec thresholds={[]} alors que DASHBOARD_COMPOSITION.md:107 écrit « seuils/version/provenance obligatoires » — le dépôt le justifie par l'absence de seuil déclaré, mais la règle et l'usage divergent.
- RÈGLE CSS MORTE — non constatée sur ces deux planches : .vx-chartframe-legend (global.css:1759, 4635) n'est employée par aucune des deux pages, mais elle appartient au socle partagé des cadres graphiques, pas à cet espace.

### 1.3 Graphiques actuels

- Chandeliers OHLC + volume — Lightweight Charts 5.2.1 (TradingView, Apache-2.0), épinglé, importé DYNAMIQUEMENT par charts/lightweightChartsLoader.ts, chunk séparé. CandleChart.tsx, dominante des DEUX pages. Attribution TradingView visible en figcaption, attributionLogo: true. Zéro overlay sur 2 admis. Table OHLCV équivalente. Repli textuel si le moteur échoue (CandleChart.tsx:150-157).
- Mini-série de l'en-tête instrument — SVG interne (Sparkline.tsx), ligne de 30 clôtures + 14 barres de volume, ligne de base pointillée = première clôture. Analyse seulement.
- Barres de volume par séance — SVG/CSS interne (DayBars.tsx sur rail), 10 dernières séances servies. Graphiques seulement.
- SMA et EMA — aire à dégradé, SVG interne (SparkFigure.tsx, variant="area"), sign={null} pour ne pas affirmer de sens. Graphiques seulement.
- Bandes de Bollinger — trois aires superposées, SVG interne (MultiSeriesArea.tsx), rendues UNIQUEMENT si indicatorBlockOf constate aligned === true. Graphiques seulement.
- RSI — ArcGauge (arc gradué SVG interne, role=meter) sur la dernière valeur servie, plus une SparkFigure de la série. Graphiques seulement.
- MACD — trois SparkFigure SÉPARÉES (macd, signal, histogram) parce que les trois lignes servies ne partagent pas leurs séances et que la page refuse de les réaligner. Graphiques seulement.
- Comparaison base 100 — MultiSeriesArea (2 séries) plus la table équivalente de RebasedComparison.tsx. Séries rebasées et calendriers intersectés PAR LE WORKER. Graphiques seulement.
- ECharts 6.1.0 — CHARGÉ NULLE PART dans cet espace. Aucun import de charts/echartsLoader.ts dans pages/analysis/ ni pages/charts/ ; ses seuls consommateurs sont MarketMap, PayoffChart, PerformanceChart et MonthlyHeatmap.

### 1.4 Fichiers lus

- `/home/user/vertex-merge/apps/web/src/pages/analysis/AnalysisPage.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/AnalysisModules.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/analysisModules.ts`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/analysisView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/AdviceCard.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/CandleChart.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/EvidenceRail.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/IndicatorsPanel.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/OhlcvTable.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/ScenarioPanel.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/AnalysisInspector.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/analysis/secView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/charts/ChartsPage.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/charts/ChartsModules.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/charts/chartsView.ts`
- `/home/user/vertex-merge/apps/web/src/pages/charts/RebasedComparison.tsx`
- `/home/user/vertex-merge/apps/web/src/components/Card.tsx`
- `/home/user/vertex-merge/apps/web/src/components/AbsentModule.tsx`
- `/home/user/vertex-merge/apps/web/src/components/FreshnessBadge.tsx`
- `/home/user/vertex-merge/apps/web/src/components/inspector/SnapshotFacts.tsx`
- `/home/user/vertex-merge/apps/web/src/components/markets/Sparkline.tsx`
- `/home/user/vertex-merge/apps/web/src/components/markets/marketsView.ts`
- `/home/user/vertex-merge/apps/web/src/components/widgets/Widget.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/MultiSeriesArea.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/SparkFigure.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/DayBars.tsx`
- `/home/user/vertex-merge/apps/web/src/components/calendar/AgendaLine.tsx`
- `/home/user/vertex-merge/apps/web/src/charts/lightweightChartsLoader.ts`
- `/home/user/vertex-merge/apps/web/src/app/routes.tsx`
- `/home/user/vertex-merge/apps/web/src/app/pages.ts`
- `/home/user/vertex-merge/apps/web/src/styles/global.css`
- `/home/user/vertex-merge/apps/web/src/styles/widgets.css`
- `/home/user/vertex-merge/apps/web/src/design/one-dominant-per-page.test.ts`
- `/home/user/vertex-merge/apps/web/src/design/no-ambiguous-dash.test.ts`
- `/home/user/vertex-merge/apps/api/src/vertex_api/routes.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/schemas.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/snapshot_views.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/freshness.py`
- `/home/user/vertex-merge/apps/api/src/vertex_api/ai_explain.py`
- `/home/user/vertex-merge/apps/worker/src/vertex_worker/analysis.py`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/decision.py`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/calculation.py`
- `/home/user/vertex-merge/docs/01-product/pages/05-analysis.md`
- `/home/user/vertex-merge/docs/01-product/ROUTES.md`
- `/home/user/vertex-merge/docs/05-design/CHART_STANDARD.md`
- `/home/user/vertex-merge/docs/05-design/WIDGET_LIBRARY.md`
- `/home/user/vertex-merge/docs/05-design/PLAN_NUIT_IDENTITE_V3.md`

## 2. Question, point focal, accent

- **Question** : Que vaut le dossier certifié de cet instrument, preuve par preuve ?
- **Visuel dominant** : La série certifiée : chandeliers OHLC, volume en histogramme sur la même échelle de temps et les trois overlays SERVIS (SMA, EMA, bandes de Bollinger) superposés — Lightweight Charts 5.2.1, chargé paresseusement, seul élément `data-rank="dominant"` de la planche.
- **Accent** : ambre (accent de page ; violet réservé au module Scénarios d'options, cyan aux modules d'étude technique, vert/rouge aux seuls signes servis)

## 3. Conception proposée

﻿# Page cible — Analyse (Graphiques absorbée)

Route unique : `/analysis/:instrument?` — `TL / 04`.
`/charts/:instrument?` est **supprimée** et redirigée en permanence vers
`/analysis/:instrument#etudes`. Un seul sélecteur d'instrument, un seul
inspecteur, un seul hook `useAnalysis`, un seul DTO `GET /api/v1/analysis/{instrument}`
chargé **une** fois.

---

## 1. Question de la page

> **Que vaut le dossier certifié de cet instrument, preuve par preuve ?**

Tout module qui ne sert pas cette question sort de la planche. La page se lit de
haut en bas dans l'ordre **SIGNAL → PREUVE → RISQUE → DÉCISION** ; ce n'est pas
un classement esthétique, c'est l'ordre dans lequel un dossier se relit.

## 2. Visuel dominant (un seul)

**La série certifiée** : chandeliers OHLC, volume en histogramme **sur la même
échelle de temps**, et les trois overlays servis (SMA, EMA, bandes de Bollinger)
superposés à la série. Moteur **Lightweight Charts 5.2.1** (TradingView,
Apache-2.0), épinglé, importé dynamiquement par `charts/lightweightChartsLoader.ts`,
chunk séparé, attribution visible en `figcaption`, `attributionLogo: true`,
repli textuel si le moteur échoue.

C'est le **seul** élément portant `data-rank="dominant"`. `gates-ledger` et
`price-chart` sont tous deux `XL` (span 12) mais `XL` est une **taille**, pas un
**rang** : le registre des portes est une table `rank="quiet"`.

**ECharts 6.1.0 n'est pas chargé sur cette route.** Toutes les figures
secondaires sont des primitives SVG internes (`SparkFigure`, `MultiSeriesArea`,
`LinearGauge`, `CellGrid`). Charger un second moteur graphique pour des séries
de quelques dizaines de points coûterait un chunk entier sans rien apporter, et
`.claude/rules/frontend.md` demande de ne charger un moteur que sur les routes
qui l'utilisent.

## 3. Accent

**Ambre** (accent de page, `TL / 04`). Réserves de teinte :
violet = module `scenarios` (options) ; cyan = modules d'étude technique
(`volatility-series`, `atr-series`, `rsi`, `macd`) ; vert / rouge = **uniquement**
un signe servi, toujours doublé d'un glyphe (`▲ ▼ =`) et d'un libellé lisible en
`vx-visually-hidden`. Une lumière dominante par carte, deux par écran hors
rouge/vert.

## 4. Zones

| Zone | Rôle | Colonnes (grille 12) | Modules |
|---|---|---|---|
| **A** — Signal | SIGNAL | R1 : 6 + 3 + 3 | `instrument-signal`, `identity-reference`, `freshness-budget` |
| **B** — La série | PREUVE | R2 : 12 · R3 : 3 + 3 + 3 + 3 | `price-chart` (dominante), `bars-integrity`, `overlays-legend`, `volatility-series`, `atr-series` |
| **C** — Les études servies (ex-Graphiques) | PREUVE | R4 : 6 + 6 · R5 : 8 + respiration + 3 · R6 : 6 + 3 + 3 | `rsi`, `macd`, `rebased-comparison`, `relative-strength-series`, `synchronized-series`, `series-annotations`, `linked-watches` |
| **D** — Les faits | PREUVE | R7 : 6 + 6 · R8 : 3 + 3 + 3 + 3 · R9 : 3 + 3 + 3 + 3 | `sec-facts`, `evidence-clusters`, `sec-conflicts`, `fundamental-quality`, `valuation`, `analyst-revisions`, `catalysts`, `peers`, `regime`, `levels` |
| **E** — Risque | RISQUE | R10 : 12 · R11 : 6 + 3 + 3 | `gates-ledger`, `coverage-rejects`, `key-risks`, `contradictions` |
| **F** — Décision | DÉCISION | R12 : 6 + 6 · R13 : 6 + 6 | `verdict`, `scenarios`, `thesis`, `model-confidence` |
| **G** — Inspecteur | DÉCISION | hors grille, panneau latéral 360 px | `dossier-lineage`, `ai-explanation` |

### Géométrie exacte

```css
.vx-analysis-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--vx-space-16);
}
/* S = span 3 · M = span 6 · L = span 8 · XL = span 12 */
```

`.vx-analysis-grid` **entre** dans la liste de sélecteurs de
`widgets.css:1428` (rayon 22, `surface-1`, ombre de panneau, surface distincte
de la dominante), au même titre que `.vx-risk-grid`, `.vx-pf-grid`,
`.vx-markets-grid`, `.vx-today-grid` et `.vx-charts-grid`. Les deux moitiés de
l'espace fusionné doivent avoir **la même matière**.

**Respiration de la colonne 9, rangée 5.** `rebased-comparison` occupe les
colonnes 1→9, `relative-strength-series` les colonnes 10→13 ; la colonne 9 reste
vide. C'est le **seul** vide déclaré de la planche, une colonne large d'un
douzième, et c'est un geste de composition asymétrique — à ne pas confondre avec
la demi-rangée vide de l'ancienne planche Graphiques (`widgets.css:1325`,
`'saved saved . .'`), qui laissait la moitié droite de l'écran nue sous 1600 px
et qui disparaît avec la fusion.

**Le bento vient de la variété des rangées, pas d'une grille régulière** :
12 pleine, 6+6, 6+3+3, 3+3+3+3, 8+3. Aucune rangée n'a la même partition que sa
voisine immédiate. Quatre modules sont `rank="dominant"`… non : **un seul**
(`price-chart`) ; deux sont `rank="loud"` (`gates-ledger`, `verdict`), le reste
`rank="quiet"`.

### Absorption de Graphiques — ce qui disparaît

- `pages/charts/` entier : `ChartsPage.tsx`, `ChartsModules.tsx`, `chartsView.ts`,
  `RebasedComparison.tsx` (sa table passe dans `DataTable`).
- Le second sélecteur d'instrument (`ChartsPage.tsx:53-80`).
- Le second inspecteur `SeriesInspector` (`ChartsPage.tsx:266-296`), absorbé par
  `dossier-lineage` — qui utilise `SnapshotFacts` et non une `dl` brute.
- L'entrée `charts` de `apps/web/src/app/pages.ts`. La navigation cible ne garde
  qu'**Analyse** dans « Explorer ».
- Un lien d'ancre unique dans la tête de la dominante : « Aller aux études de
  série » → `#etudes` (zone C). Aucun onglet, aucune sous-route : tout est sur la
  même planche, donc rien à re-sélectionner.

### `PeriodTabs` — un contrôle, un périmètre

`PeriodTabs` vit dans la tête de la dominante et pilote **la figure ET sa table
OHLCV**, toutes deux bornées à la même fenêtre (l'ancien `ChartsPage.tsx:239`
passait `bars` complet à la table pendant que la figure n'affichait que
`affichees`). Les modules d'étude gardent la fenêtre **servie** par leur propre
bloc et **l'écrivent** sous leur figure (`windowLabel` de `SparkFigure` est
obligatoire) : un seul contrôle, et chaque périmètre différent est nommé plutôt
que subi.

## 5. Action principale (une seule)

**« Ouvrir l'inspecteur du dossier »** — bouton réel dans la tête de la
dominante, ouvre le panneau latéral du shell sur `dossier-lineage`. Il est
toujours disponible parce que sa donnée est toujours servie.

La fiche produit `05-analysis.md` demande « enregistrer ou mettre à jour une
thèse ». Ce n'est **pas** l'action principale aujourd'hui : aucun contrat ne
persiste une thèse (`thesis`, `DECISION_PENDING`, **LOT 10**). Le jour où LOT 10
publie ce contrat, `thesis` devient l'action principale et « Ouvrir l'inspecteur »
redevient une action secondaire de la tête.

Vocabulaire interdit à l'écran, sans exception : acheter, vendre, ordre, buy,
sell, order, position, exécuter.

## 6. Modules

| id | titre | question | taille | widget | graphique | donnée | servi | lot bloquant |
|---|---|---|---|---|---|---|---|---|
| `instrument-signal` | Instrument | À quelle clôture publiée et à quelle variation de séance cet instrument se tient-il ? | M | Widget + KpiTile ×2 + KpiDelta + SparkFigure + StatusChip | mini-série de clôtures (SVG interne) | `bars.last_close`, `bars.currency`, `bars.last_trading_day` ; `markets/overview → tickers[].{last_close, previous_close, previous_trading_day, return_1d, return_1d_pct, currency, quality, synthetic, calculation}` | oui | — |
| `identity-reference` | Identité et référence | Quel instrument, quelle devise, quelle base d'ajustement et quel indice de référence ce dossier décrit-il ? | S | Widget + Metric ×6 + StatusChip | — | `instrument`, `population`, `bars.currency`, `bars.adjustment_basis`, `advice.instrument_id`, `indicators.relative_strength.benchmark`, `markets/overview → sectors[].name` | oui | — |
| `freshness-budget` | Âge contre budget | L'âge de ce dossier tient-il dans le budget de fraîcheur publié pour sa famille d'observation ? | S | Widget + LinearGauge + FreshnessBadge + StatusChip | jauge **linéaire** (SVG interne), bornes servies | `age_seconds`, `state`, `freshness_policy.{budget_seconds, kind, version}`, `bars.age_seconds`, `bars.fresh` | oui | — |
| `price-chart` | Série certifiée et overlays servis | Que publie le serveur de la série de cet instrument, avec ses moyennes et ses bandes servies ? | XL | **Widget rank=dominant** + PeriodTabs + DataTable | chandeliers + volume + SMA + EMA + Bollinger — **Lightweight Charts 5.2.1** | `bars.bars[]`, `indicators.overlays.sma.points[]`, `.ema.points[]`, `.bollinger_bands.{bands, points[].{lower, middle, upper}}` | oui | — |
| `bars-integrity` | Intégrité de la série | Combien de barres ont été retenues, et lesquelles ont été écartées et pour quel motif ? | S | Widget + KpiTile + DataTable | — | `bars.count`, `bars.quality`, `bars.fresh`, `bars.age_seconds`, `bars.observed_as_of`, `bars.discarded[].{index, reason}` | oui | — |
| `overlays-legend` | Overlays servis | Quelles moyennes le serveur superpose-t-il à la série, sur quelle méthode et quelle fenêtre ? | S | Widget + StepList + StatusChip + ProvenanceLine | — | `indicators.overlays.{sma, ema, bollinger_bands}.{status, window, num_std, unit, method, points[], last, available_bars, detail, reason, calculation}` | oui | — |
| `volatility-series` | Volatilité réalisée | Comment la volatilité réalisée publiée évolue-t-elle séance après séance ? | S | Widget + SparkFigure + Metric + ProvenanceLine | courbe glissante (SVG interne) | `indicators.realized_volatility.{status, window, unit, value, value_pct, available_bars, calculation}` **+ `.series.{sessions, first_trading_day, last_trading_day, points[], calculation}`** | oui | — |
| `atr-series` | Amplitude vraie moyenne (ATR) | Quelle amplitude vraie moyenne le moteur publie-t-il sur cette série, séance après séance ? | S | Widget + SparkFigure + Metric + ProvenanceLine | courbe glissante (SVG interne) | `indicators.atr.{status, lookback, unit, value, available_bars, calculation}` **+ `.series.{sessions, first/last_trading_day, points[], calculation}`** | oui | — |
| `rsi` | RSI | Où se situe l'indice de force relative publié sur ses bornes servies, et comment a-t-il évolué ? | M | Widget + **LinearGauge** + SparkFigure + ProvenanceLine | jauge linéaire + courbe (SVG interne) | `indicators.oscillators.rsi.{status, window, unit, method, points[], last, available_bars, calculation}` | oui | — |
| `macd` | MACD | Comment évoluent les trois lignes MACD publiées, chacune sur ses propres séances ? | M | Widget + SparkFigure ×3 + StatusChip + ProvenanceLine | trois courbes **séparées** (SVG interne) | `indicators.oscillators.macd.{status, windows, unit, method, lines[], series.{macd, signal, histogram}, last, calculation}` | oui | — |
| `rebased-comparison` | Comparaison base 100 | Comment cette série et l'indice déclaré se comparent-ils sur leurs seules séances communes ? | L | Widget + MultiSeriesArea + DataTable + ProvenanceLine | deux séries superposées (SVG interne) + table | `indicators.rebased_comparison.{status, benchmark, unit, base_value, currency, adjustment_basis, common_sessions, minimum_sessions, first/last_trading_day, series[].{trading_day, instrument, benchmark}, rejected_records[], reason, detail, calculation, benchmark_calculation}` | oui | — |
| `relative-strength-series` | Force relative contre l'indice | Comment cette série se compare-t-elle à l'indice déclaré, séance après séance ? | S | Widget + SparkFigure + Metric + ProvenanceLine | courbe glissante (SVG interne) | `indicators.relative_strength.{status, benchmark, horizon, common_sessions, unit, value, calculation}` **+ `.series.{sessions, points[], calculation}`** | oui | — |
| `synchronized-series` | Séries synchronisées | Quelles séries lire côte à côte sur un même calendrier ? | M | AbsentModule · `SERVER_CONTRACT_MISSING` | — | — | **non** | **LOT 9** intelligence de marché |
| `series-annotations` | Repères de série | Quels repères ai-je posés sur cette série, et où sont-ils conservés ? | S | AbsentModule · `DECISION_PENDING` | — | — | **non** | **LOT 13** observabilité et recherche |
| `linked-watches` | Surveillances liées | Quelles surveillances déclarées suivent cette série ? | S | AbsentModule · `DECISION_PENDING` | — | — | **non** | **LOT 13** observabilité et recherche |
| `sec-facts` | Faits officiels (SEC) | Quels dépôts et quels faits XBRL point-in-time sont publiés pour cet instrument ? | M | Widget + DataTable + StatusChip + ProvenanceLine | — | `sources/sec/{instrument}/fundamentals → filings[]`, `facts[].{concept, value, unit, period, available_at, accession}`, `coverage.{observations_considered, published_filings, published_facts, truncated_facts, conflicting_fact_keys, corrections_observed}`, `rights`, `population`, `age_seconds`, `freshness_policy` | oui | — |
| `sec-conflicts` | Faits officiels en conflit | Quels faits officiels se contredisent entre dépôts pour cet instrument ? | S | Widget + DataTable + StatusChip | — | `conflicts[]`, `coverage.conflicting_fact_keys`, `coverage.corrections_observed` | oui | — |
| `fundamental-quality` | Qualité fondamentale | Une note de solidité fondamentale est-elle publiée pour cet instrument ? | S | AbsentModule · `NO_SOURCE` | — | — | **non** | **LOT 7** sources manquantes |
| `valuation` | Valorisation | Un multiple ou une juste valeur est-il publié pour cet instrument ? | S | AbsentModule · `NO_SOURCE` | — | — | **non** | **LOT 7** sources manquantes |
| `analyst-revisions` | Révisions de consensus | Un consensus d'analystes et ses révisions sont-ils publiés pour cet instrument ? | S | AbsentModule · `NO_SOURCE` | — | — | **non** | **LOT 7** sources manquantes |
| `evidence-clusters` | Clusters d'observations | Quelles observations la fusion a-t-elle regroupées, sous quels droits et à partir de combien de sources ? | M | Widget + KpiTile ×3 + ActivityFeed + StatusChip | — | `evidence.{source, ruleset_version, considered, clusters_total}`, `clusters[].{cluster_id, title, sources, rights, member_count, member_event_ids, last_received_at, synthetic}` | oui | — |
| `catalysts` | Catalyseurs publiés | Quels événements datés du calendrier sont rattachés à cet instrument ? | S | Widget + ActivityFeed | — | `GET /api/v1/calendar → items[]` rattachés au ticker | oui (réserve) | rattachement au serveur : **LOT 9** |
| `peers` | Pairs du secteur servi | Comment les instruments du même secteur servi ont-ils clôturé, et quel poids y pèsent-ils ? | S | Widget + DataTable + StatusChip | — | `markets/overview → sectors[].tickers[].{ticker, last_close, previous_close, previous_trading_day, return_1d, return_1d_pct, currency, weight_in_sector_pct, weight_global_pct, quality, synthetic}` | oui | — |
| `regime` | Régime observé | Dans quel régime observé cette population se tient-elle ? | S | AbsentModule · `NO_SOURCE` | — | — | **non** | **LOT 9** intelligence de marché |
| `levels` | Niveaux publiés | Quels niveaux le serveur publie-t-il sur cette série ? | S | AbsentModule · `SERVER_CONTRACT_MISSING` | — | — | **non** | **LOT 9** intelligence de marché |
| `gates-ledger` | Registre des portes | Que chaque porte a-t-elle réellement observé, contre quel seuil et dans quelle version ? | XL | Widget + DataTable + StatusChip + ProvenanceLine | — | `advice.gates[].{gate_id, version, status, reason_code, message, observed_values, thresholds, evidence_ids}` | oui | — |
| `coverage-rejects` | Couverture et refus | Quels enregistrements ont été considérés sur la fenêtre, lesquels refusés et pour quel motif ? | M | Widget + KpiTile ×2 + DataTable | — | `coverage.{observations_considered, lookback_seconds, rejected_records[].{event_id, reason}}` | oui | — |
| `key-risks` | Limites déclarées | Quelles limites le moteur attache-t-il à ce verdict ? | S | Widget + StepList + Metric | — | `advice.risk_summary`, `advice.limitations[]` | oui | — |
| `contradictions` | Contradictions du dossier | Quels faits de ce dossier se contredisent entre eux ? | S | AbsentModule · `SERVER_CONTRACT_MISSING` | — | — | **non** | **LOT 10** décision décomposée |
| `verdict` | Verdict analytique | Quel statut et quelle direction l'unique moteur publie-t-il, et sur quel instantané d'entrée ? | M | Widget + StatusChip ×2 + Metric ×4 + StepList | — | `advice.{advice_id, instrument_id, status, direction, horizon, as_of, valid_until, engine_version, input_snapshot_id, evidence_ids, scenario_ids, supersedes, explanation_facts}` | oui | — |
| `scenarios` | Grille de scénarios (théorique) | Que vaudrait la structure de base publiée sous les spots et les horizons servis ? | M | Widget + **CellGrid** + StatusChip + Metric ×5 + ProvenanceLine | grille spots × horizons (SVG/CSS interne) | `scenarios.{status, reason, value_nature, basis.{con_id, right, strike, expiration, trading_class, multiplier, currency, premium, premium_side, iv, chain_snapshot_version}, spot_grid, time_grid_years, iv_scenarios, grid[] (tous), calculation}` | oui | — |
| `thesis` | Thèse et invalidation | Quelle thèse et quelle condition d'invalidation ai-je déclarées sur ce dossier ? | M | AbsentModule · `DECISION_PENDING` | — | — | **non** | **LOT 10** décision décomposée |
| `model-confidence` | Confiance calibrée | Une probabilité calibrée et validée hors échantillon accompagne-t-elle ce verdict ? | M | AbsentModule · `NO_SOURCE` | `advice.probability_evidence` existe au contrat et **reste nul** | — | **non** | **LOT 11** résultat et apprentissage |
| `dossier-lineage` | Lignée du dossier *(inspecteur)* | De quel instantané, de quel avis et de quels calculs ce dossier est-il issu ? | S | Widget rail + SnapshotFacts + DataTable + ProvenanceLine | — | `snapshot_version`, `schema_version`, `as_of`, `age_seconds`, `state`, `population`, `engine_version`, `freshness_policy`, `bars.*`, `advice.*`, `indicators.*.calculation`, `scenarios.calculation`, `coverage.lookback_seconds` | oui | — |
| `ai-explanation` | Explication IA *(inspecteur)* | Comment un lecteur peut-il faire expliquer ce dossier validé sans créer une seconde vérité ? | S | Widget rail + StatusChip + StepList | — | `POST /api/v1/ai/explain` (sujet `analysis/<instrument>`) + `GET /api/v1/ai/status` | oui | — |

**Bilan : 35 modules — 24 servis, 11 déclarés absents.** Contre 31 modules dont
18 servis aujourd'hui. Les six modules réellement nouveaux
(`freshness-budget`, `bars-integrity`, `sec-conflicts`, `coverage-rejects`,
`gates-ledger`, `overlays-legend`) et les huit modules enrichis ne coûtent
**aucun** travail serveur : ils affichent des champs déjà calculés par Python et
jetés à l'affichage.

## 7. Intelligence gratuite récupérée

Ce que la page cible affiche et que la page actuelle jette, champ par champ.

| Champ servi | Où il apparaît désormais |
|---|---|
| `freshness_policy.{budget_seconds, kind, version}` | `freshness-budget` — l'âge devient une jauge bornée au lieu d'un « il y a 3 j » sans échelle |
| `bars.discarded[].{index, reason}` | `bars-integrity` — quelles barres, et pourquoi |
| `bars.age_seconds`, `bars.observed_as_of` | `bars-integrity`, `instrument-signal`, `dossier-lineage` |
| `bars.count` | `bars-integrity` — et **jamais** replié sur zéro (voir §10) |
| `indicators.realized_volatility.series` | `volatility-series` — série glissante enfin tracée |
| `indicators.atr.series` | `atr-series` |
| `indicators.relative_strength.series`, `.common_sessions` | `relative-strength-series` |
| `indicators.*.unit`, `.available_bars` | lues et affichées ; plus aucun `%` ni `(ratio)` codé en dur |
| `indicators.*.calculation.{calculation_id, engine_version, input_hash, result_hash, status}` | `ProvenanceLine` de chaque module d'étude + `dossier-lineage` (cinq champs sur six étaient jetés) |
| `indicators.overlays.{sma, ema, bollinger_bands}` | **tracés sur la dominante** + `overlays-legend` |
| `indicators.oscillators.{rsi, macd}` | `rsi`, `macd` |
| `indicators.rebased_comparison` | `rebased-comparison`, désormais sur Analyse |
| `advice.gates[].observed_values`, `.thresholds`, `.version`, `.evidence_ids` | `gates-ledger` — la preuve chiffrée des dix portes |
| `advice.{advice_id, instrument_id, input_snapshot_id, evidence_ids, scenario_ids, supersedes}` | `verdict` + `identity-reference` + `dossier-lineage` |
| `coverage.{rejected_records, lookback_seconds}` | `coverage-rejects` |
| `evidence.{source, clusters_total}`, `clusters[].{rights, member_event_ids}` | `evidence-clusters` — le compte des clusters formés est **toujours** visible, plus seulement quand il n'y en a aucun |
| `scenarios.value_nature` | `scenarios` — le badge de nature vient du serveur, il n'est plus écrit en dur |
| `scenarios.basis.{multiplier, currency, iv, con_id, chain_snapshot_version}` | `scenarios` — une grille de P&L d'option a enfin sa devise et son multiplicateur |
| `scenarios.iv_scenarios`, `scenarios.grid[1..]`, `calculation.input_hash` | `scenarios` — **tous** les scénarios, plus seulement `grid[0]` |
| SEC `facts[].{available_at, accession}` | `sec-facts` — un fait point-in-time retrouve sa date de disponibilité |
| SEC `coverage.{published_filings, published_facts, truncated_facts, corrections_observed}` | `sec-facts` — la troncature de la table est **dite** |
| SEC `conflicts[]` | `sec-conflicts` — le contenu, plus seulement le compte |
| `markets/overview → tickers[].{return_1d, currency, quality, synthetic, previous_close, previous_trading_day}` | `instrument-signal` |
| `markets/overview → tickers[].{weight_in_sector_pct, weight_global_pct}` | `peers` |

**Dette serveur restante, à porter ailleurs** (aucune n'est bloquante ici) :
`_calculation_meta` ne persiste que six des quinze champs du `CalculationRecord`
(`code_sha`, `source_event_ids`, `assumptions`, `parameters`, `random_seed`,
`started_at`, `completed_at`, `warnings` sont jetés) ; les trois hypothèses
exactes du repricing de scénarios sont construites puis perdues, si bien que
`ScenarioPanel` les réécrit à la main en français ; `basis` ne publie ni le spot
de référence, ni le taux, ni le rendement de dividende, ni la maturité qui
construisent pourtant la grille. Trois demandes de contrat pour **LOT 8**.

## 8. Nouvelles primitives exigées

### `DataTable` — une seule, et elle en remplace huit

**Rôle.** LA table financière de Titan Ledger. Chiffres tabulaires alignés à
droite (`font-variant-numeric: tabular-nums`, Geist Mono), `<caption>` **réel
dans le flux du document** — pas un `aria-label` qui disparaît à l'impression et
en mode tableau de lecteur d'écran —, en-têtes portant l'unité et la devise
**servies**, hauteur bornée avec défilement interne et en-tête collante,
conteneur `overflow-x: auto` propre.

**Elle remplace** les huit tables écrites à la main dans cet espace : OHLCV,
registre des portes, faits SEC, conflits SEC, pairs, refus de couverture, barres
écartées, comparaison base 100. Elle efface d'un coup le défaut « quatre tables
financières sans `<caption>` ».

**Donnée exigée.**

```ts
interface DataTableColumn {
  key: string;
  label: string;
  unit: string | null;        // unité SERVIE, jamais devinée
  currency: string | null;    // devise SERVIE
  numeric: boolean;           // → alignement droite + tabular-nums
  absentLabel: string;        // phrase servie quand la cellule n'est pas publiée
}
interface DataTableCell { text: string | null; sign?: SignGroup; code?: string }
interface DataTableProps {
  columns: readonly DataTableColumn[];
  rows: readonly { id: string; cells: Readonly<Record<string, DataTableCell>> }[];
  caption: string;            // obligatoire, non vide — sinon la primitive refuse
  ariaLabel?: string;
  maxRows?: number;
  moreLabel?: string;         // phrase SERVIE de troncature (ex. SEC truncated_facts)
  emptyLabel: string;         // phrase d'absence, sans chiffre
}
```

Aucune valeur n'est formatée : toutes les chaînes sont **relayées verbatim**.
Pas d'arrondi, pas de séparateur de milliers ajouté, pas de conversion.

**États.** `ready`, `refreshing`, `empty` (`emptyLabel`), `partial` (bandeau de
troncature **alimenté par un champ servi**, jamais déduit d'un `maxRows` local),
`error`. Une cellule non publiée porte `data-absent` et l'`absentLabel` de sa
colonne ; une cellule publiée mais non scalaire porte « valeur non reconnue » —
la distinction entre « non publié » et « non relayable » est la même que celle
qu'`analysisView.ts` fait déjà pour les preuves de portes.

### Aucune autre primitive nouvelle

- Jauge âge/budget et RSI → `LinearGauge` (existe, prend `valuePct`,
  `valueText`, `boundsText`, `markers`, `segments`, `method`, `reason`, `status`).
- Grille de scénarios → `CellGrid` (existe, prend `rows`, `cols`, `cells`,
  `legend`, `caption`, `onOpenRow`).
- Clusters et catalyseurs → `ActivityFeed` (existe).
- Portes, limites, overlays → `StepList` (existe, porte statut + preuves).
- Liens croisés `evidence_ids` / `scenario_ids` → `StatusChip` avec `code`.

### Deux corrections de primitives existantes (obligatoires)

1. **`AbsentModule` — `aria-labelledby` cassé.** `id={`vx-absent-${reason}-${title}`}`
   produit un `id` contenant des espaces ; comme `aria-labelledby` est une
   **liste** d'`id` séparés par des espaces, le nom accessible est perdu.
   Correction : `id` dérivé de l'`id` **du module** (déjà slug), jamais du titre.
2. **`AbsentModule` — treize régions live simultanées.** `role="status"` sur
   chaque module absent fait annoncer onze contenus purement statiques au
   chargement. Correction : `role="status"` supprimé du conteneur ; l'absence est
   du contenu de page, pas un événement.

## 9. Textes d'absence (exacts, sans aucun chiffre)

| Module | Texte |
|---|---|
| `instrument-signal` | Aucune clôture de référence n'est publiée pour cet instrument dans l'instantané des marchés. |
| `identity-reference` | L'identité canonique de cet instrument n'est pas publiée dans cet instantané. |
| `freshness-budget` | Aucune politique de fraîcheur n'accompagne cet instantané : son âge ne peut être jugé contre aucun budget publié. |
| `price-chart` | Aucune barre valide n'est publiée pour cet instrument : aucune bougie n'est tracée. |
| `bars-integrity` | Le compte des barres retenues n'est pas publié dans cet instantané : aucun bilan d'intégrité n'est affiché. |
| `overlays-legend` | Le moteur n'a publié aucune moyenne mobile pour cette série : aucune superposition n'est tracée. |
| `volatility-series` | Le moteur n'a publié aucune volatilité réalisée pour cette série. |
| `atr-series` | Le moteur n'a publié aucune amplitude vraie moyenne pour cette série. |
| `rsi` | Le moteur n'a publié aucun indice de force relative pour cette série. |
| `macd` | Le moteur n'a publié aucune ligne MACD pour cette série. |
| `rebased-comparison` | Aucune comparaison base 100 n'est publiée : les deux séries ne partagent pas de calendrier commun servi. |
| `relative-strength-series` | Aucune force relative n'est publiée : le calendrier commun avec l'indice déclaré n'est pas servi. |
| `synchronized-series` | Aucun contrat d'alignement multi-séries n'est publié ; aligner plusieurs calendriers ici serait un calcul hors autorité. |
| `series-annotations` | Un repère posé sur une série est une donnée d'utilisateur persistée dont le propriétaire et le contrat ne sont pas tranchés. |
| `linked-watches` | Aucun contrat de surveillance rattachée à un instrument n'est publié, et son propriétaire n'est pas tranché. |
| `sec-facts` | Aucun dépôt officiel n'est publié pour cet instrument. |
| `sec-conflicts` | Le relais SEC ne publie aucun conflit de faits pour cet instrument. |
| `fundamental-quality` | Aucune source ne publie de note de solidité fondamentale ; la dériver des faits relayés serait un calcul hors autorité. |
| `valuation` | Aucune source ne publie de multiple ni de juste valeur ; rapprocher un prix d'un fait relayé serait une valorisation calculée hors autorité. |
| `analyst-revisions` | Aucune source de consensus d'analystes n'est collectée, et aucune collecte non autorisée n'est tentée. |
| `evidence-clusters` | La fusion n'a retenu aucun cluster d'observations pour cet instrument. |
| `catalysts` | Le calendrier ne publie aucun événement rattaché à cet instrument. |
| `peers` | L'instantané des marchés ne publie aucun secteur contenant cet instrument. |
| `regime` | Le moteur déclare lui-même qu'aucune évaluation de régime n'existe pour cette population ; une classification serait descriptive d'un observé qui n'est pas publié. |
| `levels` | Aucun niveau n'est publié dans ce dossier ; en tracer un ici serait une décision de calcul qui appartient au serveur. |
| `gates-ledger` | Le moteur n'a publié aucune porte pour ce dossier. |
| `coverage-rejects` | Le dossier ne publie aucun bilan de couverture pour cette fenêtre d'observation. |
| `key-risks` | Le moteur n'attache aucune limite déclarée à ce verdict. |
| `contradictions` | Le dossier ne publie aucune liste de contradictions ; en dresser une dans le navigateur créerait une seconde autorité. |
| `verdict` | Le moteur n'a publié aucun verdict pour ce dossier. |
| `scenarios` | Aucune chaîne d'options saine n'est publiée pour cet instrument : aucune grille n'est calculée. |
| `thesis` | Une thèse déclarée est une donnée d'utilisateur persistée dont le propriétaire et le contrat ne sont pas tranchés. |
| `model-confidence` | Le moteur ne publie aucune probabilité calibrée, avec son horizon, sa population et sa validation hors échantillon, pour ce verdict. |
| `dossier-lineage` | Aucune lignée n'est publiée avec cet instantané. |
| `ai-explanation` | Aucun fournisseur d'explication n'est activé pour cette installation : le panneau reste vide et n'invente aucun commentaire. |

### Les huit états d'une valeur, distincts à l'écran

`absent` · `zéro` · `retardé` · `périmé` · `estimé` · `théorique` · `simulé` ·
`réel`. Chacun a sa forme : `data-absent` + phrase française (absent) ; chiffre
neutre sans signe (zéro publié) ; `StatusChip` ambre `RETARDÉ` + population
`DELAYED` ; filigrane `PÉRIMÉ` + `FreshnessBadge` hors budget ; `StatusChip`
`ESTIMÉ` ; `StatusChip` violet portant `scenarios.value_nature` **servi**
(théorique) ; `StatusChip` `SYNTHÉTIQUE` non masquable (simulé, depuis
`clusters[].synthetic` et `tickers[].synthetic`) ; aucun badge (réel).

## 10. Deux absences aujourd'hui converties en zéro — interdites

La porte `no-ambiguous-dash` ne les voit pas, parce que ce ne sont pas des
glyphes. Elles restent des violations de la loi 4 et la page cible les interdit
explicitement :

- `AnalysisPage.tsx:196` — `${bars.count ?? 0} barre(s) valides` affiche
  « 0 barre(s) valides » à côté d'une figure qui en dessine soixante.
  Cible : quand `bars.count` n'est pas publié, `bars-integrity` écrit
  « compte de barres non publié », jamais un nombre.
- `EvidenceRail.tsx:12` — `{evidence.considered ?? 0} observation(s) considérée(s)`.
  Cible : `evidence-clusters` écrit « nombre d'observations considérées non
  publié », et affiche `considered` **et** `clusters_total` en permanence, pas
  seulement dans la branche vide.

Deux phrases cassées par la passe T4-5 sont réparées au passage :
« âge publié non s. » (`AnalysisPage.tsx:133`) et « nombre non publié d' événement(s) »
(`EvidenceRail.tsx:26`) — une élision suivie d'une espace. Règle générale : une
absence se compose comme une phrase entière, jamais par concaténation d'un
fragment dans un gabarit.

Trois autres défauts structurels disparaissent par construction :
la mini-série de l'en-tête ne superpose plus trente clôtures et quatorze volumes
sur la même largeur (le volume passe sur l'échelle de temps de la dominante) ;
les titres ne sont plus rendus deux fois (`Widget` porte **le** titre, l'enfant
n'en réaffiche aucun — correction déjà appliquée côté Graphiques par
`RebasedComparison.tsx:22-24`) ; et le mot « non publié » n'est plus enfermé
dans un `<code>`, qui présentait une phrase française comme un identifiant
technique.

Enfin, la contradiction la plus grave de l'espace est éteinte : le motif
`NO_SOURCE` « le registre des calculs ne publie aucun oscillateur » est supprimé,
puisque `apps/worker/.../analysis.py` publie `indicators.oscillators.rsi` et
`.macd` dans le DTO que la page a déjà chargé.

## 11. États dégradés attendus

`Widget` publie onze états ; la page les couvre tous. Règle transversale : **dans
tout état qui ne montre pas de contenu, les enfants ne sont pas rendus du tout** —
pas de zéro de remplacement, pas de squelette qui ressemble à une valeur.

| État | Déclencheur servi | Dominante | Modules | Action principale |
|---|---|---|---|---|
| `loading` | requête en vol, aucune donnée | cadre + titre + question, aucune figure, aucun axe | cadre + titre + question | désactivée, `aria-disabled` |
| `refreshing` | requête en vol, données précédentes datées | figure conservée + `LiveBadge` « rafraîchissement » ; **`as_of` reste celui affiché**, jamais l'horloge locale | inchangés | active |
| `empty` | `data.state === 'empty'` | « Aucune barre valide n'est publiée pour cet instrument : aucune bougie n'est tracée. » | chacun son texte d'absence du §9 | active (lignée servie) |
| `partial` | `bars.status !== 'OK'`, `bars.discarded.length > 0`, `bars.quality !== 'VALID'`, ou un bloc d'indicateur en `INSUFFICIENT_SAMPLE` / `REFUSED` | figure tracée sur les barres admises + bandeau nommant le motif servi | `bars-integrity` détaille chaque barre écartée ; chaque module d'étude relaie son `status`, sa `reason`, son `detail` et son `available_bars` **servis** | active |
| `delayed` | `population === 'DELAYED'` | `StatusChip` ambre `RETARDÉ` + population servie ; la figure garde sa couleur mais l'en-tête porte la nature | tous les modules du DTO héritent du chip | active |
| `stale` | `data.state === 'stale'` ou `bars.fresh === false` | filigrane `PÉRIMÉ`, `LinearGauge` de `freshness-budget` au-delà du budget avec la borne dite ; `PeriodTabs` **gelé** | figures conservées, aucune valeur retirée en silence | active ; l'IA se refuse sur un dossier périmé |
| `offline` | perte de lien SSE / réseau | figure conservée, `LiveBadge` `HORS LIGNE`, dernier `as_of` **servi** rappelé | idem | gelée si elle dépend du live ; l'inspecteur reste ouvrable |
| `error` | HTTP non 2xx, corps illisible, contrat invalide | « Le dossier n'a pas pu être lu ; aucune série n'est tracée. » + `trace_id` **si servi**, jamais un message de pile | idem | désactivée |
| `auth-required` | `GET /api/v1/ai/status` refuse | — | `ai-explanation` seul : « fournisseur non activé », motif servi `B-05_HUMAN_DECISION_PENDING` | — |
| `closed` | séance fermée déclarée par le serveur | `StatusChip` `SÉANCE FERMÉE` ; le budget appliqué est celui de séance fermée, **nommé** | — | active |

Un état inconnu **échoue visiblement** ; il ne se fond jamais dans `ready`.

## 12. Parcours clavier

Ordre de tabulation = ordre du DOM = ordre de lecture SIGNAL → PREUVE → RISQUE →
DÉCISION. Aucun `tabindex` positif.

1. **Lien d'évitement** « Aller au contenu » (shell).
2. **Sélecteur d'instrument** — `combobox` unique de la page, `aria-expanded`,
   flèches ↑ ↓ pour parcourir, `Entrée` pour ouvrir le dossier, `Échap` pour
   fermer sans changer. Il n'y en a **qu'un** : c'est le cœur de l'absorption.
3. **Action principale** « Ouvrir l'inspecteur du dossier » — `Entrée` / `Espace`.
4. **Lien d'ancre** « Aller aux études de série » → `#etudes`, qui porte
   `tabindex="-1"` et reçoit le focus programmatique.
5. **`PeriodTabs`** — `role="tablist"`, ← → pour changer d'onglet, `Origine` /
   `Fin` aux extrémités, sélection automatique au déplacement. Un onglet dont la
   fenêtre n'est pas servie est `aria-disabled` et **dit** son motif servi.
6. **Figure dominante** — `tabindex="0"`, `role="img"` avec `aria-label` portant
   instrument, unité, devise, fuseau, source et fraîcheur. `Entrée` bascule sur
   la table OHLCV équivalente, qui est la vraie alternative textuelle. Pas de
   piège au clavier ; `Échap` sort du canevas.
7. **Modules**, dans l'ordre du tableau du §6. Chaque `DataTable` est une région
   défilable atteignable (`tabindex="0"` sur le conteneur `overflow`), avec son
   `<caption>` comme nom accessible.
8. **`CellGrid` des scénarios** — en-tête de ligne = bouton réel
   (`aria-pressed`), `Entrée` ouvre l'inspecteur sur l'horizon choisi.
9. **Chips croisés** `evidence_ids` / `scenario_ids` du `verdict` — chacun est un
   lien interne vers l'ancre du module correspondant, qui reçoit le focus.
10. **Panneau inspecteur** — piège de focus tant qu'il est ouvert, `Échap` le
    ferme, **le focus revient sur le déclencheur exact**.

Contraintes vérifiées : WCAG 2.2 AA, zéro violation axe critique ou sérieuse,
focus visible partout (anneau ambre 2 px, contraste ≥ 3:1 contre la surface),
zoom 200 % sans perte de contenu, `prefers-reduced-motion` respecté (la
surbrillance de valeur mise à jour devient un contour statique), aucune
information portée par la seule couleur — chaque signe est doublé d'un glyphe
`▲ ▼ =` et d'un libellé en `vx-visually-hidden`.

## 13. Cibles de rendu

`1280×800`, `1440×900`, `1600×1000`. À 1280 la planche garde ses douze colonnes
et sa partition ; aucune rangée ne devient vide, la respiration de la colonne 9
reste large d'un douzième. `1024×768` sert de contrôle de dégradation laptop :
les rangées `3+3+3+3` passent en `6+6`, la respiration disparaît. Aucun viewport
mobile, aucune barre d'action basse, aucun geste tactile — `Mobile UI = LATER`.

## 4. Réfutations adversariales — 40 à traiter avant implémentation

**Verdict : CORRECTIONS_REQUISES** — J'ai vérifié dans le dépôt, champ par champ, les 24 modules déclarés « servi : oui ». La charpente tient : `bars.*` (analysis.py:1998-2014), `indicators.overlays.{sma,ema,bollinger_bands}` et `indicators.oscillators.{rsi,macd}` (analysis.py:1150-1191), les séries glissantes sous `INDICATOR_SERIES_KEY = \"series\"` (analysis.py:329, 921, 968, 1405), `evidence.*` (analysis.py:1742-1759), `coverage.*` (analysis.py:2165-2168), les dix portes avec `observed_values`/`thresholds`/`version` (contracts/decision.py:44-51, gates.py:800-840 — dix entrées confirmées), `scenarios.basis.*` (analysis.py:1891-1908), `MarketsTicker` avec ses poids et sa qualité (schemas.py:204-220), la couverture SEC (sec_fundamentals.py:279-291) : tout cela existe réellement. Les onze modules déclarés absents sont, eux, honnêtement absents.

Mais quinze défauts invalident la conception en l'état. Cinq sont des champs qui N'EXISTENT PAS au contrat : `schema_version` (le worker l'écrit, l'API ne le relaie pas — schemas.py:383-397), `sectors[].name` (c'est `sector` + `label`), `items[]` du calendrier (c'est `agenda[]`), `status.state` de l'IA (AiStatusResponse n'a que provider/reason/deterministic_template_available), `facts[].period` (c'est `period_start` + `period_end`). Un est une violation directe de la loi 3 : la jauge âge/budget de `freshness-budget` exige un `valuePct` SERVI — le contrat écrit de LinearGauge l'exige mot pour mot — et aucun pourcentage âge/budget n'est publié nulle part ; la construire impose une division dans le navigateur.

Trois défauts sont des sur-revendications : `scenarios.grid[1..]` n'existe pas (un seul scénario, IV inchangée — analysis.py:1855-1862), `advice.supersedes` est structurellement toujours nul sur cette route, et `available_bars` n'est publié que dans la branche d'absence, jamais en état OK — le §7 « intelligence gratuite récupérée » compte donc trois gains qui n'existent pas. Deux touchent la loi 4 : les textes d'absence de `rebased-comparison` et `relative-strength-series` nomment un motif générique là où le serveur en publie cinq distincts, et `identity-reference` annonce six mesures dont l'indice de référence, absent dès qu'aucun benchmark n'est déclaré — c'est-à-dire dans le profil de développement livré. Un touche la loi 7 : `instrument-signal` fusionne deux instantanés indépendants (dossier d'analyse et instantané des marchés) sous une seule ligne de provenance, alors que chacun a son `as_of`, son âge et son budget, et que leurs deux `last_close` peuvent diverger.

Deux défauts enfin sont extérieurs à la lentille mais bloquants : les chaînes servies que `key-risks`, `verdict` et `gates-ledger` doivent relayer verbatim sont en ANGLAIS (risk_summary, limitations, explanation_facts, gates[].message) sur une interface déclarée entièrement française — la fiche ne le nomme nulle part ; et la teinte « cyan » réservée aux quatre modules d'étude technique n'existe dans aucun jeton (`pageAccent` = macro | option | warning ; `SPARK_TONES` est une union fermée sans cyan) tandis que `pageAccent.ts:42` déclare `analysis: null`.

Deux incohérences internes, hors violations numérotées, méritent d'être corrigées au passage : la fiche promet « un seul DTO chargé une fois » alors que les 24 modules servis exigent cinq routes (analysis, markets/overview, sources/sec/{instrument}/fundamentals, calendar, ai/status + ai/explain) avec cinq fraîcheurs distinctes ; et `price-chart` annonce « trois séries de lignes servies (SMA, EMA) » là où il y en a deux.

Fichiers de preuve principaux : /home/user/vertex-merge/apps/worker/src/vertex_worker/analysis.py, /home/user/vertex-merge/apps/api/src/vertex_api/schemas.py, /home/user/vertex-merge/apps/api/src/vertex_api/snapshot_views.py, /home/user/vertex-merge/apps/api/src/vertex_api/ai_explain.py, /home/user/vertex-merge/apps/api/src/vertex_api/calendar.py, /home/user/vertex-merge/apps/worker/src/vertex_worker/sec_fundamentals.py, /home/user/vertex-merge/apps/worker/src/vertex_worker/profiles.py, /home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/information.py, /home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/decision/gates.py, /home/user/vertex-merge/apps/web/src/components/widgets/LinearGauge.tsx, /home/user/vertex-merge/apps/web/src/design/tokens.ts, /home/user/vertex-merge/apps/web/src/api/schema.d.ts.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `dossier-lineage` | Loi 7 — toute valeur critique porte source, as_of, méthode et version (et loi 4 : un champ non publié n'est pas une valeur) | apps/api/src/vertex_api/schemas.py:383-397 — `AnalysisResponse` déclare state, snapshot_version, as_of, age_seconds, freshness_policy, population, instrument, engine_version, bars, indicators, evidence, scenarios, advice, coverage, reason. Il n'y a AUCUN champ `schema_version`. Le worker l'écrit bien dans le contenu persisté (apps/worker/src/vertex_worker/analysis.py:2155 `"schema_version": ANALYSIS_SCHEMA_VERSION`), mais `build_analysis_response` (apps/api/src/vertex_api/snapshot_views.py:2186-2205) ne le relaie pas. Le client généré le confirme : apps/web/src/api/schema.d.ts:1130-1174 ne contient pas `schema_version` (la seule occurrence du dépôt est ligne 2397, pour l'export de performance). | Retirer `schema_version` de la donnée de `dossier-lineage` ET du pied de `instrument-signal` (« schéma v<schema_version> »), qui l'invoquent tous les deux. Si la version de schéma doit être affichée, c'est une demande de contrat serveur (champ à ajouter dans `AnalysisResponse` + `build_analysis_response` + régénération du client) et le module devient partiellement bloqué, il n'est pas « servi » aujourd'hui. |
| `catalysts` | Loi 4 — un champ inexistant ne peut pas être affiché ; loi 7 — la donnée doit être nommée par son contrat réel | apps/api/src/vertex_api/calendar.py:233-262 — `CalendarResponse` publie `agenda: tuple[FrozenStrMapping, ...]`, PAS `items`. Il n'existe aucun champ `items` sur cette route. Les entrées portent bien `ticker` (apps/worker/src/vertex_worker/calendar.py:1041) et `scope` (:1042), donc la sélection est possible — mais sous un autre nom. | Écrire `GET /api/v1/calendar → agenda[]` filtré sur `agenda[].ticker`. Et déclarer explicitement le trou : un événement `scope = MACRO_GLOBAL` (apps/worker/src/vertex_worker/calendar.py:187-189) n'est rattaché à aucun ticker et disparaîtrait silencieusement du module ; le texte d'absence ou un compteur servi doit le dire. |
| `peers` | Loi 4 / loi 7 — le champ nommé doit exister au contrat | apps/api/src/vertex_api/schemas.py:441-450 — `MarketsSector` = {sector, label, declared_count, covered_count, tickers}. Il n'existe pas de champ `name`. La conception l'invoque deux fois : `peers` (« markets/overview — sectors[].name ») et `identity-reference` (« markets/overview — sectors[].name »). | Remplacer `sectors[].name` par `sectors[].sector` (le code canonique) et/ou `sectors[].label` (le libellé), en disant lequel des deux est affiché. `declared_count` et `covered_count` sont servis et manquent à la table des pairs : la couverture réelle du secteur doit être dite, sinon la table laisse croire à un secteur complet. |
| `ai-explanation` | Loi 7 — le champ cité doit exister ; loi 4 — l'absence déclarée doit être la vraie | apps/api/src/vertex_api/ai_explain.py:1058-1063 — `AiStatusResponse` = {provider: Literal["DISABLED"], reason: Literal["B-05_HUMAN_DECISION_PENDING"], deterministic_template_available: Literal[True]}. Il n'y a AUCUN champ `status.state` (le pied du module écrit « état <status.state> »). Pire, le texte d'absence (« le panneau reste vide et n'invente aucun commentaire ») est faux : `deterministic_template_available` vaut True et `POST /api/v1/ai/explain` (apps/api/src/vertex_api/routes.py:509-536) renvoie un `AiAnswer` réel avec claims, contradictions, missing_data et evidence_catalog (ai_explain.py:1012-1034). | Pied = « fournisseur <status.provider> · motif <status.reason> · gabarit déterministe <status.deterministic_template_available> », plus les champs propres de la réponse (`provider`, `template_version`, `state`, `snapshot_version`, `content_hash`). Réécrire le texte d'absence : ce qui est absent, c'est un FOURNISSEUR de modèle, pas l'explication — le gabarit déterministe, lui, répond. |
| `freshness-budget` | Loi 3 — le navigateur ne calcule jamais un ratio | apps/web/src/components/widgets/LinearGauge.tsx:5-8 et :31 — contrat écrit de la primitive : « Le navigateur ne calcule ni pourcentage, ni seuil, ni position du marqueur. Toutes les coordonnées arrivent SERVIES en pourcentage » ; `valuePct: string \| null` = « Position SERVIE en pourcentage ». Or apps/api/src/vertex_api/schemas.py:141-143 (`FreshnessPolicyView`) ne publie que {budget_seconds, kind, version} et `AnalysisResponse` que `age_seconds` (entier). Aucun `age_pct` n'existe dans le dépôt (grep vide sur age_pct/budget_pct/age_ratio). Les trois seuls consommateurs actuels de LinearGauge reçoivent bien un pourcentage SERVI : apps/web/src/pages/markets/BreadthPanel.tsx:77 (`breadth.value_pct`), :87 (`breadth.coverage_pct`), et AnalysisModules.tsx:546 (`ligneRsi.last`, déjà en index_0_100). Poser age_seconds sur budget_seconds impose donc `age/budget*100` dans le navigateur. | Deux issues honnêtes, aucune troisième. (a) Demander au serveur la position (`freshness_policy.age_pct` ou équivalent servi) — le module devient alors bloqué par un lot de contrat, pas « servi ». (b) Abandonner la jauge et relayer verbatim `age_seconds`, `freshness_policy.budget_seconds`, `state` et `bars.fresh` dans des `Metric` + `FreshnessBadge` — l'échelle est dite en toutes lettres sans qu'aucune coordonnée soit calculée. |
| `scenarios` | Loi 4 — une valeur non publiée n'est ni un zéro ni une promesse | apps/worker/src/vertex_worker/analysis.py:1855-1862 — `scenario_grid((leg,), spots, times, ((iv_value,),), rate, dividend_yield)` : UN SEUL scénario d'IV est passé. :1906-1907 — `"iv_scenarios": [[_num_string(iv_value)]]` et `"grid": [...]` de longueur 1. La méthode enregistrée le dit : :1868 « single long leg, IV unchanged scenario » et :1883 « single scenario: implied volatility unchanged ». `grid` est indexé [scenario][time][spot] (packages/python/vertex_core/src/vertex_core/calculations/options.py:1185, :1221). Donc `scenarios.grid[1..]` — que le §7 « Intelligence gratuite récupérée » revendique comme un gain — N'EXISTE PAS, et une CellGrid 2D spots × horizons ne peut pas montrer « TOUS les scénarios ». | Supprimer du §7 la ligne « `scenarios.iv_scenarios`, `scenarios.grid[1..]` … tous les scénarios, plus seulement grid[0] » : il n'y a rien à récupérer. La CellGrid trace `grid[0]` (horizons × spots) et la carte DOIT écrire l'hypothèse servie : un seul scénario, volatilité implicite inchangée, une jambe longue, P&L avant coûts déclarés. |
| `verdict` | Loi 4 — un champ structurellement nul ne se présente pas comme une donnée servie | apps/worker/src/vertex_worker/analysis.py:1146-1181 — l'`AdviceInputs` construit par `build_analysis_content` ne renseigne JAMAIS `supersedes` ; packages/python/vertex_core/src/vertex_core/decision/advice.py:286 se contente de relayer `inputs.supersedes`, et packages/python/vertex_core/src/vertex_core/contracts/decision.py:79 le déclare `NonEmptyStr \| None = None`. Sur la route `/analysis/{instrument}`, `advice.supersedes` est donc toujours `null`. La conception en fait pourtant un `StatusChip` (« remplace un avis antérieur ») et une ligne de pied (« remplace <advice.supersedes> »). | Retirer le chip et la mention du pied, ou les déclarer explicitement comme une capacité de contrat non alimentée sur cette route (le chaînage des avis successifs n'est pas produit par ce handler) — jamais comme un élément servi que le lecteur croirait absent par hasard. |
| `key-risks` | Loi 4 / règle produit « tous les textes d'interface sont en FRANÇAIS » — un relais verbatim d'anglais n'est pas une interface française | Les chaînes servies que ces modules affichent verbatim sont en ANGLAIS. apps/worker/src/vertex_worker/analysis.py:2130-2144 : `risk_summary` = « SYNTHETIC development population retained; no authoritative market risk assessment exists for this instrument ». :1163 : `limitations` = `("SYNTHETIC development population",)`. :2085-2098 : `explanation_facts` = « 60 SYNTHETIC daily bars from … to … », « last SYNTHETIC close … ». packages/python/vertex_core/src/vertex_core/decision/gates.py:105-264 : `gates[].message` = « instrument identity is unresolved », « snapshot is outside its freshness window », etc. `key-risks` (StepList sur risk_summary + limitations), `verdict` (StepList sur explanation_facts) et `gates-ledger` (colonne message) rendraient donc de l'anglais comme prose d'interface. | Nommer le problème dans la fiche et choisir : soit une demande de contrat (champs français servis par le moteur, ex. `risk_summary_fr` / `message_fr`), soit un rendu explicitement typé « texte serveur (anglais) » dans un canal distinct de la prose française, jamais fondu dans la phrase de la carte. Ne pas traduire dans le navigateur : ce serait réécrire un fait du moteur. |
| `rebased-comparison` | Loi 4 — une absence dit SON motif servi, pas un motif générique | apps/worker/src/vertex_worker/analysis.py:287-289 et :306-307 déclarent cinq statuts d'absence distincts : `NO_BENCHMARK_DECLARED`, `BENCHMARK_NOT_OBSERVED`, `INSTRUMENT_IS_BENCHMARK`, `BENCHMARK_CURRENCY_MISMATCH`, `BENCHMARK_ADJUSTMENT_BASIS_MISMATCH`, plus `INSUFFICIENT_SAMPLE` (:281). Les blocs les publient avec leur `detail` (:1517-1587). La conception n'écrit qu'UNE phrase — « les deux séries ne partagent pas de calendrier commun servi » — qui est fausse pour quatre des cinq motifs (aucun indice déclaré, l'instrument EST l'indice, devise divergente, base d'ajustement divergente). Même défaut sur `relative-strength-series` (« le calendrier commun avec l'indice déclaré n'est pas servi »). | Une phrase d'absence par statut typé, et relais verbatim de `status`, `reason`, `detail`, `benchmark`, `common_sessions`, `minimum_sessions`, `currency`/`benchmark_currency`, `adjustment_basis`/`benchmark_adjustment_basis` selon le cas — l'écran ne doit jamais nommer un motif que le serveur n'a pas publié. |
| `identity-reference` | Loi 4 — une absence de champ à l'intérieur d'un module servi doit être dite champ par champ | Le module annonce six `Metric` servis dont `indicators.relative_strength.benchmark`. Or apps/worker/src/vertex_worker/analysis.py:1303-1305 : quand aucun indice n'est déclaré, le bloc vaut `{"status": NO_BENCHMARK_DECLARED, "detail": "aucun indice de référence déclaré"}` — SANS clé `benchmark`. Et le profil livré ne déclare aucun indice : apps/worker/src/vertex_worker/analysis.py:437-441 (`DEV_SYNTHETIC_ANALYSIS_CONFIG` laisse `benchmark` au défaut `None`, :403-406), tandis que le profil réel ne le déclare que sous condition (apps/worker/src/vertex_worker/profiles.py:296, `REFERENCE_BENCHMARK if REFERENCE_BENCHMARK in symboles else None`). Le module n'a qu'UN texte d'absence global, qui ne couvre pas ce trou partiel. | Donner à chacune des six mesures son propre texte d'absence servi. Pour l'indice : « aucun indice de référence n'est déclaré pour cette population » (relais de `detail`), et non un module entier déclaré absent ni un tiret. |
| `instrument-signal` | Loi 7 — chaque valeur critique porte SA source, SON as_of et SA fraîcheur | La donnée du module mélange deux instantanés indépendants : `analysis/{instrument}` (bars.last_close, bars.currency, bars.last_trading_day) et `markets/overview` (tickers[].last_close, previous_close, return_1d, return_1d_pct). Ce sont deux routes (apps/api/src/vertex_api/routes.py:329-347 et :351-372), deux instantanés distincts, chacun avec son propre `snapshot_version`, `as_of`, `age_seconds`, `state` et `freshness_policy` (apps/api/src/vertex_api/schemas.py:304-341 vs :383-397) — publiés par deux handlers différents (markets.py vs analysis.py). Le module ne porte qu'UNE ligne de pied (« IBKR daily_bar · observé le <bars.observed_as_of> · instantané v<snapshot_version> »). Les deux `last_close` peuvent diverger sans que rien ne le dise. | Soit une seule source pour la tuile, soit deux provenances distinctes et visibles (une par valeur), avec les deux âges et les deux budgets. Et si les deux `last_close` diffèrent, le dire — c'est exactement le cas de contradiction que la loi 4 exige de distinguer, pas d'harmoniser. |
| `sec-facts` | Loi 7 — la période d'un fait est une grandeur servie, pas une chaîne composée à l'écran | packages/python/vertex_core/src/vertex_core/contracts/information.py:64-65 — `FundamentalFact` porte `period_start: date \| None` et `period_end: date`. Il n'existe AUCUN champ `period`, que la conception nomme pourtant dans sa donnée (« facts[].{concept, value, unit, period, available_at, accession} ») et dans les colonnes de sa DataTable. | Deux colonnes servies, `period_start` et `period_end`, avec l'`absentLabel` de la colonne pour un `period_start` nul (fait instantané) — jamais une chaîne « début–fin » assemblée dans le navigateur, qui masquerait la distinction entre un fait de flux et un fait de stock. |
| `sec-conflicts` | Loi 4 — une colonne de table doit correspondre à un champ servi de la ligne | apps/worker/src/vertex_worker/sec_fundamentals.py:236-241 — chaque conflit publié vaut `{fact_key: [...], available_at, values, event_ids}`. Aucun champ « dépôts » (les accessions ne sont pas portées par la ligne de conflit, seulement les `event_ids` d'observation) et aucun compte de corrections par ligne : `corrections_observed` est un compteur d'instantané (:289), au même niveau que `conflicting_fact_keys` (:290). Les colonnes annoncées (« clé de fait, dépôts concernés, corrections observées ») en désignent donc deux qui n'existent pas au niveau ligne. | Colonnes = `fact_key`, `available_at`, `values` (les valeurs contradictoires relayées verbatim) et `event_ids`. `coverage.corrections_observed` et `coverage.conflicting_fact_keys` restent des KPI de module, jamais des cellules de ligne. |
| `overlays-legend` | Loi 4 / loi 7 — ne pas annoncer comme lu un champ absent de l'état servi | apps/worker/src/vertex_worker/analysis.py:1045-1053 — dans l'état `OK`, `_bloc_serie` publie {status, **parameters, unit, method, **publie, calculation} : PAS de `available_bars`, ni `reason`, ni `detail`. `available_bars` n'est publié que dans la branche `INSUFFICIENT_SAMPLE` (:1021-1023). Même chose pour `realized_volatility` (OK à :912-921, sans `available_bars`) et `atr` (OK à :961-967). Or le §7 de la fiche revendique « `indicators.*.unit`, `.available_bars` \| lues et affichées » comme une intelligence récupérée, et les modules `overlays-legend`, `rsi`, `macd`, `volatility-series`, `atr-series` listent tous `available_bars` dans leur donnée servie. | Retirer `available_bars` de la donnée des blocs SERVIS (il n'appartient qu'à l'absence nommée) et corriger le §7. Si le nombre de barres réellement consommées doit être visible en état OK, c'est une demande de contrat serveur explicite. |
| `volatility-series` | Loi 4 (état visuellement distinct) et discipline de jetons — une teinte non déclarée n'existe pas | apps/web/src/design/tokens.ts:94-98 — `pageAccent` = {macro, option, warning} ; apps/web/src/design/tokens.ts ne contient AUCUN token `cyan` (grep vide). apps/web/src/components/widgets/SparkFigure.tsx:21-29 — `SPARK_TONES` = silver \| macro \| option \| warning \| positive \| negative, union fermée : passer `tone="cyan"` est une erreur de type. apps/web/src/design/no-raw-colors.test.ts interdit un hex de substitution. La conception réserve pourtant « cyan aux modules d'étude technique » (`volatility-series`, `atr-series`, `rsi`, `macd`) et écrit « teinte cyan technique » dans le graphique de ce module. En outre apps/web/src/components/widgets/pageAccent.ts:42 déclare `analysis: null` — la page n'a aujourd'hui aucune teinte secondaire. | Utiliser `macro`, déjà la famille « contexte / technique » du catalogue (pageAccent.ts:31-33), pour les quatre modules d'étude. Introduire `cyan` exigerait un ADR de jeton, une entrée dans `tokens.ts`, dans `SPARK_TONES` et dans `PAGE_ACCENTS` — un travail de lot, pas une réserve de teinte décrétée dans une fiche de page. |

**Verdict : CORRECTIONS_REQUISES** — Vingt-cinq violations retenues, dont six bloquantes. La plus grave : la figure DOMINANTE peut tracer une série SYNTHÉTIQUE sous un pied « IBKR daily_bar » sans aucun marquage, parce que le bloc `bars` ne publie ni `synthetic` ni `population` (analysis.py:1997-2015) et que le §9 fait venir le bandeau SYNTHÉTIQUE uniquement des clusters et des tickers de marché — jamais des barres ; la nature réelle des barres n'existe que dans une phrase anglaise de `explanation_facts` (analysis.py:2089-2098), lue dans un autre module. Loi 4 rompue à l'endroit le plus visible de la planche.

Trois modules déclarés « servis » ne peuvent pas l'être sans faire calculer le navigateur. `freshness-budget` et `rsi` posent un repère sur `LinearGauge`, dont le contrat exige une position SERVIE en pourcentage (LinearGauge.tsx:6-10) que ni `freshness_policy` ni `indicators.oscillators.rsi` ne publient : il faut soit un ratio en TypeScript (loi 3), soit une jauge en permanence « non calculable ». `scenarios` pose une `CellGrid` dont chaque cellule exige une BANDE servie (CellGrid.tsx:18-30) que `scenarios.grid` ne publie pas : la teinte deviendrait un classement fait dans le navigateur, et la couleur serait seule porteuse.

Loi 2 : le scénario servi est, dans le contrat lui-même, l'achat hypothétique d'une jambe longue — `method=\"BSM repricing grid, single long leg, IV unchanged scenario\"` (analysis.py:1870), `premium=picked[\"ask\"]  # hypothetical buy of one leg` (1847). La fiche l'euphémise en « structure de base publiée » sans jamais dire en français ce que c'est, tout en imposant le relais verbatim de `calculation.method`. L'euphémisme ne tient pas si la chaîne servie s'affiche.

Loi 4 encore, quatre fois : l'état `delayed` repose sur `population === 'DELAYED'` que le dossier ne publie jamais (analysis.py:2078-2082) ; l'état `closed` repose sur une séance que rien ne sert ; `sec-facts` écrase `CONFLICTING_IDENTITY`, un refus de droits et une erreur de transport sous un unique « aucun dépôt officiel » ; `catalysts` écrase les sept états du calendrier — dont `not_entitled` — sous « aucun événement rattaché », alors que le rattachement au ticker est fait dans le navigateur et que `/api/v1/calendar` n'accepte aucun paramètre d'instrument (routes.py:431-435).

Français : toutes les chaînes que la fiche impose de relayer verbatim sont anglaises — les six `method` (analysis.py:1153-1187, 1870), les motifs typés (`invalid_bar`, `unordered_bars`, `INSUFFICIENT_SAMPLE`, `BENCHMARK_ADJUSTMENT_BASIS_MISMATCH`), les `explanation_facts` du verdict. La planche livrerait des colonnes entières de codes machine.

Loi 6 : 35 modules contre les « trois à cinq » de `.claude/rules/frontend.md`, cinq endpoints derrière une fiche qui annonce « un seul DTO chargé une fois », quatre sources sans état dégradé déclaré, et deux modules (`peers`, `regime`) qui posent une question sur le secteur, pas sur l'instrument. Le « visuel dominant unique » ne tient que devant la porte automatique qui compte les littéraux `rank=\"dominant\"`.

Enfin la composition dément sa propre règle : R8 et R9 sont toutes deux `3+3+3+3` et adjacentes, R12 et R13 toutes deux `6+6` et adjacentes, `6+6` revient quatre fois — une grille régulière là où le brief exige un bento. Et le §9, intitulé « sans aucun chiffre », contient « Aucune comparaison base 100 n'est publiée ».

Aucune de ces vingt-cinq corrections n'exige d'abandonner l'absorption de Graphiques : elles exigent de cesser de déclarer « servi » ce que le contrat ne publie pas, et de nommer les demandes de contrat correspondantes (LOT 8 pour `bars.population`, `method_label_fr`, bandes de scénarios et position de jauge ; LOT 9 pour le rattachement calendrier).

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `price-chart` | Loi 4 — absent / zéro / retardé / périmé / estimé / théorique / simulé / réel sont huit états distincts, et chacun le DIT à l'écran | apps/worker/src/vertex_worker/analysis.py:1997-2015 — le bloc `bars_block` ne publie AUCUNE clé `synthetic` ni `population`. La nature propre des barres est calculée à analysis.py:2089 (`bars_population = "SYNTHETIC" if _is_synthetic_bar(chosen) else "REAL"`) puis enfermée dans des phrases anglaises de `explanation_facts` (2090-2098), jamais servie en champ structuré. Or le §9 de la fiche énumère limitativement les sources du bandeau SYNTHÉTIQUE : « depuis `clusters[].synthetic` et `tickers[].synthetic` » — les barres n'y figurent pas. Et le pied de `price-chart` inscrit « IBKR daily_bar » en dur. | Interdire le pied « IBKR daily_bar » codé en dur. Tant que le contrat ne publie pas `bars.population` / `bars.synthetic` (demande de contrat à porter au LOT 8, à ajouter aux trois déjà listées au §7), dériver l'état de la dominante du `population` de tête du DTO : `SYNTHETIC` ⇒ filigrane SYNTHÉTIQUE non masquable sur la figure elle-même + `StatusChip` dans la tête + provenance « population synthétique » à la place de « IBKR daily_bar ». Un dossier dont la population n'est pas publiée ne trace aucune bougie. |
| `scenarios` | Loi 2 — aucun ordre, jamais ; vocabulaire « acheter / vendre / ordre / buy / sell / order » interdit à l'écran | apps/worker/src/vertex_worker/analysis.py:1870 — `method="BSM repricing grid, single long leg, IV unchanged scenario"`, champ publié verbatim par `_calculation_meta` (analysis.py:500-508). analysis.py:1843-1848 — `premium=picked["ask"],  # hypothetical buy of one leg`. analysis.py:1883 — assumption « premium side ASK (hypothetical buy of one long leg) ». La conception nomme cet objet « la structure de base publiée » sans jamais dire en français ce qu'il est, et relaie `basis.right` (CALL/PUT) et `basis.premium_side` (ASK) bruts dans ses « Metric ×5 ». | Nommer explicitement l'objet dans le module : « scénario théorique de reprise sur un contrat d'option unique, côté ASK observé » — sans verbe transactionnel. Interdire le relais de `calculation.method` sur cette carte (la chaîne servie contient « single long leg »). Exiger au LOT 8 des libellés français servis pour `right` et `premium_side` ; jusque-là, afficher le code avec sa glose française servie, jamais le code seul. |
| `scenarios` | Loi 3 — le navigateur ne calcule jamais un score, un classement ni un verdict ; loi 4 — la couleur ne porte pas seule l'information | apps/web/src/components/widgets/CellGrid.tsx:18-30 — `GridCell.band` est « un NOM publié par le serveur (`matrix_bands`) », et `legend` est servie. Or analysis.py:1907 ne publie que `"grid": [[[_num_string(cell) …]]]` : des chaînes numériques nues, sans bande, sans légende, sans seuil. Deux issues seulement : toutes les cellules retombent sur `unknown` (la grille ne dit rien), ou le navigateur classe les valeurs en bandes — un scoring d'autorité en TypeScript, dont la teinte serait le seul vecteur. | Retirer `CellGrid` de ce module. Afficher la grille en `DataTable` (spots en lignes, horizons en colonnes, chaînes verbatim, unité et devise servies). Ouvrir une demande de contrat LOT 8 pour `scenarios.matrix_bands` + `scenarios.legend` ; n'introduire la matrice colorée qu'une fois ces deux champs servis. |
| `freshness-budget` | Loi 3 — le navigateur ne calcule jamais un ratio | apps/web/src/components/widgets/LinearGauge.tsx:6-10 et 29-32 — « Le navigateur ne calcule ni pourcentage, ni seuil, ni position du marqueur… Toutes les coordonnées arrivent SERVIES en pourcentage » ; `valuePct: string \| null` est une position SERVIE. Or apps/api/src/vertex_api/schemas.py:141-143 ne publie que `budget_seconds: PositiveInt`, `kind`, `version`, et l'analyse publie `age_seconds: int` (schemas.py:386). Aucun pourcentage n'est servi : poser « le repère à age_seconds » sur l'échelle « zéro → budget_seconds » impose age/budget en TypeScript. Sans ce calcul, la jauge rend « Valeur non calculable » en permanence (LinearGauge.tsx:56-70) et le module déclaré « servi : oui » est vide. | Soit demander au LOT 8 un `freshness_policy.age_pct` servi (position du repère), soit supprimer la jauge : rendre `age_seconds` et `budget_seconds` en deux `Metric` servis côte à côte + `FreshnessBadge`, sans échelle graphique. Ne pas déclarer « servi : oui » un module dont la primitive exige un champ que le contrat ne publie pas. |
| `rsi` | Loi 3 — le navigateur ne calcule jamais un ratio ni un classement | Même contrat de primitive (LinearGauge.tsx:6-10, 29-32) : `valuePct` doit être SERVI. Le bloc `indicators.oscillators.rsi` publie `last` et `points[].value` en unité `index_0_100` mais aucun pourcentage de position, aucun `bounds`, aucun seuil (analysis.py:2017-2019 : « aucune interpretation, aucun seuil, aucun regime »). Placer la valeur sur la jauge exige value/100 en TypeScript. La fiche reconnaît d'ailleurs abandonner `ArcGauge` « parce qu'elle imposait des seuils vides » sans voir que `LinearGauge` impose une position servie. | Supprimer la jauge de ce module. Rendre `last` en `Metric` (valeur + unité `index_0_100` servies) et la série en figure, la borne servie écrite en toutes lettres. Toute jauge d'oscillateur reste bloquée jusqu'à un contrat publiant la position du repère. |
| `freshness-budget` | Loi 7 — toute valeur critique porte sa méthode et sa version ; loi 4 — une comparaison ne doit pas suggérer un jugement que la donnée ne permet pas | apps/api/src/vertex_api/freshness.py:97 `closed_session_budget`, :115 « la MÊME valeur que `closed_session_budget` », :127 `budget_seconds=int(closed_session_budget(policy).total_seconds())`. Le budget publié est TOUJOURS le TTL de séance fermée. Le module demande pourtant « L'âge de ce dossier tient-il dans le budget de fraîcheur publié ? » et le §11 prétend qu'en état `closed` « le budget appliqué est celui de séance fermée » — comme s'il en existait un autre. En séance ouverte, la comparaison affirme un « dans le budget » que le budget servi ne soutient pas. | Renommer le module et sa question : « Âge contre budget de séance fermée », et écrire cette réserve sous la mesure. Supprimer la distinction de budget de la ligne `closed` du §11. Ne rétablir un jugement de fraîcheur intra-séance qu'après un contrat publiant un budget de séance ouverte. |
| `page — §11 états dégradés` | Loi 4 — les huit états sont distincts et chacun le DIT ; un état inatteignable rend un observé retardé indiscernable d'un observé réel | apps/worker/src/vertex_worker/analysis.py:2078-2082 — le dossier ne publie que `population = "EMPTY" \| "SYNTHETIC" \| "REAL"`. Le §11 déclare pourtant l'état `delayed` « déclencheur servi : `population === 'DELAYED'` » et le §9 fonde l'état « retardé » sur « population `DELAYED` ». Ce déclencheur n'est jamais vrai. Le code actuel porte déjà cette branche morte (apps/web/src/pages/analysis/AnalysisPage.tsx:137-138, apps/web/src/pages/analysis/analysisView.ts:450) : la conception la reconduit au lieu de la nommer. | Supprimer la ligne `delayed` du §11 tant qu'aucun champ de retard n'est servi, et déclarer explicitement au §9 que l'état « retardé » n'est PAS distinguable aujourd'hui sur cet espace — une demande de contrat, pas un état livré. Retirer la branche morte de `analysisView.ts:450`. |
| `page — §11 états dégradés` | Loi 4 — une absence, un état ou un déclencheur ne s'invente pas | apps/api/src/vertex_api/schemas.py:383-397 — `AnalysisResponse` publie `state: Literal["ok", "stale", "empty"]` et AUCUN champ de session (aucune occurrence de `session_state`, `market_open`, `session_closed` dans schemas.py ni dans analysis.py). Le §11 déclare pourtant un état `closed` « déclencheur servi : séance fermée déclarée par le serveur ». Rien ne le déclare. | Supprimer la ligne `closed` du §11, ou la déplacer en demande de contrat nommée (LOT 9). Un état dont le déclencheur n'est pas servi ne figure pas dans un tableau intitulé « déclencheur servi ». |
| `bars-integrity` | Loi 4 — absent et partiel sont deux états distincts | apps/worker/src/vertex_worker/analysis.py:1998 — `"status": "OK" if valid_bars else "ABSENT"` : le vocabulaire ne compte que deux valeurs. Le §11 déclare le déclencheur `partial` = « `bars.status !== 'OK'` », c'est-à-dire exactement `ABSENT`, c'est-à-dire le cas `empty`. Cette règle fait entrer une série vide dans l'état `partial`, où le §11 prescrit « figure tracée sur les barres admises ». | Remplacer le déclencheur : `bars.status === 'ABSENT'` ⇒ `empty` (aucune figure) ; `partial` ⇒ `bars.discarded.length > 0` OU `bars.quality !== 'VALID'` OU un bloc d'indicateur en `INSUFFICIENT_SAMPLE`/`REFUSED`, uniquement. |
| `sec-facts` | Loi 4 — une absence n'est jamais un conflit d'identité, un refus de droits ni une erreur de transport | apps/api/src/vertex_api/schemas.py:413 `state: Literal["ok", "stale", "empty"]` et :422 `identity_state: Literal["RESOLVED", "CONFLICTING_IDENTITY", "ABSENT"] \| None`, plus `rights` (:420). Le module ne déclare qu'UN texte : « Aucun dépôt officiel n'est publié pour cet instrument. » Un `CONFLICTING_IDENTITY`, un refus de droits, un `stale` ou un échec HTTP du relais SEC — endpoint DISTINCT du DTO d'analyse — se liraient tous « aucun dépôt ». | Déclarer pour ce module ses propres états dégradés (il a sa propre requête) et un texte par état servi : identité en conflit, droits refusés, instantané périmé, relais illisible. Aucun de ces quatre cas ne partage le texte d'absence. |
| `catalysts` | Loi 4 — une absence n'est jamais un refus de droits, une fenêtre vide ou un filtre local infructueux | apps/api/src/vertex_api/calendar.py:233-261 — `CalendarResponse.state` a SEPT valeurs : `ok`, `empty`, `not_entitled`, `rejected`, `stale`, `empty_window`, `degraded`. Le module ne déclare qu'un texte : « Le calendrier ne publie aucun événement rattaché à cet instrument. » De plus le rattachement au ticker est fait à l'affichage (la fiche l'admet) : « mon filtre n'a rien trouvé » serait écrit « le serveur ne publie rien ». | Déclarer un texte par état servi du calendrier, et notamment ne JAMAIS écrire une absence pour `not_entitled` ou `rejected`. Tant que le rattachement est local, écrire sous la liste que la sélection est faite à l'affichage et que l'absence ne vaut que pour cette sélection. |
| `catalysts` | Loi 3 — le navigateur n'arbitre pas l'identité canonique d'un instrument (autorité `market_data` / `data_quality`) | apps/api/src/vertex_api/routes.py:431-435 — `get_calendar` n'accepte que `from` et `to` ; aucun paramètre d'instrument. Le rapprochement `event["ticker"] === instrument` serait donc une résolution d'identité entre deux instantanés de familles différentes, décidée en TypeScript. La fiche le qualifie de « SÉLECTION, pas un calcul » — formulation ambiguë : la sélection repose sur une règle d'identité non servie. | Déclarer le module ABSENT (`SERVER_CONTRACT_MISSING`, LOT 9) jusqu'à ce que `/api/v1/calendar` accepte un paramètre `instrument` et publie lui-même le rattachement. Ne pas le compter dans les « 24 servis ». |
| `instrument-signal` | Loi 7 — toute valeur critique porte SA source, SON as_of, SA fraîcheur et SA version | La donnée du module croise deux instantanés indépendants : `analysis/{instrument}` (`bars.last_close`, `bars.currency`) et `markets/overview` (`return_1d`, `return_1d_pct`, `previous_close`, `quality`, `synthetic`). Son pied unique n'en date qu'un : « IBKR daily_bar · observé le <bars.observed_as_of> · instantané v<snapshot_version> ». Le `snapshot_version` et l'`as_of` de `markets/overview` ne sont ni les mêmes ni affichés, et le `synthetic` du ticker n'apparaît pas au pied. | Scinder : une carte « clôture publiée » (source analysis, sa provenance) et une carte « variation de séance » (source markets/overview, sa provenance, sa qualité, son `synthetic`), chacune avec son propre état dégradé. Ou fusionner seulement si le serveur publie les deux grandeurs dans un même instantané daté. |
| `page — §1 « un seul DTO chargé une fois »` | Loi 6 — une page, une question, un visuel dominant, une action principale ; règle frontend « trois à cinq modules » | La fiche annonce « un seul hook `useAnalysis`, un seul DTO `GET /api/v1/analysis/{instrument}` chargé **une** fois », mais la planche consomme CINQ sources : `analysis`, `markets/overview`, `sources/sec/{instrument}/fundamentals`, `calendar`, `ai/explain` + `ai/status`. Le tableau §11 n'est piloté que par `data.state` du DTO d'analyse : quatre sources n'ont ni `loading`, ni `refreshing`, ni `error` déclarés. Par ailleurs .claude/rules/frontend.md (« Sobriété et cohérence ») impose « trois à cinq modules » : la planche en pose 35. | Corriger la fiche : nommer les cinq sources et leur cycle de vie. Déclarer, module par module, l'état dégradé de sa PROPRE requête. Et réduire la planche : soit ramener l'espace à un nombre de modules compatible avec la règle, soit obtenir un ADR qui relève explicitement le plafond pour cet espace — la règle ne se contourne pas par la taille de la grille. |
| `peers` | Loi 6 — une page répond à UNE question | La question de la page est « Que vaut le dossier certifié de CET instrument, preuve par preuve ? ». `peers` demande « Comment les instruments du même secteur servi ont-ils clôturé, et quel poids y pèsent-ils ? » et `regime` « Dans quel régime observé cette POPULATION se tient-elle ? ». Ni l'un ni l'autre ne parle de l'instrument du dossier ; tous deux relèvent de Marchés. Le texte d'absence de `peers` (« L'instantané des marchés ne publie aucun secteur contenant cet instrument ») présente en outre le résultat d'une recherche faite dans le navigateur comme une absence serveur. | Sortir `peers` et `regime` de cette planche et les rendre à Marchés. Si un renvoi contextuel est nécessaire, poser un lien vers Marchés filtré par le secteur servi, sans recopier la table ici. |
| `price-chart` | Loi 6 / règle frontend « aucun double axe non justifié » ; aucune information portée par la seule couleur | La dominante superpose des chandeliers OHLC et un histogramme de volume — deux échelles de valeur distinctes, donc un double axe, que la fiche ne justifie nulle part — plus SMA, EMA et les trois lignes de Bollinger : sept séries sur une carte. Le motif de trait par série n'est exigé QUE pour `MultiSeriesArea` (module `rebased-comparison`) ; sur la dominante rien ne distingue SMA d'EMA hors la teinte, et la légende vit dans une AUTRE carte (`overlays-legend`, rangée 3). Le §10 dénonce pourtant comme défaut le fait de « superposer trente clôtures et quatorze volumes sur la même largeur » — puis le reproduit à l'échelle de la planche. | Soit justifier le second axe par écrit et le borner (échelle de volume nommée, unité servie), soit sortir le volume dans un module propre sous la figure, sur la même échelle de temps mais avec son axe et son pied. Exiger un motif de trait ET une étiquette de série DANS la figure pour chaque overlay, et y ramener la légende. Ajouter le fuseau servi au pied, que la fiche ne place aujourd'hui que dans l'`aria-label`. |
| `overlays-legend` | Interface intégralement en français clair ; loi 7 — la méthode est une valeur affichée, pas un identifiant technique brut | `_calculation_meta` publie bien `method` (apps/worker/src/vertex_worker/analysis.py:500-508) et toutes les chaînes servies sont anglaises : analysis.py:1153 « trailing arithmetic mean (fsum) over complete windows », :1161 « exponential smoothing alpha = 2 / (window + 1), seeded by the arithmetic mean », :1169 « SMA middle band +/- num_std population standard deviations (ddof = 0) », :1179 « Wilder smoothed average gain / (gain + loss)… », :1187 « EMA(fast) - EMA(slow); signal = EMA(signal)… ». La question du module est « sur quelle méthode ? » et les pieds de `volatility-series`, `atr-series`, `rsi`, `macd` et la table de `dossier-lineage` relaient `<calculation.method>` verbatim. | Demander au LOT 8 un `calculation.method_label_fr` servi. En attendant, n'afficher que `calculation_id`, `engine_version`, `input_hash`, `result_hash` et `status` ; reléguer la chaîne anglaise `method` dans l'inspecteur, explicitement étiquetée « identifiant technique de méthode (anglais, servi verbatim) ». |
| `bars-integrity` | Interface en français clair ; loi 4 — un motif d'absence doit être lisible | Les motifs typés que la conception impose de relayer verbatim (« Aucune valeur n'est formatée : toutes les chaînes sont relayées verbatim ») sont des codes machine anglais : apps/worker/src/vertex_worker/analysis.py:191-199 (`invalid_bar`, `invalid_payload`, `invalid_currency`, `source_not_allowed`, `rights_not_usable`, `no_healthy_option_contract`), :281-307 (`INSUFFICIENT_SAMPLE`, `BENCHMARK_ADJUSTMENT_BASIS_MISMATCH`, `INSTRUMENT_IS_BENCHMARK`), :335 (`unordered_bars`). Ils alimentent les colonnes « motif typé » de `bars-integrity`, `coverage-rejects`, `rebased-comparison` et la colonne « code de motif » de `gates-ledger`. | Ajouter à `DataTableCell` une paire obligatoire { libellé français servi, code technique } et n'afficher le code qu'en second, en `<code>`, jamais seul. Ouvrir la demande de contrat correspondante (glossaire de motifs servi) ; interdire au navigateur de traduire lui-même un code qu'il ne possède pas. |
| `verdict` | Interface en français clair ; loi 4 — la nature réelle/simulée doit être dite là où elle s'applique | apps/worker/src/vertex_worker/analysis.py:2090-2098 — `explanation_facts` est construit en anglais : « {n} {REAL\|SYNTHETIC} daily bars from … to … », « last {REAL\|SYNTHETIC} close {valeur} {devise} », « {n} evidence cluster(s) from fusion ». Le module les rend dans un `StepList`. Effet secondaire grave : c'est le SEUL endroit où la nature REAL/SYNTHETIC des barres apparaît, noyée dans une phrase anglaise du module de décision, alors que la figure dominante qui trace ces barres ne la porte pas. | Ne pas présenter `explanation_facts` comme l'explication du verdict tant qu'il est en anglais : le reléguer dans l'inspecteur comme trace technique servie. Demander au LOT 8 des faits servis en français ET un champ `bars.population` structuré, pour que la nature des barres soit portée par la figure et non par une phrase. |
| `rebased-comparison` | Loi 4 — un texte d'absence ne contient aucun chiffre | Le §9 s'intitule « Textes d'absence (exacts, sans aucun chiffre) » et le texte de ce module est : « Aucune comparaison base 100 n'est publiée : les deux séries ne partagent pas de calendrier commun servi. » Il contient le nombre 100 et le dénombrement « les deux séries » — contradiction littérale avec le titre de sa propre section. | Réécrire : « Aucune comparaison rebasée n'est publiée : les séries ne partagent aucun calendrier commun servi. » Et faire porter la règle par une porte automatique (aucun caractère numérique dans un texte d'absence), au même titre que `no-ambiguous-dash`. |
| `page — zones D et F` | Composition asymétrique exigée par le brief (bento « tetris »), grille régulière interdite | La fiche affirme : « Aucune rangée n'a la même partition que sa voisine immédiate. » C'est faux deux fois dans sa propre géométrie : zone D, R8 = `3 + 3 + 3 + 3` et R9 = `3 + 3 + 3 + 3` (rangées adjacentes, partition identique) ; zone F, R12 = `6 + 6` et R13 = `6 + 6` (adjacentes, identiques). Sur treize rangées, `6 + 6` revient quatre fois et `3 + 3 + 3 + 3` trois fois : huit modules `S` alignés en deux rangées jumelles forment une grille régulière, pas un bento. | Repartitionner D et F (par exemple R8 `6 + 3 + 3`, R9 `3 + 3 + 6` ; R12 `8 + 4`, R13 `6 + 6`) et faire vérifier l'invariant par un test de composition, puisque la fiche l'énonce comme une règle. Corriger aussi la phrase auto-corrigée laissée dans le §4 (« Quatre modules sont rank=dominant… non : un seul »), qui ne peut pas être livrée telle quelle. |
| `ai-explanation` | Loi 4 — l'absence déclarée doit correspondre à l'état servi ; loi 6 — une seule action principale | apps/api/src/vertex_api/ai_explain.py:1-9 — « NO AI provider exists in this repository — `VERTEX_AI_PROVIDER=disabled` », et le SEUL chemin d'explication est un `provider = "DETERMINISTIC_TEMPLATE"`, « never presented as a model ». Le module est titré « Explication IA », déclaré « servi : oui », et son texte d'absence dit « Aucun fournisseur d'explication n'est activé pour cette installation » — alors qu'un fournisseur déterministe répond toujours. Enfin le module déclare un `POST /api/v1/ai/explain` sans aucun déclencheur : soit il part à l'ouverture de l'inspecteur (envoi non consenti du DTO), soit il cache une seconde action principale. | Renommer le module « Explication déterministe du dossier » et afficher `status.provider` servi (`DETERMINISTIC_TEMPLATE`) sans jamais l'appeler « IA ». Remplacer le texte d'absence par l'état réellement servi. Déclarer un bouton explicite, nommé, déclenché par le lecteur, et dire dans la fiche que c'est une action SECONDAIRE de l'inspecteur — l'action principale restant « Ouvrir l'inspecteur du dossier ». |
| `model-confidence` | Loi 5 — aucune probabilité prédictive sans calibration, horizon, population et validation hors échantillon publiés | Le module inscrit en `donnee` : « le champ `advice.probability_evidence` existe au contrat et reste nul ». Or apps/web/src/design/no-uncalibrated-probability.test.ts pose la règle « Aucun module web ne LIT `probability_evidence` » et distingue à l'AST une déclaration (permise) d'un `PropertyAccessExpression` (interdit sans exemption nommée). Une implémentation qui teste la nullité du champ pour choisir entre servi et absent fait échouer la porte. | Écrire dans la fiche que l'absence de ce module est INCONDITIONNELLE et que le champ n'est jamais lu : `AbsentModule` posé en dur, motif `NO_SOURCE`, lot bloquant LOT 11. Retirer le champ de la colonne `donnee` pour ne pas induire une lecture. |
| `page — §8 corrections de primitives` | Accessibilité WCAG 2.2 AA — zéro violation critique ou sérieuse ; parcours clavier déclaré | La correction 2 du §8 ne retire `role="status"` que de `AbsentModule`. Les primitives réutilisées le portent dans leurs branches d'absence : apps/web/src/components/widgets/SparkFigure.tsx:67 et :76, LinearGauge.tsx:61, MultiSeriesArea.tsx:63/70/79/91, StepList.tsx:60, ActivityFeed.tsx:56, ArcGauge.tsx:139, ainsi que CellGrid. Avec 35 modules dont 11 absents et plusieurs figures en refus, la salve de régions live annoncée au chargement survit à la correction. | Étendre la correction à toutes les branches d'absence des primitives : contenu statique de page, pas d'événement. Ne conserver `role="status"` que là où un état CHANGE après une interaction (rafraîchissement, ouverture d'inspecteur). |
| `price-chart` | Parcours clavier — rôle interactif réel exigé | Le §12, point 6, déclare la figure dominante `tabindex="0"` avec `role="img"`, `Entrée` basculant vers la table OHLCV et `Échap` « sortant du canevas ». `role="img"` n'est pas un rôle interactif : un lecteur d'écran n'annonce ni action ni état, et un gestionnaire `Entrée` sur une image est invisible à l'API d'accessibilité. `Échap` n'a par ailleurs rien à fermer, aucun piège de focus n'étant déclaré à cet endroit. | Faire de la bascule un `<button>` réel, distinct de la figure, portant `aria-expanded` et un libellé français (« Afficher la table OHLCV équivalente »). Laisser la figure en `role="img"` non focalisable avec son `aria-label` complet. Supprimer le comportement `Échap` non fondé. |

## 5. Primitives neuves exigées — 1

- **DataTable** — LA table financière de Titan Ledger : chiffres tabulaires alignés à droite, <caption> réel dans le flux (et non un simple aria-label), en-têtes portant l'unité et la devise SERVIES, hauteur bornée avec défilement interne et en-tête collante, colonne de motif typé, cellule vide rendue par une phrase française servie et jamais par un tiret ni un zéro. Elle remplace huit tables aujourd'hui écrites à la main dans cet espace (OHLCV, portes, faits SEC, conflits SEC, pairs, refus de couverture, barres écartées, comparaison base 100) et supprime d'un coup le défaut « quatre tables sans caption ».. Donnée exigée : columns[] { key, label, unit, currency, align, numeric, absentLabel }, rows[] { id, cells{ key → { text: string | null, sign?: SignGroup, code?: string } } }, caption, ariaLabel, maxRows, moreLabel (phrase servie quand la source déclare une troncature), emptyLabel (phrase d'absence sans chiffre). Aucune valeur n'est formatée : toutes les chaînes sont relayées verbatim.. États : ready, refreshing, empty (emptyLabel), partial (bandeau « lignes tronquées par la source » alimenté par un champ servi de troncature), error. Une cellule dont la valeur n'est pas publiée porte data-absent et l'absentLabel de sa colonne ; une cellule publiée mais non scalaire porte « valeur non reconnue ».
