# Plan directeur — Widgets v2 (canon Titanium Ledger v2)

Statut : plan de chantier du lot **C0** (branche `lot/w2-c0-canon-v2-20260903`, base `main@4fc901a`). Autorité : `docs/09-adr/017-titanium-ledger-v2-formes-widgets.md` (ADR-017 : formes admises, formes interdites), la spécification consolidée du 2026-09-03 et ses deux critiques adverses (canon ; vérité des données), appliquées ici sauf là où la décision v2 les rend caduques. Les citations `fichier:ligne` proviennent de ces passes (relevées sur `main@4fc901a` le 2026-09-03) ; ce lot ne les a pas re-vérifiées une à une.

Conventions : **[F]** fait vérifié par ces passes ; **[I]** inférence ou décision à confirmer au lot concerné. Classe **A** = servi par un contrat existant ; **B** = calcul ou relais serveur requis (lot S) ; **C** = refusé, rendu par un état honnête (motif cité).

## 0. Règles non négociables (inchangées par la v2)

- aucun calcul financier en TypeScript : les primitives ne reçoivent que des tableaux ou chaînes à noms neutres (`value`, `pct`, `parts`, `points`) et ne calculent que de la géométrie (`apps/web/src/design/no-authoritative-calculation.test.ts`) ; aucun nombre dérivé n'est écrit ;
- aucune valeur fabriquée ; absence ≠ 0 ni tiret ambigu ; huit états (`docs/05-design/UI_STATES.md`) plus `ready`, `auth-required`, `closed` de `ModuleState` (`moduleState.ts:18-30`) ;
- couleurs par tokens seulement (`no-raw-colors.test.ts`) ; `tokens.css` régénéré et commité ;
- une dominante par fichier de page (`one-dominant-per-page.test.ts`) et un seul porteur de `data-rank` rendu (`Card`) ;
- aucun compte à rebours, aucune horloge client, aucune fraîcheur déduite de `Date.now()` ;
- jamais `pnpm e2e` sur ce poste tant que 8000/4173 sont occupés ; jamais `playwright install` ; `pnpm install --frozen-lockfile` et `uv sync --locked` seulement ;
- aucune fusion par Claude ; PR brouillon, revue adverse, CI verte, validation humaine.

## 1. Lots, ordre et dépendances

| # | Lot | Branche | Dépend de | Contenu |
|---|---|---|---|---|
| L1 | Fenêtre Marchés affamée par le temps réel (backend) | `lot/l1-fenetre-marches-20260903` — PR #32 | — | D0 partiel : fenêtre `max_observations` / `invalid_payload` (`markets.py:161, 275-297`) |
| S0 | Famine de la file d'attention + rail de preuves Opportunités | `lot/srv-s0-attention-fenetre-20260903` | — | `handlers.py:612-617` ; bloqueur `entitlements_sufficient:UNEVALUABLE` ×161 |
| S1 | Breadth : avancées / déclins / inchangés publiés | `lot/srv-s1-breadth-comptes-20260903` | — | `markets.py:446-451, 558-570`, `schemas.py:207-225`, OpenAPI, `pnpm gen:api` |
| S5 | Budget de fraîcheur publié (`freshness_policy` + position servie) | `lot/srv-s5-budget-fraicheur-20260903` | S1 | `freshness.py:95-104, 107-187` ; capacités = C par décision (`schemas.py:536-540`) |
| S2 | Comparaison base 100 servie (`market.rebased_series`) | `lot/srv-s2-series-rebasees-20260903` | S5 | `registry:89-134`, alignement serveur (`registry:105`), kind SSE |
| S3 | Séries glissantes vol / ATR / force relative | `lot/srv-s3-series-glissantes-20260903` | — | `analysis.py:460-594` → `indicators.series` |
| S4 | Signal SSE `risk_matrix` + kinds manquants | `lot/srv-s4-sse-risk-matrix-20260903` | — | `events.py:41-47`, `hooks.ts:32-39` ; commits 55fb4b0, ec5e6c0 à relire |
| S6 | Overlays/oscillateurs au registre (EMA, SMA, Bollinger, RSI, MACD) | `lot/srv-s6-overlays-registre-20260903` | — | entrées registre + `vertex_core` + bloc `overlays`/`oscillators` |
| **C0** | **Canon v2** (ce lot) | `lot/w2-c0-canon-v2-20260903` | étude | ADR-017, documents du canon, tokens, tests, ce plan |
| L0 | Socle : `widgets.css`, primitives, direct | `lot/w2-l0-socle-20260903` | C0 | §3 |
| P1 | Aujourd'hui + Marchés | `lot/w2-today-markets-20260903` | L0 | §4.1, §4.2 |
| P2 | Opportunités + Analyse | `lot/w2-opportunities-analysis-20260903` | L0 | §4.3, §4.4 |
| P3 | Options + Simulateur | `lot/w2-options-simulator-20260903` | L0 | §4.5, §4.6 |
| P4 | Portefeuille + Risques | `lot/w2-portfolio-risks-20260903` | L0 | §4.7, §4.9 |
| P5 | Graphiques | `lot/w2-charts-20260903` | L0 (+ S2, S6 pour les emplacements B) | §4.8 |
| P6 | Catalyseurs + Calendrier + Sources & Rapports | **fait** — `claude/syncfusion-flutter-widgets-btl182` (`96aff7d` Calendrier, `5889f37` Catalyseurs + Sources) | L0 | §4.10–4.12 — conteneur `Widget` posé sur les 24 modules servis des trois planches ; dominantes laissées sur `Card` + `DataStateBoundary` ; formes v2 : `DayBars` sur densité et exposition du Calendrier |
| B | Bilan : tableau des lots, portes, écarts, ordre de fusion, passation | — | tout | — |

Ordre de fusion recommandé (humain) : #32 → S0 → S4 → S3 → S1 → S5 → S2 → S6 → C0 → L0 → P1…P6. Les lots P sont indépendants entre eux (base L0). Chaque lot part de `origin/main` à jour (`git fetch && git worktree add ../vertex-<lot> -b lot/<slug> origin/main`).

## 2. Formes v2 par famille de donnée

| Famille de donnée servie | Forme v2 | Primitive (L0) | Donnée exigée | Refus (état nommé) |
|---|---|---|---|---|
| parts en % (`*_pct`, chaînes) | anneau à chiffre central ; bande empilée | `RingShares`, `SharesBand` | parts servies ; chiffre central servi verbatim ; ≤ 4 teintes | part `null` → « non publié », absente de la forme |
| quatre parts ou valeurs bornées servies | quatuor d'anneaux | `RingShares` ×4 | unité, période, `as_of` par anneau | anneau manquant → cadre qui dit l'absence |
| valeur bornée + seuils + position servie | jauge en arc graduée ; jauge linéaire/bullet/bande | `ArcGauge`, `LinearGauge` | bornes, seuils, position en % servie, méthode/version, `as_of` | `INVALID`/`null` → « non calculable » + raison servie |
| série servie (≥ 2 points) | sparkline en aire à dégradé | `SparkFigure` | points en chaînes, période nommée | < 2 points → « série insuffisante (n barre) » |
| 2–3 séries servies alignées par le serveur | aires superposées translucides, trait distinct par série | `MultiSeriesArea` (ECharts) | alignement serveur (S2), légende | alignement client → refus |
| comptes entiers | barres sur rail (dénombrement), barres par jour | `CensusBars`, `DayBars` | comptes servis ; nom de bande servi s'il y a bande | `null` → aucune barre, « non publié » |
| bandes nommées | matrice de bandes | `CellGrid` | nom de bande servi + texte, légende servie | bande absente → `data-band="unknown"` visible |
| étapes / portes / statuts | liste d'étapes à chips | `StepList`, `StatusChip` | statut servi + texte | statut vide → « statut non publié » |
| événements horodatés | liste groupée par jour | `ActivityFeed` | ISO servis, montants en chaînes signées | montant `null` → « montant non publié » ; jamais « aujourd'hui » sans `as_of` |
| variation signée servie | pastille delta | `KpiDelta` | chaîne servie avec son signe ; fonction de signe par champ | `null` → « variation non publiée » |
| état du lien de signalement | badge direct | `LiveBadge` | table de décision (§3.5) | jamais « en direct » sur `SYNTHETIC` |

Teinte sémantique secondaire par page : une famille (`macro`, `option`, `warning` ; jamais `positive` ni `negative`, réservés au signe financier servi) déclarée dans le catalogue de la page (`*Modules.ts`), posée par `data-page-accent` sur la racine de la page, consommée par `--vx-page-accent*`. Propositions [I], à confirmer au lot de chaque page : Aujourd'hui `macro` (contexte, sources) ; Marchés `macro` (breadth, couverture) ; Opportunités `warning` (portes `DEGRADE`, exclusions) ; Analyse `macro` (force relative, benchmark) ; Options `option` ; Simulateur `option` ; Portefeuille `macro` (concentration, devise) ; Graphiques `macro` (comparaison) ; Risques `macro` (bandes de corrélation, précédent `CorrelationMatrix`) ; Catalyseurs `warning` (importance estimée, révisions) ; Calendrier `macro` ; Sources & Rapports `warning` (retard, fraîcheur). Vert/rouge restent partout réservés au signe financier servi. Les trois propositions `warning` (Opportunités, Catalyseurs, Sources & Rapports) sont suspendues à la réserve consignée dans ADR-017 (Coûts et contraintes) : `warning` `#f0c36a` ≈ `signal-bright` `#f2c76b` ; le lot L0 mesure la distinguabilité ou retire `warning` de `pageAccent` avant qu'une page ne le déclare.

## 3. Socle L0 — ce que le canon v2 impose

### 3.1 Tokens consommés

`--vx-page-accent(-soft, -gradient-start, -gradient-end)`, `--vx-<famille>-gradient-start/-end`, `--vx-motion-600` (surbrillance unique ; sous reduced-motion, `data-updated` maintenu ~1 s en contour statique), `--vx-titanium-soft` (rail), `--vx-grid-line`, `--vx-font-size-meta` (13 px : aucune méta sous 13 px dans la nouvelle couche), `--vx-radius-pill` (pastilles, précédent `.vx-iw-delta` `global.css:6587`).

### 3.2 Primitives (`apps/web/src/components/widgets/`)

- `Widget` : compose `Card` (seul porteur de `data-rank`) ; `data-module`, `data-size`, `data-state` (onze valeurs de `ModuleState`, `closed` et `auth-required` compris), méta (`FreshnessBadge`, `<time dateTime>` ISO UTC, texte dans le fuseau partagé `Europe/Zurich` ou le fuseau servi), conclusion servie seulement, `data-updated` ; ne redéclare ni fond, ni bordure, ni rayon : la surface vient de `.vx-card` + `.vx-board`.
- `KpiDelta` : chaîne servie verbatim ; fonction de signe sur chaîne, règle de zéro par champ (`signGroupOf` inchangée : elle prend un ticker) ; `radius-pill` ; `tabular-nums`.
- `SparkFigure` : `Sparkline` + `<figure>` + `<details><table>` ; aire à dégradé `<famille>-gradient-start → -end` (unique `<linearGradient>` admis, sous la série servie) ; base pointillée = première clôture servie ; `windowLabel` obligatoire.
- `RingShares` : anneau SVG à chiffre central servi ; parts `*_pct` en chaînes ; géométrie d'arc sur `pct` ; légende chiffrée ; table équivalente ; ≤ 4 teintes ; jamais « autres » calculé ; la somme n'est ni vérifiée ni étirée (reliquat non dessiné, documenté).
- `ArcGauge` : arc gradué, marqueur à la position servie (`pct` chaîne), segments par bornes servies, `role="meter"` + `aria-valuetext` ; branche `INVALID`.
- `LinearGauge` : généralise `BreadthPanel` (`width: ${pct}%`, aucune arithmétique).
- `SharesBand` : bande empilée ; accepte des parts `*_pct` servies ou, par décision écrite au lot, des ratios servis via un identifiant renommé (précédent `barWidthPct`, `ConcentrationPanel.tsx:33-39`) — jamais `entry.weight * 100` ; teintes `silver/titanium/macro` (+ `option` dans le domaine options seulement) + motif.
- `DayBars` : barres sur rail ; `value: string | null` ; `data-band` verbatim, mapping bande→teinte déclaré par widget, vert/rouge seulement si la bande est un signe ; aucune hauteur 0 pour une absence (`geometryNumber` rend 0 sur non-fini : filtrer `null` AVANT la géométrie).
- `CellGrid` : table sémantique, `data-band` verbatim, `unknown` visible (durcit `CorrelationMatrix.tsx:60` qui remplace une bande absente par `'weak'`).
- `StepList`, `StatusChip` (texte obligatoire ; `live` sans teinte : `text-secondary` + glyphe ; `warning` retard/périmé/silence ; `negative` erreur/session), `PeriodTabs` (options indisponibles désactivées avec motif, jamais masquées ; bornées par les barres servies, `bars.count`), `ActivityFeed` (codes de transaction verbatim, aucun vocabulaire d'ordre : porte `no-raw-colors`), `InstrumentTile` (déplacement de `InstrumentWidget`), `ProvenanceLine`, `MultiSeriesArea` (≤ 3 séries, trait distinct par série, `animation:false`), `LiveBadge` (§3.5).

### 3.3 CSS

`apps/web/src/styles/widgets.css`, importé par une ligne `main.tsx:9` après `global.css` ; préfixe `vx-w2-` ; uniquement `var(--vx-*)` ; pas de propriété `order:` (vocabulaire de la porte) ; `tabular-nums` sur delta, barres, cellules, montants, provenance ; une seule constante de mise en page `--vx-w2-row` (commentée, mesurée en e2e) ; gouttières `--vx-space-12` ou `--vx-space-16` sur les deux axes, jamais 20 ; Aujourd'hui/Marchés migrent vers `.vx-board` (pas de `.vx-w2-board`) ; `[data-page-accent]` posé par la page.

### 3.4 Icônes

`lucide-react` n'est pas installé (`apps/web/package.json:40-48`) [F]. Décision explicite à écrire dans L0 : (a) installer épinglé avec `manifests/dependencies.yaml`, `licenses.yaml`, NOTICE ISC ; ou (b) action textuelle « Détail › » (précédent A8) et glyphes Unicode. Chevron dans un contrôle : 18 px, cible 32×32.

### 3.5 Direct

SSE signal-only inchangé ; `api/events.ts` écoute `ping`, état `silent` après 45 s, repli en sondage 30 s (`invalidateQueries(['snapshot'])`, requêtes actives seulement) ; `useSnapshotMeta(queryKey)` sans `Date.now()` ni extrapolation ; `liveResource` par `PageDef` ; `LiveBadge` : `SESSION REQUISE` / `HORS LIGNE • dernier instantané <as_of>` / `PÉRIMÉ` / `DIFFÉRÉ • publié il y a N s` / `SANS SIGNAL • publié il y a N s` / `SIGNAL ACTIF • publié il y a N s` / `RECONNEXION` / `SONDAGE` — « publié », jamais « coté » ni « en direct » ; population `SYNTHETIC`/`DEMO` impose le chip de population. Point 5 du shell : fraîcheur + mode sourcés, cloche absente (article 17). Serveur : `("risk_matrix","global")` dans `WATCHED_SNAPSHOTS` (lot S4).

### 3.6 Tests rouges d'abord

`tokens-css.test.ts` (fait en C0), un `*.test.tsx` par primitive (onze états, « non publié », aucun `%` écrit, aucun `<linearGradient>` hors aire de série), `catalog.test.ts` (chaque entrée de chaque `*Modules.ts` déclare `size` ∈ {S,M,L,XL}, `variant` ∈ vocabulaire fermé, et la page déclare un `accent` ∈ `pageAccent` — porte dure avant tout consommateur de `--vx-page-accent*` : sans déclaration, la variable est invalide et un `fill` SVG tombe au noir, ADR-017), `no-fabricated-values.test.ts` étendu à `src/components/widgets`, `events.test.ts`, `hooks.test.tsx`, `shell.test.tsx`, `LiveBadge.test.tsx`, e2e `widget-grid.spec.ts`, `live-badge.spec.ts` (en CI seulement).

## 4. Plan par page

Tailles : S 1×1, M 2×1, L 2×2, XL 4×2 (5×2 à ≥ 1600) ; 1024 = smoke sans défilement horizontal ; mobile = C. `size` est un span de composition ; la variante visuelle reste `dominant/support/rail`. Les six modules « (nouveau) » exigent une décision utilisateur et un critère d'acceptation avant d'être composés.

### 4.1 Aujourd'hui — TL/01 — dominante : file d'attention — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| global-market | `ArcGauge` breadth (`value_pct`, bornes 0–100, seuil `coverage_threshold_pct`) + `LinearGauge` couverture + conclusion servie | A | `markets/overview.breadth.*`, `conclusion` ; `INVALID` aujourd'hui → « non calculable » + `reason` [F] |
| next-catalyst | KPI compact (heure de place + fuseau, chip `importance.code`) ; compte à rebours = C | A | `calendar.agenda[0]` (`calendarModules.ts:65` « aucun compte à rebours ») |
| source-health | `CensusBars` sur rail des `tested_status` + KPI âge worker ; jauge âge/TTL des capacités = C par décision | A / C | `system/capabilities.health.*` ; `schemas.py:536-540` |
| focus | `InstrumentTile` ×4 (`SparkFigure` à dégradé) | A | `focusView.ts:19-54` ; vide tant que 0 couvert |
| **attention** | `ActivityFeed` groupé sur `provenance.last_received_at` (pas `first_published_at`, nul sur les 15 items vivants) ; KPI A de `coverage` (`polarity_conflicts`, `truncated_ranked`, `published_items/max_items`) | A ; B pour `priority_class`, `conflicts[]`, `rejected[].failed_gates` (S0) | `today/attention.items[]`, `coverage` |
| opportunities | KPI ×3 (`qualified_count`, `excluded_count`, `universe_size`) + `CensusBars(status_counts)` ; anneau = C tant qu'aucune part `%` n'est servie | A | `opportunities.coverage.*` |
| sectors | `SectorGrid` + `KpiDelta` par puce | A | `sectors[].tickers[].return_1d_pct` |
| manual-portfolio | KPI par devise + `KpiDelta(total_unrealized)` (signe par fonction de champ) + chip `markPopulation` | A | `portfolio.valuation.positions_by_currency[]` |
| calendar | `ActivityFeed` 5 lignes | A | `calendar.agenda[0..4]` |
| volatility, regime, active-risks | état honnête | C (→ B vol d'univers : entrée registre) | `todayView.ts:32-59, 90-100` |

### 4.2 Marchés — TL/02 — dominante : treemap — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| breadth | `ArcGauge` breadth + `LinearGauge` couverture (migration `BreadthPanel`) ; `DayBars` avancées/déclins/inchangés | A ; B n°1 (S1) | `breadth.*` ; `down_count`/`flat_count` à publier |
| market-health | KPI `covered/expected` + `ArcGauge(coverage_pct)` + `CensusBars(received, covered, discarded, rejected)` | A | `coverage.*`, `data_state`, `age_seconds` |
| focus | `InstrumentTile` ×4 | A | — |
| **market-map** | treemap ECharts + table triable + conclusion + `ProvenanceLine` ; colonnes `previous_close`, `previous_trading_day`, `quality` ajoutées | A | `sectors[].tickers[].*` (`schemas.py:181-192`) |
| sectors | `SectorGrid` + `RingShares(weight_in_sector_pct)` par tuile (parts `%` servies) ou `SharesBand` | A | `weight_in_sector_pct` (`schemas.py:189`) |
| discards | liste + `StatusChip(reason)` | A | `coverage.discarded_tickers[]`, `rejected_records[]` |
| return-distribution, breadth-history | `DayBars` par classe ; `SparkFigure` de la breadth | B (décision utilisateur) | nouvelles entrées registre / bloc `breadth_history` |
| sessions, indices, rates-curve, fx, vol-structure, correlation, volatility | état honnête | C | `marketsModules.ts:20-119` (`rates-curve`, `correlation` = `SERVER_CONTRACT_MISSING`) |

D0 vivant : 495/500 `invalid_payload`, fenêtre saturée (`markets.py:161`) → lot L1 (#32).

### 4.3 Opportunités — TL/03 — dominante : classement — accent proposé `warning` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| active-ideas | KPI ×3 + note `observationsConsidered` | A | `coverage.{qualified_count,excluded_count,universe_size}` |
| global-bias | `CensusBars` directions | A | `advice.direction` (dénombrement) |
| **ranking** | table qualifiés/exclus, `StatusChip(status)`, `StepList` compact des 10 gates en `<details>` ; sparkline par ligne = B (`mini_series`) | A | `qualified[]/excluded[].{advice,gates[10],bars_status}` |
| gates-census (nouveau) | `CellGrid` gate × statut (comptes) | A (décision utilisateur) | `excluded[].gates[].{gate_id,status}` |
| missing-evidence (nouveau) | `CensusBars` | A (décision utilisateur) | `missing_evidence`, `required_evidence{}` |
| opportunity-health, exclusions | `CensusBars` | A | `coverage.status_counts`, `exclusion_reasons{}` |
| profile | `StepList` applied / not_applied | A | `profile_ref.*` |
| catalysts-provenance | faits + `StatusChip(calendar_ref.status)` | A | `calendar_ref.*` |
| quality | liste | A | `limitations` |
| mean-score, expected-return, scatter, factor-contribution | état honnête | C | `ordering.method=lexicographic` ; calibration NOT_IMPLEMENTED |
| recent-activity | état honnête | C→B | version précédente à publier |

Bloqueur primaire vivant : `entitlements_sufficient:UNEVALUABLE` ×161 (S0).

### 4.4 Analyse — TL/04 — dominante : chandeliers — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| instrument-header | `InstrumentTile` M | A | `bars.{last_close,currency,age_seconds}` |
| identity-facts | KPI compacts ×8 | A | `bars.{currency,quality,adjustment_basis}`, `population` |
| **chart** | `CandleChart` + volume + `PeriodTabs` bornées par `bars.count` (légende lue sur `bars.count`, pas « 60 barres serveur » fixe, `CandleChart.tsx:160`) + `OhlcvTable` ; overlays/niveaux = B (S6) | A | `bars.bars[]`, `bars.count` (27 servies pour AEHL [F]) |
| indicators | KPI ×3 + chips méthode ; séries glissantes = B (S3) | A | `indicators.{atr,realized_volatility,relative_strength}` |
| verdict | `AdviceCard` + `StepList` des 10 gates avec `observed_values`/`thresholds` (publiés, non lus par `analysisView.ts:153-175`) | A | `advice.gates[]` |
| financials | table + `StatusChip(identity_state)` | A | `sources/sec/{i}/fundamentals` |
| scenarios | `CellGrid` spot × temps, chip THÉORIQUE | A | `scenarios.grid` ; `ABSENT no_option_chain_snapshot` aujourd'hui |
| upcoming-catalysts, key-risks, peers, evidence | `ActivityFeed`, liste, puces + `KpiDelta`, `EvidenceRail` | A | — |
| oscillators, levels, contradictions | état honnête | B | `analysisModules.ts:56-65, 158-177` |
| analyst-revisions, regime, fundamental-quality, valuation, model-confidence | état honnête | C | `NO_SOURCE` ; `no-uncalibrated-probability` |

Sélecteur : seconde source = tickers de `opportunities.{qualified,excluded}` avec `bars_status=OK` [I, décision produit].

### 4.5 Options — TL/05 — dominante : chaîne — accent `option`

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| underlying, spot, dividend, rate | `InstrumentTile`, KPI + `<time observed_at>`, KPI + chips | A | `spot.*`, `assumptions.*` |
| identity-strip | faits + chips + `CensusBars(row_budget.published, total)` | A | `OptionsModules.tsx:125-191` |
| vol-structure | small multiples `IvSmile` compact | A | par groupe |
| underlying-series | `SparkFigure` 60/20 | A | `analysis/{u}.bars` |
| iv-smile | `IvSmile` + greeks × strike en small multiples + `DayBars` volume / open_interest par strike (`String(contract.volume)`, aucune arithmétique) + chip `open_interest_status` | A | `options.py:441-462, 558-570` |
| **chain** | table Calls/Strike/Puts + OI/volume ; spread = C (`bid`/`ask` dans le vocabulaire de la porte) | A | `expirations[].contracts[]` |
| expected-move, iv-reference | état honnête | B | entrée registre `options.expected_move` |
| iv-rank, strategy-builder, payoff-profile, strategy-metrics | état honnête | C | `optionsModules.ts:70-79, 117-135` |

Réel : chaîne vide (lookback 72 h) [F].

### 4.6 Simulateur — TL/06 — dominante conditionnelle : payoff — accent `option`

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| manual-entry, base-parameters | formulaires ; unique bouton rempli « Calculer » | A | `SimComposer.tsx` |
| **payoff** | ECharts P&L/spot + markLine 0 + breakevens + chips `max_gain/max_loss` + table | A | `payoff_points`, `breakevens`, `max_*_on_grid` |
| kpi-served | KPI ×3 + `StatusChip(defined_risk.reason_code)` | A | `SimResult.tsx:110-154` |
| scenarios | `CellGrid` spot × temps (signe lu sur la chaîne) | A | grilles de scénario |
| catalysts, key-assumptions, sources, method | `ActivityFeed` filtré, faits, `StepList` | A | — |
| stress-tests | état honnête (catalogue `NO_SOURCE` à aligner sur B) | B | `analysis.py:950` `iv_scenarios [[iv]]` |
| sensitivity, portfolio-impact | état honnête | B | `simulation.py` + `options.greeks` |
| kpi-probabilistic, monte-carlo | état honnête | C | calibration NOT_IMPLEMENTED |

### 4.7 Portefeuille — TL/07 — dominante : concentration — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| value | KPI par devise + `KpiDelta(total_unrealized)` + chip `markPopulation` + `ProvenanceLine` | A | `PortfolioSummary.tsx:44-162` |
| total-performance | KPI twr/xirr ×4 | A | `performance.metrics` (`INSUFFICIENT_DATA` aujourd'hui [F]) |
| cash | KPI « espèces au dernier jour valorisé <trading_day> » (dernier point servi ; libellé obligatoire) | B (décision) | `series.points[].cash` (vide aujourd'hui) |
| performance | ECharts brut/net + drawdown + `PeriodTabs` de vues : enveloppe `gross_value` servie et composantes `cash`/`position_value` NON empilées ; ligne `fees_cumulative` ; marqueurs `external_cashflows[]` ; `DayBars(twr.periods[])` ; heatmap `months[].return_pct` | A | `performance.py:507-523, 583-591, 622-634, 637-702, 833-860` |
| **concentration** | `RingShares`/`SharesBand` : `concentration.weights` sont des ratios (`_decimal_text`), pas des `%` → soit `weight_pct` publié (B), soit géométrie sur ratio renommé (précédent `barWidthPct`) [I décision écrite au lot] + Herfindahl verbatim + table | A/B | `ConcentrationPanel.tsx:73-130` |
| positions | table + barres signées par lot (géométrie sur `unrealized_pnl` renommé) | A | `unrealized.lots[]`, `excluded_lots[]` |
| dividends, ledger | `ActivityFeed` par `effective_at` / groupé par jour, codes verbatim | A | `transactions` |
| currency-exposure | KPI par devise (montants ≠ parts : pas d'anneau) | A | `positions_by_currency[].concentration.total_value` |
| sector-exposure | état honnête | B bloqué | secteur unique `NON_CLASSE` |
| day-performance, benchmark, allocation, country-exposure, attribution, concentration-alerts | état honnête | C | `portfolioModules.ts` |

D0 : contradiction v31913 `mark_population: REAL` (valorisation) vs `SYNTHETIC_MARKS_REAL_LEDGER` (performance) — à corriger au worker, jamais masquée.

### 4.8 Graphiques — TL/08 — dominante : main-chart — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| **main-chart** | `CandleChart` + `PeriodTabs` + volume + OHLCV | A | `analysis.bars` |
| served-indicators | KPI ×3 | A | `indicators` |
| comparison | `MultiSeriesArea` (≤ 3 séries, trait distinct, alignement serveur) | B n°2 (S2) | `market.rebased_series` |
| overlays, rsi, macd | état honnête | B (S6) | — |
| synchronized | état honnête | B | contrat d'alignement |
| selected-object, linked-alerts, layouts, saved-studies | état honnête | C | `DECISION_PENDING` |

Pas de grille aujourd'hui (`ChartsPage.tsx:76-179`) : lot à part (P5).

### 4.9 Risques — TL/09 — dominante : corrélations — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. | Donnée servie / chemin |
|---|---|---|---|
| **correlations** | `CellGrid(matrix, matrix_bands)` + légende 5 bandes + seuils servis (`strong_threshold`, `moderate_threshold`) + conclusion + chips extrêmes ; `overflow-x:auto` interne mesuré | A | `risk/matrix.*` ; bande absente → `unknown` (durcit `CorrelationMatrix.tsx:60`) |
| extremes, coverage, alignment, discards | KPI + chip bande ; KPI + `CensusBars` ; `CensusBars` ; liste | A | `extremes.*`, `coverage.*`, `trading_days_lost_to_alignment{}` |
| max-drawdown | KPI ×2 + `SparkFigure(drawdown.points[])` (prop renommée) | A | `performance.metrics.drawdown_*` (vide aujourd'hui) |
| concentration | `RingShares`/`SharesBand` + Herfindahl (voir §4.7) | A/B | `portfolio.concentration` |
| volatility, rolling-correlation | état honnête | B | `market.realized_volatility` sur `gross_value` ; `risk.correlation` par fenêtre |
| turnover, risk-register | état honnête | B | `SERVER_CONTRACT_MISSING` |
| risk-score, var-cvar, benchmark-relative, liquidity, stress-loss, factor-exposures, risk-budget, radar, alert-log | état honnête | C | `NO_SOURCE` ; radar sans dimension multiple servie = interdit (ADR-017) |

SSE `risk_matrix` : lot S4.

### 4.10 Catalyseurs — TL/10 — dominante : timeline — accent proposé `warning` [I]

| Widget | Forme v2 | Cl. |
|---|---|---|
| upcoming-count | KPI (dénombrement `event_context × theses`) | A |
| **timeline** | `ActivityFeed` groupé par jour (heure de place + fuseau), chips statut/importance/SYNTHÉTIQUE | A |
| revisions, category-split | `CensusBars` | A |
| portfolio-exposure | `DayBars` événements × positions (dénombrement) | A [I] |
| sources-freshness | `ProvenanceLine` + `FreshnessBadge` | A |
| window, filters, conflicts, orphan-theses | `PeriodTabs`/selects, listes | A |
| review | `StepList(due[])` + table thèses + formulaire | A |
| event-alerts | état honnête | B (`SERVER_CONTRACT_MISSING`, `catalystsModules.ts:119-124`) |
| mean-impact, confidence, surprises, consensus, surprise-history | état honnête | C |

Réel : agenda vide, `due 0` [F] (D0 : préfixe synthétique `calendar.py:178`).

### 4.11 Calendrier — TL/11 — dominante : agenda — accent proposé `macro` [I]

| Widget | Forme v2 | Cl. |
|---|---|---|
| view-controls, timezone | `PeriodTabs` jour/semaine + fuseau servi | A |
| **agenda** | `ActivityFeed` groupé jour/semaine | A |
| density, daily-exposure | `DayBars` par jour (dénombrement, vue) ; `CellGrid` heures × jours | A (vue) / B (compteurs serveur) |
| next-event | KPI heure de place ; compte à rebours = C | A |
| counters | `CensusBars` — se ferme sur l'ÉTAT DE PAGE (`window.statuses` sert des zéros en `empty`) | A |
| importance-rule, provenance, revisions, conflicts | `StepList`, faits, listes | A |
| reminders, changes-since-visit | état honnête | C (`SERVER_CONTRACT_MISSING`) |

### 4.12 Sources & Rapports — TL/12 — dominante : registre — accent proposé `warning` [I]

| Widget | Forme v2 | Cl. |
|---|---|---|
| **registry** | matrice 6 colonnes + chips | A |
| status-census | `CensusBars(tested_status)` sur rail | A |
| freshness | `ArcGauge` âge/budget quand `age_pct_of_budget` est servi (S5) ; capacités = C par décision ; en attendant KPI âge + chip | B n°5 / C |
| last-sync, versions, components-health | KPI, `StepList` pipeline, versions (incl. état du flux SSE, `sourcesModules.ts:94`) | A |
| exports | routes servies (`GET /portfolio/export`, `GET /performance/{id}/export`) | A |
| unknown-probes | liste | A |
| global-health, error-rate, field-coverage, field-quality, incidents, lineage, audit-log, reports, backups | état honnête | C |

## 5. Lots serveur et données

S1 comptes breadth (`markets.py:446-451` → `breadth_block`, schéma, OpenAPI byte-identique, `pnpm gen:api`) ; S2 séries rebasées (alignement serveur, kind SSE dans `WATCHED_SNAPSHOT_KINDS` et `SSE_RESOURCE_PREFIXES`) ; S3 séries glissantes (`indicators.series`, sans champ `consumers` : il n'existe pas au registre) ; S4 `risk_matrix` SSE ; S5 `freshness_policy.{budget_seconds,kind}` + position servie `age_pct_of_budget`, budget « séance fermée » (`ttl_closed_seconds`), capacités exclues ; S6 overlays/oscillateurs au registre ; S0 famine attention + rail de preuves. D0 : `invalid_payload` 495/500 et `max_observations` (L1 #32), `MAX_QUOTE_OBSERVATIONS=10000` (`performance.py:141`), préfixe calendrier réel, `evidence_cluster_ids=[]`, contradiction REAL/SYNTHETIC des marques v31913.

## 6. Portes par lot

`pnpm tokens:css && git diff --exit-code -- src/design/tokens.css` · `pnpm lint` · `pnpm typecheck` · `pnpm test` (portes de design incluses : `no-raw-colors`, `no-authoritative-calculation`, `no-fabricated-values`, `one-dominant-per-page`, `no-uncalibrated-probability`, `tokens-css`, `canon-v2-docs`) · `pnpm exec vite build --manifest` · aperçu sur port dédié (4174+) relayant l'API réelle · captures 1280/1440/1600 avant/après (relecture locale seulement, jamais en PR) · `python3 .claude/skills/vertex-titanium-ledger/scripts/audit_titanium_ledger.py --repo-root <worktree> --strict-target` (empreinte canonique inchangée) · `bash tools/run_checks.sh` sans `env.live` · `NOW.md` mis à jour · revue adverse · PR brouillon · CI 7/7 (e2e SYNTHETIC en CI seulement).

## 7. Risques et non vérifié

1. Données réelles majoritairement vides : les widgets A afficheront d'abord des états honnêtes ; les captures réelles ne prouvent pas le rendu « rempli ».
2. `--vx-w2-row` et les hauteurs de rangée ne sont pas mesurées hors navigateur (vitest `css:false`) ; seule l'e2e densité le prouvera.
3. `PeriodTabs` en découpage local des barres servies = décision à consigner (fenêtrage serveur vs filtre explicite).
4. Aucun quatuor de parts servies en classe A n'est identifié aujourd'hui ; candidats après S1/S5 (breadth, couverture, avancées/déclins, fraîcheur).
5. `RingShares` sur `concentration.weights` dépend d'une décision (ratio renommé vs `weight_pct` servi).
6. Les propositions de teinte secondaire par page (§2) sont des inférences ; chaque lot P les confirme dans son catalogue.
7. `gh` absent dans WSL ; PR brouillons depuis Windows ou l'interface web.
8. Cadence SSE variable : aucun e2e ne dépend d'une republication spontanée.
9. Tensions du canon non tranchées ici : kicker 10 px (`global.css:6791-6795`) vs plancher 13 px ; « 3–5 modules » (`frontend.md:28`, `widget-catalog.yaml`) vs 11–19 composés (précédent A3–A8 assumé) ; `DASHBOARD_COMPOSITION.md:78` « gradient argent→violet » vs capture ; State Plate « rectangulaire » vs badges pill.
