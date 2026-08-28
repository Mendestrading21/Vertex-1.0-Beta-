# Sonde de droits et capacités IBKR

## Question résolue

La sonde ne demande pas « quel abonnement le compte semble posséder ? ». Elle
répond, pour un utilisateur TWS/IB Gateway et un instrument précis : quels
champs l'API délivre réellement, avec quel type de marché, à quel instant, sous
quelles limites et avec quelle preuve.

Le résultat est opérationnel et périssable. Il ne remplace ni les conditions
des exchanges ni le Market Data Assistant IBKR. Une donnée visible dans TWS ne
prouve pas à elle seule qu'elle est disponible par API.

## Frontière de sécurité

- connexion locale TWS/IB Gateway, API read-only, client ID fixe non nul ;
- port loopback uniquement ; aucune route HTTP publique vers IBKR ;
- méthodes autorisées : heure/connexion, contrats, définitions de chaîne,
  market data, historique et annulation des abonnements de données ;
- méthodes compte, positions, P&L, marge, ordres, exécutions, exercice et
  `whatIfOrder` interdites par le port, l'AST et la CI ;
- aucun identifiant de compte dans le contrat de sonde ;
- aucun achat/modification d'abonnement automatisé ; Vertex indique seulement
  le manque et renvoie vers le Market Data Assistant ;
- le portefeuille reste déclaré manuellement dans Vertex.

## Manifeste d'autorité

`manifests/ibkr-market-data-capabilities.yaml` définit les requêtes, callbacks,
ticks, dépendances, limites et règles d'interprétation. Le code généré ou validé
depuis ce manifeste ne peut ajouter une capacité non revue.

Statuts canoniques :

- `AVAILABLE` : preuve positive dans le type de marché attendu ;
- `DELAYED` : donnée reçue en delayed/delayed-frozen, jamais requalifiée live ;
- `NOT_ENTITLED` : refus fournisseur ou absence démontrée du droit requis ;
- `UNSUPPORTED` : API/documentation ne fournit pas cette capacité ;
- `ERROR` : sonde non concluante à cause de connexion, pacing, timeout ou erreur ;
- `MANUAL_EXPORT` : réservé à une capacité officiellement exportable, non utilisé
  pour simuler une capacité IBKR automatique.

`ERROR` et timeout ne signifient jamais `NOT_ENTITLED`. Absence d'un tick pendant
une courte fenêtre ne constitue pas à elle seule une preuve de non-abonnement.

## Prérequis locaux

L'utilisateur choisit dans la configuration locale :

1. un sous-jacent liquide et son `conId` exact ;
2. une option liquide qualifiée par `conId`, `tradingClass`, expiry, strike,
   right, multiplicateur, devise et exchange ;
3. la session attendue et l'environnement paper/live-information ;
4. l'autorisation éventuelle de tester un fallback delayed ;
5. les budgets maximaux de lignes et de requêtes.

Aucun symbole ou contrat « populaire » n'est codé en dur. Si l'identité ou la
session est ambiguë, la sonde s'arrête.

## Séquence bornée

### 1. Pré-vol

- vérifier connexion, heure serveur, dérive d'horloge et epoch ;
- mesurer les abonnements Vertex actifs et réserver au moins 20 % des lignes
  détectées/paramétrées ;
- refuser si une reconnexion, une autre sonde ou un incident pacing est actif ;
- créer `probe_id`, deadline, budget et journal de preuves.

### 2. Définition de chaîne

Appeler `reqSecDefOptParams` pour le sous-jacent, recevoir exchanges,
`tradingClass`, multiplicateurs, expirations et strikes, puis qualifier le
contrat échantillon. Une réponse positive prouve la capacité de définition,
pas le droit aux quotes de toute la chaîne.

La sonde ne souscrit jamais toute une chaîne. Elle utilise un sous-jacent et une
option exacts, puis annule chaque ligne dans un `finally`.

### 3. Sous-jacent live

Demander `reqMarketDataType(1)`, puis un stream borné du sous-jacent. Capturer
ticks bid/ask/last/tailles, callback `marketDataType`, timestamps et erreurs.
Le type callback ou tick réel l'emporte sur l'intention de requête.

### 4. Option live et calculs

Souscrire l'option avec les génériques nécessaires, au maximum
`100,101,104,105,106`. Capturer séparément :

- top-of-book/volume du contrat ;
- calculs option 10/11/12/13 : IV et Greeks bid/ask/last/modèle ;
- CALL/PUT volume 29/30 demandé par 100 ;
- CALL/PUT open interest 27/28 demandé par 101 ;
- volatilité historique 23 demandée par 104 ;
- volume option moyen 87 demandé par 105 ;
- IV 30 jours du sous-jacent 24 demandée par 106.

Les Greeks live nécessitent les droits live de l'option **et** du sous-jacent.
L'erreur 10090 peut donc signifier une capacité partielle : les quotes reçues
restent observées, mais les Greeks manquants restent `NOT_ENTITLED` ou `ERROR`
selon la preuve.

### 5. Delayed optionnel

Si le live est refusé et si la configuration l'autorise, demander explicitement
le type 3. Le callback et les ticks retardés 66–76 et 80–83 sont enregistrés
comme `DELAYED`. Les génériques disponibles en delayed sont plus limités ; leur
absence n'est pas extrapolée.

Le type 2/4 est frozen/delayed-frozen et n'est pas une preuve de fraîcheur. Une
source delayed peut informer une page de diagnostic mais ne franchit aucune
gate exigeant du live.

### 6. Annulation et publication

Annuler sous-jacent et option, attendre confirmation locale, libérer les lignes
et publier un snapshot immuable par champ. Le snapshot inclut requête, callback,
tick, type de marché, `observed_at`, erreur éventuelle, epoch, latence et
expiration de la preuve.

## Interprétation des ticks

| Besoin | Requête/callback | Limite obligatoire |
|---|---|---|
| Bid/ask/last/tailles | ticks par défaut 0–9 | agrégés, pas tick-by-tick options live |
| Greeks/IV option | 10/11/12/13 | base bid/ask/last/modèle distincte |
| Greeks delayed | 80/81/82/83 | jamais mélangés aux ticks live |
| Volume contrat | tick 8 | cumul/sémantique et `as_of` conservés |
| Volume CALL/PUT | générique 100 → 29/30 | portée fournisseur, pas sens du trade |
| OI CALL/PUT | générique 101 → 27/28 | pas une mesure intraday d'ouverture |
| HV sous-jacent | générique 104 → 23 | fenêtre/méthode IBKR, pas HV Vertex |
| Volume option moyen | générique 105 → 87 | disponibilité dépendante du produit |
| IV sous-jacent 30 j | générique 106 → 24 | estimation IBKR, pas IV du contrat |
| Chaîne | `reqSecDefOptParams` | définition seulement, quotes séparées |

Une valeur `-1`, sentinelle, non finie ou absente n'est jamais convertie en
zéro. Le last peut être ancien ou hors spread. Volume et OI ne révèlent ni
acheteur/vendeur, ni ouverture/fermeture, ni hedge, roll ou spread.

## Erreurs et raisons

- 100 : cadence > 50 messages/s ; sonde `ERROR`, refroidissement et aucun retry
  immédiat ; Vertex vise 35–40/s maximum ;
- 101 : maximum de tickers ; `ERROR/CAPACITY_EXHAUSTED`, aucune éviction opaque ;
- 354 : live non souscrit pour l'instrument ; preuve `NOT_ENTITLED` du live ;
- 10090 : partie des données non souscrite ; statut par champ, jamais global ;
- 10186 : live non souscrit et delayed non activé ; live `NOT_ENTITLED`, delayed
  encore inconnu ;
- 10197 : session concurrente ; `ERROR/COMPETING_SESSION`, pas manque de droit ;
- 1100/1101/1102/1300/502 : appliquer la machine d'état IBKR et abandonner la
  sonde de l'ancien epoch.

Les textes fournisseurs complets restent dans un log local expurgé ; l'API
expose un `reason_code` stable et un résumé sans secret.

## Pacing et fraîcheur

- une seule sonde active ;
- deux lignes simultanées par défaut, jamais plus de 80 % de la capacité restante ;
- 35–40 messages/s maximum local, même si TWS accepte jusqu'à 50 ;
- timeout par étape et deadline totale configurés, aucun retry non borné ;
- backoff avec jitter sur erreur transport, pas sur refus d'entitlement ;
- résultat live valable seulement pour l'instrument, venue, type de donnée,
  utilisateur technique, environnement et epoch testés ;
- re-sonde au démarrage, changement d'epoch/configuration, erreur d'entitlement
  et cadence périodique raisonnable, jamais par page ou par contrat affiché ;
- une capacité périmée devient inconnue pour les gates et est re-sondée ; le
  dernier snapshot reste visible comme historique.

## Tests et critères de sortie

- simulateur : tous ticks 0–13, 23/24, 27–30, 80–83, 87 et champs manquants ;
- matrices live/delayed/frozen/delayed-frozen, marché ouvert/fermé, option liquide
  ou sans trade, sous-jacent live + option absente et inverse ;
- erreurs 100/101/354/10090/10186/10197 et déconnexion pendant chaque étape ;
- deux `tradingClass` à même échéance ne sont jamais fusionnées ;
- 100 % des capacités publiées portent statut, champ/tick de preuve, type de
  marché, `tested_at`, `expires_at`, epoch et raison ;
- aucune sonde ne dépasse deux lignes par défaut, 80 % de capacité ni 40 messages/s ;
- toutes les subscriptions sont annulées après succès, timeout, exception ou
  déconnexion ;
- delayed/frozen ne satisfait jamais une politique live dans les tests mutants ;
- aucun appel de compte, position, ordre, exécution, marge ou exercice dans le
  graphe d'appels ; contrôle CI bloquant ;
- smoke test manuel paper/live-information avec données non persistées dans Git,
  comparaison des capacités à l'affichage TWS et au Market Data Assistant.

## Sources officielles

- IBKR, types de ticks : https://interactivebrokers.github.io/tws-api/tick_types.html
- IBKR, Greeks options : https://interactivebrokers.github.io/tws-api/option_computations.html
- IBKR, types live/frozen/delayed : https://interactivebrokers.github.io/tws-api/market_data_type.html
- IBKR, codes d'erreur : https://interactivebrokers.github.io/tws-api/message_codes.html
- IBKR Campus, lignes de marché : https://ibkrcampus.com/docs/general/market-data-subscriptions/market-data-lines/introduction
- IBKR Campus, prérequis d'abonnement API : https://ibkrcampus.com/docs/general/market-data-subscriptions/introduction
- IBKR Campus, chaînes options : https://ibkrcampus.com/campus/ibkr-quant-news/handling-options-chains/

