# ADR-000 — Modèle de décision d’architecture

- Statut : À choisir (`Proposé`, `Accepté`, `Remplacé` ou `Rejeté`)
- Date : AAAA-MM-JJ
- Décideurs : propriétaire produit, responsable architecture, responsable du domaine concerné
- Portée : indiquer les modules, contrats et lots concernés
- Remplace : aucun, ou identifiant de l’ADR remplacé

## Contexte

Décrire le problème concret, les contraintes vérifiables, les risques et la raison pour laquelle une décision durable est nécessaire. Séparer les faits des hypothèses. Lister les documents et preuves qui encadrent la décision.

## Décision

Énoncer une seule décision normative. Préciser :

- ce qui devient obligatoire ;
- ce qui reste optionnel ;
- les frontières de responsabilité ;
- les invariants qui ne peuvent pas être contournés ;
- le mécanisme de preuve attendu dans les tests, la CI ou les runbooks.

## Conséquences

### Positives

- Décrire les bénéfices attendus et la complexité supprimée.

### Coûts et contraintes

- Décrire les compromis, migrations, dépendances et charges d’exploitation.
- Identifier le propriétaire de chaque contrainte durable.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Option A | Risque, incohérence ou coût supérieur |
| Option B | Ne respecte pas un invariant de la Constitution |

## Preuves d’application

- Tests ou contrôles CI attendus.
- Fichiers de configuration, contrats ou runbooks concernés.
- Métriques ou traces permettant de vérifier la décision en fonctionnement.

## Critères de réexamen

La décision n’est réexaminée que si un fait mesuré invalide son hypothèse principale, si une obligation réglementaire ou contractuelle change, ou si une autre ADR Acceptée la remplace explicitement.
