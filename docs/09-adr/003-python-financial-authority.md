# ADR-003 — Python est l’unique autorité financière

- Statut : Accepté
- Date : 2026-08-28
- Portée : calculs, gates, décision, API, interface, IA

## Contexte

La duplication de formules entre backend, frontend et IA produit des écarts impossibles à expliquer. Prix d’options, Greeks, PnL, exposition, probabilités, risque et ratio rendement-risque exigent unités, précision, méthodes et versions explicites.

## Décision

Tous les calculs financiers autoritaires vivent dans le cœur Python.

- Le cœur utilise des contrats typés, des unités explicites, des dates timezone-aware et Decimal pour les valeurs sensibles.
- Chaque calcul est enregistré dans le registre avec méthode, version, hypothèses, tolérances et oracles.
- Un seul AdviceEngine applique les gates et produit AdviceResult.
- Le worker exécute les calculs lourds avec le même package que l’API.
- TypeScript formate et affiche les valeurs reçues ; il ne recalcule ni score, ni gate, ni résultat.
- Les simulations stochastiques enregistrent leur graine, leurs entrées et la version du moteur.
- L’IA ne peut ni créer ni modifier une valeur, un gate ou un verdict.

## Conséquences

### Positives

- Résultats reproductibles et explicables.
- Une seule correction modifie tous les consommateurs.
- Tests différentiels et par invariants concentrés sur une autorité.

### Coûts et contraintes

- Une interaction web nécessitant un calcul passe par l’API ou un résultat pré-calculé.
- Les contrats décimaux et les unités imposent davantage de validation.
- Le worker doit rester disponible pour les simulations coûteuses.

## Options rejetées

| Option | Motif du rejet |
|---|---|
| Formules dupliquées en TypeScript | Divergence silencieuse et précision flottante |
| Plusieurs moteurs de verdict | Autorités contradictoires |
| Calculs confiés au LLM | Non déterministes et non auditables |
| Feuilles de calcul comme production | Versionnement, typage et tests insuffisants |

## Critères de réexamen

Une autre implémentation peut servir d’oracle indépendant ou d’accélérateur interne, mais ne devient jamais une seconde autorité sans remplacement explicite de cette ADR.
