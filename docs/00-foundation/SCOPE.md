# Périmètre

## Inclus

- actions, ETF, indices de référence et options listées ;
- données de marché IBKR, live ou retardées selon les abonnements ;
- alertes TradingView normalisées et non autoritaires ;
- portefeuille, transactions, cashflows et thèses saisis manuellement ;
- options : chaîne, IV, Greeks, skew, structure à terme, payoff et scénarios ;
- risque, concentration, performance et attribution avec hypothèses visibles ;
- décision canonique, portes de qualité, preuve et explication ;
- application web privée installable sur le bureau, servie uniquement sur la
  machine locale pendant la Beta ;
- 12 pages définies dans `docs/01-product/pages/` ;
- recherche et backtests séparés, sur jeux de données explicitement licenciés.

## Plateformes de Vertex 1.0 Beta

Vertex 1.0 Beta est **desktop only**. La matrice de conception, développement et QA couvre les largeurs bureau/laptop 1280, 1440 et 1600 px. Une largeur de 1024 px peut proposer une dégradation laptop explicite — rail replié, modules secondaires déplacés sous la dominante ou défilement interne maîtrisé — sans devenir une interface mobile.

Mobile : **LATER**. Les contrats sémantiques des pages, données, états, actions, sources, unités, fraîcheur, accessibilité et liens profonds sont conservés afin de ne pas bloquer une phase ultérieure, mais aucun rendu ni parcours Vertex mobile ne fait partie de cette Beta. Sur téléphone, le seul accès prévu est **Claude Remote Control** ; ce contrôle distant n'est pas une UI Vertex.

## Hors périmètre

- passage, modification, annulation, simulation de routage ou exercice d'ordre ;
- synchronisation automatique de compte, positions, P&L ou exécutions IBKR ;
- conseil réglementé, gestion sous mandat ou publication de signaux ;
- scraping contraire aux conditions d'un fournisseur ;
- trading haute fréquence ;
- multi-utilisateur, facturation ou SaaS public ;
- promesse de profit ou probabilité non calibrée ;
- blockchain, microservices ou application native au lancement ;
- toute interface Vertex pour téléphone dans Vertex 1.0 Beta.

## Données commerciales non décidées

L'historique point-in-time des chaînes d'options, quotes bid/ask et ajustements contractuels exige généralement une licence payante. Le fournisseur est une décision humaine unique à prendre avant tout vrai backtest options. Sans cette source, l'interface doit écrire « simulation théorique ».
