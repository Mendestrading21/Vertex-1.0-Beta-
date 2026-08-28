# Fusion des signaux

## Principe

Vertex ingère beaucoup d'informations mais n'affiche et ne combine que des preuves
traçables. La fusion ne fabrique pas une certitude : elle organise les signaux,
réduit les doublons, expose les contradictions et prépare une entrée certifiée pour
l'unique `AdviceEngine`.

Un signal n'est ni un ordre, ni un verdict, ni automatiquement une probabilité. Un
modèle ne décide jamais seul. Les gates de droits, identité, fraîcheur, couverture,
qualité et risque restent lexicographiquement prioritaires et fail-closed.

## Contrat `SignalEvidence`

```text
signal_id, signal_type, signal_version, entity_id, horizon,
event_time, available_at, as_of, valid_until,
role, direction, strength?, uncertainty?, calibration_status?,
feature_snapshot_hash, model_run_id?, calculation_ids[],
source_evidence_ids[], correlation_group, quality_status,
freshness_policy, limitations[], reason_codes[], supersedes?
```

`role` vaut `CONTEXT`, `DIRECTIONAL`, `RISK`, `QUALITY` ou `CONTRADICTION`.
`direction` vaut `BULLISH`, `BEARISH`, `NEUTRAL`, `MIXED` ou `UNKNOWN`.
`strength` est une échelle descriptive locale et versionnée ; elle n'est jamais
présentée comme chance de réussite. Une probabilité prédictive suit le contrat séparé
de `PROBABILITY_CALIBRATION.md`.

## Familles de preuve

| Famille | Exemples | Rôle par défaut |
|---|---|---|
| qualité/droits | fraîcheur, couverture, entitlement, conflit | `QUALITY` |
| marché | tendance, breadth, dispersion, volatilité | `CONTEXT` ou `DIRECTIONAL` |
| liquidité | spread, profondeur, volume, qualité de chaîne | `RISK` |
| options | IV, skew, terme, Greeks, payoff | `CONTEXT` ou `RISK` |
| événements | résultats, macro, filing, corporate action | `RISK` ou `CONTEXT` |
| anomalies/régime | rupture, drift, outlier, GARCH | `CONTEXT`, `RISK` ou `CONTRADICTION` |
| portefeuille manuel | concentration, exposition, thèse | `RISK` |
| prédictif validé | probabilité calibrée et non expirée | `DIRECTIONAL` limité |

Les signaux dérivés d'un même choc partagent un `correlation_group`. Rendement,
momentum, ATR et volatilité d'un même prix ne constituent pas quatre preuves
indépendantes. Même règle pour une actualité reprise par plusieurs fournisseurs ou
une surface options déclinée en plusieurs métriques.

## Pipeline déterministe

### 1. Éligibilité

Chaque signal passe les contrôles de schéma, identité, unité, droits, `available_at`,
fraîcheur, couverture, modèle et validité. Une preuve inéligible reste dans le graphe
avec sa raison, mais ne contribue pas à la synthèse.

### 2. Normalisation sémantique

Le moteur convertit uniquement vers un vocabulaire commun de rôle, direction,
horizon et force descriptive. Il ne compare pas directement un z-score, une
probabilité, une IV et un score Isolation Forest. Toute transformation possède une
version, des bornes et des tests.

### 3. Déduplication et budget par groupe

Les preuves identiques sont absorbées par hash. Les preuves fortement dépendantes
sont rassemblées par `correlation_group` et soumises à un plafond de contribution.
Une famille ne peut monopoliser le résultat par multiplication de features.

### 4. Contradictions

Les directions opposées, horizons incompatibles, données conflictuelles et écarts
entre modèle/challenger produisent des objets `CONTRADICTION`. La fusion ne choisit
pas silencieusement un camp. Une contradiction critique bloque ; une contradiction
tolérée réduit la portée et apparaît dans `limitations`.

### 5. Synthèse descriptive

La sortie contient familles présentes/manquantes, direction descriptive,
concordance, diversité des preuves, couverture, incertitude, contradictions et
raisons. Le score interne éventuel sert seulement à ordonner des dossiers ayant les
mêmes gates ; il est décomposable et ne doit jamais être affiché comme probabilité.

### 6. Passage au `AdviceEngine`

Le paquet de preuves est immuable et lié à son `as_of`. `AdviceEngine` réévalue ses
propres gates, peut dégrader ou bloquer, puis crée le seul `AdviceResult`. Aucune
règle de fusion ne peut produire `QUALIFIED` directement.

## Modes autorisés

### Fusion à règles

Mode initial obligatoire. Les priorités, plafonds, minima de diversité et traitements
des contradictions sont configurés et versionnés. La sortie est explicable sans IA.

### Méta-modèle calibré

Un méta-modèle peut devenir challenger uniquement après validation de
`MODEL_RISK_AND_VALIDATION.md`. Ses entrées sont les signaux point-in-time, jamais les
verdicts futurs. Entraînement, calibration et test sont séparés avec purge/embargo.
Il publie incertitude, domaine de support, validité et raison d'abstention.

Le méta-modèle ne remplace ni les gates ni la fusion à règles. Il reste en shadow
jusqu'à preuve de gain hors échantillon, stabilité multi-régimes et revue humaine.

## Incertitude et abstention

La synthèse s'abstient et renvoie `INSUFFICIENT_EVIDENCE` lorsque l'une des conditions
suivantes s'applique :

- aucune famille indépendante suffisante ;
- qualité ou fraîcheur sous le seuil de l'usage ;
- modèle expiré, drifté, non calibré ou hors domaine ;
- contradictions critiques non résolues ;
- incertitude supérieure au budget ;
- horizon, instrument, devise ou multiplicateur non résolu ;
- graphe incomplet ou preuve sans provenance.

L'abstention est un résultat normal mesuré par famille, régime et source. Elle ne doit
pas être contournée par un fallback sur la dernière valeur ou une phrase IA.

## Probabilités

Les trois notions restent disjointes :

1. probabilité implicite risque-neutre d'options ;
2. fréquence historique empirique d'un événement figé ;
3. probabilité physique prédictive calibrée.

Seule la troisième peut alimenter un champ prédictif, si `calibration_status=VALID`,
si la fenêtre d'évaluation est réellement hors échantillon et si `valid_until` n'est
pas dépassé. La calibration scikit-learn ou un intervalle MAPIE ne garantit pas une
prédiction parfaite ; la couverture doit être mesurée en walk-forward par régime.

## Exemple de synthèse, sans verdict

```text
entity: instrument exact
horizon: 5 séances
eligible_families: [market, options, events]
missing_families: [portfolio_risk]
descriptive_direction: MIXED
agreement: LOW
uncertainty: HIGH
critical_contradictions: [event_before_horizon, option_liquidity_degraded]
result: INSUFFICIENT_EVIDENCE
```

Ce résultat ne peut être converti en achat/vente et ne promet aucun rendement.

## Tests obligatoires

- permutations d'entrées donnant la même synthèse et le même hash ;
- signal dupliqué 1, 10 ou 1 000 fois sans augmentation de contribution ;
- features corrélées regroupées et plafonnées ;
- `BLOCK` qualité/droits jamais compensé par concordance directionnelle ;
- contradiction critique toujours visible et bloquante ;
- horizon ou `available_at` incohérent rejeté ;
- probabilité non calibrée, expirée ou hors échantillon absente de la sortie ;
- disparition d'une famille augmentant l'incertitude ou provoquant l'abstention ;
- mêmes entrées/versions/configuration produisant un résultat bit-à-bit stable ;
- recherche statique prouvant l'absence de second `AdviceEngine`, d'ordre et de
  formule financière dans le frontend ou l'IA.

## Mesures de production

- taux d'éligibilité et d'abstention ;
- nombre de familles indépendantes par synthèse ;
- contradictions par cause ;
- contribution/plafond par `correlation_group` ;
- âge, couverture et domaine de support ;
- dérive des distributions de features/signaux ;
- calibration et erreur hors échantillon pour les sorties prédictives ;
- différences champion/challenger et rollback.

## Sources officielles utiles

- [Calibration des probabilités — scikit-learn](https://scikit-learn.org/stable/modules/calibration.html), licence [BSD-3-Clause](https://github.com/scikit-learn/scikit-learn).
- [Anomaly et novelty detection — scikit-learn](https://scikit-learn.org/stable/modules/outlier_detection.html).
- [River — apprentissage en ligne](https://riverml.xyz/), licence [BSD-3-Clause](https://github.com/online-ml/river).
- [MAPIE — quantification conforme de l'incertitude](https://mapie.readthedocs.io/), licence [BSD-3-Clause](https://github.com/scikit-learn-contrib/MAPIE). MAPIE reste candidat recherche et ses hypothèses doivent être vérifiées pour chaque série temporelle.

