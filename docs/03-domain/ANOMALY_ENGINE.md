# Moteur d'anomalies

## Mandat et limite de sécurité

Le moteur d'anomalies détecte qu'une observation, une séquence ou le comportement
d'un modèle mérite une vérification. Il ne prédit pas à lui seul une hausse ou une
baisse, ne transforme pas une rareté en opportunité et ne déclenche jamais d'ordre.

Une anomalie est un **constat d'écart par rapport à une référence versionnée**, pas
une preuve de fraude, de causalité, de rendement futur ou d'erreur fournisseur. Un
score élevé ne peut ni franchir une gate bloquante ni produire un `AdviceResult`.
Seul l'unique `AdviceEngine` peut combiner un constat certifié avec les autres
preuves, et il reste fail-closed.

Il n'existe aucune promesse de détection à 100 %, de zéro faux positif ou de gain.
Quand les conditions de validité ne sont pas prouvées, le moteur s'abstient.

## Contrat canonique

Chaque exécution produit un `AnomalyAssessment` immuable :

```text
assessment_id, entity_id, usage, as_of, valid_until,
detector_id, detector_version, model_artifact_hash?, feature_set_id,
feature_snapshot_hash, training_cutoff?, calibration_window?,
score?, threshold?, state, severity?, uncertainty?,
quality_status, drift_status, reason_codes[], evidence_ids[],
limitations[], created_at, supersedes?
```

`state` vaut `NORMAL`, `WATCH`, `ANOMALY`, `UNKNOWN` ou `NOT_APPLICABLE`.
`severity` ne peut être renseignée que si son échelle et sa calibration sont
validées. Un score absent reste absent ; il n'est jamais remplacé par zéro.

Le contrat conserve séparément :

- le score brut propre au détecteur ;
- le seuil et sa version ;
- l'incertitude ou la stabilité observée ;
- la qualité des entrées ;
- l'alarme de drift ;
- les faits lisibles qui expliquent le constat.

## Défense en couches

### 0 — Qualité déterministe avant modèle

Les contrôles de schéma, identité, droits, horloge, fraîcheur, bid/ask, OHLC,
couverture, doublon et cohérence d'unité sont prioritaires. Une quote croisée, une
chaîne partielle ou un trou de données est un incident de qualité explicite, pas un
« signal de marché » donné à un modèle.

### 1 — Références robustes et interprétables

Médiane glissante, MAD, quantiles, IQR, variation relative et règles session-aware
forment le baseline. Les fenêtres n'utilisent que des valeurs disponibles avant
`as_of`, excluent les observations invalides et publient leur effectif réel. Ce
baseline reste le challenger obligatoire de tout modèle complexe.

### 2 — Anomalies multivariées batch

`IsolationForest` et, pour la nouveauté uniquement, `LocalOutlierFactor` de
scikit-learn peuvent être évalués en recherche. Les notions d'outlier et de novelty
ne sont pas interchangeables. Le contamination rate, le prétraitement et le seuil
sont appris uniquement dans les fenêtres autorisées, jamais sur la période test.

### 3 — Surveillance séquentielle

River peut fournir des détecteurs en ligne tels que `HalfSpaceTrees` pour un score
d'anomalie et ADWIN/Page-Hinkley pour une alarme de dérive. Un événement est d'abord
scoré, puis seulement appris lorsque la politique anti-contamination l'autorise.
Le système ne fait jamais `learn_one` avant `score_one` sur le même événement.

ADWIN ou Page-Hinkley sont des capteurs de changement, pas des preuves que le modèle
doit être automatiquement remplacé. Une alarme met le modèle en `WATCH`, augmente
l'incertitude et peut provoquer l'abstention ou une revue humaine.

### 4 — Ruptures et volatilité conditionnelle

`ruptures` est réservé à la segmentation **hors ligne** d'un historique coupé à
`as_of`. Une rupture détectée rétrospectivement ne doit jamais être antidatée comme
si elle avait été connue au moment du marché. Le délai de détection et la stabilité
du point de rupture sont conservés.

`arch` peut être évalué en recherche pour ARCH/GARCH/EGARCH et la volatilité
conditionnelle. Un échec de convergence, des résidus défaillants, une fenêtre trop
courte ou une prévision instable produit `UNKNOWN`. Une volatilité inhabituelle n'est
pas, en soi, une direction de marché.

## Temps, point-in-time et contamination

- Chaque feature possède `event_time`, `available_at`, version et règle de révision.
- Une exécution à `t` ne lit que les lignes avec `available_at <= t`.
- Les barres, univers, corporate actions, événements et fondamentaux utilisent leur
  vintage connu à `t`, pas leur version corrigée actuelle.
- Les fenêtres sont définies par calendrier de séance et nombre minimal
  d'observations ; aucun forward-fill silencieux ne traverse fermeture ou incident.
- Les labels retardés ne peuvent mettre à jour un modèle en ligne qu'après leur
  `label_available_at` réel.
- Un exemple dont l'horizon chevauche validation/test est purgé ; l'embargo défini
  par le protocole modèle s'applique après chaque fenêtre d'évaluation.
- Toute normalisation, imputation, sélection de variables et calibration est ajustée
  dans le train du fold, jamais avant le split.

## Seuils, abstention et faux positifs

Un seuil est propre à `detector × version × usage × classe d'actif × régime`. Il est
choisi sur une fenêtre de calibration séparée selon le coût documenté des faux
positifs/faux négatifs et la capacité de revue humaine. Le quantile d'un score n'est
pas une probabilité.

Le moteur retourne `UNKNOWN` et s'abstient au minimum lorsque :

- couverture, fraîcheur, droits ou identité sont insuffisants ;
- le nombre d'observations est inférieur au minimum validé ;
- le vecteur sort du domaine de support ou contient une unité inconnue ;
- le drift dépasse le seuil autorisé ou la calibration est expirée ;
- le modèle, son artefact, son registre de features ou son hash ne correspond pas ;
- plusieurs détecteurs critiques se contredisent sans politique validée ;
- l'incertitude ou le taux d'alertes excède le budget de revue.

Les seuils ne s'ajustent jamais automatiquement pour rendre une stratégie plus
attractive. Toute modification produit une nouvelle version et une validation.

## Anti-poisoning et apprentissage en ligne

- Les données `INVALID`, `CONFLICT`, `STALE` ou suspectes sont mises en quarantaine.
- Une anomalie non résolue n'entre pas immédiatement dans la référence « normale ».
- Les mises à jour utilisent un délai, une fenêtre de quarantine et une limite de
  masse par source/instrument.
- Snapshot avant mise à jour, journal des poids/états, seed et rollback sont requis.
- Aucun retrain ou reset de détecteur n'est promu automatiquement après drift.
- Un modèle en shadow reçoit les mêmes événements sans influencer les sorties live.
- Le champion précédent reste restaurable tant que le challenger n'a pas passé la
  durée et les régimes prévus par la validation.

## Rôle dans la fusion et l'interface

L'évaluation devient un nœud de preuve dans `EVIDENCE_GRAPH.md`. Elle est rattachée à
un groupe de corrélation afin qu'un choc de prix ne soit pas compté plusieurs fois
via rendement, ATR, volatilité et volume. `SIGNAL_FUSION.md` peut la résumer comme
contexte, risque ou contradiction ; il ne la transforme pas en probabilité.

L'interface affiche : type, état, score et seuil si valides, période de référence,
`as_of`, délai, variables principales, qualité, incertitude, source et « pourquoi je
vois ceci ? ». Elle offre une action de revue, jamais « acheter » ou « vendre ».

## Validation minimale

- chronologie point-in-time prouvée sur chaque fold ;
- données synthétiques avec anomalies connues, ordre inversé, doublons, trous,
  changement de régime et contamination ;
- taux de faux positifs, précision à capacité de revue, rappel lorsque les labels
  existent, délai de détection et stabilité du seuil ;
- résultats par instrument, liquidité, séance, régime et horizon, avec intervalles ;
- comparaison au baseline robuste et test de non-infériorité défini avant l'étude ;
- tests de replay, seed, idempotence, limites numériques, drift et rollback ;
- test prouvant qu'aucun `AnomalyAssessment` ne crée seul un `AdviceResult` ;
- surveillance live du taux d'alertes, des scores, entrées, erreurs et abstentions.

## Outils candidats et sources officielles

Les outils ci-dessous sont des candidats à évaluer ; leur présence ici ne vaut pas
approbation runtime. Versions et hashes doivent être verrouillés après revue.

| Outil | Usage envisagé | Licence | Sources officielles |
|---|---|---|---|
| Polars | Features columnaires lazy/streaming en recherche | MIT | [guide lazy](https://docs.pola.rs/user-guide/lazy/using/), [dépôt et licence](https://github.com/pola-rs/polars) |
| Apache Arrow/PyArrow | Schémas, datasets et Parquet versionnés | Apache-2.0 | [documentation Python](https://arrow.apache.org/docs/python/), [dépôt](https://github.com/apache/arrow), [licence](https://github.com/apache/arrow/blob/main/LICENSE.txt) |
| River | Score en ligne et drift | BSD-3-Clause | [documentation](https://riverml.xyz/), [HalfSpaceTrees](https://riverml.xyz/dev/api/anomaly/HalfSpaceTrees/), [ADWIN](https://riverml.xyz/dev/api/drift/ADWIN/), [dépôt/licence](https://github.com/online-ml/river) |
| ruptures | Ruptures hors ligne, uniquement historique arrêté | BSD-2-Clause | [documentation](https://centre-borelli.github.io/ruptures-docs/), [PELT](https://centre-borelli.github.io/ruptures-docs/user-guide/detection/pelt/), [dépôt](https://github.com/deepcharles/ruptures), [licence](https://github.com/deepcharles/ruptures/blob/master/LICENSE) |
| arch | Modèles de volatilité en recherche | NCSA | [documentation](https://bashtage.github.io/arch/), [prévisions](https://bashtage.github.io/arch/doc/univariate/univariate_volatility_forecasting.html), [dépôt](https://github.com/bashtage/arch), [licence](https://github.com/bashtage/arch/blob/main/LICENSE.md) |
| scikit-learn | Baselines batch, calibration, anomaly/novelty | BSD-3-Clause | [anomaly/novelty](https://scikit-learn.org/stable/modules/outlier_detection.html), [calibration](https://scikit-learn.org/stable/modules/calibration.html), [dépôt/licence](https://github.com/scikit-learn/scikit-learn) |
| MAPIE | Intervalles conformes, candidat recherche seulement | BSD-3-Clause | [documentation](https://mapie.readthedocs.io/), [choix d'algorithme](https://mapie.readthedocs.io/en/stable/choosing_the_right_algorithm.html), [dépôt/licence](https://github.com/scikit-learn-contrib/MAPIE) |

