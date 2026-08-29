# ADR-012 — Politique de migration depuis le Vertex actuel

- Statut : Accepté
- Date : 2026-08-28
- Portée : dépôt donneur, nouveau dépôt, code, données, design

## Contexte

Le Vertex actuel contient désormais des contrats, tests, validations, calculs
purs et actifs visuels utiles, mais aussi un monolithe historique, des autorités
concurrentes et des comportements que la Constitution interdit. Une copie
globale conserverait la dette ; une réécriture totale gaspillerait les éléments
déjà prouvés.

## Décision

- Vertex One naît dans un nouveau dépôt GitHub avec une histoire et des
  protections neuves.
- Le dépôt actuel est un donneur épinglé en lecture seule, jamais une dépendance
  de production.
- Toute capacité candidate est classée `KEEP`, `ADAPT`, `REWRITE`, `REFERENCE`
  ou `DROP` avec provenance, licence, frontière et test.
- L'absence d'inventaire signifie « non migré », pas « automatiquement copié ».
- Les contrats et fonctions purs peuvent migrer après tests indépendants.
- Le moteur de décision unique, les stores, les ports de source et la
  composition de l'interface restent gouvernés par Vertex One.
- Aucun copier-coller massif, sous-module ou import runtime vers le donneur.
- Une migration de données exige schéma source, transformation idempotente,
  rapport, quarantaine et rollback.
- Les décisions sont regroupées par vague et PR brouillon.

## Conséquences

### Positives

- Les anciennes hypothèses ne deviennent pas des contraintes cachées.
- Le travail sain déjà réalisé peut être conservé avec preuve.
- Chaque élément conservé possède une provenance et un test.
- Historique Git, dépendances et CI restent propres.

### Coûts et contraintes

- Audit initial et maintien d'une traçabilité donneur.
- Oracles indépendants pour les calculs financiers.
- Comparaisons visuelles et fonctionnelles documentées.
- Les données anciennes ambiguës peuvent rester non migrées.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Grande branche de refonte dans le dépôt existant | Hérite structure, historique et dépendances |
| Fork complet puis nettoyage | Valeur par défaut trop permissive |
| Réutilisation globale de tous les moteurs | Réintroduit les autorités concurrentes |
| Réécriture intégrale sans audit | Perd contrats, tests et calculs purs utiles |
| Migration silencieuse de toutes les données | Qualité et sens non garantis |

## Critères de réexamen

Une capacité peut être reclassée uniquement par une décision documentée, avec
preuve de compatibilité et tests. Le donneur ne devient jamais une dépendance de
production.

