# LOT-13 — Page Marchés

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/03-markets.md`.
- Références : `docs/03-domain/CALCULATION_CATALOG.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/04-integrations/DATA_FUSION.md`, `docs/05-design/CHART_STANDARD.md`, `docs/05-design/ACCESSIBILITY.md` et `docs/06-quality/PERFORMANCE_BUDGETS.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-05 TradingView, LOT-06 Data Fusion, LOT-07 Quant et LOT-09 API/jobs et LOT-10 Design shell.

## Objectif

Livrer `/markets`, une lecture synthétique et traçable du contexte de marché, dominée par une heatmap ou treemap secteurs/instruments et complétée uniquement par le régime, la breadth, la dispersion, la volatilité et les benchmarks utiles.

Périmètre Vertex 1.0 Beta : **DESKTOP ONLY**, testé en `1280×800`, `1440×900`
et `1600×1000` ; `1024×768` est une dégradation laptop optionnelle.
`Mobile UI = LATER`, sans changer les contrats d'univers, de couverture ou de
provenance.

## Non-objectifs

- calculer rendements, breadth, volatilité ou régime en JavaScript ;
- présenter un export TradingView comme un flux live ;
- afficher une carte dont la couverture ou l'univers point-in-time est inconnu ;
- utiliser couleur, surface ou animation comme seule preuve ;
- ajouter des visualisations 3D ou des indicateurs non enregistrés au catalogue.

## Livrables attendus

1. Route `/markets` et sélecteur d'univers/période compact.
2. Bandeau session/régime avec méthode et version.
3. `ChartFrame` ECharts pour heatmap/treemap avec conclusion textuelle, table équivalente et export.
4. Modules breadth/dispersion/volatilité et benchmarks avec provenance.
5. Table sectorielle triée équivalente à la visualisation, avec barres et
   sparklines SVG/CSS accessibles sur desktop.
6. Stories, fixtures et tests performance/visuels/accessibilité.

## Contrats et autorité

Entrées : univers point-in-time, `QuoteSnapshot`, `ScannerResult`, classifications, benchmarks, `MarketRegimeSnapshot`, résultats de breadth, dispersion et volatilité, tous enveloppés par `DataEnvelope`.

- Le serveur fournit valeur, rang, couverture, méthode et `as_of`.
- Le frontend peut filtrer ou changer de représentation, jamais recalculer la valeur financière.
- Les imports de screener portent explicitement `MANUAL_EXPORT` et leur date.
- Toute conclusion textuelle du graphique dérive d'un champ backend ou d'une règle d'affichage non financière testée.

## Interface et états

- `loading` : géométrie stable sans fausse valeur.
- `refreshing` : carte précédente conservée.
- `empty` : univers réellement vide avec cause.
- `partial` : taux de couverture et secteurs manquants affichés.
- `delayed` : badge par source et jamais « live ».
- `stale` : watermark, classement figé et `as_of` exact.
- `offline` : dernière clôture/snapshot connu, daté.
- `error` : couche fautive isolée ; benchmarks ou tableau sains restent accessibles.

## Tests obligatoires

- Unitaires : mapping DTO→série, légende, unités, tri reçu et tableau équivalent.
- Contrats : univers point-in-time, couverture et régime versionné.
- Storybook/visuel : huit états, densités faibles/fortes et trois viewports
  desktop ; `1024×768` seulement si utile comme dégradation laptop.
- E2E : live, partial, delayed, stale, import screener et drill-down instrument.
- Accessibilité : navigation vers l'alternative tabulaire et lecture sans couleur.
- Sécurité : libellés externes échappés, aucun payload brut dans télémétrie.

## Performance, sécurité et accessibilité

- ECharts importé uniquement sur cette route ; absent du bundle initial.
- Filtre local p95 ≤ 100 ms ; interactions ordinaires à 60 FPS sur la fixture de référence.
- Snapshot préparé p95 API ≤ 250 ms et p99 ≤ 750 ms.
- Aucun traitement quantitatif ni décimation non tracée sur le thread UI.
- `ChartFrame` déclare unité, devise, période, source, couverture, méthode, limites et table.
- WCAG 2.2 AA, motifs/signes en complément des couleurs, reduced motion et zéro violation axe critique/sérieuse.

## Critères de sortie mesurables

- 100 % des cartes affichent couverture, `as_of`, source et méthode.
- La table accessible contient le même univers et les mêmes valeurs que la visualisation.
- Aucun export TradingView n'est étiqueté live.
- La treemap et sa table équivalente restent lisibles aux trois viewports desktop,
  sans perte de tri, couverture ou provenance. Aucune capture `390`/`360` ni QA
  mobile n'est requise pour la Beta.
- Budgets Web Vitals, route chunk, FPS et tests E2E respectés.
- Revue humaine validant qu'aucun calcul financier ou second régime n'existe côté client.
