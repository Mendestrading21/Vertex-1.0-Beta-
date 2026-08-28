# Probabilités et calibration

Vertex sépare strictement :

1. probabilité implicite risque-neutre dérivée des options ;
2. fréquence historique empirique d'un événement défini ;
3. probabilité prédictive physique issue d'un modèle calibré.

Une probabilité de toucher une cible avant un stop dépend du chemin et ne se remplace pas par (N(d_2)).

## Protocole minimal prédictif

- résultat et horizon figés avant construction des variables ;
- variables disponibles uniquement à l'instant de décision ;
- split walk-forward avec gap au moins égal à l'horizon du label ;
- calibration séparée de l'entraînement ;
- holdout final intouchable ;
- Brier score, log loss et diagramme de fiabilité ;
- intervalles par bootstrap en blocs ;
- résultats par horizon, régime et famille d'instrument ;
- registre du nombre de variantes testées ;
- abstention si échantillon, stabilité ou calibration insuffisants.

## Contrat UI

Une valeur ne peut être affichée comme probabilité prédictive que si `calibration_status=VALID`, `evaluation_window` est hors échantillon et `valid_until` n'est pas dépassé. Sinon, la valeur est masquée et la cause est affichée.

