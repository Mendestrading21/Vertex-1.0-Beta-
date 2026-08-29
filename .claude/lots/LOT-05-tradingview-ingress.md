# LOT-05 — Ingress et imports TradingView

## Références et dépendances

- Références obligatoires : `docs/04-integrations/TRADINGVIEW.md`, `docs/04-integrations/IBKR.md`, `docs/04-integrations/SOURCE_CAPABILITY_MATRIX.md`, `contracts/json-schema/tradingview-alert-v1.schema.json`, `docs/03-domain/CANONICAL_CONTRACTS.md` et `docs/02-architecture/THREAT_MODEL.md`.
- Dépendances bloquantes : LOT-00 à LOT-04. LOT-04 est requis car toute alerte exploitable doit être revalidée par une observation IBKR postérieure au déclenchement.
- Sources TradingView autorisées : alertes/webhooks officiels, fonctions `request.*()` de Pine documentées et exports utilisateur officiels TXT/CSV.
- Précondition humaine : approuver la création du projet Cloudflare isolé. Commencer sur Workers/Queues Free si les limites revérifiées suffisent ; aucune facturation, publication ou montée d'offre sans commande explicite.

## Objectif

Livrer une entrée publique minimale, résistante aux doublons et aux pannes, qui transforme les alertes Pine en déclencheurs non autoritaires, plus un assistant local d'import des exports TradingView officiels. L'ingress doit conserver le signal original et sa provenance, puis demander une nouvelle observation IBKR et une réévaluation Vertex complète.

## Non-objectifs et interdictions

- considérer le prix, le score, la direction ou le texte d'une alerte comme vérité de marché ou verdict ;
- exécuter un ordre ou appeler une API IBKR de compte, positions, P&L, ordre ou exécution ;
- automatiser un navigateur, scraper TradingView, aspirer News Flow/Calendars ou contourner les limites du plan ;
- supposer qu'une information visible dans l'interface TradingView possède une API consommateur ;
- placer secret, token de compte ou donnée personnelle dans Pine, le corps du webhook, les logs ou Git ;
- faire vivre un calcul financier dans le Worker Cloudflare, la Queue ou le parseur d'import ;
- importer un résultat de stratégie ou de broker comme portefeuille réel ;
- accuser réception avant durabilité dans la Queue, ou ack côté edge avant commit PostgreSQL.

## Livrables attendus

1. Pack Pine versionné : `vertex_market_sensor.pine`, `vertex_company_sensor.pine`, `vertex_macro_sensor.pine` et fonction unique `vertex_alert_contract.pine`.
2. Inventaire documenté des appels `request.security`, `request.financial`, `request.economic`, `request.earnings`, `request.dividends`, `request.splits` et `request.footprint` effectivement utilisés, avec unités, limites et comportement de repaint.
3. Worker Cloudflare minimal : POST/HTTPS, JSON strict, taille maximale 16 Ko, validation d'une capacité de route non journalisée, allowlist IP officielle, fenêtre temporelle et rate limit.
4. Queue durable, dead-letter queue, politiques de retry/expiration et consommateur local HTTP pull sortant ; aucune connexion entrante vers la machine Vertex.
5. Persistance idempotente du payload brut borné, de son hash et d'un `TechnicalSignal` normalisé ; ack seulement après commit.
6. Registre d'alertes autorisées : `alert_id`, script/version, symbole/timeframe attendus, état actif, création, révocation et hash de capacité.
7. Orchestrateur de revalidation : état `RECEIVED` → `PERSISTED` → `WAITING_FOR_IBKR` → `REVALIDATED` ou `BLOCKED`/`EXPIRED`.
8. Demande d'une quote IBKR nouvelle, portant un `connection_epoch` courant et `observed_at >= received_at` du déclencheur, puis lancement du pipeline de qualité/calcul/décision.
9. Assistant d'import avec aperçu et validation pour watchlist TXT, Screener CSV et chart CSV ; mapping d'identité, timezone, timeframe, unités, colonnes et provenance.
10. Rapport de diff/idempotence avant commit d'import, quarantaine des instruments ambigus et snapshot du fichier par hash sans contenu sensible dans les logs.
11. Tableau de santé : dernier webhook, âge de Queue, retries, DLQ, versions Pine, alertes à recréer, imports et taux de revalidation IBKR.
12. Fixtures synthétiques, émulateur Worker/Queue et exemples de payloads sans données commerciales.
13. Estimation du volume d'opérations et alerte de budget, comparées à la tarification officielle vérifiée le jour du lot : https://developers.cloudflare.com/queues/platform/pricing/

## Contrat d'alerte et règles d'authenticité

- Le JSON v1 contient seulement les champs définis par le schéma : `schema`, `alert_id`, `script_version`, `sent_at`, `bar_time`, exchange, ticker, interval, condition, valeurs et unités autorisées.
- Les champs inconnus, types coercibles, valeurs non finies, timestamps sans timezone, payloads trop gros, dates trop anciennes/futures et symboles non résolus sont rejetés ou quarantinés selon le contrat.
- TradingView ne fournit pas de signature applicative personnalisable ; la protection combine HTTPS, capacité de route à forte entropie stockée sous forme de hash, allowlist réseau officielle, registre d'alertes, fenêtre temporelle, rate limit et détection de rejeu. Aucun de ces contrôles ne transforme le webhook en source fiable de prix.
- La clé de déduplication canonique est déterministe et inclut `alert_id`, `script_version`, `bar_time`, `condition` et le hash du payload normalisé.
- Toute modification d'un script ou du contrat impose une nouvelle version et la recréation documentée des alertes TradingView concernées.
- `bar_time` représente la barre analysée ; `sent_at` et `received_at` mesurent le transport. Ils ne sont jamais interchangeables.
- Un signal repaintable ou sur barre non confirmée le déclare explicitement et ne peut pas être élevé silencieusement en signal confirmé.

## Revalidation IBKR obligatoire

Une alerte ne produit jamais directement un `AdviceResult`. Après commit :

1. résolution de l'identité TradingView vers l'`InstrumentId` canonique ;
2. demande d'une observation IBKR fraîche, postérieure à la réception, dans l'epoch courant ;
3. contrôle de droit, délai, session, spread, couverture et fraîcheur ;
4. calculs Python certifiés puis gates de l'unique `AdviceEngine` ;
5. lien de preuve entre alerte originale, quote IBKR et résultat éventuel.

Si l'instrument est ambigu, IBKR absent/retardé/périmé, la session inconnue ou la deadline dépassée, le signal termine `BLOCKED` ou `EXPIRED`. Le dernier cours connu ne sert jamais de validation de remplacement.

## Imports officiels

- Watchlist TXT : aperçu ajout/suppression/collision, résolution par exchange lorsque disponible et snapshot horodaté.
- Screener CSV : conservation du fichier source, date d'export, univers, colonnes, filtres saisis par l'utilisateur et mapping ; les lignes restent un snapshot manuel.
- Chart CSV : symbole, exchange, timeframe, timezone, plage, colonnes OHLCV/indicateurs et version d'import ; aucun indicateur n'est promu en calcul canonique sans reproduction Python.
- Un import identique est idempotent. Un fichier modifié crée une nouvelle révision sans écraser l'original.
- Les formules, cellules actives, chemins, HTML et URLs non sûres sont neutralisés avant aperçu et export ultérieur.

## Tests obligatoires

- Contrat : valide, champ absent/inconnu, mauvais type, nombre non fini, mauvaise unité, >16 Ko, timestamp naïf/vieux/futur et version inconnue.
- Sécurité : méthode autre que POST, mauvais content-type, capacité inconnue/révoquée, IP refusée, rejeu, flood, injection de log et contenu source tentant de donner une instruction.
- Livraison : erreur avant enqueue, enqueue réussi, double livraison, désordre, retry, Queue saturée, DLQ, edge offline et crash après commit avant ack.
- Idempotence : même alerte répétée au moins 100 fois, variantes d'ordre JSON et collisions simulées.
- Revalidation : quote IBKR postérieure valide, antérieure, ancien epoch, delayed, stale, absente, instrument ambigu et deadline expirée.
- Pine : compilation de chaque script, limites `request.*()` sous le plafond du plan ciblé, barres confirmées/non confirmées, timezone/DST et golden payloads conformes au JSON Schema.
- Imports : encodages et séparateurs documentés, CSV hostile, colonne inconnue/manquante, symboles ambigus, doublon, fichier vide/tronqué et réimport identique.
- Architecture : contrôle statique de l'absence de bibliothèque d'automatisation navigateur/scraping et de calcul financier dans Worker/importer.
- Résilience : perte de Cloudflare, edge local arrêté 24 h puis reprise, rotation/révocation de capacité et déploiement Worker N/N-1.

## Critères de sortie mesurables

- 100 % des réponses `202` correspondent à un message durablement écrit en Queue ; zéro ack local avant commit PostgreSQL.
- 10 000 livraisons synthétiques comprenant doublons, désordre et retries produisent exactement le nombre attendu de signaux canoniques, sans perte silencieuse.
- 100 répétitions du même payload produisent un seul `TechnicalSignal` et conservent le compteur/traçage de livraisons.
- Aucune alerte n'engendre un `AdviceResult` sans quote IBKR portant `observed_at >= trigger.received_at`, epoch courant, entitlement acceptable et politique de fraîcheur satisfaite.
- Payloads >16 Ko, timestamps hors fenêtre, capacités invalides/révoquées et versions inconnues sont refusés avant Queue avec métrique sans contenu sensible.
- Chaque script passe la compilation ciblée et publie script/version/timeframe/unités/état de confirmation ; toute modification invalide l'ancienne configuration d'alerte.
- Les trois formats d'import passent aperçu, quarantaine, diff, commit et rejeu idempotent ; aucun symbole ambigu n'entre dans la liste canonique.
- Zéro dépendance ou appel de scraping/browser automation dans l'ingress et les imports ; contrôle CI bloquant.
- Le test de reprise après 24 h offline vide la Queue selon la backpressure IBKR sans dépasser ses budgets et route les expirés sans les requalifier.
- Les dashboards distinguent reçus, dédupliqués, en attente IBKR, revalidés, bloqués, expirés, retries et DLQ, avec alerte sur dérive.
- Revue humaine confirme que TradingView déclenche seulement et qu'IBKR revalide toujours le marché avant tout nouveau résultat.
