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

## Contrat causal S1

### Propriétaire unique de l'état

Une session possède un seul propriétaire de `ConnectionStateMachine`. Dans le
runner continu, l'adaptateur est configuré avec
`manage_connection_state=False` : il journalise les événements asynchrones et
le runner est seul à les appliquer. Pour un appel autonome, l'adaptateur reste
le propriétaire de l'état. Une machine est obligatoire à la construction : il
n'existe aucun mode implicite sans barrière d'état. Les deux chemins ne pilotent
jamais la même machine en parallèle.

Le journal de statut fournisseur (`ProviderStatusJournal`) est matérialisé par
des `ProviderStatusEvent`. Chaque événement global `502`, `1100`, `1101`,
`1102` ou `1300` porte un `journal_id` de session et une `sequence` strictement
croissante. Le couple `(journal_id, sequence)` est la barrière causale ; un
champ d'erreur attaché à une requête reste un fait et ne peut pas remplacer ce
journal ni autoriser une transition.

### Barrière des opérations

Avant chaque appel fournisseur, un `OperationToken` fige le `journal_id`,
`connection_epoch_at_start`, `provider_sequence_at_start` et
`market_update_sequence_at_start`. Les enveloppes utilisent l'epoch du début de
l'opération, jamais un epoch relu après la réponse.

Si le journal, sa séquence ou l'epoch change pendant l'appel, la réponse est
refusée. Pour un snapshot composé de plusieurs enveloppes, le rejet est
atomique : aucune partie du lot n'atteint le puits de persistance. La même
barrière protège les contrats, chaînes, historiques, scanners, actualités et
événements WSH.

Une sonde de capacités capture également un epoch positif unique avant son
préambule. Chaque résultat de snapshot, chacune de ses enveloppes et l'epoch
relu avant publication doivent correspondre exactement à cet epoch. Un
changement entre deux étapes ou un lot mélangeant plusieurs epochs compromet la
sonde entière : aucune matrice n'est publiée.

Après `1102`, la session reste `RECOVERING`. Elle ne redevient `HEALTHY` qu'à
partir d'une opération ultérieure contenant au moins une enveloppe `VALID` et
une mise à jour du ticker reçue après le début de cette opération. Une réponse
`PARTIAL` ou `INSUFFICIENT_DATA`, une valeur déjà présente, ou l'opération dans
laquelle `1102` a été reçu ne ferme pas la récupération.

### Annulation et quarantaine

Seul `CancellationOutcome.CANCELLED`, obtenu après confirmation du fournisseur
**et** accompagné d'un registre de souscriptions revenu à zéro, libère la
souscription et le budget de lignes de l'adaptateur. Le libellé `CANCELLED` seul
n'est jamais une preuve suffisante. Un résultat
`NOT_FOUND`, `FAILED` ou une exception conserve la souscription dans le registre
comme ligne en quarantaine. Après un résultat `NOT_FOUND` ou `FAILED`, le runner
réessaie l'annulation une fois. Une exception ou un second échec interdit la
persistance, arrête le cycle et impose le recyclage de la session avant toute
nouvelle requête. La reconnexion est refusée si la fermeture de session ou
l'absence de souscription résiduelle ne peut pas être prouvée.

### Preuve d'intégration

Le câblage S1 exécute en série, dans `tools/run_checks.sh --integration` et dans
le job PostgreSQL de la CI, les quatre suites `vertex_persistence`, `worker`,
`api` et `edge-ibkr`. Une garde inventorie les répertoires
`tests_integration` non vides et exige leur présence dans les deux chemins. Ce
câblage décrit les contrôles requis ; le verdict de la branche dépend de leur
exécution effective.

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
