# Tests — règles obligatoires

Un lot n’est terminé que si ses preuves sont exécutées depuis un checkout propre et que les commandes/résultats exacts sont reportés dans la PR.

## Discipline

- Écrire un test reproducteur avant toute correction de défaut.
- Tester le comportement public et les invariants ; ne pas figer les détails d’implémentation.
- Utiliser uniquement fixtures synthétiques, minimales et déterministes. Aucune donnée IBKR/TradingView réelle, capture personnelle ou payload de production dans Git.
- Une fixture, un fake ou un mock porte explicitement le statut `SYNTHETIC`/`DEMO` et ne peut franchir une frontière de production.
- Interdire réseau public, horloge réelle et ordre aléatoire non seedé dans les tests ordinaires.
- Aucun test désactivé, flaky relancé jusqu’au vert ou assertion affaiblie pour passer la CI.

## Couverture obligatoire

- Unitaires : contrats, fonctions pures, états et règles.
- Propriétés : invariants financiers avec Hypothesis, cas limites, `NaN`, infini, signe, unité et arrondis.
- Différentiels : QuantLib/SciPy ou oracle indépendant et golden vectors avec provenance.
- Contrats : JSON Schema, OpenAPI, exemples et compatibilité.
- Intégration : PostgreSQL réel, migrations, outbox, TWS simulé et Cloudflare simulé.
- E2E : parcours critiques des 12 pages sur Chromium ; Firefox et WebKit avant release.
- Accessibilité : axe, clavier, focus, zoom, contraste et revue lecteur d’écran des parcours critiques.
- Performance : budgets web/API, chaînes options lourdes, tables 10 000 lignes et backpressure.
- Résilience/chaos : déconnexion, duplication, désordre, redémarrage, timeout, disque faible et dérive d’horloge.
- Sécurité : capacités interdites, auth, injection, traversal, replay, secrets et supply-chain.

## Matrice financière minimale

- `live`, `delayed`, `frozen`, `stale`, `partial`, `offline`, `error` ;
- marché ouvert/fermé, DST, demi-séance, jour férié ;
- actions, ETF, indices, options, devises, multiplicateurs et corporate actions ;
- option exacte : expiration, strike, right, exchange, currency, multiplier et `trading_class` ;
- données absentes, zéro, futures, contradictoires et hors ordre ;
- codes TWS 1100, 1101, 1102, 1300 et 502 ;
- alertes TradingView valides, forgées, vieilles, futures, dupliquées, désordonnées et trop grosses ;
- IA valide, invalide, indisponible et soumise à prompt injection.

## Seuils et sortie

- 100 % des branches des gates, décision, fraîcheur, ledger et contrats critiques.
- Au moins 90 % des branches du cœur financier, 80 % des autres modules backend et 85 % du frontend hors code généré.
- Mutation score au moins 95 % sur les modules critiques, sans mutant dangereux survivant.
- Zéro violation axe critique/sérieuse et zéro vulnérabilité critique/haute exploitable non acceptée.
- Un test rouge, flaky, ignoré ou non exécuté vaut échec ; une absence de preuve vaut `NO-GO`.

