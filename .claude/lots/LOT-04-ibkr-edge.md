# LOT-04 — Edge IBKR d'information

## Références et dépendances

- Références obligatoires : `docs/04-integrations/IBKR.md`, `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md`, `docs/02-architecture/THREAT_MODEL.md` et `docs/06-quality/OBSERVABILITY.md`.
- Dépendances bloquantes : LOT-00 Gouvernance, LOT-01 Toolchain/CI, LOT-02 Contrats et identités, LOT-03 Stockage/qualité/outbox.
- L'adaptateur `ib_async` est verrouillé derrière un port Vertex étroit ; la documentation TWS API officielle reste l'autorité.
- Les essais connectés commencent exclusivement sur TWS/IB Gateway paper, API read-only, loopback, avec un client ID fixe non nul.

## Objectif

Livrer un service edge local, observable et résilient qui extrait le maximum d'informations autorisées par les abonnements IBKR réellement détectés : contrats, quotes, historique, chaînes/options, scanner, actualités et événements WSH. Chaque observation doit conserver son identité exacte, son type live/retardé, son droit, sa couverture, sa fraîcheur et son epoch de connexion avant d'entrer dans le stockage canonique.

## Non-objectifs et interdictions

- envoyer, prévisualiser, modifier, annuler ou exercer un ordre ;
- lire compte, positions, cash, P&L, marge, ordres ouverts/terminés ou exécutions ;
- utiliser les watchlists TWS comme substitut implicite au portefeuille manuel Vertex ;
- exposer le port TWS/IB Gateway au LAN, à Tailscale, à Docker, à Cloudflare ou à
  Internet ; cette interdiction reste absolue quand `Mobile UI = LATER`, et Remote
  Control sur téléphone pilote Claude Code seulement ;
- augmenter automatiquement les limites, contourner le pacing, multiplier les sessions ou masquer une erreur d'entitlement ;
- présenter une donnée delayed, frozen, partielle, mise en cache ou théorique comme live ;
- recopier un article de presse lorsque les droits autorisent seulement son titre ou son lien ;
- calculer un verdict, une stratégie ou un conseil dans l'edge.

Une denylist testée couvre au minimum `placeOrder`, `cancelOrder`, `reqGlobalCancel`, `exerciseOptions`, `reqPositions`, `reqAccountUpdates`, `reqPnL`, `reqOpenOrders`, `reqCompletedOrders`, `reqExecutions` et leurs variantes synchrones/async. Aucun type de domaine lié au compte ne doit être importable depuis le port public de l'adaptateur.

## Livrables attendus

1. Port `IbkrInformationPort` typé et implémentation `IbAsyncInformationAdapter`, sans méthode interdite.
2. Processus `edge-ibkr` local, configuration validée, secrets hors dépôt et contrôle explicite de loopback/read-only/client ID/environnement paper.
3. Machine d'état de connexion versionnée : `STARTING`, `CONNECTING`, `HEALTHY`, `DEGRADED`, `DOWN`, `RECOVERING`, `STOPPED`.
4. Gestion déterministe des codes 1100, 1101, 1102, 1300, 502/EOF, avec nouvel epoch, backoff exponentiel borné, jitter, verrou de reconnexion et arrêt propre.
5. Registre des requêtes et abonnements actifs : propriétaire, priorité, deadline, coût estimé, état, annulation et raison de terminaison.
6. Planificateur de pacing/backpressure partagé, budgets configurables par famille d'appel, limite volontaire globale de 35–40 requêtes/s et plafond de 80 % des lignes de marché détectées.
7. Résolution de contrats et quarantaine des ambiguïtés ; persistance du `conId` et de la symbologie complète.
8. Collecteurs de quotes/snapshots, barres historiques et sessions, avec `market_data_type`, timestamps serveur/local et contrôle de dérive d'horloge.
9. Collecteur options lazy : `reqSecDefOptParams`, qualification exacte, lignes visibles/suivies, snapshots de chaîne et couverture calculée.
10. Collecteur scanner : définitions versionnées, dix scans actifs maximum, cinquante résultats maximum par scan et enrichissement de quotes séparé.
11. Collecteur news : découverte des providers, headlines, historique et corps uniquement selon les droits de restitution ; conservation de provider/article ID/droit.
12. Collecteur WSH : capacité sondée, une demande concurrente maximum, événements et révisions conservés.
13. Sonde d'entitlements et `SourceCapabilitySnapshot` publiant pour chaque capacité `AVAILABLE`, `DELAYED`, `NOT_ENTITLED`, `UNSUPPORTED` ou `ERROR`.
14. Écriture idempotente des `DataEnvelope`, outbox et métriques/healthchecks sans contenu commercial ou secret dans les logs.
15. Simulateur protocolaire et fixtures entièrement synthétiques pour tous les scénarios de tests hors smoke test paper.

## Règles de données et d'autorité

- Toute observation inclut au minimum `event_id`, `source_event_id?`, `request_id`, `connection_epoch`, `received_at`, `as_of`, `market_data_type`, `entitlement_id?`, `quality_flags`, `payload_hash` et l'identité canonique résolue.
- Un symbole seul ne peut jamais produire un `InstrumentId`. Une réponse ambiguë passe en quarantaine et n'alimente aucun calcul.
- Une option est identifiée par `conId`, `tradingClass`, sous-jacent, expiry, strike, right, multiplier, currency et exchange ; une date d'expiration seule est insuffisante.
- Les Greeks IBKR restent des observations fournisseur. Les Greeks et IV Vertex sont calculés ailleurs, avec un `CalculationRecord` séparé.
- Chaque collection publie `expected`, `received`, `valid`, `delayed`, `stale`, `missing`, `coverage_ratio` et `max_age` quand ces notions sont définies.
- Les droits sont évalués par capacité et environnement. La présence d'une donnée dans l'interface TWS n'est jamais utilisée comme preuve d'accès API.
- Un cache antérieur reste consultable avec son `as_of`, mais ne redevient jamais frais après reconnexion sans observation postérieure dans le nouvel epoch.
- Une erreur ou un manque de droit produit un état explicite, jamais une substitution silencieuse par une autre source.

## Résilience et observabilité

- `1100` passe immédiatement l'edge à `DOWN` et bloque tous les nouveaux résultats dépendant du live.
- `1101` invalide les abonnements de l'ancien epoch puis reconstruit seulement ceux encore demandés.
- `1102` ne repasse pas directement à `HEALTHY` : au moins une observation post-reconnexion valide est nécessaire.
- `1300` invalide la configuration de port en cours et exige une reconnexion contrôlée.
- Les files ont une capacité bornée, une politique d'expiration et une priorité explicite ; aucune requête n'attend indéfiniment.
- Les métriques minimales sont : état/epoch, âge du dernier message, dérive d'horloge, requêtes par famille, throttles, lignes utilisées/disponibles, profondeur de file, reconnexions, couverture, erreurs et capacités par statut.
- Les logs structurés utilisent des identifiants techniques et hashes ; ils excluent secrets, corps d'article non redistribuable et données personnelles.

## Tests obligatoires

- Structure/AST : le port public n'expose aucune méthode de la denylist et le module n'importe aucun contrat compte/ordre/position/exécution.
- Unitaires/propriétés : scheduler, budgets, annulation, backoff borné, epochs, timestamps, idempotence, identité et calcul de couverture.
- Contrats : toutes les observations valident `DataEnvelope`; schémas inconnus, décimales flottantes non autorisées, timestamps naïfs et identités incomplètes sont rejetés.
- Options : deux `tradingClass` à même expiry restent distinctes ; multiplicateur/devise/exchange divergents ne fusionnent jamais.
- Pacing/charge : burst, abonnements concurrents, file saturée, annulation et priorité ; aucune émission au-delà des budgets configurés.
- Résilience : 1100 → 1101, 1100 → 1102, 1300, 502, EOF, perte réseau, message dupliqué/désordonné, horloge décalée et arrêt pendant reconnexion.
- Entitlements : live, delayed, frozen, absent, expiré et erreur ; aucun état n'est requalifié silencieusement.
- News/WSH/scanner : droits headline-only, article interdit, provider absent, révision d'événement, seconde requête WSH concurrente et limite de scans.
- Intégration : PostgreSQL réel, transaction + outbox, redémarrage après commit avant ack et rejeu idempotent.
- Sécurité : écoute loopback, secrets expurgés, absence de port publié et test d'échec de configuration si read-only/paper ne peuvent pas être attestés.
- Smoke paper manuel : contrat liquide non ambigu, quote, petit historique, une chaîne bornée, un scanner et capacités news/WSH selon droits ; aucune donnée réelle n'entre dans Git.

## Critères de sortie mesurables

- Zéro méthode compte/ordre/position/exécution dans le port, le graphe d'appels, les routes et les tests d'intégration ; contrôle CI bloquant.
- 100 % des observations persistées portent source, epoch, identité, timestamps, type de délai, qualité et hash ; aucune datetime naïve ni nombre financier flottant.
- Les tests 1100/1101/1102/1300/502 passent sans observation ancien-epoch déclarée fraîche et sans double abonnement résiduel.
- Le harnais de charge n'émet jamais plus que le budget configuré, conserve au moins 20 % de marge sur les lignes détectées et borne chaque file/retry.
- Une chaîne test comportant au moins deux `tradingClass`, données manquantes et lignes retardées publie une couverture exacte et ne porte jamais le libellé « complète ».
- Scanner limité à 10 abonnements/50 résultats, WSH limité à une demande concurrente et dépassements refusés localement avant appel fournisseur.
- 100 % des capacités sondées apparaissent dans la matrice avec statut, délai, `tested_at` et raison exploitable.
- Toutes les écritures résistent à un rejeu d'au moins 10 000 événements synthétiques sans doublon canonique ni perte d'outbox.
- Aucun secret, donnée commerciale brute ni identifiant personnel n'est détecté dans dépôt, logs et artefacts CI.
- Couverture de branches de 100 % sur machine d'état, denylist, fraîcheur, entitlement et pacing ; mutation score conforme à `TEST_STRATEGY.md`.
- Revue humaine sur TWS/IB Gateway paper confirmant read-only, loopback et absence totale de parcours de trading.
