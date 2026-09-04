# Désordre documentaire de `/home/user/vertex-merge` — état exact et rangement cible

**Périmètre lu** : 135 fichiers sous `docs/` (12 dossiers), 27 fiches `.claude/lots/`, 7 fichiers `.claude/rules/`, 2 skills (`vertex-one`, `vertex-titanium-ledger` + 9 références + 7 planches + 1 script), `CLAUDE.md`, `AGENTS.md`.
**Preuves de code** relevées sur `HEAD = b50e09e` (branche `lot/t4-7-fin-dette-20260904`, merge de `origin/main` — dernier lot fusionné : T4-6 / PR #54, 2026-09-04).

---

## 0. Le diagnostic en une phrase

Le dépôt n'a pas un problème de volume documentaire : il a **quatre systèmes de numérotation concurrents** (`.claude/lots/LOT-00..26`, `FOLDER_BY_FOLDER_PROGRAM` dossiers 00–25, les lots de session `A2/C0/L0/P1-6/S0-6/T1-T4-7`, et la liste de tâches `LOT 0..24`), **deux skills qui se déclarent chacun « maître »**, et **une couche produit (01-product, 05-design partiellement, 07-delivery) figée sur les douze pages d'avant les quatre absorptions de LOT-07/08/10/12**, alors que le code a bougé et est, lui, cohérent.

Chiffres mesurés :

| Mesure | Valeur relevée dans le code |
|---|---|
| Destinations réelles | 12 + `/auth` hors rail (`apps/web/src/app/pages.ts`) |
| Redirections permanentes | 4 (`/system`, `/performance`, `/follow-up`, `/ai`) |
| Endpoints protégés/publics | 31 chemins (`apps/api/src/vertex_api/`) |
| Jobs CI | 7 (`ci.yml`) + 2 nightly |
| Motifs d'absence déclarés | `NO_SOURCE` 61, `SERVER_CONTRACT_MISSING` 41, `DECISION_PENDING` 18, `SUBSCRIPTION_REQUIRED` 3 |
| Registre de calculs | 29 `APPROVED`, 2 `NOT_IMPLEMENTED`, 1 `RESEARCH_ONLY` |
| Largeur de rail | `--vx-rail-width: 136px` (`apps/web/src/styles/global.css:87`) |

---

## 1. Classification des 135 fichiers de `docs/`

Légende : **N** = norme (contrat durable) · **P** = plan (chantier, périmable) · **R** = rapport (constat daté) · **A** = archive (terminé).

### `docs/00-foundation/` (5) — tout **N**
`CONSTITUTION.md` **N** · `GLOSSARY.md` **N** · `NON_GOALS.md` **N** · `PRODUCT_VISION.md` **N** · `SCOPE.md` **N**

### `docs/00-product/` (1)
`CURRENT_VERTEX_SALVAGE_MATRIX.md` **R** (audit daté du donneur au SHA `c683c944`, doublonné par `manifests/current-vertex-salvage.yaml`)

### `docs/01-product/` (15)
`INFORMATION_ARCHITECTURE.md` **N** (périmée) · `NAVIGATION.md` **N** (périmée) · `ROUTES.md` **N** (partiellement à jour, incomplète)
Fiches : `01-today` **N** · `02-calendar` **N** · `03-markets` **N** · `04-opportunities` **N** · `05-analysis` **N** · `06-options` **N** · `07-simulator` **N** · `08-portfolio` **N** · `09-follow-up` **N** (bandeau d'absorption posé) · `10-performance` **N** (périmée, **sans bandeau**) · `11-vertex-ai` **N** (bandeau posé) · `12-system` **N** (périmée, **sans bandeau**)
**Manquants** : aucune fiche pour `/risks` ni `/charts`, deux destinations réelles.

### `docs/02-architecture/` (7)
`DATA_FLOW.md` **N** · `HOT_PATHS_AND_CACHING.md` **N** · `LOCAL_FIRST_DEPLOYMENT.md` **N** · `MODULE_BOUNDARIES.md` **N** · `REPOSITORY_MAP.md` **N** (périmée) · `SYSTEM_CONTEXT.md` **N** · `THREAT_MODEL.md` **N**

### `docs/03-domain/` (18)
`ANOMALY_ENGINE` **N** · `ATTENTION_AND_RELEVANCE_ENGINE` **N** · `CALCULATION_CATALOG` **N** (périmé) · `CANONICAL_CONTRACTS` **N** · `DATA_QUALITY` **N** · `DECISION_ENGINE` **N** · `EVIDENCE_GRAPH` **N** · `MODEL_RISK_AND_VALIDATION` **N** · `OPTIONS_FLOW_INTELLIGENCE` **N** · `OPTIONS_PRICING_AND_SCENARIOS` **N** · `PORTFOLIO_MANUAL` **N** · `PROBABILITY_CALIBRATION` **N** · `QUANTUM_VS_QUANTITATIVE` **N** · `REGIME_AND_SECTOR_MODEL` **N** · `SIGNAL_FUSION` **N** · `STRATEGY_PROFILES` **N** · `UNITS_TIME_AND_PRECISION` **N** · `calculations/CALCULATION_REGISTRY.yaml` **N** (autorité machine, à jour)

### `docs/04-integrations/` (14)
`AI_GATEWAY` **N** · `DATA_FUSION` **N** · `DEPENDENCY_REGISTER` **N** · `IBKR` **N** · `IBKR_ENTITLEMENT_PROBE` **N** · `IBKR_EXPLOITABLE_FIELDS` **N**+**R** (mixte) · `INFORMATION_UNIVERSE` **N** · `NEWS_SOCIAL_INTELLIGENCE` **N** (revue datée 28/08/2026) · `OFFICIAL_SOURCE_ADAPTERS` **N** · `OFFICIAL_SOURCE_MAP` **N** · `SOURCE_CAPABILITY_MATRIX` **N** · `SOURCE_RIGHTS_AND_RETENTION` **N** · `TRADINGVIEW` **N** · `TRADINGVIEW_EXPLOITABLE_FIELDS` **N**

### `docs/05-design/` (16) — le dossier le plus mélangé
`ACCESSIBILITY` **N** · `CHART_STANDARD` **N** (carte de pages périmée) · `DASHBOARD_COMPOSITION` **N** (périmée) · `DESIGN_SYSTEM` **N** · `ICON_SYSTEM` **N** · `MOTION_AND_MICROINTERACTIONS` **N** · `RESPONSIVE` **N** (rail périmé) · `TITANIUM_LEDGER_VISUAL_SYSTEM` **N** (codes TL périmés) · `TOKENS` **N** · `UI_STATES` **N** · `WIDGET_LIBRARY` **N**
`PAGE_ARBITRATION` **N**+**R**+**journal** (mixte : la table d'arbitrage est la seule norme à jour des destinations ; le reste est un journal d'exécution)
`PLAN_NUIT_IDENTITE_V3` **P** (terminé → **A**) · `REFONTE_TITANIUM_LEDGER` **P** (terminé → **A**) · `WIDGETS_V2_PLAN` **P** (partiellement exécuté) · `VERTEX_ONE_VISUAL_DIRECTION` **A** (l'en-tête le dit lui-même)

### `docs/06-quality/` (9)
`CI_GATES` **N** (périmée) · `DATA_LATENCY_BUDGETS` **N** · `OBSERVABILITY` **N** · `PERFORMANCE_BUDGETS` **N** (doublon périmé) · `PERFORMANCE_TEST_PLAN` **N** · `SECURITY_CONTROLS` **N** · `TEST_MATRIX` **N** · `TEST_STRATEGY` **N** · `ACCESSIBILITY_REPORT` **R**

### `docs/07-delivery/` (13)
`BACKLOG` **N** · `DEFINITION_OF_DONE` **N** · `DEPENDENCY_MATRIX` **N** (doublon partiel) · `MIGRATION_POLICY` **N** · `checklists/BEFORE_LOT` **N** · `checklists/BEFORE_PR` **N** · `checklists/PAGE_ACCEPTANCE` **N** · `checklists/RELEASE` **N**
`MASTER_ROADMAP` **P** (périmé) · `FOLDER_BY_FOLDER_PROGRAM` **P** (périmé) · `DONOR_EXTRACTION_PROTOCOL` **P** · `MIGRATION_INVENTORY.csv` **P** (11 lignes, toutes `status=planned`, `reviewed_by` vide) · `BETA_REPOSITORY_BOOTSTRAP` **A** (périmé)

### `docs/08-runbooks/` (12)
`BACKUP_RESTORE` **N** · `CLAUDE_REMOTE_CONTROL` **N** · `CLAUDE_SKILLS_AND_AGENTS` **N** (périmée) · `CLAUDE_TOOLS` **N** · `FIRST_INSTALL` **N** · `GIT_HISTORY_QUARANTINE` **N** · `IBKR_SETUP` **N** · `INCIDENT` **N** · `START_LOCAL` **N** (exécutable, à jour) · `TRADINGVIEW_SETUP` **N**
`GITHUB_PROTECTION` **N**+**R** (mixte) · `REPRENDRE_ICI` **R** (passation datée 2026-09-02 → **A**)

### `docs/09-adr/` (18) — tout **N**
`000-template` **N** · `001`…`017` **N**, tous `Accepté`. Aucun `Remplacé`. ADR-017 (2026-09-03) est le plus récent et fait autorité sur les formes de widgets.

### `docs/99-status/` (7)
`NOW.md` **R**+**journal** (2 616 lignes : ~565 de bloc YAML d'état, ~2 050 de journal de session) · `DEBT.md` **N**+**journal** (799 lignes : registre vivant + accumulation par lot) · `BLOCKERS.md` **N** (partiellement périmé) · `HISTORY.md` **R** (ce n'est plus l'historique promis par son propre en-tête, mais 3 rectifications de messages de commit) · `R0_GITHUB_SECURITY` **A** · `R2_REQUALIFICATION` **A** · `CLAUDE_RECOVERY_PLAN` **A**

**Synthèse** : 96 **N**, 8 **P**, 8 **R**, 6 **A**, 5 mixtes (`NOW.md`, `DEBT.md`, `PAGE_ARBITRATION.md`, `GITHUB_PROTECTION.md`, `IBKR_EXPLOITABLE_FIELDS.md`), 12 fiches produit à statut hétérogène.

---

## 2. Documents qui se contredisent deux à deux (citations exactes)

### C-01 — Groupes de navigation : IA/NAVIGATION contre le code (**bloquant**)
- `docs/01-product/INFORMATION_ARCHITECTURE.md:8` : « **- Piloter : Portefeuille, Suivi, Performance.** »
- `docs/01-product/INFORMATION_ARCHITECTURE.md:9` : « **- Assistance : Vertex AI, Système.** »
- `docs/01-product/NAVIGATION.md` (table) : « | Piloter | **Portefeuille, Suivi, Performance** | » · « | Assistance | **Vertex AI, Système** | »
- `apps/web/src/app/pages.ts` : « `{ label: 'Piloter', pages: [portfolio, risk, catalysts] },` » et « `{ label: 'Assistance', pages: [system] },` » avec `system.title = 'Sources & Rapports'`, `Observer` incluant `charts`.
→ Trois pages nommées par les normes n'existent plus ; trois pages réelles n'y figurent pas.

### C-02 — Largeur de rail : quatre valeurs pour un seul objet
- `docs/01-product/NAVIGATION.md:16` : « Rail gauche **232 px** rétractable à 68 px. »
- `docs/05-design/RESPONSIVE.md:21` : « Composition canonique : rail **232 px** rétractable… »
- `docs/05-design/DASHBOARD_COMPOSITION.md:17` : « - rail : **232 px** ouvert ou 68 px replié ; »
- `docs/05-design/DESIGN_SYSTEM.md:54` : « - rail desktop **248 px** rétractable à 68 px ; »
- `docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md:168` : « - rail : **248 px** ouvert, 68 px compact ; »
- `apps/web/src/styles/global.css:87` : « `--vx-rail-width: 136px;` »
- `docs/05-design/REFONTE_TITANIUM_LEDGER.md:232` : « Rail 248 → **136 px** ». `apps/web/src/shell/NavRail.tsx:15` porte encore le commentaire « Rail de navigation desktop — **232 px** ».

### C-03 — Codes Ledger `TL/NN` : deux affectations incompatibles
- `docs/05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md:149` : « | **TL/02 | Opportunités** | candidats admissibles | » … « | TL/09 | **Suivi** | » · « | TL/10 | **Performance** | » · « | TL/11 | **Vertex IA** | » · « | TL/12 | **Système** | »
- `docs/05-design/WIDGETS_V2_PLAN.md:113` : « ### 4.2 **Marchés — TL/02** — dominante : treemap » … « 4.9 **Risques — TL/09** » · « 4.10 **Catalyseurs — TL/10** » · « 4.11 **Calendrier — TL/11** » · « 4.12 **Sources & Rapports — TL/12** »
- `apps/web/src/shell/AppShell.tsx:42-52` : « `markets: 'TL / 02'` … `risks: 'TL / 09'`, `catalysts: 'TL / 10'`, `calendar: 'TL / 11'`, `'sources-reports': 'TL / 12'` ».
→ Le code suit `WIDGETS_V2_PLAN` ; `TITANIUM_LEDGER_VISUAL_SYSTEM` — qui se déclare pourtant l'autorité de style — est faux sur dix lignes sur douze.

### C-04 — Matrice de composition « normative » contre la table d'arbitrage
- `docs/05-design/DASHBOARD_COMPOSITION.md:70` : « **Cette matrice est normative.** » — et elle liste « Suivi », « Performance », « Vertex AI », « Système » comme des pages, sans Graphiques, Risques, Catalyseurs ni Sources & Rapports.
- `docs/05-design/PAGE_ARBITRATION.md:25-42` : « | `performance` | Portefeuille | **`ABSORBER`** | » · « | `follow-up` | Catalyseurs | **`ABSORBER`** | » · « | `ai` | inspecteur contextuel | **`ABSORBER`** | » · « | — | **Graphiques** | `CRÉER` | » · « | — | **Risques** | `CRÉER` | ».

### C-05 — Registre des calculs : « planning_seed » contre « runtime_partially_approved »
- `docs/03-domain/CALCULATION_CATALOG.md:3` : « Dans ce blueprint, il est un **`planning_seed`** : **aucune ligne n'est runtime-ready** avant que le LOT-07 ajoute et valide version, méthode, paramètres, tolérances… »
- `docs/03-domain/calculations/CALCULATION_REGISTRY.yaml:5` : « `registry_status: **runtime_partially_approved**` » ; « **Twenty-nine entries carry a verified runtime block (APPROVED)** ». Vérifié : 29 `APPROVED`, 2 `NOT_IMPLEMENTED`, 1 `RESEARCH_ONLY`. `tools/check_calculation_registry.py` l'impose en CI.

### C-06 — Accessibilité : la norme affirme une validation que le rapport dément
- `docs/05-design/ACCESSIBILITY.md:15` : « - **tables virtualisées** testées avec lecteur d'écran et focus ; »
- `docs/05-design/ACCESSIBILITY.md` (Validation) : « …parcours clavier, **NVDA/VoiceOver desktop** sur parcours clés et **Storybook** aux états complets… »
- `docs/99-status/NOW.md` (`ecarts_declares`) : « **revue lecteur d'écran par une personne : NON FAITE** » · « **tables non virtualisées** : le budget de 160 lignes rendues n'est pas atteignable en l'état »
- `docs/06-quality/ACCESSIBILITY_REPORT.md:5` : « **État global : PARTIELLEMENT CONFORME.** Un critère AA est mesuré non conforme… »
- Vérifié : aucun `.storybook`, aucun `*.stories.*`, aucune dépendance Storybook dans `apps/web/package.json`. Storybook est cité comme moyen de validation par 4 documents et n'existe pas.

### C-07 — Portes CI : 15 checks documentés contre 7 jobs réels
- `docs/06-quality/CI_GATES.md` déclare quinze checks : `policy`, `python-quality`, `web-quality`, `contracts`, `migrations`, `finance-unit`, `finance-property`, `fusion`, `integration`, `security`, `build`, `e2e`, `a11y`, `performance`, `release`.
- `.github/workflows/ci.yml` : `garde-fous`, `python-quality`, `python-unitaire`, `python-integration`, `web`, `e2e`, `supply-chain` (7). `nightly.yml` : `cross-browser`, `licences`.
→ Neuf noms de checks documentés n'existent sous aucune forme ; les noms réels ne figurent nulle part dans `docs/`.

### C-08 — Budgets de performance : promesses contre objectifs provisoires
- `docs/06-quality/PERFORMANCE_BUDGETS.md` : « - LCP ≤ 2,5 s ; - INP ≤ 200 ms ; … - **lecture snapshot cached p95 ≤ 250 ms, p99 ≤ 750 ms** ; »
- `docs/06-quality/DATA_LATENCY_BUDGETS.md:5` : « Ces budgets sont des **objectifs provisoires à benchmarker**, **pas des promesses**… La source machine des valeurs est `manifests/performance-budgets.yaml`. »
- `manifests/performance-budgets.yaml:4` : « `status: **provisional_targets**` »
- `docs/99-status/NOW.md` : « **latence API : AUCUNE mesure** — p95 exige 1 000 échantillons… »

### C-09 — Carte du dépôt contre le dépôt
- `docs/02-architecture/REPOSITORY_MAP.md` : « | Web partagé | **`packages/typescript/api-client`, `ui`, `charts`** | » · « | Contrats | `contracts/json-schema`, **`events`**, `examples`, **`openapi`** | » · « | Fixtures | **`fixtures/synthetic`**, `contracts`, `golden` | » · « | Tests | **`tests/unit`, `property`, `contract`…** | »
- Vérifié : `packages/` ne contient que `python/` (`vertex_core`, `vertex_persistence`) ; `contracts/` ne contient que `examples/` et `json-schema/` ; il n'existe ni `fixtures/` ni `tests/` à la racine. Le code graphique vit dans `apps/web/src/charts/`.

### C-10 — Feuille de route contre la réalité des pages
- `docs/07-delivery/MASTER_ROADMAP.md` : « | 19 | **Suivi** | … | 20 | **Performance** | … | 21 | **Vertex AI** | … | 22 | **Système** | »
- `docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md` : « | 23 | **`apps/web/src/pages/follow-up/`, `performance/`** | … | 24 | **`apps/web/src/pages/vertex-ai/`, `system/`** | »
- Vérifié : `apps/web/src/pages/` contient `catalysts/`, `charts/`, `risk/`, `sources/`, `SourcesReportsPage.tsx` ; aucun `follow-up/`, `performance/`, `vertex-ai/`, `system/`.

### C-11 — Numéros de lot : la même étiquette pour deux choses
- `docs/01-product/pages/09-follow-up.md:3` : « **Statut depuis le LOT-10** : ce n'est plus une destination. » — or `.claude/lots/LOT-10-design-shell.md` est « **LOT-10 — Design system Black Glass et shell desktop** ».
- `docs/01-product/pages/11-vertex-ai.md:3` : « **Statut depuis le LOT-12** » — or `.claude/lots/LOT-12-calendar.md` est « **LOT-12 — Page Calendrier** ».
- `apps/web/src/app/pages.ts` attribue encore `lot: 'LOT-15'` à Aujourd'hui (numérotation `FOLDER_BY_FOLDER`), tandis que `.claude/lots/LOT-15-analysis.md` est « Page Analyse ».
→ Trois référentiels de numérotation se croisent dans les mêmes phrases.

### C-12 — Deux skills « maîtres »
- `.claude/skills/vertex-one/SKILL.md:7` : « # Vertex One — **skill maître** »
- `.claude/skills/vertex-titanium-ledger/SKILL.md:7` : « # Vertex 1.0 Beta — **skill maître** d'audit et d'identité »
- `AGENTS.md` : « …lire entièrement **`.claude/skills/vertex-titanium-ledger/SKILL.md`** » — `CLAUDE.md` de la racine ne cite aucun des deux et impose le protocole `.claude/lots/`.
- `docs/08-runbooks/CLAUDE_SKILLS_AND_AGENTS.md:6` : « - **un skill maître : `.claude/skills/vertex-one/SKILL.md`** ; - **six sous-agents d'audit** » — vérifié : aucun sous-agent dans `.claude/agents/`.

### C-13 — Routes produit incomplètes contre l'arbitrage qu'elles citent
- `docs/01-product/ROUTES.md` liste dix routes et intègre bien les quatre absorptions, mais **ne contient ni `/risks` ni `/charts`**, alors que le même document est censé être la table des destinations et que `PAGE_ARBITRATION.md` les déclare « `CRÉER` » et que `pages.ts` les sert.

### C-14 — Carte page → moteur graphique périmée
- `docs/05-design/CHART_STANDARD.md:31-45` : « | **Suivi** | file de revues | … | **Performance** | capital/drawdown | ECharts | … | **Vertex AI** | réponse/citations | … | **Système** | matrice de santé | » — aucune ligne pour Graphiques, Risques, Catalyseurs, Sources & Rapports.

### C-15 — Blocages humains partiellement morts
- `docs/99-status/BLOCKERS.md` : « | B-01 | **Auditer puis fusionner la PR #1 (bootstrap)** … | `main` reste au commit initial | »
- Vérifié : `git log` montre 54 PR fusionnées jusqu'à `#54` (2026-09-04). B-01 est mort. B-02 à B-05 restent vivants et sont bien repris dans `NOW.md`.

---

## 3. Documents périmés, avec la preuve de ce qui les a dépassés

| Document | Affirmation périmée | Preuve dans le code |
|---|---|---|
| `01-product/INFORMATION_ARCHITECTURE.md` | groupes Piloter/Assistance à 5 pages mortes | `pages.ts` `NAV_GROUPS` |
| `01-product/NAVIGATION.md` | mêmes groupes + rail 232 px | `pages.ts`, `global.css:87` |
| `01-product/ROUTES.md` | 10 routes, sans `/risks` ni `/charts` | `routes.tsx` `INSTALLED_PAGES` (12 clés) |
| `01-product/pages/10-performance.md` | « # Page 10 — Performance `/performance` » présentée comme destination | `routes.tsx` `LEGACY_REDIRECTS` : `['/performance', '/portfolio']` |
| `01-product/pages/12-system.md` | « # Page 12 — Système `/system` » | `routes.tsx` : `['/system', '/sources-reports']` |
| `02-architecture/REPOSITORY_MAP.md` | `packages/typescript/*`, `contracts/openapi`, `contracts/events`, `fixtures/`, `tests/` | aucun de ces chemins n'existe |
| `03-domain/CALCULATION_CATALOG.md` | registre = `planning_seed`, rien de runtime-ready | `CALCULATION_REGISTRY.yaml` : 29 `APPROVED`, porte CI `check_calculation_registry.py` |
| `05-design/DASHBOARD_COMPOSITION.md` | matrice « normative » des 12 anciennes pages ; rail 232 px | `pages.ts`, `PAGE_ARBITRATION.md`, `global.css` |
| `05-design/CHART_STANDARD.md` (carte pages) | Suivi/Performance/Vertex AI/Système | `apps/web/src/pages/` |
| `05-design/RESPONSIVE.md` | rail 232 px | `global.css:87` = 136 px |
| `05-design/DESIGN_SYSTEM.md` (§ Mise en page) | rail 248 px | idem |
| `05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md` | table `TL/01..TL/12` + rail 248 px | `AppShell.tsx:41-53` |
| `05-design/TOKENS.md` | « Le **LOT-10 la convertit** en une source typée unique » (futur) | `apps/web/src/design/tokens.ts` + `tokens.css` générés, 9 portes dans `apps/web/src/design/` |
| `06-quality/CI_GATES.md` | 15 checks nommés | `ci.yml` : 7 jobs |
| `06-quality/PERFORMANCE_BUDGETS.md` | budgets présentés comme des seuils fermes | `manifests/performance-budgets.yaml` `status: provisional_targets` |
| `07-delivery/MASTER_ROADMAP.md` | lots 19–22 = Suivi/Performance/Vertex AI/Système | quatre absorptions exécutées (LOT-07/08/10/12 de la campagne) |
| `07-delivery/FOLDER_BY_FOLDER_PROGRAM.md` | dossiers 23–24 = `follow-up/`, `performance/`, `vertex-ai/`, `system/` | ces dossiers n'existent pas |
| `07-delivery/BETA_REPOSITORY_BOOTSTRAP.md` | « Cible … **quasi vide**, branche de travail déjà poussée » | 54 PR fusionnées, ~3 800 tests Python, 12 pages |
| `08-runbooks/CLAUDE_SKILLS_AND_AGENTS.md` | « un skill maître `vertex-one` ; **six sous-agents** » | 2 skills, 0 sous-agent |
| `08-runbooks/GITHUB_PROTECTION.md` (§ État initial) | « dépôt public ; `main` **non protégée** ; **aucun ruleset** » (1er sept.) | `NOW.md` : « ruleset main-required 22076309 **actif** ; main protégée ; squash seul ; sept checks » |
| `08-runbooks/REPRENDRE_ICI.md` | « état au **2026-09-02** », base `main@ecc50c1` | HEAD `b50e09e`, 2026-09-04 |
| `99-status/BLOCKERS.md` (B-01) | « `main` reste au commit initial » | 54 PR fusionnées |
| `99-status/NOW.md` (bloc YAML) | `phase: post_merge_requalification_r2` ; `main_head_observed: ecc50c1` ; `prochaine_commande: "ATTENDRE LA REVUE CODEX DE R1 (PR #17)"` | HEAD `b50e09e` ; T4-7 en cours ; R1/R2 clos |
| `05-design/PLAN_NUIT_IDENTITE_V3.md` | plan T1→P6 « à exécuter » | T1, T2, T3, T4-0…T4-7, P1, P2b, P2d, P4, P5 tous fusionnés |
| `05-design/REFONTE_TITANIUM_LEDGER.md` | lots V1→V9 « à exécuter » | §2bis dit lui-même « fait » pour V1/V2 ; la campagne A2–A8 puis C0/L0/P/T l'a dépassé |

---

## 4. Doublons

| # | Doublons | Nature | Qui doit rester l'autorité |
|---|---|---|---|
| D-01 | Palette Titanium Ledger déclarée **trois fois** : `DESIGN_SYSTEM.md` (bloc CSS 17 tokens), `TITANIUM_LEDGER_VISUAL_SYSTEM.md` (table Rôle/Token/Valeur), `apps/web/src/design/tokens.ts` | valeurs identiques aujourd'hui, mais trois copies à maintenir | `tokens.ts` (source typée qui génère `tokens.css`) ; les docs citent, ne recopient plus |
| D-02 | Catalogue de widgets **trois fois** : `05-design/WIDGET_LIBRARY.md`, `05-design/WIDGETS_V2_PLAN.md` §2-4, `.claude/skills/…/references/component-system.md` (+ `manifests/widget-catalog.yaml`) | recouvrement fort, vocabulaires divergents | `manifests/widget-catalog.yaml` (machine) + `WIDGET_LIBRARY.md` (norme) |
| D-03 | Composition des 12 pages **quatre fois** : `01-product/pages/*.md`, `05-design/DASHBOARD_COMPOSITION.md`, `05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md` §« Architecture des douze pages », `.claude/skills/…/references/pages.md` | trois listes sur quatre sont périmées | `references/pages.md` du skill (la seule à jour sur les 12 destinations réelles) |
| D-04 | Frontières de modules : `02-architecture/MODULE_BOUNDARIES.md` (Possède / Ne possède jamais) et `07-delivery/DEPENDENCY_MATRIX.md` (Consommateurs autorisés / interdits + « Règles d'import ») ; les règles d'import sont en outre dans `.claude/rules/architecture.md` | même contenu sous trois angles | `MODULE_BOUNDARIES.md` + `.claude/rules/architecture.md` |
| D-05 | Programme de construction **deux fois** : `MASTER_ROADMAP.md` (lots 00–24) et `FOLDER_BY_FOLDER_PROGRAM.md` (dossiers 00–25), avec des correspondances différentes | contradictoire | un seul programme, à réécrire |
| D-06 | Matrice de récupération du donneur : `docs/00-product/CURRENT_VERTEX_SALVAGE_MATRIX.md` et `manifests/current-vertex-salvage.yaml` — le doc le dit : « **En cas d'écart, le YAML fait foi** » | doublon assumé | le YAML |
| D-07 | Migration du donneur **trois fois** : `07-delivery/MIGRATION_POLICY.md`, `07-delivery/DONOR_EXTRACTION_PROTOCOL.md`, `09-adr/012-migration-policy.md` | même politique | ADR-012 (décision) + `MIGRATION_INVENTORY.csv` (exécution) |
| D-08 | Budgets de performance : `06-quality/PERFORMANCE_BUDGETS.md` vs `06-quality/DATA_LATENCY_BUDGETS.md` vs `manifests/performance-budgets.yaml` | le premier est un résumé périmé des deux autres | le manifeste (machine) + `DATA_LATENCY_BUDGETS.md` (sémantique) |
| D-09 | Sources officielles **quatre fois** : `OFFICIAL_SOURCE_MAP.md`, `OFFICIAL_SOURCE_ADAPTERS.md`, `SOURCE_CAPABILITY_MATRIX.md`, `SOURCE_RIGHTS_AND_RETENTION.md` (+ `manifests/official-source-capabilities.yaml`) | recouvrement partiel légitime mais frontières floues | à répartir : carte (liens) / adaptateurs (livré) / droits (politique) — la matrice de capacités devient une vue du manifeste |
| D-10 | Univers d'information : `04-integrations/INFORMATION_UNIVERSE.md` vs `IBKR_EXPLOITABLE_FIELDS.md` vs `DATA_FUSION.md` §familles | trois listes de familles de données | `INFORMATION_UNIVERSE.md` |
| D-11 | Accessibilité : `05-design/ACCESSIBILITY.md` (norme) vs `06-quality/ACCESSIBILITY_REPORT.md` (mesure) | légitime, mais la norme affirme des validations que le rapport dément (C-06) | les deux, après correction de la norme |
| D-12 | Stratégie de tests : `06-quality/TEST_STRATEGY.md`, `06-quality/TEST_MATRIX.md`, `.claude/rules/testing.md` | trois expressions de la même pyramide | `.claude/rules/testing.md` (contraignante) + `TEST_MATRIX.md` (couverture) |
| D-13 | Passation/état : `99-status/NOW.md` (bloc YAML) et `08-runbooks/REPRENDRE_ICI.md` | deux documents de reprise, l'un obsolète | `NOW.md` réduit |
| D-14 | Deux skills « maîtres » (C-12) et deux `SKILL.md` couvrant le même produit | 122 + 176 lignes en concurrence | un seul |

---

## 5. Arborescence cible, fichier par fichier

**Principe** : les numéros de dossiers existants sont cités depuis le code, `CLAUDE.md` et des centaines de liens croisés — on ne les renumérote pas. On **ajoute trois destinations de nature** et on y range ce qui n'est pas une norme :

- `docs/50-plans/` — **PLANS** actifs, périmables, datés, avec critère de fin.
- `docs/60-reports/` — **RAPPORTS** datés, immuables.
- `docs/90-archive/AAAA-MM/` — **ARCHIVES** : terminées, conservées pour la preuve, jamais lues comme instruction.

### 5.1 Déplacements

| Chemin actuel | Chemin cible | Raison |
|---|---|---|
| `docs/00-product/CURRENT_VERTEX_SALVAGE_MATRIX.md` | `docs/60-reports/2026-08-28-donor-salvage-matrix.md` | Rapport daté d'audit du donneur ; supprime un dossier orphelin (`00-product`) qui double `01-product`. Le contenu exploitable vit déjà dans `manifests/current-vertex-salvage.yaml`, qui fait foi (D-06). |
| `docs/05-design/VERTEX_ONE_VISUAL_DIRECTION.md` | `docs/90-archive/2026-08/VERTEX_ONE_VISUAL_DIRECTION.md` | Son propre en-tête : « Décision mise à jour : **Titanium Ledger** a été retenu… La spécification active se trouve dans `TITANIUM_LEDGER_VISUAL_SYSTEM.md` ». Étude comparative close ; conservée comme trace de décision. |
| `docs/05-design/REFONTE_TITANIUM_LEDGER.md` | `docs/90-archive/2026-09/REFONTE_TITANIUM_LEDGER.md` | Plan V1→V9 exécuté (§2bis « fait »). **Avant archivage, extraire** : les mesures de densité 1600×1000 (§2.1) et les hauteurs de page avant/après (§ « Hauteurs… ») → `docs/60-reports/2026-09-02-densite-titanium-ledger.md` ; la règle « une seule lumière dominante par carte » (§2.3) → `DESIGN_SYSTEM.md` ; les décisions §5 non tranchées → `BLOCKERS.md`. |
| `docs/05-design/PLAN_NUIT_IDENTITE_V3.md` | `docs/90-archive/2026-09/PLAN_NUIT_IDENTITE_V3.md` | Lots T1→P6 tous fusionnés. **Avant archivage, extraire** : les invariants §4 (non négociables) → `.claude/rules/frontend.md` s'ils n'y sont pas ; la boucle de travail §3 → `docs/07-delivery/checklists/BEFORE_PR.md`. |
| `docs/05-design/WIDGETS_V2_PLAN.md` | `docs/50-plans/WIDGETS_V2.md` | Plan encore partiellement ouvert (lots P/S restants). **Extraire d'abord** la classification A/B/C par module (§4.1–4.12) vers `manifests/widget-catalog.yaml` : c'est le seul inventaire écrit des 225 modules et de leurs motifs d'absence, il ne doit pas mourir avec le plan. |
| `docs/05-design/PAGE_ARBITRATION.md` | **scindé** : table + règles d'exécution → `docs/01-product/DESTINATIONS.md` (**norme**) ; §« Graphiques et Risques », §« Le motif d'inspecteur », § « Journal d'exécution », § ticker → `docs/60-reports/2026-09-01-arbitrage-destinations.md` | La table `actuel → cible → décision` est la **seule norme à jour** des 12 destinations : elle doit vivre dans `01-product`, à côté de `ROUTES.md`, pas dans `05-design`. Le journal reste un rapport. |
| `docs/06-quality/ACCESSIBILITY_REPORT.md` | `docs/60-reports/2026-09-03-accessibilite-wcag22.md` | Rapport daté de mesure, pas une norme. |
| `docs/07-delivery/BETA_REPOSITORY_BOOTSTRAP.md` | `docs/90-archive/2026-08/BETA_REPOSITORY_BOOTSTRAP.md` | Le bootstrap est fait. **Extraire** : les variables `VERTEX_DONOR_ROOT` / `VERTEX_BETA_ROOT` et la vérification du remote → `.claude/rules/repository-role.md` (qui porte déjà la règle) et `docs/08-runbooks/FIRST_INSTALL.md`. |
| `docs/07-delivery/MASTER_ROADMAP.md` | `docs/90-archive/2026-08/MASTER_ROADMAP.md` | Lots 11–22 = pages mortes. **Extraire** : les Portes A/B/C/D/E → `docs/07-delivery/PHASE_GATES.md` (**norme**, elles sont toujours valides) ; le reste est remplacé par le programme actif. |
| `docs/07-delivery/FOLDER_BY_FOLDER_PROGRAM.md` | `docs/90-archive/2026-08/FOLDER_BY_FOLDER_PROGRAM.md` | Dossiers 23–24 pointent des répertoires inexistants. **Extraire** : le cycle `PLAN → DONOR AUDIT → … → ACCEPTED`, le « Paquet de preuve » et les « Règles UI phase 1 » → `docs/07-delivery/DEFINITION_OF_DONE.md`. |
| `docs/07-delivery/DONOR_EXTRACTION_PROTOCOL.md` | `docs/50-plans/DONOR_EXTRACTION.md` | Chantier encore ouvert (B-02 non tranché), mais périmable : c'est un plan, pas une norme. |
| `docs/07-delivery/MIGRATION_INVENTORY.csv` | `docs/50-plans/MIGRATION_INVENTORY.csv` | Même raison ; 11 lignes toutes `planned`, `reviewed_by` vide. |
| `docs/08-runbooks/REPRENDRE_ICI.md` | `docs/90-archive/2026-09/REPRENDRE_ICI-20260902.md` | Passation datée dépassée. **Extraire** : le diagnostic « 443 classes `.vx-*`, 89 atteintes, 15 listes énumérées » et la triple déclaration du rail → `docs/60-reports/2026-09-02-densite-titanium-ledger.md`, puis corriger `NAVIGATION/RESPONSIVE/DESIGN_SYSTEM/DASHBOARD_COMPOSITION` à 136 px. |
| `docs/08-runbooks/GITHUB_PROTECTION.md` | **scindé** : ruleset obligatoire + procédure → reste en `docs/08-runbooks/GITHUB_PROTECTION.md` (**norme**) ; § « État de référence initial — 1er septembre 2026 » → `docs/60-reports/2026-09-01-etat-github.md` | Un relevé daté n'est pas une norme et ne doit pas contredire l'état actuel (ruleset actif). |
| `docs/99-status/R0_GITHUB_SECURITY.md` | `docs/90-archive/2026-09/R0_GITHUB_SECURITY.md` | Opération R0 close. |
| `docs/99-status/R2_REQUALIFICATION.md` | `docs/90-archive/2026-09/R2_REQUALIFICATION.md` | Requalification close. **Extraire** : les écarts encore non corrigés (A1/A2/A3/A4, B1/B2, C1, F1-F3) → `DEBT.md` s'ils n'y sont pas. |
| `docs/99-status/CLAUDE_RECOVERY_PLAN.md` | `docs/90-archive/2026-09/CLAUDE_RECOVERY_PLAN.md` | PR #14/#18 fusionnées ; le plan a été exécuté puis dépassé par R2. |
| `docs/99-status/HISTORY.md` | `docs/60-reports/2026-08-rectifications-de-commits.md` **et** `docs/99-status/HISTORY.md` recréé vide avec son format | Le fichier actuel ne contient pas l'historique promis par son propre en-tête (« Ajouter une ligne après chaque lot fusionné ») mais trois rectifications de messages de commit. Les rectifications sont des rapports ; le journal de lots reste à tenir. |
| `docs/99-status/NOW.md` (l. 570–2616) | `docs/60-reports/journal/2026-09-01…2026-09-04.md` (un fichier par session, ou un seul `JOURNAL-2026-09.md`) | Journal de sessions, pas un état courant. Voir §7. |
| `docs/06-quality/PERFORMANCE_BUDGETS.md` | **supprimé après report** : ses valeurs web (LCP/INP/CLS/bundle) → `manifests/performance-budgets.yaml` si absentes ; sa §« Données » (PostgreSQL d'abord, TimescaleDB/Redis sur ADR) → `docs/07-delivery/BACKLOG.md` qui porte déjà la règle | Doublon périmé qui transforme des objectifs provisoires en promesses (C-08, D-08). |

### 5.2 Créations

| Fichier cible | Contenu | Raison |
|---|---|---|
| `docs/01-product/DESTINATIONS.md` | table `actuel → cible → décision`, les 4 redirections permanentes, les 12 clés, les codes `TL/NN` | Il n'existe aujourd'hui **aucune norme unique** des destinations : la vérité est éclatée entre `PAGE_ARBITRATION.md`, `pages.ts` et le skill. |
| `docs/01-product/pages/13-risks.md` | question, dominante, modules, états, critères | `/risks` est une destination réelle sans fiche produit. |
| `docs/01-product/pages/14-charts.md` | idem | `/charts` est une destination réelle sans fiche produit. |
| `docs/05-design/ABSENCE_DOCTRINE.md` | vocabulaire fermé `NO_SOURCE` / `SUBSCRIPTION_REQUIRED` / `SERVER_CONTRACT_MISSING` / `DECISION_PENDING`, les trois interdits (aucun chiffre, aucun rectangle gris, aucune promesse), la porte anti-tiret ambigu | **La loi 4 du produit n'est écrite nulle part dans `docs/`** : sa seule expression est le commentaire d'en-tête de `apps/web/src/components/AbsentModule.tsx`. C'est la règle la plus structurante du produit et elle n'a pas de norme. |
| `docs/07-delivery/PROGRAM.md` | le programme actif unique (LOT 0 → LOT 24 de la liste de tâches courante), avec la correspondance explicite vers les anciennes numérotations | Remplace `MASTER_ROADMAP` + `FOLDER_BY_FOLDER_PROGRAM` et clôt C-11. |
| `docs/07-delivery/PHASE_GATES.md` | Portes A/B/C/D/E extraites de `MASTER_ROADMAP.md` | Elles restent valides et ne doivent pas être archivées avec le plan périmé. |
| `docs/60-reports/2026-09-04-inventaire-modules.md` | les 225 modules × 12 pages, servis / absents, avec motif | Aucun document ne porte cet inventaire ; il n'existe que dispersé dans le TSX. |

### 5.3 Corrections sur place (fichier inchangé, contenu à rectifier)

| Fichier | Correction |
|---|---|
| `01-product/INFORMATION_ARCHITECTURE.md` | groupes → Décider / Observer (+ Graphiques) / Piloter (Portefeuille, Risques, Catalyseurs) / Assistance (Sources & Rapports) |
| `01-product/NAVIGATION.md` | mêmes groupes ; rail **136 px** rétractable à 68 px |
| `01-product/ROUTES.md` | ajouter `/risks` et `/charts` |
| `01-product/pages/10-performance.md` | poser le bandeau d'absorption comme `09-follow-up.md` |
| `01-product/pages/12-system.md` | renommer « Sources & Rapports », route `/sources-reports` |
| `02-architecture/REPOSITORY_MAP.md` | refléter `packages/python/*`, `apps/web/src/charts`, `contracts/{examples,json-schema}`, absence de `tests/` et `fixtures/` racine |
| `03-domain/CALCULATION_CATALOG.md` | remplacer `planning_seed` par le renvoi au `registry_status` réel |
| `05-design/DESIGN_SYSTEM.md` | rail 136 px ; la palette **cite** `tokens.ts` au lieu de la recopier |
| `05-design/DASHBOARD_COMPOSITION.md` | matrice reconstruite sur les 12 destinations réelles ; rail 136 px |
| `05-design/RESPONSIVE.md` | rail 136 px |
| `05-design/TITANIUM_LEDGER_VISUAL_SYSTEM.md` | table `TL/NN` alignée sur `AppShell.tsx` ; rail 136 px |
| `05-design/CHART_STANDARD.md` | carte page → moteur sur les 12 destinations réelles |
| `05-design/ACCESSIBILITY.md` | retirer Storybook et « tables virtualisées testées » ; renvoyer au rapport pour l'état réel |
| `05-design/TOKENS.md` | passer du futur (« Le LOT-10 la convertit ») au présent |
| `06-quality/CI_GATES.md` | les 7 jobs réels + les 2 nightly, avec leurs noms exacts |
| `06-quality/TEST_MATRIX.md` | « PWA/pages » → 12 destinations, 3 tailles |
| `07-delivery/DEPENDENCY_MATRIX.md` | retirer le graphe de lots (périmé) ; garder producteurs/consommateurs |
| `08-runbooks/CLAUDE_SKILLS_AND_AGENTS.md` | un seul skill maître, zéro sous-agent, ou créer les sous-agents |
| `99-status/BLOCKERS.md` | retirer B-01 (mort) ; garder B-02…B-05 + le connecteur MCP IBKR |
| `.claude/skills/` | fusionner `vertex-one` dans `vertex-titanium-ledger`, ou archiver `vertex-one` — un seul « skill maître » (C-12) |

### 5.4 Inchangés (autorité confirmée)

`00-foundation/*` (5) · `02-architecture/{DATA_FLOW, HOT_PATHS_AND_CACHING, LOCAL_FIRST_DEPLOYMENT, MODULE_BOUNDARIES, SYSTEM_CONTEXT, THREAT_MODEL}` · `03-domain/*` sauf `CALCULATION_CATALOG` (17) · `04-integrations/*` (14) · `05-design/{ICON_SYSTEM, MOTION_AND_MICROINTERACTIONS, UI_STATES, WIDGET_LIBRARY}` · `06-quality/{DATA_LATENCY_BUDGETS, OBSERVABILITY, PERFORMANCE_TEST_PLAN, SECURITY_CONTROLS, TEST_STRATEGY}` · `07-delivery/{BACKLOG, DEFINITION_OF_DONE, MIGRATION_POLICY, checklists/*}` · `08-runbooks/*` sauf les 3 traités (9) · `09-adr/*` (18) · `99-status/{NOW.md réduit, DEBT.md, BLOCKERS.md}`.

**Aucune suppression n'est proposée sans destination** : le seul fichier réellement supprimé est `06-quality/PERFORMANCE_BUDGETS.md`, et ses deux contenus utiles sont explicitement reportés (§5.1).

---

## 6. Les 27 fiches `.claude/lots/` : vivantes ou mortes

| Fiche | État | Justification |
|---|---|---|
| `LOT-00-governance` | **MORTE** (archive) | Constitution acceptée, inventaire en place, `NOW.md` opérationnel. Reste vivant : B-02 (`reviewed_by` vide), qui vit déjà dans `BLOCKERS.md`. |
| `LOT-01-toolchain-ci` | **MORTE** | `uv.lock`, `pnpm-lock.yaml`, 7 jobs CI, actions épinglées par SHA, `check_policy.py`. |
| `LOT-02-contracts-identity` | **MORTE** | `packages/python/vertex_core/contracts`, `contracts/json-schema/*`. |
| `LOT-03-storage-quality` | **MORTE** | `packages/python/vertex_persistence`, migrations, outbox, tests d'intégration PostgreSQL 18 en CI. |
| `LOT-04-ibkr-edge` | **PARTIELLEMENT VIVANTE** | `apps/edge-ibkr` + 3 régimes de collecte livrés, mais « **AUCUNE exécution contre un TWS réel** » pour temps réel et découverte, et le droit de cotation d'option reste **NON CONCLUANT** (`NOW.md`). |
| `LOT-05-tradingview-ingress` | **VIVANTE** | Worker écrit et testé (53 tests de contrat), mais « **déploiement : AUCUN — B-03 en attente** ». |
| `LOT-06-data-fusion` | **MORTE** | `vertex_core/fusion` livré et sous test. |
| `LOT-07-quant-engine` | **MORTE** | Registre à 29 entrées `APPROVED`, porte CI active. |
| `LOT-08-decision-engine` | **MORTE** | `vertex_core/decision`, `AdviceEngine` unique, ADR-014. |
| `LOT-09-api-jobs-observability` | **MORTE** | 31 endpoints, SSE `/events/stream`, auth passkey, OpenAPI exportée. |
| `LOT-10-design-shell` | **MORTE mais toxique** | Le shell existe. La fiche fixe « rail **232 px** » (l. 99-101), en contradiction avec le code : elle doit être archivée, pas laissée comme référence. |
| `LOT-11-today` | **MORTE** | `/today` livrée, composée, passée en widgets v2 (P1) et purgée du tiret ambigu (T4). |
| `LOT-12-calendar` | **MORTE** | `/calendar` livrée (A7, T4-4). |
| `LOT-13-markets` | **MORTE** | `/markets` livrée (A3, P1, T4-6). |
| `LOT-14-opportunities` | **MORTE** | `/opportunities` livrée (A4, P2d, T4-1). |
| `LOT-15-analysis` | **MORTE** | `/analysis` livrée (A4, P2b, T4-5). |
| `LOT-16-options` | **MORTE** | `/options` livrée (A5, T4-6). |
| `LOT-17-simulator` | **MORTE** | `/simulator` livrée (A5, T4-6). |
| `LOT-18-portfolio` | **MORTE** | `/portfolio` livrée (A6, P4, T4-2). |
| `LOT-19-follow-up` | **MORTE comme page, VIVANTE comme contrat de module** | `/follow-up` absorbée par `/catalysts` ; la question, les états et les critères restent le contrat du module de revue (bandeau de `pages/09-follow-up.md`). Doit devenir une section de la fiche Catalyseurs. |
| `LOT-20-performance` | **MORTE comme page, VIVANTE comme contrat de module** | Module Performance de Portefeuille ; TWR/XIRR/drawdown/heatmap/export CSV préservés (`PAGE_ARBITRATION.md`). |
| `LOT-21-vertex-ai` | **MORTE comme page, VIVANTE comme contrat de panneau** | `/ai` absorbée dans l'inspecteur ; B-05 (fournisseur IA) toujours ouvert, l'IA reste `DISABLED`. |
| `LOT-22-system` | **MORTE comme page, VIVANTE comme périmètre** | Renommée Sources & Rapports ; le volet **ÉTENDRE** (lignage, incidents, rapports) « n'est ni livré ni simulé » (`NOW.md`, LOT-07). |
| `LOT-23-quality-security` | **PARTIELLEMENT VIVANTE** | Chaos, traçabilité (24/30), WCAG mesuré. Restent : **mutation testing sans score** (mutmut retiré), **1.4.10 reflow non conforme**, **revue lecteur d'écran non faite**, **latence API jamais mesurée**. |
| `LOT-24-release` | **VIVANTE** | Aucune release candidate, aucune restauration sur la machine cible, aucune séance de soak. Le plus gros reste à faire. |
| `LOT-25-official-source-adapters` | **MORTE** | `apps/edge-official` livré (SEC, FRED, OpenFIGI, BCE, BNS) ; FMP et ORATS désactivés. |
| `LOT-26-sec-edgar-pit` | **MORTE** | `apps/worker/src/vertex_worker/sec_fundamentals.py`, route `/sources/sec/{instrument}/fundamentals`, `tools/run_sec_edgar.py`. |

**Bilan** : **19 mortes**, **4 mortes-comme-page mais porteuses d'un contrat de module à préserver** (19, 20, 21, 22), **4 vivantes ou partiellement vivantes** (04, 05, 23, 24).
**Recommandation** : archiver les 27 fiches sous `.claude/lots/archive/` en reportant d'abord (a) les contrats de module des lots 19–22 dans les fiches produit hôtes (Catalyseurs, Portefeuille, inspecteur, Sources & Rapports), (b) le reste ouvert des lots 04, 05, 23, 24 dans `DEBT.md` et `BLOCKERS.md`, puis remplacer le dossier par le programme unique `docs/07-delivery/PROGRAM.md`. Le protocole `EXÉCUTE LOT NN` de `CLAUDE.md` devra alors pointer vers ce programme.

---

## 7. `NOW.md` : ce qui est vivant, ce qui est journal

`NOW.md` fait 2 616 lignes en deux blocs nettement distincts :
- **lignes 3–568** : un bloc YAML d'« état courant » — mais dont l'en-tête est faux (`phase: post_merge_requalification_r2`, `main_head_observed: ecc50c1`, `prochaine_commande: "ATTENDRE LA REVUE CODEX DE R1 (PR #17)"`) alors que HEAD est `b50e09e` du 2026-09-04 ;
- **lignes 570–2616** : ~30 sections `## SESSION AAAA-MM-JJ — LOT …`, chacune avec « Ce qui est livré », « Mesuré sur cette machine », « Transmis, non corrigé ici ». **C'est un journal**, et il doit partir tel quel dans `docs/60-reports/journal/`.

### 7.1 Information VIVANTE qui doit survivre à la réduction

**A. Carte des destinations et redirections** (l. 336–362)
`pages_reelles` (12 + `/auth`), `pages_non_implementees: []`, `destinations_cibles_manquantes: []`, `redirections_permanentes` (4). → **destination : `docs/01-product/DESTINATIONS.md`**, où c'est une norme et non un état.

**B. Les 12 écarts déclarés** (l. 363–389) — le cœur de l'honnêteté du produit :
WCAG 1.4.10 non conforme (384 px de débordement à 200 %) ; revue lecteur d'écran non faite ; latence API jamais mesurée ; tables non virtualisées ; provenance et signature de release non faisables ; mutation testing sans score (6 017 mutants tous ignorés, cause écrite) ; 6 interdictions sur 30 non prouvées par un test ; Cloudflare non déployé, Compose jamais exécuté ; « **RIEN de ces données réelles n'existe en CI** ». → **destination : `DEBT.md`** (registre des limites de preuve, qui les porte déjà en partie — dédoublonner, ne pas recopier).

**C. Blocages humains** (l. 390–396) : B-02, B-03, B-04, B-05 + le connecteur MCP IBKR non autorisé. → **destination : `BLOCKERS.md`**, qui est leur propriétaire déclaré (« Ce fichier ne contient pas de décision humaine ; celles-ci restent dans `BLOCKERS.md` » — en-tête de `DEBT.md`).

**D. Trois régimes de collecte IBKR** (l. 427–460) — information opérationnelle unique, écrite nulle part ailleurs : `client_id` 71/72/73 distincts ; temps réel plafonné à `MAX_UNIVERSE_SIZE = 24` (limite de lignes ~100/compte) ; historique 60 req/10 min → ~2 h 50 pour 1 000 titres ; découverte 50 lignes/scan à 1 scan/s ; « des milliers d'instruments en TEMPS RÉEL simultané » est **impossible** chez IBKR. → **destination : `docs/08-runbooks/IBKR_SETUP.md`** (+ renvoi depuis `docs/04-integrations/IBKR.md`).

**E. Droits IBKR prouvés et non concluants** (l. 501–514, sonde du 2026-08-31) : actions US temps réel (bid/ask/last/volume) ; Greeks options en direct (tick 13) ; HV 30 j (23), IV 30 j (24) ; volume moyen d'options (87) ; définition de chaîne (20 bourses, 17 échéances, 107 strikes) ; **non concluants** : bid/ask/last de l'option, open interest, volume call/put du sous-jacent (marché fermé) ; **`not_entitled: AUCUN`**. → **destination : `docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md`** — c'est la seule mesure réelle de droits du projet, et elle est aujourd'hui enterrée dans un fichier d'état.

**F. Ce que chaque page affiche réellement** (l. 461–500) : pages en population `REAL` (Marchés, Aujourd'hui, Analyse 251 barres, Opportunités) ; pages **sans données** avec leur cause exacte — Options (« aucun collecteur de chaîne COTÉE n'existe »), Calendrier (`calendar.py` n'admet que `synthetic-calendar-event/` alors que l'adaptateur émet `ibkr.corporate-events/1`), Système (sonde jamais lancée avec `--persist`), Portefeuille (aucune transaction saisie — absence normale). → **destination : `DEBT.md`** pour les trois premières (défauts) et **`docs/60-reports/2026-09-04-inventaire-modules.md`** pour la vue d'ensemble.

**G. Le budget de fraîcheur au relais** (l. 272–292) : propriétaire unique `apps/api/src/vertex_api/freshness.py` ; TTL lus dans `vertex_core.data.freshness`, jamais écrits dans l'API ; politique par relais (`news_attention`, `daily_bar`, `option_surface`, `portfolio_mark`) ; les capacités publient leur âge **sans budget**, motif écrit. Et le défaut ouvert : « la gate INTERNE affirme encore `FRESH_AND_COHERENT` à +71 h alors que sa fenêtre vaut 48 h ». → **destination : `docs/03-domain/DATA_QUALITY.md`** (norme) + `DEBT.md` (le défaut).

**H. Mesures de référence** (l. 316–335) : bundle initial 118 317 octets / budget 307 200 ; ECharts 205 ko et Lightweight 53 ko hors charge initiale ; 3 moteurs de navigateur verts (665 passed, 2 skipped) ; 168 cas d'accessibilité. → **destination : `docs/60-reports/2026-09-04-mesures.md`**, avec la date et la commande. Ces chiffres **périment** : ils n'ont pas leur place dans une norme, et `NOW.md` avoue lui-même que « **SEPT chiffres de ce registre se sont révélés faux, dont un trois fois** ».

**I. Démarrage local et refus vérifiés** (l. 307–315) : `bash tools/start_local.sh` ; les deux ports refusent la connexion depuis l'adresse non-loopback ; refus sur DSN absent (code 2), sur base déjà journalisée, sur nom de base de test. → **destination : `docs/08-runbooks/START_LOCAL.md`**, qui est déjà exécutable et à jour.

**J. Sonde d'entitlements** (l. 293–306) : commande `python3 tools/probe_entitlements.py --symbol <X> --dry-run` ; refus vérifiés (identité ambiguë → arrêt, jamais « le premier » ; `client_id` nul refusé ; code 10197 → `ERROR`, jamais `NOT_ENTITLED`). → **destination : `docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md`**.

**K. Écart Cloudflare non couvert par une porte** (l. 515–521) : « `tools/check_notices.py` n'inventorie que `uv.lock` et `apps/web/pnpm-lock.yaml` : le verrou du Worker n'est **PAS** couvert par la porte `release/notices` ». → **destination : `DEBT.md`** (l'écart est déjà écrit dans `THIRD_PARTY_NOTICES.md`, à recouper).

**L. Deux décisions d'utilisateur en attente** enfouies dans un champ nommé `ancienne_prochaine_commande_lot_14` (l. 543-555) : **le barème de SÉVÉRITÉ de la page Risques** et **le périmètre affiché** (huit indices mondiaux, `profiles.RISK_PERIMETER`). Ce sont des blocages produit vivants, rangés sous un nom qui dit « ancienne ». → **destination : `BLOCKERS.md`** (nouvelles entrées B-06 et B-07).

### 7.2 Ce qui est du journal, et rien d'autre

- l. 36–156 `lots_de_cette_session` (LOT-04 → LOT-14, récits) ;
- l. 157–193 `mesures_de_cette_session` (comptages Playwright 405 → 399 → 417 → 432 …) ;
- l. 194–271 `active_work`, `completed`, `audits` (numéros de CI #98…#107, PR #11…#13) ;
- l. 522–568 les quatre champs `ancienne_prochaine_commande_*` et `prochaine_commande` périmée ;
- l. 570–2616 les ~30 sections `## SESSION …` en entier.

### 7.3 `NOW.md` cible

Un fichier de **80 lignes au maximum**, en YAML strict, avec exactement : `head` (SHA + date), `branche`, `lot_actif`, `etat`, `pages_reelles`, `redirections`, `blocages_ouverts` (renvoi `BLOCKERS.md`), `dette_ouverte` (renvoi `DEBT.md`), `derniere_mesure` (renvoi au rapport daté), `prochaine_commande`. Tout le reste renvoie par lien. Le format compact « lot, état, branche, fichiers, tests, risque, blocage, prochaine commande » qu'impose déjà `CLAUDE.md` pour Remote Control est exactement cette forme : **`NOW.md` viole aujourd'hui la règle de son propre `CLAUDE.md`**, qui demande « `STATUT` : huit lignes maximum ».

---

## 8. Ordre de traitement recommandé

1. **Geler la vérité des destinations** : créer `docs/01-product/DESTINATIONS.md` depuis la table de `PAGE_ARBITRATION.md` + `pages.ts`, puis corriger `INFORMATION_ARCHITECTURE`, `NAVIGATION`, `ROUTES`, les deux fiches sans bandeau, `DASHBOARD_COMPOSITION`, `CHART_STANDARD`, `TITANIUM_LEDGER_VISUAL_SYSTEM` (C-01, C-03, C-04, C-13, C-14). Poser une porte de test qui compare `pages.ts` à `DESTINATIONS.md`, comme `canon-v2-docs.test.ts` le fait déjà pour ADR-017.
2. **Une seule valeur de rail** (C-02), puis une porte qui interdit une largeur en dur dans un `.md`.
3. **Écrire la doctrine de l'absence** dans `docs/05-design/ABSENCE_DOCTRINE.md` — c'est la loi 4, elle n'existe qu'en commentaire TSX.
4. **Réduire `NOW.md`** en reportant les blocs A→L, et sortir le journal.
5. **Archiver** les 6 documents clos + les 19 fiches de lot mortes, après extraction.
6. **Un seul programme** (`docs/07-delivery/PROGRAM.md`) et **un seul skill maître** (C-11, C-12).
7. Corriger `REPOSITORY_MAP`, `CALCULATION_CATALOG`, `CI_GATES`, `ACCESSIBILITY`, supprimer `PERFORMANCE_BUDGETS` (C-05, C-06, C-07, C-08, C-09).

**Risque restant** : les points 1 et 6 touchent des documents cités par des commentaires de code (`routes.tsx`, `pages.ts`, `AppShell.tsx` citent `PAGE_ARBITRATION.md` et `FOLDER_BY_FOLDER_PROGRAM.md` par chemin) ; tout déplacement doit être accompagné de la mise à jour de ces renvois, sinon le rangement casse la traçabilité qu'il prétend restaurer.

**Prochaine commande recommandée** : `EXÉCUTE LOT 1 — Remettre le dossier en ordre`, borné aux points 1 à 3 ci-dessus, sur une branche `lot/01-remise-en-ordre-documentaire`.