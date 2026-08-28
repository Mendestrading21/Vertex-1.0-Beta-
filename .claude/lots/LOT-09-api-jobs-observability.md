# LOT-09 — API, jobs, accès et observabilité

## Références et dépendances

- Références obligatoires : `docs/02-architecture/MODULE_BOUNDARIES.md`,
  `docs/02-architecture/DATA_FLOW.md`, `docs/02-architecture/LOCAL_FIRST_DEPLOYMENT.md`,
  `docs/02-architecture/THREAT_MODEL.md`, `docs/06-quality/OBSERVABILITY.md`,
  `docs/06-quality/SECURITY_CONTROLS.md` et
  `docs/06-quality/PERFORMANCE_BUDGETS.md`.
- Décisions applicables : ADR-001, ADR-002, ADR-006, ADR-009 et ADR-010.
- Dépendances bloquantes : LOT-03 PostgreSQL/outbox/qualité et LOT-08 Gates,
  calibration et `AdviceEngine`. Les sources des LOT-04 à 06 sont consommées à
  travers leurs contrats, jamais par couplage direct de l'API.

## Objectif

Exposer les cas d'usage autorisés par une API FastAPI privée, documentée par une
OpenAPI reproductible, et exécuter les traitements asynchrones via l'outbox
PostgreSQL. Livrer en même temps l'authentification applicative, le canal SSE léger,
les contrôles réseau et une observabilité bout en bout sans données sensibles.

## Non-objectifs

- rendre l'API publique, utiliser Tailscale Funnel ou considérer le réseau privé
  comme une authentification suffisante ;
- exposer l'interface produit à un téléphone ou via Tailscale Serve pendant la
  phase Vertex 1.0 Beta ; cet accès applicatif est `LATER` ;
- exposer ordres, exécutions, compte, positions ou portefeuille IBKR ;
- calculer dans les handlers HTTP, dupliquer le domaine en schémas ad hoc ou lancer
  une tâche CPU longue dans l'event loop ;
- utiliser SSE comme vérité durable ou envoyer des payloads financiers complets dans
  les notifications ;
- ajouter GraphQL, WebSocket généraliste, Redis, Celery ou TimescaleDB sans preuve et
  ADR ;
- exporter contenu d'actualité, thèse, portefeuille ou secret vers un SaaS de logs ;
- masquer un échec de source, de job ou de lecture derrière un cache.

## Livrables attendus

1. Application FastAPI séparant transport, cas d'usage et domaine, avec injection de
   dépendances et transactions explicites.
2. API REST versionnée pour snapshots, instruments, informations fusionnées,
   calculs, verdicts, portefeuille manuel, thèses, santé et administration locale ;
   seules les capacités prévues au périmètre sont présentes.
3. OpenAPI générée de façon déterministe, exemples synthétiques valides/invalides,
   contrôle de compatibilité et mécanisme de génération du client TypeScript du
   LOT-10.
4. Écritures idempotentes avec clé client, contrôle de concurrence et audit ; toute
   mutation métier crée son événement outbox dans la même transaction.
5. Worker PostgreSQL utilisant lease, `FOR UPDATE SKIP LOCKED`, tentatives bornées,
   backoff, échéance, état terminal/quarantaine et handlers idempotents.
6. Canal SSE authentifié publiant uniquement identifiant, type, version et curseur ;
   le client recharge ensuite le snapshot canonique par REST.
7. Authentification WebAuthn/passkey, session courte renouvelable, révocation,
   procédure de récupération locale et séparation des rôles utilisateur/admin.
8. Accès applicatif local destiné au poste desktop de phase 1 ; aucun accès
   téléphone ni exposition de l'interface par Tailscale Serve. Services métier et
   base restent privés, et TWS demeure lié à `127.0.0.1`. Les contrats OpenAPI
   gardent leur sémantique indépendante du terminal pour `Mobile UI = LATER`.
9. Protections HTTP : cookie `Secure`/`HttpOnly`/`SameSite`, CSRF, CORS fermé, CSP,
   validation stricte, limites de taille/débit, timeouts et en-têtes de sécurité.
10. OpenTelemetry cohérent sur API/worker/edge/ingress, logs JSON expurgés, endpoint
    Prometheus privé, traces corrélées et tableaux/alertes définis dans la
    documentation d'exploitation.
11. Endpoints distincts de liveness, readiness et diagnostic authentifié ; readiness
    vérifie les dépendances requises sans divulguer de secret.
12. Tests de contrats, PostgreSQL réel, concurrence, résilience, sécurité, charge et
    observabilité.

## Contrats API et sémantique des jobs

- Les schémas publics réutilisent ou projettent explicitement les contrats
  canoniques. Une projection ne change ni unité, ni précision, ni sémantique.
- Prix, montants et ratios sensibles restent des chaînes décimales ; les timestamps
  sont UTC et timezone-aware.
- Chaque réponse de snapshot indique `as_of`, qualité, délai, couverture, provenance
  et identifiant de trace. Les erreurs utilisent des codes stables et actionnables.
- Les listes sont paginées avec curseur stable ; aucun endpoint illimité pour chaînes
  options, news ou historique.
- La livraison des jobs est au moins une fois. L'effet métier est rendu idempotent par
  clé unique et transaction, jamais qualifié d'« exactly once ».
- `LISTEN/NOTIFY` ne fait que réveiller : une notification perdue ne perd aucun job.
- Un lease expiré peut être repris ; une ancienne tentative ne peut pas écraser le
  résultat d'une tentative plus récente.
- Le SSE signale une invalidation. Après reconnexion ou trou de curseur, le client
  recharge l'état ; aucune décision ne dépend de la réception parfaite du flux.

## Observabilité et sécurité

- Tous les composants propagent `trace_id`, `event_id`, version de calcul et hash de
  configuration lorsqu'ils existent.
- Les métriques couvrent fraîcheur/couverture, outbox, durée et échecs des calculs,
  API p50/p95/p99, DB, reconnexions/pacing IBKR, Queue/DLQ, disque, backup et dérive
  d'horloge.
- Aucun ticker, texte utilisateur, URL d'article, identifiant de portefeuille ou ID
  de session ne devient label métrique à forte cardinalité.
- Les logs sont testés contre secrets, cookies, payloads WebAuthn, données de compte,
  textes de thèse et corps d'actualité.
- Les endpoints d'administration exigent authentification récente, autorisation et
  audit ; aucun diagnostic public ne révèle versions internes ou topologie.
- Une perte d'authentification ferme SSE et REST sans effacer l'état local déjà
  affiché ; le frontend devra marquer cet état comme non rafraîchissable.

## Tests obligatoires

- Contrats : golden OpenAPI, exemples positifs/négatifs, valeurs décimales, enums,
  pagination, compatibilité et erreurs stables.
- Intégration sur PostgreSQL réel : atomicité métier+outbox, rollback, concurrence de
  plusieurs workers, lease expiré, retry, ordre inversé et job poison.
- Propriété d'idempotence : N livraisons d'un même événement produisent un seul effet
  métier observable et un audit cohérent.
- API : contrôle d'autorisation par route, limites de taille/débit, timeout,
  validation stricte et absence de calcul CPU sur la boucle événementielle.
- SSE : reconnexion, curseur ancien/inconnu, duplication, ordre inversé, expiration de
  session et rechargement REST après invalidation.
- WebAuthn/session : enrollment, authentification, replay, challenge expiré, origine
  incorrecte, révocation, CSRF et récupération documentée.
- Observabilité : propagation de trace, métriques attendues, alertes synthétiques et
  tests de redaction des journaux.
- Charge/résilience : source lente, DB brièvement indisponible, backlog, arrêt brutal
  du worker et reprise sans perte ni double effet.
- Architecture/sécurité : aucune route ou dépendance ordre/compte/position/exécution
  IBKR ; ports et exposition conformes au threat model.

## Critères de sortie mesurables

- Le document OpenAPI est reproductible bit à bit, passe le contrôle de compatibilité
  et permet de générer un client TypeScript sans édition manuelle.
- 100 % des routes exigent l'autorisation prévue ; seuls liveness et les fichiers PWA
  explicitement publics répondent sans session.
- Sous la fixture de charge de référence, lecture snapshot cached p95 ≤ 250 ms et
  p99 ≤ 750 ms, taux d'erreur ≤ 1 %, sans tâche longue CPU dans l'event loop.
- Avec au moins quatre workers concurrents et 1 000 événements dont 10 % dupliqués,
  aucun événement durable n'est perdu et chaque effet métier idempotent apparaît une
  seule fois.
- Une perte de `NOTIFY`, un restart API et un restart worker séparés sont récupérés à
  partir des tables sans intervention ni verdict contradictoire.
- 100 % des réponses financières portent `as_of` et état de qualité ; 100 % des
  traces de décision relient snapshot, calculs et `AdviceResult`.
- Zéro secret, cookie, donnée de compte IBKR ou payload financier complet détecté
  dans logs, métriques et traces des tests de redaction.
- Aucune voie distante vers l'interface produit n'est livrée dans Vertex 1.0 Beta ;
  aucun service métier, base ou TWS n'écoute une interface publique. Remote
  Control officiel, lorsqu'il est utilisé depuis un téléphone, pilote Claude Code
  seulement et n'expose pas Vertex.
- Les alertes initiales de `OBSERVABILITY.md` sont déclenchables par tests ou fixtures
  et renvoient vers un runbook.
