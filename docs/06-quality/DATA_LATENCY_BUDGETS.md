# Budgets de latence des données

## Interprétation

Ces budgets sont des **objectifs provisoires à benchmarker**, pas des promesses de marché, de fournisseur ou de produit. Ils servent à rendre un ralentissement visible, à dimensionner les files et à décider quand passer en état dégradé. La source machine des valeurs est `manifests/performance-budgets.yaml` ; ce document en explique la sémantique.

La Beta Vertex 1.0 qualifie uniquement l'interface desktop aux viewports 1280×800, 1440×900 et 1600×1000. Le viewport laptop 1024×768 doit rester exploitable en mode dégradé explicite. Aucun viewport téléphone n'est un gate Beta ; l'interface mobile est `LATER` et devra réutiliser les contrats canoniques sans créer de DTO ni de calcul concurrent.

Avant qu'une baseline reproductible soit acceptée, un dépassement produit un rapport et une décision. Après activation explicite d'un gate, il bloque la PR ou la release selon `enforcement.stage`. Aucun budget de vitesse ne peut assouplir un gate de qualité, de droit, de précision ou de sécurité.

## Horloges et points de mesure

### Horodatages canoniques

| Champ | Producteur | Sens |
|---|---|---|
| `observed_at` | source/adaptateur | instant auquel la donnée décrit le marché |
| `published_at` | fournisseur | instant de publication lorsqu'il existe |
| `received_at` | première frontière Vertex | réception par Vertex, UTC |
| `admitted_at` | admission locale | entrée dans une file bornée |
| `committed_at` | PostgreSQL | commit durable de l'enveloppe |
| `quality_at` | moteur qualité | fin de l'évaluation de fraîcheur/couverture |
| `calculated_at` | worker | fin du calcul versionné |
| `api_sent_at` | API | sérialisation terminée |
| `client_received_at` | navigateur | réponse reçue |
| `painted_at` | navigateur | commit/rendu utile visible |

Les durées dans un même processus utilisent une horloge monotone. Les durées entre processus utilisent UTC synchronisé et enregistrent la dérive d'horloge. Si la dérive excède le seuil du manifeste, les mesures inter-processus sont marquées invalides et la donnée live concernée peut être bloquée ; on ne « corrige » pas une mesure négative en la mettant à zéro.

### Types de durée

- **Service time** : temps réellement exécuté par une étape.
- **Queue wait** : temps admis mais non commencé.
- **Provider wait** : attente d'une source externe, séparée du travail Vertex.
- **End-to-end** : somme observée aux frontières, jamais somme artificielle de percentiles.
- **Freshness age** : `now - observed_at`; ce n'est pas la latence de traitement.
- **Render ready** : visuel dominant et libellés d'état prêts, pas seulement premier byte.

## Niveaux et action

| Niveau | Définition | Action |
|---|---|---|
| `objective` | p95/p99 visés sur la machine et le dataset de référence | suivre la tendance |
| `investigate` | objectif dépassé sur une série valide de runs | profilage et issue avant optimisation |
| `degrade` | délai où l'expérience doit annoncer partial/stale/slow | réduire préfetch, servir état explicite |
| `timeout` | attente maximale d'une opération non durable | annuler/refuser avec raison ; jamais inventer |
| `safety` | exactitude, zéro perte durable, freshness et droits | bloque toujours, indépendamment de la vitesse |

Les p95/p99 ne sont calculés que si le nombre d'échantillons minimal, le warm-up, le profil machine et le dataset sont conformes. Un unique run « rapide » n'établit aucune baseline.

## Budgets end-to-end prioritaires

### HP-01 — Quote reçue localement vers écran

Mesuré à partir de `received_at` sur l'edge, donc hors délai de transport fournisseur antérieur.

| Segment | Objectif p95 | Objectif p99 | Dégradation |
|---|---:|---:|---:|
| admission + commit PostgreSQL | 120 ms | 400 ms | 750 ms |
| commit → qualité + snapshot | 120 ms | 400 ms | 750 ms |
| snapshot → invalidation SSE reçue | 250 ms | 750 ms | 1 500 ms |
| invalidation → snapshot peint | 250 ms | 750 ms | 1 500 ms |
| edge reçu → snapshot peint | 800 ms | 2 500 ms | 3 000 ms |

Contraintes de sécurité : zéro observation durable perdue ; epoch, droit et délai conservés ; une saturation ne prolonge pas `stale_after`. Une interface dépassant la dégradation affiche l'âge exact et l'état ; elle ne change pas la donnée en `offline` si seule la vue est lente.

### HP-02 — Webhook TradingView vers résultat persisté

| Segment | Objectif p95 | Objectif p99 | Limite/comportement |
|---|---:|---:|---|
| validation Worker + enqueue + réponse | 100 ms | 300 ms | timeout interne 2 500 ms |
| message disponible → pull local | 2 000 ms | 5 000 ms | alerte queue lag |
| pull → quote IBKR fraîche ou blocage expliqué | 3 000 ms | 8 000 ms | deadline 10 000 ms |
| pull → `AdviceResult` persisté si préconditions satisfaites | 4 000 ms | 10 000 ms | sinon statut fail-closed |

TradingView annule officiellement un webhook distant au-delà de trois secondes. Le Worker acquitte uniquement l'écriture durable et ne réalise pas la revalidation IBKR dans cette fenêtre. Le délai source/Internet reste ventilé et n'est pas imputé silencieusement à l'API locale.

### HP-03 — Snapshot de page

| Scénario | Objectif p95 | Objectif p99 | Gate maximal initial |
|---|---:|---:|---:|
| requête PostgreSQL chaude individuelle | 50 ms | 150 ms | 250 ms |
| API snapshot chaude, serveur seulement | 150 ms | 500 ms | 250 / 750 ms p95/p99 |
| API snapshot froide mais sans source externe | 500 ms | 1 500 ms | 2 000 ms |
| navigation avec cache client valide | 100 ms | 250 ms | 500 ms |
| interaction locale tri/filtre borné | 50 ms | 100 ms | INP 200 ms |

Le « cached » de l'API signifie snapshot PostgreSQL/CAS déjà calculé, jamais résultat gardé sans contrôle de hash et fraîcheur. Le test page inclut validation DTO, sérialisation, transfert HTTP local et commit React dans une mesure séparée end-to-end.

### HP-04 — Chaîne d'options lazy

| Étape | Objectif p95 | Objectif p99 | Comportement limite |
|---|---:|---:|---|
| expirations/classes depuis snapshot | 250 ms | 750 ms | état cache/stale visible |
| expiration sélectionnée depuis cache valide | 750 ms | 2 000 ms | couverture incluse |
| premier batch utilisable non caché | 3 000 ms | 8 000 ms | progressif, `PARTIAL` permis |
| fenêtre demandée complète ou état partiel final | 8 000 ms | 10 000 ms | à 10 s publier manquants |
| scroll/filtre local sur lignes déjà reçues | 50 ms | 100 ms | DOM virtualisé au seuil |

Les temps IBKR varient avec pacing, abonnement, séance et taille de fenêtre. Une chaîne reçue en moins de 10 secondes mais sans preuve de couverture n'est pas un succès complet. Le système ne précharge pas toutes les expirations ni toutes les ailes pour gagner un benchmark artificiel.

### HP-05 — Fusion d'information

| Étape | Objectif p95 | Objectif p99 | Limite |
|---|---:|---:|---:|
| événement local commité → normalisé disponible | 500 ms | 2 000 ms | 5 000 ms |
| fin de micro-batch → clusters/vues publiés | 1 000 ms | 3 000 ms | 10 000 ms |
| nouvelle source → item d'attention peint | 2 000 ms | 8 000 ms | 15 000 ms |

`published_at → received_at` est rapporté séparément comme délai fournisseur. Le classement de pertinence peut prendre du retard sans bloquer l'accès à l'observation brute autorisée ; l'UI affiche alors « enrichissement en cours ».

### HP-06 — Calcul

| Type | Objectif p95 | Objectif p99 | Politique |
|---|---:|---:|---|
| calcul déterministe léger déjà admis | 100 ms | 300 ms | API ou worker selon profil CPU |
| création idempotente d'un job lourd | 150 ms | 500 ms | réponse avec identifiant/progrès |
| première progression utilisateur | 500 ms | 1 000 ms | sinon état `queued` explicite |
| cancellation cooperative observée | 250 ms | 1 000 ms | après point sûr du calcul |

La durée finale d'un backtest, d'une calibration ou d'une simulation dépend d'un budget par algorithme, taille et erreur cible. Aucun nombre global ne déclare tout calcul lourd « rapide ».

### HP-07 — Historique et visualisation

| Scénario | Objectif p95 | Objectif p99 | Limite |
|---|---:|---:|---:|
| fenêtre ≤ 2 000 barres depuis snapshot chaud | 250 ms | 750 ms | 1 500 ms |
| scan 1 M lignes + filtre + downsampling serveur | 1 000 ms | 3 000 ms | 5 000 ms |
| rendu initial graphique prix desktop | 200 ms | 500 ms | points budgetés |
| mise à jour incrémentale du graphique | 16,7 ms | 33,3 ms | pas de `setData` récurrent |
| pan/zoom depuis cache voisin | 100 ms | 250 ms | fetch annulable en fond |

Le temps de scan enregistre lignes et octets effectivement lus, colonnes projetées, partitions prunées, batch size, readahead, threads et peak RSS. Une réduction rapide qui omet un gap ou un extrême échoue sur la justesse.

## Budgets de batch et backpressure

### Paramètres initiaux à calibrer

| Mécanisme | Valeur initiale | Pourquoi |
|---|---:|---|
| micro-batch ingestion `max_wait` | 25 ms | amortir transaction sans masquer le live |
| micro-batch ingestion `max_items` | 500 | borner transaction et mémoire |
| micro-batch ingestion `max_bytes` | 1 MiB | éviter payload dominant |
| claim outbox | 100 jobs | lease court et partage équitable |
| coalescence SSE par ressource | 50 ms | éviter refetch par tick |
| file admission générale | 1 024 items | point de départ, à profiler par type |
| file requêtes options | 256 items | protéger pacing et mémoire |
| high-water / critical | 75 % / 90 % | agir avant saturation |

Ces nombres ne remplacent pas les limites officielles de chaque fournisseur. Si la taille moyenne rend le budget octets plus strict que `max_items`, le budget octets gagne. Les messages P0/P2 durables ne sont jamais abandonnés pour respecter une latence.

### Objectifs de récupération

- Sous burst de référence : zéro perte durable et aucun deadlock.
- À `high_water` : préfetch/backfill arrêtés en moins d'une seconde.
- À `critical` : admission non prioritaire refusée ou différée avec raison.
- Après fin du burst : retour sous 50 % de capacité en moins de 30 secondes sur le profil de référence.
- Event-loop lag API : p95 < 20 ms, p99 < 100 ms sous charge nominale.
- Aucun retry sans jitter/backoff ni boucle de refetch offline.

## Budgets de cache

| Couche | Hit p95 | Hit p99 | Contrôle prioritaire |
|---|---:|---:|---|
| L0 objet mémoire | 2 ms | 5 ms | limite taille/TTL et hash |
| L1 snapshot PostgreSQL | 50 ms | 150 ms | version, as-of, qualité |
| L2 CAS local ≤ 10 MiB | 100 ms | 300 ms | checksum + droits |
| L3 TanStack Query | 16,7 ms | 50 ms | staleTime et rendu |

Objectifs non temporels : hit ratio rapporté mais jamais optimisé en servant une entrée périmée ; 100 % des entrées L2 ont checksum/métadonnées ; 0 corruption silencieuse ; `singleflight` empêche plus d'un producteur simultané par clé ; un miss reste fonctionnel.

## Budgets frontend

Les Web Vitals existants restent : LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1. Ils sont testés au p75 par profil/route pertinent, sans les confondre avec p95 API.

| Élément | Objectif |
|---|---:|
| bundle initial gzip | ≤ 300 KiB recommandé |
| moteur graphique | chunk de route, jamais dans `/today` sans besoin |
| points initiaux desktop | ≤ 4 000 |
| points par pixel CSS | ≤ 2 |
| lignes DOM de table virtualisée | ≤ 160 |
| overscan lignes | ≤ 20 par côté |
| long task ordinaire | aucune > 50 ms |
| commit React interaction p95 | ≤ 50 ms |
| mémoire JS après navigation répétée | plateau, pas de croissance monotone |

La virtualisation n'est pas automatique pour une petite liste. Le seuil initial est 200 lignes et doit être mesuré avec clavier, lecteur d'écran et hauteurs variables.

## Ressources et stabilité

Les limites RSS du manifeste servent de détecteurs initiaux, pas de dimensionnement universel. Chaque rapport enregistre CPU, RAM, disque, OS, navigateur, versions et autres processus actifs.

- API : aucun traitement CPU lourd et RSS stable sous 30 minutes nominales.
- Worker : mémoire bornée par job/batch et rejet avant OOM.
- Edge : callbacks courts, files bornées, reconnexion prioritaire.
- Navigateur : disposer graphiques/listeners/observers à la navigation.
- PostgreSQL : pool borné, transactions courtes, autovacuum/statistiques visibles.
- Soak 8 h : croissance RSS entre les deux dernières heures ≤ 5 % après GC/compaction attendue, aucun backlog monotone.

## Freshness et latence

La fraîcheur est évaluée par politique métier, pas par ces budgets. Exemples :

- un traitement en 100 ms d'une quote déjà vieille reste stale ;
- un traitement en 2 s d'un filing confirmé peut rester valide si sa politique le permet ;
- un cache à hit 2 ms n'améliore pas `observed_at` ;
- une chaîne partielle très rapide reste `PARTIAL` ;
- offline conserve la dernière valeur avec âge, sans nouveau verdict live.

Le budget de latence peut déclencher une dégradation plus tôt que `stale_after`, mais jamais repousser `stale_after`.

## Mesure et agrégation

- Utiliser des histograms Prometheus avec buckets entourant objectifs et dégradations ; ne pas publier p95/p99 calculés côté application comme gauges.
- Calculer les quantiles sur une fenêtre et une population homogènes ; séparer route, état cache, profil machine et classe de scénario.
- Ne jamais utiliser ticker, `instrument_id`, texte d'actualité, portefeuille ou trace ID comme label métrique.
- Relier un cas lent à une trace OpenTelemetry via exemplar ou log corrélé.
- Propager `traceparent` entre API, worker et edge ; ne pas mettre secrets ou données financières en baggage.
- Conserver résultats bruts, configuration, commit, hashes de dataset et manifeste dans l'artefact du run.

## Sources officielles utiles à l'interprétation

- [Prometheus — Histograms and summaries](https://prometheus.io/docs/practices/histograms/) explique pourquoi les histograms sont agrégables entre processus, contrairement aux quantiles de summaries.
- [Prometheus — Instrumentation](https://prometheus.io/docs/practices/instrumentation/) recommande une cardinalité de labels faible.
- [OpenTelemetry — Context propagation](https://opentelemetry.io/docs/concepts/context-propagation/) fournit la corrélation causale entre étapes.
- [PostgreSQL — EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) précise qu'`EXPLAIN ANALYZE` exécute la requête et ne couvre pas automatiquement tout le coût client/réseau.
- [TanStack Query — Important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults) montre que `staleTime` vaut zéro par défaut ; Vertex le remplace par la politique serveur.
- [TradingView — Webhook alerts](https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/) fixe la contrainte externe de réponse à trois secondes.

Les valeurs Vertex ne viennent pas de ces sources : elles constituent une hypothèse produit révisable par benchmark. Toute modification exige un résultat avant/après, un risque métier et une mise à jour synchronisée de ce document et du manifeste.
