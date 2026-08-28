# Règles d’architecture — obligatoires

Ces règles s’appliquent à toute modification. Une règle contredite bloque le lot et impose soit une correction, soit un ADR accepté avant de poursuivre.

## Forme du système

- Conserver un monolithe modulaire local-first composé de `api`, `worker`, `edge-ibkr`, `web` et `ingress-tradingview`.
- Respecter les propriétaires et dépendances définis dans `docs/02-architecture/MODULE_BOUNDARIES.md`.
- Le domaine Python pur ne dépend jamais de FastAPI, SQLAlchemy, IBKR, Cloudflare, React ni d’un fournisseur d’IA.
- Les adaptateurs traduisent les protocoles externes vers les contrats canoniques ; ils ne calculent aucun verdict.
- Toute dépendance vers un module doit suivre le sens `contrats → domaine → application → adaptateurs/API/UI`. Aucun import inverse ou cyclique n’est accepté.
- Ne pas introduire microservice, Redis, Celery, TimescaleDB, GraphQL, Next.js, broker supplémentaire ou seconde base sans benchmark, motif opérationnel et ADR accepté.

## Autorités uniques

- PostgreSQL est l’autorité persistante du runtime.
- `market_data` possède les observations ; `data_quality` possède fraîcheur, droits et couverture.
- `vertex_core` Python est l’unique autorité des calculs financiers.
- `AdviceEngine` est l’unique autorité du statut et du verdict.
- TypeScript, Pine et l’IA affichent ou expliquent des résultats signés/versionnés ; ils ne les recalculent ni ne les corrigent.

## Contrats et données

- Tout échange entre processus utilise un contrat versionné, validé et rétrocompatible ou une migration explicite.
- Conserver identité canonique, source, droit, unité, devise, timezone, `observed_at`, `received_at`, qualité et fraîcheur jusqu’à l’interface.
- Distinguer systématiquement valeur absente, zéro, donnée périmée, retardée, estimée, théorique, simulée et réelle.
- Utiliser UTC pour le stockage ; convertir pour l’affichage avec une timezone IANA explicite.
- Les écritures, événements, webhooks et jobs doivent être idempotents. Utiliser l’outbox PostgreSQL pour les effets asynchrones persistants.
- Aucune donnée de recherche ou de notebook ne peut écrire dans le runtime live.

## Discipline de changement

- Lire le lot, ses ADR et ses spécifications avant de modifier du code.
- Ne traiter qu’un lot sur une branche `lot/NN-slug` et une PR dédiée.
- Ne pas déplacer une responsabilité entre modules ni changer une technologie structurante sans ADR.
- Générer le client TypeScript depuis OpenAPI ; ne pas maintenir un second modèle manuel concurrent.
- Un contournement temporaire, un deuxième chemin d’autorité ou un fallback silencieux est interdit, même derrière un feature flag.

