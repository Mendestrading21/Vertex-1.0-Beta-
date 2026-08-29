# ADR-011 — Séparation recherche et runtime

- Statut : Accepté
- Date : 2026-08-28
- Portée : backtests, notebooks, données historiques, production

## Contexte

La recherche utilise bibliothèques, notebooks et expériences rapides qui ne respectent pas toujours les contraintes d’un runtime live. Lui donner accès en écriture à la base canonique permettrait de promouvoir silencieusement un résultat surajusté ou incomplet.

## Décision

- Le runtime live et la recherche sont des environnements, dépendances et processus séparés.
- La recherche consomme des snapshots versionnés en lecture seule, exportés en Parquet avec provenance.
- DuckDB et les notebooks restent dans le plan recherche.
- Aucun notebook ne possède de secret runtime ni de droit d’écriture PostgreSQL.
- Une expérience enregistre dataset, vintage, code SHA, paramètres, seed, coûts, splits et métriques.
- Un résultat de recherche ne rejoint le runtime qu’après spécification, implémentation dans le cœur, tests indépendants, calibration et revue.
- Les modèles et paramètres promus sont versionnés comme artefacts, jamais chargés depuis un répertoire de travail mutable.

## Conséquences

### Positives

- Expérimentation libre sans contaminer le live.
- Backtests reproductibles et point-in-time.
- Surface de dépendances runtime plus petite.

### Coûts et contraintes

- Il faut un pipeline d’export et un processus de promotion.
- Des calculs peuvent exister deux fois temporairement comme prototype puis implémentation contrôlée.
- Le stockage historique doit être budgété et documenté.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Notebook connecté en écriture au live | Contamination et fuite possibles |
| Importer directement une stratégie de recherche | Absence de gates de production |
| Base DuckDB comme vérité live | Concurrence et transactions inadaptées |
| Dépendances de recherche dans l’image API | Surface et reproductibilité dégradées |

## Critères de réexamen

La frontière ne disparaît pas. Seuls les mécanismes d’export et de promotion peuvent évoluer après preuve d’isolation équivalente.
