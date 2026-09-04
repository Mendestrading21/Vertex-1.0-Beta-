# Dossier de refonte — Marchés

> Produit par l'audit-conception du 2026-09-04 : un auditeur a lu le code et les
> contrats, un concepteur a dessiné la page cible, puis **deux lentilles
> adversariales** ont tenté de la réfuter. Les réfutations sont reportées ici
> telles quelles : **ce dossier est une conception à corriger, pas une
> spécification approuvée.** Le lot qui l'implémente applique d'abord le §4.

## 1. Ce que l'audit a mesuré

L'espace Marchés est le mieux tenu du dépôt sur la ligne « fail-closed » et le plus pauvre sur la ligne « exploiter ce qui est déjà servi ». Treize modules catalogués (marketsModules.ts), six servis, sept absents avec un motif du vocabulaire fermé — plus deux surfaces réellement rendues et NON catalogueées : le bandeau de population et l'inspecteur. Un seul endpoint propre, `GET /api/v1/markets/overview`, relayé verbatim par `build_markets_overview_response` ; deux endpoints empruntés pour la rangée « focus ».

LE POINT CENTRAL DE L'AUDIT — CE QUI EST SERVI ET JAMAIS AFFICHÉ. Quatre champs du contrat ont ZÉRO lecture dans tout `apps/web/src` : `freshness_policy` (le budget qui donne son sens à l'âge, publié dans tous les états y compris `empty`), `breadth.value` (le ratio exact), `breadth.coverage_threshold` (le seuil en ratio) et surtout `breadth.calculation` — la lignée complète du seul calcul agrégé de la page, publiée puis ignorée, pendant que le pied du cadre RÉÉCRIT à la main le nom de la méthode. Six autres champs ne survivent que dans le CSV ou dans un inspecteur exclusif qui disparaît dès qu'on sélectionne un instrument (`weight_in_sector`, `weight_global`, `ticker.sector`, `display_unit`, `observations_considered`, `lookback_seconds`).

CE QUE LE WORKER CALCULE PUIS JETTE AVANT MÊME LE CONTRAT. `_calculation_meta` (markets.py l. 353) ampute le `CalculationRecord` de dix champs, dont `source_event_ids` et `assumptions` qu'il vient de construire. Le `as_of` réel de chaque observation ne sert qu'au tri : le `as_of` publié est l'horloge du worker, donc aucune fraîcheur par instrument n'existe alors que la donnée est en base. L'`adjustment_basis`, entrée obligatoire du rendement, est haché et jeté. La liste des tickers reçus se réduit à sa longueur. Le `synthetic_count` serveur est jeté puis RECALCULÉ par le navigateur dans `censusOfNature`. Les sommes de clôtures qui servent de dénominateurs aux poids disparaissent, ce qui laisse le mot « poids » sans base au moment où il est le plus lu.

DÉFAUTS VISUELS LES PLUS COÛTEUX. Trois `'?'` substitués à des valeurs absentes (MarketsPage.tsx l. 139, dette T4-6 déjà enregistrée). Sept sites de prose française à l'intérieur d'un `<code>`. `state=\"ready\"` codé en dur sur les quatre widgets servis, donc muets sur un snapshot périmé ou partiel. Une pastille de qualité comparée à `'OK'` alors que le serveur publie `VALID` — toujours ambre, toujours à tort. Aucune `<caption>` sur la table équivalente. Une règle CSS morte (`.vx-markets-picked`). Et un système de tailles S/M/L/XL entièrement neutralisé par les aires nommées de la grille, dont les valeurs déclarées contredisent désormais la composition réelle.

Graphiques : un treemap ECharts 6 chargé paresseusement (dominante unique, 360 px, couleur à trois valeurs seulement — l'amplitude n'est encodée nulle part), quatre sparklines SVG maison, un demi-arc gradué, une jauge linéaire CSS et deux groupes de barres de dénombrement. Lightweight Charts n'est pas utilisé ici.

### 1.1 Champs servis et jamais affichés — 15 relevés

La matière gratuite : déjà calculée par Python, publiée par le contrat, et
jetée par l'interface.

- `MarketsOverviewResponse.freshness_policy` (objet FreshnessPolicyView : `budget_seconds`, `kind`, `version`) — PUBLIÉ DANS TOUS LES ÉTATS, y compris `empty` (snapshot_views.py l. 1981 et 2017, `_MARKETS_BUDGET`). ZÉRO lecture dans tout `apps/web/src` hors `api/schema.d.ts` et `test/fixtures.ts` (vérifié par grep exhaustif). Conséquence directe : MarketsPage.tsx l. 296 écrit « âge publié 604800 s » et MarketsInspector.tsx l. 122 « Âge publié … s » SANS l'échelle qui les juge. Le budget de fraîcheur de la famille `daily_bar`, sa version et son nom sont servis et jetés. Fichiers qui l'ignorent : apps/web/src/pages/markets/MarketsPage.tsx, apps/web/src/pages/markets/MarketsInspector.tsx.
- `MarketsBreadth.value` (ratio décimal borné [0,1], validé par `_bounded_ratio`, snapshot_views.py l. 1813) — ZÉRO lecture. BreadthPanel.tsx ne lit que `value_pct`. Le ratio exact, seule forme non arrondie de la breadth, n'atteint jamais l'écran ni l'inspecteur. Fichier qui l'ignore : apps/web/src/pages/markets/BreadthPanel.tsx.
- `MarketsBreadth.coverage_threshold` (le seuil en RATIO, ex. « 0.8 ») — ZÉRO lecture. BreadthPanel.tsx l. 69 et 92-99 n'utilise que `coverage_threshold_pct`. Fichier qui l'ignore : apps/web/src/pages/markets/BreadthPanel.tsx.
- `MarketsBreadth.calculation` (bloc de lignée COMPLET du calcul de breadth : `calculation_id` = « market.breadth », `engine_version`, `method` = « participation ratio above_count / covered_count », `input_hash`, `result_hash`, `status`) — ZÉRO lecture. C'est le champ le plus coûteux ignoré de la page : la breadth est la seule mesure agrégée servie, et sa preuve d'origine est publiée puis jetée. Pire, MarketsPage.tsx l. 255-259 RÉÉCRIT À LA MAIN « breadth `market.breadth` calculés par le worker » au lieu d'afficher la méthode servie. Fichiers qui l'ignorent : apps/web/src/pages/markets/BreadthPanel.tsx (aucune occurrence de `calculation`), apps/web/src/pages/markets/MarketsPage.tsx.
- `MarketsTicker.weight_in_sector` et `MarketsTicker.weight_global` (les parts en DÉCIMAL brut, six décimales) — lues UNIQUEMENT par `renderMarketsCsv` (MarketsTable.tsx l. 84-85) ; jamais affichées. L'écran ne montre que les versions `_pct` arrondies au centième. Fichier concerné : apps/web/src/pages/markets/MarketsTable.tsx.
- `MarketsTicker.sector` (le CODE de secteur canonique, distinct du libellé) — lu UNIQUEMENT par `renderMarketsCsv` (MarketsTable.tsx l. 78). À l'écran, MarketsTable.tsx l. 227 affiche `entry.sectorLabel` et SectorGrid.tsx l. 39 n'utilise `sector.sector` que comme clé React. Le code d'identité canonique n'est jamais lisible.
- `MarketsTicker.return_1d` (le ratio brut, ex. « 0.0123 ») — une seule lecture, dans l'inspecteur (MarketsInspector.tsx l. 72), plus le CSV. Il disparaît dès qu'aucun instrument n'est sélectionné : la table, la carte et les puces sectorielles ne montrent que `return_1d_pct`.
- `MarketsOverviewResponse.display_unit` — une seule lecture, MarketsInspector.tsx l. 143, dans le SnapshotInspector QUI DISPARAÎT dès qu'un instrument est sélectionné (MarketsPage.tsx l. 449-461, les deux inspecteurs sont exclusifs). Le méta du cadre dominant (MarketsPage.tsx l. 175) écrit l'unité en prose à la main au lieu de la lire.
- `MarketsCoverage.observations_considered` et `MarketsCoverage.lookback_seconds` — une seule lecture chacune, MarketsInspector.tsx l. 155 et 160, dans le SnapshotInspector exclusif. Dès qu'un ticker est sélectionné, la fenêtre de recul et le nombre d'observations examinées ne sont plus lisibles nulle part.
- LIGNÉE AMPUTÉE AVANT LE CONTRAT — `apps/worker/src/vertex_worker/markets.py` l. 353-363, `_calculation_meta` ne conserve QUE 6 clés du `CalculationRecord`. Le worker construit (l. 453-473) un enregistrement complet puis JETTE : `source_event_ids` (les deux `event_id` des observations retenues), `assumptions` (« consecutive trading days from admitted daily-quote observations »), `code_sha`, `calculation_type`, `parameters`, `random_seed`, `warnings`, `started_at`, `completed_at` et `result`. Aucun de ces champs n'atteint jamais l'API ni l'écran.
- CALCULÉ PUIS JETÉ PAR LE WORKER — `_ParsedQuote.as_of` (markets.py l. 286, l'instant RÉEL de l'observation) : il ne sert qu'au tri et à la déduplication (l. 419). Le `as_of` publié est `now.isoformat()` (l. 664), l'horloge du worker. Aucune fraîcheur PAR INSTRUMENT n'existe donc, alors que la donnée est en base.
- CALCULÉ PUIS JETÉ PAR LE WORKER — `_ParsedQuote.adjustment_basis` (markets.py l. 283) : entrée obligatoire de `simple_return` (l. 442-447), hachée dans `input_hash`, jamais publiée. L'écran ne peut pas dire si les deux clôtures partagent la même base d'ajustement.
- CALCULÉ PUIS JETÉ PAR LE WORKER — `received` (markets.py l. 431, la LISTE triée des tickers réellement reçus) : seule sa LONGUEUR est publiée (l. 671). Un ticker reçu mais non couvert n'est donc distinguable d'un ticker jamais reçu que par recoupement.
- CALCULÉ PUIS JETÉ PAR LE WORKER — `synthetic_count` (markets.py l. 421-426) : ne sert qu'à choisir l'étiquette `population`. L'interface REFAIT ce comptage elle-même dans `censusOfNature` (components/markets/marketsView.ts l. 108-122), sur les drapeaux par instrument. Un compte serveur existe et le navigateur le recalcule.
- CALCULÉ PUIS JETÉ PAR LE WORKER — `sector_totals` et `universe_total` (markets.py l. 495-502, les SOMMES DE CLÔTURES qui servent de dénominateurs aux poids) : les poids sont publiés sans leur base. L'écran affiche « poids global » sans jamais pouvoir dire de quelle somme il est la part.

### 1.2 Défauts visibles dans le code — 17

- GLYPHE AMBIGU CONFIRMÉ — MarketsPage.tsx l. 139 : `${coverage?.covered ?? '?'} instruments couverts sur ${coverage?.expected ?? '?'} attendus, ${coverage?.discarded ?? '?'} écartés`. Trois `'?'` substitués à des valeurs absentes, dans le bandeau d'état PARTIEL. Ce défaut est officiellement enregistré : `apps/web/src/design/no-ambiguous-dash.test.ts` l. 147 inscrit `src/pages/markets/MarketsPage.tsx` dans `DETTE_T4`, lot T4-6, plafond `DETTE_MAX = 17`.
- PROSE FRANÇAISE DANS UN CANAL DE CODE SERVEUR — 7 sites. MarketsPage.tsx l. 258 `<code>{data.engine_version ?? 'version inconnue'}</code>` ; l. 296 `<code>{data.data_state ?? 'non publié'}</code>` ; MarketsInspector.tsx l. 117, 131, 137, 143 rendent `publie(...)` (qui retourne « non publié ») à l'intérieur de `<code>` ; l. 95-102 rendent `lineageString(...)` (« non publié ») dans quatre `<code>`. Un `<code>` en Geist Mono qui contient une phrase française se lit comme une valeur servie : l'absence prend l'apparence de la donnée.
- ÉTAT « ready » CODÉ EN DUR SUR LES QUATRE WIDGETS SERVIS — MarketsPage.tsx l. 293, 345, 407, 433 : `state="ready"` littéral sur `market-health`, `discards`, `breadth` et `sectors`. Quand `frameStateOf` conclut `stale`, `partial` ou `delayed`, seul le cadre dominant l'annonce ; les quatre autres cartes servies continuent d'afficher leurs chiffres comme s'ils étaient frais. Les huit états distincts ne sont donc pas tenus module par module.
- TON D'ALERTE PERMANENT SUR LA QUALITÉ — components/widgets/InstrumentTile.tsx l. 102 : `tone={quality === 'OK' ? 'neutral' : 'warning'}`. Le vocabulaire serveur est `VALID` / `PARTIAL` / `STALE` (`_QUALITY_ORDER`, markets.py l. 113 ; `CalculationStatus.VALID` dans contracts/enums.py l. 111). `'OK'` n'existe pas : la pastille est donc TOUJOURS ambre, y compris pour un instrument parfaitement `VALID`. Quatre tuiles ambre permanentes sur la rangée « focus » de Marchés.
- PASTILLE VIDE POSSIBLE — même fichier l. 101 : `label={quality === '' ? '' : quality}` rend un StatusChip sans texte lorsque la chaîne est vide ; une pastille colorée sans libellé est de la couleur seule.
- AUCUN `<caption>` SUR LA TABLE ÉQUIVALENTE — MarketsTable.tsx l. 200 : `<table className="vx-markets-table" aria-label="…">`. La seule légende de la page est le `<figcaption>` du treemap (MarketMap.tsx l. 227). La table qui porte l'équivalence complète de la dominante n'a ni caption ni résumé de colonnes.
- RÈGLE CSS MORTE — `.vx-markets-picked { color: var(--vx-signal); }` (global.css l. 5860) : ZÉRO consommateur dans tout `apps/web/src`. Le composant utilise `vx-markets-pick` (sans « ed »).
- TAILLES DE MODULE MORTES — `MARKETS_MODULES` déclare S/M/L/XL (marketsModules.ts) et `Widget` les pose en `data-size` (Widget.tsx l. 205), mais `.vx-markets-grid` place chaque module par `grid-area` nommée (widgets.css l. 1202-1229) : `grid-area` écrase `grid-column: span N` (widgets.css l. 44-57). Résultat, les tailles déclarées CONTREDISENT la composition réelle — `breadth` est S mais occupe 2 colonnes, `sectors` est L mais occupe 3 colonnes sur 1 rangée, `discards` est M mais occupe 1 colonne à 1280/1440. Pour les modules absents c'est pire : `AbsentMarketsModule` (MarketsPage.tsx l. 86) pose `data-size` sur un `<div>` nu qui n'est même pas `.vx-w2`, donc aucun sélecteur ne le lit.
- POIDS NON QUALIFIÉ SOUS LA DOMINANTE — la légende du treemap (MarketMap.tsx l. 228-231) dit « Taille de tuile = poids global (%) » sans dire de quoi. La nature réelle (part de la SOMME DES CLÔTURES, markets.py l. 495-512) n'est écrite qu'au pied du cadre, l. 268 : « Poids = parts descriptives des clôtures servies ». Un lecteur pressé lira une pondération de capitalisation. Le mot « poids » porte à lui seul une hypothèse financière que la carte ne défend pas à côté d'elle.
- MAGNITUDE ABSENTE DE LA DOMINANTE — la couleur du treemap n'a que 3 valeurs (positif / négatif / stable, MarketMap.tsx l. 44-63). L'amplitude du rendement, servie au centième pour chaque tuile, n'est encodée par AUCUN canal visuel : la carte distingue un +0,05 % d'un +9 % uniquement par le texte de la tuile.
- BRANCHE D'ÉTAT INATTEIGNABLE — MarketsPage.tsx l. 70-72 : `if (data.population === 'DELAYED') return 'delayed'`. Le worker Marchés ne publie que `EMPTY`, `SYNTHETIC` ou `REAL` (markets.py l. 604-609). L'état « Données différées » de cette page ne peut donc jamais s'afficher aujourd'hui.
- MÉTA DE MODULE JAMAIS RENDUE — aucun des quatre `Widget` servis ne passe la prop `served` (MarketsPage.tsx l. 288-292, 341-344, 402-409, 428-436). `WidgetMeta` (Widget.tsx l. 146-178), qui porte âge, `as_of`, version de snapshot et nature de population par carte, n'est donc JAMAIS monté sur Marchés. La date et la nature n'existent qu'en deux points de la page.
- DOCSTRING FAUSSE — MarketsPage.tsx l. 33-38 annonce « douze modules … Cinq sont SERVIS ». Le catalogue en compte TREIZE, dont SIX servis (`marketsModules.test.ts` l. 8-27 l'assert correctement). Le module `focus` a été ajouté sans mettre à jour l'en-tête de la page.
- CONTRADICTION DE DOCTRINE GRAPHIQUE — components/CensusBars.tsx l. 6-8 cite « `references/charts.md` : pas de jauge circulaire, pas d'anneau », alors que ce fichier (`.claude/skills/vertex-titanium-ledger/references/charts.md` l. 45-46) ADMET explicitement l'anneau à chiffre central et l'arc gradué (ADR-017), tout comme `docs/05-design/CHART_STANDARD.md` l. 7 et 63-70. Sur le fond, Marchés ne porte AUCUNE jauge circulaire ni anneau : seul un demi-arc gradué, à position servie et sans aiguille — forme admise. Le défaut est la citation périmée qui condamne la forme employée juste à côté.
- UNE SEULE DOMINANTE DÉCLARÉE, MAIS NEUF FORMES VISUELLES — `data-rank="dominant"` n'est posé qu'une fois (MarketsPage.tsx l. 154). La planche empile pourtant, sous cette dominante : 1 demi-arc, 1 jauge linéaire, 2 groupes de barres de dénombrement, 4 sparklines, 1 grille de puces sectorielles colorées, 2 listes de pastilles ambre et 1 table de 7 colonnes. La règle « un visuel dominant au maximum » est tenue par déclaration, pas par la densité réelle.
- AUCUNE COULEUR SEULE PORTEUSE — vérifié et CONFORME : treemap (ticker + rendement signé écrits dans la tuile), table (glyphe `▲ ▼ =` + texte masqué du groupe, MarketsTable.tsx l. 231-236), puces sectorielles (SectorGrid.tsx l. 58-66), légende (libellés + `aria-pressed` + barré en CSS quand désactivé). Contrastes du treemap : `--vx-black` #030302 sur #50c992, #ef6f6c et #948c7d — tous largement au-dessus du seuil.
- AUCUN DÉBORDEMENT MESURABLE DANS LE CODE — `.vx-chartframe` est `overflow: hidden` mais le treemap est ancré aux quatre bords et re-résolu par `ResizeObserver` (MarketMap.tsx l. 148-155, 198-201) ; la table est bornée à `max-height: 420px` avec `overflow-y: auto`, `tabIndex={0}`, `role="region"` et en-tête collant (global.css l. 5409-5429) ; `.vx-markets-grid > [data-module] { min-width: 0 }` (global.css l. 5842) ferme le débordement de grille.

### 1.3 Graphiques actuels

- Treemap ECharts — MarketMap.tsx. Moteur : `echarts/core` + `TreemapChart` + `TooltipComponent` + `AriaComponent` + `CanvasRenderer`, importé DYNAMIQUEMENT via `import('../../charts/echartsLoader.ts')` (chunk hors bundle initial). Taille de tuile = `weight_global_pct` parsé pour la géométrie ; couleur = 3 seuls jetons (`--vx-positive`, `--vx-negative`, `--vx-text-muted`) selon le SIGNE de la chaîne servie ; libellé de tuile = ticker + rendement signé. Ancrée aux quatre bords, hauteur forcée à 360 px par `.vx-markets-grid .vx-marketmap-canvas` (global.css l. 5854). `nodeClick: false`, `roam: false`, clic sur feuille = sélection d'instrument.
- Sparkline SVG artisanale — components/markets/Sparkline.tsx, 4 exemplaires (un par tuile de la rangée « focus », borne `FOCUS_LIMIT = 4`). AUCUN moteur : polyline + path d'aire + ligne pointillée sur la PREMIÈRE clôture de la fenêtre + barres de volume, viewBox 120×40 et 120×18, `preserveAspectRatio="none"`. Fenêtres : 30 clôtures pour la ligne, 14 pour les volumes.
- ArcGauge — demi-cercle SVG gradué (rayon 70, viewBox 160×96), un exemplaire : la breadth (BreadthPanel.tsx l. 75-84). Position servie (`value_pct`), aucun seuil passé (`thresholds={[]}`), ton `macro`, refus total de la forme si `status === 'INVALID'`.
- LinearGauge — jauge à rail en CSS pur (aucun SVG), un exemplaire : la couverture, avec le marqueur du seuil exigé (BreadthPanel.tsx l. 85-103).
- CensusBars — barres de dénombrement en CSS (`width` en pourcentage du plus grand compte), DEUX exemplaires : les 3 comptes de breadth (hausses/baisses/inchangés) et les 4 comptes de couverture (reçus/couverts/écartés/rejetés). Les barres sont `aria-hidden`, le compte entier est écrit à côté.
- Lightweight Charts 5.2.1 N'EST PAS utilisé sur Marchés : `charts/lightweightChartsLoader.ts` n'est importé par aucun fichier de cet espace.

### 1.4 Fichiers lus

- `/home/user/vertex-merge/apps/web/src/pages/markets/MarketsPage.tsx (504 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/marketsModules.ts (173 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/MarketMap.tsx (234 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/MarketsTable.tsx (252 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/BreadthPanel.tsx (110 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/MarketsInspector.tsx (165 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/MarketsPage.test.tsx (593 l.)`
- `/home/user/vertex-merge/apps/web/src/pages/markets/marketsModules.test.ts (45 l.)`
- `/home/user/vertex-merge/apps/web/src/components/markets/marketsView.ts (124 l.)`
- `/home/user/vertex-merge/apps/web/src/components/markets/SectorGrid.tsx (87 l.)`
- `/home/user/vertex-merge/apps/web/src/components/markets/Sparkline.tsx (119 l.)`
- `/home/user/vertex-merge/apps/web/src/components/widgets/InstrumentTile.tsx (FocusRowModule, module « focus »)`
- `/home/user/vertex-merge/apps/web/src/components/widgets/Widget.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/ArcGauge.tsx`
- `/home/user/vertex-merge/apps/web/src/components/widgets/LinearGauge.tsx`
- `/home/user/vertex-merge/apps/web/src/components/CensusBars.tsx`
- `/home/user/vertex-merge/apps/web/src/components/Metric.tsx`
- `/home/user/vertex-merge/apps/web/src/components/AbsentModule.tsx`
- `/home/user/vertex-merge/apps/web/src/components/SyntheticBanner.tsx`
- `/home/user/vertex-merge/apps/web/src/components/DataStateBoundary.tsx`
- `/home/user/vertex-merge/apps/web/src/components/FreshnessBadge.tsx`
- `/home/user/vertex-merge/apps/web/src/pages/focusView.ts`
- `/home/user/vertex-merge/apps/web/src/charts/echartsLoader.ts`
- `/home/user/vertex-merge/apps/web/src/api/client.ts`
- `/home/user/vertex-merge/apps/web/src/styles/global.css (blocs 1694-2018, 4515-4710, 5400-5435, 5820-5912)`
- `/home/user/vertex-merge/apps/web/src/styles/widgets.css (blocs 44-57, 1190-1242, 1479-1485)`
- `/home/user/vertex-merge/apps/web/src/design/tokens.css`
- `/home/user/vertex-merge/apps/web/src/design/no-ambiguous-dash.test.ts`
- `/home/user/vertex-merge/apps/api/src/vertex_api/routes.py (l. 329-347)`
- `/home/user/vertex-merge/apps/api/src/vertex_api/schemas.py (l. 118-143, 204-337)`
- `/home/user/vertex-merge/apps/api/src/vertex_api/snapshot_views.py (l. 1756-2035)`
- `/home/user/vertex-merge/apps/worker/src/vertex_worker/markets.py (846 l.)`
- `/home/user/vertex-merge/packages/python/vertex_core/src/vertex_core/contracts/calculation.py`
- `/home/user/vertex-merge/docs/01-product/pages/03-markets.md`
- `/home/user/vertex-merge/docs/05-design/CHART_STANDARD.md`
- `/home/user/vertex-merge/apps/web/e2e/markets.spec.ts`

## 2. Question, point focal, accent

- **Question** : Dans quel contexte de marché vais-je analyser les instruments ?
- **Visuel dominant** : Carte des marchés — treemap ECharts 6.1.0 chargé paresseusement, unique porteur de `data-rank="dominant"` de la page. Taille de tuile = `weight_global_pct` servi ; couleur = signe servi à trois valeurs (`--vx-positive`, `--vx-negative`, `--vx-text-muted`) ; libellé de tuile = ticker + rendement signé servi. Canevas ancré aux quatre bords, hauteur fixe 360 px à 1280/1440 et 420 px à 1600, re-résolu par `ResizeObserver`. Légende-filtre local (aucune valeur modifiée), conclusion serveur verbatim, et table équivalente triable avec `<caption>` et export CSV. Aucune autre forme de la page ne porte de rang dominant, et aucun autre moteur graphique n'est chargé sur cette route.
- **Accent** : cyan — jeton `macro` (#6bc5bc), déjà déclaré pour `markets` dans `PAGE_ACCENTS` (`components/widgets/pageAccent.ts`). Le cyan porte le CONTEXTE : filets de zone, rail des jauges, marqueur de budget de fraîcheur, soulignement de l'en-tête collant de la table équivalente, anneau de focus des puces sectorielles. L'ambre (`signal`) reste la seule lumière de la dominante et le marqueur de l'instrument actif (`.vx-markets-pick[aria-pressed='true']`). Vert et rouge restent strictement réservés au signe financier servi. Le violet (`option`) est interdit sur cette page : aucun module d'options n'y est servi.

## 3. Conception proposée

# Fiche de page — Marchés (`/markets`)

Identité **Titan Ledger / Institutional Signal**. Desktop only : `1280×800`, `1440×900`, `1600×1000`.
Code réel : `apps/web/src/pages/markets/` et `apps/web/src/components/markets/`.

---

## 1. Question de la page

> **Dans quel contexte de marché vais-je analyser les instruments ?**

Une seule question, un seul visuel dominant, une seule action principale :
**ouvrir le dossier d'analyse d'un instrument**. Le filtre de légende, le tri de
la table et la sélection d'un instrument sont des commandes de VUE, pas des
actions : elles ne modifient aucune valeur servie et le disent à l'écran.

## 2. Visuel dominant

**Carte des marchés** — treemap **Apache ECharts 6.1.0**, importé dynamiquement
par `charts/echartsLoader.ts`, hors bundle initial. Unique porteur de
`data-rank="dominant"` de la page (porte `one-dominant-per-page.test.ts`).

| Canal | Encodage | Origine |
|---|---|---|
| Aire de tuile | `weight_global_pct` servi | serveur |
| Couleur | signe servi à trois valeurs : `--vx-positive`, `--vx-negative`, `--vx-text-muted` | serveur |
| Libellé de tuile | ticker + rendement signé servi | serveur |
| Amplitude | **non encodée** — aucune bande servie (module `map-amplitude`, LOT 9) | — |

Canevas ancré aux quatre bords, re-résolu par `ResizeObserver`.
Hauteur : **360 px** à 1280 et 1440, **420 px** à 1600. `roam: false`,
`nodeClick: false` ; le clic sur une feuille sélectionne un instrument.

**Lightweight Charts n'est pas chargé sur cette route** et ne doit pas l'être :
aucune série temporelle de prix n'y est servie.

### Budget de formes

Une dominante, **quatre familles secondaires au maximum**, jamais davantage :

1. arc gradué (largeur de marché) ;
2. rail gradué (couverture, fraîcheur — `LinearGauge` et `BudgetBar` partagent le rail) ;
3. barres de dénombrement (`CensusBars`) ;
4. sparkline servie (`SparkFigure`, rangée de suivi).

Sont **retirées** par rapport à l'état mesuré : les barres de volume des tuiles
de suivi (la microstructure appartient à Analyse) et la `Sparkline` SVG
artisanale de `components/markets/Sparkline.tsx`, remplacée par la primitive
`SparkFigure` portée par `KpiTile`.

## 3. Accent

**Cyan** — jeton `macro` (`#6bc5bc`), déjà déclaré pour `markets` dans
`PAGE_ACCENTS`. Le cyan porte le **contexte** : filets de zone, rail des jauges,
marqueur du budget de fraîcheur, soulignement de l'en-tête collant de la table
équivalente, anneau de focus des puces sectorielles.

- **Ambre** (`signal`) : seule lumière de la dominante et marqueur de
  l'instrument actif (`.vx-markets-pick[aria-pressed='true']`).
- **Vert / rouge** : strictement réservés au signe financier servi.
- **Violet** (`option`) : interdit ici, aucun module d'options n'est servi.
- Aucune couleur n'est jamais seule porteuse de sens : chaque signe est doublé
  d'un glyphe (`▲ ▼ =`) et du texte signé servi.

## 4. Zones

| # | Zone | Rôle | Colonnes | Modules |
|---|---|---|---|---|
| 1 | Contexte publié et carte dominante | **SIGNAL** | 12 | `population`, `market-map`, `breadth`, `freshness`, `served-state` |
| 2 | De quoi la carte est faite | **PREUVE** | 12 | `sectors`, `coverage`, `window`, `breadth-lineage`, `unit-convention` |
| 3 | Ce que la carte ne montre pas | **RISQUE** | 12 | `discards`, `received-uncovered`, `weights-basis`, `map-amplitude`, `instrument-freshness`, `adjustment-basis`, `calculation-events` |
| 4 | Contexte non collecté | **RISQUE** | 12 | `sessions`, `indices`, `volatility`, `rates-curve`, `fx`, `correlation`, `vol-structure`, `sector-return` |
| 5 | Vers l'analyse | **DÉCISION** | 12 | `focus`, `inspector` (panneau du shell, hors grille) |

Chaque zone est un `<section>` avec son `<h2>` (`vx-zone-title`) et un filet
cyan de 1 px en tête. Les titres de zone sont dans le flux du document : ils
donnent au lecteur d'écran la hiérarchie SIGNAL → PREUVE → RISQUE → DÉCISION.

## 5. Grille — bento asymétrique sur 12 colonnes

```css
.vx-mk-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--vx-space-16);
  grid-auto-rows: minmax(var(--vx-w2-row), auto); /* 152px, jeton existant */
  grid-template-areas:
    'pop  pop  pop  pop  pop  pop  pop  pop  pop  pop  pop  pop '
    'map  map  map  map  map  map  map  map  map  map  map  map '
    'brd  brd  brd  brd  brd  brd  fres fres fres stat stat stat'
    'sect sect sect sect sect sect cov  cov  cov  win  win  win '
    'sect sect sect sect sect sect lin  lin  lin  unit unit unit'
    'disc disc disc disc disc disc recu recu recu wbas wbas wbas'
    'disc disc disc disc disc disc ampl ampl ampl ifre ifre ifre'
    'disc disc disc disc disc disc adjb adjb adjb cevt cevt cevt'
    'sess sess sess indx indx indx vola vola vola rate rate rate'
    'fx   fx   fx   corr corr corr vols vols vols sret sret sret'
    'focu focu focu focu focu focu focu focu focu focu focu focu';
}
```

**Le relief « tetris » vient des spans verticaux**, pas d'une alternance de
largeurs : `sectors` tient **deux** rangées à mi-largeur, `discards` en tient
**trois**, la dominante et la rangée de suivi prennent la largeur entière, et la
bande d'instruments encadre trois cartes étroites. Les surfaces sont donc
franchement différentes — 12, 6×2, 6×3, 3 — et aucune rangée n'est régulière.

**La taille `L` (8 colonnes) n'est pas utilisée sur cette page**, et c'est une
décision, pas un oubli : sur 12 colonnes, `L` exige un module de 4 colonnes qui
n'existe pas dans le vocabulaire fermé `S | M | L | XL`. Une rangée `8 + 3`
laisserait une colonne vide ragée. Si un jour une taille de 4 colonnes est
ajoutée au vocabulaire, `sectors` prend `L` et `coverage` la complète.

**Les tailles déclarées et les aires nommées doivent coïncider.** Le défaut
mesuré aujourd'hui (`breadth` déclaré `S` mais posé sur 2 colonnes, `sectors`
déclaré `L` mais posé sur 3, `discards` déclaré `M` mais posé sur 1) est fermé
par une porte : `design/markets-grid-size.test.ts` compare, pour chaque
`data-module`, le span de son `grid-area` au `data-size` du catalogue et échoue
sur toute divergence. Les modules absents portent désormais `data-size` sur une
`section.vx-absent` réellement ciblée par la grille, plus sur un `<div>` nu.

Aux trois viewports de release, **les aires ne changent pas** : seule la hauteur
du canevas de la dominante passe de 360 à 420 px à 1600 px. Aucun breakpoint
mobile, aucune barre d'action basse, aucun geste tactile.

## 6. Modules

| id | titre | question | taille | widget | graphique | donnée | servi | lot bloquant |
|---|---|---|---|---|---|---|---|---|
| `population` | Nature des données affichées | Ce que je regarde est-il réel, synthétique ou non déclaré ? | XL (12) | SyntheticBanner + StatusChip | — | `population` + recensement des drapeaux `tickers[].synthetic` | oui | — |
| `market-map` | Carte des marchés | Comment les secteurs et les instruments suivis ont-ils clôturé sur la dernière séance servie ? | XL (12) | MarketsFrame `data-rank="dominant"` + MarketMap + MarketsTable + DataStateBoundary | **Treemap ECharts 6.1.0** (chargé paresseusement) | `sectors[].tickers[].weight_global_pct`, `return_1d_pct`, `conclusion`, `unit`, `display_unit` | oui | — |
| `breadth` | Largeur de marché | Quelle part des instruments couverts progresse sur la séance servie ? | M (6) | Widget + ArcGauge + Metric + CensusBars | demi-arc gradué SVG + barres de dénombrement | `breadth.value_pct`, **`breadth.value`**, `above_count`, `down_count`, `flat_count`, `covered_count`, `universe_size` | oui | — |
| `freshness` | Fraîcheur de l'instantané | L'instantané affiché tient-il encore dans le budget de fraîcheur publié ? | S (3) | Widget + **BudgetBar** + FreshnessBadge + StatusChip | rail gradué à bornes servies | `age_seconds`, **`freshness_policy.budget_seconds` / `.kind` / `.version`**, `as_of` | oui | — |
| `served-state` | État publié | Quel état le serveur déclare-t-il pour cet instantané ? | S (3) | Widget + StatusChip ×3 + ProvenanceLine | — | `state`, `data_state`, `population`, `reason`, `engine_version`, `snapshot_version` | oui | — |
| `sectors` | Carte sectorielle | Quels secteurs portent la séance, instrument par instrument ? | M (6, span 2) | Widget + SectorGrid + StatusChip | grille de puces signées | `sectors[].sector` (**code canonique**), `.label`, `declared_count`, `covered_count`, `tickers[].return_1d_pct` | oui | — |
| `coverage` | Couverture de l'univers | Quelle part de l'univers déclaré a été effectivement couverte ? | S (3) | Widget + LinearGauge + Metric | rail gradué CSS + marqueur de seuil servi | `coverage_pct`, `coverage_threshold_pct`, **`coverage_threshold`**, `coverage.*` | oui | — |
| `window` | Fenêtre d'observation | Sur quel recul et sur combien d'observations cet instantané a-t-il été construit ? | S (3) | Widget + Metric ×2 | — | **`coverage.observations_considered`**, **`coverage.lookback_seconds`** | oui | — |
| `breadth-lineage` | Lignée du calcul de largeur | D'où vient la largeur de marché affichée, et par quelle méthode servie ? | S (3) | Widget + **LineageBlock** | — | **`breadth.calculation`** complet | oui | — |
| `unit-convention` | Unité et convention | Dans quelle unité les valeurs de cette page sont-elles calculées et affichées ? | S (3) | Widget + Metric ×2 + StatusChip | — | `unit`, **`display_unit`**, `engine_version` | oui | — |
| `discards` | Écarts et rejets nommés | Qu'a-t-on refusé d'afficher, et pour quel motif servi ? | M (6, span 3) | Widget + StatusChip + deux listes | — | `coverage.discarded_tickers[]`, `coverage.rejected_records[]` | oui | — |
| `received-uncovered` | Reçus sans couverture | Quels instruments ont été reçus sans finir sur la carte ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`received` réduit à sa longueur) | **non** | **LOT 9** |
| `weights-basis` | Base des poids | De quelle somme servie le poids affiché est-il la part ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`sector_totals`, `universe_total` jetés) | **non** | **LOT 9** |
| `map-amplitude` | Amplitude des variations | Quelle intensité servie sépare une variation faible d'une variation forte sur la carte ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`return_band` non publié) | **non** | **LOT 9** |
| `instrument-freshness` | Fraîcheur par instrument | De quand date l'observation servie de chaque instrument affiché ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`_ParsedQuote.as_of` jeté) | **non** | **LOT 9** |
| `adjustment-basis` | Base d'ajustement des clôtures | Les deux clôtures comparées partagent-elles la même base d'ajustement servie ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`adjustment_basis` haché puis jeté) | **non** | **LOT 9** |
| `calculation-events` | Observations sources du calcul | Quelles observations exactes alimentent le rendement de l'instrument sélectionné ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | inexistant (`_calculation_meta` ampute dix champs) | **non** | **LOT 13** |
| `sessions` | Sessions mondiales | Quelles places de marché sont ouvertes à cet instant ? | S (3) | AbsentModule `NO_SOURCE` | — | aucun calendrier de séance | **non** | **LOT 7** |
| `indices` | Indices | Comment les grands indices ont-ils clôturé ? | S (3) | AbsentModule `NO_SOURCE` | — | aucun indice dans l'univers | **non** | **LOT 7** |
| `volatility` | Volatilité de marché | La volatilité implicite du marché est-elle élevée ? | S (3) | AbsentModule `NO_SOURCE` | — | aucun indice de volatilité | **non** | **LOT 7** |
| `rates-curve` | Courbe des taux | Comment la courbe des taux s'est-elle déformée ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | aucune route ni instantané de courbe | **non** | **LOT 7** |
| `fx` | Devises | Comment les devises ont-elles bougé face à la devise de référence ? | S (3) | AbsentModule `NO_SOURCE` | — | aucune cotation de change | **non** | **LOT 7** |
| `correlation` | Corrélation entre classes d'actifs | Les grandes classes d'actifs évoluent-elles ensemble ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | aucune corrélation inter-classes publiée | **non** | **LOT 9** |
| `vol-structure` | Structure de volatilité | La volatilité implicite est-elle plus chère à court ou à long terme ? | S (3) | AbsentModule `NO_SOURCE` | — | aucune structure par échéance publiée | **non** | **LOT 8** |
| `sector-return` | Rendement de secteur | Quel rendement le secteur affiche-t-il, au-delà de ses instruments ? | S (3) | AbsentModule `SERVER_CONTRACT_MISSING` | — | aucun rendement agrégé de secteur | **non** | **LOT 9** |
| `focus` | Instruments suivis | Que font les instruments dont un dossier d'analyse est publié ? | XL (12) | Widget + KpiTile ×4 (Glyph, KpiDelta, SparkFigure) + StatusChip | sparkline servie `SparkFigure` (SVG interne) | `GET /api/v1/opportunities` + `GET /api/v1/analysis/{instrument}`, borne `FOCUS_LIMIT = 4` | oui | — |
| `inspector` | Inspecteur | Quelles chaînes serveur et quelle lignée portent l'élément que je regarde ? | XL — **panneau du shell, hors grille** | InspectorPanel + Metric + StatusChip + **LineageBlock** | — | section « Instantané » toujours présente + section « Instrument » quand une sélection existe | oui | — |

**27 modules catalogués, 13 servis.** L'état mesuré comptait 13 modules
catalogués dont 6 servis, plus deux surfaces rendues et non inventoriées
(bandeau de population, inspecteur) : elles entrent au catalogue.

### Ce que cette page cesse de jeter

Priorité absolue de la refonte : **tout champ servi et jamais affiché devient un
module réel**. Cette intelligence est déjà calculée par Python ; l'écran la
jetait.

| Champ servi | Lectures aujourd'hui | Module cible |
|---|---|---|
| `freshness_policy.{budget_seconds,kind,version}` | **zéro** (publié dans tous les états, `empty` compris) | `freshness` |
| `breadth.value` (ratio exact) | **zéro** | `breadth` |
| `breadth.coverage_threshold` (seuil en ratio) | **zéro** | `coverage` |
| `breadth.calculation` (lignée complète) | **zéro** | `breadth-lineage` |
| `weight_in_sector`, `weight_global` (décimaux) | CSV seulement | `inspector` |
| `tickers[].sector` (code canonique) | CSV seulement | `sectors`, `inspector`, colonne de la table |
| `return_1d` (ratio brut) | inspecteur exclusif | `inspector` (les deux formes côte à côte) |
| `display_unit` | inspecteur exclusif | `unit-convention` + méta de la dominante |
| `observations_considered`, `lookback_seconds` | inspecteur exclusif | `window` |

L'inspecteur cesse d'être **exclusif** : ses deux sections coexistent, la vérité
de l'instantané ne disparaît plus quand un instrument est sélectionné.

## 7. Nouvelles primitives exigées

Deux, et deux seulement. Les vingt et une primitives existantes couvrent tout le
reste ; aucune famille visuelle nouvelle n'est introduite.

### `BudgetBar`

**Rôle.** Poser une valeur servie sur une échelle servie exprimée dans la **même
unité** — l'âge d'un instantané sur son budget de fraîcheur. Elle partage le
rail, les jetons et les graduations de `LinearGauge` : la famille visuelle reste
« rail gradué ».

**Pourquoi `LinearGauge` ne suffit pas.** `LinearGauge` exige `valuePct`, une
position servie en pourcentage. Le contrat Marchés ne publie ni pourcentage ni
ratio de fraîcheur : il publie deux durées en secondes. La position est un
rapport de **géométrie** entre deux chaînes servies — du même ordre que la
hauteur d'une barre de `DayBars` ou l'aire d'une tuile de treemap — jamais un
ratio financier et jamais un statut reconstruit : le verdict de fraîcheur reste
`state` servi par le serveur. Le contrat de `FreshnessPolicyView` prescrit
lui-même cet usage : « le client pose `age_seconds` sur cette échelle et
n'invente ni TTL ni ratio ».

**Donnée exigée.** `age_seconds` et `freshness_policy.budget_seconds` dans la
même unité, plus `freshness_policy.kind` et `freshness_policy.version` écrits en
toutes lettres à côté du rail. La borne basse est zéro par définition de
l'unité ; la borne haute est servie, ou la barre n'existe pas.

**États.**

- valeur dans le budget → rail rempli + marqueur nommé « budget servi » ;
- valeur au-delà → segment de dépassement nommé « au-delà du budget servi »,
  jamais tronqué ni ramené à la borne ;
- âge non publié → « L'âge de cet instantané n'est pas publié. », aucun rail ;
- budget non publié → « Le budget de fraîcheur n'est pas publié pour cette
  route. », aucun rail ;
- les deux absents → **une seule** phrase, jamais deux ;
- `state = stale` servi → ton prudence, sans jamais remplacer le mot servi par
  une couleur.

### `LineageBlock`

**Rôle.** Rendre la lignée servie d'un calcul en paires clé/valeur :
identifiant, moteur, méthode, empreinte d'entrée, empreinte de résultat, statut.

**Pourquoi elle existe.** Sept sites de la page rendent aujourd'hui une phrase
française (« non publié », « version inconnue ») **à l'intérieur d'un `<code>`**
en Geist Mono : l'absence y prend l'apparence exacte d'une valeur servie. Et
`breadth.calculation`, lignée du seul calcul agrégé de la page, est publiée puis
jetée pendant que le pied du cadre dominant réécrit la méthode à la main.

**Donnée exigée.** L'objet `calculation` servi, tel quel. Aucune clé devinée,
aucune valeur reformulée, aucune empreinte raccourcie.

**États.**

- objet absent → « Aucune lignée n'est publiée pour ce calcul. » ;
- clé absente → « non publié » en **texte français ordinaire** porteur de
  `data-absent`, **jamais** dans un `<code>` ;
- valeur servie → chasse fixe, `overflow-wrap: anywhere`, jamais tronquée ;
- `status` servi → StatusChip : `VALID` ton neutre, `PARTIAL` et `STALE` ton
  prudence, valeur hors vocabulaire ton neutre et nommée telle quelle. La
  comparaison porte sur le vocabulaire serveur (`VALID` / `PARTIAL` / `STALE`),
  jamais sur un mot inventé comme `'OK'`.

## 8. Textes d'absence

Une phrase par module, en français, **sans aucun chiffre**, qui dit pourquoi la
donnée manque et ne suggère jamais que la valeur existerait ailleurs.

| Module | Texte exact |
|---|---|
| `population` | La nature de la population n'est pas déclarée par cet instantané : rien n'affirme que ces valeurs soient réelles. |
| `market-map` | Aucun secteur n'est publié dans cet instantané : aucune carte n'est tracée et aucune surface de remplacement n'est dessinée. |
| `breadth` | La largeur de marché n'est pas publiée par le worker : aucune valeur de remplacement n'est affichée et les comptes servis restent seuls. |
| `freshness` | Le budget de fraîcheur n'est pas publié pour cette route : l'âge servi ne peut être jugé sur aucune échelle. |
| `served-state` | Le serveur ne déclare aucun état pour cet instantané : rien ne permet de dire s'il fait autorité. |
| `sectors` | Aucun secteur n'est publié : la répartition sectorielle n'existe pas dans cet instantané. |
| `coverage` | La couverture n'est pas publiée : la part de l'univers réellement observée est inconnue. |
| `window` | La fenêtre d'observation n'est pas publiée : le recul retenu pour construire cet instantané est inconnu. |
| `breadth-lineage` | Aucune lignée n'est publiée pour ce calcul : sa méthode et ses empreintes d'entrée ne sont pas relayées. |
| `unit-convention` | L'unité de calcul n'est pas publiée : les valeurs affichées n'ont aucune échelle déclarée. |
| `discards` | La couverture n'est pas publiée : aucun écart ni aucun rejet n'est connu pour cet instantané. |
| `received-uncovered` | L'instantané ne publie pas la liste nominative des instruments reçus : distinguer un instrument reçu mais non couvert d'un instrument jamais reçu demanderait de la reconstituer. |
| `weights-basis` | La somme de clôtures qui sert de dénominateur aux poids n'est pas publiée : la part affichée ne peut donc pas dire de quel total elle est la part. |
| `map-amplitude` | Aucune bande d'amplitude n'est publiée avec ses seuils : classer les variations par intensité dans le navigateur créerait un classement sans propriétaire. |
| `instrument-freshness` | Aucune date d'observation par instrument n'est publiée : l'instant relayé est celui de la production de l'instantané, et l'attribuer à chaque instrument serait faux. |
| `adjustment-basis` | La base d'ajustement des clôtures n'est pas publiée : rien ne permet de dire si les deux clôtures comparées reposent sur la même base. |
| `calculation-events` | Les identifiants des observations qui alimentent chaque calcul ne sont pas publiés : la lignée servie s'arrête aux empreintes. |
| `sessions` | Aucun calendrier de séance n'est collecté : les heures d'ouverture et de fermeture des places ne sont publiées par aucune source. |
| `indices` | Aucun indice n'est déclaré dans l'univers suivi : le collecteur ne reçoit que des titres, et reconstituer un indice ici inventerait une valeur. |
| `volatility` | Aucun indice de volatilité n'est collecté : rien ne publie une mesure de volatilité à l'échelle du marché. |
| `rates-curve` | Aucun contrat versionné ne publie de courbe de taux : la construire ici créerait une seconde autorité de calcul. |
| `fx` | Aucune cotation de change n'est collectée : la devise de chaque instrument est relayée telle qu'elle est publiée, sans conversion. |
| `correlation` | Aucun contrat ne publie de corrélation entre classes d'actifs : la calculer dans le navigateur produirait une mesure sans propriétaire. |
| `vol-structure` | Aucune structure de volatilité par échéance n'est publiée : rien ne relaie une courbe de volatilité à l'échelle du marché. |
| `sector-return` | Aucun rendement agrégé de secteur n'est publié : l'instantané ne relaie que des rendements par instrument, et les agréger ici créerait une mesure sans méthode déclarée. |
| `focus` | Aucun dossier d'instrument n'est publié : aucune tuile de suivi n'est affichée et aucune série n'est tracée. |
| `inspector` | Aucun instantané n'est publié et aucun élément n'est sélectionné : l'inspecteur n'a rien à décrire. |

**Règle transverse.** Aucun `?`, aucun `—` ambigu, aucun zéro de remplacement,
aucune moyenne, aucune valeur théorique. Le glyphe `?` substitué à trois valeurs
absentes dans le détail d'état partiel (`MarketsPage.tsx`, dette **T4-6**
enregistrée dans `no-ambiguous-dash.test.ts`) est remplacé par
« nombre non publié » ; le fichier sort de `DETTE_T4` et le plafond descend de
17 à 16.

## 9. États dégradés attendus

`ModuleState` publie onze états. Chaque `Widget` servi reçoit désormais
`state={moduleStateOf(queryState, served)}` — **plus aucun `state="ready"`
littéral** — et `served={{ asOf, ageSeconds, snapshotVersion, population }}`,
de sorte que `WidgetMeta` soit enfin monté sur cette page.

| État | Déclencheur servi | Comportement de la page |
|---|---|---|
| `loading` | requête en vol, aucune donnée | `DataStateBoundary` pleine page. La grille n'est pas montée, le bandeau de population n'est pas affiché (la nature est inconnue). Aucun squelette porteur de chiffre. |
| `refreshing` | requête en vol, donnée précédente présente | Le contenu reste, la méta de chaque carte porte « actualisation ». Surbrillance unique à la bascule de `snapshot_version`, jamais une pulsation ; sous `prefers-reduced-motion`, contour statique. |
| `empty` | `state === 'empty'` | `DataStateBoundary` avec la `reason` servie. **Les modules absents des zones 3 et 4 restent affichés** : leur absence ne dépend d'aucun instantané. Aucun module servi n'est monté — pas de zéro, pas de dernière valeur. `freshness` reste monté et montre le budget servi (publié même en `empty`) avec « L'âge de cet instantané n'est pas publié. » |
| `partial` | `data_state === 'partial'` | Tous les widgets servis passent en `partial`. Le détail du cadre écrit les comptes servis, ou « nombre non publié » — jamais `?`. La dominante reste tracée ; les comptes servis restent lisibles. |
| `delayed` | `population === 'DELAYED'` | **Branche déclarée, aujourd'hui inatteignable** : le worker Marchés ne publie que `EMPTY`, `SYNTHETIC` ou `REAL`. Elle reste dans le vocabulaire et **ne doit jamais être simulée** pour une démonstration ou une capture. |
| `stale` | `state === 'stale'` ou `data_state === 'stale'` | Tous les widgets servis passent en `stale`. `BudgetBar` affiche le segment « au-delà du budget servi ». Filigrane explicite sur la dominante. Aucun module ne prétend à la fraîcheur ; la raison servie et l'âge servi sont écrits. |
| `offline` | erreur réseau vers l'API locale | `DataStateBoundary` `offline`. Un instantané conservé n'est jamais présenté comme vivant : il porte son `as_of`, le filigrane hors ligne et son âge servi. Les commandes dépendant du direct sont figées. |
| `error` | réponse invalide ou inattendue | `DataStateBoundary` `error`, aucun rendu partiel, aucune tuile, aucun chiffre. |
| `auth-required` | session absente | `AuthRequiredNotice`. Aucune donnée n'est révélée, aucune existence de ressource n'est confirmée. |
| `closed` | non applicable | Aucun calendrier de séance n'est servi : la page ne peut pas conclure à une place fermée et ne le prétend pas (module `sessions`, LOT 7). |

## 10. Parcours clavier

Ordre logique, focus visible partout, aucun piège, restauration du focus après
tout panneau. WCAG 2.2 AA, zéro violation axe critique ou sérieuse, zoom 200 %.

1. **Lien d'évitement** → `#vx-main`.
2. `h1` « Marchés » et question de page : dans le flux, non focusables.
3. **Bandeau de population** : `role="status"`, non focusable, annoncé à la
   mise à jour.
4. **Dominante** — premier arrêt de focus de la grille : les **trois boutons de
   légende** (`aria-pressed`), `Tab` entre eux, `Espace`/`Entrée` bascule le
   filtre local. Le treemap est `role="img"` avec `aria-label` et `<figcaption>` :
   il n'est **pas** un piège clavier, son équivalent opérable est la table.
5. **Table équivalente** : `role="region"`, `tabIndex={0}`, `<caption>`
   obligatoire (« Équivalent tabulaire de la carte des marchés — mêmes valeurs
   servies, triables »), en-tête collant souligné en cyan. `Tab` atteint les
   boutons de tri des `<th>` (`aria-sort` tenu à jour), puis le bouton ticker de
   chaque ligne (`.vx-markets-pick`, `aria-pressed`). `Entrée` sélectionne.
6. **Sélection** → le focus se déplace vers le titre de la section « Instrument
   sélectionné » de l'inspecteur. `Échap` ferme la section et **restaure le
   focus sur le bouton d'origine** (ligne de table, puce sectorielle ou tuile).
7. **Cartes de contexte** (`breadth`, `freshness`, `served-state`, `coverage`,
   `window`, `breadth-lineage`, `unit-convention`) : arc, rails et barres sont
   `role="img"` avec `aria-label` complet ; aucun arrêt de focus, aucune valeur
   accessible uniquement au survol.
8. **Puces sectorielles** : boutons, même contrat de sélection que la table,
   anneau de focus cyan.
9. **Écarts et rejets** : listes non interactives ; chaque motif est un
   `StatusChip` avec son libellé écrit, jamais une couleur seule.
10. **Modules absents** : `role="status"`, aucun contenu interactif, aucun arrêt
    de focus — huit cartes qui parlent, zéro qui piège.
11. **Rangée de suivi** : chaque `KpiTile` porte **un** lien —
    « Ouvrir le dossier de *ticker* » vers Analyse. C'est **l'unique action
    principale de la page**.
12. **Inspecteur** : dernier dans l'ordre du document ; bouton « Fermer » en
    dernier arrêt ; `Échap` équivalent.

## 11. Défauts fermés par cette conception

| Défaut mesuré | Fermeture |
|---|---|
| Trois `?` substitués à des valeurs absentes (dette T4-6) | phrases « nombre non publié » ; sortie de `DETTE_T4`, plafond 17 → 16 |
| Sept sites de prose française dans un `<code>` | `LineageBlock` : l'absence est du texte, jamais de la chasse fixe |
| `state="ready"` codé en dur sur quatre widgets servis | `moduleStateOf(...)` sur chaque widget ; les huit états sont tenus module par module |
| `quality === 'OK'` → pastille toujours ambre | comparaison au vocabulaire serveur `VALID` / `PARTIAL` / `STALE` |
| Pastille de qualité sans libellé | `StatusChip` refuse le libellé vide et écrit « libellé non publié » |
| Aucune `<caption>` sur la table équivalente | `<caption>` obligatoire, vérifiée par l'e2e |
| Règle CSS morte `.vx-markets-picked` | supprimée |
| Tailles `S/M/L/XL` neutralisées par les aires nommées | aires et tailles alignées, porte `markets-grid-size.test.ts` |
| « Poids » non qualifié sous la dominante | légende : « Taille = part servie du poids global ; sa base n'est pas publiée » + module `weights-basis` |
| Amplitude non encodée sur la dominante | module `map-amplitude` déclaré absent (LOT 9) — jamais un classement inventé côté navigateur |
| `WidgetMeta` jamais montée | prop `served` passée sur chaque widget servi |
| Docstring fausse (« douze modules … cinq servis ») | en-tête réécrit : vingt-sept modules, treize servis |
| Citation périmée dans `CensusBars.tsx` (« pas d'anneau ») | citation alignée sur ADR-017 et `CHART_STANDARD.md`, qui admettent l'arc gradué employé juste à côté |
| Inspecteur exclusif | deux sections coexistantes |

## 12. Portes de conception à exécuter

```
pnpm --filter web test -- design/no-ambiguous-dash.test.ts
pnpm --filter web test -- design/one-dominant-per-page.test.ts
pnpm --filter web test -- design/no-authoritative-calculation.test.ts
pnpm --filter web test -- design/no-fabricated-values.test.ts
pnpm --filter web test -- design/no-raw-colors.test.ts
pnpm --filter web test -- design/markets-grid-size.test.ts        # NOUVELLE
pnpm --filter web test -- design/no-french-prose-in-code.test.ts  # NOUVELLE
pnpm --filter web test -- src/pages/markets
pnpm --filter web exec playwright test e2e/markets.spec.ts
```

Deux portes nouvelles :

- **`markets-grid-size.test.ts`** — pour chaque `data-module`, le span de
  `grid-area` doit égaler le `data-size` déclaré au catalogue.
- **`no-french-prose-in-code.test.ts`** — aucun `<code>` ne peut contenir une
  phrase française d'absence (« non publié », « version inconnue », « non
  fournie ») : une absence n'emprunte jamais l'apparence d'une valeur servie.

## 13. Risques restants, nommés

- La position de `BudgetBar` est une géométrie sur deux durées servies. Elle
  doit rester interdite de toute lecture financière : aucun libellé du type
  « fraîcheur à tant pour cent ». Le verdict reste `state` servi.
- `schema_version` n'est pas publié par `MarketsOverviewResponse` :
  `ProvenanceLine` écrit « version de schéma non publiée ». C'est un manque du
  contrat, à traiter au **LOT 13**, pas à combler côté interface.
- Onze rangées de grille font une page longue à 1280×800. La dominante est
  volontairement en deuxième rangée pour rester atteignable au premier regard ;
  la mesure exacte doit être refaite en capture aux trois viewports avant de
  déclarer la planche terminée.

## 4. Réfutations adversariales — 21 à traiter avant implémentation

**Verdict : CORRECTIONS_REQUISES** — Vérification champ par champ des 13 modules « servi: oui » contre packages/python/vertex_core/src/vertex_core/contracts/, apps/api/src/vertex_api/schemas.py + snapshot_views.py + routes.py, apps/worker/src/vertex_worker/markets.py et le client généré apps/web/src/api/schema.d.ts.

CE QUI TIENT. Tous les champs nommés existent réellement et sont typés dans le client généré : freshness_policy.{budget_seconds,kind,version} (servi dans TOUS les états, empty compris — snapshot_views.py:1975-1992 et 2012-2032, confirmé) ; breadth.{value,value_pct,above_count,down_count,flat_count,covered_count,universe_size,coverage_pct,coverage_threshold,coverage_threshold_pct,status,reason} ; coverage.{expected,received,covered,discarded,discarded_tickers[].{ticker,reason},rejected_records[].{event_id,reason},observations_considered,lookback_seconds} ; sectors[].{sector,label,declared_count,covered_count} et tickers[].{ticker,sector,trading_day,previous_trading_day,last_close,previous_close,currency,return_1d,return_1d_pct,weight_in_sector(_pct),weight_global(_pct),quality,synthetic,calculation} ; state, data_state, population, unit, display_unit, engine_version, snapshot_version, conclusion, as_of, age_seconds, reason. La revendication « schema_version n'est pas publié par cette réponse » est exacte (le worker le met bien dans le contenu, markets.py:653, mais le relais ne le porte pas). FOCUS_LIMIT = 4 et bars_status existent (apps/web/src/pages/focusView.ts:19, apps/worker/src/vertex_worker/opportunities.py:711). Le défaut quality === 'OK' est réel (InstrumentTile.tsx:102, contre _QUALITY_ORDER = VALID/PARTIAL/STALE). BudgetBar est défendable : published_budget renvoie exactement le closed_session_budget qui décide de state='stale' (apps/api/src/vertex_api/freshness.py:99-131), donc le rail ne peut pas contredire le verdict serveur — risque résiduel accepté, pas violation.

CE QUI NE TIENT PAS — huit violations. Trois sont structurelles et touchent la dominante : (1) le treemap renormalise les aires dès que la légende filtre, donc l'aire cesse d'être weight_global_pct et devient une part calculée dans le navigateur (loi 3), alors que la conception jure que la légende « ne modifie aucune valeur servie » ; (2) ce même poids est une part d'une somme de clôtures MULTI-DEVISES sans devise, sans unité, sans méthode et sans version — le worker l'admet (« descriptive Decimal shares, not registry calcs ») et le module fx de la conception déclare qu'aucune conversion n'existe (loi 7) ; (3) le contrat Marchés ne publie AUCUNE source ni AUCUN droit, alors que le worker les possède par observation et les jette (loi 7) — aucun module servi de cette page ne peut donc satisfaire la loi 7 en entier, et la conception ne le dit qu'une fois, en note.

Deux violations portent sur la lignée, cœur des deux modules nouveaux : (4) LineageBlock compare calculation.status à VALID/PARTIAL/STALE, qui est le vocabulaire de MarketsTicker.quality ; le vocabulaire réel d'un CalculationRecord est OK/INVALID/NOT_IMPLEMENTED, donc le seul statut sain jamais servi serait déclaré « hors vocabulaire » et les deux statuts alarmants passeraient en ton neutre ; (5) l'objet calculation est un FrozenStrMapping sans aucune clé déclarée, typé { [key: string]: unknown } côté client — les six clés que LineageBlock rend sont exactement devinées, contre la promesse « aucune clé n'est devinée ».

Trois violations de présentation : (6) unit/display_unit sont, par contrat, l'unité du rendement sectoriel seulement, et la conception les présente comme l'unité « des valeurs de cette page » qui en compte au moins cinq d'unités différentes ; (7) la fenêtre de sparkline est un découpage client de 30 séances présenté comme « fenêtre servie » ; (8) les §8, §11 et §12 ferment un défaut inexistant — MarketsPage.tsx n'a plus aucun « ? » et la liste DETTE_T4 ainsi que son plafond ont été supprimés du dépôt avec instruction explicite de ne pas les réintroduire.

Aucun module « servi: oui » ne dépend d'un lot d'intelligence non livré : les 25 modules absents sont correctement motivés et leurs lots bloquants correspondent aux manques réels du contrat. Le problème n'est pas l'inventaire de l'absence, il est l'excès de confiance dans ce qui est déclaré servi.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `breadth-lineage` | Loi 4 — absent, zéro, réel et les autres états sont distincts et le DISENT (ici : un état servi rangé hors vocabulaire) | packages/python/vertex_core/src/vertex_core/contracts/enums.py:200-209 — CalculationStatus = OK \| INVALID \| NOT_IMPLEMENTED. apps/worker/src/vertex_worker/markets.py:353-362 — _calculation_meta publie "status": record.status.value, donc littéralement « OK », « INVALID » ou « NOT_IMPLEMENTED ». La conception impose à LineageBlock : « comparaison au vocabulaire serveur uniquement (VALID/PARTIAL/STALE), jamais à un mot inventé comme 'OK' ». C'est l'inverse : VALID/PARTIAL/STALE est le vocabulaire de MarketsTicker.quality (_QUALITY_ORDER, markets.py:111), pas celui d'un CalculationRecord. | Séparer les deux vocabulaires servis. LineageBlock compare calculation.status à OK (ton neutre), INVALID et NOT_IMPLEMENTED (ton prudence, libellé écrit) ; StatusChip de qualité compare quality à VALID/PARTIAL/STALE. Sans cela, le seul statut jamais servi pour une lignée saine (« OK ») serait affiché « hors vocabulaire », et INVALID / NOT_IMPLEMENTED — les deux qui doivent alerter — passeraient en ton neutre. Ajouter un test qui verrouille les deux listes sur les énumérations Python. |
| `market-map` | Loi 3 — le navigateur ne calcule jamais un ratio ni un classement ; aucun graphique ne dessine une grandeur non servie | apps/web/src/pages/markets/MarketMap.tsx:40-60 — buildTreemapData(sectors, visibleGroups) FILTRE les feuilles avant de les remettre à ECharts. Un treemap redistribue toujours 100 % du canevas entre les feuilles restantes : dès qu'un groupe de signe est masqué par la légende, l'aire d'une tuile n'est plus weight_global_pct (part de universe_total, apps/worker/src/vertex_worker/markets.py:496-516) mais une part RENORMALISÉE du sous-ensemble filtré, calculée par le moteur dans le navigateur. La conception affirme pourtant que la légende est une commande de vue qui « ne modifie aucune valeur servie » et que « Aire de tuile = weight_global_pct servi ». | Soit la légende n'enlève rien de la géométrie (les tuiles masquées gardent leur aire et passent en état atténué explicitement nommé), soit le filtre reste et le cadre DIT à l'écran que « les aires sont renormalisées sur le sous-ensemble affiché et ne sont plus la part servie du poids global », avec un retour visible à l'état non filtré. Ajouter une porte e2e qui compare l'aire d'une tuile filtrée / non filtrée. |
| `market-map` | Loi 7 — toute valeur critique porte valeur, unité, devise, source, as_of, fraîcheur, qualité, méthode et version | apps/worker/src/vertex_worker/markets.py:496-516 — weight_in_sector et weight_global sont calculés comme close / sector_total et close / universe_total, où universe_total additionne latest.close de TOUS les instruments couverts SANS regarder la devise (aucune occurrence de currency entre les lignes 496 et 516 ; grep currency dans markets.py ne renvoie que 281, 323-324, 332, 485). MarketsTicker.currency est str \| None et n'est contraint par aucun invariant d'unicité (apps/api/src/vertex_api/schemas.py:204-232). Le commentaire du worker l'admet : « descriptive Decimal shares (labeled, not registry calcs) » — donc aucun CalculationRecord, aucune method, aucune version, aucune unité. La conception fait pourtant de cette grandeur la GÉOMÉTRIE du seul visuel dominant de la page, et son pied revendique « méthode servie market.simple_return » — méthode qui gouverne le rendement, pas le poids. Son propre module fx déclare qu'aucune cotation de change n'est collectée. | Ne pas encoder une somme de clôtures multi-devises comme aire dominante. Trois issues, une seule à choisir : (a) le worker publie le poids avec sa base, sa devise de base et sa méthode versionnée (LOT 9) et la carte attend ce contrat ; (b) la carte encode une grandeur qui porte déjà sa méthode servie (return_1d_pct) et le poids sort de la géométrie ; (c) le module market-map descend en absent SERVER_CONTRACT_MISSING jusqu'au LOT 9. Dans tous les cas, retirer du pied la revendication « méthode servie market.simple_return » pour l'aire. |
| `unit-convention` | Loi 7 — unité déclarée par grandeur ; Loi 4 — une unité non publiée n'est pas l'unité d'à côté | apps/api/src/vertex_api/snapshot_views.py:803 MARKETS_UNIT = "return_ratio" et 2001-2004, où le relais refuse le contenu avec le message « unit: the published sector-return unit is required ». unit et display_unit sont donc, par contrat, l'unité du RENDEMENT SECTORIEL et de rien d'autre. La conception demande au module unit-convention de répondre « Dans quelle unité les valeurs de cette page sont-elles calculées et affichées ? » avec ces deux champs, et au méta du cadre dominant de « lire ces champs au lieu de les écrire en prose ». Or la page affiche au moins quatre grandeurs d'unités différentes : weight_global_pct (part), breadth.value_pct (participation), coverage_pct (couverture), above/down/flat_count (dénombrements), lookback_seconds (durée). | Reformuler la question du module en « Dans quelle unité le rendement servi est-il calculé et affiché ? » et écrire explicitement que le contrat ne publie l'unité que de return_1d. Chaque autre grandeur affiche « unité non publiée par le contrat » jusqu'à ce que le LOT 9 publie une unité par grandeur. Supprimer du pied de market-map la phrase « unité servie affichée dans l'unité d'affichage servie », qui attribue l'unité du rendement à l'aire des tuiles. |
| `served-state` | Loi 7 — toute valeur critique porte sa SOURCE (et son droit) | apps/worker/src/vertex_worker/markets.py:128-138 — QuoteRecord porte source et rights par observation, et markets.py:141-142 ne s'en sert que pour dériver le booléen synthetic. apps/api/src/vertex_api/schemas.py:304-336 — MarketsOverviewResponse ne publie AUCUN champ source ni rights, ni au niveau instantané ni au niveau instrument (à comparer avec AttentionItem, schemas.py:152-166, qui publie sources et rights). Confirmé dans le client généré : apps/web/src/api/schema.d.ts, MarketsOverviewResponse / MarketsSector / MarketsTicker n'ont ni source ni rights. La conception ne le déclare qu'une fois, en note de pied de served-state (« aucune source nommée par le contrat »), pendant que douze autres modules servis revendiquent une provenance complète. | Ajouter un module absent explicite (par exemple source-rights, SERVER_CONTRACT_MISSING, LOT 9 — publier source et rights par instrument, que le worker possède déjà et jette) dans la zone RISQUE, et retirer de tous les pieds servis toute formule laissant croire à une provenance complète. Tant que le contrat ne publie ni source ni droit, aucun module de cette page ne satisfait la loi 7 dans son intégralité et la page doit le dire une fois, à un seul endroit propriétaire. |
| `breadth-lineage` | Loi 7 — la méthode et la version doivent être portées par un contrat versionné, pas devinées | apps/api/src/vertex_api/schemas.py:243-270 — MarketsBreadth.calculation: FrozenStrMapping \| None, et MarketsTicker.calculation: FrozenStrMapping (schemas.py:204-232) : aucune clé n'est déclarée. Le relais ne vérifie que le TYPE des clés : apps/api/src/vertex_api/snapshot_views.py:302-317 (_wire_mapping) et 1788-1790, 1847. Le client généré le confirme : apps/web/src/api/schema.d.ts → calculation: { [key: string]: unknown }. La conception affirme pourtant « L'objet calculation servi, tel quel (calculation_id, engine_version, method, input_hash, result_hash, status) » et « Aucune clé n'est devinée » : les six clés sont exactement devinées, contre une cartographie non typée qu'aucune version de schéma ne garantit. | Publier un CalculationLineageView typé dans apps/api/src/vertex_api/schemas.py (calculation_id, engine_version, method, input_hash, result_hash, status), le valider clé par clé au relais, régénérer le client OpenAPI, puis seulement déclarer breadth-lineage « servi ». Sinon le module reste AbsentModule SERVER_CONTRACT_MISSING (LOT 13), et le pied du cadre dominant cesse de réécrire la méthode à la main sans la remplacer par une lecture non garantie. |
| `focus` | Loi 7 — la fenêtre affichée doit être la fenêtre servie, ou être nommée comme une décision d'affichage | apps/web/src/components/widgets/InstrumentTile.tsx:36 LINE_WINDOW = 30 et l. 50 bars.slice(-LINE_WINDOW) : la fenêtre tracée est un découpage CLIENT de 30 séances. Le dossier d'analyse publie la fenêtre RÉELLE de la série (first_trading_day, last_trading_day, count, currency, adjustment_basis — lus par barsViewOf, apps/web/src/pages/analysis/analysisView.ts:59-105) ; aucune fenêtre de 30 séances n'est servie nulle part. La conception écrit pourtant en pied de focus « fenêtre servie de la série », et KpiTileSeries.windowLabel (apps/web/src/components/widgets/KpiTile.tsx:46-53) est une chaîne fournie par l'appelant, pas par le serveur. | Écrire le libellé de fenêtre à partir des jours de séance réellement tracés et le qualifier : « 30 dernières séances servies, du <premier jour servi> au <dernier jour servi> — plafond d'affichage, la série servie en compte <count servi> ». Remplacer « fenêtre servie de la série » par cette formule dans le pied du module. |
| `market-map` | Loi 4 — l'état mesuré doit être décrit tel qu'il est ; une correction ne peut pas fermer un défaut inexistant | apps/web/src/pages/markets/MarketsPage.tsx:138-151 — le détail d'état partiel écrit déjà « nombre non publié d' », « un nombre non publié », « raison non publiée », « non publié » : aucun glyphe ? n'y subsiste (grep de '?' dans le fichier : zéro occurrence). apps/web/src/design/no-ambiguous-dash.test.ts:66-73 — « LA DETTE EST REMBOURSÉE […] La liste et son mécanisme ont disparu avec le dernier fichier converti […] Ne les réintroduisez pas ». Les §8, §11 et §12 de la conception décrivent « trois ? substitués à des valeurs absentes (dette T4-6) », la sortie du fichier de DETTE_T4 et un plafond qui descend « de 17 à 16 » : ni la dette, ni la liste, ni le plafond n'existent dans le dépôt. | Supprimer ces trois affirmations et le gain qu'elles revendiquent. Réviser la §11 en ne conservant que les défauts encore mesurables (state="ready" en dur, quality === 'OK', absence de <caption>, aires vs data-size, WidgetMeta non montée) et vérifier chacun par grep avant de le lister. Ne réintroduire sous aucune forme une liste d'exemption dans no-ambiguous-dash.test.ts. |

**Verdict : CORRECTIONS_REQUISES** — Audit adversarial « invariants » de la conception de Marchés, mené module par module contre le code réel de /home/user/vertex-merge (apps/web/src/pages/markets/, components/markets/, design/, apps/worker/src/vertex_worker/markets.py, apps/api/openapi.json).

PROPRE, vérifié explicitement : Loi 1 — aucun module, contrat ni chemin de données ne touche compte, solde, cash, NAV, position, P&L ou exécution ; les trois contrats consommés (markets/overview, opportunities, analysis/{instrument}) ne portent que de la donnée de marché. Loi 2 — aucun mot du vocabulaire d'ordre à l'écran ; les occurrences d'« ordre » dans la fiche désignent une séquence documentaire et ne deviennent jamais du texte d'interface (à surveiller si un pied reprend « ordre servi » : préférer « rang servi »). Loi 5 — aucune probabilité, aucun score prédictif ; `breadth` est un ratio de participation descriptif d'un observé, et `conclusion` est une phrase serveur verbatim. Textes d'absence — aucun ne contient de chiffre. Loi 6, dominante — un seul `data-rank="dominant"` (le treemap), un seul moteur graphique chargé sur la route. Couleur seule — chaque signe est doublé d'un glyphe ▲▼= et du texte signé servi.

13 VIOLATIONS retenues, dont cinq bloquantes.

Les trois plus graves sont mécaniques, pas rédactionnelles. (1) Loi 3 : la table « équivalente » de la dominante trie en convertissant les décimales servies en flottants (`geometryNumber(left) - geometryNumber(right)`, MarketsTable.tsx:139) — le navigateur produit donc le classement financier que la conception refuse par ailleurs au module `map-amplitude`, et la porte no-authoritative-calculation ne le voit pas parce que son vocabulaire fermé ignore `last_close` et `weight_global_pct`. (2) Loi 4 : `geometryNumber` (marketsView.ts:50) transforme toute chaîne illisible en `0`, ce qui donne une tuile d'aire nulle sur la carte et un rang de zéro dans la table. (3) Loi 4 : le dispositif d'états promis en §9 ne peut pas fonctionner — `moduleStateOf` ne rend jamais `partial`, ignore `data_state`, et l'objet `served` prescrit n'a pas la clé `state` qu'il exige, si bien qu'un instantané périmé s'afficherait en `ready` sur les quatre widgets.

S'y ajoutent : un vocabulaire serveur inventé pour `LineageBlock` (`calculation.status` vaut OK|INVALID|NOT_IMPLEMENTED, pas VALID|PARTIAL|STALE — un calcul invalide se lirait comme un calcul valide) ; une seconde action non cataloguée et absente du parcours clavier (le bouton « Exporter (CSV) », premier arrêt de focus de la table) ; un texte d'absence qui affirme une méthode non publiée (`weights-basis`) en contradiction avec la légende de la même page ; une population réduite à trois étiquettes là où le bandeau fail-closed en porte neuf plus deux natures d'alerte ; deux propriétaires du vocabulaire de nature ; quatorze cartes identiques formant deux grilles régulières là où le brief exige l'asymétrie ; et deux affirmations de §8/§11 non mesurées — le défaut `?` n'existe pas et `DETTE_T4` a été supprimée avec interdiction écrite de la réintroduire.

La conception est solide sur l'honnêteté déclarative — elle branche enfin `freshness_policy`, `breadth.value`, `coverage_threshold` et `breadth.calculation`, tous publiés et jamais lus — mais elle ne peut être exécutée en l'état : les corrections 1 à 6 doivent être intégrées à la fiche avant tout code.

| Module | Loi enfreinte | Preuve | Correction |
|---|---|---|---|
| `market-map` | Loi 4 — une absence n'est jamais un zéro | apps/web/src/components/markets/marketsView.ts:50-53 — `geometryNumber` retourne `0` dès que `Number.parseFloat` échoue ; consommé en aire de tuile à apps/web/src/pages/markets/MarketMap.tsx:55 (`geometryNumber(entry.ticker.weight_global_pct)`) et en clé de tri à apps/web/src/pages/markets/MarketsTable.tsx:139. La conception reconduit les deux usages sans les nommer. | `geometryNumber` doit rendre `null` sur toute chaîne illisible. Une tuile dont le poids servi n'est pas lisible n'est PAS dessinée à aire nulle : elle sort de la carte et entre dans une liste nommée « poids servi illisible » sous la dominante, et la ligne de table correspondante porte `data-absent` au lieu d'un rang. Ajouter un test de propriété sur une chaîne non décimale servie. |
| `market-map` | Loi 3 — le navigateur ne calcule jamais un classement | apps/web/src/pages/markets/MarketsTable.tsx:96-113 (`rawValue` lit `last_close`, `return_1d_pct`, `weight_in_sector_pct`, `weight_global_pct`) puis 135-142 : `geometryNumber(left) - geometryNumber(right)`. La fiche §1, §4 et §10.5 érige cette table en « équivalent tabulaire » de la dominante, donc le rang que lit un lecteur d'écran est calculé par le navigateur en flottant, sur des décimales servies. La conception refuse pourtant exactement cela au module `map-amplitude` (« classer les variations par intensité dans le navigateur créerait un classement sans propriétaire »). La porte design/no-authoritative-calculation.test.ts ne le voit pas : son vocabulaire fermé contient `close`, `weight`, `ratio` mais pas `last_close` ni `weight_global_pct`, et `rawValue` masque le nom. | Supprimer toute conversion numérique du tri. Deux issues admises : (a) la table conserve l'ORDRE SERVI et le dit, le tri se limitant à un réarrangement lexicographique sur chaînes servies via un comparateur décimal exact (comparaison chiffre à chiffre, aucun `parseFloat`), étiqueté « réarrangement d'affichage, aucun rang servi » ; (b) LOT 9 publie un `rank` servi par colonne et la table le relaie. Élargir le vocabulaire fermé de la porte aux noms réels du contrat Marchés. |
| `freshness` | Loi 3 — le navigateur ne calcule jamais un ratio | Nouvelle primitive `BudgetBar` : la position est le quotient `age_seconds / freshness_policy.budget_seconds`, calculé côté navigateur. La docstring de `FreshnessPolicyView` (apps/api/openapi.json, schéma FreshnessPolicyView) autorise « le client pose `age_seconds` sur cette échelle » mais interdit dans la même phrase d'« inventer un TTL ou un ratio ». La conception ne borne l'interdiction qu'aux LIBELLÉS (« pas de fraîcheur à tant pour cent ») et laisse le quotient libre ailleurs. | Écrire la contrainte au niveau du DOM, pas de la prose : le quotient n'existe que comme longueur CSS (`clamp`), jamais dans un texte, un `aria-label`, un `title`, un `aria-valuenow` ni un `data-*`. Le nom accessible ne contient que les deux durées servies, `freshness_policy.kind`, `.version` et le mot `state` servi. Au-delà du budget, l'échelle ne se re-normalise pas. Ajouter une porte qui refuse tout opérateur `/` dont une opérande lit `age_seconds` ou `budget_seconds` hors d'une propriété de style. |
| `breadth-lineage` | Loi 7 — méthode et version servies, jamais inventées (et Loi 4) | La conception impose à `LineageBlock` le vocabulaire `VALID \| PARTIAL \| STALE` pour `calculation.status`. Or ce champ vient de `record.status.value` (apps/worker/src/vertex_worker/markets.py:353-361) dont l'énumération est `CalculationStatus = OK \| INVALID \| NOT_IMPLEMENTED` (packages/python/vertex_core/src/vertex_core/contracts/enums.py:200-209). `VALID/PARTIAL/STALE` est le vocabulaire d'un AUTRE champ, `MarketsTicker.quality` (`_QUALITY_ORDER`, markets.py:111). Conséquence directe : un calcul `INVALID` ou `NOT_IMPLEMENTED` tombe dans « valeur hors vocabulaire → ton neutre » et se lit exactement comme un calcul valide. | Deux vocabulaires nommés séparément dans la fiche : `calculation.status` ∈ {OK, INVALID, NOT_IMPLEMENTED} — `OK` neutre, `INVALID` et `NOT_IMPLEMENTED` ton prudence avec le mot servi écrit en toutes lettres ; `quality` ∈ {VALID, PARTIAL, STALE} pour `sectors[].tickers[].quality` et la rangée de suivi. Aucune valeur hors énumération ne peut retomber en ton neutre : elle est nommée telle quelle en ton prudence. |
| `served-state` | Loi 4 — les huit états sont distincts et chacun le dit | §9 promet que chaque widget servi reçoit `state={moduleStateOf(queryState, served)}` et `served={{ asOf, ageSeconds, snapshotVersion, population }}`. Deux défauts mécaniques : (1) `moduleStateOf` (apps/web/src/components/moduleState.ts:48-69) ne rend JAMAIS `partial` et ignore `data_state` — la ligne « partial \| data_state === 'partial' \| tous les widgets passent en partial » est inatteignable, et `data_state === 'stale'` se rend `ready` ; (2) l'objet passé est un `WidgetServed` (apps/web/src/components/widgets/Widget.tsx:65-72) alors que `moduleStateOf` attend un `ServedFacts` qui exige la clé `state` (moduleState.ts:44-47) : `served.state` vaut `null`, les branches `empty`, `stale` et `closed` sont sautées et un instantané périmé s'affiche en `ready`. | Prescrire explicitement deux objets distincts : `moduleStateOf(queryState, { state: data.state, dataState: data.data_state, population: data.population })` — en étendant `ServedFacts` et `moduleStateOf` d'une branche `dataState === 'partial' → 'partial'` et `dataState === 'stale' → 'stale'` — et `served={{ asOf, ageSeconds, snapshotVersion, population }}` pour la seule méta. Ou réutiliser `frameStateOf` (MarketsPage.tsx:53-77) qui traite déjà `data_state`. Test : un instantané `data_state='partial'` doit rendre les quatre widgets en `partial`. |
| `market-map` | Loi 6 — une seule action principale, et tout parcours clavier déclaré | apps/web/src/pages/markets/MarketsTable.tsx:155-168 : bouton « Exporter (CSV) » qui écrit un fichier via `saveTextAsFile`. C'est une action réelle, pas une commande de vue. Elle apparaît dans le champ `focal` de la conception (« table équivalente triable avec <caption> et export CSV ») mais dans AUCUN module du catalogue des 27, aucune zone, aucun pied, et aucune étape du parcours clavier §10 — alors qu'elle est le premier arrêt de focus à l'intérieur de la table équivalente, avant les boutons de tri. | Trancher et l'écrire : soit l'export sort de la page, soit il devient un module catalogué (titre, question, taille, état dégradé, pied de provenance nommant la population exportée) inséré explicitement entre l'étape 4 et l'étape 5 du parcours clavier, avec la mention que l'unique action PRINCIPALE reste « Ouvrir le dossier de l'instrument » et que l'export est une action secondaire déclarée. |
| `weights-basis` | Loi 7 — toute valeur critique porte sa méthode servie (et Loi 4) | Texte d'absence proposé : « La somme de clôtures qui sert de dénominateur aux poids n'est pas publiée ». Le dénominateur est un `Decimal` interne au worker (apps/worker/src/vertex_worker/markets.py:497-502, `sector_totals` et `universe_total`) qui n'est justement PAS publié — l'écran affirmerait donc comme un fait une méthode que le contrat ne sert pas. La même fiche écrit à l'opposé, en §11 : « Taille = part servie du poids global ; sa base n'est pas publiée ». Deux phrases contradictoires sur le même fait, sur la même page. | Texte : « La base des poids servis n'est pas publiée : la part affichée ne peut pas dire de quel total elle est la part. » Aucune mention d'une somme de clôtures tant que LOT 9 ne publie pas la base ET sa nature. Même passe sur `instrument-freshness` (« l'instant relayé est celui de la production de l'instantané ») et `indices` (« le collecteur ne reçoit que des titres ») : ne nommer que ce que le contrat publie. |
| `population` | Loi 4 — huit états distincts, chacun nommé à l'écran | La conception réduit le champ à « population (EMPTY \| SYNTHETIC \| REAL) » et déclare `delayed` « inatteignable ». Le propriétaire réel du vocabulaire, `SyntheticBanner` (apps/web/src/components/SyntheticBanner.tsx:45-120), publie NEUF natures distinctes — REAL, DELAYED, THEORETICAL, SIMULATED, SYNTHETIC, DEMO, USER_DECLARED, SYNTHETIC_MARKS_REAL_LEDGER, EMPTY — plus deux natures fail-closed : `UNDECLARED` et `UNRECOGNISED` (lignes 105-120), en ton `risk` et `role="alert"`. Le `texteAbsence` du module et le tableau §9 ne nomment aucune de ces deux natures fail-closed ; une étiquette forgée ou hors vocabulaire n'a donc aucun comportement déclaré par la fiche. | Le module `population` déclare le vocabulaire fermé complet, plus les deux natures fail-closed avec leur ton et leur `role="alert"`, et l'invariant « une étiquette inconnue AVERTIT, elle ne disparaît jamais ». Remplacer « (EMPTY \| SYNTHETIC \| REAL) » par « vocabulaire fermé de POPULATION_LABELS ; le worker Marchés n'en émet aujourd'hui que trois, ce qui ne réduit pas le vocabulaire rendu ». |
| `population` | Loi 6 — un seul propriétaire, une seule voix par page | Le pied du module affirme « le bandeau est le seul propriétaire de ce vocabulaire, aucune autre carte ne le répète », mais la conception ne supprime pas la rangée méta de la dominante qui imprime `provenanceSentence(nature)` (apps/web/src/pages/markets/MarketsPage.tsx:193) sous une étiquette `<dt>Source</dt>` (ligne 185) — alors que le contrat `MarketsOverviewResponse` ne publie AUCUN champ de source, ce que la conception reconnaît elle-même au pied de `served-state` (« aucune source nommée par le contrat »). | Supprimer la rangée `Source` de la méta de la dominante ; le recensement des drapeaux `synthetic` reste au seul bandeau. Si un fait doit rester sous la carte, l'écrire « Nature déclarée : voir le bandeau » sans recompter ni renommer une source. Ajouter à la porte de page une assertion : `provenanceSentence` n'a qu'un seul site de rendu. |
| `received-uncovered, weights-basis, map-amplitude, instrument-freshness, adjustment-basis, calculation-events, sessions, indices, volatility, rates-curve, fx, correlation, vol-structure, sector-return` | Composition — bento asymétrique exigé, grille régulière proposée | Le `grid-template-areas` de §5 pose quatorze cartes de 3 colonnes en deux matrices parfaitement régulières : rangées 6-8 (`recu\|wbas`, `ampl\|ifre`, `adjb\|cevt`, soit 3×2 surfaces identiques à droite de `disc`) et rangées 9-10 (`sess\|indx\|vola\|rate`, `fx\|corr\|vols\|sret`, soit 4×2 surfaces identiques). Le relief revendiqué ne vient que de deux spans (`sectors` 6×2, `discards` 6×3) ; plus de la moitié de la page est une grille uniforme, ce que le brief Titan Ledger refuse. | Regrouper les absences par LOT bloquant en surfaces franchement différentes : une carte large par lot (LOT 7, LOT 8, LOT 9, LOT 13) listant ses sujets absents avec leur motif typé, au lieu de quatorze cartes identiques. Chaque sujet garde son `data-module`, son motif et son texte d'absence — la porte `markets-grid-size.test.ts` compare alors le span au `data-size` de la carte de lot, pas d'une vignette. |
| `market-map, served-state` | Loi 7 — preuve mesurée, jamais supposée | §8 et §11 déclarent fermer un défaut mesuré inexistant et prescrivent un remède interdit. (1) Aucun glyphe `?` substitué n'existe dans la page : le détail d'état partiel écrit déjà « nombre non publié » (apps/web/src/pages/markets/MarketsPage.tsx:141-143) ; `grep` de `'?'` sur `pages/markets/` et `components/markets/` ne rend rien. (2) La liste `DETTE_T4` et son cliquet n'existent plus : la docstring de la porte les déclare supprimés avec le dernier fichier converti et interdit de les réintroduire (apps/web/src/design/no-ambiguous-dash.test.ts:62-72) ; il n'existe donc aucun « plafond 17 » à faire descendre à 16. | Supprimer ces deux affirmations de §8 et de la table §11. Aucun lot ne doit rouvrir `DETTE_T4` ni recréer un plafond. Toute ligne de la table « Défauts fermés » doit citer un fichier:ligne vérifié ; celles qui n'en citent pas sortent de la fiche. |
| `received-uncovered` | Loi 4 — un texte d'absence ne suggère jamais que la valeur existe ailleurs | Texte proposé : « … distinguer un instrument reçu mais non couvert d'un instrument jamais reçu demanderait de la reconstituer. » La proposition subordonnée laisse entendre que l'interface pourrait reconstituer la liste. Le worker ne publie que la longueur de `received` (apps/worker/src/vertex_worker/markets.py:429). | « L'instantané ne publie pas la liste nominative des instruments reçus : seul leur nombre est servi. Un instrument reçu sans couverture ne peut donc pas être distingué d'un instrument jamais reçu. » |
| `breadth` | Brief — aucune jauge circulaire ; arbitrage manquant | Le module conserve `ArcGauge` (apps/web/src/pages/markets/BreadthPanel.tsx:80-89), une forme radiale, alors que la lentille de conception proscrit « toute jauge circulaire ». La fiche §11 tranche le conflit d'autorité par une simple ligne de citation (« citation alignée sur ADR-017 et CHART_STANDARD.md, qui admettent l'arc gradué »). Le canon interne l'admet en effet (docs/05-design/CHART_STANDARD.md:7 « jauges en arc graduées », « anneaux à chiffre central » ; ADR-017), mais une fiche de page ne peut pas arbitrer seule un désaccord entre le brief d'identité et un ADR accepté. | Ouvrir un ADR d'arbitrage (LOT 3, doctrine visuelle Titan Ledger) : soit l'arc gradué reste admis et le brief est amendé, soit `breadth` passe à la famille rail déjà présente sur la page (`LinearGauge`) et l'arc disparaît des douze espaces. Tant que l'ADR n'est pas accepté, `breadth` reste sur le rail et la fiche cite la décision en attente au lieu de la trancher. |

## 5. Primitives neuves exigées — 2

- **BudgetBar** — Rail gradué qui pose une valeur servie sur une échelle servie exprimée dans LA MÊME unité — l'âge d'un instantané sur son budget de fraîcheur. Il partage le rail, les jetons et les graduations de LinearGauge : il n'ajoute AUCUNE famille visuelle nouvelle, seulement une règle de géométrie. LinearGauge exige une position servie EN POURCENTAGE ; le contrat ne publie ici ni pourcentage ni ratio, seulement deux durées servies. La position est un rapport de géométrie entre deux chaînes servies, du même ordre que la hauteur d'une barre de DayBars ou l'aire d'une tuile de treemap — jamais un ratio financier, jamais un statut reconstruit : le verdict de fraîcheur reste `state` servi par le serveur. Le contrat de `FreshnessPolicyView` prescrit lui-même cet usage : « le client pose `age_seconds` sur cette échelle et n'invente ni TTL ni ratio ».. Donnée exigée : `age_seconds` (valeur servie) et `freshness_policy.budget_seconds` (borne haute servie), dans la même unité, plus `freshness_policy.kind` et `freshness_policy.version` affichés en toutes lettres à côté du rail. Aucune borne inventée : la borne basse est zéro par définition de l'unité, la borne haute est servie ou la barre n'existe pas.. États : valeur dans le budget → rail rempli + marqueur de budget nommé (« budget servi ») ; valeur au-delà du budget → segment de dépassement nommé « au-delà du budget servi », jamais tronqué ni ramené à la borne ; âge non publié → phrase « L'âge de cet instantané n'est pas publié. » et AUCUN rail ; budget non publié → phrase « Le budget de fraîcheur n'est pas publié pour cette route. » et AUCUN rail ; les deux absents → une seule phrase, jamais deux ; état `stale` servi → le rail prend le ton prudence, sans jamais remplacer le mot servi par une couleur.
- **LineageBlock** — Rend la lignée SERVIE d'un calcul en paires clé/valeur : identifiant, moteur, méthode, empreinte d'entrée, empreinte de résultat, statut. Il existe parce que sept sites de la page rendent aujourd'hui une phrase française (« non publié », « version inconnue ») À L'INTÉRIEUR d'un `<code>` en Geist Mono : l'absence y prend l'apparence exacte d'une valeur servie. Il existe aussi parce que `breadth.calculation` — la lignée du seul calcul agrégé de la page — est publiée puis jetée, pendant que le pied du cadre dominant réécrit la méthode à la main.. Donnée exigée : L'objet `calculation` servi, tel quel : `breadth.calculation` ou `sectors[].tickers[].calculation` (`calculation_id`, `engine_version`, `method`, `input_hash`, `result_hash`, `status`). Aucune clé n'est devinée, aucune valeur n'est reformulée, aucune empreinte n'est raccourcie.. États : objet absent → « Aucune lignée n'est publiée pour ce calcul. » ; clé absente → « non publié » en TEXTE FRANÇAIS ordinaire porteur de `data-absent`, JAMAIS dans un `<code>` ; valeur servie → chasse fixe, coupure autorisée (`overflow-wrap: anywhere`), jamais tronquée ni abrégée ; `status` servi → StatusChip (`VALID` ton neutre, `PARTIAL` et `STALE` ton prudence, valeur hors vocabulaire ton neutre et nommée telle quelle) ; comparaison au vocabulaire serveur uniquement (`VALID`/`PARTIAL`/`STALE`), jamais à un mot inventé.
