# Intégration IBKR

## Rôle

IBKR est la source principale de marché : contrats, quotes, historique, options, scanner, news et calendrier WSH selon les droits. IBKR ne fournit jamais le portefeuille à Vertex et ne reçoit jamais d'ordre.

## Adaptateur autorisé

Utiliser `ib_async`, version verrouillée, derrière une interface Vertex qui n'expose que : connexion/heure serveur, contrats, chaînes, market data, historique, scanner, news, WSH et annulation des abonnements de données.

Denylist minimale : `placeOrder`, `cancelOrder`, `reqGlobalCancel`, `exerciseOptions`, `reqPositions`, `reqAccountUpdates`, `reqPnL`, `reqOpenOrders`, `reqCompletedOrders`, `reqExecutions` et équivalents async.

## Configuration TWS

- TWS Offline ou IB Gateway compatible ;
- `Enable ActiveX and Socket Clients` activé ;
- `Read-Only API` activé ;
- localhost uniquement, aucun Trusted IP distant ;
- client ID fixe non nul, non Master, par exemple `71` ;
- commencer en paper : TWS `7497` ou Gateway `4002` ;
- ports live : TWS `7496`, Gateway `4001` ;
- aucune publication de ces ports dans Docker, LAN, Tailscale ou Cloudflare.

## Machine d'état

- `1100` : `DOWN`, tous les résultats frais bloqués ;
- `1101` : nouvel epoch et réabonnement complet ;
- `1102` : attendre une observation post-reconnexion avant `HEALTHY` ;
- `1300` : relire le port et reconnecter ;
- EOF/502 : backoff exponentiel avec jitter et verrou de reconnexion.

Chaque observation porte `con_id`, `connection_epoch`, `market_data_type`, `observed_at`, `received_at`, `last_confirmed_at`, `request_id` et `quality_flags`.

## Options

- `reqSecDefOptParams` pour les expirations/strikes ;
- identité complète : `conId`, `tradingClass`, strike, expiry, right, multiplier, currency, exchange ;
- plusieurs `tradingClass` peuvent partager une date ;
- abonnements lazy sur lignes visibles et contrats suivis ;
- budget volontaire de 35–40 requêtes/s et moins de 80 % des lignes disponibles ;
- surface partielle étiquetée avec couverture et âge ;
- les Greeks IBKR sont une observation fournisseur, les Greeks Vertex un calcul distinct.

## Actualités, scanners et calendrier

- détecter les fournisseurs news via API ;
- ingérer headlines live, historique et article uniquement si le droit l'autorise ;
- conserver le provider, article ID, heure, contrat et droit de restitution ;
- scanner : maximum 10 abonnements et 50 contrats par scan, puis quotes séparées ;
- WSH : abonnement Corporate Event Data requis, une demande concurrente à la fois ;
- événements : résultats, dividendes, expirations, splits, spinoffs et conférences selon couverture.

La page Sources & Rapports affiche séparément droits TWS UI, droits API réellement testés, données retardées et capacités absentes.

## Documentation officielle à conserver

- TWS API, introduction et index : https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/
- Téléchargement TWS ou IB Gateway : https://www.interactivebrokers.com/docs/tws-api/doc/download-tws-or-ib-gateway/download-tws-or-ib-gateway
- Adaptateur `ib_async` audité et verrouillé : https://github.com/ib-api-reloaded/ib_async

La documentation IBKR est l'autorité du protocole. `ib_async` est un adaptateur local remplaçable, jamais une justification pour exposer une méthode interdite.
