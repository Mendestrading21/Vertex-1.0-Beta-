---
paths:
  - "apps/api/**/*.py"
  - "apps/worker/**/*.py"
  - "apps/edge-ibkr/**/*.py"
  - "packages/python/**/*.py"
  - "tests/**/*.py"
---

# Python — règles obligatoires

## Langage et types

- Python 3.13, formatage/lint Ruff et mypy strict ; ne pas neutraliser une règle globalement pour corriger un fichier.
- Toute API publique est typée. Éviter `Any`; l’isoler à la frontière d’une bibliothèque non typée et valider immédiatement.
- Utiliser des modèles Pydantic stricts aux frontières et des types de domaine immuables lorsque possible.
- Aucun dictionnaire libre ne traverse les frontières métier critiques.

## Numérique, temps et identité

- Utiliser `Decimal` pour argent, prix contractuels, strikes et quantités définis comme décimaux par le registre.
- Les flottants sont admis pour calcul scientifique interne seulement avec conversion, tolérance, domaine et traitement de `NaN`/infini explicites.
- Toute date/heure est timezone-aware ; stockage et calcul en UTC, calendrier de marché et timezone IANA explicites.
- Ne jamais identifier un instrument par ticker seul. Utiliser l’identité canonique incluant les champs nécessaires aux options.
- Ne jamais confondre `None`, zéro, chaîne vide, valeur non autorisée ou valeur périmée.

## Domaine et effets de bord

- Les fonctions de domaine sont déterministes et sans accès réseau, base, horloge système ou variable d’environnement implicite.
- Injecter horloge, identifiants, clients et configuration ; ne pas masquer un singleton global.
- Aucun adaptateur, endpoint ou job ne duplique une formule du registre de calculs.
- Les écritures persistantes et jobs sont idempotents, transactionnels et compatibles avec rejeu.
- Ne pas exécuter calcul CPU ou appel IBKR bloquant sur l’event loop FastAPI.
- Exceptions typées : aucune capture `except Exception` silencieuse, aucun retry infini, aucun fallback permissif.

## Intégrations

- Encapsuler `ib_async` derrière l’adaptateur étroit prévu ; aucun import IBKR dans le domaine.
- Respecter pacing, backpressure, limites de lignes, reconnexion et codes TWS documentés.
- Valider capacité/secret de route, registre, taille, âge, schéma, allowlist et idempotency key avant de persister une alerte TradingView ; ne pas inventer de signature cryptographique fournie par TradingView.
- Ne scraper aucune interface ni contourner un abonnement, entitlement, paywall ou condition d’utilisation.

## Vérification

- Toute formule nouvelle référence son identifiant dans `CALCULATION_REGISTRY.yaml`, ses hypothèses et son oracle indépendant.
- Toute correction de bug ajoute d’abord un test reproducteur.
- Aucun `# type: ignore`, `# noqa`, xfail ou skip sans motif étroit, ticket et échéance.
- Les logs sont structurés et expurgés ; interdiction de journaliser secret, compte, payload complet ou donnée commerciale brute.
