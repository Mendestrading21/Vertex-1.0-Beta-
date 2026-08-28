# LOT-20 — Page Performance

## Références et dépendances

- Fiche produit obligatoire : `docs/01-product/pages/10-performance.md`.
- Références transversales : `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/CALCULATION_CATALOG.md`, `docs/03-domain/UNITS_TIME_AND_PRECISION.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/05-design/CHART_STANDARD.md`, `docs/05-design/UI_STATES.md`, `docs/05-design/ACCESSIBILITY.md` et `docs/06-quality/PERFORMANCE_BUDGETS.md`.
- Dépendances bloquantes : LOT-02 Contrats canoniques, LOT-03 Stockage et qualité, LOT-04 IBKR, LOT-07 Quant, LOT-09 API/jobs, LOT-10 Design shell et LOT-18 Portefeuille.

Le lot ne commence qu'après validation des contrats de ledger manuel, cashflows, frais, FX, benchmarks, populations et `CalculationRecord` versionnés.

## Question à résoudre

Quelle performance ai-je réellement enregistrée, avec quels risques, coûts et contributions, selon quelles données et conventions ?

## Objectif

Livrer `/performance`, une vérité de performance reproductible dominée par des courbes synchronisées de valeur et de drawdown. La page sépare systématiquement brut/net, TWR/XIRR et les populations réel, hypothétique, théorique et démo.

## Non-objectifs

- recalculer rendement, FX, drawdown, Sharpe, volatilité ou attribution en TypeScript ;
- agréger ou comparer silencieusement des populations incompatibles ;
- interpoler une valeur, un FX ou un benchmark manquant sans méthode enregistrée ;
- présenter une simulation théorique comme performance réalisée ;
- lire les comptes, transactions, positions ou exécutions IBKR ;
- remplacer une définition financière par un résumé IA.

## Contrats et autorité

Entrées minimales : `Portfolio`, `CashLedgerEntry`, `PositionLot`, `Transaction`, séries FX datées, benchmark point-in-time et `CalculationRecord` certifiés.

Contrats de page à exposer par OpenAPI :

- `PerformanceSnapshot` : population, période, devise de référence, valeur, cashflows, frais, état de couverture, `as_of` et versions de calcul ;
- `PerformancePoint` : timestamp, capital avant/après cashflow, rendement de sous-période, drawdown, FX et qualité ;
- `MetricDefinition` : identifiant, valeur, unité, période, brut/net, annualisation, taux sans risque, méthode et limites ;
- `ContributionRecord` : dimension, contribution, couverture, résidu, source et méthode ;
- `PerformanceExportManifest` : filtres, populations, hypothèses, identifiants de calcul et hash des fichiers.

Le backend est l'unique autorité de TWR, XIRR, P&L, drawdown, volatilité, Sharpe/Sortino, FX et attribution. Les valeurs sensibles traversent l'API sous forme de chaînes décimales. Toute métrique est liée à un `CalculationRecord`; une couverture insuffisante produit `INSUFFICIENT_DATA`, jamais zéro.

## Livrables desktop

1. `ChartFrame` ECharts synchronisant capital et drawdown sur la même période et le même curseur.
2. Bandeau compact de métriques avec définition, période, unité, brut/net, hypothèses et version ouvrables.
3. Heatmap mensuelle avec table équivalente et distinction explicite des périodes incomplètes.
4. Attribution par instrument, secteur ou stratégie uniquement lorsque le contrat de couverture l'autorise, avec résidu visible.
5. Contrôles de période, devise, benchmark et population dont la sélection ne mélange jamais les séries.
6. Export des données, hypothèses, méthodes, qualités et identifiants de calcul dans un manifeste reproductible.

## Périmètre Vertex 1.0 Beta

- Phase 1 **DESKTOP ONLY** : `1280×800`, `1440×900` et `1600×1000`.
- `1024×768` est une dégradation laptop optionnelle avec modules desktop empilés,
  jamais une vue téléphone.
- Courbes mobiles empilées, liste substitutive téléphone, feuilles basses, bottom
  nav, `MobileActionBar`, gestes tactiles et QA `390`/`360` sont `LATER`.
- Les contrats sémantiques conservent curseur partagé, résumé, métriques, périodes,
  heatmap/table, sélecteurs et export avec exactement les mêmes valeurs et états
  pour l'adaptation future.

## États UI obligatoires

- `loading` : axes et géométrie stables, sans valeur synthétique ;
- `refreshing` : dernier calcul visible avec version et activité discrète ;
- `empty` : ledger réellement vide pour la population et la période choisies ;
- `partial` : dates, FX, frais, benchmarks ou dimensions d'attribution manquants listés ;
- `delayed` : mark courant retardé, sans invalider l'historique réalisé ;
- `stale` : valeur actuelle marquée avec son âge, historique clôturé conservé ;
- `offline` : dernier snapshot certifié consultable et exportable avec son `as_of` ;
- `error` : module fautif isolé, aucune valeur remplacée par zéro ni série inventée.

Un historique incomplet désactive les métriques qui nécessitent la période complète et explique la condition manquante.

## Accessibilité

- Chaque `ChartFrame` fournit question, conclusion textuelle, unité, devise, période, source, fraîcheur, méthode, limites et table complète.
- Capital et drawdown restent distinguables sans couleur ; focus, curseur et plage sélectionnée sont annoncés.
- Table alternative navigable au clavier avec en-têtes associés et libellés de période non ambigus.
- WCAG 2.2 AA, zoom 200 %, reduced motion et cibles interactives suffisantes.
- Vérification NVDA ou VoiceOver du changement de population, de la lecture d'un point et de l'export.
- Zéro violation axe critique ou sérieuse.

## Performance

- Snapshot préparé : p95 API ≤ 250 ms et p99 ≤ 750 ms ; export asynchrone et borné pour les longues périodes.
- Changement de période déjà chargée, survol ou sélection : p95 ≤ 100 ms et interactions ordinaires à 60 FPS.
- ECharts chargé uniquement avec la route `/performance` et absent du bundle initial.
- Décimation éventuelle exécutée côté worker, avec méthode, seuil et points conservés inscrits au contrat.
- Aucun calcul financier, conversion FX ou agrégation de population sur le thread UI.

## Tests obligatoires

- Vecteurs de référence approuvés pour TWR, XIRR, drawdown, récupération, volatilité, Sharpe/Sortino, frais et FX daté.
- Tests de propriétés : conservation des contributions, neutralité d'un cashflow externe sur TWR, reproductibilité et absence de mélange inter-populations.
- Contrats : rejet d'une unité/devise absente, d'une population inconnue, d'une métrique sans méthode ou d'une attribution sans couverture.
- Storybook et régression visuelle : huit états UI, valeurs négatives, grande amplitude, période courte et historique incomplet.
- E2E : cashflow externe, changement FX, frais, benchmark incomplet, passage brut/net, population théorique et export.
- Accessibilité : parité exacte graphique/table et parcours complet sans souris.
- Sécurité : exports sans identifiant de compte, formule injectable, secret ou chemin local.

## Critères de sortie mesurables

- Les vecteurs TWR, XIRR et drawdown correspondent aux références approuvées dans la tolérance documentée du registre de calculs.
- Zéro agrégation entre réel, hypothétique, théorique et démo dans les tests unitaires, de contrat et E2E.
- 100 % des métriques visibles affichent période, unité, brut/net, méthode/version et état de couverture.
- 100 % des points du graphique de référence sont récupérables dans la table ou l'export avec mêmes timestamps et valeurs.
- Un mark live stale laisse l'historique réalisé inchangé et marque uniquement les valeurs dépendantes du mark.
- Les huit états UI, les trois viewports desktop, budgets Web Vitals et scénarios
  E2E passent en CI ; `1024×768` est une dégradation laptop optionnelle et aucune
  QA mobile ne bloque la Beta.
- Revue indépendante confirmant l'absence totale de calcul financier et de décision dans le frontend.
