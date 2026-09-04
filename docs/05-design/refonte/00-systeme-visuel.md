# ÉTAT DU SYSTÈME VISUEL VERTEX 1.0 BETA — audit exhaustif au 2026-09-04

---

## 1. TABLEAU DES JETONS ET CONTRASTES CALCULÉS (WCAG 2.2, luminance relative)

Source unique : `apps/web/src/design/tokens.ts:16-79` → généré vers `apps/web/src/design/tokens.css:5-53` par `apps/web/src/design/generate-css.ts:53-96`.

### 1.1 Surfaces (7 valeurs) — écarts de luminance mesurés

| Jeton | Valeur | ligne | L relative | ratio vs surface suivante |
|---|---|---|---|---|
| `black` | `#030302` | tokens.ts:17 | 0,00089 | 1,029 vs `app` |
| `app` | `#080806` | tokens.ts:18 | 0,00238 | 1,030 vs `surface-0` |
| `surface-0` | `#0d0d0b` | tokens.ts:19 | 0,00398 | 1,047 vs `surface-1` |
| `surface-1` | `#141310` | tokens.ts:20 | 0,00652 | 1,058 vs `surface-2` |
| `surface-2` | `#1b1915` | tokens.ts:21 | 0,00982 | 1,092 vs `surface-3` |
| `surface-3` | `#242119` | tokens.ts:22 | 0,01533 | 1,109 vs `hover` |
| `hover` | `#2d2920` | tokens.ts:23 | 0,02248 | — |

**Verdict** : l'échelle est logarithmiquement irrégulière. `black→app` et `app→surface-0` valent 1,03 : deux surfaces qui ne se distinguent pas. `surface-2→surface-3` vaut 1,09. Pour une composition bento à « surfaces franchement différentes », les trois premiers crans sont inutilisables comme séparateurs.

### 1.2 Texte plein sur surface — ratio calculé, verdict AA (seuil 4,5:1 texte normal)

| Jeton texte | app | surface-0 | surface-1 | surface-2 | surface-3 | hover | AA |
|---|---|---|---|---|---|---|---|
| `text` `#f6f2e8` (tokens.ts:28) | 17,93 | 17,40 | 16,62 | 15,70 | 14,38 | 12,96 | **AA partout** |
| `text-secondary` `#b8b0a0` (:29) | 9,31 | 9,04 | 8,63 | 8,15 | 7,47 | 6,73 | **AA partout** |
| `text-muted` `#948c7d` (:30) | 6,02 | 5,84 | 5,58 | 5,27 | 4,83 | **4,35** | **ÉCHEC sur `hover`** |
| `silver` `#d8d3c7` (:31) | 13,42 | 13,03 | 12,44 | 11,75 | 10,76 | 9,70 | AA |
| `titanium` `#aaa497` (:32) | 8,08 | 7,84 | 7,49 | 7,08 | 6,48 | 5,84 | AA |
| `signal` `#d7a94a` (:39) | 9,22 | 8,95 | 8,55 | 8,08 | 7,40 | 6,67 | AA |
| `signal-bright` `#f2c76b` (:40) | 12,56 | 12,19 | 11,64 | 11,00 | 10,07 | 9,08 | AA |
| **`signal-deep` `#765319` (:41)** | **2,88** | **2,80** | **2,67** | **2,53** | **2,31** | **2,08** | **ÉCHEC TOTAL — jamais utilisable comme texte** |
| `positive` `#50c992` (:49) | 9,65 | 9,37 | 8,94 | 8,45 | 7,74 | 6,97 | AA |
| `negative` `#ef6f6c` (:51) | 6,83 | 6,63 | 6,33 | 5,98 | 5,48 | 4,94 | AA |
| `warning` `#f0c36a` (:53) | 12,14 | 11,78 | 11,25 | 10,63 | 9,73 | 8,77 | AA |
| `option` `#a88ae8` (:55) | 7,13 | 6,92 | 6,60 | 6,24 | 5,71 | 5,15 | AA |
| `macro` `#6bc5bc` (:57) | 9,87 | 9,58 | 9,15 | 8,64 | 7,91 | 7,13 | AA |

### 1.3 Non-texte : bordures, grille, filigrane, bandes (seuil WCAG 1.4.11 = 3:1)

Composés en alpha sur leur fond, puis comparés à ce fond.

| Jeton | app | surface-1 | surface-2 | hover | Verdict 3:1 |
|---|---|---|---|---|---|
| `border-soft` (tokens.ts:24) | 1,12 | 1,16 | 1,18 | 1,20 | **ÉCHEC** |
| `border` (:25) | 1,26 | 1,32 | 1,35 | 1,38 | **ÉCHEC** |
| `border-strong` (:26) | 1,64 | 1,74 | 1,77 | 1,79 | **ÉCHEC** |
| `grid-line` (:27) | 1,07 | 1,09 | 1,10 | 1,12 | **ÉCHEC** (délibéré, décor) |
| `titanium-soft` (:33) | 1,18 | 1,23 | 1,25 | 1,28 | **ÉCHEC** |
| `titanium-ghost` (:38) | 1,06 | 1,09 | 1,10 | 1,11 | **ÉCHEC** (délibéré, filigrane) |
| `signal-soft` (:42) | 1,24 | 1,30 | 1,32 | 1,34 | **ÉCHEC** |
| `signal-faint` (:43) | 1,08 | 1,10 | 1,11 | 1,13 | **ÉCHEC** |
| `signal-strong` (:48) | 1,76 | 1,84 | 1,86 | 1,84 | **ÉCHEC** |
| `positive-soft` (:50) | 1,18 | 1,22 | 1,24 | 1,26 | **ÉCHEC** |
| `negative-soft` (:52) | 1,13 | 1,17 | 1,18 | 1,19 | **ÉCHEC** |
| `warning-soft` (:54) | 1,22 | 1,27 | 1,30 | 1,32 | **ÉCHEC** |
| `option-soft` (:56) | 1,14 | 1,18 | 1,20 | 1,21 | **ÉCHEC** |
| `macro-soft` (:58) | 1,18 | 1,23 | 1,25 | 1,27 | **ÉCHEC** |
| `macro-strong` (:59) | 1,72 | 1,80 | 1,82 | 1,79 | **ÉCHEC** |

**Conséquence dure** : **aucun** jeton de bordure ou de bande n'atteint 3:1. Toute information portée par une bordure seule ou une bande de `CellGrid` seule est invisible au sens de WCAG 1.4.11. Le contrat s'en sauve par sa règle « jamais la couleur seule » (`tokens.ts:34-38` ; `CellGrid` écrit le coefficient + `data-band` + légende, widgets.css:817-823) — mais le jeton `border` à 1,32:1 ne **délimite** pas non plus une carte : sur `.vx-card` (global.css:5219-5229), la carte est reconnue par sa surface et son ombre, pas par sa bordure.

### 1.4 Texte sémantique sur fond teinté (le vrai cas des pastilles)

Fond `-soft` composé sur `surface-1` puis `surface-2` :

| Paire | /surface-1 | /surface-2 | AA |
|---|---|---|---|
| `signal` sur `signal-soft` | 6,57 | 6,11 | AA |
| `positive` sur `positive-soft` | 7,31 | 6,81 | AA |
| `negative` sur `negative-soft` | 5,43 | 5,07 | AA |
| `warning` sur `warning-soft` | 8,84 | 8,20 | AA |
| `option` sur `option-soft` | 5,59 | 5,22 | AA |
| `macro` sur `macro-soft` | 7,43 | 6,92 | AA |
| `signal` sur `signal-strong` | 4,64 | **4,33** | **AA-large seulement sur surface-2** |
| `text-muted` sur `signal-faint` (survol de ligne) | 5,06 | 4,73 | AA |

### 1.5 Texte sombre sur accent plein (boutons remplis)

`black`/`app`/`surface-0` sur `signal` = 9,49 / 9,22 / 8,95 → AA.
`text` sur `signal` = **1,94 → ÉCHEC** ; sur `warning` = **1,48** ; sur `positive` = **1,86** ; sur `macro` = **1,82**. Aucune porte n'interdit `color: var(--vx-text)` sur `background: var(--vx-signal)`.
`black` sur `signal-deep` = **2,97 → ÉCHEC** : `signal-deep` n'est utilisable ni comme texte ni comme fond de texte sombre ; il n'est légitime que comme fin de dégradé (ADR-017 ligne 43).

### 1.6 Jetons non couleur

| Famille | Clés | Fichier | Usage réel mesuré |
|---|---|---|---|
| `space` | 4/8/12/16/20/24/32/40/48 | tokens.ts:101-111 | 4:130, 8:215, 12:236, 16:171, 20:67, 24:28, 32:9, **40:0**, **48:0** |
| `radius` | 6/10/14/**18→16px**/**22→20px**/pill | tokens.ts:114-121 | 6:47, 10:49, 14:12, 18:3, **22:1**, pill:22 |
| `shadow` | panel/glass/floating/inset | tokens.ts:132-137 | `floating` : 0 usage CSS |
| `motionDuration` | 90/140/180/220/600 | tokens.ts:144-153 | 90:1, 140:18, 180:3, 220:1, 600:1 |
| `motionEase` | standard/decelerate | tokens.ts:156-159 | — |
| `zIndex` | base/sticky/popover/sheet/dialog/toast | tokens.ts:162-169 | **3 usages seulement** ; 8 `z-index` bruts (`1`, `2`, `-1`) |
| `fontSize` | meta 13 / body 14 / label 13 / title 16 / display 22 / headline 28 / metric 34 | tokens.ts:185-193 | metric : **1 usage, mort** (§5) |

---

## 2. PRIMITIVES PAR NOMBRE DE CONSOMMATEURS RÉELS

21 fichiers dans `apps/web/src/components/widgets/` (19 primitives React + 2 modules). Consommateurs = imports hors `components/widgets/`, hors fichiers de test.

| Primitive | Consom. externes | Fichiers consommateurs (fichier:ligne) |
|---|---|---|
| `Widget.tsx` | **19** (5 en composant, 14 en type seul) | composant : `pages/risk/RiskPage.tsx:13`, `pages/risk/RiskModules.tsx:13`, `pages/markets/MarketsPage.tsx:13`, `pages/portfolio/PortfolioModules.tsx:7`, `pages/portfolio/PortfolioPage.tsx:17`, `pages/charts/ChartsPage.tsx:18`, `pages/charts/ChartsModules.tsx:8` — type seul : 12 catalogues `*Modules.ts` |
| `StatusChip.tsx` | **4** + 5 internes | `pages/risk/RiskModules.tsx:12`, `pages/markets/MarketsPage.tsx:12`, `pages/portfolio/PortfolioPage.tsx:16`, `pages/charts/ChartsModules.tsx:7` |
| `InstrumentTile.tsx` | **3** | `pages/options/OptionsModules.tsx:13`, `pages/markets/MarketsPage.tsx:19`, `pages/TodayPage.tsx:12` |
| `ArcGauge.tsx` | **2** | `pages/markets/BreadthPanel.tsx:3`, `pages/charts/ChartsModules.tsx:1` |
| `DayBars.tsx` | **2** | `pages/risk/RiskModules.tsx:9`, `pages/charts/ChartsModules.tsx:2` |
| `Glyph.tsx` | **2** (+1 interne KpiTile) | `shell/NavGlyph.tsx:1`, `pages/portfolio/PortfolioSummary.tsx:2` |
| `KpiDelta.tsx` | **2** (+1 interne) | `pages/TodayModules.tsx:11`, `pages/portfolio/PortfolioSummary.tsx:3` |
| `KpiTile.tsx` | **2** | `pages/TodayModules.tsx:12`, `pages/portfolio/PortfolioSummary.tsx:4` |
| `SparkFigure.tsx` | **2** (+1 interne) | `pages/risk/RiskModules.tsx:11`, `pages/charts/ChartsModules.tsx:6` |
| `ActivityFeed.tsx` | **1** | `pages/portfolio/PortfolioModules.tsx:5` |
| `CellGrid.tsx` | **1** | `pages/risk/RiskPage.tsx:11` |
| `LinearGauge.tsx` | **1** | `pages/markets/BreadthPanel.tsx:4` |
| `LiveBadge.tsx` | **1** | `shell/ContextBar.tsx:9` |
| `MultiSeriesArea.tsx` | **1** | `pages/charts/ChartsModules.tsx:4` |
| `PeriodTabs.tsx` | **1** | `pages/charts/ChartsPage.tsx:16` |
| `ProvenanceLine.tsx` | **1** | `pages/opportunities/OpportunitiesPage.tsx:13` |
| `RingShares.tsx` | **1** | `pages/portfolio/ConcentrationPanel.tsx:1` |
| `SharesBand.tsx` | **1** | `pages/portfolio/ConcentrationPanel.tsx:3` |
| **`StepList.tsx`** | **0** | **AUCUN.** Prévu `PLAN_NUIT_IDENTITE_V3.md:40` (« jamais posé → P2, P6 ») |
| `geometry.ts` | 0 externe (helper interne légitime, 6 primitives) | LinearGauge:1, SharesBand:1, MultiSeriesArea:1, DayBars:1, RingShares:1-2, ArcGauge:1 |
| **`pageAccent.ts`** | **0 au runtime** | **Importé uniquement par `catalog.test.ts:41`.** Aucune page ne le lit. |

### Trois trous mesurés

1. **`StepList` à zéro consommateur** — la primitive existe (`StepList.tsx:31-66`) et son test aussi (`StepList.test.tsx`), mais aucune page ne la pose. Les dix gates d'Analyse et le pipeline d'Opportunités, qu'elle devait servir, ne l'utilisent pas.

2. **`pageAccent.ts` est une table morte au runtime.** `PAGE_ACCENTS` (`pageAccent.ts:30-49`) déclare `options: 'option'` et `simulator: 'option'`. Le DOM ne pose `data-page-accent` que dans **trois** fichiers, tous en `"macro"` : `pages/risk/RiskPage.tsx:248`, `pages/markets/MarketsPage.tsx:474`, `pages/charts/ChartsPage.tsx:421`. **Options et Simulateur ne posent rien** ; leur teinte déclarée n'atteint jamais l'écran (`PLAN_NUIT_IDENTITE_V3.md:127` le nommait déjà : « Poser `data-page-accent="option"` (déclaré depuis le socle, **jamais posé**) »). Aucune porte ne compare la table au DOM.

3. **`Widget` n'est le conteneur que de 5 pages sur 12.** Les 7 autres (`today`, `options`, `opportunities`, `analysis`, `simulator`, `catalysts`, `calendar`, `sources`) importent seulement `WidgetSize`/`WidgetVariant` comme types et rendent encore `Card` directement.

### Les 14 composants racine (`apps/web/src/components/`)

| Composant | Consommateurs |
|---|---|
| `AbsentModule.tsx` | 24 |
| `Card.tsx` | 20 | `DataStateBoundary.tsx` | 20 |
| `FreshnessBadge.tsx` | 17 | `moduleState.ts` | 16 |
| `AuthRequiredNotice.tsx` | 15 | `SyntheticBanner.tsx` | 13 |
| `Metric.tsx` | 12 | `absence.tsx` | 12 |
| `CensusBars.tsx` | 7 | `ModuleStatus.tsx` | 6 |
| `StatusBadge.tsx` | **2** (`pages/sources/CapabilityInspector.tsx:2`, `pages/SourceHealthMatrix.tsx:4`) — doublon fonctionnel de `StatusChip` |
| `NotFoundPage.tsx` / `NotInstalledPage.tsx` | 1 chacun (`app/routes.tsx:6-7`) |

---

## 3. LES 21 FAMILLES DE CLASSES CSS DE TABLE (24 fichiers)

Le chiffre est exact : **24 fichiers `.tsx` rendent un `<table>`, pour 21 familles de classes distinctes.**

| # | Famille | Fichier:ligne du `<table>` | Règles CSS |
|---|---|---|---|
| 1 | `vx-matrix-table` | `components/ai/AiAnswerView.tsx:227`, `pages/SourceHealthMatrix.tsx:112`, `pages/opportunities/OpportunitiesModules.tsx:221`, `pages/opportunities/OpportunityTable.tsx:244`, `pages/analysis/AnalysisModules.tsx:252`, `pages/calendar/EventAgenda.tsx:187` et `:250`, `pages/calendar/CalendarModules.tsx:106`, `:155`, `:209` | global.css:1152-1193, 4181-4184, 7128, 8065-8082, 8198-8222 (29 occurrences) |
| 2 | `vx-opp-table` | modificateur sur `OpportunityTable.tsx:244` | **0 règle CSS** — classe morte |
| 3 | `vx-sec-facts` | modificateur sur `AnalysisModules.tsx:252` | global.css (2) |
| 4 | `vx-cal-revision-table` | modificateur sur `EventAgenda.tsx:187`, `:250` | global.css (2) |
| 5 | `vx-chain-table` | `pages/options/OptionChainTable.tsx:181` | global.css:2218-2276 (11) |
| 6 | `vx-markets-table` | `pages/markets/MarketsTable.tsx:182` | global.css:1881-1946 (20) |
| 7 | `vx-ohlcv-table` | `pages/analysis/OhlcvTable.tsx:12`, `pages/charts/RebasedComparison.tsx:109` | global.css:2453-2484 (6) |
| 8 | `vx-scenarios-table` | `pages/simulator/SimResult.tsx:177`, `pages/analysis/ScenarioPanel.tsx:41` | global.css:2454-2476, 7279, 7714 (6) |
| 9 | `vx-sim-points` | `pages/simulator/SimResult.tsx:84` | global.css:2455-2482 (5) |
| 10 | `vx-pf-lots` | `pages/portfolio/PortfolioTable.tsx:37` | global.css:2925-2970, 7799 (6) |
| 11 | `vx-pf-excluded-table` | `pages/portfolio/PortfolioTable.tsx:107` | global.css:2926-2942 (3) |
| 12 | `vx-pf-ledger-table` | `pages/portfolio/LedgerPanel.tsx:117` | global.css:2927-2944 (3) |
| 13 | `vx-pf-concentration-table` | `pages/portfolio/ConcentrationPanel.tsx:95` | global.css:2928-2946, 7791 (4) |
| 14 | `vx-pf-import-errors` | `pages/portfolio/CsvImportPanel.tsx:149` | global.css:2929-2948 (3) |
| 15 | `vx-pf-import-valid` | `pages/portfolio/CsvImportPanel.tsx:189` | global.css:2930-2950 (3) |
| 16 | `vx-fu-theses-table` | `pages/catalysts/review/ReviewQueueSection.tsx:214` | global.css:2931-2952 (3) |
| 17 | `vx-perf-months-table` | `pages/portfolio/performance/PerformanceSection.tsx:288` | global.css:2932-2953 (3) |
| 18 | `vx-perf-points-table` | `pages/portfolio/performance/PerformanceSection.tsx:341` | global.css:2933-2955 (3) |
| 19 | `vx-w2-figure-table` | `components/widgets/MultiSeriesArea.tsx:191`, `DayBars.tsx:130`, `RingShares.tsx:193` | widgets.css:711-734 |
| 20 | `vx-w2-spark-table` | `components/widgets/SparkFigure.tsx:131` | widgets.css:710-733 |
| 21 | `vx-w2-grid` | `components/widgets/CellGrid.tsx:69` | widgets.css:803-852 |

### Ce qui se recouvre exactement

- **Groupe A — `width:100% / border-collapse / font-size: meta`, à l'identique** : familles 7, 8, 9 (global.css:2453-2459) **et** 10-18 (global.css:2925-2937). Deux blocs séparés, même déclaration, douze familles. La seule différence : `text-align: right; white-space: nowrap` (global.css:2461-2471) contre `text-align: left; vertical-align: top; white-space: nowrap` (global.css:2939-2961).
- **Groupe B — `vx-w2-spark-table` et `vx-w2-figure-table` sont strictement identiques** : widgets.css:710-734 les déclare toujours ensemble, sans une seule règle propre à l'une. Deux noms, un style. Fusion immédiate.
- **`vx-matrix-table` est la seule famille avec `padding: 8px 16px`, `border-top`, `caption`** (global.css:1158-1178). Elle est aussi la plus utilisée (10 tables sur 24) : c'est la base de fait de la future `DataTable`.
- **`vx-opp-table` (famille 2) n'a AUCUNE règle** : une classe posée dans le JSX qui ne fait rien.
- **7 familles d'ENVELOPPE de défilement** pour ces 21 tables : `vx-matrix-scroll`, `vx-chain-table-scroll`, `vx-markets-table-scroll`, `vx-pf-table-scroll`, `vx-ohlcv-scroll`, `vx-cal-scroll`, `vx-w2-grid-scroll`. Les cinq premières partagent `max-height: 420px` et l'en-tête collant (global.css:5408-5428) — **`vx-chain-table-scroll` en est absent** : la chaîne d'options, la table la plus dense du produit, n'a **pas** d'en-tête collant.
- **Seules 6 tables sur 24 portent un `<caption>`** (`OpportunityTable`, `SourceHealthMatrix`, `EventAgenda`, `CalendarModules`, `AiAnswerView`, `CellGrid`). Les 18 autres utilisent `aria-label` sur `<table>` — sémantiquement plus faible et invisible visuellement.

### Contrat exact proposé pour la primitive `DataTable`

```ts
// apps/web/src/components/widgets/DataTable.tsx

/** Alignement = TYPE de valeur, jamais une préférence. `num` ⇒ mono + tabular + droite. */
export type ColumnAlign = 'text' | 'num' | 'status';

export interface DataColumn<Row> {
  readonly key: string;
  /** Nom de colonne. Micro-libellé : mono 10 px capitales (règle unique, global.css:4688). */
  readonly header: string;
  /** Unité / devise SERVIE, rendue sous l'en-tête. Une colonne numérique sans unité est refusée au typage. */
  readonly unit: ColumnAlign extends 'num' ? string : string | null;
  readonly align: ColumnAlign;
  /** `true` ⇒ <th scope="row"> : la colonne d'identité de la ligne. Exactement une par table. */
  readonly rowHeader?: boolean;
  /** Largeur de composition. Jamais un px libre. */
  readonly width?: 'auto' | 'min' | 'ch8' | 'ch12' | 'ch16';
  /**
   * Rend une valeur SERVIE verbatim, ou <AbsentCell quoi nature reason/>.
   * Ne calcule rien : la porte no-authoritative-calculation reste la loi.
   */
  readonly cell: (row: Row) => ReactNode;
  /** Signe SERVI (`signGroupOfText`), jamais déduit d'un nombre. `null` = pas de couleur. */
  readonly sign?: (row: Row) => SignGroup | null;
}

export interface DataTableProps<Row> {
  readonly id: string;
  /** <caption> OBLIGATOIRE et visible — remplace les 18 aria-label actuels. */
  readonly caption: string;
  /** Phrase d'unité/période sous la légende. Une table sans unité n'est pas qualifiée. */
  readonly captionDetail?: string;
  readonly columns: readonly DataColumn<Row>[];
  readonly rows: readonly Row[];
  /** Clé stable SERVIE. Jamais un index, jamais un repli (défaut réel de portfolioView.ts). */
  readonly rowKey: (row: Row) => string;
  readonly density: 'comfortable' | 'compact';
  /**
   * 'panel' ⇒ enveloppe défilante bornée + thead collant + tabIndex={0} + role="region".
   * Une seule implémentation pour les 7 familles d'enveloppe actuelles.
   */
  readonly overflow: 'none' | 'panel';
  /** État nommé quand rows est vide. Jamais une table vide, jamais un tiret. */
  readonly emptyLabel: string;
  readonly selectedRowKey?: string | null;
  readonly onOpenRow?: (key: string) => void;
  readonly rowActionLabel?: (row: Row) => string;
  /** Ordre SERVI. Le client ne trie pas : il déclare l'ordre qu'il a reçu. */
  readonly servedOrder: { readonly by: string; readonly direction: 'asc' | 'desc' } | null;
  /** Pied : méthode, version, source, as_of. Rendu par ProvenanceLine. */
  readonly footnote?: ReactNode;
}
```

**Une seule famille CSS** : `.vx-dt` + `[data-density]`, `.vx-dt-cell[data-align]`, `[data-sign]`, `[data-absent]`, `.vx-dt-scroll[data-overflow='panel']`. Elle remplace les 21 familles et les 7 enveloppes.

**Invariants portés par le type, pas par la revue** : une colonne `num` exige `unit: string` (non nullable) ; `rowKey` n'a pas de valeur par défaut ; `emptyLabel` est obligatoire ; `servedOrder` est explicitement `null` quand le serveur ne publie pas d'ordre — ce qui interdit d'inventer un tri client.

---

## 4. PIÈGES DU CSS — ORDRE D'IMPORT ET SPÉCIFICITÉ, AVEC PREUVE

Ordre d'import, `apps/web/src/main.tsx:6-9` :
```
fonts.css → design/tokens.css → styles/global.css → styles/widgets.css
```
`global.css` : 8 231 lignes, 557 sélecteurs de classe racine. `widgets.css` : 1 748 lignes, 100 sélecteurs. **Aucun `@layer`, aucun `@import`** — l'arbitrage repose entièrement sur l'ordre des fichiers et sur la spécificité. `PLAN_NUIT_IDENTITE_V3.md:185-186` le nomme : « Le placement d'une planche convertie vit dans `widgets.css`, **après** les spans du socle — **piège déjà payé trois fois** ».

**8 sélecteurs sont déclarés dans les deux fichiers** : `.vx-board`, `.vx-markets-grid`, `.vx-metric-label`, `.vx-metric-value`, `.vx-pf-grid`, `.vx-risk-concentration-block`, `.vx-risk-grid`, `.vx-today-grid`.

### Piège 1 — La déclaration morte de `.vx-metric-value` (triple déclaration)

| Site | Déclaration |
|---|---|
| global.css:5459-5467 | `color: silver; font-family: mono; font-size: var(--vx-font-size-metric)` **(=34 px)** ; `letter-spacing: -0.025em; line-height: 1.1` |
| global.css:6138-6141 | `font-size: 30px; line-height: 1.05` |
| widgets.css:1460-1463 | `line-height: 1.05; letter-spacing: -0.02em` |

Spécificité identique (0,1,0) trois fois ⇒ le dernier gagne, propriété par propriété. **Résultat effectif : 30 px** (global.css:6138), `letter-spacing: -0.02em` (widgets.css:1462). **`--vx-font-size-metric` (34 px) n'est appliqué nulle part dans le produit** : c'est son seul site d'usage (global.css:5462) et il est écrasé 676 lignes plus bas.

Idem `.vx-metric-label` : global.css:5450 pose `letter-spacing: 0.08em`, global.css:6134 le passe à `0.12em`, widgets.css:1465-1468 le ramène à `0.08em`. **La déclaration intermédiaire global.css:6134 est morte.**

### Piège 2 — Marchés et Aujourd'hui n'ont pas la même gouttière, à cause de l'ordre seul

`global.css:6008-6012` déclare les deux ensemble :
```css
.vx-today-grid, .vx-markets-grid { gap: var(--vx-space-20) var(--vx-space-16); margin-top: var(--vx-space-20); }
```
`widgets.css:1202-1214` redéclare `.vx-markets-grid` seul, même spécificité (0,1,0), fichier postérieur :
```css
.vx-markets-grid { … gap: var(--vx-space-12); … margin-top: var(--vx-space-12); }
```
**Mesuré : Aujourd'hui a des gouttières 20/16 px, Marchés 12/12 px.** Les deux planches sœurs de l'anatomie canonique diffèrent, alors qu'une règle unique les déclarait identiques. Personne ne le voit en lisant `global.css`.

Corollaire : `global.css:6726` pose `.vx-board { align-items: stretch }`, `widgets.css:1735-1739` pose `.vx-board, .vx-today-grid, .vx-markets-grid { align-items: start }` — **`stretch` est mort sur les trois.**

### Piège 3 — Le matériau de carte est scindé en deux, 5 pages contre 7

`widgets.css:1424-1443` énumère à la main cinq grilles :
```css
.vx-risk-grid > [data-module] > .vx-card, .vx-pf-grid > …, .vx-markets-grid > …,
.vx-today-grid > …, .vx-charts-grid > … {
  border-radius: var(--vx-radius-22);              /* 20 px */
  box-shadow: var(--vx-shadow-panel), var(--vx-shadow-inset);
}
```
`global.css:6741-6750` pose pour toutes les planches `.vx-board` :
```css
.vx-board > [data-module] > .vx-card, … { border-radius: var(--vx-radius-14);  /* 14 px */
  box-shadow: var(--vx-shadow-inset); }
```
Spécificité (0,3,0) des deux côtés ; `widgets.css` gagne sur `risk`, `portfolio`, `charts` qui portent les deux classes (`pages/risk/RiskPage.tsx:190` `"vx-risk-grid vx-board"`, `pages/portfolio/PortfolioPage.tsx:170`, `pages/charts/ChartsPage.tsx:326`).

**Résultat mesuré sur les douze destinations :**
- **rayon 20 px + `shadow-panel`** : Aujourd'hui, Marchés, Portefeuille, Risques, Graphiques (5) ;
- **rayon 14 px + `shadow-inset` seul** : Options, Opportunités, Analyse, Calendrier, Catalyseurs, Simulateur, Sources & Rapports (7) ;
- **rayon 16 px + `shadow-glass`** de `.vx-card` (global.css:5219-5229) : **jamais visible**, toute carte étant sur une planche.

C'est exactement le défaut que l'en-tête de `Card.tsx:6-22` déclare avoir corrigé (« 15 listes de sélecteurs énumérées à la main … un module ajouté n'hérite de RIEN »). `widgets.css:1424-1443` **est la seizième liste**.

### Piège 4 — Spécificité : `widgets.css` ne peut pas battre `.vx-main table …`

`global.css:4688-4696` :
```css
.vx-main table thead th { color: titanium; font-family: mono; font-size: 10px; text-transform: uppercase; }
```
Spécificité (0,1,2). `widgets.css:719-727` pose `.vx-w2-spark-table th, .vx-w2-figure-table th { color: text-secondary }` — spécificité (0,1,1). **La spécificité l'emporte sur l'ordre du fichier** : les tables équivalentes des figures reçoivent l'en-tête mono 10 px capitales de `global.css`, jamais le `text-secondary` que `widgets.css` déclare. La déclaration de `widgets.css` est morte pour `thead`.

Même mécanique pour `.vx-main table tbody tr:hover { background: signal-faint }` (global.css:4715-4717, spécificité 0,2,2) : elle s'applique **à toutes les tables de la zone de travail**, y compris `.vx-w2-grid` (la matrice de corrélation), sans qu'aucune famille puisse s'en exclure autrement qu'en montant la spécificité.

### Piège 5 — Hygiène brute non gardée

- **418 valeurs `px` brutes** (367 dans `global.css`, 51 dans `widgets.css`) hors jetons.
- **41 `font-size` en px libres** : 18× `10px`, 6× `11px`, **5× `10.5px`**, `40px`×2, `30px`, `28px`, `26px`, `20px`, `12px`. Les `10.5px` sont les pieds de carte (global.css:6073, 6789), la méthode d'Analyse (7274) et les légendes de smile (7538, 7575) — sous le plancher 13 px que `DESIGN_SYSTEM.md:49` et `WIDGETS_V2_PLAN.md:63` (« aucune méta sous 13 px ») déclarent.
- **8 `z-index` bruts** (`1`×6, `2`, `-1`×2) contre 3 usages des jetons `--vx-z-*`, alors que `TOKENS.md:16` écrit « aucune valeur locale arbitraire ».
- **`max-height: 420px`** brut sur les cinq enveloppes défilantes (global.css:5409-5415).
- **Deux couleurs de focus** : `--vx-silver` en défaut global (global.css:34) et `--vx-signal` sur 7 sites (3673, 4782, 4868, 4979, 5383, 5760, 7482). Contrastes 12,44 et 8,55 — tous deux conformes, mais deux significations pour un état.
- **`.vx-num`** (global.css:4654-4656) ne pose que `font-variant-numeric` — **pas** `font-family: mono`. Sur les 115 usages en TSX, seuls ceux imbriqués dans `.vx-markets-table` (global.css:1933) et `.vx-chain-table` (2237) obtiennent la chasse fixe. « Mono/tabular pour prix, dates, unités » n'est donc pas tenu par la classe qui prétend le porter.

---

## 5. INCOHÉRENCES CLÉ/VALEUR DES JETONS

| # | Incohérence | Preuve | Conséquence |
|---|---|---|---|
| 1 | **`radius[18] = '16px'`** | `tokens.ts:118` | La clé ment. `VERTEX_ONE_VISUAL_DIRECTION.md:104` écrit « rayons … 18 px pour les grandes surfaces » ; suivre la doc donne 16 px. `TITANIUM_LEDGER_VISUAL_SYSTEM.md:171` écrit « grande surface : rayon 16 px » : les deux documents se contredisent, et le jeton donne raison au second tout en portant le nom du premier. |
| 2 | **`radius[22] = '20px'`** | `tokens.ts:119` | Idem. `PLAN_NUIT_IDENTITE_V3.md:65` le documente comme un fait acquis (« le socle a `radius-18: 16px` et `radius-22: 20px` ») au lieu de le corriger. `tokens-css.test.ts:77` fige l'anomalie : `expect(Object.keys(radius)).toEqual(['6','10','14','18','22','pill'])` — la porte protège le mensonge. |
| 3 | **`--vx-font-size-metric` (34 px) inutilisable** | `tokens.ts:192`, seul usage global.css:5462, écrasé global.css:6138 | Un jeton de la source typée sans effet sur l'écran. |
| 4 | **`space[40]` et `space[48]` à zéro usage** | `tokens.ts:109-110` ; 0 occurrence dans `global.css` et `widgets.css` | Deux jetons morts que `tokens-css.test.ts:70` exige pourtant (`toEqual([4,8,12,16,20,24,32,40,48])`). |
| 5 | **`shadow.floating` à zéro usage** | `tokens.ts:135` | Idem, figé par `tokens-css.test.ts:87`. |
| 6 | **`warning` ≈ `signal-bright` : Δ max 4/255** | `tokens.ts:40` `#f2c76b` vs `:53` `#f0c36a` — Δ RGB = (2,4,1), ratio de contraste **1,03** | Deux jetons, une seule apparence. Réserve 3 d'ADR-017 (ligne 76) : à trancher « au lot L0, avant toute page P ». Toujours non tranchée ; `catalog.test.ts:146-155` la tient par une porte qui interdit à toute page de déclarer `warning`. |
| 7 | **`titanium` ≈ `text-secondary` : Δ max 14/255** | `tokens.ts:32` `#aaa497` vs `:29` `#b8b0a0`, ratio **1,15** | Même défaut que #6, jamais signalé nulle part. `titanium` sert les micro-libellés (global.css:4690, 5451), `text-secondary` le texte courant : deux rôles, une couleur perçue. |
| 8 | **`silver` ≈ `text` : Δ 33, ratio 1,34** | `tokens.ts:31` vs `:28` | Limite mais distinguable ; à documenter, pas à corriger. |
| 9 | **`motionDuration` : les noms documentaires n'existent pas** | `MOTION_AND_MICROINTERACTIONS.md:11-14` définit `--vx-motion-instant/fast/base/slow` ; le CSS généré n'expose que `--vx-motion-90/140/180/220/600` (`tokens.css:81-85`) | Un développeur qui suit la table normative écrit quatre variables inexistantes. Seul `--vx-motion-data` porte sa correspondance (`tokens.ts:151`). |
| 10 | **`fontSize` : vocabulaire documenté ≠ vocabulaire livré** | `TOKENS.md:14` liste « `body`, `meta`, `label`, `title`, `display`, `mono-number` » ; `tokens.ts:185-193` livre `meta, body, label, title, display, headline, metric` | `mono-number` n'existe pas ; `headline` et `metric` ne sont pas documentés. |
| 11 | **`meta` et `label` valent tous deux `13px`** | `tokens.ts:186` et `:188` | Deux clés, une valeur : le protocole de nuance interdit un alias de même valeur (ADR-017, options rejetées, ligne 84). `label` : 6 usages ; `meta` : 198. |
| 12 | **`--vx-page-accent*` sans consommateur CSS** | `tokens.css:111-130` génère 12 variables ; **aucune règle de `global.css` ni de `widgets.css` ne lit `var(--vx-page-accent…)`** | Les trois pages qui posent `data-page-accent="macro"` (RiskPage:248, MarketsPage:474, ChartsPage:421) n'obtiennent **aucun effet visuel**. |

---

## 6. CE QU'AUCUNE PORTE NE VÉRIFIE — ET DEVRAIT

### Ce que les 9 portes vérifient, exactement

| Porte | Vérifie | Ne vérifie PAS |
|---|---|---|
| `no-raw-colors.test.ts` | `#hex` / `rgb()` / `hsl()` hors `src/design/tokens.*` (:48-63) ; vocabulaire d'ordre FR+EN (:163-181) ; anti-vacuité par injection (:203-213) | tailles, espaces, rayons, z-index, ombres bruts ; contraste ; **qu'un jeton soit utilisé** |
| `tokens-css.test.ts` | identité `tokens.css` = sortie du générateur (:54-56) ; présence de chaque couleur/space/radius/shadow/motion/z (:63-105) ; reduced-motion à 0 ms (:107-114) ; dégradés dans la famille, alpha 0 en fin (:116-134) ; blocs `[data-page-accent]`, `signal`/`positive`/`negative` inéligibles, aucun défaut `:root` (:136-167) | **aucun ratio de contraste** ; qu'une clé corresponde à sa valeur ; qu'un jeton soit consommé |
| `canon-v2-docs.test.ts` | ADR-017 existe/Accepté/sections (:168-185) ; 9 formes admises nommées (:187-197) ; 13 interdits maintenus (:199-206) ; 15 documents du canon citent ADR-017 (:227-230) ; 10 formulations v1 ne reviennent pas (:232-240) ; 6 formulations de teinte signée interdites (:242-255) ; 17 invariants toujours écrits (:257-265) | **la cohérence numérique entre documents** (rail, colonnes, rayons, durées) ; que le code applique la règle (elle le dit, :20-22) |
| `no-authoritative-calculation.test.ts` | arithmétique `+ - * / % **` dont une opérande lit un des **51 noms** de `FINANCIAL_PROPERTIES` (:53-66) ; coercition `Number/parseFloat/parseInt` (:81) ; anti-vacuité (> 50 fichiers, > 20 opérations, :219-223) ; 9 injections positives / 6 négatives (:241-272) | variable intermédiaire renommée ; calcul dans une fonction appelée ; nom assemblé à l'exécution (avoué :28-34) |
| `no-fabricated-values.test.ts` | 4 formes littérales (`\d,\d`, milliers, `\d %`, `\d (CHF\|EUR\|USD\|GBP\|JPY)`) dans `src/pages` **et** `src/components/widgets` (:52, 58-74) ; anti-vacuité + faux positifs (:208-236) | `src/components/**` hors `widgets` ; `src/shell` ; valeur assemblée à l'exécution (avoué :29-33) |
| `no-ambiguous-dash.test.ts` | 11 glyphes (:96-108) selon 3 règles — littéral exact, position de repli avec `trim`, texte JSX enfant unique (:250-271) — sur `src/pages` **et** `src/components` (:81-89) ; 1 exemption (`absence.tsx`) avec cliquet anti-morte (:296-312) | indirection par constante ; `?? '0'` ; que `reason` vienne du serveur ; **`src/shell`** (avoué :47-60) |
| `no-uncalibrated-probability.test.ts` | toute lecture de `probability_evidence` (accès, index, déstructuration) sur `src/**` (:88-121) ; anti-vacuité sur la présence du champ (:146-152) ; 6+4 injections (:166-188) | tout autre champ prédictif ; l'affichage d'une probabilité venue d'un autre nom |
| `one-dominant-per-page.test.ts` | nombre de `rank="dominant"` / `data-rank="dominant"` par fichier `.tsx` de `src/pages`, forme conditionnelle comprise (:50-92) | un fichier ≠ une page ; dominante portée par un composant enfant (avoué :22-27) ; **zéro dominante** (une page sans dominante passe) |
| `widgets/catalog.test.ts` | 12 catalogues non vides (:66-71) ; `size` ∈ {S,M,L,XL} (:73-83) ; `variant` ∈ 6 valeurs (:85-95) ; ≤ 1 `dominant` (:97-106) ; dominante pas en `S` (:108-119) ; ids uniques (:121-126) ; teinte ∈ `pageAccent`, jamais signée, jamais `warning`, 12 entrées explicites (:129-162) | **que le DOM pose la teinte déclarée** ; qu'un `XL` occupe 4 colonnes (avoué :23-24) ; **qu'une page sans déclaration ne pose pas `data-page-accent`** |

### Les 12 trous qu'aucune porte ne couvre

1. **Aucune porte de contraste.** `TOKENS.md:21` affirme « Chaque token de couleur a un libellé/icône associé et **une paire texte/fond vérifiée AA** » : rien ne le vérifie. `signal-deep` à 2,67:1 sur `surface-1` et `text` sur `signal` à 1,94:1 passeraient sans bruit. La seule mesure automatique est `axe` en e2e (`ci.yml:280`, `e2e/accessibility.spec.ts:89`), qui ne teste que les paires **rendues à l'écran sur les données du moment** — un état non atteint n'est jamais mesuré. **Porte à écrire** : calcul WCAG sur toutes les paires déclarées de `tokens.ts`, avec allowlist nommée pour les jetons décoratifs (`grid-line`, `titanium-ghost`, `signal-deep`).

2. **Aucune porte « clé = valeur » sur les jetons numériques.** `radius[18]='16px'` et `radius[22]='20px'` passent, et `tokens-css.test.ts:77` les **fige**. **Porte** : pour toute clé numérique de `space`, `radius`, `motionDuration`, `fontSize`, exiger `value === `${key}px``.

3. **Aucune porte anti-jeton mort.** `space[40]`, `space[48]`, `shadow.floating` : zéro usage ; `--vx-font-size-metric` : un usage écrasé. **Porte** : chaque `--vx-*` généré doit avoir ≥ 1 lecture `var(--vx-…)` dans `src/styles/**` ou `src/**/*.tsx`.

4. **Aucune porte anti-déclaration morte / anti-collision d'ordre.** Les 8 sélecteurs déclarés dans les deux fichiers et les 3 déclarations mortes prouvées en §4 passent en silence. **Porte** : parser `global.css` + `widgets.css` dans l'ordre d'import de `main.tsx`, calculer pour chaque couple (sélecteur, propriété) le vainqueur, et échouer sur toute déclaration jamais gagnante.

5. **Aucune porte sur les valeurs px brutes.** 418 `px`, dont 41 `font-size` et 5 sous 11 px, alors que `DESIGN_SYSTEM.md:49` fixe 13 px comme plancher AA. **Porte** : interdire `font-size`, `border-radius`, `gap`, `padding`, `margin`, `z-index` littéraux hors allowlist nommée (`1px` de filet, `2px` de contour de focus).

6. **Aucune porte ne relie `PAGE_ACCENTS` au DOM.** ADR-017 ligne 97 affirme que « `catalog.test.ts` exige que **chaque page qui pose `data-page-accent`** déclare une famille » — **l'ADR sur-déclare** : le test (`catalog.test.ts:129-162`) ne lit que la table, jamais le JSX. Options et Simulateur déclarent `option` et ne posent rien ; l'inverse (poser sans déclarer) passerait aussi, et c'est précisément le `fill` SVG noir que la réserve 5 voulait interdire. **Porte** : balayer `pages/**/*.tsx`, extraire chaque `data-page-accent="X"`, exiger `PAGE_ACCENTS[page] === X` **dans les deux sens**.

7. **Aucune porte n'exige une dominante.** `one-dominant-per-page.test.ts:101` ne filtre que `total > 1`. Une page à zéro dominante — « deux dominantes c'est zéro dominante », dit son propre en-tête ligne 18 — est verte.

8. **Aucune porte sur la matière de carte.** Les deux matériaux (20 px/`shadow-panel` contre 14 px/`shadow-inset`) coexistent sur douze destinations sans qu'aucun test ne l'énonce. **Porte** : `.vx-card` ne doit recevoir `border-radius` et `box-shadow` que d'**un seul** bloc CSS ; toute liste énumérée de grilles qui les redéclare échoue.

9. **Aucune porte sur les tables.** 21 familles, 7 enveloppes, 6 `<caption>` sur 24, un en-tête collant absent de la chaîne d'options, `vx-opp-table` sans règle. **Porte** (dès la `DataTable` livrée) : tout `<table>` de `src/pages` et `src/components` doit être rendu par `DataTable`, allowlist nommée pour les tables équivalentes des figures.

10. **`src/shell` est hors du périmètre de deux portes.** `no-ambiguous-dash` balaie `src/pages` + `src/components` (:81-89) ; `no-fabricated-values` balaie `src/pages` + `src/components/widgets` (:52). `src/shell/ShellTicker.tsx`, `ContextBar.tsx`, `NavRail.tsx` rendent des valeurs servies et **échappent aux deux**.

11. **Aucune porte sur la cohérence numérique des 16 documents.** `canon-v2-docs.test.ts` vérifie des *formulations*, jamais des *nombres*. Les contradictions mesurées :
   - **rail** : 248 px (`DESIGN_SYSTEM.md:54`, `TITANIUM_LEDGER_VISUAL_SYSTEM.md:168`) contre 232 px (`DASHBOARD_COMPOSITION.md:17`, `:26`, `RESPONSIVE.md:21`) — **réel : 136 px** (`global.css:87`) ;
   - **grille** : « 12 colonnes » (`DESIGN_SYSTEM.md:55`, `DASHBOARD_COMPOSITION.md:18`, `RESPONSIVE.md:15`, `:21`, `TITANIUM_LEDGER_VISUAL_SYSTEM.md:169`) — **réel : `repeat(4, minmax(0,1fr))`** (`global.css:5783`, `widgets.css:1211`) ;
   - **dominante** : 6–8 col. (`DESIGN_SYSTEM.md:56`, `WIDGET_LIBRARY.md:142`) / 7–8 (`DASHBOARD_COMPOSITION.md:19`) / 7–9 (`TITANIUM_LEDGER_VISUAL_SYSTEM.md:170`) ;
   - **gouttières** : 16–20 px (`DESIGN_SYSTEM.md:55`) / 16–24 px (`TITANIUM_LEDGER_VISUAL_SYSTEM.md:169`) — **réel : 12 sur Marchés, 20/16 sur Aujourd'hui et `.vx-board`** ;
   - **modules par page** : « trois à cinq » (`DESIGN_SYSTEM.md:57`, `DASHBOARD_COMPOSITION.md:5`, `WIDGET_LIBRARY.md:7`) — **réel : 13 sur Marchés, 19 sur Risques, 18 sur Portefeuille** (`widgets.css:1079-1097`, `1155-1172`, `1217-1229`) ; `REFONTE_TITANIUM_LEDGER.md:208` l'avoue sans le résoudre ;
   - **durées** : « 140–220 ms » (`DESIGN_SYSTEM.md:76`) contre 90/140/180/220/600 (`TOKENS.md:15`, `MOTION_AND_MICROINTERACTIONS.md:11-15`) ;
   - **rayons** : 18 px (`VERTEX_ONE_VISUAL_DIRECTION.md:104`) contre 16 px (`TITANIUM_LEDGER_VISUAL_SYSTEM.md:171`).

12. **Aucune porte n'oppose les dépendances déclarées aux dépendances installées.** Documents normatifs contre `apps/web/package.json` :
   - `ICON_SYSTEM.md:5` : « **Lucide est l'unique bibliothèque d'icônes** » — **lucide n'est pas installé** ;
   - `ICON_SYSTEM.md:5` : « les **vingt** SVG Vertex de `design-assets/icons/custom/` » — **il y en a 21**, et `GLYPH_NAMES` (`Glyph.tsx:39-62`) en déclare 21 ;
   - `DESIGN_SYSTEM.md:65`, `WIDGET_LIBRARY.md:14-16`, `:116` : « Radix Primitives » — **non installé** ;
   - `WIDGET_LIBRARY.md:17-19`, `:48-50`, `CHART_STANDARD.md:34`, `:36`, `:38` : « TanStack Table / TanStack Virtual » — **non installés** ; les tables sont du `<table>` manuel ;
   - `DESIGN_SYSTEM.md:63` liste 15 « primitives communes » : **10 n'existent pas** — `ProvenancePopover`, `EntitlementBadge`, `ChartFrame`, **`AccessibleDataTable`**, `EvidenceList`, `GateBadge`, `StatusBanner`, `SideSheet`, `NewsClusterRow`, `EventRow`. `AccessibleDataTable` est nommément la `DataTable` manquante, contractualisée depuis le premier jour et jamais écrite ;
   - `ACCESSIBILITY.md:20`, `TOKENS.md:44-46`, `WIDGET_LIBRARY.md:178` : « **Storybook** montre états, thèmes, focus, contrastes » — **aucun Storybook dans le dépôt** ;
   - `PLAN_NUIT_IDENTITE_V3.md:62-66` (lot T1, marqué fait) : `--vx-glass-veil`, `--vx-glass-edge`, `--vx-elev-1/2/3` — **aucun n'existe** dans `tokens.ts`.

---

## SYNTHÈSE — les 5 blocages structurants pour Titan Ledger

1. **Le matériau n'est pas unifié** : 5 pages en 20 px/`shadow-panel`, 7 en 14 px/`shadow-inset`, la carte de base en 16 px jamais visible (`widgets.css:1424-1443` vs `global.css:6741-6750`). Une composition bento « à surfaces franchement différentes » ne peut pas se construire sur deux matériaux involontaires.
2. **Le contraste n'est mesuré nulle part** : 15 jetons de bordure/bande sous 2:1, deux couples de jetons visuellement identiques (`warning`/`signal-bright` à Δ4, `titanium`/`text-secondary` à Δ14), et une affirmation documentaire fausse (`TOKENS.md:21`).
3. **La `DataTable` est le trou central** : 21 familles pour 24 fichiers, 7 enveloppes, un en-tête collant absent de la chaîne d'options, 18 tables sans `<caption>`. Le contrat existe depuis `DESIGN_SYSTEM.md:63` sous le nom `AccessibleDataTable` et n'a jamais été écrit.
4. **La cascade CSS n'est arbitrée par personne** : pas de `@layer`, 8 sélecteurs en double, au moins 3 déclarations mortes prouvées, un jeton (`font-size-metric`) neutralisé, deux planches sœurs aux gouttières différentes.
5. **Les documents et le code divergent sans porte** : rail 248/232 vs 136 réel, 12 colonnes déclarées vs 4 réelles, 3–5 modules déclarés vs 19 réels, Lucide/Radix/TanStack/Storybook normatifs et absents, et `pageAccent` déclaré pour 5 pages mais posé sur 3, sans effet CSS.