# Ce que Vertex PEUT calculer et ne calcule pas encore

## 0. Périmètre de lecture (honnêteté sur les preuves)

**Lu intégralement** : `calculations/__init__.py` (vide), `contracts/` (enums, calculation, decision, envelope, information, identity, market_quote), `CALCULATION_REGISTRY.yaml` (en-tête + tous les `id`/`runtime_status` + les 4 entrées non-APPROVED en entier), `CALCULATION_CATALOG.md`, `DECISION_ENGINE.md`, `PROBABILITY_CALIBRATION.md`, `OPTIONS_FLOW_INTELLIGENCE.md`, `REGIME_AND_SECTOR_MODEL.md`, `MODEL_RISK_AND_VALIDATION.md` (première moitié), `SIGNAL_FUSION.md` (première moitié), `SOURCE_CAPABILITY_MATRIX.md`, `OFFICIAL_SOURCE_MAP.md`, `IBKR_EXPLOITABLE_FIELDS.md`, `OFFICIAL_SOURCE_ADAPTERS.md`, `TRADINGVIEW_EXPLOITABLE_FIELDS.md`, `IBKR.md` (début), `SOURCE_RIGHTS_AND_RETENTION.md` (classes + rétention), `manifests/options-anomaly-features.yaml`, `contracts/json-schema/option-anomaly-snapshot-v1.schema.json`, `apps/worker/.../options.py` (entier), `edge-ibkr/port.py` (modèles), `edge-ibkr/normalize.py`, `worker/risk.py` (contenu publié).

**Lu par signatures + docstrings + extraits ciblés** : `calculations/market.py`, `options.py`, `performance.py`, `portfolio.py`, `risk.py`, `decision/gates.py`, `decision/advice.py`, `worker/markets.py`, `analysis.py`, `opportunities.py`, `performance.py`, `follow_up.py`, `calendar.py`, `handlers.py`, `api/routes.py`, `api/schemas.py`.

**NON lu** : `api/snapshot_views.py` (114 Ko), `api/ai_explain.py` (91 Ko), `worker/portfolio.py` en entier, `ANOMALY_ENGINE.md`, `EVIDENCE_GRAPH.md`, `ATTENTION_AND_RELEVANCE_ENGINE.md`, `OPTIONS_PRICING_AND_SCENARIOS.md`, `DATA_FUSION.md`, `INFORMATION_UNIVERSE.md`, `NEWS_SOCIAL_INTELLIGENCE.md`, `AI_GATEWAY.md`, `IBKR_ENTITLEMENT_PROBE.md`, `DEPENDENCY_REGISTER.md`. Aucune affirmation ci-dessous ne repose sur ces fichiers.

**Correction factuelle** : `apps/api/src/vertex_api/routes.py` déclare **27** routes (`@public_router`/`@protected_router`), pas 28 ; la 28ᵉ vient du `auth_router` monté séparément (`app.py:150-152`).

---

## 1. Le registre exact des calculs autorisés

`docs/03-domain/calculations/CALCULATION_REGISTRY.yaml`, `registry_status: runtime_partially_approved`. **22 entrées APPROVED, 1 RESEARCH_ONLY, 2 NOT_IMPLEMENTED.**

| Famille | `id` APPROVED |
|---|---|
| market | `simple_return`, `log_return`, `realized_volatility`, `atr`, `rebased_series`, `relative_strength`, `breadth`, `sma`, `ema`, `bollinger_bands`, `rsi`, `macd` |
| options | `forward_price`, `no_arbitrage_bounds`, `european_price`, `american_price`, `implied_volatility`, `greeks`, `payoff`, `scenario_grid` |
| portfolio | `realized_pnl`, `unrealized_pnl`, `concentration` |
| performance | `twr`, `xirr`, `drawdown` |
| risk | `covariance`, `correlation` |
| decision | `risk_reward` |

Trois blocages de registre à connaître avant tout plan :

- `portfolio.fx_conversion` → **RESEARCH_ONLY** (ligne 611). Interdit dans un `CalculationRecord` de production. **Toute agrégation multi-devises est bloquée par là.**
- `options.gex_estimate` → **NOT_IMPLEMENTED**, `blocking_reason` : « no function, no module and no string literal "options.gex_estimate" appears anywhere in packages/python or apps ».
- `probability.calibration` → **NOT_IMPLEMENTED**, `criticality: critical`. Tant qu'elle l'est, **aucune probabilité prédictive ne peut être affichée** (loi 5).

Trois entrées APPROVED portent `runtime_usage: not_called_by_production_code_yet` : `risk.covariance`, `risk.correlation` (fausse aujourd'hui — `worker/risk.py:326` les appelle) et **`decision.risk_reward`** (vraie : R:R est approuvé, testé, et appelé par personne).

---

## 2. Trois constats structurants — ce que les jobs JETTENT

### Constat A — `ibkr.quote/1` est écrit en base et lu par personne

`apps/edge-ibkr/src/vertex_edge_ibkr/port.py:262-268` — `QuoteObservation` porte exactement les champs dont l'intelligence d'options a besoin :

```python
call_volume: FiniteDecimal | None = None                    # tick 29 (generic 100)
put_volume: FiniteDecimal | None = None                     # tick 30 (generic 100)
call_open_interest: FiniteDecimal | None = None             # tick 27 (generic 101)
put_open_interest: FiniteDecimal | None = None              # tick 28 (generic 101)
historical_volatility_30d: FiniteDecimal | None = None      # tick 23 (generic 104)
average_option_volume: FiniteDecimal | None = None          # tick 87 (generic 105)
option_implied_volatility_30d: FiniteDecimal | None = None  # tick 24 (generic 106)
```

`adapter.py:976-982` les mappe réellement. `adapter.py:122-131` les estampille `ibkr.quote/1`. Et ensuite :

1. **Aucun handler ne lit `ibkr.quote/1`.** `markets.py:101` n'admet que `ibkr.daily-quote/`, `analysis.py:178` que `ibkr.daily-bars/`, `handlers.py:140-176` exclut explicitement les familles de marché du rail de preuve. L'observation est persistée et morte.
2. **Pire : le collecteur ne demande jamais ces ticks.** `EdgeIbkrRunner.__init__` a `generic_ticks: tuple[int, ...] = ()` (`runner.py:134`) et `tools/run_edge_ibkr.py:237-252` construit le runner **sans passer `generic_ticks`**. Les ticks 100/101/104/105/106 ne sont donc jamais demandés à TWS en production. Seul `probe.py:275-276` les teste.

### Constat B — la chaîne d'options réelle n'a aucun producteur

`worker/options.py:113` admet le préfixe `ibkr.option-chain/`. Mais `adapter.py:130` associe ce schéma à `OptionChainDefinition`, dont `port.py:390-402` donne la forme réelle : `exchange`, `underlying_con_id`, `trading_class`, `multiplier`, `expirations`. **Ni `contracts`, ni `underlying_spot`, ni `rate`, ni `dividend_yield`** — les quatre champs que `build_option_chain_content` exige (`options.py:459-476`), faute de quoi l'enregistrement est rejeté `REASON_INVALID_PAYLOAD`.

Conséquence : le seul producteur d'une chaîne cotée est `vertex_core/synthetic/options.py`. **Toute intelligence d'options ci-dessous est aujourd'hui calculable uniquement sur `population: "SYNTHETIC"`.**

### Constat C — la chaîne garde volume et OI, et n'agrège rien

`worker/options.py:452-461` conserve par contrat :

```python
"volume": raw.get("volume") if isinstance(raw.get("volume"), int) else None,
"open_interest": raw.get("open_interest") if isinstance(..., int) else None,
"open_interest_status": raw.get("open_interest_status") if isinstance(..., str) else None,
```

relayés verbatim par `api/schemas.py:462-464`. Le contenu publié (`options.py:757-778`) contient `spot`, `assumptions`, `expirations[]`, `row_budget`, `coverage` — **aucun bloc d'agrégat**. Tout est là, rien n'est sommé.

---

## 3. Verdicts

### Intelligence d'options

---

**1. Ratio put/call — FAISABLE**

*Entrée qui existe.* Deux bases distinctes, à ne jamais confondre :
- **Chaîne exacte** : `contracts[].volume` et `contracts[].open_interest` + `right` (`worker/options.py:433,452-461`), servis par `OptionChainContract` (`schemas.py:440-467`).
- **Sous-jacent (tick)** : `call_volume`/`put_volume` (tick 29/30), `call_open_interest`/`put_open_interest` (tick 27/28) — `port.py:262-265`. Non demandés, non normalisés (constat A).

*Calcul à écrire.* `options.put_call_ratio` dans `packages/python/vertex_core/src/vertex_core/calculations/options.py`. Entrées : `call_quantity: int`, `put_quantity: int`, `basis: Literal["VOLUME","OPEN_INTEREST"]`, `scope: Literal["EXACT_CHAIN","UNDERLYING_TICK"]`, `covered_count`/`expected_count`. Portes : `positive_denominator` (put = 0 → `INSUFFICIENT_DATA`, jamais ∞ ni 0), `coverage_threshold`, `open_interest_delay_declared` (le `open_interest_status = "OI_DELAYED"` doit voyager). Un contrat sans `volume` **décrémente la couverture**, il ne compte pas pour zéro (loi 4).

*Contrat.* Bloc `aggregates` ajouté au contenu `option_chain`, bump `OPTION_CHAIN_SCHEMA_VERSION` de `vertex.option-chain/1.0` → `1.1` (`worker/options.py:110`) ; `OptionChainResponse` (`schemas.py:493`) gagne `aggregates: FrozenStrMapping | None`.

*Endpoint.* Existant : `GET /api/v1/options/{underlying}/chain` (`routes.py:391`).

*Tests de propriétés.* `tests/calculations/test_options.py` : ratio ≥ 0 ; `call == put` → exactement 1 ; additivité sur deux sous-populations disjointes ; `put_quantity == 0` ne produit jamais de nombre ; un contrat écarté fait baisser `coverage` et jamais le numérateur.

---

**2. Max pain — FAISABLE (étiqueté DESCRIPTIF, jamais prédictif)**

*Entrée qui existe.* `strike`, `right`, `open_interest`, `multiplier` par contrat (`worker/options.py:430-461`), regroupés par `(expiration, trading_class)` (`options.py:729-746`).

*Calcul à écrire.* `options.max_pain`, même module. Méthode : pour chaque strike candidat *S* du groupe, valeur intrinsèque totale des contrats ouverts = Σ OI·M·max(S−K,0) sur les calls + Σ OI·M·max(K−S,0) sur les puts ; `max_pain = argmin`. Arithmétique `Decimal` sous contexte local 60 chiffres — **le même choix que `payoff_at_expiry` (`options.py:1097-1166`), mais `payoff_at_expiry` n'est pas réutilisable** : il exige `premium` par jambe et passe par `_require_defined_risk_for_shorts`, deux notions absentes ici.

*Portes.* `single_expiration_and_trading_class` (deux `trading_class` à la même échéance sont deux identités — `contracts/identity.py:66-88`) ; `open_interest_complete` (ratio de couverture publié) ; `ties_published` (plusieurs argmin → tous publiés, jamais un choisi).

*Sortie.* `strike`, la courbe complète de valeur, `value_nature: "DESCRIPTIVE"`, `open_interest_as_of`, `open_interest_status`.

*Tests.* OI symétrique sur deux strikes → égalité publiée ; ajouter un contrat d'OI 0 ne déplace rien ; un OI absent n'est pas un OI nul ; invariance par permutation de l'ordre des contrats.

---

**3. Rang et percentile d'IV — BLOQUÉ-PAR-SOURCE (le jour 1), FAISABLE en historique local**

*Preuve du manque.* `apps/web/src/pages/options/optionsModules.ts`, module `iv-rank` : `reason: 'NO_SOURCE'`, note « Aucun historique d'IV n'est collecté ; un rang sans historique serait une valeur inventée. » Diagnostic exact.

*Source officielle manquante.* Une **série historique d'IV licenciée**. Le seul candidat cartographié est **ORATS**, statut dans `SOURCE_CAPABILITY_MATRIX.md` : « Analytique options payante — ORATS — désactivé en attente du plan et des droits ». Droit exigé : classe `R2_LICENSED_METADATA` (`SOURCE_RIGHTS_AND_RETENTION.md`) — droit de **stockage** et d'**affichage** des dérivés, plus la porte de déploiement humaine (propriétaire, finalité, plan tarifaire, plafond de coût, territoires).

*Ce qu'IBKR donne et ne donne pas.* `option_implied_volatility_30d` (tick 24, generic 106) et `historical_volatility_30d` (tick 23, generic 104) existent dans `port.py:266,268` et comme capacités `underlying_option_implied_volatility_30d` / `underlying_historical_volatility_30d` dans `manifests/ibkr-market-data-capabilities.yaml`. Ce sont des **points**, pas une distribution 52 semaines. Ils suffisent à une **divergence IV/HV**, jamais à un rang.

*Chemin honnête.* `OPTIONS_FLOW_INTELLIGENCE.md`, § Historique : « Vertex construit uniquement un historique local à partir des observations auxquelles l'utilisateur a droit. Il ne rétro-invente pas une série… Les détecteurs dont la fenêtre minimale n'est pas atteinte restent `WARMING_UP`. » La table `snapshots` versionne déjà chaque `option_chain/{underlying}` (`models.py:133-141`) : l'historique local est constructible sans nouvelle table. Statut à l'écran d'ici là : `WARMING_UP` avec le compte de séances réellement accumulées.

---

**4. Activité inhabituelle d'options — contrat publié, moteur inexistant**

*Preuve.* `manifests/options-anomaly-features.yaml` déclare `authority: vertex_core.options_anomaly`. **Ce module n'existe pas** : `vertex_core/` contient `calculations`, `contracts`, `data`, `decision`, `fusion`, `synthetic`, `version.py` — rien d'autre. Le schéma `contracts/json-schema/option-anomaly-snapshot-v1.schema.json` est complet (détecteurs, `direction_hypothesis`, `coverage`, `entitlement_evidence`, `safety.trade_side_inference_allowed: false`) et n'a **aucun producteur ni consommateur**.

Verdict par détecteur des 10 déclarés :

| Détecteur | Verdict | Preuve |
|---|---|---|
| `volume_open_interest_ratio` | **FAISABLE** | `volume` + `open_interest` + `open_interest_status` déjà servis (`worker/options.py:452-461`) |
| `strike_expiry_concentration` | **FAISABLE** | idem + `strike`/`expiration` + `greeks.delta` servi pour le delta-bucket |
| `liquidity_cost` | **FAISABLE** | `quote.bid/ask/bid_size/ask_size` + `multiplier` servis (`options.py:440-451`) |
| `quote_integrity` | **FAISABLE, partiellement fait** | `_quote_status` produit `OK/CROSSED/STALE/MISSING` ; `locked` (bid==ask) est **replié dans CROSSED** (documenté `options.py:20-24`) — le publier séparément est un ajout de champ, pas un calcul |
| `contract_volume_percentile` | **BLOQUÉ-PAR-SOURCE** | exige une population de référence point-in-time ; `WARMING_UP` |
| `implied_volatility_shift` | **BLOQUÉ-PAR-SOURCE** | idem (voir item 3) |
| `skew_term_break` | **BLOQUÉ-PAR-SOURCE** | exige `prior_surface` |
| `underlying_call_put_volume_relative` | **BLOQUÉ-PAR-PIPELINE + droit** | ticks 29/30 (generic 100) et 87 (generic 105) jamais demandés (constat A) ; capacités à sonder |
| `catalyst_overlap` | **BLOQUÉ-PAR-SOURCE** | `worker/calendar.py:178` : `CALENDAR_EVENT_SCHEMA_PREFIXES = ("synthetic-calendar-event/",)` — **le calendrier est synthétique uniquement**. Source manquante : IBKR WSH, abonnement séparé (`SOURCE_CAPABILITY_MATRIX.md` : « WSH avec abonnement séparé ») |
| `cross_source_novelty` | **FAISABLE, socle existant** | `vertex_core.fusion.fuse` (dedup + clusters) déjà appelé par `analysis.py` et `follow_up.py` |

*Interdits à graver.* `manifests/options-anomaly-features.yaml`, `forbidden_interpretations` : `smart_money_detected`, `call_is_automatically_bullish`, `put_is_automatically_bearish`, `volume_proves_opening_trade`, `volume_proves_trade_side`, `open_interest_is_intraday`. Et `DirectionHypothesis` (`contracts/enums.py`) est un **type séparé** de `Direction` : l'anomalie ne produit jamais un verdict.

---

**5. Agrégation des Greeks — FAISABLE en mono-devise, BLOQUÉE en multi-devises**

*Entrée qui existe.* `worker/options.py:559-570` publie par contrat `delta`, `gamma`, `vega`, `vega_per_point`, `theta`, `theta_per_calendar_day`, `rho`, `rho_per_bp`, avec `value_nature: "THEORETICAL"` et la lignée `CalculationRecord`.

*La frontière est déjà écrite.* `GreeksResult` docstring, `calculations/options.py:634-636` : « Monetary exposures (multiplier x quantity x FX) are deliberately NOT computed here: they require the manual position declaration and a dated FX rate, which belong to the caller. » C'est donc un **nouveau calcul**, pas une extension de `options.greeks`.

*Deux agrégations distinctes, à ne pas mélanger :*
- **(a) Structure de la chaîne**, pondérée par OI. Descripteur, pas exposition. `value_nature: "DESCRIPTIVE"`. FAISABLE aujourd'hui.
- **(b) Exposition du portefeuille** : Σ qᵢ · Mᵢ · greekᵢ · FX. Entrées : lots déclarés (`models.py:219-231` — `instrument` JSONB, `quantity`, `unit_cost`, `currency`) croisés avec la chaîne. **BLOQUÉE en multi-devises** : `portfolio.fx_conversion` est `RESEARCH_ONLY` au registre (ligne 611) et interdit en production. FAISABLE en mono-devise stricte, avec porte `single_currency` qui refuse au lieu de convertir.

*Calcul à écrire.* `options.greeks_exposure` dans `calculations/options.py`. Money en `Decimal`, greek en float64, **unité déclarée par champ**.

*Contrat/endpoint.* (a) → bloc `aggregates` de `option_chain`, `GET /api/v1/options/{underlying}/chain`. (b) → snapshot portefeuille, `GET /api/v1/portfolio` (`routes.py:706`).

*Tests de propriétés.* Linéarité (agrégat de deux sous-portefeuilles disjoints = somme) ; un greek absent exclut la position et décrémente la couverture, il ne vaut jamais 0 ; convention de signe (quantité courte → contribution négative) ; **non-mélange d'unités** : `theta_per_calendar_day` jamais sommé avec `theta` brut, `vega_per_point` jamais avec `vega`.

---

**6. Structure par terme agrégée — FAISABLE**

*Attention au faux positif.* `optionsModules.ts` déclare `vol-structure` `served`, mais son contrat le dit : `« expirations[].contracts[].iv (petits multiples) »`. L'écran trace des **points d'IV bruts par échéance**. Il n'existe **aucune IV ATM par échéance, aucune pente, aucun nombre**.

*Entrée qui existe.* Par groupe : `maturity_years` (`worker/options.py:736`), `expiration`, et par contrat `strike` + `iv.value` + `greeks.delta` + le `spot` publié (`options.py:764`).

*Calcul à écrire.* `options.atm_iv_term_structure` dans `calculations/options.py`. Méthode : par `(expiration, trading_class)`, IV à la monnaie définie **explicitement** — soit par strike le plus proche du `forward_price` (déjà APPROVED, `options.forward_price`), soit par |delta| le plus proche de 0,50 ; la convention choisie est un paramètre publié, jamais implicite. Aucune interpolation par défaut : si le strike ATM exact n'existe pas, la méthode d'interpolation est déclarée et versionnée, ou le point est `ABSENT`.

*Portes.* `single_trading_class`, `iv_resolved_both_sides` (call et put), `no_interpolation_without_declared_method`, `arbitrage_check` (structure non monotone → anomalie de donnée, pas opportunité — `OPTIONS_FLOW_INTELLIGENCE.md`).

*Contrat/endpoint/tests.* Bloc `aggregates.term_structure` ; même endpoint ; propriétés : une échéance sans IV résolue est `ABSENT` nommée et non interpolée ; l'ordre des échéances est chronologique strict ; deux `trading_class` ne fusionnent jamais.

---

**7. Skew agrégé — FAISABLE**

Même diagnostic que 6 : `iv-smile` est `served` avec le contrat `« expirations[].contracts[].iv (géométrie seule) »` — un nuage de points, **aucune mesure**.

*Calcul à écrire.* `options.iv_skew` dans `calculations/options.py`. Deux sorties possibles, chacune nommée : **risk reversal 25-delta** (IV du put à |delta|≈0,25 − IV du call à delta≈0,25) et **pente locale** (dIV/dK autour de l'ATM, normalisée). Le delta utilisé est **le delta Vertex déjà servi** (`greeks.delta`), pas un delta reconstruit dans le navigateur.

*Portes.* `both_wings_resolved` (un côté sans IV → `INSUFFICIENT_DATA`, jamais une pente sur une aile), `same_expiration_and_trading_class`, `delta_bucket_tolerance_declared`.

*Tests.* Skew nul sur une surface plate synthétique ; signe correct sur un smile construit à la main ; refus si une aile manque ; invariance à l'ordre des contrats.

---

### Intelligence de marché

---

**8. Rotation sectorielle — BLOQUÉ-PAR-SOURCE**

*Preuve exacte.* `packages/python/vertex_core/src/vertex_core/contracts/market_quote.py:62-63` :

```python
UNCLASSIFIED_SECTOR_CODE = "NON_CLASSE"
UNCLASSIFIED_SECTOR_LABEL = "Secteur non déclaré"
```

et `apps/worker/src/vertex_worker/profiles.py:84-85` : `REAL_SECTOR_CODE = UNCLASSIFIED_SECTOR_CODE`. Le commentaire du contrat est explicite : « Ce n'est pas un secteur, c'est l'aveu qu'il n'y en a pas. » Les secteurs n'existent que pour l'univers synthétique (`SYNTHETIC_SECTOR_TICKERS`, `SYNTHETIC_SECTOR_LABELS_FR`).

*Source officielle manquante.* Une classification sectorielle avec provenance. Deux candidats :
- **GICS ou ICB** — licenciés. Droit exigé : licence commerciale d'affichage et de dérivation ; absents de `OFFICIAL_SOURCE_MAP.md`, donc soumis à la porte de déploiement complète de `SOURCE_RIGHTS_AND_RETENTION.md`.
- **Code SIC de la SEC** — gratuit, classe `R1_PUBLIC_FACT`, et le client existe déjà (`SecEdgarClient.submissions`, `clients.py:136`). Limite à dire à l'écran : SIC est grossier, américain seulement, et ne couvre que les émetteurs porteurs d'un CIK (`InstrumentId.cik`, `identity.py:52`).

*Ce qui n'est PAS bloqué.* Le calcul lui-même : `market.relative_strength` est APPROVED (`calculations/market.py:465`, `RS = prod(1+r_actif)/prod(1+r_indice)` sur un horizon aligné). Le jour où une classification arrive avec sa provenance, la rotation est une agrégation de `relative_strength` par groupe — pas un nouveau moteur.

---

**9. Régime de marché — FAISABLE en version dégradée déclarée**

*Preuve du manque.* `apps/web/src/pages/todayView.ts`, module `regime` : `reason: 'NO_SOURCE'`.

*Sortie canonique déjà spécifiée.* `REGIME_AND_SECTOR_MODEL.md` : `RISK_ON | RISK_OFF | TRANSITION | STRESS | RANGE | UNKNOWN`, « état descriptif versionné, jamais une prévision certaine », `UNKNOWN` bloque toute règle dépendante. C'est une **classification descriptive** au sens de la loi 5 — légale si elle le dit.

Verdict des 7 couches du document :

| Couche | Verdict | Preuve |
|---|---|---|
| 1. tendance + volatilité des indices | **FAISABLE** | barres quotidiennes servies ; `market.realized_volatility`, `market.sma`, `market.ema` APPROVED |
| 2. breadth, participation | **FAISABLE, déjà calculé** | `market.breadth` APPROVED, déjà publié dans `markets_overview` avec `coverage_threshold` explicite (`worker/markets.py:19-24`) |
| 3. courbe des taux, crédit, dollar, indice de vol | **BLOQUÉ** | voir item 11 ; `marketsModules.ts` : `fx` = `NO_SOURCE`, `volatility` = `NO_SOURCE` |
| 4. rotation sectorielle | **BLOQUÉ-PAR-SOURCE** | item 8 |
| 5. corrélations et ruptures | **FAISABLE, déjà calculé** | `risk.correlation` APPROVED, publié `risk_matrix/global` |
| 6. calendrier macro | **BLOQUÉ-PAR-SOURCE** | `worker/calendar.py:178` : synthétique uniquement |
| 7. changement de régime hors ligne / dérive en ligne | **INTERDIT en runtime aujourd'hui** | `OFFICIAL_SOURCE_MAP.md` : « River n'est pas une autorité de décision. ruptures, arch et MAPIE restent hors runtime de production jusqu'à validation et promotion formelle. » |

*Calcul à écrire.* `market.regime_classification` dans `calculations/market.py`. Entrées : sorties des couches 1, 2, 5 uniquement, chacune avec son statut. **Règles déterministes robustes en baseline**, versionnées (`REGIME_RULE_VERSION`), exactement comme `IMPORTANCE_RULE_VERSION` du calendrier (`worker/calendar.py:181-183`). Porte : couverture insuffisante → `UNKNOWN`, jamais un régime par défaut. Chaque couche absente est **nommée à l'écran**, pas silencieuse.

*Contrat/endpoint.* Snapshot `regime/global`, relayé par `GET /api/v1/today/attention` (`routes.py:564`) ou une route dédiée.

*Tests.* Table de vérité exhaustive de la règle ; une couche absente ne peut jamais faire basculer vers un régime affirmatif ; changement de version de règle = changement de sortie déclaré ; aucun mot de prédiction dans les libellés (test lexical, comme la porte anti-tiret ambigu déjà en place).

---

**10. Indice de conditions composite — FAISABLE SOUS CONDITION STRICTE, sinon INTERDIT**

*Loi violée si mal fait.* `DECISION_ENGINE.md`, § Classement : « Aucun score global ne masque une porte, une incertitude ou un manque de données. » Et `SIGNAL_FUSION.md` § 2-3 : le moteur « ne compare pas directement un z-score, une probabilité, une IV et un score Isolation Forest » ; les preuves dépendantes partagent un `correlation_group` et subissent **un plafond de contribution**. `MODEL_RISK_AND_VALIDATION.md` classe un méta-modèle de fusion en **M3**, dont l'« effet maximal autorisé » est « challenger de fusion, jamais verdict », et qui exige revue indépendante + autorisation humaine explicite.

*Verdict.* Un indice composite est **FAISABLE** si et seulement si : chaque composante est publiée séparément avec sa fenêtre et sa couverture ; la transformation vers l'échelle commune est versionnée, bornée et testée ; les composantes issues d'un même choc partagent un `correlation_group` plafonné ; et l'indice **n'entre jamais** dans `AdviceInputs` ni ne modifie `AdviceStatus`. Un nombre unique présenté comme « les conditions sont à 72/100 » et pilotant une décision est **INTERDIT** (loi 6 : une page, une question, un visuel dominant ; et le score masquerait une porte).

---

**11. Courbe des taux — FAISABLE (source officielle gratuite, cliente déjà livrée)**

*Preuve du diagnostic front, qui est juste.* `apps/web/src/pages/markets/marketsModules.ts`, module `rates-curve` : `reason: 'SERVER_CONTRACT_MISSING'` — pas `NO_SOURCE`. Correct.

*Entrée qui existe.* `apps/edge-official/src/vertex_edge_official/clients.py:169-231` — `FredClient.observations(series_id, ...)` retourne un `DataEnvelope`, `rights="R1_PUBLIC_FACT:FRED_SERIES_TERMS_REVIEW_REQUIRED"` (ligne 226). Sonde exécutable : `tools/probe_official_sources.py --live --source fred --series-id GDP`.

*Ce qui manque, dans l'ordre :*
1. Une **allowlist de séries** (DGS1MO … DGS30). `OFFICIAL_SOURCE_ADAPTERS.md` : « FRED/ALFRED : client livré, clé locale obligatoire » et « La prochaine famille autorisée est FRED/ALFRED point-in-time, dans un lot séparé ».
2. Un module de **normalisation** — `apps/edge-official/` contient `sec.py`, `transport.py`, `config.py`, `clients.py`, `__init__.py`. **Aucun `fred.py` de normalisation.**
3. Un **préfixe de schéma d'ingestion** (`fred.series/1`) admis par un handler.
4. Un **handler worker** publiant `rates_curve/global`.
5. Un **modèle de réponse + route** API.

*Droit exigé.* Clé `VERTEX_FRED_API_KEY` (compte FRED gratuit) + la **revue humaine des conditions de série** que le libellé de droit exige littéralement (`FRED_SERIES_TERMS_REVIEW_REQUIRED`), conformément à la porte de déploiement de `SOURCE_RIGHTS_AND_RETENTION.md`. Rétention imposée par la même table : réponse API ≤ 24 h, métadonnées durables **seulement pour série autorisée**, **vintage obligatoire** (ALFRED `realtime_period`).

*Calcul à écrire.* Une courbe est un **relais**, pas un calcul — aucune entrée de registre pour la courbe elle-même. Seul le **spread** en est un : `market.yield_spread` (différence de deux points, unité **points de base**, portes `same_maturity_convention` et `same_vintage`). Une différence de deux séries de vintages différents est un artefact, pas un spread.

*Tests.* Une révision ALFRED ne réécrit jamais un point passé ; un point absent n'est pas interpolé ; l'unité (pourcent annualisé vs points de base) ne se mélange jamais ; deux séries de conventions différentes refusent de se soustraire.

---

### Décision, lignée, résultat

---

**12. Décomposition du score de décision — FAISABLE, aucun calcul à écrire**

*Il n'y a pas de score.* `DECISION_ENGINE.md` l'interdit. Ce qui est décomposable, ce sont les **dix portes**.

*La preuve est déjà produite.* `decision/gates.py` définit `GATE_CATALOG` / `GATE_ORDER` avec les dix portes : `instrument_resolved`, `entitlements_sufficient`, `snapshot_fresh_and_coherent`, `session_and_event_known`, `minimum_liquidity`, `calculations_valid`, `manual_portfolio_risk_available`, `probability_calibrated_if_used`, `critical_contradictions_resolved`, `user_constraints_versioned`. Chaque `GateResult` (`contracts/decision.py:37-53`) porte `gate_id`, `version`, `status`, `reason_code`, `message`, `evidence_ids`, **`observed_values`**, **`thresholds`** — et ces deux derniers **sont réellement remplis** (`gates.py:106,115,126,137,174,183,192,205,247,256,265,274,283,320,329,337,387,390,400,409,453,465,477,485,529,540,556,564,604,617,626`).

*La preuve est déjà servie.* `worker/analysis.py:2164` : `"advice": advice.model_dump(mode="json")` → `AnalysisResponse.advice` (`schemas.py:399`) → typée dans `apps/web/src/api/schema.d.ts:1640-1665` (`observed_values`, `thresholds`).

*Ce qui manque : l'écran, uniquement.* `grep -rn "observed_values|thresholds" apps/web/src` ne renvoie que `ArcGauge.tsx` (une prop générique de widget) et `BreadthPanel.tsx`. **Aucune page ne lit `advice.gates[].observed_values`.**

*Travail.* Un registre de portes en table financière : dix lignes `porte | version | statut | reason_code | observé | seuil`. Aucun calcul, aucun contrat serveur.

*Tests qui le figent.* Un test d'interface asserte que les dix `gate_id` de `GATE_ORDER` sont rendus **dans l'ordre canonique** ; un test de dérive asserte que la liste rendue et `GATE_ORDER` restent identiques (une onzième porte ajoutée casse le test au lieu d'être invisible) ; un test asserte qu'une porte `BLOCK` n'est jamais rendue avec un style neutre.

---

**13. Lignée de calcul jusqu'à l'écran — FAISABLE, aucun calcul à écrire**

*Le contrat existe.* `contracts/calculation.py` — `CalculationRecord` porte `calculation_id`, `calculation_type`, `engine_version`, `code_sha`, `input_hash`, `source_event_ids`, `assumptions`, `method`, `parameters`, `random_seed`, `started_at`, `completed_at`, `status`, `warnings`, `result_hash`, `result`. `make_calculation_record` dérive les hachages des vraies données.

*Il est produit partout.* `worker/markets.py`, `analysis.py`, `options.py`, `portfolio.py`, `performance.py` appellent tous `make_calculation_record` et publient un bloc `calculation` (ex. `options.py:496-521,540-558`).

*Ce qui manque.* (a) `_calculation_meta(...)` est **redéfini dans chaque module worker** — il n'y a pas de projection partagée, donc rien ne garantit que les cinq publient le même jeu de clés ; (b) aucune surface d'interface ne montre la chaîne complète *valeur → `calculation_id` → `method` → `engine_version` → `input_hash` → `source_event_ids` → observation*.

*Travail.* Une seule fonction `calculation_meta` dans `vertex_core.contracts` (ou `vertex_worker`), consommée par les cinq ; un panneau d'inspecteur qui déroule la chaîne.

*Garde déjà en place à réutiliser.* `tools/check_calculation_registry.py` + `packages/python/vertex_core/tests/test_calculation_registry.py` imposent déjà qu'un `CalculationRecord` de production ne porte qu'un `id` **APPROVED**. Le test à ajouter est symétrique : tout bloc `calculation` publié porte exactement le même jeu de clés, et chaque `calculation_id` publié existe au registre.

---

**14. Issue des thèses — FAISABLE, bloqué par un VOCABULAIRE absent, pas par une source**

*Preuve exacte.* `packages/python/vertex_persistence/src/vertex_persistence/enums.py`, `ThesisRevisionAction` : `CREATED`, `REVIEWED`, `SNOOZED`, `NOTE_UPDATED`, `ARCHIVED`, `REACTIVATED`. **Aucun membre ne dit l'issue.** `ARCHIVED` ne distingue pas une thèse confirmée d'une thèse invalidée.

*L'ingrédient est pourtant là.* `models.py:319` — `Thesis.invalidation: Mapped[str]`, le falsificateur **obligatoire**, plus `horizon` (ligne 320). Le critère de réfutation est écrit ; sa résolution n'est jamais enregistrée. `project_thesis_state` (`repository/theses.py:435-511`) ne projette que `ACTIVE`/`SNOOZED`/`ARCHIVED`.

*Travail.* Ajouter des membres d'issue (`CLOSED_CONFIRMED`, `CLOSED_INVALIDATED`, `CLOSED_EXPIRED`, `CLOSED_ABANDONED`) à `ThesisRevisionAction` ; migration Alembic à la suite de `0006_theses.py` ; étendre `record_thesis_revision` et `project_thesis_state` ; publier l'issue dans `review_queue/global` (`worker/follow_up.py`) et la servir par `GET /api/v1/follow-up/queue` (`routes.py:1100`).

*Loi à respecter.* Une issue est une **déclaration de l'utilisateur**, exactement comme le portefeuille (loi 1). Vertex ne doit jamais déduire qu'une thèse est invalidée depuis un prix. Test-témoin : aucun chemin de code ne fixe une issue depuis une observation de marché — le seul écrivain est `POST /api/v1/theses/{id}/revisions`.

---

**15. Taux de réussite — FAISABLE APRÈS 14**

*Nature.* `PROBABILITY_CALIBRATION.md` sépare trois familles : implicite risque-neutre, **fréquence historique empirique d'un événement défini**, prédictive physique calibrée. Un taux de réussite est la famille 2. Il est donc **légal sans calibration**, à condition de ne jamais être présenté comme la chance de réussite de la prochaine thèse (loi 5).

*Calcul à écrire.* `performance.thesis_hit_rate` dans `calculations/performance.py`. Entrées : issues closes typées. Sorties : ratio, `n`, intervalle de Wilson. Portes : `minimum_sample` (sous le seuil → `INSUFFICIENT_DATA`, jamais un pourcentage sur trois thèses) ; `closed_population_only` (une thèse `ACTIVE` n'est pas un échec) ; `no_survivorship` (une thèse abandonnée compte, elle n'est pas retirée).

*Contrat/endpoint.* Bloc `outcomes` du snapshot `review_queue/global`, `GET /api/v1/follow-up/queue`.

*Tests.* Le ratio est dans [0,1] ; `n` est toujours affiché avec lui ; retirer une issue perdante change le résultat (preuve anti-survivorship) ; l'intervalle contient le ratio ; sous le seuil, **aucun nombre n'est exposé**.

---

**16. Espérance — FAISABLE, conditionnée à UNE déclaration utilisateur de plus**

*Le blocage n'est pas une source, c'est un champ.* Une espérance exige un **montant d'issue**. `Thesis` (`models.py:310-324`) porte `portfolio_id`, `instrument`, `title`, `hypotheses`, `invalidation`, `horizon`, `review_due_at`, `created_at` — **ni entrée, ni stop, ni cible, ni montant**. Et joindre silencieusement une thèse au registre de transactions mélangerait deux populations déclarées distinctes, ce qu'interdit la discipline de population appliquée partout ailleurs (`worker/performance.py` : population `SYNTHETIC_MARKS_REAL_LEDGER`, « NEVER aggregated with any other »).

*Le moteur existe déjà et n'est appelé par personne.* `decision.risk_reward` est **APPROVED** (registre ligne 1372) avec `runtime_usage: not_called_by_production_code_yet`. Entrées : `entry`, `stop`, `target`, `multiplier`, `costs`, `currency_match`, `horizon_defined`, tout en `Decimal` exact. Sortie : `RiskRewardResult`, statut `OK` ou `INVALID` — **et sur `INVALID`, aucun chiffre n'est exposé**.

*Travail.* Ajouter à la thèse un triplet déclaré (entrée/stop/cible + coûts) validé par `decision.risk_reward`, puis `performance.thesis_expectancy` = moyenne des multiples de R des issues closes. Unité : **multiples de R**, pas de la monnaie — ce qui évite complètement la jonction interdite avec le registre.

*Tests.* Espérance = Σ(pᵢ·Rᵢ) sur la population close ; une thèse sans triplet est **exclue et comptée**, jamais comptée à 0 ; le signe est correct ; l'unité R n'est jamais rendue avec un symbole monétaire.

---

**17. Comparaison à un indice de référence — verdict scindé**

*Sur Analyse : DÉJÀ FAIT.* `worker/analysis.py:26-56` — `market.relative_strength` contre l'indice **DÉCLARÉ**, et une comparaison base 100 servie par `market.rebased_series` sur les **seules séances communes, intersectées côté serveur**, avec refus nommés `BENCHMARK_NOT_OBSERVED`, `INSUFFICIENT_SAMPLE`, divergence de devise ou de base d'ajustement. Le commentaire dit pourquoi : « un rebasage dans le navigateur serait un calcul financier en TypeScript, interdit ».

*Sur Performance : ABSENT.* `worker/performance.py` publie la série de valorisations, TWR, XIRR, drawdown, la carte mensuelle, brut et net — **aucune série d'indice, aucun excédent**.

*Erreur de motif à corriger.* `apps/web/src/pages/risk/riskModules.ts`, module `benchmark-relative` : `reason: 'NO_SOURCE'`. **C'est faux.** Les cotations quotidiennes de l'indice sont déjà persistées et déjà consommées par `markets.py` et `analysis.py`. Le motif exact est `SERVER_CONTRACT_MISSING`.

*Calcul à écrire.* Réutiliser `market.rebased_series` (APPROVED) sur la courbe brute du portefeuille et sur celle de l'indice ; ajouter `performance.excess_return` (TWR portefeuille − TWR indice sur les **mêmes** journées valorisées).

*Portes.* `same_valued_days` — intersection stricte, **et publication des journées perdues**, exactement comme `worker/risk.py` publie `trading_days_lost_to_alignment` ; `same_currency` ; `gross_vs_net_declared` — comparer un net à un indice brut est une comparaison fausse, la convention doit être publiée.

*Endpoint.* `GET /api/v1/performance/{portfolio_id}` (`routes.py:1321`).

*Tests.* Excédent nul quand portefeuille = indice ; une journée manquante d'un côté est exclue des deux et comptée ; brut vs net ne se comparent jamais implicitement ; le rebasage est identique à celui d'Analyse (même fonction, pas une seconde implémentation).

---

**18. Attribution de performance — trois verdicts distincts**

- **Contribution par instrument — FAISABLE.** `portfolio.realized_pnl` et `portfolio.unrealized_pnl` sont APPROVED et déjà exécutés lot par lot (`worker/portfolio.py`), avec `LotRealizedPnl` / `LotUnrealizedPnl` par lot (`calculations/portfolio.py:173,207`). Le job performance possède déjà les poids quotidiens par journée valorisée. Ce qui manque est l'**identité de réconciliation** : la somme des contributions doit égaler le TWR de la période, ce qui ne tient pas naïvement en présence de flux externes — la méthode d'attribution doit donc être **déclarée et versionnée**, pas déduite.
- **Attribution sectorielle — BLOQUÉE-PAR-SOURCE.** Même preuve que l'item 8.
- **Attribution par stratégie — BLOQUÉE-PAR-CONTRAT.** `position_lots` (`models.py:219-231`) porte `instrument`, `quantity`, `unit_cost`, `currency`, `opened_at`, `source`, `note`. **Aucun champ de stratégie.** Ce n'est pas un manque de source : c'est un champ à déclarer.
- **Attribution de Brinson — BLOQUÉE deux fois.** Elle exige la composition sectorielle de l'indice **et** la classification des titres.

*Tests pour la contribution par instrument.* Σ contributions = TWR de la période à la tolérance déclarée ; un lot non valorisable est exclu **et compté**, jamais valorisé à zéro ; la contribution d'un lot fermé en cours de période est portée par les journées où il était ouvert.

---

**19. Concentration et corrélation — DÉJÀ FAIT, avec un vrai trou restant**

*Concentration.* `portfolio.concentration` APPROVED ; `worker/portfolio.py:789-818` l'appelle et publie `total_value`, `weights`, `herfindahl_index` avec lignée ; `ConcentrationResult` (`calculations/portfolio.py:242-247`) ; porte `positive_denominator`, invariant `sum(weights) == 1` à `WEIGHT_SUM_TOLERANCE`. Servi par `GET /api/v1/portfolio` ; `riskModules.ts` module `concentration` = `served`.

*Corrélation.* `risk.covariance` + `risk.correlation` APPROVED ; `worker/risk.py` publie `risk_matrix/global` avec `matrix`, **`matrix_bands`** (la bande est décidée côté serveur — « classer un coefficient est un jugement de domaine, pas une mise en page »), `extremes`, `synchronicity_warning` (avec la mesure du 2026-09-01 : SPX/N225 à +0,168 par décalage de fuseau, pas par décorrélation). Servi par `GET /api/v1/risk/matrix` (`routes.py:1289`).

*Le trou restant, FAISABLE sans nouveau calcul.* Le périmètre de la matrice est `RiskConfig.perimeter` — **déclaré**, et ce ne sont **pas** les positions du portefeuille. « La corrélation de mon portefeuille » n'est donc pas servie. Il suffit d'alimenter `risk.covariance` avec les tickers des lots ouverts déclarés. Manquent aussi : la concentration **par secteur** (bloquée, item 8) et **par émetteur** (`InstrumentId.issuer_id` existe, `identity.py:53`, et n'est jamais rempli).

---

**20. Jours perdus à l'alignement — DÉJÀ FAIT sur Risques, à uniformiser ailleurs**

*Preuve.* `worker/risk.py:346` : `perdues = {t: seances_par_instrument[t] - len(communs) for t in retenus}`, publié en `coverage.trading_days_lost_to_alignment` avec `trading_days_per_instrument`, `common_trading_days`, `window_start`, `window_end`, `minimum_common_days` (seuil de 30, déclaré et publié : « Ce n'est pas parce qu'un nombre SORT qu'il veut dire quelque chose »). Servi et affiché : `riskModules.ts:204` (`kind: 'served'`), lu par `riskView.ts:168`.

*Ce qui reste.* La **même perte** existe ailleurs sous d'autres noms : journées exclues de `worker/performance.py` (marques incomplètes), intersection de la série base 100 dans `worker/analysis.py`. Les publier sous un nom commun est FAISABLE, sans calcul.

---

**21. Latence des routes et des jobs — FAISABLE, rien n'est instrumenté**

*Preuve du vide.* `grep -rn "latency|duration_ms|elapsed|perf_counter|monotonic"` sur `apps/api/src` et `apps/worker/src` ne renvoie que `auth/challenges.py` (un TTL de défi) et `events.py:129,151` (un ping SSE). **Aucune mesure de route, aucune mesure de job.** `WorkerStats` (`worker/runner.py:178-186`) compte `batches`, `claimed`, `acked`, `failed`, `dead`, `lease_lost` — des comptes, jamais des durées.

*Le dépôt l'avoue déjà.* `manifests/performance-budgets.yaml:596-609` — `api.page_snapshot.hot_api_snapshot_server.latency_ms.p95`, `status: NOT_YET_MEASURED`, raison : « Aucune mesure de latence API n'a jamais été exécutée », `expires_at: "2026-12-31"`.

*Ce n'est PAS un calcul financier.* Il n'entre pas dans `vertex_core` et **ne va pas au registre des calculs**. C'est un middleware ASGI + un chronomètre de handler + un relais `/system/…`.

*Contraintes imposées par le manifeste lui-même.* `measurement.minimum_samples` : p95 = 1 000, p99 = 10 000 ; `clocks.within_process: monotonic` ; `warmup_excluded: true` ; `max_cross_process_skew_ms: 2000` avec invalidation au-delà. Et `tools/check_performance_budgets.py` échoue sur `insufficient_samples` — « un p99 sur 12 échantillons est une phrase, pas une statistique ». Publier un p95 sur 12 mesures **fait échouer la porte par construction**, ce qui est le comportement voulu.

---

**22. Backtest — BLOQUÉ-PAR-SOURCE ; INTERDIT s'il est présenté comme un résultat**

*Preuve du vide.* `grep -rn "backtest|Backtest"` sur `apps`, `packages` et `research` renvoie **zéro occurrence**. Rien n'existe.

*Ce que le dépôt exige déjà.* `CALCULATION_CATALOG.md` § Backtests : « Univers, sociétés radiées, changements de symbole, splits, dividendes, calendriers, quotes tradables, bid/ask options, ajustements OCC, frais, spread, slippage, latence, fills et capacité doivent être point-in-time. Sans chaînes options historiques licenciées, Vertex écrit "simulation théorique". »

*Faits bloquants, un par un :*
1. **Aucun univers point-in-time** — pas de table de vintage, pas d'historique de délisting ni de changement de symbole.
2. **Les barres IBKR ne sont pas ajustées.** `edge-ibkr/normalize.py:69` : `IBKR_TRADES_ADJUSTMENT_BASIS = "ibkr-trades-unadjusted"`, avec le commentaire « Une barre `TRADES` d'IBKR n'est PAS ajustée des dividendes ni des splits. Écrire `adjusted` serait faux ». Un backtest pluriannuel sur ces barres serait **simplement faux**.
3. **Aucune chaîne d'options historique licenciée** — ORATS « désactivé en attente du plan et des droits » (`SOURCE_CAPABILITY_MATRIX.md`).
4. **La machinerie walk-forward existe mais est clôturée en recherche.** `research/pipelines/walk_forward.py` (walk-forward purgé, embargo distinct et facultatif) et `research/pipelines/calibration.py` (Brier, log loss, diagramme de fiabilité, bootstrap en blocs, **règle d'abstention**) existent — et `research/tests/test_boundary.py` interdit statiquement tout import de `vertex_api`/`vertex_worker`/`vertex_persistence` et tout lancement de `psql`/`alembic`/`uvicorn` depuis `research/`. `research/README.md` le dit : « ce dossier existe pour répondre à une question, pas pour alimenter le runtime ».

*Verdict.* Un backtest réel est **BLOQUÉ-PAR-SOURCE**. Sources manquantes nommées : (a) des barres **ajustées** avec vintage — la même famille FRED/ALFRED donne le modèle du vintage mais pas les prix ; (b) des chaînes d'options historiques licenciées (ORATS ou équivalent), droit exigé : stockage + dérivation + affichage en classe `R2_LICENSED_METADATA` ; (c) un historique de composition d'univers et de corporate actions. Une simulation synthétique dans `research/` est autorisée ; l'afficher comme une performance devient **INTERDIT** (loi 4 — « simulé » est l'un des huit états distincts et doit le dire ; `MODEL_RISK_AND_VALIDATION.md` — « L'absence de preuve vaut abstention »).

---

## 4. Récapitulatif

| # | Intelligence | Verdict | Bloqueur exact |
|---|---|---|---|
| 1 | Ratio put/call | FAISABLE | aucun (agrégat à écrire) — REAL bloqué par constat B |
| 2 | Max pain | FAISABLE | idem |
| 3 | IV rank / percentile | BLOQUÉ-PAR-SOURCE | série IV historique licenciée (ORATS) ; local `WARMING_UP` possible |
| 4 | Activité inhabituelle | 4 détecteurs FAISABLES, 5 BLOQUÉS | module `vertex_core.options_anomaly` inexistant + historique + WSH |
| 5 | Agrégation des Greeks | FAISABLE mono-devise | `portfolio.fx_conversion` = RESEARCH_ONLY |
| 6 | Structure par terme agrégée | FAISABLE | `vol-structure` est un nuage de points, pas une mesure |
| 7 | Skew agrégé | FAISABLE | `iv-smile` idem |
| 8 | Rotation sectorielle | BLOQUÉ-PAR-SOURCE | `NON_CLASSE` : aucune classification réelle |
| 9 | Régime de marché | FAISABLE dégradé (couches 1,2,5) | couches 3,4,6 sans source ; couche 7 hors runtime |
| 10 | Indice composite | FAISABLE sous condition, sinon INTERDIT | `DECISION_ENGINE.md` « aucun score global » ; M3 |
| 11 | Courbe des taux | FAISABLE | pipeline FRED absent + revue humaine des conditions de série |
| 12 | Décomposition de la décision | FAISABLE, servie à 90 % | l'écran seul |
| 13 | Lignée jusqu'à l'écran | FAISABLE, servie | `_calculation_meta` non unifié + aucun panneau |
| 14 | Issue des thèses | FAISABLE | `ThesisRevisionAction` sans membre d'issue |
| 15 | Taux de réussite | FAISABLE après 14 | dépend de 14 |
| 16 | Espérance | FAISABLE après déclaration | triplet R:R absent de `Thesis` |
| 17 | Comparaison à un indice | FAIT sur Analyse, ABSENT sur Performance | motif front `NO_SOURCE` erroné |
| 18 | Attribution | instrument FAISABLE ; secteur/stratégie/Brinson BLOQUÉS | classification + champ stratégie |
| 19 | Concentration et corrélation | DÉJÀ FAIT | périmètre ≠ portefeuille ; `issuer_id` jamais rempli |
| 20 | Jours perdus à l'alignement | DÉJÀ FAIT sur Risques | à uniformiser sur Performance et Analyse |
| 21 | Latence routes et jobs | FAISABLE, zéro instrumentation | `NOT_YET_MEASURED` assumé au manifeste |
| 22 | Backtest | BLOQUÉ-PAR-SOURCE | barres non ajustées + aucune chaîne historique + aucun univers PIT |

**Le levier le plus court** : items 12, 13, 19, 20 ne demandent **aucun calcul nouveau** — la preuve est déjà produite, publiée et typée jusqu'à `schema.d.ts`, et personne ne la regarde. Items 1, 2, 5a, 6, 7 ne demandent **qu'un bloc `aggregates`** sur un contrat déjà servi. Le constat A (ticks 100/101/104/105/106 jamais demandés) est un changement d'**une ligne d'appel** dans `tools/run_edge_ibkr.py`, et il débloque à lui seul le ratio put/call au niveau du sous-jacent et la divergence IV/HV.