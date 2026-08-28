# Plan de tests de performance

## But

Prouver que Vertex One reste exact, réactif et borné sur une architecture locale, y compris sous burst, données partielles, cache froid et déconnexion. Ce plan mesure les objectifs provisoires de `manifests/performance-budgets.yaml`; il ne transforme pas ces objectifs en promesses.

L'ordre de décision est immuable :

1. exactitude et sécurité ;
2. zéro perte d'événement durable ;
3. fraîcheur, droits et couverture corrects ;
4. stabilité mémoire/CPU/files ;
5. latence et débit.

Un run rapide qui perd une donnée, masque `stale`, modifie un résultat ou contourne le pacing est un échec.

## Questions auxquelles répondre

- L'event loop API reste-t-elle disponible quand les workers calculent ou scannent un historique ?
- Les files bornées ralentissent-elles proprement avant saturation ?
- PostgreSQL absorbe-t-il le débit nominal et les bursts sans backlog monotone ?
- Le cache par hash est-il exact, résistant au stampede et réellement utile ?
- La chaîne d'options progressive fournit-elle vite un premier lot sans prétendre être complète ?
- Projection, predicate pushdown, batch et downsampling réduisent-ils octets, mémoire et durée ?
- Les snapshots de page évitent-ils N+1, waterfalls et payloads inutiles ?
- Les tables, React et les graphiques restent-ils interactifs sur les trois viewports desktop Beta et le laptop dégradé ?
- Les états `partial`, `delayed`, `stale`, `offline` et `error` restent-ils visibles sous charge ?
- L'observabilité aide-t-elle à localiser le goulot sans cardinalité ni coût excessifs ?

## Non-objectifs

- mesurer la vitesse publique d'IBKR, TradingView ou Internet comme une garantie Vertex ;
- utiliser des données personnelles, commerciales ou réelles dans la CI ;
- optimiser un microbenchmark sans effet sur un hot path ;
- battre un autre framework ou justifier une dépendance par réputation ;
- ajouter Redis, TimescaleDB ou davantage de workers avant preuve ;
- exécuter un test de PR sur la machine où TWS de production est ouvert.

## Autorités et artefacts

- Budgets machine : `manifests/performance-budgets.yaml`.
- Sémantique : `DATA_LATENCY_BUDGETS.md`.
- Architecture : `docs/02-architecture/HOT_PATHS_AND_CACHING.md`.
- Exactitude : contrats, invariants, golden vectors et `TEST_STRATEGY.md`.
- Résultat d'un run : artefact immuable lié à `git_sha`, hash du manifeste, hash du dataset et profil machine.

Un rapport sans l'un de ces identifiants est informatif uniquement et ne peut créer ou remplacer une baseline.

## Profils d'exécution

### P-CI — Régression relative

Runner GitHub hébergé et isolé autant que possible. Il sert aux smoke tests et comparaisons avant/après dans le même workflow. Ses latences absolues ne qualifient pas une release locale.

À enregistrer : image runner, CPU visible, RAM, disque, noyau, charge initiale, versions Python/Node/PostgreSQL/navigateur et durée de queue GitHub.

### P-LOCAL — Machine de marché de référence

Machine locale dédiée au test, configuration proche de la cible, mais TWS réel déconnecté ou en paper/read-only selon le scénario autorisé. Le profil doit capturer :

- modèle CPU, cœurs/threads et gouverneur ;
- RAM, swap/pagefile et pression mémoire ;
- type/capacité/espace libre du disque et chiffrement ;
- OS/build, système de fichiers et runtime conteneur ;
- versions exactes des runtimes et images ;
- écran, navigateur, accélération GPU et zoom ;
- HTTP local et latence réseau de base ;
- processus concurrents, antivirus et mode alimentation.

La première exécution remplit ces métadonnées. Le manifeste ne suppose pas un matériel que l'utilisateur n'a pas encore désigné.

### P-DESKTOP — Matrice d'interface Beta

La qualification complète s'exécute à 1280×800, 1440×900 et 1600×1000. Le profil 1024×768 vérifie la dégradation laptop : aucune vérité financière, provenance, alerte ou action essentielle ne peut être masquée, tronquée ou rendue inaccessible, même si la densité et le nombre de modules simultanément visibles diminuent.

Tester clavier, zoom 200 %, reduced motion et lecteur d'écran séparément de la charge maximale. Aucun viewport téléphone ne fait partie du QA Beta. L'interface mobile reste `LATER` et devra consommer les mêmes contrats canoniques.

## Jeux de données synthétiques

Chaque générateur est déterministe, versionné, seedé et produit un manifest de hash. Les timestamps couvrent DST, demi-séance, jours fériés, gaps, données hors ordre et révisions.

| Dataset | Instruments | Observations/barres | Contrats option | News/événements | Usage |
|---|---:|---:|---:|---:|---|
| S — smoke | 100 | 100 000 | 5 000 | 2 000 | PR rapide |
| R — référence | 1 000 | 10 000 000 | 250 000 | 100 000 | nightly/release |
| X — stress | 5 000 | 50 000 000 | 1 000 000 | 1 000 000 | limites et capacity planning |

Le dataset R inclut au minimum :

- 250 instruments suivis activement et 750 froids ;
- expirations partageant dates mais différant par `trading_class`/multiplicateur ;
- chaînes de 400, 2 000 et 10 000 contrats pour tester la fenêtre lazy ;
- 200 lots de portefeuille manuel et 100 thèses ;
- news dupliquées, clusters, filings et corporate events révisés ;
- quotes live/delayed/frozen, epoch ancien, droits absents et conflits ;
- 5 millions de lignes dans une seule fenêtre historique pour le test columnar ciblé ;
- payloads près des limites de taille, jamais de secret ou identifiant réel.

Les datasets S/R/X sont des enveloppes de capacité, pas une estimation de l'abonnement réel.

## Protocole commun

### Préparation

1. Checkout propre au SHA testé et lockfiles gelés.
2. Base PostgreSQL 18 créée/restaurée depuis une fixture hashée.
3. Cache L0/L2/L3 vidé pour run froid ; état explicitement préchauffé pour run chaud.
4. Horloges synchronisées et dérive mesurée.
5. Télémétrie, sampling, logs et niveau de debug fixés dans le manifest du run.
6. Machine stabilisée : alimentation, température, espace disque, absence de job concurrent inconnu.
7. Warm-up séparé et exclu des percentiles.

### Échantillonnage

- Au moins 5 répétitions indépendantes pour une baseline release.
- Au moins 1 000 observations homogènes pour p95 ; 10 000 pour utiliser p99 comme gate.
- Durée nominale ≥ 15 minutes ; soak 8 heures.
- Publier p50, p90, p95, p99, max, moyenne, écart-type, erreurs, throughput, queue wait et service time.
- Publier intervalle de confiance/bootstrap lorsque le test compare deux implémentations.
- Ne pas fusionner froid/chaud, succès/timeout, viewports desktop/laptop ou datasets différents.
- Conserver les valeurs brutes ; une capture Grafana seule n'est pas une preuve.

### Comparaison

Comparer à une baseline du même profil, dataset, manifeste et versions externes. Une variation de matériel ou PostgreSQL crée une nouvelle série.

- dérive < 10 % : surveiller ;
- dérive 10–20 % : avertissement et profil obligatoire ;
- dérive > 20 % sur p95 ou ressource critique : blocage si répétée sur au moins trois runs comparables ;
- amélioration de latence avec régression d'exactitude, mémoire non bornée ou perte durable : rejet immédiat.

Ces seuils de régression sont initiaux et révisables avec le même niveau de preuve.

## Scénarios backend

### T-API-01 — Event loop non bloquée

- Injecter charge I/O nominale sur snapshots et SSE.
- En parallèle, déclencher calcul CPU, scan Parquet, sérialisation lourde et écriture fichier via les chemins prévus.
- Mesurer event-loop lag, latence route santé/snapshot, threadpool, pool DB et CPU par processus.
- Faire échouer le test si un calcul lourd s'exécute dans l'event loop, même si le p95 global passe.
- Vérifier cancellation et shutdown pendant l'opération.

FastAPI exécute une route `def` dans un threadpool, mais ce mécanisme n'est pas un pool de calcul illimité. Le worker reste la destination des tâches CPU.

### T-ING-01 — Ingestion nominale, burst et recovery

| Phase | Charge synthétique | Durée |
|---|---:|---:|
| warm-up | 50 événements/s | 2 min |
| nominal | 100 événements/s | 15 min |
| burst | 1 000 événements/s | 30 s |
| recovery | 100 événements/s | 5 min |

Mesurer admission, queue depth, wait, batch fill, transactions/s, WAL, locks, commit, quality, outbox, RSS et CPU. Vérifier : zéro perte durable, hashes/comptages identiques, retour sous 50 % de file dans le budget et aucun TTL prolongé.

Répéter avec : doublons 20 %, désordre, événement futur, epoch invalide, payload maximal, disque ralenti et PostgreSQL momentanément indisponible.

### T-BP-01 — Backpressure

1. Saturer progressivement P4, puis P3, P2 et P1 avec producteurs contrôlés.
2. Prouver arrêt du prefetch/backfill à high-water.
3. Prouver admission réservée à P0, absence de starvation et hysteresis.
4. Vérifier `429/503 + Retry-After` pour non-durable et absence d'ack pour durable non commité.
5. Restaurer le consommateur et vérifier ordre, idempotence, queue age et recovery.
6. Exécuter un producteur non coopératif pour vérifier timeout/circuit de protection.

### T-OUTBOX-01 — Leases concurrents

- 1, 2, 4 et 8 consommateurs sur backlog 100 000.
- Crash avant/après commit, lease expiré, message poison et retry avec jitter.
- Mesurer throughput, locks, duplications de tentative, effets uniques et équité.
- Comparer tailles de claim 10/50/100/500 ; adopter seulement le meilleur compromis documenté.
- Perdre volontairement `NOTIFY` et prouver que le polling durable vide la table.

### T-DB-01 — Plans et partitions

Pour chaque requête hot path :

- exécuter froid/chaud avec `EXPLAIN (ANALYZE, BUFFERS, WAL, SETTINGS, SERIALIZE)` lorsque sûr ;
- conserver plan JSON, estimé/réel, buffers, rows removed, partitions prunées et temps de sérialisation ;
- vérifier index-only/bitmap/sequential selon cardinalité réelle plutôt que forcer un index ;
- tester frontière de partition, pagination keyset, dernier intervalle chaud et historique froid ;
- mesurer coût d'écriture de chaque index et taille totale ;
- refaire après `ANALYZE` et sur base restaurée.

Un plan est rejeté si le pruning attendu manque, si un N+1 apparaît, si une estimation est massivement fausse ou si l'index gagne 5 ms au prix d'une write amplification non acceptable.

### T-CACHE-01 — CAS et coalescence

Matrice : L0/L1/L2 froid/chaud, entrée valide/stale/partial/delayed, hit/miss/corruption, 1/20 producteurs simultanés.

Prouver :

- clé identique pour entrées canonically identiques ; clé différente pour code, politique, entitlement, résolution ou input modifié ;
- un seul producteur par clé sous stampede ;
- checksum vérifié et corruption traitée comme miss + incident ;
- pointeur publié seulement après écriture atomique complète ;
- aucune fuite entre scopes de droit ;
- GC ne supprime aucun artefact référencé ;
- un cache totalement désactivé conserve exactitude et fonctionnalité.

Mesurer hit/miss, latence, octets lus, temps de hash, RSS, espace disque, duplication évitée et temps de reconstruction. Ne jamais augmenter artificiellement le hit ratio en ignorant `stale_after`.

### T-COL-01 — Polars/PyArrow A/B

Ce test précède toute adoption runtime de Polars ou PyArrow.

Cas : filtre d'instruments/plage, projection OHLCV, agrégation par bucket, export Parquet, cluster événementiel simple et lecture 1 M/5 M/50 M lignes selon dataset.

Comparer l'implémentation de référence autorisée avec :

- Polars eager vs lazy `scan_parquet` ;
- plan lazy avec/sans projection/predicate pushdown ;
- PyArrow Dataset Scanner par `RecordBatch` et `to_table` ;
- batch sizes et readahead bornés ;
- nombre de threads borné pour ne pas affamer API/PostgreSQL ;
- memory map Arrow IPC et lecture Parquet, sans présumer zero-copy.

Collecter : plan optimisé, colonnes/lignes/octets lus, durée, CPU, peak RSS/Arrow memory pool, copies/conversions, taille de sortie et hash résultat. Tous les candidats doivent produire le même résultat canonique ou une tolérance explicitement autorisée. L'adoption exige gain end-to-end matériel, mémoire bornée, licence/pin/ADR et absence de nouvelle autorité.

### T-OPT-01 — Chaîne d'options progressive

Utiliser fake TWS contrôlant pacing, erreurs, latence et droits.

- Charger seulement métadonnées, expiration choisie et fenêtre de strikes.
- Scénarios 400/2 000/10 000 contrats, 0/20/50 % données manquantes.
- Pacing normal, throttling, reconnexion 1100/1101/1102 et epoch remplacé.
- Mesurer first usable batch, progression, deadline partielle, lignes actives, mémoire et cancellation après changement d'expiration.
- Vérifier que l'ancienne requête ne repeint pas la nouvelle sélection.
- Vérifier couverture, `trading_class`, multiplicateur, live/delayed et source sur chaque résultat.

Une stratégie qui charge la chaîne entière avant d'afficher est refusée, même si elle passe sur la petite fixture.

### T-QUANT-01 — Worker et fairness

- Mélanger calculs légers, simulations lourdes et jobs de fusion.
- Tester 1..N workers CPU jusqu'au point où API/DB se dégradent.
- Mesurer admission, wait, run, cancellation, RSS par job, progression et cache hit.
- Prouver qu'un gros job ne bloque pas quote fraîche, qualité ou demande utilisateur prioritaire.
- Rejouer même clé et vérifier un seul `CalculationRecord` autoritaire/résultat identique.
- Vérifier seed, version, hash et absence de thread BLAS non borné.

## Scénarios API et frontend

### T-HTTP-01 — Snapshots

Routes représentatives des 12 pages, avec 1, 5 et 20 clients simulés plus deux connexions SSE. Matrice cache L1/L2 chaud/froid, payload normal/max et gzip/brotli selon le serveur local.

Collecter TTFB, download, validation, taille compressée/non compressée, requêtes SQL, pool wait, sérialisation et erreurs. Vérifier cohérence `as_of`, aucun N+1 et aucune requête externe déclenchée par une simple lecture.

### T-SSE-01 — Invalidation

- 1 000 changements/s en entrée pendant 30 s sur ressources répétées et distinctes.
- Vérifier coalescence par ressource/version, ordre utile, reconnexion et Last-Event-ID si retenu.
- Mesurer événements envoyés, refetches clients, payload, CPU et mémoire.
- Prouver qu'une invalidation perdue est réparée par refetch/refresh périodique sans faire du SSE une file durable.

### T-WEB-01 — React et TanStack Query

- Navigation froide/chaude et aller-retour 100 fois entre pages lourdes.
- Saisie rapide d'un filtre avec résultats lents, cancellation des queries obsolètes et `useDeferredValue` seulement si profilé utile.
- Offline pendant fetch, reconnexion, stale cache, partial response et erreur isolée.
- Profiler React : temps de render/commit, composants rerendus, long tasks et heap snapshots.
- Vérifier que `staleTime` vient du DTO/policy et que `gcTime` ne transforme pas une donnée en fraîche.
- Rechercher waterfall, invalidation globale, query key incomplète et listeners non disposés.

### T-TABLE-01 — Table virtualisée

Rendre 50, 200, 1 000 et 10 000 lignes avec hauteurs fixes/variables, tri serveur, sélection et mise à jour. Mesurer nombre de nœuds DOM, FPS, commit, scroll, heap et overscan.

Tester clavier, focus après virtualisation, lecteur d'écran et zoom 200 % aux trois viewports de livraison et au smoke test laptop `1024×768`. Une table rapide qui perd l'ordre de lecture ou le focus échoue. Ne pas virtualiser 50 lignes si la complexité n'apporte pas de gain mesuré.

### T-CHART-01 — Graphiques

Lightweight Charts : 500/2 000/4 000 points initiaux, puis 10/100/1 000 updates/s synthétiques. Comparer `update` au chemin interdit récurrent `setData` pour établir un test de régression, sans retenir ce dernier.

ECharts : SVG/Canvas, import complet/minimal, 500/1 000/4 000/20 000 éléments, animations activées/désactivées. Mesurer chunk gzip, parse/eval, first render, update, FPS, heap et dispose.

Downsampling : vérifier open/high/low/close/volume, gaps, sessions, extrema, compte original/retourné et hash algorithme. Tester les viewports 1280×800, 1440×900, 1600×1000 et le laptop dégradé 1024×768, avec pan/zoom annulable.

### T-WEB-02 — Web Vitals et accessibilité sous charge

Lighthouse CI et mesures terrain/lab sur les 12 routes aux trois viewports desktop `1280×800`, `1440×900` et `1600×1000`, avec CPU/réseau contrôlés. Le profil `1024×768` reste un smoke test séparé de dégradation laptop. Publier LCP, INP, CLS, TBT, taille/requests et screenshot filmstrip.

Répéter avec `partial`, `stale`, `offline` et texte long. Les badges/alternatives doivent être disponibles avant ou avec le visuel ; le lazy loading ne peut cacher l'état de qualité.

## Pannes et chaos ciblé

- PostgreSQL indisponible 5 s, lent, pool épuisé puis retour.
- Disque à 90/95/100 %, écriture CAS interrompue et checksum faux.
- Worker tué au milieu d'un batch/calcul et lease expiré.
- Edge déconnecté/reconnecté avec nouvel epoch.
- Clock skew ±3 s et timestamp futur.
- Liaison HTTP locale lente/coupée, navigateur offline puis reconnecté.
- Queue pleine, message poison, source delayed et entitlement perdu.
- OTel/Prometheus indisponible : l'application continue sans bloquer le hot path.

Chaque panne vérifie latence de détection, état UI, perte, retry, récupération, backlog et absence de fallback silencieux.

## Observabilité du test

### Traces OpenTelemetry

Un trace ID relie edge/admission/DB/outbox/worker/API/client pour les scénarios contrôlés. Auto-instrumentation couvre HTTP/DB ; spans manuels couvrent queue wait, batch, quality, cache, downsampling et calculation. Le sampling du test est déclaré et le coût est mesuré avec/sans instrumentation.

### Métriques Prometheus

- histograms avec buckets autour des budgets ;
- counters de résultats et saturation ;
- gauges de capacité/backlog/RSS, jamais quantile calculé côté app ;
- labels bornés : service, route templatisée, hot_path, outcome, cache_state, quality_class ;
- ticker, instrument, portefeuille, news ID et trace ID interdits comme labels.

### Profils

Utiliser profils CPU, allocations, heap navigateur et plans SQL seulement sur runs dédiés ; leur overhead invalide une mesure absolue si mélangé au run de référence. Un profil doit pointer vers la même opération/trace lente.

## Gates par cadence

### PR

- dataset S ;
- lint/validation du manifeste ;
- event-loop blocking sentinel ;
- API snapshot smoke ;
- idempotence/backpressure smoke ;
- cache key/corruption ;
- rendu page critique, bundle et long task ;
- comparaison relative avec avertissement 10 %, blocage répété 20 %.

Durée cible de cette suite : courte et stable ; les tests statistiques lourds n'y sont pas compressés au point de perdre leur sens.

### Nuit

- dataset R ;
- ingestion nominale/burst, outbox concurrence, plans PostgreSQL ;
- chaînes options 400/2 000/10 000 ;
- Polars/PyArrow A/B lorsque candidat ;
- 12 routes, charts/tables, trois navigateurs ;
- p95/p99 avec volumes suffisants ;
- chaos court et rapport de régression.

### Release

- cinq runs reproductibles P-LOCAL sur dataset R ;
- dataset X au moins une fois pour connaître la rupture ;
- soak 8 h ;
- backup/restore avant/après ;
- matrice desktop 1280×800, 1440×900 et 1600×1000, plus dégradation laptop 1024×768 ;
- TWS paper/read-only strictement information-only pour un smoke d'intégration autorisé ;
- tous les invariants sécurité/qualité, baseline acceptée et exceptions signées.

## Critères d'acceptation

### Toujours bloquants

- perte d'un événement durable ou effet dupliqué non idempotent ;
- donnée stale/delayed/partial/offline présentée comme live/complète ;
- résultat financier différent hors tolérance autorisée ;
- file, mémoire, tâches, connexions ou DOM non bornés ;
- CPU lourd dans l'event loop ;
- cache sans hash/checksum/droit ou corruption silencieuse ;
- secret/donnée réelle dans fixture, trace, métrique ou rapport ;
- capacité IBKR ordre/compte/position/exécution ;
- benchmark non reproductible utilisé pour adopter Redis ou une dépendance.

### Performance

- Les objectifs activés comme gates passent sur le profil défini.
- Les objectifs encore provisoires possèdent baseline, écart et décision `accept|optimize|resize|defer`.
- Une exception liste owner, cause, impact UX/finance, mitigation, échéance et critère de fermeture.
- Le système atteint un plateau de ressources, récupère après burst et conserve l'interactivité.
- Aucune optimisation ne dégrade accessibilité, provenance ou comportement fail-closed.

## Rapport obligatoire

```text
RUN : <uuid>  SHA : <git sha>  BUDGETS : <hash>
DATE/UTC : <start/end>  PROFIL : <P-CI|P-LOCAL|P-DESKTOP + hash>
DATASET : <S|R|X + generator version + seed + hash>
SCÉNARIO : <ID/version>  CACHE : <cold|warm|mixed>
CHARGE : <rate/concurrency/durée>  ÉCHANTILLONS : <n>
RÉSULTATS : p50/p90/p95/p99/max, débit, erreurs, queue wait
RESSOURCES : CPU, RSS/heap peak et plateau, disque/WAL, connexions
QUALITÉ : pertes 0, doublons, stale/partial/delayed, hash résultat
RÉGRESSION : baseline <run> ; écart ; confiance
PROFILS/PLANS/TRACES : <artefact IDs expurgés>
DÉCISION : pass | investigate | fail | provisional
RISQUE/EXCEPTION : aucun | owner + échéance + mitigation
```

Joindre JSON brut, rapport lisible, manifest environnement, plans SQL, métriques, traces échantillonnées, profils dédiés et logs expurgés. Ne jamais joindre un secret ou payload financier complet.

## Sources primaires guidant le protocole

- [FastAPI — async/await](https://fastapi.tiangolo.com/async/) et [Python — asyncio.Queue](https://docs.python.org/3/library/asyncio-queue.html) : séparer E/S awaitables, threadpool et files bornées.
- [Polars — optimizations](https://docs.pola.rs/user-guide/lazy/optimizations/) et [LazyFrame explain](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.explain.html) : conserver et comparer les plans optimisés.
- [Apache Arrow — Scanner](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html) : mesurer projection, filtre, batch size, readahead, threads et mémoire.
- [PostgreSQL — EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html) : plans réels, buffers, sérialisation et caveats de mesure.
- [React — Profiler](https://react.dev/reference/react/Profiler) et [performance tracks](https://react.dev/reference/dev-tools/react-performance-tracks) : mesurer render/commit avec builds adaptés.
- [TanStack Query — cancellation](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation), [TanStack Table virtualization](https://tanstack.com/table/latest/docs/framework/react/guide/virtualization) et [TanStack Virtual](https://tanstack.com/virtual/latest/docs/api/virtualizer) : requêtes annulables et fenêtre DOM mesurée.
- [Lightweight Charts — data updates](https://tradingview.github.io/lightweight-charts/docs/5.1) : `update` pour les mises à jour incrémentales.
- [Apache ECharts — Canvas vs SVG](https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/) et [imports minimaux](https://echarts.apache.org/handbook/en/basics/import/) : comparer renderer, mémoire et bundle.
- [OpenTelemetry Python — instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/) et [Prometheus — histograms](https://prometheus.io/docs/practices/histograms/) : corrélation causale et distributions agrégables.

Ces sources définissent les mécanismes de mesure. Le protocole Vertex, les datasets et tous les seuils restent à vérifier sur le système réel.
