# Page 03 — Marchés `/markets`

## Question

Dans quel contexte de marché vais-je analyser les instruments ?

## Dominante et modules

Dominante : heatmap/treemap secteurs et instruments.

1. Session et régime.
2. Carte dominante.
3. Breadth, dispersion et volatilité.
4. Benchmarks avec sparklines.

Action principale : ouvrir un secteur ou instrument.

## Données et logique

Univers point-in-time, quotes IBKR, scanners IBKR, imports screeners TradingView, classifications et benchmarks. Rendements, breadth et régimes sont calculés serveur avec couverture affichée. Les exports TradingView restent des snapshots datés.

## États et adaptation desktop

Watermark en stale, classement figé et couverture visible. Cible Vertex 1.0 Beta : 1280, 1440 et 1600 px. À 1024 px, la carte conserve sa sémantique et réduit sa densité de libellés ; l'alternative tabulaire reste disponible sous la dominante.

Mobile : **LATER**. Les contrats sémantiques de secteurs, classements, filtres, états et sélection sont conservés, sans variante de rendu Vertex pour téléphone.

## Acceptation

- alternative tabulaire identique ;
- aucune couleur sans texte/symbole ;
- lazy-load ECharts ;
- p95 interaction ≤ 100 ms pour le filtre local ;
- E2E live, partial, stale et import screener.
