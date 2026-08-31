# Format du plan cloud

## 1. Verdict

Répondre en premier : peut-on lancer le candidat, quelles capacités sont
réellement actives, quels risques interdisent une Beta live et quelle preuve
manque. Éviter tout pourcentage global.

## 2. Baseline

Tableau dépôt/branche/PR/SHA/CI/date/protection/limites. Signaler explicitement
si le travail annoncé par Claude n'apparaît pas dans GitHub.

## 3. Matrice de vérité

| ID | Capacité | État | Chemin runtime | Preuve | Donnée | Risque | Lot |
|---|---|---|---|---|---|---|---|

Une ligne par capacité et non par document. Séparer « code présent » de « code
appelé » et « validé live ».

## 4. Constats

| ID | P | Domaine | Constat | Preuve chemin:symbole | Effet | Correction proposée | Acceptation |
|---|---|---|---|---|---|---|---|

Inclure les défauts, contradictions, duplications, code mort, mocks, valeurs en
dur, tests faibles, droits manquants, limites de preuve et dettes de conception.

## 5. Pages et connexions

Fournir une matrice des douze pages et une matrice IBKR/TradingView/sources.
Chaque case indique `PROUVÉ`, `PRÉSENT_NON_PROUVÉ`, `PLANIFIÉ`, `BLOQUÉ`,
`ABSENT`, `CONTREDIT` ou `INCONNU`.

Ajouter ensuite la carte de portage entre `Vertex-` et `Vertex-1.0-Beta-` avec
les décisions `REPRENDRE`, `ADAPTER`, `RÉÉCRIRE`, `REJETER` ou `BLOQUÉ`. Une
capacité legacy n'est pas une preuve Beta et ne doit jamais être comptée deux
fois.

## 6. Lots d'exécution

Ordonner par dépendances et risque, pas par préférence visuelle. Chaque lot doit
tenir dans une PR et préciser : objectif, fichiers probables, non-objectifs,
préconditions, tests, preuves, rollback, risque restant et décision humaine.

Ordre par défaut à adapter aux constats :

1. vérité Git/GitHub et gouvernance ;
2. démarrage reproductible et vérité des données ;
3. calculs, gates et intelligence réellement reliés ;
4. intégrations et recette live strictement lecture seule ;
5. reconstruction page par page sur le contrat visuel approuvé ;
6. boucle d'amélioration offline contrôlée ;
7. release, monitoring, backup/restore et recette Beta.

Ne jamais mettre plusieurs autorités financières ou plusieurs pages majeures
dans un lot si cela empêche un rollback clair.

## 7. Recette poste live différée

Créer une liste séparée pour les seules preuves impossibles dans le cloud : TWS
paper en Read-Only API, entitlements, délais, reconnexion, TradingView signé,
Cloudflare si B-03 est approuvé, latence réelle et captures bureau. Chaque test
reste sans ordre, sans compte et sans secret dans les logs.

## 8. Pilotage téléphone

Après le rapport complet, fournir un statut de huit lignes maximum : candidat,
SHA, CI, P0, P1, blocage live, lot recommandé, commande suivante. Le statut
compact ne remplace pas les preuves du rapport.

Commande d'exécution recommandée seulement après validation humaine :

`EXÉCUTE LOT <NN>`

Le mode Plan ne l'exécute jamais lui-même.
