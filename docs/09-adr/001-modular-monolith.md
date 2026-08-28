# ADR-001 — Monolithe modulaire

- Statut : Accepté
- Date : 2026-08-28
- Portée : dépôt, backend, worker, agent IBKR, web

## Contexte

Vertex One doit réunir collecte de données, qualité, calcul quantitatif, portefeuille manuel, décision, API et présentation sans recréer plusieurs autorités concurrentes. Le produit vise d’abord un utilisateur, un ordinateur de marché et un déploiement local. Des microservices ajouteraient des contrats réseau, de la réplication, des déploiements et des pannes distribuées avant qu’un besoin de mise à l’échelle soit démontré.

## Décision

Vertex One est un monolithe modulaire dans un monorepo.

- Les modules Python respectent les frontières décrites dans MODULE_BOUNDARIES.md.
- Le domaine pur ne dépend ni du réseau, ni de la base, ni de FastAPI, ni de l’interface.
- API et worker sont des processus distincts, mais importent le même cœur de domaine et le même moteur de décision.
- L’agent IBKR et le web sont des applications périphériques sans autorité financière.
- Les interactions internes privilégient appels de fonctions, transactions et contrats versionnés ; aucun bus distribué n’est ajouté au lancement.
- Des tests d’architecture interdisent les imports contraires aux frontières.

## Conséquences

### Positives

- Une seule implémentation des règles et calculs.
- Transactions atomiques et débogage de bout en bout plus simples.
- Déploiement, sauvegarde et exploitation adaptés à une machine locale.
- Possibilité d’extraire ultérieurement un module sur la base de mesures réelles.

### Coûts et contraintes

- Les frontières doivent être contrôlées automatiquement pour éviter un monolithe emmêlé.
- Les travaux CPU lourds doivent quitter le processus API et passer par le worker.
- Une modification transversale peut imposer de tester plusieurs modules dans la même PR.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Microservices dès le départ | Complexité réseau et opérationnelle sans charge justifiée |
| Kubernetes et service mesh | Inadaptés à un déploiement local sur un seul poste |
| Application unique sans modules | Rendrait les responsabilités et dépendances incontrôlables |
| Un dépôt par application | Favoriserait la dérive des contrats et versions |

## Critères de réexamen

Une extraction n’est envisagée que si un profil de charge, une exigence de sécurité ou un cycle de déploiement indépendant est mesuré pendant plusieurs versions et ne peut être résolu par une séparation de processus.
