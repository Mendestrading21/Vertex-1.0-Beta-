# Matrice de récupération du Vertex actuel

## Snapshot audité

| Champ | Valeur vérifiée |
|---|---|
| Dépôt | `Mendestrading21/Vertex-` — public |
| Branche par défaut | `main` |
| HEAD | [`c683c944f93f61d5fd22303df726fac6e79820fe`](https://github.com/Mendestrading21/Vertex-/commit/c683c944f93f61d5fd22303df726fac6e79820fe) |
| Date du commit | `2026-08-28T19:55:51Z` |
| Titre | merge PR `#856` — fraîcheur serveur honnête |
| Écart depuis le précédent audit | `4` commits, `15` fichiers modifiés ou ajoutés, branche en avance et non divergente |
| Derniers changements utiles | publication de lignes par copie atomique (lot 45) et timestamps serveur sur calendrier/options (lot 46) |
| CI du merge | non vérifiable par le connecteur : aucun workflow PR ni statut combiné n'est retourné pour ce SHA |
| Résultat déclaré dans le dépôt | `4 471 passed`, `152 skipped`, `0 failed` dans `docs/vertex-2-0/lot-46/RAPPORT.md`; déclaration non assimilée à une preuve CI indépendante |

Le fichier lu sans `ref` sur `main` et le même fichier lu au SHA figé possèdent le même blob Git (`docs/vertex-2-0/lot-46/RAPPORT.md`, blob `bdbb577a…`). Le SHA ci-dessus est donc le point de départ de cette matrice, pas l'ancien `9c0e0bc…`.

## Méthode et limites

- Métadonnées, HEAD, comparaison de commits et fichiers structurants ont été lus avec le connecteur GitHub en lecture seule. Aucune mutation GitHub n'a été appelée.
- L'index de recherche de code du dépôt est signalé indisponible et le connecteur refuse de lister un répertoire. L'inventaire d'arbre complet vient donc du clone propre du SHA `9c0e0bc…`, complété par la comparaison GitHub exhaustive `9c0e0bc… → c683c944…` puis par une relecture au HEAD des fichiers structurants et des 15 chemins changés.
- Les volumes actuels sont des projections contrôlées à partir de cette comparaison : environ `2 544` fichiers suivis, `952` Python, `524` fichiers `tests/test*.py`, `1 082` Markdown, `49` JavaScript, `19` CSS et `359` PNG. Ils ne remplacent pas une nouvelle énumération d'arbre GitHub, impossible avec le connecteur disponible.
- Aucun TWS/IB Gateway, abonnement, webhook TradingView, fournisseur IA, sauvegarde ou navigateur réel n'a été lancé. La disponibilité live et les entitlements ne sont donc pas certifiés ici.
- Les valeurs des JSON de runtime, données de portefeuille, caches, secrets, historique Git sensible, binaires, polices et captures n'ont pas été ouvertes. Seuls leurs rôles et chemins non sensibles sont inventoriés.
- L'absence de `LICENSE` et de `NOTICE` racine est confirmée par GitHub. Geist dispose d'un texte OFL; le dépôt documente Chart.js MIT et Lightweight Charts Apache-2.0, mais toute réutilisation passera quand même par le registre de dépendances de Vertex 1.0. Aucun code ou binaire n'est copié par cette matrice.

## Sens des décisions

| Décision | Sens obligatoire dans Vertex 1.0 |
|---|---|
| `KEEP_AS_REFERENCE` | Conserver uniquement exigence, comportement observé, preuve ou vecteur de test. Aucun import de code. |
| `ADAPT` | Réexprimer l'idée dans les contrats et l'architecture neufs après revue licence, sécurité et exactitude. Aucun copier-coller. |
| `REWRITE` | Refaire intégralement depuis la spécification et des oracles indépendants. L'implémentation actuelle n'entre pas dans le nouveau runtime. |
| `DROP` | Ne pas migrer. La capacité ou l'artefact est exclu du produit cible. |

La matrice YAML `manifests/current-vertex-salvage.yaml` est la version exploitable par Claude Code. En cas d'écart, le YAML fait foi pour les identifiants et dispositions.

## Architecture

| ID | Capacité et preuves au HEAD | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| A01 | Runtime Flask encore centré sur `terminal.py`; `vertex.runtime` active le profil puis importe le monolithe. `README.md`, `vertex/runtime.py`, `terminal.py`, `vertex/app/factory.py` | `REWRITE` | État et responsabilités couplés; démarrage difficile à isoler. | Monolithe modulaire local : FastAPI, worker, edge IBKR et web séparés; aucun import du runtime historique. |
| A02 | Découpage métier déjà visible sous `vertex/{data_sources,engines,options,portfolio,positions,storage,ui}`. | `ADAPT` | Les frontières déclarées restent traversées par injections et globals. | Reprendre le vocabulaire de domaines, puis imposer dépendances unidirectionnelles et contrats Pydantic. |
| A03 | `scan_state` global mutable; lots 42/45 améliorent publication générationnée et copie des rows. `vertex/app/state.py`, `terminal.py`, `tests/test_rows_publies_immuables_lot45.py` | `REWRITE` | Snapshots encore partagés; lecture concurrente et mutation résiduelle possibles. | Observations immuables, transaction/outbox PostgreSQL, snapshots typés et versionnés. Garder les invariants du lot 45 comme tests. |
| A04 | Magasin stale-while-revalidate et singleflight. `vertex/app/snapshot.py` | `ADAPT` | Clés/threads et plafonds insuffisamment bornés selon l'audit précédent. | Cache borné par domaine, métadonnées `DataEnvelope`, cancellation, backpressure et métriques. |
| A05 | File IBKR pure : priorités, coalescence, péremption, breaker. `vertex/services/file_ibkr.py` | `ADAPT` | Clé via `repr(args)`, file non bornée et retour `None` ambigu. | Edge IBKR unique, clé de requête typée, limites/pacing, erreurs structurées et tests de contention. |
| A06 | Registre point-in-time append-only avec `observed_at`, `available_at`, `received_at`, checksum et migrations. `vertex/storage/point_in_time.py`, `vertex/storage/schemas.py` | `ADAPT` | JSONL local non transactionnel et peu branché au runtime. | Tables append-only PostgreSQL + Parquet/DuckDB recherche; même sémantique temporelle et contrôle d'intégrité. |
| A07 | 29 blueprints et près de 200 endpoints; factory partielle et injections restantes. `vertex/app/factory.py`, `vertex/app/routes/*.py` | `REWRITE` | API non typée, collisions/aliases et réseau parfois exécuté dans une requête. | API FastAPI OpenAPI, DTO générés, jobs asynchrones, aucune collecte dans les routes. |

## Pages et routes

Toutes les pages conservent leur question métier et leurs besoins comme référence; leur HTML Python, CSS inline et JavaScript spécifique sont réécrits.

| ID | Surface actuelle et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| P01 | Aujourd'hui `/`; brief dense et nombreux modules. `vertex/ui/pages/briefing.py`, `vertex/app/routes/redesign.py` | `REWRITE` | Page très volumineuse, priorité et états trop dispersés. | `/today` : file de 8–15 éléments, provenance et raison de priorité; trois à cinq modules. |
| P02 | Calendrier `/calendar`; `/cal-feed` possède désormais `ts` serveur. `calendar_page.py`, `calendar.js`, lot 46 | `REWRITE` | Couverture partielle et catégories reconnues sans source. | Agenda jour/semaine fusionné, dates révisables, droits et couverture explicites. |
| P03 | Marchés `/markets`. `markets_page.py` | `REWRITE` | Page et graphiques monolithiques, provenance/fallback non obligatoires. | Heatmap/treemap dominante, régime/breadth/dispersion calculés au serveur et table accessible. |
| P04 | Opportunités `/opportunities`. `opportunities_page.py`, `opportunities_api.py` | `REWRITE` | Plusieurs scores/verdicts, densité et adaptateurs ad hoc. | Table qualifiés/exclus issue du seul `AdviceEngine`, gates avant rang, aucune action d'ordre. |
| P05 | Analyse `/analysis[/<sym>]`. `analysis_page.py`, `analysis_api.py` | `REWRITE` | Deux moteurs graphiques et vérité R:R/décision incohérente. | Dossier instrument typé, chandeliers LWC, preuves, gates et calculs canoniques. |
| P06 | Options `/options`, dossier `/options/dossier/<sym>`; `/options/<sym>` reste JSON. `options_intel_page.py`, `options_symbol_page.py`, `ticker_api.py` | `REWRITE` | Sémantique de route collisionnée; neuf sous-vues et calculs/identités hétérogènes. | `/options` et contrat exact par `OptionContractId`; chaîne principale, surface/risque/scénarios secondaires. |
| P07 | Simulateur `/simulator`. `simulator_page.py`, `redesign.py`, `scenario_pricer.py`, `multileg_lab.py` | `REWRITE` | Multiplicateur/horizon et modèles américains incomplets. | Scénarios certifiés spot × temps × IV, payoff multi-jambes, hypothèses et limites obligatoires. |
| P08 | Portefeuille `/portfolio`. `portfolio_page.py`, `desk.py`, `positions/repository.py` | `REWRITE` | Store JSON, sous-vues redondantes et limites historiques divergentes. | Portefeuille exclusivement manuel/import approuvé, ledger transactionnel, risque et thèses séparés. |
| P09 | Suivi `/follow-up`, alias `/tracking`. `tracking_page.py`, `tracking_api.py` | `REWRITE` | Suit surtout des idées hypothétiques; pas de thèse/révision append-only complète. | File de revues, timeline de preuves et révisions immuables; aucune modification automatique de thèse. |
| P10 | Performance `/performance`, alias `/journal`. `performance_page.py`, `track_record_api.py`, `performance_ledger.py` | `REWRITE` | Discipline et performance vivent encore dans plusieurs populations/lieux. | Capital/drawdown, TWR/XIRR, brut/net et populations strictement séparées; export reproductible. |
| P11 | Vertex IA actuelle `/intelligence`. `intelligence_page.py`, `ai_api.py`, `vertex/ai/*` | `REWRITE` | Texte Copilot non uniformément cité/validé et plusieurs chemins fournisseur. | `/ai` : réponse structurée, claims cités vers snapshots, aucune écriture, aucun calcul ou verdict IA. |
| P12 | Système `/system`. `system_page.py`, `system.py`, `strategy_os_api.py` | `REWRITE` | Santé globale peut masquer sources/jobs incomplets; entitlements non exhaustifs. | Matrice sources × capacités avec droits déclarés/testés, couverture, fraîcheur, queues, backups et diagnostics. |

## Composants, styles, graphiques et actifs

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| U01 | Shell, navigation groupée, deep links et progressive enhancement. `vertex/ui/shell/__init__.py`, `vx-router.js` | `ADAPT` | Shell Python + routeur maison; commentaires et héritages obsolètes. | React Router, TanStack Query, Beta desktop-only 1280/1440/1600 et dégradation 1024; mobile `LATER`; conserver les quatre groupes après test utilisateur. |
| U02 | Primitives `vx2` qui rendent absent `—` et interdisent les calculs. `vertex/ui/vx2.py` | `ADAPT` | HTML concaténé et contrats facultatifs. | Composants React/Radix typés; `DataStateBoundary`, `ProvenanceBadge`, `Metric`, `Table`, `Drawer`. |
| U03 | Vocabulaire loading/empty/stale/error/offline/demo et fraîcheur. `states.css`, `vx-core.js`, lot 46 | `ADAPT` | États incomplets et implémentés page par page; démo remplace parfois partial/delayed. | Huit états obligatoires : loading, empty, partial, delayed, stale, offline, error, refreshing; fixtures et tests. |
| U04 | `ChartCard` porte question, unité, source, date et limites. `chart-core.js`, `vx2.py` | `ADAPT` | Métadonnées encore facultatives; logique de rendu dispersée. | `ChartFrame` strict avec table accessible/export; le build échoue si une métadonnée requise manque. |
| U05 | Chart.js 4.4.1 et Lightweight Charts 4.2.3 vendus dans le dépôt. `static/chart.umd.min.js`, `vertex/static/vertex/js/vendor/*` | `DROP` | Deux stacks, versions figées manuellement et notices racine incomplètes. | Installer ECharts et Lightweight Charts officiels, versions verrouillées, attribution/NOTICE générés; aucun fichier vendored repris. |
| U06 | Palette Black Glass, obsidienne/argent, vert positif, rouge risque, ambre prudence, violet options. `tokens.css`, `vertex-2-0.css` | `ADAPT` | Dix-neuf feuilles et alias legacy; deux couches revendiquent une vérité finale. | Conserver l'ADN couleur, recréer une seule taxonomie de tokens avec contrastes WCAG et zéro alias historique. |
| U07 | Geist sous OFL; autres polices, icônes PNG/SVG et triangle de marque présents. `fonts/licences/GEIST-OFL.txt`, `static/icon-180.png`, routes favicon/manifest | `ADAPT` | Provenance/licence non uniforme pour tous les binaires et glyphes décoratifs. | Geist via paquet/source vérifiée, icônes Lucide ou SVG internes, nouveau logo validé; ne reprendre aucun binaire sans preuve de droits. |

## Calculs et décision

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| C01 | Identités instrument et options existent partiellement. `vertex/domain/instruments.py`, `ibkr_contracts.py`, `ibkr_option_chain.py` | `ADAPT` | Symbole/date d'expiration encore utilisés comme clés; `trading_class` et ajustements incomplets. | `InstrumentId` et `OptionContractId` exacts, `conId`, trading class, multiplicateur, devise, règlement et période de validité. |
| C02 | Plan action calcule `rr_res` mais publie aussi `plan.rr=3.0`; `rr_score` publie un score 0–100 sous `rr`. `analysis.py`, `quant_engine.py` | `REWRITE` | Grandeurs financière et score confondues; verdict potentiellement faux. | Une formule R:R versionnée, unités/coûts explicites, état `INVALID`; score nommé séparément et jamais affiché comme ratio. |
| C03 | Advice, DecisionStack, Executive, Comité, Skyler et Strategy OS publient des orientations. `vertex/engines/*`, `vertex/strategy/*` | `REWRITE` | Autorités concurrentes et gates fail-open. | Un seul `AdviceEngine`; `GateResult` fail-closed puis statut/direction séparés; anciennes sorties deviennent uniquement preuves. |
| C04 | Indicateurs, breadth, régimes, facteurs et contexte multi-horizon. `vertex/engines/indicators.py`, `vertex/market/regime_*`, `vertex/research/institutional/*` | `ADAPT` | Méthodes/versions et univers point-in-time non uniformes. | Registre YAML des calculs, fonctions pures, unités, fenêtres, univers et tests contre références indépendantes. |
| C05 | BSM, IV, Greeks, payoff, scénarios, surface, GEX et tests golden. `scenario_pricer.py`, `legacy_engine.py`, `multileg_lab.py`, `tests/test_calculations_golden.py` | `ADAPT` | Doublons, modèle européen appliqué à des américaines, ×100 et hypothèses de GEX. | QuantLib comme cœur, SciPy oracle, modèle selon style, multiplicateur contrat, bornes d'arbitrage et hypothèse dealer visible. |
| C06 | Risque portefeuille : poids, concentration, secteurs, bêta, corrélations, stress et Greeks. `portfolio/risk_engine.py`, `portfolio_stress.py` | `ADAPT` | Couverture partielle et sources réelles/simulées encore ambiguës dans des couches legacy. | Calculs sur ledger manuel typé, couverture/unité/devise obligatoires, scénarios et résultats certifiés. |
| C07 | `PerformanceLedger` sépare plusieurs populations mais calcule des métriques simplifiées. `performance_ledger.py` | `REWRITE` | Pas de ledger cashflow/FX transactionnel, Sharpe-like et absence de TWR/XIRR. | Ledger double entrée simplifié, cashflows/frais/FX datés, TWR/XIRR et métriques définies/versionnées. |
| C08 | Probabilités ML/Kelly/Monte-Carlo heuristiques. `quant/ml_calibration.py`, `quant_engine.py`, `validation/probability_calibration.py` | `DROP` | Probabilité non entraînée/calibrée utilisée comme vérité; Kelly fondé sur heuristique. | Aucune probabilité affichée avant dataset, calibration hors échantillon, Brier/log-loss et `probability_evidence` valides. |
| C09 | Forward-test/backtest sur watchlist actuelle et pseudo walk-forward. `engines/backtest.py`, `research/*` | `DROP` | Survivorship bias, coûts/slippage/capacité et réentraînement incomplets. | Nouveau laboratoire point-in-time séparé du runtime; LEAN/oracle externe et données licenciées. Aucun résultat historique migré. |

## Connecteurs et sources

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| X01 | Gateway IBKR `readonly=True`, quotes/historique et détection prudente live/delayed. `ibkr_gateway.py`, `ibkr_market_data.py`, `ibkr_historical.py` | `ADAPT` | Connexion dispersée dans le monolithe; type live/frozen parfois non observable. | Edge IBKR isolé, `ib_async` derrière une façade étroite, epoch de connexion, codes 1100/1101/1102/1300 et état de droit. |
| X02 | Entonnoir chaînes, OI, IV, Greeks et annulation des abonnements. `ibkr_option_chain.py`, `options/chain_loader.py` | `ADAPT` | Identité de contrat et pacing encore incomplets; appels à la demande parfois longs. | `reqSecDefOptParams`, budget de lignes, snapshots exacts, pacing/backpressure et contrat qualifié avant calcul. |
| X03 | Dépêches IBKR interrogées fournisseur par fournisseur. `ibkr_news.py`, `market/news_pipeline.py` | `ADAPT` | Liste de fournisseurs mesurée pour un compte et droits article non modélisés. | Découverte dynamique des providers, `ArticleAccess`, entitlement, déduplication et conservation des droits/horodatages. |
| X04 | Lecteur historique de résumé de compte/positions encore présent dans des scripts racine. `ib_reader.py`, `test_connection.py`; worker actif réduit au socket dans `terminal.py` | `DROP` | Frontière market-data-only contournable et données de compte imprimables. | Aucun account/position/execution/order call dans le nouveau dépôt; portefeuille manuel uniquement. |
| X05 | Webhook TradingView avec secret dans JSON, store mémoire et Pine. `tradingview_webhooks.py`, `tradingview_signal_store.py`, `tradingview/vertex_signals.pine` | `REWRITE` | Documentation/Pine/timestamp incohérents, `payload()` non utilisé, anti-replay/dédup non durable et callback masqué. | TradingView → ingress Cloudflare → Queue/DLQ → pull local; schéma versionné, idempotence durable, quote IBKR fraîche avant réévaluation. |
| X06 | Gateway IA avec budgets/audit; Copilot appelle Anthropic et possède un fallback. `vertex/ai/gateway.py`, `copilot.py`, `response_validator.py` | `REWRITE` | Validation/citations non uniforme et contexte encore construit depuis stores bruts. | Passerelle IA sans accès TWS/DB/secrets, outils read-only allowlistés, schéma strict, citations vers snapshots et refus calcul/ordre. |
| X07 | Sources primaires SEC, FRED et BLS. `sec_edgar.py`, `sec_fondamentaux.py`, `fred.py`, `bls.py` | `ADAPT` | Couverture, vintages, entitlements et retries non unifiés. | Connecteurs officiels versionnés, ALFRED/vintages, taxonomie/unités, cache et limites par source. |
| X08 | yfinance/Stooq et autres fallbacks web dans scan/fondamentaux. `fallback_market_data.py`, `fundamentals.py`, `terminal.py` | `DROP` | Origines mélangées, révisions non point-in-time, throttling et qualité incertaine. | Interdits pour décision live; éventuellement sandbox recherche explicitement non autoritaire. |
| X09 | WMB/news plus et enrichissements web. `market/wmb.py`, `services/news_plus.py` | `ADAPT` | Réseau, droits et provenance hétérogènes; certains appels bloquants. | Sources primaires/IR autorisées via Data Fusion Hub; ingestion asynchrone, droits et clusters déterministes. |

## Données et stockage

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| D01 | `ProvenancedValue`, fraîcheur par mode et pire qualité critique. `data_sources/models.py`, `provenance.py`, `quality.py`; lot 46 | `ADAPT` | Métadonnées non appliquées à tous les payloads; seuils globaux. | `DataEnvelope[T]` obligatoire avec observation/publication/réception, stale-after, droit, epoch, hash et couverture. |
| D02 | Routeur de source priorisé. `source_router.py` | `REWRITE` | Fallback peut devenir une seconde vérité et la matrice d'entitlements n'est pas exhaustive. | Priorité par champ, `SourceEntitlement`, `SourceCoverage` et états `AVAILABLE/DELAYED/MANUAL_EXPORT/NOT_ENTITLED/UNSUPPORTED/ERROR`. |
| D03 | Caches et stores JSON atomiques par fichier. `services/persist.py`, routes desk/tracking | `REWRITE` | Échec d'écriture avalé, transaction read-modify-write non atomique, cloud éphémère. | PostgreSQL/Alembic, transactions, optimistic locking, outbox; sauvegarde et restauration testées. |
| D04 | Positions manuelles/simulées et suivis. `positions/models.py`, `positions/repository.py`, `tracking/*` | `ADAPT` | Schémas legacy et données personnelles potentielles dans les fichiers runtime. | Migrer uniquement schémas et données explicitement choisies après export/redaction; jamais les blobs du dépôt automatiquement. |
| D05 | News, calendrier, fondamentaux et événements existent dans plusieurs pipelines. `news_pipeline.py`, `macro_calendar.py`, `catalysts/*`, `company/*` | `REWRITE` | Pas de Data Fusion unique, déduplication/droits/révisions partiels. | Hub de fusion : entités, clusters, conflits, événements révisables, fondamentaux/ETF et classement explicable. |
| D06 | Univers/constituants et données démo statiques. `data/universe.py`, `_constituents_static.py`, `data/demo.py` | `DROP` | Survivorship bias et confusion possible entre fixture et donnée réelle. | Fixtures synthétiques séparées; univers de recherche point-in-time et univers live déclaré par source. |

## Tests, qualité et preuves

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| T01 | Suite pytest très large; rapport du lot 46 annonce 4 471 réussites. `tests/**`, `docs/vertex-2-0/lot-46/RAPPORT.md` | `KEEP_AS_REFERENCE` | Fort couplage à l'implémentation historique et 152 skips déclarés; CI du merge non vérifiée. | Extraire scénarios/invariants utiles; ne pas porter la suite en bloc. Nouvelle pyramide unit/contract/integration/E2E. |
| T02 | Tests golden et propriétés mathématiques. `tests/test_calculations_golden.py` et tests options/portfolio. | `ADAPT` | Certains goldens comparent deux implémentations internes et non un oracle externe. | Vecteurs indépendants QuantLib/SciPy/finance, tolérances/units/edge cases inscrits au registre. |
| T03 | Garde no-orders et readonly. `tests/test_no_orders.py`, contrôles IBKR. | `ADAPT` | Scanner par motifs incomplet et capacités racine/JS/config difficiles à couvrir. | AST + allowlist d'appels IBKR + manifeste forbidden-capabilities + tests d'API et CI bloquante. |
| T04 | Tests des lots 45/46 : immutabilité publiée et fraîcheur serveur. `test_rows_publies_immuables_lot45.py`, `test_fraicheur_honnete_lot46.py` | `KEEP_AS_REFERENCE` | Tests très liés au texte/source de `terminal.py`. | Réécrire comme propriétés de contrats : snapshot antérieur immuable et aucun timestamp client présenté comme observation. |
| T05 | Tests a11y/Lighthouse/Playwright existent. `requirements-dev.txt`, `test_a11y_lighthouse_lot28.py`, autres tests navigateur. | `REWRITE` | Chromium absent de la CI et plusieurs tests s'abstiennent. | Playwright Chromium/Firefox/WebKit, axe, 1280/1440/1600, smoke 1024, captures et budgets Web Vitals obligatoires; aucune QA mobile en Beta. |
| T06 | CI compile/test/safety. `.github/workflows/ci.yml` | `REWRITE` | Actions par tags, dépendances non verrouillées, pas de CodeQL/SBOM/CVE/licences; branches/rulesets non prouvés. | Actions pinées SHA, uv/pnpm lock, CodeQL, dependency review, gitleaks, pip-audit/OSV, Syft/Grype/Cosign et ruleset PR. |

## Configuration, sécurité et livraison

| ID | Capacité et preuves | Décision | Risque actuel | Cible Vertex 1.0 |
|---|---|---|---|---|
| S01 | Constitution `ANALYSIS_ONLY`, `READONLY`, aucun ordre. `README.md`, `READONLY_SAFETY.md`, `app/config.py` | `KEEP_AS_REFERENCE` | Le texte seul ne ferme pas les anciens appels compte/positions. | Constitution machine-readable, capacités interdites, TWS read-only et tests fail-closed. |
| S02 | Code d'accès optionnel et session Flask. `app/routes/auth.py`, `app/config.py` | `REWRITE` | Démo sans code ouverte; authentification faible pour tout accès distant. | Runtime Vertex loopback-only pour la Beta; téléphone limité à Claude Remote Control officiel; aucune interface Vertex distante ou publique. |
| S03 | `requirements.txt`/`requirements-dev.txt` avec plages larges. | `REWRITE` | Résolution non reproductible et audit supply-chain absent. | Python 3.13, `pyproject.toml` + `uv.lock`; Node 24 + `pnpm-lock.yaml`; registre licences et digests. |
| S04 | Déploiement Render gratuit, `0.0.0.0`, `DEMO=1`. `render.yaml` | `DROP` | Démo publique mutable, stockage éphémère et TWS absent. | Produit local-first; seul ingress TradingView public et minimal. Aucun runtime Vertex public. |
| S05 | Variables d'environnement et validation d'alias. `.env.example`, `app/config_validation.py` | `ADAPT` | Noms historiques multiples et options de sécurité facultatives. | Schéma de configuration strict, secrets hors dépôt, démarrage refusé si incohérent; aucun secret dans diagnostic. |
| S06 | Lanceurs `.bat/.command/.cmd` et service worker manuel. `Lancer_VERTEX*`, `Installer_Demarrage_Auto.bat`, `sw.js` dans `system.py` | `DROP` | Multiples chemins de démarrage/cache, rollback et versions manuels. | Scripts `make`/PowerShell documentés, services locaux explicites; PWA seulement après stratégie offline testée. |
| S07 | Geist OFL documenté, Chart.js MIT et LWC Apache documentés; pas de `LICENSE`/`NOTICE` racine. | `REWRITE` | Provenance globale et redistribution non gouvernées. | `THIRD_PARTY_NOTICES`, SBOM et vérification licence automatisée; décision de licence propriétaire/open source avant release. |
| S08 | Nombreux audits, rapports et skills Claude. `docs/**`, `.claude/**`, `CLAUDE.md` | `KEEP_AS_REFERENCE` | Plus de mille Markdown, contradictions historiques et coût de navigation élevé. | Conserver seulement preuves sélectionnées dans l'inventaire de migration; le pack Vertex 1.0 reste l'autorité unique. |

## Ordre de récupération

1. Extraire les invariants `S01`, `T03`, `T04`, `C01` et `D01` avant toute page.
2. Refaire `A01`, `A03`, `A07`, `D02` et `D03`; aucune UI ne doit contourner ces fondations.
3. Adapter les connecteurs IBKR et sources primaires, puis reconstruire TradingView et l'IA derrière leurs limites.
4. Certifier calculs/gates avant les pages Analyse, Options, Simulateur, Portefeuille et Performance.
5. Recréer le design Black Glass et les 12 pages une par une; ne migrer ni HTML, ni CSS, ni JS historique.
6. N'importer des données personnelles qu'après inventaire, aperçu du diff, consentement explicite et sauvegarde restaurable.

## Décision globale

Le Vertex actuel est une excellente **bibliothèque de besoins, d'incidents, de tests et d'idées métier**, mais pas une base de code à prolonger. Le salvage recommandé est contractuel : récupérer l'intention, les preuves et quelques invariants algorithmiques; reconstruire le runtime, la vérité financière, le stockage, les connecteurs et l'interface.
