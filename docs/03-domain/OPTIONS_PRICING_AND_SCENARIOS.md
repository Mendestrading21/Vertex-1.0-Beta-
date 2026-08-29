# Pricing et scénarios options

## But et autorité

Vertex chiffre des observations et des scénarios conditionnels. Il ne recommande
pas une transaction, n'envoie aucun ordre et n'exerce aucune option. IBKR reste
une source de marché en lecture seule ; les positions et quantités éventuelles
sont déclarées manuellement dans Vertex.

Le module Python `vertex_core.options` est l'unique autorité des prix théoriques,
IV, Greeks, payoffs et grilles de scénarios. Les calculs navigateur sont interdits.
Chaque résultat produit un `CalculationRecord` avec version du moteur, snapshot
d'entrée, hypothèses, méthode, paramètres, tolérances, avertissements et preuves.

## Identité et snapshot indivisibles

Aucun calcul ne commence sans :

- sous-jacent canonique et `conId` IBKR ;
- option qualifiée par `conId`, `tradingClass`, échéance, strike, CALL/PUT,
  multiplicateur, devise, exchange, style d'exercice et règlement ;
- livrable et `adjustment_code` lorsque le contrat a été ajusté ;
- quote option et quote sous-jacent compatibles, avec `observed_at`, epoch,
  type live/delayed/frozen et qualité ;
- calendrier de marché, instant d'évaluation UTC, échéance/règlement et convention
  de jour ;
- courbe de taux, dividendes/corporate actions et convention d'annualisation ;
- côté de quote choisi, coûts, slippage hypothétique et source de chaque valeur.

Un symbole, une date d'échéance ou une option « proche de 180 DTE » ne constitue
jamais une identité. Des jambes de devises, multiplicateurs, livrables ou
sous-jacents incompatibles ne sont pas agrégées.

## Trois familles de valeurs séparées

### Observation IBKR

Les ticks `tickOptionComputation` 10/11/12/13 représentent respectivement les
calculs basés sur bid, ask, last et modèle. Les ticks retardés 80/81/82/83 sont
stockés dans des observations différentes. Chaque callback peut contenir IV,
delta, gamma, vega, theta, prix option, valeur actuelle des dividendes et prix
du sous-jacent.

Ces valeurs portent `source=IBKR`, `tick_type`, `market_data_type`,
`observed_at`, `underlying_price` et les champs réellement reçus. Une valeur
sentinelle, non finie ou absente reste `null`, jamais zéro. Les Greeks IBKR ne
sont pas renommés « Greeks Vertex » et ne servent pas d'oracle unique.

### Prix exécutable hypothétique

- achat d'une jambe : ask observable, plus slippage/coûts configurés ;
- vente d'une jambe couverte : bid observable, moins slippage/coûts ;
- liquidation d'une jambe longue : bid ; liquidation d'une jambe courte
  couverte : ask ;
- mid et last sont descriptifs, jamais supposés exécutables ;
- quote crossed, locked non expliqué, périmée, sans taille ou partielle déclenche
  une pénalité ou un blocage selon le profil.

Le mot « prix d'entrée » désigne donc une hypothèse datée et non une offre
d'ordre. Aucun calcul de marge broker ou de pouvoir d'achat n'est effectué.

### Valeur théorique Vertex

- européenne vanilla : modèle analytique validé dans son domaine, avec QuantLib
  et oracle indépendant ;
- américaine vanilla : arbre ou différences finies QuantLib, grille et convergence
  testées ;
- contrat ajusté, dividende discret, règlement particulier ou exercice exotique :
  méthode dédiée validée ou `UNSUPPORTED` ;
- hors domaine, courbe invalide, maturité négative ou prix hors bornes : résultat
  `INVALID`, jamais fallback BSM silencieux.

La valeur théorique explique une sensibilité ; elle ne remplace pas le marché.

## Volatilité implicite

Vertex conserve séparément :

- IV bid, ask, last et modèle observées chez IBKR ;
- IV 30 jours du sous-jacent IBKR, tick 24/générique 106 ;
- IV Vertex résolue depuis chaque côté de quote valide ;
- volatilité historique/réalisée, méthode et fenêtre explicites.

L'IV Vertex exige un prix dans les bornes de non-arbitrage, un bracket de racine,
des courbes valides et une convergence documentée. Les sorties sont des décimaux
annualisés (`0.25`, pas `25`) avec convention de jours. Un échec de résolution,
une IV négative/non finie ou un résidu hors tolérance reste un échec explicite.

Smile, skew et structure à terme affichent couverture, interpolation, extrapolation
et violations. Une surface partielle ne permet ni percentile global ni anomalie
de surface présentée comme certaine.

## Unités des Greeks

Chaque champ encode son unité ; aucun libellé nu « vega » ou « theta » :

- delta par unité de sous-jacent et delta contrat = delta × multiplicateur ×
  quantité manuelle ;
- gamma = variation de delta par unité monétaire de mouvement du sous-jacent ;
- vega brut par variation de volatilité `1.0`, plus vue dérivée par point de
  volatilité `0.01` ;
- theta brut selon temps du modèle, plus conversion par jour calendaire ou de
  séance explicitement nommée ;
- rho par variation de taux `1.0`, plus conversion par point de base `0.0001` ;
- expositions monétaires toujours accompagnées de multiplicateur, quantité,
  devise et taux FX daté.

Les approximations delta/gamma/vega servent seulement au voisinage local et sont
étiquetées. Une grande variation spot, temps ou IV impose un repricing complet.

## Payoff générique à l'échéance

Pour chaque jambe `i`, quantité signée `q_i` (positive longue, négative courte),
prime par unité `p_i`, multiplicateur `M_i` et payoff intrinsèque `h_i(S_T)` :

\[
P\&L_T(S_T)=\sum_i q_i M_i\,[h_i(S_T)-p_i]-F
\]

où `F` regroupe les coûts positifs. Cette formule décrit l'échéance seulement.
Avant échéance, Vertex reprice chaque jambe avec temps et IV restants. Taxes,
assignment précoce, pin risk, gap, impossibilité de clôturer, exercice automatique,
corporate action et variation de liquidité sont des risques séparés.

## CALL et PUT longs

Pour un CALL long de strike `K`, débit total `D = prime × M + frais` :

\[
P\&L_T=M\max(S_T-K,0)-D
\]

- perte maximale théorique : `D` ;
- breakeven à l'échéance : `K + D/M` ;
- gain théorique non borné si le sous-jacent n'a pas de plafond ;
- avant échéance : sensibilité IV/temps et liquidité restent déterminantes.

Pour un PUT long :

\[
P\&L_T=M\max(K-S_T,0)-D
\]

- perte maximale théorique : `D` ;
- breakeven : `K - D/M` s'il reste dans le domaine du sous-jacent ;
- gain maximal théorique pour un actif planché à zéro : `KM-D` ;
- contrat cash-settled, exercice européen ou livrable ajusté utilise ses propres
  règles au lieu de cette simplification.

## Stratégies multi-jambes à risque défini

Le catalogue initial autorise seulement :

- `BULL_CALL_DEBIT` : CALL long `K1` + CALL court `K2`, même sous-jacent,
  échéance, livrable et multiplicateur, avec `K1 < K2` ;
- `BEAR_PUT_DEBIT` : PUT long `K2` + PUT court `K1`, mêmes contraintes,
  avec `K1 < K2` ;
- `LONG_STRADDLE` et `LONG_STRANGLE` : toutes les jambes longues ;
- vertical crédit uniquement après preuve formelle que la jambe longue couvre
  chaque contrat court sur tout le domaine et que la perte maximale est finie.

Pour un vertical débit de largeur `W`, débit total `D` coûts inclus : perte max
`D`, gain max `WM-D`. Le bull call casse à `K1 + D/M`; le bear put à
`K2 - D/M`. Si `D <= 0`, `D >= WM`, quotes incohérentes ou jambes non appariées,
la structure est rejetée plutôt que corrigée.

Avant tout scénario multi-jambes, le vérificateur :

1. groupe les jambes par identité économique exacte ;
2. interdit toute quantité courte résiduelle non protégée ;
3. construit les morceaux de payoff à tous les strikes et dans les deux queues ;
4. démontre une perte maximale finie, coûts compris ;
5. signale assignment américain, ex-dividende, expiration/pin et settlement ;
6. refuse calendar, ratio, broken-wing ou combinaison inconnue tant qu'un profil
   séparé n'a pas été validé.

Une jambe courte n'existe dans Vertex que comme composante inséparable d'une
structure certifiée `DEFINED_RISK`. Aucune vente nue, aucun legging et aucun
ordre jambe par jambe.

## Grilles de scénarios

Une grille certifiée croise au minimum :

- spot absolu et chocs relatifs, incluant strikes/breakevens ;
- maintenant, jalons de revue et approche de l'échéance ;
- IV inchangée, parallèle plus/moins, et scénarios skew/terme seulement si la
  surface est assez couverte ;
- taux/dividendes de base et stress explicitement versionnés ;
- bid/ask/slippage/liquidité et coûts ;
- événements confirmés avant horizon.

Toutes les jambes sont repricées sur le même snapshot cohérent. La grille montre
P&L par jambe et total, valeur temps, Greeks, gain/perte max, breakevens,
hypothèses, inconnues et état de qualité. Elle ne transforme pas un scénario en
probabilité. Une probabilité n'est jointe que par le pipeline de calibration
hors échantillon prévu ailleurs.

## Anomalies options : limites d'interprétation

Volume, OI, IV et Greeks enrichissent le contexte mais ne révèlent pas : côté
acheteur/vendeur, ouverture/fermeture, hedge, roll, spread, intention ou identité
de l'acteur. L'OI n'est pas traité comme une mesure intraday. Le volume CALL
n'est pas automatiquement haussier et le volume PUT n'est pas automatiquement
baissier.

Un `OptionAnomalySnapshot` conserve donc le tick, sa portée, son `as_of`, le
type live/delayed, la couverture et les interdictions d'inférence. Un signal
`WARMING_UP`, partiel, hors droits ou sans population historique ne qualifie
aucune stratégie.

## Portefeuille manuel

Les scénarios de position utilisent seulement les lots et quantités saisis ou
importés manuellement dans Vertex. Aucun appel IBKR de compte, positions, cash,
marge, P&L, ordres ou exécutions n'est autorisé. Un portefeuille absent ne peut
pas être reconstitué depuis des données de marché.

## Validation minimale

- bornes de non-arbitrage, parité put-call et monotonicité/convexité ;
- prix → IV → prix dans la tolérance, échecs et extrêmes inclus ;
- comparaison analytique, QuantLib et oracle indépendant ;
- convergence de grille américaine et tests près dividende/exercice ;
- linéarité de somme des jambes et payoff exact à chaque rupture ;
- preuve automatique de risque borné pour toute jambe courte ;
- bid/ask crossed, quote stale/delayed, multiplicateur/devise/livrable incohérent ;
- dates zéro, DST, jours fériés, expiration, taux négatif et volatilité extrême ;
- tests propriétés et mutation sur perte maximale, breakevens et interdiction
  de vente nue ;
- aucun test ne crée, prévisualise ou envoie un ordre, même en paper.

## Sources primaires

- IBKR, Greeks et IV options : https://interactivebrokers.github.io/tws-api/option_computations.html
- IBKR, types de ticks : https://interactivebrokers.github.io/tws-api/tick_types.html
- IBKR Campus, chaînes options : https://ibkrcampus.com/campus/ibkr-quant-news/handling-options-chains/
- IBKR Campus, abonnements de marché : https://ibkrcampus.com/docs/general/market-data-subscriptions/introduction
- OCC, document courant sur les caractéristiques et risques : https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document
- OCC/OIC, volatilité et Greeks : https://www.optionseducation.org/advancedconcepts/volatility-the-greeks
- Cboe Options Institute, calculateur prix/Greeks : https://www.cboe.com/optionsinstitute/tools/options_calculator/
- Cboe Options Institute, stratégies de spreads : https://www.cboe.com/optionsinstitute/courses/spread-strategies/

Les anciennes pages `interactivebrokers.github.io` sont utilisées pour les
tables TWS détaillées encore référencées ; IBKR Campus reste l'autorité courante
et toute divergence doit être résolue en faveur de sa documentation la plus
récente.

