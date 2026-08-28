# LOT-03 — PostgreSQL, outbox et qualité des données

## Dépendances et préconditions

- Dépendance bloquante : LOT-02 fusionné, contrats et schémas canoniques verts.
- Branche d'exécution : `lot/03-storage-quality` depuis le commit sain de LOT-02.
- PostgreSQL 18 doit être exécuté dans un environnement de test isolé, par digest immuable, avec données exclusivement synthétiques.
- ADR applicables : ADR-001, ADR-002, ADR-003, ADR-006, ADR-009 et ADR-010.

Ce lot ferme la porte A de la roadmap. LOT-04 et LOT-05 ne peuvent démarrer tant que migrations, idempotence, provenance, fraîcheur et restauration ne sont pas prouvées sur PostgreSQL réel.

## Objectif

Construire la vérité transactionnelle initiale : persistance PostgreSQL, migrations Alembic, observations append-only, snapshots courants, outbox durable et moteur de qualité/fraîcheur/couverture. Toute donnée stockée doit rester traçable à son enveloppe canonique et tout état dérivé doit être reproductible.

La preuve principale attendue par la feuille de route est : ingestion idempotente, provenance et fraîcheur testées, avec restauration vérifiée.

## Non-objectifs

- connecter ou simuler fonctionnellement IBKR, TradingView, SEC, FRED ou une source live ;
- implémenter Data Fusion, calcul quantitatif, gates, `AdviceEngine`, API HTTP ou interface ;
- ajouter Redis, Celery, TimescaleDB, Kafka ou une file externe ;
- utiliser SQLite comme substitut de test ;
- stocker secrets, comptes/positions IBKR automatiques ou payloads commerciaux réels ;
- optimiser prématurément sans mesure ou promettre une sémantique « exactement une fois ».

## Lecture obligatoire

1. `CLAUDE.md`, la Constitution et `docs/99-status/NOW.md` ;
2. `docs/03-domain/CANONICAL_CONTRACTS.md`, `DATA_QUALITY.md` et `UNITS_TIME_AND_PRECISION.md` ;
3. `docs/02-architecture/MODULE_BOUNDARIES.md`, `DATA_FLOW.md` et `THREAT_MODEL.md` ;
4. `docs/07-delivery/DEPENDENCY_MATRIX.md`, `DEFINITION_OF_DONE.md` et la porte A de `MASTER_ROADMAP.md` ;
5. `docs/06-quality/TEST_STRATEGY.md`, `TEST_MATRIX.md`, `CI_GATES.md`, `OBSERVABILITY.md` et `SECURITY_CONTROLS.md` ;
6. `docs/08-runbooks/BACKUP_RESTORE.md` et `INCIDENT.md` ;
7. `docs/09-adr/001-modular-monolith.md`, `002-local-first.md`, `003-python-financial-authority.md`, `006-postgresql-outbox.md`, `009-security-network.md` et `010-testing.md` ;
8. schémas, exemples, preuves et rapport de compatibilité produits par LOT-02.

## Livrables

1. Modèles de persistance SQLAlchemy séparés des modèles du domaine, mappers explicites et ports de repositories ; aucune règle financière dans `persistence`.
2. Migration Alembic initiale et migrations atomiques suivantes couvrant identités, enveloppes/observations, qualité, conflits, entitlements, couverture, snapshots, outbox, tentatives et leases.
3. Tables d'observations append-only avec identifiant source, version de schéma, timestamps, epoch, droits, qualité, hash et clé d'idempotence ; les corrections créent une révision, jamais un écrasement silencieux.
4. Contraintes d'identité temporelle et d'option conformes à LOT-02, avec quarantaine explicite des références non résolues.
5. Snapshots courants dérivés et reconstruisibles, séparés des événements immuables ; aucune vue courante ne devient la seule preuve historique.
6. Outbox dans la même transaction que la mutation métier, réclamation par lease et `SKIP LOCKED`, tentatives bornées, backoff, état terminal et mécanisme de rejeu manuel audité.
7. Handlers de test idempotents démontrant la sémantique au moins une fois et le recouvrement après crash.
8. Registre versionné de politiques TTL par source/type/session/usage et évaluateur de qualité produisant états, raisons, âge, couverture et conflits sans fallback.
9. Agrégats de couverture : attendu, reçu, valide, retardé, périmé, manquant, taux et âge maximal, sans appeler « complet » un ensemble non prouvé.
10. Partitionnement/rétention initial pour observations volumineuses, avec création anticipée, frontière UTC, archivage et suppression contrôlée testés.
11. Métriques/logs structurés : latence transactionnelle, backlog outbox, âge du plus vieux message, retries, erreurs, fraîcheur, couverture, partitions et `trace_id`, sans payload sensible.
12. Procédure et test automatisable de sauvegarde puis restauration dans une instance PostgreSQL vierge avec comparaison d'intégrité.

## Étapes d'exécution

1. Vérifier les preuves de LOT-02, les hashes des schémas, l'état Git et le digest PostgreSQL ; passer `NOW.md` à `running`.
2. Écrire le modèle logique, les clés, index, contraintes, volumes attendus, politique de rétention et stratégie de rollback avant la première migration.
3. Créer les rôles minimaux séparant migration, runtime API futur, worker et lecture de sauvegarde ; les secrets restent injectés hors dépôt.
4. Implémenter migrations et mappers par tranche : identités, enveloppes immuables, qualité/couverture, snapshots, puis outbox/leases.
5. Implémenter l'API interne d'ingestion transactionnelle : validation LOT-02, clé d'idempotence, insertion d'observation, mise à jour dérivée et événement outbox dans un seul commit.
6. Implémenter la réclamation concurrente, renouvellement/expiration de lease, retries et finalisation idempotente. `LISTEN/NOTIFY` ne sert que de réveil.
7. Implémenter le registre TTL et l'évaluateur session-aware ; un statut absent, retardé, ancien, future-dated ou contradictoire ne peut devenir valide par défaut.
8. Ajouter partitions, tâches de maintenance et métriques ; benchmarker avec un dataset synthétique versionné avant tout index additionnel.
9. Écrire et exécuter les tests sur PostgreSQL 18 réel, incluant crash, concurrence, rollback, horloge et limites de partition.
10. Effectuer sauvegarde et restauration vers une base vierge ; comparer comptages, clés, hashes, relations, outbox et reconstruction des snapshots.
11. Vérifier la redaction des logs, les privilèges, l'absence de capacités interdites et la stabilité des migrations depuis un checkout propre.
12. Mettre à jour runbook, matrice de qualité, `NOW.md`, `HISTORY.md` et `BLOCKERS.md`, puis produire la preuve sans lancer une source réelle.

## Tests obligatoires

### Migrations et intégrité

- `upgrade` depuis une base vierge, `downgrade` jusqu'au point supporté, puis nouvel `upgrade`, sans dérive de schéma ;
- validation des contraintes, index, clés étrangères, intervalles d'identité et références de schéma ;
- transaction annulée ne laisse ni observation, ni snapshot, ni événement outbox ;
- observation immuable ne peut être modifiée/supprimée par le rôle runtime ordinaire ;
- frontières de partitions avant/après mois, année et timestamps UTC, y compris pendant un changement DST d'exchange.

### Idempotence et outbox

- le même `event_id`/identifiant source reçu plusieurs fois ne crée qu'un effet métier et conserve un compteur ou audit de doublon ;
- deux workers concurrents ne traitent pas simultanément le même lease valide ;
- crash avant commit, après commit et avant ack, expiration de lease et retry produisent un état final cohérent ;
- un handler rejoué n'ajoute pas un second effet ; ordre inversé et événement tardif restent auditables ;
- `LISTEN/NOTIFY` perdu n'empêche pas le polling durable de vider l'outbox ;
- poison message atteint un état terminal/DLQ logique sans bloquer les messages sains.

### Qualité, fraîcheur et couverture

- matrice `VALID|PARTIAL|STALE|INVALID|CONFLICT|INSUFFICIENT_DATA` et `LIVE|FROZEN|DELAYED|DELAYED_FROZEN|UNKNOWN` ;
- timestamps absents, futurs, naïfs, hors ordre, epoch ancien et dérive d'horloge ;
- TTL distinct selon usage et séance ; aucune valeur globale implicite ;
- absence de droit produit une couverture explicite et jamais une substitution silencieuse ;
- attendu/reçu/valide/manquant et âge maximal restent exacts face aux doublons et quarantaines ;
- conflit multi-source conserve les observations et raisons, sans vote automatique.

### Restauration, performance et observabilité

- sauvegarde logique puis restauration dans une instance vierge avec hashes et comptages identiques ;
- snapshots courants reconstruits depuis l'historique donnent les mêmes hashes ;
- test de charge synthétique documente débit, p50/p95/p99, taille/index et backlog sans fixer un seuil marketing non mesuré ;
- chaque erreur et retry possède `trace_id`, code stable et métrique, sans payload complet ;
- la CI échoue sur migration divergente, partition absente, restauration incorrecte ou log sensible.

## Sécurité et garde-fous

- PostgreSQL écoute uniquement sur le réseau interne/loopback prévu ; aucun port public et aucun mot de passe dans Compose, Git ou logs.
- Rôles à moindre privilège : le runtime n'a ni `SUPERUSER`, ni création de rôle/base, ni bypass RLS, ni mutation d'historique append-only.
- Les requêtes sont paramétrées ; identifiants, noms de partition et commandes d'administration passent par allowlist stricte.
- Sauvegardes chiffrées hors dépôt, permissions minimales, rétention définie et test de restauration expurgé.
- Aucun payload fournisseur réel, compte courtier, position automatique, secret de webhook ou donnée personnelle dans fixtures/captures.
- Erreurs, SQL debug et métriques n'exposent ni chaîne de connexion, ni payload, ni identifiant sensible.
- La quarantaine n'est pas une poubelle invisible : accès restreint, motif, compteur, rétention et procédure de rejeu audités.
- Redis/Celery/TimescaleDB restent interdits sans benchmark et ADR de réexamen.

## Critères de sortie mesurables

- Migrations `up → down supporté → up` vertes sur PostgreSQL 18 réel, schéma sans diff et rollback documenté.
- 100 % des écritures testées associent source, versions, timestamps requis, unité/devise applicables, qualité, fraîcheur et hash.
- 0 effet métier supplémentaire après rejeu d'un même événement ; concurrence, crash et lease expiré ont des tests verts.
- 100 % des mutations génératrices d'événement écrivent l'outbox dans la même transaction ; un rollback laisse zéro événement orphelin.
- 100 % des politiques TTL sont nommées/versionnées par usage ; aucun fallback global ou passage silencieux à `VALID/LIVE`.
- Couverture et conflits restent exacts sous doublon, désordre, retard, droit absent et donnée future.
- Restauration sur base vierge réussie avec hashes, comptages et snapshots reconstruits identiques.
- 0 permission excessive, port public, secret, payload réel ou capacité IBKR interdite.
- Tests d'intégration, propriétés, migrations, sécurité, architecture et scans CI verts ; métriques de benchmark enregistrées comme baseline, pas comme promesse.
- Porte A de `MASTER_ROADMAP.md` cochée avec preuves ; sinon LOT-04 et LOT-05 restent bloqués.

## Format de preuve de fin de lot

```text
LOT : 03 — PostgreSQL, outbox et qualité
ÉTAT : done | review | blocked
BRANCHE / COMMIT : lot/03-storage-quality / <sha>
DÉPENDANCE : LOT-02 <sha fusionné + hash schémas>
POSTGRESQL : 18 / image <digest> / schéma <hash>
MIGRATIONS : up <résultat> ; down <point + résultat> ; re-up <résultat> ; diff <vide/non vide>
IDEMPOTENCE : événements soumis <n> ; effets <n uniques> ; doublons audités <n>
OUTBOX : concurrence <résultat> ; crash/retry <résultat> ; backlog final <n>
QUALITÉ : politiques TTL <n> ; états testés <n/n> ; conflits/couverture <résultat>
RESTAURATION : archive <hash> ; base vierge <oui/non> ; intégrité <hash avant/après>
TESTS : <commande exacte> → <exit code, durée, tests, couverture>, une ligne par gate
SÉCURITÉ : privilèges <résultat> ; secrets/logs <résultat> ; ports <résultat>
PERFORMANCE : dataset synthétique <taille> ; débit/p50/p95/p99 ; backlog max
FICHIERS MODIFIÉS : <nombre + chemins principaux>
RISQUE RESTANT : aucun | <risque concret>
BLOCAGE : aucun | <un seul blocage actionnable>
ROLLBACK : <migration/commit et résultat prouvé>
PROCHAINE COMMANDE : AUDITE LOT 03
```

Joindre rapports de migrations, tests de concurrence, matrice de qualité, métriques, manifest de sauvegarde et comparaison de restauration. Une sauvegarde non restaurée ou un test SQLite vaut `NO-GO`.
