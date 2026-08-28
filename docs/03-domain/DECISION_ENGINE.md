# Moteur de décision unique

## Responsabilité

`AdviceEngine` agrège uniquement des résultats certifiés. Il ne récupère pas de données, ne lance pas de modèle IA et ne possède pas de logique d'interface.

## Ordre des portes

1. Instrument résolu.
2. Entitlements suffisants.
3. Snapshot cohérent et frais.
4. Session et événement connus.
5. Liquidité minimale définie par classe d'actif.
6. Calculs numériques valides.
7. Risque portefeuille manuel disponible si requis.
8. Probabilité calibrée si elle est utilisée.
9. Contradictions critiques résolues ou explicites.
10. Contraintes utilisateur versionnées.

Une porte `BLOCK` ne peut pas être compensée par un score. Une porte `DEGRADE` réduit le niveau de résultat et ajoute une limite visible.

## R:R exact

Pour un scénario directionnel long avec entrée (E), stop (S<E), cible (T>E), coûts (C) et multiplicateur (M) :

\[
Risque = (E-S)M + C, \qquad Récompense = (T-E)M - C
\]

\[
R:R = \frac{Récompense}{Risque}
\]

Si risque ≤ 0, entrée/stop/cible absents, devise incohérente ou horizon indéfini, le ratio est `INVALID`. Une structure options utilise sa fonction de payoff et ses coûts ; elle ne réutilise pas naïvement cette formule.

## Classement

Les opportunités sont d'abord séparées par statut/gates, puis classées par critères décomposables. Aucun score global ne masque une porte, une incertitude ou un manque de données.

## Explication

`AdviceResult.explanation_facts` contient des faits structurés. L'IA peut les reformuler et citer les preuves. Si l'IA est absente, l'interface doit pouvoir expliquer entièrement le résultat par gabarit déterministe.

