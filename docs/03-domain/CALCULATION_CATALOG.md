# Catalogue des calculs

Le registre YAML est la source de vérité des calculs activés. Dans ce blueprint, il est un `planning_seed` : aucune ligne n'est runtime-ready avant que le LOT-07 ajoute et valide version, méthode, paramètres, tolérances, hypothèses, criticité, oracles et tests. Les familles listées ci-dessous mais absentes du YAML restent candidates, pas des fonctions autorisées.

## Marché et statistiques

- rendements simples/log, cumuls et annualisation ;
- volatilité réalisée close-to-close et estimateurs OHLC documentés ;
- ATR, gaps, volume relatif, VWAP lorsque les données le permettent ;
- moyennes, momentum, force relative et niveaux avec lookback explicite ;
- breadth, advance/decline, dispersion, corrélation et régimes ;
- bêta, covariance shrinkée et facteurs seulement avec historique suffisant.

## Options

- courbes taux/dividendes, forward et bornes de non-arbitrage ;
- BSM européennes ; arbres/finite differences ou modèle validé pour américaines ;
- IV bid/mid/ask avec échec explicite ;
- delta, gamma, vega, theta, rho ; vanna/vomma/charm après validation ;
- smile, skew, structure à terme et surface avec contrôles d'arbitrage ;
- payoff multi-jambes, gain/perte max, breakevens, débit/crédit, commissions ;
- scénarios spot × temps × IV, puis Monte-Carlo seedé en mode avancé ;
- expositions dollar delta/gamma/vega/theta ;
- GEX toujours accompagné de l'hypothèse de signe dealer.

## Portefeuille et performance

- lots, coût moyen, P&L réalisé/non réalisé et frais ;
- FX daté et résultat par devise ;
- allocation, concentration, exposition delta et scénarios ;
- TWR et XIRR séparés ;
- volatilité, Sharpe/Sortino avec taux/hypothèses, drawdown et récupération ;
- attribution par instrument/secteur/stratégie seulement si les données sont complètes ;
- réel, hypothétique et théorique dans des populations distinctes.

## Backtests

Univers, sociétés radiées, changements de symbole, splits, dividendes, calendriers, quotes tradables, bid/ask options, ajustements OCC, frais, spread, slippage, latence, fills et capacité doivent être point-in-time. Sans chaînes options historiques licenciées, Vertex écrit « simulation théorique ».

## Invariants non négociables

- parité put-call et bornes de prix ;
- monotonicité et convexité appropriées ;
- delta borné, gamma/vega vanilla positifs ;
- aller-retour prix → IV → prix ;
- cohérence analytique/QuantLib/oracle indépendant ;
- conservation et linéarité des agrégations ;
- résultats finis aux extrêmes, maturité zéro et taux négatifs ;
- contraintes et résidus des optimisations ;
- déterminisme, idempotence, fuseaux et calendriers.
