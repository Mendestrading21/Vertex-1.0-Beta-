# R2 — requalification post-fusion des squashes #14 et #18

## Objectif

Dire, vague par vague, ce que `main` contient réellement du travail Claude
fusionné par les squashes #14 (`505d465`) et #18 (`beb2498`), avec quelle
preuve, et ce qu'il reste à reprendre — sans rien fusionner, sans toucher au
chantier graphique, sans ajouter de capacité IBKR.

## Périmètre et méthode

- Base auditée : `main` = `ecc50c1027314dd3ed594410430d41a3b1189ebf`
  (squash humain de #20, après #17 `c3f2400`). Socle de comparaison :
  `a5b7d205388e58f4e2716deeba5ecbea0ca9af21` (dernier `main` avant #14).
- Vagues : celles de `CLAUDE_RECOVERY_PLAN.md`, relues sur `ecc50c1`.
- Exécution le 2026-09-02 : huit rapports de requalification indépendants
  (R2-A, B, C, D, E, F, G, J), chacun dans un worktree jetable à `ecc50c1`,
  puis cinq contre-vérifications **adverses** indépendantes (R2-A, B, C, F, J)
  chargées de réfuter les écarts signalés. Consolidation par un treizième
  rapport. Aucun fichier suivi modifié, aucune collecte IBKR, aucune connexion
  TWS dans ces travaux.
- Contre-lecture propre du rédacteur de ce document, par `grep` sur `ecc50c1`,
  des faits marqués « (relu) » ci-dessous.
- Réserve de méthode (fait confirmé par trois rapports) : les `.pth` éditables
  du venv résolvent `vertex_*` vers le dépôt principal, pas vers le worktree ;
  les résultats ont été obtenus avec `PYTHONPATH` forcé sur le worktree sauf
  mention contraire. Sans conséquence : `git diff --stat ecc50c1 f9af140 --
  apps/api/src apps/worker/src packages/python` est vide.

**Ce que ce document n'est pas.** Il n'exécute aucune correction. Il ne
transforme pas un « signalé par un seul rapport » en fait établi : les vagues
D, E, G n'ont **pas** été contre-vérifiées, et leurs écarts restent indéterminés
(§4). Les chiffres de tests sont ceux relevés par les rapports ; ils ne sont
pas des chiffres de CI.

## 1. Décisions par vague

| Vague | Décision R0 | Décision R2 | Présent dans `main` | Preuves relevées (rapport, puis contre-vérification) | Écarts confirmés |
|---|---|---|---|---|---|
| R2-A vérité des relais | ADAPT | **ADAPT** | partiel — 6 intentions sur 8 (déclenchement Marchés, `$` dans `_CODE_RE`, semis fournisseur, `MarksView.population` portefeuille, libellés page Marchés, `data_state` partial) ; absentes : nature des marks dans `performance.py`, conclusion `markets.py:362` | 7 fichiers → 490 passed ; suite unitaire → 4057 passed, 4 skipped ; intégration (3 fichiers) → 6 passed ; vitest 4 fichiers → 43 ; tsc 0 ; ruff/mypy 0 ; falsification `_CODE_RE` → 17 rouges attendus ; reproducteurs → 2 rouges. Contre-vérif : 501 passed ; 2 reproducteurs indépendants rouges | A1, A2, A3, A4 (A5 réfuté) |
| R2-B Analyse | ADAPT | **ADAPT** | partiel — 3 calculs branchés, relayés, testés ; affichage limité à vol/ATR, force relative jamais affichée ni au contrat (lacune d'origine, pas perte de squash) | `test_analysis_content` → 77 ; `test_market` → 134 ; api 4 fichiers → 447 ; profils → 39 ; intégration → 2 ; vitest → 19 ; tsc 0 ; `tools/run_checks.sh` → TOUT VERT rc=0. Contre-vérif : reproducteur B2 → 1 failed ; mutation `indicators` → 1 failed (garde existante) | B1, B2, B3, B4(b), B6 (B5 rétrogradé, B4(a) réfuté) |
| R2-C Presse (+ ajout R1 `732f7e5`) | ADAPT | **ADAPT** | oui — dérivation, identité, préfixe, `time_unzoned`, collecteur, rail de preuves ; mais **inopérant en production** (hachage d'un datetime naïf) | @`ecc50c1` : `test_news` → 13 ; edge-ibkr → 367 ; reproducteur `test_news_hashing_chain.py` → **2 failed, 1 passed** ; worker → 98. @`59a5e3f` : 17 / 371 passed ; ruff/mypy 0 ; `run_edge_news.py` sans env → rc=2 (5 scénarios). Contre-vérif : idem + mutation `_instrument_ref_de` → 353 passed (mutant survivant) | C1, C2, C3, C4, C5, C6 (+ C7, C8 faits hors intention) |
| R2-D Graphiques (Python) | ADAPT | **KEEP** | oui — registre `:89-134`, `rebase_series` `market.py:390-448`, `TestRebaseSeries` ; aucune page, aucun contrat | `TestRebaseSeries` → 15 ; `test_market` → 134 ; calculs → 516 ; suite hors edge-ibkr → 4057 passed, 4 skipped ; registre ok ; ruff/mypy 0 | **non contre-vérifié** — D1, D2, D3 indéterminés (§4) |
| R2-E Risques cœur | ADAPT | **KEEP** | oui — `risk.correlation` au registre, worker `build_risk_matrix_content`, périmètre déclaré, route `/risk/matrix`, `value` signé, contrat worker→API testé | 7 fichiers → 117 ; intégration `test_worker_risk_chain.py` → 4 ; ruff 0, mypy strict 0 ; registre/frontière ok | **non contre-vérifié** — E1, E2, E3, E4 indéterminés (§4) |
| R2-F Risques page (UI) | ADAPT | **ADAPT** | oui — route `/risks`, page, matrice, Ledger 09 dans les deux sources, e2e a11y déclaré ; seule dérive : `data-rank="dominant"` (style) | vitest 3 fichiers → 57 ; suite → 486 ; tsc 0 ; biome 0 ; pytest risk → 26. Contre-vérif : 8 reproducteurs → **7 rouges** (F1, F2 ×3, F3 ×2, F4), témoin vert | F1, F2, F3, F5 (F4 = décision produit ; F6 = style, hors R2) |
| R2-G shell vérité (UI) | ADAPT | **KEEP** | oui — `LEDGER_CODE_BY_PAGE` ↔ `--vx-page-ledger` (test croisé), `AbsentModule`, horloge servie/`age_seconds`/version ; fichiers identiques à l'origine | vitest 4 fichiers → 45 ; suite → 486 ; tsc 0 ; biome 0 ; `gen:api` → diff vide ; pytest api → 55 ; 3 falsifications → rouges attendus ; playwright `--list` → 36 déclarés, **non exécutés** | **non contre-vérifié** — G1, G2 indéterminés (§4) |
| R2-J surfaces post-fusion #18 | AUDIT / ADAPT | **ADAPT scindée** : CSS V11–V12 = KEEP ; passation `REPRENDRE_ICI.md` → R2-I | oui — `main` == HEAD #18 `b8a0d4d6` pour les 2 fichiers | vitest suite → 486 (1 échec de charge `OptionsPage.test.tsx` non reproduit isolément, 12/12 ×3) ; design → 61 ; biome 0. Contre-vérif : A/B Chromium `505d465` vs `ecc50c1` | J1, J2 (J3 = régression de style, hors R2 ; J4 vérifié sans écart) |
| R2-H accès local (`d357e4c`) | HOLD | **HOLD maintenu** | présent dans `main` via #14 (`VERTEX_AUTH_OPEN_LOCAL`, fermé par défaut) — non instruit par R2 | non exécutés | décision sécurité séparée |
| R2-I documentation (`d8031cb`, `7e21e5b`, + `f9af140`) | REWRITE / DROP | **REWRITE / DROP maintenu** — destinataire des écarts documentaires A4, F5, G1, G2, J1, J2, D3, E1 | information indisponible | non exécutés | §5 |
| R2-C' (ajout R1 `732f7e5`) | ADAPT | **ADAPT exécuté** | non (le défaut C1 est dans `main`) | branche `lot/r2c-presse-hachage-20260902` : reproducteur rouge sur `ecc50c1` puis vert ; voir §3 | C2 à retirer dans le même lot |
| PR #19 démarrage (`e8ff5e6`) | APRÈS #17 | **reprise exécutée** | non | PR #21 (brouillon) depuis `ecc50c1` : 4 fichiers, `NOW.md` écarté ; 12 tests, six portes documentaires, CI 7/7 verte sur `6d05603` | — |

## 2. Écarts confirmés par une contre-vérification indépendante

Chaque écart ci-dessous a été signalé par un rapport **et** confirmé par une
contre-vérification adverse qui a tenté de le réfuter. Les mentions « (relu) »
sont des contre-lectures du rédacteur sur `ecc50c1` le 2026-09-02.

### 2.1 R2-A — vérité des relais

- **A1 — `performance.py` grave `marks = "SYNTHETIC"` sur des cotes IBKR**
  (backend, persisté). `apps/worker/src/vertex_worker/performance.py:136` et
  `:808-811` écrits sans condition (relu : `:811`) ; fichier identique
  socle/`main`. Reproducteur indépendant (profil réel GOOG, 3 cotes
  `source=ibkr`) → `population_components.marks == "SYNTHETIC"` : rouge.
  `70512db` l'avait laissé ouvert explicitement (décision de contrat).
  Impact : deux instantanés persistés de la même base se contredisent (Marchés
  `REAL`, performance « marques SYNTHETIC ») ; tables append-only, non
  rattrapable. Correction minimale : décision propriétaire d'un membre composé
  de `POPULATION_LABELS` (`snapshot_views.py:541-552`, ex.
  `REAL_MARKS_REAL_LEDGER`, cas `EMPTY` à trancher) ; `performance.py` dérive
  `marks` de la nature des cotes retenues (règle `markets.py:140-141`,
  fail-closed `EMPTY`) ; `SyntheticBanner.tsx:45-101` (`POPULATION_NATURES`)
  doit recevoir chaque nouveau membre, sinon « nature non reconnue ». La
  contre-vérification a **réduit** la liste des fixtures à mettre à jour :
  celles citées par le premier rapport n'ont aucune cote IBKR.
- **A2 — `markets.py:362` persiste « synthétiques attendus » sur population
  `REAL`** (backend, persisté). `_french_conclusion` sans paramètre
  `population` (relu : `:362`) ; relayé `snapshot_views.py:1885`, affiché
  `MarketsPage.tsx:186-187`. Reproducteur indépendant → rouge. Pins à ajuster :
  `apps/web/src/test/fixtures.ts:266`, `apps/api/tests/test_markets_overview.py:72`.
- **A3 — nom d'export CSV « marches-synthetiques.csv » en dur**
  (`MarketsTable.tsx:123-127`, relu : `:125`) ; aucun test ne fixe ce nom.
  Correction : nom neutre ou dérivé du recensement, avec test vitest sur le
  nom passé à `saveTextAsFile`.
- **A4 — état documentaire périmé** (→ R2-I). `NOW.md:589-603` listait huit
  étiquettes « Reste cassé » dont six sont corrigées dans `main` (relu :
  `:591`). Provenance corrigée par la contre-vérification : `505d465` (#14),
  pas `d8031cb` ; `REPRENDRE_ICI.md` n'a **pas** été touché par #17.
  Réécrit dans `NOW.md` par la présente PR.
- **Réfuté** : A5 (`_MAPPING_KEY_RE` sans `$`) — exécuté en mémoire sur le
  corpus `demo_seed` (60 enveloppes, 9 identifiants `SYNWIRE$…`) : 0 clé de
  mapping contenant `$`, `checked_relayed_content` accepte. Pas un défaut.

### 2.2 R2-B — Analyse

- **B2 — l'indice de référence contourne la porte source/droits** (backend,
  défaut réel). `analysis.py:595-618` `_barres_de` filtre uniquement
  `payload.ticker` et le type de `bars` (relu : `:595`), alors que
  l'instrument est rejeté `REASON_SOURCE_NOT_ALLOWED` / `RIGHTS_NOT_USABLE` /
  devise / base (`:987-1014`). Reproducteur (config synthétique, SPX
  `source="ibkr"`, 80 barres) → `relative_strength.status OK`,
  `rejected_records []` : rouge. Correction minimale : dans `_barres_de`,
  ignorer tout record dont `source ∉ allowed_sources` ou `rights ∉
  usable_rights`, devise/base invalides → `BENCHMARK_NOT_OBSERVED` ou raison
  dédiée, tracé dans `coverage.rejected_records`.
- **B1 — force relative calculée, persistée, relayée mais jamais affichée ni
  décrite au contrat** (UI de contenu + docstring OpenAPI ; lacune d'origine).
  `AnalysisPage.tsx:456-457` ne lit que `realized_volatility`/`atr` ;
  `relative_strength` absent de `apps/web/src`, `openapi.json`,
  `schemas.py:311-316` ; elle traverse l'API par `additionalProperties: true`.
  Correction : une `Ligne` supplémentaire lisant `status`/`value`/`benchmark`/
  `common_sessions`/`horizon` tels quels (aucun calcul TS) ; docstring
  `AnalysisResponse` ; `tools/export_openapi.py` + `pnpm gen:api` ; fixture.
- **B3 — assemblage `build_analysis_content` et profil réel non testés**
  (couverture) : `_barres_de` dans aucun test ; `benchmark` absent de
  `test_profiles.py`. Comportement vérifié correct par reproducteurs.
- **B4(b) — aucun test positif du relais des indicateurs** (couverture API).
  B4(a) **réfuté** : le chemin « dossier antérieur → 200 » est gardé (mutation
  de `snapshot_views.py:2013-2017` → FAILED).
- **B6 — registre : `tests:` incomplet** pour `market.realized_volatility`,
  `market.atr`, `market.relative_strength` (ne citent que `test_market.py`).
- **Rétrogradé** : B5 (`_relative_strength_block` sans `source_event_ids`) —
  `_calculation_meta` ne publie jamais ce champ, `input_hash`/`result_hash`
  identiques avec ou sans. Impact nul ; le reproducteur du premier rapport
  était invalide.

### 2.3 R2-C — Presse

- **C1 — collecte de presse INOPÉRANTE à `ecc50c1`** (backend, bloquant).
  `port.py:360` `time_unzoned: datetime | None` (relu) ; `adapter.py:706`
  `_naive_or_none(...)` (relu) ; `adapter.py:1057` hache la charge ;
  `hashing.py:61-64` refuse le datetime naïf. Reproducteur
  `test_news_hashing_chain.py` → **2 failed, 1 passed** à `ecc50c1`, trace
  `CanonicalizationError: naive datetime cannot be canonicalized`. Pourquoi la
  suite était verte : `test_news.py:194-203` ne hache que la charge dérivée,
  jamais l'enveloppe source. Impact : 0 dépêche insérée, page Aujourd'hui
  vide. Correction : celle de `59a5e3f` — vérifiée par la contre-vérification
  (17 + 371 passed, ruff/mypy 0) ; convertir dans `news.py` seul serait
  insuffisant, assouplir le canonicaliseur serait faux. **Ne pas refaire.**
- **C2 — code mort dans `59a5e3f` : `adapter.py:254 _naive_or_none` sans
  appelant** (relu sur la branche : définition seule). Le code mort vient du
  commit d'origine `732f7e5`, pas du cherry-pick. À retirer dans le même lot.
- **C3 — le test « collecte → hachage → ingestion » exigé par le plan
  s'arrête à la dérivation** : `test_news_hashing_chain.py` n'importe ni
  `ingest_envelope` ni session. Correction : test d'intégration (motif
  `_load_tool()` sur `tools/run_edge_news.py`) ingérant
  `news_headline_envelopes(...)`, vérifiant 1 ligne `ibkr.news-headline/1` et
  `inserted=False` à la relance. Non exécuté (base partagée).
- **C4 — `test_real_profile_chain.py:53-72` fabrique une forme qu'IBKR n'émet
  jamais** (`ibkr.news-headlines/1` avec `title` plat). La suite resterait
  verte si la dérivation cessait d'être appelée. Correction : construire via
  `news_headline_envelopes(...)` et asserter `provenance.member_event_ids`.
- **C5 — cadrage du rail de preuves par instrument sans aucun test ; mutant
  survivant** : suppression de `analysis.py:1229` `instrument_ref=_instrument_ref_de(...)`
  → 353 passed. La régression « 0 preuve GOOG parmi 500 » (`7880413`) peut
  revenir sans échec. Correction : test unitaire de `_instrument_ref_de` +
  test d'intégration 501 dépêches d'un autre `con_id` / 1 GOOG /
  `max_observations=500` → `evidence.considered == 1`.
- **C6 — aucun test de `tools/run_edge_news.py`** ; refus fail-closed exécutés
  manuellement (5 scénarios, rc=2). Correction : `tools/tests/test_run_edge_news_refuse.py`.
- **Faits hors intention** (pas des écarts de requalification) : C7 — toutes
  les dépêches IBKR arrivent sans fuseau → `published_at=None`,
  `as_of=received_at`, la file classe sur l'âge de collecte, pas d'actualité ;
  assumé par `0c79f78` et par le plan → **décision utilisateur** (déclarer le
  fuseau). C8 — `provider_time_unzoned` stocké mais relayé nulle part →
  audit seulement.

### 2.4 R2-F — Risques page (UI de contenu, non-style)

- **F1 — `CorrelationMatrix.tsx:54` peint une bande absente en « Peu liés »**
  (`?? 'weak'`, relu) alors que l'en-tête l'interdit. Reproducteur rouge.
  Inatteignable via l'API (`risk.py:192-212`), mais fonction exportée.
  Correction : repli hors vocabulaire, pas de `data-band`, ou refus de la vue
  si `bands` n'a pas la forme de `matrix` ; aucune règle CSS nouvelle.
- **F2 — `riskView.ts:71-73 numberOf` → 0 et `:75-82 stringGridOf` → `''` sur
  donnée absente** (relu) — `.claude/rules/frontend.md:21` l'interdit.
  Reproducteurs : `coverage: {}` → DOM `0 sur 0 déclarés` : rouge.
  Correction : refus de la vue (état `error`), cohérent avec le relais qui
  exige `_COVERAGE_COUNTS`.
- **F3 — aucun `as_of`/`age_seconds`/`snapshot_version` affiché ; bandeau
  `stale` sans heure** (relu : aucune occurrence dans `RiskPage.tsx`).
  `UI_STATES.md:10` exige pour `stale` « watermark, heure exacte » ; six pages
  installées le font. Reproducteurs rouges. Correction : `asOfLabel` sur le
  bandeau (motif `OpportunitiesPage.tsx:352`) + entrée `as_of` dans
  `dl.vx-risk-coverage` ; rien affiché quand `as_of` est null.
- **F5 — `NOW.md:612-618` annonçait un « 500 latent sur Risques » déjà
  corrigé** : à `ecc50c1`, `"value"` est sous `_SIGNED_DECIMAL_KEYS`
  (relu : `snapshot_views.py:977`). Réécrit par la présente PR.
- **F4 — décision produit** : le refus motivé est rendu sous le libellé
  « Aucune donnée » (`DataStateBoundary state="empty"`) ; reproducteur rouge,
  mais `DataStateBoundary.tsx:23` interdit de reformuler sans décision produit.
- **F6 — style, hors R2** : `global.css:4903 .vx-risk-page-section` sans
  utilisateur. À transmettre au propriétaire de `global.css`.

### 2.5 R2-J — surfaces post-fusion #18

- **J1 — `REPRENDRE_ICI.md` §1 périmé et contradictoire** (→ R2-I) :
  `:12-13` « Branche de travail : `claude/snapshots-confirmation-20260901` /
  En attente de fusion : PR #18 » (relu) alors que #18 est fusionnée.
  **Aggravant** : les sous-sections 4.1–4.4 présentes à `505d465` ont été
  supprimées par `b8a0d4d` (#18) — à `ecc50c1`, 0 titre `### 4.` (relu) —
  alors que du code les cite comme justification (relu :
  `snapshot_views.py:970` « REPRENDRE_ICI.md §4.3 » ; le rapport en compte
  sept dont `test_risk_signed_value_contract.py`, `marketsView.ts:64`,
  `markets.py:581`, `generator.py:77`). Aucune porte ne le voit. Correction :
  bandeau de supersession vers `NOW.md`, §1 réécrit depuis les preuves,
  réintroduction ou ré-adressage des faits 4.1–4.4 sous ancres stables.
  **La suppression du fichier est à écarter** (citations). La PR #21 corrige
  déjà le §8 ; elle ne traite ni le §1 ni les ancres.
- **J2 — supersession par R1 de facto, jamais déclarée** (→ R2-I) :
  `CLAUDE_RECOVERY_PLAN.md:64/:66` et `R0_GITHUB_SECURITY.md:160` visent la
  version `f9af140`, pas celle de `main`. Reproducteur préféré : exiger une
  ligne de supersession dans les 5 premières lignes tant que le fichier existe.
- **J3 — régression de style introduite par #18, prouvée par A/B Chromium,
  hors R2** : la règle V12 `.vx-main button:not(.vx-primary-action)`
  (`global.css:4783-4798`, spécificité 0,2,1) écrase
  `.vx-legend-chip[aria-pressed='false']` et
  `.vx-chain-group[aria-pressed='true']` (0,2,0) — couleurs identiques
  true/false à `ecc50c1`, distinctes à `505d465`. `line-through` et `▸`
  survivent, `aria-pressed` porté : pas un état dégradé. Aucune porte ne
  couvre ce point. **À transmettre au propriétaire de `global.css`**, avec un
  reproducteur statique (`getComputedStyle`) plutôt qu'un e2e.
- **J4 — vérifié sans écart** : ordre de source des `thead th` voulu par V11 ;
  aucun `<th>` ne porte d'attribut d'état ; `button:disabled` conforme à
  l'intention V12.

## 3. Lots R2 déjà ouverts (aucune fusion)

| Lot | Branche @ tête | Base | Contenu | Preuves |
|---|---|---|---|---|
| R2-C' presse, hachage | `lot/r2c-presse-hachage-20260902` | `ecc50c1` | `cherry-pick -x 732f7e5` (hunks identiques) + `test_news_hashing_chain.py` ; retrait de `_naive_or_none` (C2) | reproducteur rouge sur `ecc50c1` (2 failed) puis vert ; ruff 0, mypy 0, edge-ibkr 371, intégration 5, `tools/tests` 427 ; batterie complète et CI : voir la PR |
| Reprise #19 | `lot/r2-pr19-demarrage-20260902` @ `6d05603` — **PR #21** | `ecc50c1` | `cherry-pick -x e8ff5e6` : `FIRST_INSTALL.md`, `START_LOCAL.md`, `REPRENDRE_ICI.md` §8, `test_bootstrap_local.py` (3 gardes) ; hunk `NOW.md` écarté (propriétaire : cette PR) | 12 passed ; six portes documentaires 0 ; CI 7/7 verte (deux runs) |
| Requalification R2 (ce document) | `lot/r2-requalification-20260902` | `ecc50c1` | `R2_REQUALIFICATION.md` (nouveau) + `NOW.md` (A4, F5, état R2) | portes documentaires ; aucun code |

## 4. Indéterminés — signalés par un seul rapport, ou relevant d'une décision

| Réf. | Vague | Constat (preuve citée par le rapport) | Ce qui manque pour trancher |
|---|---|---|---|
| D1 | R2-D | nomenclature des portes de `rebase_series` incohérente entre registre `:93`, docstring `market.py:404-412` et codes levés ; `test_market.py:626-644` n'assertent pas `reason` | contre-vérification ; documentaire |
| D2 | R2-D | `rebase_series` n'appelle pas `_require_sequence` (itérateur → `TypeError`, chaîne acceptée) | contre-vérification ; faible (annotation `Sequence` respectée, mypy vert) |
| D3 | R2-D/E | `CALCULATION_REGISTRY.yaml:7` « Twenty-three entries » (relu) vs 24 comptées par le rapport | recompte indépendant ; documentaire |
| E1 | R2-E | `runtime_usage: not_called_by_production_code_yet` sur `risk.covariance` et `risk.correlation` (relu : `:1017`, `:1060`) alors que `worker/risk.py:326` les appellerait en production ; aucune porte ne lit `runtime_usage` | contre-vérification de l'appel ; test proposé |
| E2 | R2-E | docstring `worker/risk.py:460-462` « six tickers » vs quatre mesurés | nul en exécution |
| E3 | R2-E | seuil compté en rendements (`len(communs) - 1`) mais publié en séances : à 30 séances/seuil 30, refus « Seulement 30 séances … sous le seuil déclaré de 30 » | choix d'unité à trancher ; borné à la frontière exacte |
| E4 | R2-E | trajet HTTP avec `most_opposed.value` négatif non exercé par `TestClient` | test vert par construction |
| G1 | R2-G | `DEBT.md:534` « FERMÉ » vs `:612-614` « reste ouvert » ; `:548` « 08 et 09 réservés » alors que `AppShell.tsx:51` attribue 09 | contre-vérification ; documentaire |
| G2 | R2-G | `PAGE_ARBITRATION.md:92` « trente routes … ni `charts` ni `risks` » (relu) vs `openapi.json` 32 routes dont `/api/v1/risk/matrix` | contre-vérification ; documentaire |
| G3 | R2-G | `ShellTicker.test.tsx` sert `makeMarketsOverview()` à toutes les URL, `TypeError` absorbé | bruit de test seulement |
| F4 | R2-F | refus motivé sous « Aucune donnée » | décision produit |
| B-ATR | R2-B | libellé « ATR (Wilder) » vs registre `method: wilder_true_range_simple_arithmetic_mean` | décision de libellé |
| B-WIN | R2-B | fenêtre `load_daily_bar_records(lookback=8 j, limit=500)` partagée par 161 instruments peut exclure SPX → `BENCHMARK_NOT_OBSERVED` sans autre signal | mesure sur base réelle |
| A-E2E | R2-A | `e2e/portfolio.spec.ts:51` épingle `mark_population = SYNTHETIC` | campagne Playwright (jamais exécutée) |
| HORS | R2-B/J | `marketsView.ts:17 signGroupOf` et `PortfolioTable.tsx:55 startsWith('-')` : classification du signe côté TS, préexistante au socle | rattachement à une vague, lecture au critère 4 |

## 5. R2-I — faits de `f9af140` à porter par réécriture, jamais par fusion

Le commit Claude `f9af140` (passation d'un poste) est **DROP**. Les seuls faits
qu'il portait et qui méritent d'être dits ailleurs, réécrits depuis les
mesures du 2026-09-02 :

- TWS écoute en **7496 (Live)** ; le port est fourni par `VERTEX_IBKR_PORT`,
  l'adaptateur n'accepte que `127.0.0.1` ; TWS lui-même écoute sur `0.0.0.0`
  (intervention humaine : restreindre à localhost dans TWS).
- Le collecteur temps réel a un **budget de 24 instruments** ; un univers de
  8 indices (`~/.vertex/univers-temps-reel.json`) tient dedans.
- Sur ce poste, **NDX, ESTX50 et N225 ne sont disponibles qu'en différé** ;
  aucun repli automatique vers le différé n'est activé.
- Les identifiants de client (71 temps réel, 72 historique, 73 découverte,
  79 presse, 74 sonde, 75 exécuteur borné) sont distincts pour coexister.

Aucun chemin, aucun secret, aucune valeur d'environnement n'est reproduit ici.

## 6. Ordre de correction recommandé (PR bornées, non exécutées)

Backend avant UI ; un propriétaire par fichier verrouillé (`global.css`,
`tokens.ts`, `AppShell.tsx`, `routes.tsx`, OpenAPI, `NOW.md`) ; chaque PR :
test rouge d'abord, validations ciblées puis `tools/run_checks.sh`,
brouillon, revue humaine, squash.

0. **Préalables sans code** — (i) contre-vérification adverse de R2-D, R2-E,
   R2-G avant toute PR sur leurs écarts ; (ii) décisions propriétaire :
   membre(s) composé(s) de `POPULATION_LABELS` pour A1 (cas `EMPTY` inclus),
   unité du seuil E3, libellé F4, libellé B-ATR ; (iii) décision utilisateur
   C7 (fuseau des dépêches).
1. **PR-1 (backend, bloquante) — R2-C hachage** : le lot R2-C' (C1 + C2) ;
   C3 en suite. Débloque la page Aujourd'hui.
2. **PR-2 (tests seuls) — R2-C couverture** : C4, C5 (le test qui tue le
   mutant), C6.
3. **PR-3 (backend) — R2-B porte de l'indice** : B2 avec son reproducteur
   rouge ; B3, B4(b) ; B6.
4. **PR-4 (backend, petite) — R2-A conclusion Marchés** : A2 + deux pins.
5. **PR-5a (backend, contrat) — nature des marks performance** : après
   0(ii) : `POPULATION_LABELS`/`GENERATED_NATURE_LABELS`/`NATURE_PARENT_KEYS`
   + `performance.py` (A1) + `test_performance_population_follows_source.py`.
6. **PR-5b (UI de contenu) — Marchés/Portefeuille** : `SyntheticBanner.tsx`
   reçoit les nouveaux membres + A3 + test vitest. Après PR-5a.
7. **PR-6 (UI de contenu) — R2-F vérité des données** : F1, F2, F3 avec les
   reproducteurs de la contre-vérification. F4 seulement sur décision produit.
8. **PR-7 (contrat + UI de contenu) — force relative** : B1. Après PR-3.
9. **PR-8 (documentation, R2-I, propriétaire `NOW.md`)** : `REPRENDRE_ICI.md`
   (bandeau de supersession, §1, ancres 4.1–4.4 — J1, J2), `DEBT.md` (G1),
   `PAGE_ARBITRATION.md:92` (G2), `CALCULATION_REGISTRY.yaml:7` (D3),
   `runtime_usage` (E1), docstring E2 ; runbook du collecteur
   `run_edge_news.py`. A4 et F5 sont traités par la présente PR.
10. **Hors R2 — chantier graphique (propriétaire `global.css`)** : J3, F6. À
    transmettre, pas à corriger ici.

## 7. Non vérifié — dit franchement

- **Contre-vérification absente** sur R2-D, R2-E, R2-G : leurs KEEP reposent
  sur un seul rapport.
- **`tools/run_checks.sh` complet à `ecc50c1`** : exécuté par un seul rapport
  (R2-B, TOUT VERT rc=0) ; les sept autres ne l'ont pas rejoué (worktrees sans
  `node_modules`/Chromium, batterie concurrente).
- **Campagne Playwright e2e** : jamais exécutée par aucune vague (ports
  8000/4173 occupés, `/opt/pw-browsers` absent). Tout ce qui concerne le rendu
  réel reste inférence ou audit statique.
- **Tests d'intégration PostgreSQL** : exécutés pour R2-A (6), R2-B (2),
  R2-E (4) ; non exécutés pour R2-C, F, G, J. Le trajet dépêche → base → file
  d'attention n'est prouvé nulle part.
- **Mesures sur données réelles** citées par les commits (16 946 messages,
  162/163 têtes, GOOG vol 27,95 %, SPX/NDX 0,927, SPX/VIX −0,803, 161
  instruments) : aucune connexion à `vertex_live` par l'audit ; non re-mesurées.
- **Comportement IBKR réel** (préfixe, horodatages naïfs, `$` dans
  `article_id`, timeouts par fournisseur) : repris des messages de commit,
  jamais re-mesuré par l'audit.
- **Cause exacte** de l'échec unique de `OptionsPage.test.tsx` sous charge :
  « timing », non prouvée.
- **R2-H** : non instruit ; HOLD maintenu.
