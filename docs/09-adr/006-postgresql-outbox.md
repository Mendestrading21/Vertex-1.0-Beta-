# ADR-006 — PostgreSQL et outbox sans Redis initial

- Statut : Accepté
- Date : 2026-08-28
- Portée : persistance, jobs, événements, cache

## Contexte

Le lancement vise un seul poste et un volume compatible avec PostgreSQL. Ajouter Redis et Celery multiplierait les services, les mécanismes de reprise et les incohérences possibles entre transaction métier et publication de job.

## Décision

PostgreSQL 18 est la vérité transactionnelle et porte l’outbox initiale.

- Une mutation métier et son événement outbox sont écrits dans la même transaction.
- Les workers réclament des lignes avec verrouillage et SKIP LOCKED, puis enregistrent tentative, lease et résultat.
- Les handlers sont idempotents et protégés par clés uniques.
- LISTEN et NOTIFY servent uniquement de signal de réveil ; les tables restent la source durable.
- Les observations volumineuses sont append-only, partitionnées et soumises à rétention.
- Les snapshots courants sont séparés des événements immuables.
- Aucun cache ne peut masquer la source, la fraîcheur ou un échec de lecture.
- Redis, Celery et TimescaleDB sont différés jusqu’à preuve par benchmark.

## Conséquences

### Positives

- Atomicité entre état et job.
- Un seul système à sauvegarder, surveiller et restaurer.
- Rejeu, audit et résolution d’incident simplifiés.

### Coûts et contraintes

- La base concentre la charge et doit avoir des budgets mesurés.
- Le nettoyage, le partitionnement et les leases exigent des tests de concurrence.
- La sémantique est au moins une fois, jamais exactement une fois par magie.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Redis et Celery au LOT-01 | Complexité prématurée |
| Publication après commit sans outbox | Fenêtre de perte entre transaction et job |
| LISTEN/NOTIFY comme file durable | Notifications non conçues comme stockage |
| TimescaleDB par défaut | Licence mixte et besoin non mesuré |
| Cache frontend comme vérité | Risque d’afficher un état périmé comme valide |

## Critères de réexamen

Une file externe est évaluée seulement si les métriques montrent une saturation durable, un besoin de distribution multi-hôte ou une latence que PostgreSQL ne peut pas respecter après optimisation documentée.
