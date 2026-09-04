# Journal — Vertex Dashboard System Upgrade

Branche : `agent/vertex-1-0-dashboard-system-upgrade-v2`, ouverte depuis
`agent/vertex-1-0-dashboard-system-upgrade` (sept commits déjà livrés, conservés).
Base : `main` = `75f14d5`.

Ce journal enregistre, pour chaque changement majeur : le fichier, la raison, la
preuve. Il enregistre aussi ce qui a été REFUSÉ et pourquoi — un refus motivé est
une décision, et il vaut d'être retrouvé.

---

## Mesure « avant » — bundle, 2026-09-04

Relevé par `npm run build` depuis `apps/web`, sur `cdf0d9f`.

| Chunk | Brut | gzip | Chargé quand |
|---|---:|---:|---|
| `index` (fermeture initiale) | 319,00 kB | **96,08 kB** | toujours |
| `index.css` | 185,48 kB | **27,11 kB** | toujours |
| `moduleState` (partagé) | 139,96 kB | 45,77 kB | première page à modules |
| `echartsLoader` | 609,33 kB | **205,44 kB** | route qui rend une heatmap/treemap |
| `lightweightChartsLoader` | 163,98 kB | **52,96 kB** | route qui rend un prix |
| `PortfolioPage` | 69,16 kB | 17,55 kB | `/portfolio` |
| `AnalysisPage` | 53,05 kB | 14,99 kB | `/analysis` |
| `CatalystsPage` | 53,98 kB | 13,41 kB | `/catalysts` |
| `OptionsPage` | 42,81 kB | 12,00 kB | `/options` |
| `CalendarPage` | 41,95 kB | 10,51 kB | `/calendar` |
| `SimulatorPage` | 33,09 kB | 9,94 kB | `/simulator` |
| `OpportunitiesPage` | 30,39 kB | 8,01 kB | `/opportunities` |
| `RiskPage` | 29,48 kB | 8,70 kB | `/risks` |
| `MarketsPage` | 25,42 kB | 7,61 kB | `/markets` |
| `ChartsPage` | 23,91 kB | 7,00 kB | `/charts` |
| Polices Geist + Geist Mono | 141,01 kB | — | toujours (auto-hébergées, OFL-1.1) |

**Ce que cette mesure établit, et qui change le plan.** Le découpage par route
est DÉJÀ fait, page par page, et les deux moteurs graphiques sont DÉJÀ hors de
la fermeture initiale. L'exigence « lazy-load des moteurs » du programme est donc
tenue avant d'avoir commencé ; le travail de performance ne consiste pas à
découper, mais à ne pas défaire ce découpage en ajoutant des imports statiques
dans des modules partagés. Toute hausse du chunk `index` sera signalée ici.

ECharts pèse **quatre fois** Lightweight Charts en gzip. Une visualisation qui
peut se faire en SVG interne sans perdre en lisibilité ne doit donc pas tirer
ECharts sur une route qui ne l'a pas déjà.

---

## Dépendances — état et décisions

**Aucune dépendance ajoutée à ce stade.** Le produit tourne sur sept
dépendances de production :

`@tanstack/react-query` 5.102.8 · `echarts` 6.1.0 · `geist` 1.7.2 ·
`lightweight-charts` 5.2.1 · `react` 19.2.8 · `react-dom` 19.2.8 ·
`react-router-dom` 7.18.3.

### Refusées, avec le motif

| Paquet | Motif du refus |
|---|---|
| `cmdk` | La palette est un `combobox` + `listbox` : motif entièrement décrit par WAI-ARIA APG, écrit en une centaine de lignes de HTML natif. Le paquet aurait apporté un thème à neutraliser, une surface de bundle sur TOUTES les routes et une seconde convention de focus. Motif repris, paquet refusé. |
| `react-animated-numbers` | Une transition de chiffre est une interpolation et un `requestAnimationFrame`. Le paquet n'apporte ni format monétaire ni respect de `prefers-reduced-motion` conformes à nos règles. |
| `react-gauge-component` et alternatives | Les jauges Vertex sont servies : la position vient du serveur, le composant ne calcule rien. Une bibliothèque de jauges apporte surtout de la normalisation locale — exactement ce qui est interdit. |

### En attente de mesure

`@tanstack/react-table` et `@tanstack/react-virtual` sont demandés par le
programme pour la chaîne d'options. La décision attend la VOLUMÉTRIE RÉELLE :
la documentation du composant actuel annonce ~12 strikes par échéance et un
budget serveur de 240 lignes toutes échéances confondues. Sous ce volume, la
virtualisation coûte plus qu'elle ne rapporte, et casse la sémantique de table
native que l'accessibilité exige. Le chiffre sera relevé avant de trancher.

---

## Changements livrés

### Lot 1 — primitives (sept commits, branche parente)

| Fichier | Raison |
|---|---|
| `components/widgets/DataTable.tsx` | Remplace 21 familles de classes de table mesurées. Contrat tenu par le type : colonne numérique sans unité impossible, `rowKey` sans défaut, `emptyLabel` obligatoire, `servedOrder` explicitement nul quand le serveur ne trie pas. |
| `components/widgets/LiveDataIndicator.tsx` | Huit états de donnée. AUCUNE latence : le contrat n'en publie pas, un test gèle cette absence. |
| `components/widgets/BulletMetric.tsx` | Mesure quantitative sur axe linéaire, préférée à la jauge dès que plusieurs mesures se comparent. |
| `components/widgets/MicroBars.tsx`, `MicroRange.tsx`, `MiniHeatStrip.tsx` | Micro-visualisations sur positions SERVIES. Aucune normalisation locale. |
| `components/widgets/Skeleton.tsx` | Six squelettes par forme. Réservent la place réelle, donc suppriment le sursaut de mise en page. |
| `components/widgets/ChartFrame.tsx` | Anatomie commune des figures. `equivalent` tabulaire OBLIGATOIRE par le type. |
| `shell/CommandPalette.tsx` | Recherche globale ⌘K, HTML natif. Cherche dans ce que le serveur a publié, et dit quand l'instantané n'est pas chargé. |
| `app/workspace.tsx` | Contexte de travail partagé. L'URL reste propriétaire de ce qu'elle porte ; le contexte porte le reste. |

### Correctifs visuels — ce que seule la capture a montré

| Défaut | Cause exacte |
|---|---|
| Légende de `DataTable` rendue comme une cellule | `display: flex` sur un `<caption>` : un affichage non tabulaire dans une `<table>` est enveloppé dans des boîtes de tableau anonymes. |
| Déclencheur ⌘K en troisième rang | Posé entre la barre de contexte et le ticker, il coupait en deux la surface vitrée continue du bandeau. |

Les tests unitaires passaient dans les deux cas : ils vérifiaient que l'élément
EXISTE et qu'il est nommé, jamais sa place.
