# Vertex — audit cloud maximal et portage legacy

Date : 2026-08-31 UTC  
Mode : GitHub en lecture seule ; aucun accès au poste TWS/TradingView  
Cible : `Mendestrading21/Vertex-1.0-Beta-`  
Source de comparaison : `Mendestrading21/Vertex-`

## Verdict exécutif

Le transfert Claude vers la Beta est bien arrivé sur `main` et sa CI est verte.
La Beta possède une architecture nettement plus saine que l'ancien Vertex :
contrats typés, calculs Python centralisés, PostgreSQL append-only, séparation
API/worker/edge/web, états explicites et frontière sans ordre. Elle n'est
cependant **pas prête pour une Beta live** ni « intelligente à 100 % ».

Deux P0 interdisent de la déclarer opérationnelle aujourd'hui :

1. le nouveau service IBKR continu ne peut pas atteindre `connectAsync`, car la
   même machine d'état reçoit deux fois la transition de connexion ;
2. des valeurs provenant réellement d'IBKR ont été commitées dans le dépôt
   public, en contradiction avec les règles absolues du projet.

La CI ne couvre ni l'un ni l'autre. Elle prouve la construction, les tests
déclarés et le parcours synthétique ; elle ne prouve pas une chaîne TWS live.
Le backfill de barres quotidiennes est le seul chemin IBKR réel correctement
normalisé visible dans le code. Le flux top-of-book continu est mal typé,
TradingView n'est pas déployé, les options/news/calendriers réels ne sont pas
produits et l'apprentissage automatique reste un plan de recherche.

L'ancien `Vertex-` contient bien des comportements live utiles — connexion
`readonly=True`, workers de cotations, entonnoir de chaîne options, annulation
des lignes de marché, escalade live/frozen/delayed, scanner et webhook
TradingView. Il ne faut pas le fusionner dans la Beta : son runtime canonique
importe encore un monolithe Flask de 2 798 lignes, repose sur de nombreux
threads et états mémoire globaux, conserve des surfaces de lecture de compte et
surévalue plusieurs garanties TradingView. Les comportements utiles doivent
être réexprimés derrière les contrats Beta, un test rouge à la fois.

Conclusion : **NO-GO pour déploiement/live**, **GO pour une campagne de
correction ordonnée**. Le premier lot est la quarantaine des données et la
réparation du démarrage IBKR ; le design et le machine learning viennent après
la vérité de la chaîne de données.

L'ancien dépôt ajoute un incident historique distinct : un identifiant IBKR
réel, une capture TWS et un objet d'inventaire de positions restent joignables
dans des refs/objets Git publics. Aucune valeur n'est reproduite ici. Ne pas
réutiliser son historique ; décider humainement d'une mise en privé et d'une
purge coordonnée des branches, caches et forks.

## 1. Baseline GitHub figée

| Champ | Beta — cible | Vertex historique — comparaison |
|---|---|---|
| Dépôt | `Mendestrading21/Vertex-1.0-Beta-` | `Mendestrading21/Vertex-` |
| Visibilité | Public | Public |
| Branche par défaut | `main` | `main` |
| SHA audité | `bdf9f306a6c3e3a372c8757abfb987eba315a648` | `c683c944f93f61d5fd22303df726fac6e79820fe` |
| Tree | `1353251713048e3d733616037db6392f33e9dd45` | `691ccc497599450f3ecfe3362e782876e617be4e` |
| Fusion | PR #8, head `f4ef048`, tree identique au merge | PR #856 |
| CI du SHA | Run `33403277105`, 7/7 jobs verts | Run `33206015298`, jobs `test` et `safety` verts |
| PR ouvertes | 0 | 1 brouillon historique, #654, sur une base non-`main` |
| Branches | 4 observées, aucune protégée | 750 observées, aucune protégée |
| Ruleset `main` | Aucun | Aucun observé |
| Licence racine | Absente | Absente |
| Taille GitHub | Environ 2,4 MB | Environ 179 MB |
| Arbre | 740 fichiers / 123 dossiers au relevé | 2 703 entrées Git au relevé |

La PR Beta #8 a été fusionnée pendant l'audit. Le commit de merge `bdf9f306`
et son head `f4ef048` portent le même tree ; les conclusions ont été recalées
sur le commit `main`. La CI post-fusion du SHA exact est verte.

### Ce que la CI Beta prouve

- Ruff et mypy strict sur les sources Python ;
- unitaires, propriétés et oracles numériques déclarés ;
- intégrations PostgreSQL persistence/worker/API déclarées ;
- guardrails financiers et frontière sans ordre ;
- web lint, types, tests, build, budget et drift OpenAPI ;
- Chromium E2E aux trois viewports bureau avec contrôles axe ;
- audit de dépendances web/Python et SBOM Python.

### Ce qu'elle ne prouve pas

- la composition réelle `runner + adapter` de l'edge IBKR ;
- `apps/edge-ibkr/tests_integration` ;
- une connexion TWS, les entitlements ou le mode de marché sur le poste ;
- les options, news et calendriers IBKR de bout en bout ;
- le déploiement TradingView/Cloudflare ;
- Firefox/WebKit sur le nouveau head ;
- l'absence de données de marché réelles dans le dépôt ;
- une performance prédictive, une calibration ou un apprentissage actif ;
- SBOM/notices/audit du lock Wrangler.

## 2. Points solides de la Beta

- Monorepo organisé par responsabilités : core, persistence, API, worker,
  edge IBKR, ingress TradingView, web, recherche, contrats et outils.
- Verrouillages présents : `uv.lock`, `pnpm-lock.yaml`, actions GitHub épinglées
  par SHA et image PostgreSQL par digest.
- Frontière IBKR positive dans l'adaptateur : loopback, `client_id > 0`,
  `readonly=True`, allowlist market-data-only et aucun ordre.
- Calculs faisant autorité côté Python ; le web ne doit pas recalculer prix,
  Greeks, verdicts ou probabilités canoniques.
- `AdviceEngine` unique, déterministe, dix gates et abstention dominante ;
  aucune sortie BUY/SELL et aucun chemin d'exécution.
- Barres historiques IBKR normalisées vers cotation quotidienne et OHLC ; des
  tests de segments prouvent le chemin vers Marchés et Analyse lorsque cette
  normalisation est appelée explicitement.
- Douze routes installées, chargement par route, ECharts modulaire,
  Lightweight Charts séparé, tables accessibles et motion réduite.
- PostgreSQL, outbox et versions de snapshots constituent une base sérieuse
  pour une machine explicable et rejouable.
- Les formules BSM européennes, Greeks, payoff, scénarios, P&L, TWR,
  drawdown, rendements, ATR et covariance sont bien structurées sur leur
  domaine déclaré et possèdent de nombreux oracles/propriétés.

Ces qualités sont un socle ; elles ne compensent pas les défauts de composition,
de contrat et de fraîcheur ci-dessous.

## 3. Constats prioritaires Beta

### P0 — arrêt immédiat

| ID | Constat | Preuve | Effet | Correction minimale |
|---|---|---|---|---|
| B-P0-01 | Le service IBKR continu ne démarre pas. | `tools/run_edge_ibkr.py:225-233` injecte la même `ConnectionStateMachine` dans l'adaptateur et le runner. `apps/edge-ibkr/src/vertex_edge_ibkr/runner.py:171-199` appelle `begin_connect()`/`on_connected()`, puis `adapter.py:295-313` recommence. | Le second `begin_connect()` lève avant `connectAsync`; le chemin continu annoncé s'arrête. | Une seule autorité de transition. Test de composition avec vrais runner/adapter et faux port, puis test local TWS différé. |
| B-P0-02 | Données IBKR réelles dans le dépôt public, contre les règles du projet. | `CLAUDE.md:67`, `.claude/rules/security.md:5` et `apps/edge-ibkr/tests/test_normalize_bars.py:39-53`. D'autres docs/tests doivent être inventoriés. | Risque de droits, rétention et vérité du dépôt ; la CI verte n'a rien détecté. | Quarantaine, remplacement par vecteurs totalement inventés, garde CI ; décision humaine séparée sur l'historique. Ne jamais force-push automatiquement. |

### P1 — vérité financière et runtime

| ID | Constat | Preuve | Effet | Acceptation attendue |
|---|---|---|---|---|
| B-P1-01 | Une top-of-book brute est étiquetée `ibkr.daily-quote/1`. | `apps/edge-ibkr/src/vertex_edge_ibkr/adapter.py:_SCHEMA_BY_PAYLOAD`; `port.py:QuoteObservation`; `apps/worker/src/vertex_worker/markets.py:_parse_quote`. | Marchés exige ticker, secteur, jour, close et base d'ajustement : chaque quote live est `invalid_payload`. | Schéma `ibkr.quote/1` distinct ; normaliseur explicite ; test adapter→DB→worker→snapshot. |
| B-P1-02 | Les quotes brutes invalides peuvent évincer les daily quotes valides. | `markets.py` charge les 500 plus récentes avant validation ; chaque snapshot reçoit un nouvel UUID. | Après assez de ticks, Marchés peut devenir vide malgré un backfill valide. | Filtrer/type-checker en SQL ou avant la limite ; fenêtre par instrument/jour ; test de saturation. |
| B-P1-03 | Une observation peut être persistée après code IBKR 1100/1300. | `adapter.py:649-669`, `state.py:129-135,190-197`, `runner.py:262-269,304-330`. | L'état devient DOWN sans nouvel epoch ; `_persist` teste l'epoch, pas `observation_is_fresh()`/HEALTHY. | Gate de santé juste avant persist ; régression 1100/1300 + enveloppe tardive. |
| B-P1-04 | L'intégration edge PostgreSQL n'est pas dans GitHub Actions et ne teste pas le vrai schéma. | `tools/run_checks.sh:164-180`, `.github/workflows/ci.yml:200-209`, `apps/edge-ibkr/tests_integration/test_edge_ingestion_chain.py`. | CI verte malgré B-P0-01 et B-P1-01. | Ajouter le dossier à CI et un test contractuel utilisant les vrais objets adapter. |
| B-P1-05 | L'outbox reste `IN_PROGRESS` après crash. | `packages/python/vertex_persistence/.../outbox.py:claim_outbox_batch,reap_expired_leases`; `apps/worker/.../runner.py:run_once`. | Un travail peut rester bloqué indéfiniment. | Appeler le reaper avec métriques, concurrence testée et seuil configurable. |
| B-P1-06 | Le démarrage standard n'est pas un démarrage live coordonné. | `tools/start_local.sh`, `docs/08-runbooks/START_LOCAL.md`, `apps/worker/src/vertex_worker/profiles.py:resolve_profile`. | API/worker/Vite démarrent ; l'edge est séparé et le profil worker reste synthétique par défaut. Le guide réel peut conduire à lancer un second worker avec un registre différent sur le même outbox. | Superviseur local unique, **un seul worker** au profil explicite, prévol, health/readiness par composant et arrêt propre. |
| B-P1-07 | Compose web est non fonctionnel. | `infra/compose/serve-static.mjs` écoute `127.0.0.1` dans le conteneur et ne proxy pas `/api`; variables d'auth manquantes. | Le web n'est pas joignable ou reçoit `index.html` à la place de l'API. | Bind `0.0.0.0`, proxy/routage explicite, origine/auth, smoke Compose réel. |
| B-P1-08 | Univers réel et fenêtre Marchés sont incompatibles. | `profiles.py:MAX_REAL_INSTRUMENTS=500`; `markets.py` limite à 500 observations et exige deux jours par ticker. | Un univers large peut produire zéro couverture. | Pagination/partition par instrument, deux sessions point-in-time garanties, budget mesuré. |
| B-P1-09 | Le backfill amplifie l'outbox. | Une observation et un `quotes.ingested` par barre ; overview recalculé et republié avec `as_of=now`. | Centaines de milliers de jobs/versions possibles. | Ingestion bulk, coalescence, watermark, idempotence de contenu et benchmark. |
| B-P1-10 | TradingView n'est pas un runtime durable. | `tradingview/README.md`, `wrangler.toml`, `TradingViewOrchestrator._pending`. | Worker non déployé ; attente en mémoire ; ack avant `_pending`; crash window sans rechargement/outbox. | Décision B-03, flux authentifié/versionné/anti-rejeu, store PostgreSQL, orchestration durable, redelivery/idempotence et `REEVALUATE` uniquement. Ne dire « signé » qu'avec une vraie signature de message. |

### P1 — calculs, décisions et intelligence

| ID | Constat | Preuve | Effet | Acceptation attendue |
|---|---|---|---|---|
| B-P1-11 | XIRR peut certifier une racine unique à tort. | `packages/python/vertex_core/src/vertex_core/calculations/performance.py::xirr`. Un flux non conventionnel de régression possède trois racines proches/éloignées, mais la grille n'en voit qu'une. | Rendement matériellement faux affiché `OK`. | Pour flux non conventionnels, prouver l'unicité ou retourner INVALID ; test multi-racines rapprochées. |
| B-P1-12 | Validation des quotes options insuffisante. | `apps/worker/src/vertex_worker/options.py::_quote_status,_optional_decimal,_build_contract_entry`. | Timestamp futur, prix négatif, booléens/entiers négatifs et style arbitraire peuvent passer ; BSM européen est appliqué à tout style. | Bornes, enums, âge dans `[0,TTL]`, style européen seulement ou moteur American dédié. |
| B-P1-13 | Les gates acceptent des preuves auto-déclarées. | `vertex_core/decision/advice.py:AdviceInputs,_derive_status`; `/advice/preview`. | Des booléens vrais et des tuples contenant `""` peuvent satisfaire la ladder sans objet de preuve existant. | IDs `NonEmptyStr`, résolution/hash des snapshots, CalculationRecords et contraintes avant gate. |
| B-P1-14 | La traçabilité `code_sha` n'est pas un SHA de build. | `contracts/calculation.py`; `_CODE_SHA` des workers ; projection snapshot partielle. | Impossible de reproduire exactement un verdict par version. | Digest immuable injecté au build et CalculationRecord complet persisté/référencé. |
| B-P1-15 | Analyse réelle reste sémantiquement synthétique. | `apps/worker/src/vertex_worker/analysis.py:770-831` et textes `AnalysisPage.tsx`. | Population REAL mais faits/risque synthétiques, direction UNKNOWN, conid non résolu ; UI peut mal décrire la donnée. | Contrat de provenance réel, conid, session/calendrier/liquidité, indicateurs et tests de rendu REAL. |
| B-P1-16 | Options, calendrier et news réels ne sont pas produits selon les contrats worker. | Edge produit sec-def/WSH/news bruts ; workers attendent slice options et événements/titres normalisés différents. | Pages présentes mais chaîne réelle absente ou vide. | Producteurs/normaliseurs versionnés, ordonnanceur, fixtures inventées issues des vrais objets de port. |
| B-P1-17 | Une opportunité réelle ne peut pas être qualifiée. | `apps/worker/src/vertex_worker/opportunities.py`: secteur synthétique et preuves régime/fondamentaux/portfolio-fit à false. | Le moteur réel s'abstient toujours ; aucun ranking intelligent exploitable. | Alimenter chaque preuve de manière point-in-time avant tout score ou wording de qualification. |
| B-P1-18 | Aucun apprentissage automatique actif. | `research/README.md`, manifests `feature-registry.yaml` et `model-candidates.yaml`, absence de tables prediction/outcome/model/drift. | « Auto-amélioration » et précision prédictive ne sont pas des capacités actuelles. | Journal décision→résultat, dataset point-in-time, walk-forward purgé, baseline, calibration, registry, shadow, promotion humaine et rollback. |

### P1 — UI, cache et vérité visuelle

| ID | Constat | Preuve | Effet | Acceptation attendue |
|---|---|---|---|---|
| B-P1-19 | L'état top-level `stale` est ignoré sur quatre pages. | `TodayPage.tsx`, `MarketsPage.tsx::frameStateOf`, `analysisView.ts::analysisStateOf`, `optionsView.ts::chainStateOf`. | Une snapshot rassise peut être rendue comme prête. | État unique serveur→hook→vue ; tests top-level stale. |
| B-P1-20 | Reconnexion SSE sans rattrapage avec caches infinis. | `apps/web/src/api/events.ts`, hooks `staleTime: Infinity`, `main.tsx` sans focus refresh/polling. | Un événement manqué peut laisser l'écran faux indéfiniment. | Baseline/version à `onopen`, invalidation ciblée ou sync route, test de coupure/reconnexion. |
| B-P1-21 | Le Simulateur garde un ancien résultat après changement des entrées. | `apps/web/src/pages/SimulatorPage.tsx`. | L'utilisateur voit un résultat qui ne correspond plus au formulaire. | Lier résultat à un hash d'inputs, effacer ou marquer périmé à chaque modification. |
| B-P1-22 | Vertex IA peut figer une explication ancienne. | Clé `['ai','explain',kind,key]`, `staleTime: Infinity`, aucune version de snapshot/invalidation. | Explication non alignée au dossier courant. | Ajouter snapshot/version/hash, invalidation et affichage de l'autorité déterministe. |
| B-P1-23 | L'univers Marchés est traité comme univers Analyse/Options/IA. | `apps/web/src/pages/devUniverse.ts::useDeclaredInstruments`. | Liens vers dossiers sans snapshot ; chargement/panne/absence fusionnés ; jusqu'à ~153 chips. | Catalogue de capacités typé + recherche/combobox/favoris/virtualisation. |
| B-P1-24 | Les libellés de provenance restent codés synthétiques. | `AnalysisPage.tsx`, `OptionsPage.tsx`. | Une donnée REAL peut être présentée comme synthétique ; les états vides mentent sur la cause. | Rendre source, population et droits depuis l'API, avec test REAL/DELAYED/NOT_ENTITLED. |

### P2/P3 structurants

- `NOW.md`, `BLOCKERS.md`, `DEBT.md`, README et manifests se contredisent ou
  citent des SHA/portes obsolètes.
- Aucun ruleset, aucune review obligatoire et aucune protection de branche.
- Dépôt public sans licence racine ; statut propriétaire incohérent entre
  packages.
- Wrangler et son lock ne sont pas couverts par notices/audit/SBOM ; aucune
  SBOM Node/conteneurs ni provenance de release.
- Pas de métriques, alertes, traces, heartbeat edge, profondeur/âge outbox,
  monitoring drift ou runbook d'incident complet.
- Backups sans ordonnancement, preuve de restauration, WAL/PITR ou rétention
  hors machine.
- Dernier nightly Firefox/WebKit vert sur l'ancien head, pas sur `bdf9f306`.
- `global.css` approche 4 170 lignes ; plusieurs modules Python dépassent
  1 300–2 200 lignes ; aucune porte de complexité n'empêche la croissance.
- 22 nouveaux modules/tests Python portent un mode exécutable inutile.
- Guide Windows non reproductible et fichier de prompt d'installation cité
  mais absent.

## 4. Matrice de vérité de l'intelligence Beta

| Capacité | État | Vérité au SHA audité |
|---|---|---|
| Calculs déterministes centraux | `PROUVÉ` avec réserves | 25 entrées au registre : 22 APPROVED ; FX reste recherche ; GEX et calibration non implémentés. XIRR/options exigent corrections P1. |
| AdviceEngine / dix gates | `PROUVÉ` structurellement | Unique, fail-closed, sans BUY/SELL ; provenance des entrées insuffisamment liée aux objets persistés. |
| Profil worker IBKR réel | `PRÉSENT_NON_PROUVÉ` live | Opt-in, univers par conid et droits explicites ; démarrage coordonné absent. |
| Backfill barres quotidiennes | `PROUVÉ` par tests de segments | Normalisation correcte vers daily quote/OHLC ; connexion réelle du poste non prouvée dans le cloud. |
| Quotes top-of-book continues | `PRÉSENT_NON_PROUVÉ` et cassé | Runner présent, mais P0 de double transition et P1 de schéma. |
| Analyse technique réelle | `PRÉSENT_NON_PROUVÉ` | Barres atteignent un snapshot en test ; contenu réel reste synthétique/UNKNOWN. |
| Chaîne options réelle | `ABSENT` | Aucun agrégateur sec-def + contrats + quotes + spot/taux/dividendes/style. |
| IV/Greeks/scénarios réels | `ABSENT` de bout en bout | Calculs présents, producteur réel compatible absent. |
| GEX/skew/term structure/anomalies | `PLANIFIÉ` | Contrats/recherche ou NOT_IMPLEMENTED ; aucun runtime réel. |
| News, earnings, calendrier, macro | `ABSENT` ou `PLANIFIÉ` en réel | Payloads edge et contrats worker ne correspondent pas ; aucune boucle complète. |
| Régime/secteur/fondamentaux | `PRÉSENT_NON_PROUVÉ` | Fragments/synthétique ; insuffisants pour qualifier une opportunité réelle. |
| Opportunities | `PROUVÉ` en synthétique | En réel, gates structurellement manquantes donc abstention. |
| IA fournisseur | `BLOQUÉ/DISABLED` | Explication déterministe disponible ; aucun modèle fournisseur actif prouvé. |
| Probabilité calibrée | `ABSENT` | `probability.calibration` NOT_IMPLEMENTED ; aucune métrique live fiable. |
| Apprentissage automatique | `ABSENT` | Pas de dataset/version/artefact/chargement/monitoring runtime. |
| Auto-amélioration contrôlée | `PLANIFIÉ` | Research anti-fuite utile, mais aucun ledger décision→résultat ni registry/promotion. |

Une machine « intelligente » ne devient pas fiable en ajoutant un LLM ou un
score. L'ordre obligatoire est : identité/provenance → données point-in-time →
calculs validés → outcomes → évaluation hors ligne → calibration → shadow →
promotion humaine. Jamais de réentraînement sur ses propres affirmations,
d'auto-modification du code ou d'auto-promotion live.

## 5. Audit des douze pages Beta

| Page | État technique | Données actuelles | Défaut prioritaire | Cible de composition |
|---|---|---|---|---|
| Aujourd'hui | Présente, E2E synthétique | Snapshots agrégés | top-level stale ignoré | Une décision du jour, cadran régime, changements, trois alertes maximales. |
| Calendrier | Présente | Surtout synthétique/manuel | aucun producteur IBKR normalisé ; requête par saisie | Timeline filtrable, source/droits/timezone, earnings/macro/options clairement séparés. |
| Marchés | Présente | Synthétique + backfill quotidien testable | quote live mal typée, fenêtre 500, cadran circulaire absent | Régime circulaire, breadth, secteurs, ticker supérieur et inspecteur. |
| Opportunités | Présente | Synthétique exploitable | réel jamais qualifié, page très longue | Funnel puis shortlist justifiée ; aucune ligne sans preuves/gates. |
| Analyse | Présente | Barres réelles possibles par backfill | texte synthétique, direction UNKNOWN, provenance incomplète | Dossier unique : prix/structure/catalystes/risque/scénarios/verdict. |
| Options | Présente | Chaîne synthétique | producteur réel absent et validation fragile | Chaîne virtualisée, smile/skew/term, liquidité, scénarios et contrat inspecté. |
| Simulateur | Présente | Calcul serveur | ancien résultat après input changé | Une hypothèse explicite, hash d'inputs, provenance modèle et limites. |
| Portefeuille | Présente | Saisie manuelle, par design | densité et plusieurs limites de modèle | Exposition/risque/thèses ; jamais importer compte/positions IBKR. |
| Suivi | Présente | Thèses manuelles | sheet sans inert/backdrop complet | Thèses actives, événements, invalidation et post-analyse. |
| Performance | Présente | Ledger manuel | XIRR P1, attribution annoncée mais absente | Populations séparées, TWR/XIRR honnête, attribution et coûts. |
| Vertex IA | Présente | Template déterministe | cache figé, sélection auto instable | Explication de faits versionnés ; jamais autorité de calcul/verdict. |
| Système | Présente | Health partiel | edge/TV/backups/outbox non observables | Matrice connexions, fraîcheur, files, droits, backup/restore et incidents. |

### Écart au contrat visuel approuvé

Les captures actuelles confirment des pages longues, denses et fragmentées. Le
shell codé reste un fond noir quadrillé avec halo ambre, sidebar ouverte à
248 px, cartes opaques et monogramme `VX`. Il manque le fond bleu-noir orbital,
la petite sidebar intégrée, l'ordre canonique de navigation, le ticker haut, le
cadran circulaire de régime, l'inspecteur droit commun, les cartes Black Glass
translucides, le logo maître et la hiérarchie centrale dominante.

La reconstruction visuelle doit commencer seulement après B-P0/B-P1 et avancer
une page/PR à la fois, avec captures `1280x800`, `1440x900` et `1600x1000`.
Elle ne doit ni changer la vérité des calculs ni inventer de données pour remplir
un widget.

## 6. Ce que l'ancien Vertex prouve réellement

### P0/P1 propres au legacy

| ID | Constat | Preuve | Effet / décision |
|---|---|---|---|
| L-P0-01 | La frontière market-data-only n'est pas fermée à l'échelle du dépôt. | `ib_reader.py::IBKRReader.account_summary,positions`, `test_connection.py::main`, rôles `compte/pnl` de `ibkr_link.py`, `terminal.py::_load_ibkr`. Les scans CI n'incluent pas toutes les racines. | Ces surfaces restent exécutables/importables. `REJETER` et ajouter un scanner AST global dans la Beta. |
| L-P0-02 | L'historique public conserve des éléments IBKR/positions issus du réel. | Test interne `tests/test_vertex_1_0_compte_hors_git.py`, une ref historique, `tests/fixtures/ibkr/g5_capture.json` et un objet Git d'inventaire de positions. | Ne rien citer/copier. Mise en privé immédiate à considérer, inventaire de toutes refs, décision de purge GitHub/caches/forks et traitement de l'identifiant exposé. |
| L-P1-01 | Le fail-closed réseau local ne couvre pas l'entrée WSGI. | `terminal.py::_start_app` applique l'exposition ; `render.yaml` lance `gunicorn vertex.runtime:app`; `vertex/runtime.py::create_app` ne réapplique pas la porte. | Une configuration sans secret peut être publiée autrement que prévu. Porter une politique réseau/auth au niveau factory/middleware, testée sur toutes les entrées. |
| L-P1-02 | Provenance du scan agrégée au lieu d'être par observation. | `terminal.py::_download_universe`, `vertex/data_sources/scan_evidence.py::_source`, `build_scan`, `engines/decision_evidence.py::for_symbol`. | IBKR/yfinance/Stooq sont fusionnés puis tous les titres reçoivent un label global faux ou dégradé. Ne porter que des enveloppes Beta par instrument/source. |
| L-P1-03 | Fraîcheur globale pouvant rafraîchir artificiellement un symbole ancien. | `terminal.py::_store_ticker,_quotes_worker`, `_live_meta['ts']`, `live_state_api.py::quotes_ep`. | Un autre symbole actualisé peut faire paraître une ancienne quote fraîche. Timestamp, mode, conid, exchange et devise doivent être par observation. |
| L-P1-04 | Plusieurs autorités de décision alimentent différentes pages. | Analyse appelle `/api/strategy/decision`, `/api/decision` et `/api/skyler`; Aujourd'hui/Opportunités lisent directement `rows[].verdict`. | Deux pages peuvent contredire un blocage de qualité. Ne porter aucune autorité legacy ; garder l'unique AdviceEngine Beta. |
| L-P1-05 | TradingView réveille un scan, mais ne rejoint pas un verdict durable. | Pine → `tradingview_webhooks.make_blueprint` → singleton mémoire → `terminal.py::_on_tv_signal`; `tv_confluence.py` non consommé et confluence dupliquée en JS. | Perte au restart, callback échoué mais 200, dédup trop faible, payload Pine défini mais non appelé. Garder l'architecture Beta et réécrire le runtime durable. |
| L-P1-06 | Auth/exposition cloud insuffisamment fail-closed. | `render.yaml` démo publique sans `VERTEX_CODE`; routes mutables de tracking/mémoire/log/IA ; confiance brute dans `X-Forwarded-For`; secrets activés dès qu'ils sont non vides. | Bloquer toutes les écritures/coûts en démo, valider la force des secrets, proxy de confiance et rate-limit durable. |
| L-P1-07 | XSS et méthodes HTTP à effets de bord. | `docs/vertex-audit/11-security-audit.md`, nombreux `.innerHTML`, `vx-core.js::VX.states.*`, absence de CSP ; rescan/regen/refresh déclenchés par GET. | Ne jamais copier le front. Builders sûrs/textContent, CSP, POST-only, CSRF/origin/rate-limit. |
| L-P1-08 | Chaîne de dépendances non reproductible. | `requirements.txt` à plages larges, aucun lock/hash ; Actions par tags mutables ; aucun SCA/SBOM/notices/licence/secret scan ; Playwright déclaré mais navigateur non installé en CI. | La CI verte n'est pas une preuve supply-chain ni E2E. Réinstaller uniquement par locks/notices Beta. |
| L-P1-09 | Bugs runtime cachés par la CI démo. | `positions_api.py::_quotes` référence `_POS_TTL_S` non défini ; `cotation_unifiee.py` recrée le circuit breaker ; `IbkrScheduler` n'applique pas toutes ses limites annoncées. | Tests de composition et panne nécessaires ; ne pas porter ces implémentations. |
| L-P1-10 | News/calendrier/persistance peuvent annoncer une fraîcheur ou une santé non prouvée. | `_news_loop`, `live_engine._upd_ts`, `ibkr_news.FOURNISSEURS`, `_cal_loop`, `macro_calendar.py`, `services/persist.py`, `services/connections.py`. | Providers figés, calendrier approximatif, erreurs transformées en défauts silencieux et JSON local sans garanties interprocessus. Réécrire sous enveloppes/PostgreSQL. |

Autres défauts vérifiés : le cache yfinance est écrit mais jamais lu ; le mémo
d'analyse reçoit un type incompatible dans le chemin réel ; des collisions de
routes historiques restent documentées ; et environ 77 modules sur 379 ne sont
pas atteignables statiquement depuis le runtime canonique. Recherche,
pseudo-calibration et « decision memory » ne doivent donc pas être comptées
comme intelligence active sans appelant prouvé.

### Baseline et forces utiles

- `python -m vertex` active un profil puis importe encore `terminal.py` via
  `vertex/runtime.py::_legacy_runtime`.
- La CI du SHA exact est verte en mode `NO_IBKR=1`, `DEMO=1`, avec compilation,
  pytest, smoke `/healthz` et deux tests de sûreté.
- `vertex/data_sources/ibkr_gateway.py::IbkrGateway.connect` impose
  `readonly=True`, un timeout et une sonde de ports.
- `terminal.py::_ibkr_opt_worker` possède un worker unique, une file priorisée,
  coalescence, péremption et circuit breaker.
- L'entonnoir options appelle `reqSecDefOptParams`, élimine les classes ajustées,
  limite les strikes, demande volume/OI/IV, lit `modelGreeks` et annule les
  abonnements dans tous les chemins principaux.
- Les boucles de cotations/indices savent escalader live → frozen → delayed →
  delayed-frozen et retenter le live ; elles exposent une fraîcheur de 75 s.
- Scanner, news broker et fondamentaux Reuters sont demandés par le même worker
  sérialisé.
- Le webhook TradingView valide symbole/signal/timestamp, borne le payload,
  applique anti-rejeu/dédup/rate-limit et ne retourne que `REEVALUATE`.
- `vertex/app/snapshot.py` apporte un modèle single-flight/stale-while-revalidate
  intéressant, et `vertex/storage/point_in_time.py` une bonne intention sur les
  temps d'observation/connaissance/effet ; reprendre les invariants, pas le
  stockage mémoire/JSONL.

### Pourquoi il ne faut pas copier le runtime

- `vertex/runtime.py` réimporte un monolithe Flask ; `terminal.py` contient
  encore 2 798 lignes et orchestre des globals/threads daemon.
- 20 des 27 tâches recensées par son scheduler sont encore explicitement
  `NON_IMPLEMENTED` : le grand nombre de modules ne correspond pas au même
  nombre de capacités actives.
- La CI force démo et `NO_IBKR`; elle ne prouve aucune connexion live.
- Cinq connexions IBKR distinctes ont existé ; le code conserve des rôles de
  client liés au compte/P&L et des scripts lisant résumé et positions.
- `ib_reader.py::account_summary,positions` et `test_connection.py` lisent des
  données de compte. Même read-only, ces surfaces sont `REJETER` pour la Beta.
- Les erreurs de jobs IBKR sont souvent ramenées à `None`, ce qui perd type,
  entitlement, pacing, freshness et corrélation.
- Le worker options encode `0.0` pour certains prix/IV absents et utilise des
  dictionnaires ad hoc sans schéma/version/rights hash immuable.
- Les états sont en mémoire ; la persistance, le replay et la concurrence ne
  répondent pas aux garanties PostgreSQL/outbox de la Beta.
- Le secret TradingView voyage dans le JSON, pas dans une signature du corps ;
  le store/rate-limit est mémoire et `_on_tv_signal` ne fait que réveiller un
  rescan global. Les docs annoncent confirmation IBKR et états plus riches que
  le chemin réellement branché.
- L'exception du callback TradingView est avalée ; le webhook répond succès même
  si la réévaluation échoue.
- La documentation se contredit : README dit market-data-only sans compte,
  tandis que des guides/scripts décrivent encore positions et résumé IBKR.
- Le dépôt possède 750 branches non protégées, une PR brouillon historique,
  aucune licence racine et une dette de maintenance considérable.

L'ancien Vertex prouve donc des **séquences opérationnelles et des cas limites**,
pas une architecture à fusionner.

## 7. Carte de portage legacy → Beta

| Capacité legacy | Source | Équivalent Beta | Décision | Test rouge avant portage |
|---|---|---|---|---|
| Sonde de ports + readonly + timeout | `ibkr_gateway.py`, `ibkr_link.py` | adapter/config edge | `ADAPTER` | Un seul owner de state, boucle locale, client IDs sans collision, timeout/reconnect. |
| Escalade 1→2→3→4 puis retry live | `terminal.py::_quotes_worker,_indices_loop` | state machine/rights edge | `ADAPTER` | Entitlement/mode explicite par observation, jamais conclure live par absence de delayed fields. |
| Worker IBKR unique + file priorisée | `_ibkr_opt_worker`, `services/file_ibkr.py` | runner/pacing/line budget/outbox | `RÉÉCRIRE` | Priorité, coalescence, cancellation, backpressure et métriques sous PostgreSQL/async. |
| Découverte options | `ibkr_option_chain.py::fetch_expirations` | sec-def edge | `REPRENDRE` comme comportement | Paramsets SMART, classe standard, expirations/strikes avec conid exact et fixtures inventées. |
| Chargement ciblé de contrats | `fetch_contract_details`, `chain` | agrégateur options absent | `ADAPTER` | Sec-def→qualification→quotes→OI/volume/Greeks→slice versionné, annulation dans `finally`. |
| Mémoire de strikes refusés | `vertex/options/strike_memory.py` | absent | `ADAPTER` | Clé conid+expiry+tradingClass+révision, TTL et invalidation sur corporate action. |
| Snapshot/historique actions | `ibkr_market_data.py`, `ibkr_historical.py` | quote/bar edge | `ADAPTER` | Schémas quote vs daily bar séparés, timezone/session/adjustment explicites. |
| Scanner marché | worker `scan` | discovery edge | `ADAPTER` | Pacing, universe provenance, dédup, droits et absence honnête. |
| News broker | worker `news`, `ibkr_news.py` | payload edge non normalisé | `RÉÉCRIRE` | Provider/article/timestamp/title normalisés, droits/rétention, dédup et pertinence. |
| Fondamentaux tick 258 | worker `fund` | absent/incomplet | `BLOQUÉ` puis `ADAPTER` | Entitlement/licence/retenue validés ; schéma par champ et date de publication. |
| Webhook TradingView | `tradingview_webhooks.py`, signal store | Worker/ingress Beta | `RÉÉCRIRE` | Authentification supportée de bout en bout, anti-rejeu, event ID, store/outbox durable, confirmation IBKR et crash recovery ; HMAC seulement si le protocole le permet réellement. |
| Fraîcheur 75 s et statuts UI | `app/ibkr_state.py`, `services/connections.py` | System/health Beta | `REPRENDRE` comme exigence | Heartbeat par source, âge dernier succès/erreur, rights, backlog et mode. |
| Snapshot single-flight/SWR | `app/snapshot.py` | cache API/SSE Beta | `ADAPTER` | Autorité DB/version, stale explicite, cancellation, baseline de reconnexion et métriques. |
| Trois temps point-in-time | `storage/point_in_time.py` | envelopes/ledger Beta | `REPRENDRE` comme invariant | Observation, connaissance et effet immuables avec contraintes PostgreSQL et replay. |
| Lecture compte/positions/P&L | `ib_reader.py`, rôles `compte/pnl`, anciens docs | explicitement interdit | `REJETER` | Guard CI sur symboles/imports/endpoints et aucun secret/donnée de compte. |
| Monolithe Flask, globals, threads daemon | `terminal.py` | services Beta séparés | `REJETER` | Aucun import legacy, aucun dossier copié, tests de comportement seulement. |
| UI/cartes legacy | templates/static legacy | React Beta | `RÉÉCRIRE` | Réutiliser questions métier et cas empty/stale, pas DOM/CSS/JS ni calcul client. |

## 8. Plan d'exécution recommandé

Chaque lot doit tenir dans une PR indépendante, posséder un rollback et ne pas
élargir la frontière financière.

### Lot 00 — quarantaine et vérité GitHub

Objectif : retirer les données réelles du nouveau contenu et empêcher toute
récidive.

- inventaire des fixtures/docs/captures/identifiants provenant d'IBKR ;
- remplacement par symboles/valeurs entièrement inventés ;
- garde CI de provenance de fixtures ;
- mise en privé du legacy à décider sans attendre le portage ; inventaire de ses
  750 branches/objets/caches/forks et procédure de purge séparée ;
- réécriture de `NOW.md`, `BLOCKERS.md`, `DEBT.md` au SHA courant ;
- décision humaine : dépôt privé propriétaire ou licence ; historique à
  conserver, nettoyer via procédure dédiée, ou traiter juridiquement ;
- ruleset `main`, PR/checks/review obligatoires.

Acceptation : aucun contenu nouveau ne viole la règle ; CI rouge sur une fixture
marquée/réelle de régression ; aucun force-push dans ce lot.

### Lot 01 — démarrage IBKR continu et contrat quote

- supprimer la double transition de la machine d'état ;
- séparer `ibkr.quote/1` et `ibkr.daily-quote/1` ;
- gate HEALTHY juste avant persist, codes 1100/1300 ;
- test réel de composition adapter→runner→DB→worker→Marchés ;
- inclure l'intégration edge dans GitHub Actions.

Acceptation : une fausse top-of-book atteint un snapshot quote sans devenir
close ; une déconnexion tardive ne persiste rien ; démarrage/arrêt sans fuite.

### Lot 02 — résilience, outbox et volume

- reaper de leases, métriques et alertes ;
- bulk/coalescence/watermarks de backfill ;
- fenêtre Marchés par instrument/session ;
- benchmark 500 instruments, backfill annuel, p95/p99 et mémoire ;
- health/readiness edge, worker, DB et SSE.

### Lot 03 — exactitude calculs et gates

- XIRR multi-racines ;
- validation options complète et style explicite ;
- evidence/scenario/facts non vides et résolus ;
- CalculationRecord complet, build SHA immuable ;
- chronologie des lots portefeuille, population/devise/identité point-in-time.

Acceptation : oracles, propriétés, contre-exemples et aucune valeur `OK` sans
domaine prouvé.

### Lot 04 — démarrage desktop reproductible

- un superviseur lance Postgres/migrations/API/worker réel/edge/Vite ;
- prévol local sans secret imprimé ;
- ports et origine WebAuthn cohérents ;
- arrêt coordonné et reprise ;
- smoke Compose ou suppression de la voie non supportée ;
- recette Windows/macOS distincte.

### Lot 05 — options réelles par portage comportemental

- tests de caractérisation synthétiques de l'entonnoir legacy ;
- agrégateur Beta sec-def→contrats→quotes→slice ;
- OI/volume/Greeks broker avec source et timestamp ;
- cancel dans `finally`, line budget, partial/not-entitled ;
- taux/dividendes/style/expiry exacts avant IV/scénarios ;
- ensuite seulement smile, skew, term structure et anomalies.

### Lot 06 — news, calendrier, fondamentaux et TradingView

- normaliseurs IBKR news/WSH et ordonnanceur ;
- droits, rétention, timezone, corrections et dédup ;
- fondamentaux seulement après décision de licence/entitlement ;
- TradingView durable, authentifié, idempotent, anti-rejeu, recovery et
  `REEVALUATE` uniquement ;
- aucun prix/verdict TradingView canonique.

### Lot 07 — intelligence réelle contrôlée

- ledger immuable observation/décision/action humaine/outcome/horizon ;
- feature snapshots point-in-time avec lineage ;
- baselines simples, walk-forward purgé, embargo, coûts et régimes ;
- calibration et abstention ;
- registry, shadow, comparaison champion/challenger, approbation humaine,
  canary et rollback ;
- jamais d'auto-promotion ou d'auto-modification runtime.

### Lots 08 à 19 — douze pages, une PR par page

Ordre : Aujourd'hui, Calendrier, Marchés, Opportunités, Analyse, Options,
Simulateur, Portefeuille, Suivi, Performance, Vertex IA, Système.

Pour chaque page : question métier unique, catalogue de capacités, graphe
dominant, inspecteur, source/âge/droits, huit états, clavier, reduced motion,
captures aux trois viewports, budget route et tests REAL/SYNTHETIC/STALE.

### Lot 20 — release Beta locale

- nightly Chromium/Firefox/WebKit sur le head ;
- SBOM Python/Node/conteneurs, notices Wrangler, audit et provenance ;
- backup/restauration/PITR ;
- métriques/alertes/runbooks ;
- recette live strictement market-data-only sur poste ;
- décision humaine GO/NO-GO documentée.

## 9. Recette live différée au poste

Ces preuves sont impossibles depuis GitHub. Elles doivent être exécutées
localement sans envoyer de secret ni de valeur de marché dans Git :

1. TWS paper avec Read-Only API, loopback et client IDs dédiés ;
2. démarrage superviseur et état HEALTHY de chaque processus ;
3. droits LIVE/DELAYED/NOT_ENTITLED par type de donnée ;
4. quote puis barres sur symboles de test autorisés, conservation uniquement
   des métadonnées non commerciales ;
5. code 1100, reconnexion 1101, port reset 1300 et absence de persist tardif ;
6. pacing, line budget, cancellation et aucune ligne abandonnée ;
7. backfill contrôlé et absence de tempête outbox ;
8. chaîne options limitée, OI/volume/Greeks, partial/not-entitled ;
9. fermeture TWS, reprise, arrêt/restart Vertex et récupération outbox ;
10. TradingView authentifié après déploiement approuvé, duplicate/replay/crash et
    résultat maximal `REEVALUATE` ;
11. captures bureau des douze pages en états réel/différé/manquant ;
12. vérification réseau qu'aucun endpoint compte/ordre n'est appelé.

## 10. Décisions humaines restantes

- Visibilité/licence des deux dépôts et traitement des données déjà publiées.
- Autorisation de B-03 et choix d'hébergement TradingView/Cloudflare.
- Ensemble exact des entitlements IBKR et droits de conservation par flux.
- Univers maximum et latence cible par session.
- Sources externes autorisées pour news, macro, fondamentaux et social.
- Modèle d'IA éventuel, données transmises, budget et politique de rétention.
- Capture maîtresse versionnée pour la validation pixel.
- Seuils de promotion d'un modèle et personnes autorisées à approuver.

## 11. Prochaine commande recommandée à Claude

Après lecture complète du présent rapport et du skill
`vertex-cloud-max-audit`, rester en mode Plan et préparer uniquement le Lot 00 :

`EXÉCUTE LOT 00`

Ne pas lancer les autres lots, ne pas fusionner l'ancien dépôt et ne pas tester
TWS depuis le cloud avant acceptation du plan et fermeture des deux P0.

PLAN CLOUD VERTEX TERMINÉ — AUCUNE MODIFICATION EFFECTUÉE
