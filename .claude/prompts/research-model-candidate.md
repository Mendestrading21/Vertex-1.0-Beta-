# Prompt — évaluer un modèle candidat

Travaille en mode Plan et ne modifie rien. Pour `MODEL_ID` et `FEATURE_SET` :

- définir outcome, population, horizon et connaissance disponible au temps t ;
- établir la baseline déterministe la plus simple ;
- vérifier licence, maintenance, dépendances et coût ;
- concevoir dataset point-in-time, walk-forward, purge/embargo et coûts ;
- définir métriques de discrimination, calibration, couverture, stabilité,
  drift, latence et abstention ;
- exiger tests d'ablation et résultats négatifs ;
- conclure `REJECT`, `RESEARCH_ONLY`, `SHADOW_CANDIDATE` ou
  `VALIDATION_CANDIDATE` ;
- interdire l'activation runtime dans cette session.

