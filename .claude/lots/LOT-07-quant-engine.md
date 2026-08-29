# LOT-07 — Moteur quantitatif

## Références et dépendances

- Références obligatoires : `docs/03-domain/CALCULATION_CATALOG.md`,
  `docs/03-domain/calculations/CALCULATION_REGISTRY.yaml`,
  `docs/03-domain/CANONICAL_CONTRACTS.md`,
  `docs/03-domain/UNITS_TIME_AND_PRECISION.md` et
  `docs/03-domain/DATA_QUALITY.md`.
- Décisions applicables : ADR-003, ADR-010 et ADR-011.
- Contrôles transversaux : `docs/06-quality/TEST_STRATEGY.md`,
  `docs/06-quality/PERFORMANCE_BUDGETS.md` et
  `docs/07-delivery/DEFINITION_OF_DONE.md`.
- Dépendances bloquantes : LOT-02 Contrats, identité, unités et temps ; LOT-03
  PostgreSQL, outbox et qualité.

Le lot commence uniquement lorsque les contrats canoniques sont versionnés et que
les observations de test peuvent être reconstruites avec leur provenance. Il ne
dépend d'aucune page et ne doit pas attendre le frontend.

## Objectif

Construire le cœur Python pur qui devient l'unique autorité de tous les calculs
financiers de Vertex. Chaque résultat doit être déterministe, versionné, exprimé
avec des unités explicites, relié à ses entrées et vérifiable par exemples,
propriétés mathématiques et oracle indépendant.

Le lot livre d'abord le socle commun et les familles critiques nécessaires aux
pages ultérieures : statistiques de marché, liquidité, pricing/IV/Greeks et payoff
options, scénarios, expositions de portefeuille manuel et mesures de performance.
Une famille trop large est découpée par ADR sans créer une deuxième autorité.

## Non-objectifs

- collecter des données, appeler IBKR/TradingView, ouvrir une connexion HTTP ou
  écrire directement en base depuis le domaine quantitatif ;
- appliquer des gates, classer une opportunité ou produire un `AdviceResult` ;
- entraîner ou publier un modèle prédictif non couvert par le protocole de
  calibration du LOT-08 ;
- implémenter des produits exotiques, du HFT, un moteur d'exécution ou des ordres ;
- présenter une simulation théorique comme un backtest ou une performance réelle ;
- recopier une formule en TypeScript, SQL, prompt IA ou composant graphique ;
- ajouter Redis, Celery, TimescaleDB ou une dépendance non inventoriée.

## Livrables attendus

1. Package Python `quant` sans dépendance vers FastAPI, SQLAlchemy, React, IBKR ou
   un fournisseur IA, avec API publique minimale et frontières vérifiées.
2. Chargeur validant le registre de calculs : identifiant stable, version, méthode,
   unités, hypothèses, paramètres, tolérances, propriétaire et oracles obligatoires.
3. Fabrique commune de `CalculationRecord` incluant `engine_version`, `code_sha`,
   `input_hash`, entrées sources, avertissements, durée et `result_hash`.
4. Types explicites pour montants, prix, ratios, taux, volatilités, dates, horizons,
   devises et multiplicateurs ; conversions centralisées et refus des unités
   ambiguës.
5. Implémentations initiales enregistrées pour :
   - rendements, annualisation, volatilité, drawdown, ATR, spread et volume relatif ;
   - BSM européen, bornes de non-arbitrage, IV bid/mid/ask, Greeks vanilla et
     aller-retour prix–IV–prix ;
   - prix d'options américaines via méthode QuantLib explicitement configurée ;
   - payoff multi-jambes, débit/crédit, coûts, breakevens, gain/perte max et grille
     spot × temps × IV ;
   - agrégations d'exposition, TWR, XIRR, Sharpe et Sortino avec hypothèses visibles.
6. Interface de scénarios stochastiques enregistrant graine, générateur, paramètres,
   nombre de chemins et limites ; aucune graine implicite en production.
7. Jeux de vecteurs dorés synthétiques, documentation des hypothèses et benchmarks
   reproductibles sur la machine de référence.
8. Suite de tests unitaires, par propriétés, différentiels, de limites, de mutation
   et de performance.

## Autorité, précision et erreurs

- Les entrées doivent être des contrats canoniques certifiés ou des valeurs typées,
  jamais des dictionnaires bruts de fournisseur.
- `Decimal` est conservé aux frontières pour prix, montants, strikes, coûts et
  résultats contractuels. Un solveur numérique peut utiliser un flottant en interne
  seulement si la conversion, la tolérance et la stabilité sont documentées.
- Toute donnée absente reste absente : zéro, `NaN`, infini et valeur manquante ne sont
  jamais interchangeables.
- Un calcul invalide retourne un état typé et une raison stable ; il n'invente ni
  valeur de secours ni dernière valeur silencieuse.
- Calendrier, séance, timezone, day-count, taux, dividendes, style d'exercice,
  settlement et multiplicateur font partie des entrées ou hypothèses versionnées.
- Un résultat dépendant de données `STALE`, `PARTIAL`, `CONFLICT` ou non autorisées
  conserve cet état et ne peut pas être promu par le moteur quantitatif.
- Les calculs lourds exposent une fonction synchrone pure appelée plus tard par le
  worker ; ils ne bloquent jamais directement l'event loop de l'API.

## Tests obligatoires

- Exemples : vecteurs analytiques connus, cas documentés et résultats attendus avec
  tolérance déclarée dans le registre.
- Propriétés Hypothesis : parité put-call, bornes, monotonicité, convexité, delta
  borné, gamma/vega vanilla positifs, conservation et linéarité des agrégations.
- Différentiels : comparaison au minimum avec QuantLib et un second oracle
  indépendant pertinent ; un désaccord est expliqué, jamais moyenné.
- Numériques : aller-retour prix → IV → prix, absence de résultat non fini, résidus
  des solveurs et convergence contrôlée.
- Limites : maturité nulle ou quasi nulle, volatilité nulle/forte, taux négatif,
  strike extrême, spread nul/inversé, données partielles, coûts supérieurs au gain,
  multiplicateurs et devises différents.
- Temps : DST, jours fériés, demi-séances, année bissextile, dates timezone-aware et
  plusieurs conventions de day-count autorisées.
- Reproductibilité : mêmes entrées/version/graine donnent exactement le même hash et
  le même résultat sérialisé.
- Mutation : aucun mutant dangereux survivant sur pricing, IV, payoff, P&L,
  annualisation ou agrégation.
- Architecture : test interdisant au package `quant` les imports réseau, UI,
  persistance, adaptateurs et IA.

## Critères de sortie mesurables

- 100 % des implémentations publiques possèdent une entrée active dans le registre,
  une spécification, des unités, des hypothèses, au moins un oracle et des tests.
- ≥ 90 % de couverture de branches du cœur financier et mutation score ≥ 95 % sur
  les modules critiques, sans mutant dangereux survivant.
- Tous les invariants et golden vectors passent sur les versions Python verrouillées ;
  aucun résultat `NaN`/infini non typé ne traverse une frontière publique.
- 100 % des scénarios stochastiques persistables possèdent une graine et un
  `input_hash` ; deux replays identiques produisent le même `result_hash`.
- Les benchmarks publient p50/p95, mémoire maximale et taille d'entrée ; toute
  régression supérieure à 20 % bloque la fusion jusqu'à explication ou nouveau budget.
- Une recherche automatique et une revue humaine confirment qu'aucune formule
  financière autoritaire n'existe hors du package Python prévu.
- Les tests, la documentation du registre et les contrôles de licence sont verts ;
  toute fonction non encore validée reste explicitement `NOT_IMPLEMENTED` et n'est
  exposée à aucun consommateur.

