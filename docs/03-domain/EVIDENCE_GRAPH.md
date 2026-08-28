# Graphe de preuves

## Rôle

Le graphe de preuves rend chaque nombre, signal, gate, verdict et explication
remontable jusqu'aux observations et versions qui l'ont produit. C'est un graphe de
provenance, **pas** une ontologie de causalité et pas un moteur de décision.

Le graphe est append-only, dirigé et acyclique. Une correction crée un nouveau nœud
et un lien `SUPERSEDES`; elle ne réécrit pas le passé. L'IA peut parcourir et citer
des nœuds autorisés, mais ne peut ajouter une preuve certifiée, inventer un lien ou
modifier un `AdviceResult`.

## Types de nœuds

| Type | Contenu | Producteur autorisé |
|---|---|---|
| `SOURCE_EVENT` | enveloppe reçue, droit, timestamps, hash | adaptateur |
| `CANONICAL_FACT` | observation/fait normalisé et identité | Data Fusion/domaine |
| `QUALITY_ASSESSMENT` | fraîcheur, couverture, conflit | data quality |
| `FEATURE_VALUE` | valeur du registre, fenêtre et disponibilité | moteur de features Python |
| `CALCULATION` | `CalculationRecord` | moteur quantitatif Python |
| `MODEL_RUN` | artefact, features, sortie et incertitude | runtime modèle approuvé |
| `ANOMALY_ASSESSMENT` | constat du moteur d'anomalies | anomaly engine |
| `SIGNAL` | `SignalEvidence` | signal fusion |
| `GATE` | `GateResult` | domaine décision |
| `ADVICE` | `AdviceResult` | unique `AdviceEngine` |
| `EXPLANATION` | rendu déterministe ou IA sourcé | couche explication |
| `REVIEW` | validation, rejet, note et auteur | utilisateur autorisé |

Un nœud contient une référence vers le payload canonique ; le graphe ne duplique pas
automatiquement un corps d'article, un secret ou une donnée dont les droits
interdisent la conservation.

## Enveloppe commune

```text
node_id, node_type, schema_version, entity_ids[],
event_time?, available_at, as_of, valid_until?, created_at,
producer, producer_version, code_sha, configuration_hash,
payload_ref, payload_hash, quality_status, rights,
trace_id, supersedes?, tombstone_reason?
```

Les identifiants sont immuables. `payload_hash` porte sur la représentation
canonique. `available_at` exprime la première heure à laquelle Vertex pouvait
l'utiliser ; `created_at` n'est jamais utilisé comme substitut.

## Types d'arêtes

```text
DERIVED_FROM, SUPPORTS, CONTRADICTS, BLOCKS,
DEGRADES, INVALIDATES, EXPLAINS, REVIEWS, SUPERSEDES
```

Chaque arête possède :

```text
edge_id, edge_type, from_node_id, to_node_id,
rule_id, rule_version, created_at, producer,
weight?, rationale_code, metadata_hash
```

`weight` est optionnel, local à une règle et jamais interprété comme probabilité.
Une arête `SUPPORTS` ne prouve pas une causalité. Une arête `CONTRADICTS` ne choisit
pas le vainqueur. `BLOCKS` et `DEGRADES` ne sont produits que par les gates autorisées.

## Invariants

1. Aucun cycle, y compris via `SUPERSEDES`.
2. Toute dérivation a au moins un parent et une règle versionnée.
3. Un parent a `available_at <= as_of` de l'enfant.
4. Un `FEATURE_VALUE` référence une entrée active de `feature-registry.yaml`.
5. Un `MODEL_RUN` référence artefact, feature snapshot, training cutoff et validation.
6. Un `SIGNAL` référence ses calculs/features/modèles et son groupe de corrélation.
7. Un `GATE` cite ses valeurs observées, seuils et preuves.
8. Un `ADVICE` provient d'un seul `AdviceEngine` et cite tous ses gates.
9. Une explication ne possède aucun fait absent de ses parents certifiés.
10. Un nœud révoqué ou expiré ne disparaît pas ; son statut empêche un nouvel usage.

## Construction transactionnelle

- L'objet métier et ses nœuds/arêtes sont enregistrés dans la même transaction ou
  via un événement outbox idempotent qui peut être rejoué.
- Une clé déterministe absorbe les doubles livraisons sans fusionner deux sources
  réellement distinctes.
- La validation du sous-graphe est effectuée avant publication.
- Le graphe accepté est immuable ; une erreur ultérieure produit
  `INVALIDATES`/`SUPERSEDES` et propage une réévaluation via l'outbox.
- La base transactionnelle reste PostgreSQL. Une base graphe dédiée n'est ajoutée
  qu'après benchmark et ADR ; elle ne devient jamais une seconde vérité.

## Requêtes obligatoires

### « Pourquoi je vois ceci ? »

Retourne les chemins courts depuis une news, un événement, une position manuelle ou
un signal jusqu'à l'élément UI, avec sources, fraîcheur, droits et règles.

### « D'où vient ce nombre ? »

Retourne feature/calcul, version, unités, entrées, hypothèses, tolérances et
`CalculationRecord` sans exposer de secret.

### « Pourquoi est-ce bloqué ? »

Retourne gate, seuil, valeur observée, preuve manquante ou contradictoire et action
de résolution. Un score favorable non pertinent n'est pas mélangé au chemin.

### « Qu'est-ce qui a changé ? »

Compare deux sous-graphes reliés par `SUPERSEDES` : nouvelle donnée, révision,
fraîcheur, modèle, configuration, gate ou contrainte utilisateur.

### Replay à une date

Reconstruit seulement les nœuds avec `available_at <= as_of`, les versions qui
étaient actives et les droits autorisés. Le replay doit produire le même hash ou une
différence explicitement expliquée.

## Droits, confidentialité et rétention

- `rights` gouverne lecture, stockage, dérivation, affichage et export par nœud.
- Le graphe conserve un hash et des métadonnées minimales si le payload ne peut être
  retenu ; il ne contourne jamais une licence fournisseur.
- Les données du portefeuille manuel et les thèses restent locales et ne sont jamais
  exportées vers une observabilité SaaS ou un fournisseur IA sans autorisation.
- Secrets, cookies, identifiants de session et compte IBKR sont interdits.
- Les explications filtrent les parents par droits de l'utilisateur avant rendu.
- Une demande de purge autorisée crée une tombstone auditée sans casser silencieusement
  les enfants ; ceux-ci deviennent inéligibles si la preuve requise n'est plus lisible.

## Lien avec l'incertitude et l'abstention

Le graphe conserve les preuves absentes attendues via des nœuds de qualité ou des
raisons stables. Une absence ne devient pas zéro. Si un chemin obligatoire est
manquant, expiré, conflictuel ou hors droits, la gate correspondante bloque ou
dégrade et l'abstention reste visible.

La largeur d'un intervalle, l'état de calibration, le drift, le domaine de support et
la taille de l'échantillon sont des parents du `MODEL_RUN`/`SIGNAL`, jamais une note
de bas de page détachée.

## Tests obligatoires

- propriétés génératives prouvant l'acyclicité et le rejet de parent futur ;
- doublon/replay donnant les mêmes nœuds, arêtes et hashes ;
- mutation d'un payload provoquant un hash différent ;
- révision conservant l'ancien sous-graphe et créant `SUPERSEDES` ;
- révocation de droits bloquant lecture/export et nouvelle décision ;
- chaque `AdviceResult` relié à tous ses gates, calculs et sources ;
- explication contenant uniquement des faits accessibles dans ses chemins parents ;
- contradiction et preuve manquante visibles dans la requête « pourquoi bloqué ? » ;
- charge sur profondeur/largeur maximales avec pagination et budgets ;
- absence de secret, donnée de compte IBKR et corps non licencié dans payloads/logs.

## Critères de qualification

- 100 % des calculs, modèles, signaux, gates et verdicts de fixtures possèdent une
  chaîne complète jusqu'à une source ou une absence explicitement justifiée ;
- zéro cycle sur les tests de propriété et la vérification périodique en base ;
- replay identique bit-à-bit pour un snapshot/version/configuration donnés ;
- p95 de la requête « pourquoi ? » sous 250 ms sur le dataset de référence ou budget
  documenté sans omettre de preuve ;
- aucune explication IA ne peut être enregistrée comme `CANONICAL_FACT`, `GATE` ou
  `ADVICE` ;
- aucune arête de modèle n'a la capacité de transmettre un ordre ou d'élever seule un
  statut vers `QUALIFIED`.

## Standards techniques officiels utiles

Le transport analytique peut utiliser les schémas et tables de
[PyArrow](https://arrow.apache.org/docs/python/) et les datasets
[Arrow](https://arrow.apache.org/docs/python/dataset.html), sous licence
[Apache-2.0](https://github.com/apache/arrow/blob/main/LICENSE.txt). Polars peut être
évalué pour les transformations lazy point-in-time, sous licence
[MIT](https://github.com/pola-rs/polars). Ces bibliothèques n'altèrent pas les
invariants du graphe et ne constituent pas une base de vérité indépendante.

