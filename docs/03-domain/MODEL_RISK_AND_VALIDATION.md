# Risque modèle et validation

## Politique générale

Un modèle est une approximation limitée, pas une source de vérité. Aucun modèle,
score, intervalle ou détecteur ne décide seul, n'ouvre un ordre et ne neutralise une
gate. Vertex ne revendique jamais 100 % de précision, de couverture ou de fiabilité.

L'absence de preuve vaut abstention. Un résultat de recherche ne rejoint le runtime
qu'après données point-in-time, validation hors échantillon, calibration, revue
indépendante, shadow mode, seuils de surveillance et rollback prouvé.

## Classes de risque

| Classe | Exemples | Effet maximal autorisé |
|---|---|---|
| M0 — déterministe | unités, contrôles de qualité | gate/résultat déterministe testé |
| M1 — descriptif | régime, clustering, anomalie | contexte, risque ou revue |
| M2 — prédictif | probabilité directionnelle, volatilité | preuve limitée et calibrée |
| M3 — fusion | méta-modèle, ranking | challenger de fusion, jamais verdict |

La criticité augmente avec l'effet potentiel, l'opacité, la sensibilité aux données,
la difficulté de labellisation et le risque de rétroaction. M2/M3 exigent une revue
indépendante de l'auteur et une autorisation humaine explicite.

## Dossier modèle obligatoire

Avant toute expérience, le dossier fixe :

- `model_id`, propriétaire, classe de risque, usage et utilisateurs ;
- cible/label exact, horizon et `label_available_at` ;
- univers point-in-time, exclusions et coût des erreurs ;
- features autorisées avec version du registre ;
- baseline, champion/challengers et hypothèse réfutable ;
- protocole de split, purge, embargo, calibration et holdout ;
- métriques primaires/secondaires, seuils de promotion et budget d'abstention ;
- domaines supportés, limites, équité par segments pertinents et usages interdits ;
- dépendances, licences, code SHA, seeds, artefacts et stratégie de rollback.

Changer label, horizon, univers, coût, feature set ou métrique primaire après examen
des résultats crée une nouvelle expérience ; le changement n'est pas réécrit dans
l'ancien dossier.

## Vérité point-in-time

Chaque ligne d'apprentissage possède au minimum :

```text
entity_id, event_time, available_at, decision_time,
label_start, label_end, label_available_at,
universe_vintage, feature_snapshot_hash, source_evidence_ids
```

Règles :

- `available_at <= decision_time` pour chaque feature et chaque jointure ;
- une révision n'existe qu'à partir de son heure de publication réelle ;
- univers, delistings, changements de symbole, splits, dividendes et ajustements OCC
  utilisent leur vintage ;
- aucun backfill ou forward-fill silencieux ; la politique d'imputation est apprise
  dans le train et produit un indicateur de manque ;
- normalisation, winsorisation, sélection, PCA, imputation et encodage vivent dans le
  pipeline ajusté sur le train du fold ;
- les données commerciales restent soumises à leurs droits d'usage et de rétention.

Un test automatique déplace artificiellement `available_at` après `decision_time` et
doit prouver que la ligne devient inaccessible.

## Walk-forward purgé avec embargo

Une division aléatoire ou une cross-validation IID est interdite pour les séries
temporelles de marché.

Pour chaque fold externe :

1. train chronologique ;
2. zone de purge ;
3. calibration/validation chronologique ;
4. test contigu futur ;
5. embargo avant toute réutilisation d'observations post-test dans un fold suivant.

Une observation train est purgée si son intervalle de label `[label_start,
label_end]` chevauche un intervalle de calibration ou de test. L'embargo est défini
en temps de marché et au minimum par l'horizon maximal, auquel s'ajoute la latence de
label/publication nécessaire. Les horizons variables sont traités par les intervalles
réels, pas par un simple nombre fixe de lignes.

`TimeSeriesSplit(gap=...)` de scikit-learn peut servir de primitive, mais ne suffit
pas à lui seul lorsque les labels se chevauchent ou ont des horizons variables. Le
splitter Vertex doit tester explicitement l'absence de chevauchement.

Les hyperparamètres utilisent des folds internes purgés. La calibration utilise une
tranche qui n'a pas servi à ajuster le modèle. Le dernier holdout contigu est gelé,
ouvert une seule fois après choix complet, et toute consultation est journalisée.

## Calibration et incertitude

### Classification

- calibration séparée de l'entraînement ;
- Brier score et log loss comme métriques primaires ;
- diagramme de fiabilité, erreur de calibration et sharpness en complément ;
- résultats par horizon, régime, famille d'instrument et liquidité ;
- intervalle par bootstrap en blocs, jamais bootstrap IID naïf ;
- probabilité masquée si calibration expirée, instable ou hors domaine.

Les méthodes scikit-learn telles que sigmoid/isotonic sont des candidates, pas une
garantie. Une méthode flexible exige suffisamment de données de calibration et doit
être comparée à la fréquence de base.

### Régression et prévision

- MAE, RMSE ou pinball loss définis avant l'étude selon l'usage ;
- intervalles avec couverture et largeur mesurées en rolling out-of-sample ;
- biais, résidus, stabilité et couverture par régime ;
- seeds et trajectoires conservées pour simulation/bootstrap.

MAPIE peut être évalué comme enveloppe conforme. Les garanties dépendent des
hypothèses de la méthode ; une série temporelle non échangeable et driftée exige une
méthode adaptée et une preuve empirique rolling. « Couverture nominale 95 % » ne
signifie ni couverture conditionnelle parfaite ni précision directionnelle de 95 %.

### Anomalies et ruptures

Le score d'anomalie n'a souvent pas de probabilité calibrée. La validation mesure
faux positifs par unité de temps, précision à capacité de revue, rappel si labels
fiables, délai, stabilité du seuil et robustesse à la contamination. Les ruptures
hors ligne enregistrent leur délai de disponibilité ; elles ne sont jamais antidatées.

## Métriques et décisions de promotion

Les métriques sont publiées avec effectif, intervalle, période, régime et baseline.
AUC seule, accuracy seule, rendement brut, meilleur fold ou meilleure variante ne
suffisent jamais.

Une promotion exige simultanément :

- amélioration hors échantillon selon la métrique primaire préenregistrée ;
- calibration et incertitude dans les budgets ;
- stabilité sur plusieurs folds, régimes et segments supportés ;
- absence de fuite et contrôles négatifs réussis ;
- coûts, slippage et disponibilité point-in-time lorsque l'usage les nécessite ;
- complexité, latence et mémoire sous budgets ;
- explication, abstention, monitoring et rollback fonctionnels ;
- licence et supply-chain approuvées ;
- validation indépendante et décision humaine documentée.

Les variantes testées et échecs sont conservés pour limiter le data snooping. Une
recherche massive de paramètres exige correction ou protocole de tests multiples.

## Contrôles négatifs et attaques

- labels permutés : aucune performance prédictive persistante ;
- feature future injectée : test de fuite doit échouer ;
- timestamps décalés, DST, demi-séance et ordre inversé ;
- univers survivant uniquement comparé à l'univers point-in-time ;
- trous, doublons, stale, conflit, source absente et entitlements perdus ;
- changement de régime, choc de volatilité et contamination graduelle ;
- features constantes, très corrélées, valeurs extrêmes et hors domaine ;
- version d'artefact/feature incompatible et modèle corrompu ;
- tentative de faire produire par le modèle ordre, verdict ou certitude.

## Cycle de vie

```text
PROPOSED → RESEARCH → VALIDATED → SHADOW → LIMITED → APPROVED
                                        ↘ QUARANTINED → RETIRED
```

- `PROPOSED`/`RESEARCH` : aucun accès runtime.
- `VALIDATED` : dossier complet, mais aucune influence live.
- `SHADOW` : données live, sorties non consommées par la décision.
- `LIMITED` : usage/horizon/univers bornés, avec kill switch humain.
- `APPROVED` : seulement dans le périmètre exact validé.
- `QUARANTINED` : drift, incident, incompatibilité ou métrique hors budget ; abstention.
- `RETIRED` : artefact conservé pour audit, jamais rechargé par défaut.

Un retrain crée une nouvelle version et repasse par validation/shadow. Aucun drift
detector ne déclenche seul promotion, retrain, reset ou rollback.

## Surveillance et seuils de retrait

- drift des inputs, valeurs manquantes et domaine de support ;
- drift de score/prédiction et taux d'abstention ;
- performance retardée lorsque les labels arrivent ;
- Brier/log loss, calibration, couverture/largeur des intervalles ;
- faux positifs et délai pour anomalies ;
- différences champion/challenger ;
- latence, mémoire, échecs, versions et hash ;
- qualité, fraîcheur, droits et changements de source.

Les seuils `WATCH`, `DEGRADE`, `QUARANTINE` et rollback sont définis avant promotion.
En l'absence de label suffisamment récent, le système ne suppose pas que le modèle
reste correct : il réduit sa validité puis s'abstient.

## Séparation recherche/runtime

Polars/Arrow/Parquet peuvent construire des snapshots de recherche immuables. Le
runtime ne charge que des artefacts signés/versionnés depuis un registre approuvé.
Les notebooks sont en lecture seule, sans secrets et sans écriture live. Un pickle ou
artefact mutable provenant d'un dossier de recherche n'est jamais chargé en production.

Le manifeste `manifests/model-candidates.yaml` ne vaut pas approbation. Le registre
des features `manifests/feature-registry.yaml` est la liste blanche de construction ;
une feature absente ou non `APPROVED` ne peut entrer dans un modèle runtime.

## Sources officielles et licences

- Polars : [API lazy](https://docs.pola.rs/user-guide/lazy/using/), [streaming](https://docs.pola.rs/user-guide/concepts/streaming/), dépôt/licence [MIT](https://github.com/pola-rs/polars).
- Apache Arrow/PyArrow : [documentation Python](https://arrow.apache.org/docs/python/), [datasets](https://arrow.apache.org/docs/python/dataset.html), [Parquet](https://arrow.apache.org/docs/python/parquet.html), dépôt/licence [Apache-2.0](https://github.com/apache/arrow).
- River : [documentation](https://riverml.xyz/), [ADWIN](https://riverml.xyz/dev/api/drift/ADWIN/), dépôt/licence [BSD-3-Clause](https://github.com/online-ml/river).
- ruptures : [documentation officielle](https://centre-borelli.github.io/ruptures-docs/), dépôt/licence [BSD-2-Clause](https://github.com/deepcharles/ruptures).
- arch : [documentation stable](https://bashtage.github.io/arch/), [prévision de volatilité](https://bashtage.github.io/arch/doc/univariate/univariate_volatility_forecasting.html), dépôt et licence [NCSA](https://github.com/bashtage/arch/blob/main/LICENSE.md).
- scikit-learn : [calibration](https://scikit-learn.org/stable/modules/calibration.html), [anomaly/novelty](https://scikit-learn.org/stable/modules/outlier_detection.html), [`TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html), dépôt/licence [BSD-3-Clause](https://github.com/scikit-learn/scikit-learn).
- MAPIE : [documentation](https://mapie.readthedocs.io/), [conformalisation](https://mapie.readthedocs.io/en/v1.3.0/split_cross_conformal.html), dépôt/licence [BSD-3-Clause](https://github.com/scikit-learn-contrib/MAPIE).

