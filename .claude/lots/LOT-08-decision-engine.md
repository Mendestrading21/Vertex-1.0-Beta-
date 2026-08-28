# LOT-08 — Gates, calibration et moteur de décision

## Références et dépendances

- Références obligatoires : `docs/03-domain/DECISION_ENGINE.md`,
  `docs/03-domain/PROBABILITY_CALIBRATION.md`,
  `docs/03-domain/CANONICAL_CONTRACTS.md`, `docs/03-domain/DATA_QUALITY.md` et
  `docs/04-integrations/DATA_FUSION.md`.
- Décisions applicables : ADR-003, ADR-008, ADR-010 et ADR-011.
- Contrôles transversaux : `docs/06-quality/TEST_STRATEGY.md` et
  `docs/07-delivery/DEFINITION_OF_DONE.md`.
- Dépendances bloquantes : LOT-06 Data Fusion Hub et LOT-07 Moteur quantitatif.

Le lot ne commence que si les données fusionnées conservent droits, qualité,
fraîcheur et provenance, et si chaque calcul consommé produit un
`CalculationRecord` certifié.

## Objectif

Livrer l'unique `AdviceEngine` de Vertex. Il applique des portes bloquantes ou
dégradantes dans un ordre déterministe, sépare statut, direction, confiance et
probabilité, puis produit un `AdviceResult` immuable, explicable et reproductible.

Le moteur doit échouer fermé : une donnée inconnue, périmée, contradictoire,
insuffisamment licenciée ou numériquement invalide ne peut jamais être compensée
par un score favorable.

## Non-objectifs

- récupérer des données, recalculer un prix ou exécuter un job de collecte ;
- créer plusieurs moteurs par page, actif, stratégie ou fournisseur ;
- émettre `BUY`, `SELL`, une taille d'ordre, un ordre IBKR ou une promesse de gain ;
- demander à un LLM d'arbitrer un gate, d'inventer une probabilité ou de modifier un
  verdict ;
- produire un score global opaque qui masque les preuves et les exclusions ;
- appeler une fréquence historique « probabilité prédictive » ou confondre mesure
  risque-neutre et probabilité physique ;
- relâcher une porte parce qu'une source ou un modèle est indisponible.

## Livrables attendus

1. Catalogue versionné des gates avec ordre, classe `BLOCK` ou `DEGRADE`, seuils,
   unités, raison stable, preuves requises et politique par usage/classe d'actif.
2. Évaluateurs purs pour les dix portes définies dans
   `docs/03-domain/DECISION_ENGINE.md`, sans accès réseau ni persistance directe.
3. Un seul `AdviceEngine`, injecté par l'application, consommant des snapshots et
   calculs certifiés et produisant le contrat canonique `AdviceResult`.
4. Politique déterministe de transition vers `BLOCKED`, `INSUFFICIENT_DATA`,
   `OBSERVE`, `REVIEW` ou `QUALIFIED`, indépendante de la direction
   `BULLISH|BEARISH|NEUTRAL|MIXED|UNKNOWN`.
5. Modèle d'explication structurée : `explanation_facts`, `limitations`,
   `evidence_ids`, seuils observés et gates dans leur ordre d'évaluation.
6. Calcul du R:R directionnel et calculs de payoff options consommés depuis LOT-07,
   avec résultat `INVALID` lorsque les préconditions ne sont pas réunies.
7. Registre de calibration séparant explicitement : probabilité implicite
   risque-neutre, fréquence historique et probabilité prédictive physique.
8. Pipeline d'évaluation prédictive hors échantillon : split walk-forward, gap au
   moins égal à l'horizon, calibration séparée, holdout final, Brier, log loss,
   fiabilité, bootstrap en blocs et abstention.
9. Gabarit déterministe capable d'expliquer tout verdict sans IA.
10. Suite de tests exhaustive des branches, combinaisons de gates, calibration,
    invariants, replay, mutation et non-régression.

## Sémantique fail-closed

- L'ordre canonique des portes est conservé ; l'évaluation peut poursuivre après un
  blocage seulement pour collecter des diagnostics, jamais pour renverser le statut.
- `BLOCK` domine toujours `DEGRADE` et tout classement. Plusieurs blocages sont
  conservés, ordonnés et cités.
- Une preuve absente ou non résolue n'équivaut jamais à `PASS`.
- Une source `DELAYED` peut être autorisée pour un usage historique documenté mais
  bloque tout usage exigeant du live ; l'usage fait partie de la configuration.
- La configuration et les contraintes utilisateur sont immuables, versionnées et
  incluses dans le hash de décision.
- Une contradiction critique reste visible et bloque ou dégrade selon une règle
  versionnée ; aucune priorité de source ad hoc n'est créée dans le moteur.
- La confiance décrit la qualité/robustesse du résultat ; elle n'est ni la direction
  ni une probabilité de succès.
- Une probabilité prédictive n'apparaît que si `calibration_status=VALID`, que sa
  fenêtre est hors échantillon et que `valid_until` n'est pas dépassé.
- Un `AdviceResult` n'est jamais modifié : une réévaluation crée un nouvel objet avec
  `supersedes` et conserve l'audit de l'ancien.

## Tests obligatoires

- Table de décision couvrant chaque gate en `PASS`, `DEGRADE`, `BLOCK`, valeur
  absente, valeur limite exacte et raison inconnue.
- Propriétés : ajouter une preuve défavorable ne peut pas améliorer un statut ;
  permuter des preuves équivalentes ne change pas le verdict ; un `BLOCK` ne peut
  jamais devenir `QUALIFIED` par hausse d'un score.
- Exhaustivité : 100 % des branches de gates et de l'agrégation de décision ; chaque
  `reason_code` a au moins un test positif et un test de rejet.
- Déterminisme : mêmes snapshots, versions et configuration donnent le même
  `AdviceResult`, ordre des faits et hash compris.
- Limites : heure de validité exacte, données stale à la frontière, séance inconnue,
  conflit source, devise/multiplicateur incohérent, calcul non fini et liquidité au
  seuil.
- Calibration : fuite temporelle volontaire rejetée, gap insuffisant rejeté,
  holdout intouchable, échantillon trop petit, dérive, mauvaise calibration et
  `valid_until` expiré entraînent l'abstention.
- Contrats : sérialisation des cinq statuts et cinq directions, compatibilité de
  version et rejet de tout champ d'ordre ou de valeur non sourcée.
- Mutation : opérateurs de comparaison, priorité `BLOCK`, validité temporelle et
  conditions de calibration ne laissent aucun mutant dangereux survivant.
- Architecture : aucun import adaptateur, FastAPI, frontend ou fournisseur IA dans
  le domaine `decision`.

## Critères de sortie mesurables

- Une seule définition de `AdviceEngine` et un seul chemin de production du contrat
  `AdviceResult` sont trouvés dans le dépôt.
- 100 % des branches des gates, décisions, validités et politiques de probabilité
  sont couvertes ; mutation score ≥ 95 % sans mutant critique survivant.
- 100 % des résultats contiennent `as_of`, `valid_until`, version moteur, snapshot
  d'entrée, gates, preuves, limites et faits d'explication.
- Toute entrée invalide, inconnue ou insuffisante testée produit `BLOCKED` ou
  `INSUFFICIENT_DATA`, jamais `QUALIFIED`.
- Aucun contrat, enum ou texte d'API du moteur ne contient une commande d'achat,
  vente, transmission ou exécution.
- Les trois natures de probabilité sont identifiables par un type non ambigu ; une
  probabilité prédictive invalide ou expirée est absente du DTO d'affichage et sa
  cause est fournie.
- Cent replays d'un même cas de référence produisent le même hash et aucune
  divergence de statut, direction ou explication structurée.
- Le gabarit sans IA explique 100 % des cas de la matrice de décision avec preuves et
  limitations lisibles.

