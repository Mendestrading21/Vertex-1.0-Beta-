# Audit de chirurgie du dépôt — Phase 1

Lecture seule. Aucune suppression, aucun déplacement, aucune dépendance touchée.

Base : `75f14d5`, branche `agent/vertex-repository-surgery`.
Outils : Ruff 0.15.8, Vulture, Knip, Madge, Node 22.22, pnpm 10.33.

## Verdict

**Le dépôt ne présente pas le désordre que la chirurgie visait.** Les quatre
détecteurs classiques de code mort, cycles et dépendances inutiles rendent
**zéro suppression prouvée**. Les seuls candidats survivants sont des exports et
types TypeScript, qui demandent un examen pièce par pièce, pas un passage
d'outil.

La raison est structurelle : ce dépôt est une reconstruction récente, et sa CI
tient déjà dix portes — dont Ruff sans tolérance, mypy `--strict`, frontière
financière, registre des calculs, verrouillage supply-chain, licences et
traçabilité. Ce que la chirurgie devait nettoyer, ces portes l'empêchent
d'entrer.

## Mesures — état initial

| Mesure | Valeur |
|---|---|
| Fichiers suivis | 992 |
| Python | 349 fichiers · 115 720 lignes |
| TypeScript `.ts` | 110 fichiers · 25 244 lignes |
| TypeScript `.tsx` | 176 fichiers · 35 265 lignes |
| Documentation `.md` | 229 fichiers · 29 504 lignes |
| Manifestes `.yaml` | 26 fichiers · 11 711 lignes |
| Dépendances runtime web | 7 |
| devDependencies web | 16 |
| Fichiers > 500 lignes | 71 |
| Cycles de dépendances | **0** |

## Carte du dépôt

| Chemin | Catégorie | Rôle | Fichiers |
|---|---|---|---|
| `packages/python/vertex_core` | CORE | calculs financiers, autorité canonique | — |
| `packages/python/vertex_persistence` | CORE | PostgreSQL, migrations | — |
| `apps/api` | ACTIVE FEATURE | API HTTP, routes, auth, vues snapshot | 79 |
| `apps/worker` | WORKER | analyse, calendrier, opportunités, handlers | 60 |
| `apps/edge-ibkr` | ADAPTER | données de marché IBKR (lecture seule) | 33 |
| `apps/edge-official` | ADAPTER | sources officielles (SEC, FRED, BCE…) | 10 |
| `apps/ingress-tradingview` | ADAPTER | réception de signaux TradingView | 20 |
| `apps/web` | ACTIVE FEATURE | interface React 19 / Vite / TypeScript | 299 |
| `contracts/` | SHARED | JSON Schema et exemples, contrat commun | 13 |
| `manifests/` | INFRASTRUCTURE | 22 manifestes de gouvernance | 22 |
| `tools/` | INFRASTRUCTURE | portes CI exécutables | 37 |
| `infra/` | INFRASTRUCTURE | compose, monitoring, sauvegarde | 14 |
| `docs/` | DOCUMENTATION | 12 sections numérotées `00` → `99` | 151 |
| `research/` | ACTIVE FEATURE | pipelines et notebooks, lecture seule | 8 |
| `design-assets/` | SHARED | icônes et références visuelles | 23 |
| `tradingview/` | ADAPTER | scripts Pine | 5 |
| `.claude/` | DOCUMENTATION | doctrine, lots, skills | 75 |

Aucun dossier `UNKNOWN`. Aucun dossier `LEGACY`. Aucun nom de la liste noire du
brief (`utils-old`, `backup`, `temp`, `final-final`, `components2`…).

## Détection de code mort — résultats

### Python — Ruff : `All checks passed!`

Aucune violation sur l'arbre entier, jeu de règles `E, W, F, I, UP, B` et
au-delà. **F401 fait partie du jeu : il n'existe aucun import inutilisé.** La
porte CI `Q1` l'exige déjà sans tolérance.

### Python — Vulture : 271 candidats, **0 actionnable**

Les 271 candidats à 60 % de confiance sont dominés par des faux positifs
structurels : handlers de routes FastAPI (`post_login_verify`, `get_health`),
`model_config` Pydantic, champs de schémas de réponse (`registered`,
`logged_out`), méthodes de validation.

Les **19 candidats à 100 %** ont été relus un par un. **Aucun n'est
supprimable :**

| Candidat | Réalité |
|---|---|
| `clean_database`, `migrated_database` (7×) | fixtures pytest demandées pour leur effet de bord |
| `exc_type`, `tb` | signature de `__exit__` |
| `req`, `fp`, `newurl` | signature du gestionnaire de redirection `urllib` |
| `underlyingSymbol`, `futFopExchange`, `underlyingSecType` | noms d'attributs de l'API IBKR sur un objet de test |
| `case`, `conn`, `executemany`, `parent_names` | usages indirects dans les tests |

Vulture est ici **100 % bruit**. Il produit des candidats ; il ne décide pas.

### TypeScript — Madge : **aucun cycle**

265 fichiers traités. `✔ No circular dependency found!`

### TypeScript — Knip : 1 faux positif majeur, 112 candidats à examiner

**`geist` déclaré « dépendance inutilisée » — c'est FAUX.**
`src/styles/fonts.css` charge les fichiers depuis
`node_modules/geist/dist/fonts/…woff2`. Knip ne suit pas les `url()` CSS vers
`node_modules`. **La supprimer casserait les polices de toute l'interface.**
C'est le cas d'école que le brief interdit : ne jamais supprimer sur la seule
parole d'un outil.

`pg_isready` et `service`, signalés « binaires non listés », sont des binaires
système appelés par la configuration e2e. Faux positifs.

Restent **46 exports** et **66 types exportés** sans consommateur détecté. Ce
sont les **seuls candidats réels** du dépôt. Ils ne sont pas traités ici :
beaucoup sont des interfaces de vue (`GateView`, `AdviceView`,
`SecCoverageView`…) qui peuvent constituer un contrat documenté volontairement
exporté. Chacun demande une preuve individuelle.

## Doublons

`echarts` **et** `lightweight-charts` coexistent — le cas « deux paquets qui
font la même chose » du brief. Vérification faite : **ce n'est pas une
duplication.**

- `echarts` — 9 fichiers : treemap de marché, heatmap mensuelle, courbe de
  performance, payoff du simulateur ;
- `lightweight-charts` — 1 fichier : `CandleChart.tsx`, chandeliers financiers,
  la spécialité de cette bibliothèque.

Les remplacer l'un par l'autre dégraderait le rendu. **KEEP les deux**, raison
documentée.

## Fichiers volumineux

71 fichiers dépassent 500 lignes. Les cinq plus gros :

| Fichier | Lignes | Nature |
|---|---|---|
| `apps/web/src/api/schema.d.ts` | 4 180 | **généré** (`openapi-typescript`) — ne pas découper |
| `apps/api/src/vertex_api/snapshot_views.py` | 2 658 | à examiner |
| `apps/api/tests/test_ai_explain.py` | 2 551 | test |
| `apps/api/src/vertex_api/ai_explain.py` | 2 271 | à examiner |
| `apps/worker/src/vertex_worker/analysis.py` | 2 268 | à examiner |

Le brief l'exige : découper uniquement si plusieurs responsabilités réelles
existent. Non tranché à ce stade.

## Classement des candidats

| Classe | Nombre | Détail |
|---|---|---|
| SAFE | **0** | aucun candidat n'a survécu à la vérification |
| CAREFUL | 112 | 46 exports + 66 types TypeScript, preuve individuelle requise |
| RISKY | — | `vertex_core`, adaptateurs IBKR / TradingView / SEC / FRED, migrations, auth : non touchés |
| UNKNOWN | 0 | tout dossier est expliqué |

## Conflit de gouvernance à trancher

Le `CLAUDE.md` de ce dépôt impose des branches `lot/NN-slug`, une PR par lot, et
interdit de commencer un lot sans commande explicite. La branche demandée est
`agent/vertex-repository-surgery`, hors convention. Elle a été créée telle que
demandée ; l'écart est signalé, pas dissimulé.

## Ce que cet audit ne dit pas

- Il n'a **pas** exécuté la suite de tests du dépôt (`pytest`, `vitest`, e2e)
  ni le build : aucune mesure de temps de build ou de bundle n'est fournie.
- Il n'a **pas** audité les 22 manifestes ni les 37 portes CI ligne à ligne.
- Il porte sur des **fichiers, exports et dépendances**, jamais sur la
  justesse des calculs financiers.
- Les 112 candidats TypeScript sont **comptés**, pas jugés.

---

# Phases 7 à 14 — exécution

## Baseline mesurée (`75f14d5`)

| Contrôle | Résultat | Temps |
|---|---|---|
| `pnpm typecheck` | 0 erreur | 9,8 s |
| `pnpm lint` (Biome) | 0 erreur, 1 info préexistante | 0,7 s |
| `pnpm test` (Vitest) | **97 fichiers, 981 tests, tout vert** | 57,1 s |
| `pnpm build` (Vite) | OK | 1,76 s |
| `uv run mypy` (strict) | **0 issue, 143 fichiers** | 14,8 s |
| `uv run pytest` | 1 échec — voir ci-dessous | 96,3 s |
| `ruff check .` | `All checks passed!` | — |
| Bundle | 2,0 Mo · 1 688 ko de JS | — |

**L'échec pytest n'est pas un défaut produit.**
`apps/edge-ibkr/tests/test_denylist.py::test_adapter_satisfies_the_port_protocol`
échoue sur `isinstance(fake, IbkrInformationPort)`. L'environnement local
fournit Python 3.11 ; la cible est 3.13, et `pyproject.toml` documente cet
écart. Preuve indépendante : la CI du dépôt est **verte sur `75f14d5`**, le SHA
exact de cette base ([run 422](https://github.com/Mendestrading21/Vertex-1.0-Beta-/actions/runs/33917758251)).
Le comportement d'`isinstance` sur les protocoles `runtime_checkable` a changé
en 3.12.

## Ce qui a été fait

### Lot 1 — huit symboles morts supprimés

Prouvés par recherche du nom dans **tout le monorepo** : une seule occurrence
chacun, leur propre déclaration. Cinq alias de jetons (`SpaceToken`,
`RadiusToken`, `ShadowToken`, `MotionDurationToken`, `ZIndexToken`),
`CalendarWindowEcho`, `CenterDensity`, `subjectOf`.

Le typecheck a pris la cascade : deux imports (`AiSubject`, `TextDensity`)
devenus orphelins, retirés à leur tour. `AiSubject` reste exporté par
`client.ts` — il appartient au contrat OpenAPI.

### Lots 2 à 4 — soixante-dix symboles rendus privés

Utilisés dans leur propre module, jamais importés ailleurs. Seul le mot-clé
`export` part ; aucun code n'est supprimé.

Le cas le plus net : `decisionApi.ts` et `portfolioApi.ts` exposaient des
fetchers bruts **et** les hooks React Query qui les enveloppent. Seuls les hooks
sont consommés ; les fetchers ne servaient que de `queryFn` sur place. La
couche publique dit désormais ce qu'elle est.

## Avant / après

| Mesure | Avant | Après | Δ |
|---|---:|---:|---:|
| Candidats Knip | 112 | **35** | **−77** |
| — exports inutilisés | 46 | 14 | −32 |
| — types exportés inutilisés | 66 | 21 | −45 |
| Symboles supprimés | — | 8 | — |
| Symboles rendus privés | — | 70 | — |
| Lignes `.ts` | 25 244 | 25 234 | −10 |
| Lignes `.tsx` | 35 265 | 35 262 | −3 |
| Cycles de dépendances | 0 | 0 | = |
| Tests Vitest | 981 verts | **981 verts** | = |
| Bundle JS | 1 688 ko | 1 688 ko | = |
| Build | 1,76 s | ~1,0 s | — |

**Le bundle ne bouge pas, et c'est attendu :** 77 des 78 symboles traités sont
des types ou des symboles restés en place. Les types sont effacés à la
compilation. Ce chantier réduit la surface publique et la charge de lecture,
pas le poids livré. Annoncer un gain de bundle ici aurait été faux.

## Ce qui reste, et pourquoi

**35 candidats Knip conservés délibérément.**

- **~10 types de `src/api/client.ts`** — `SimulationAssumptions`,
  `PortfolioInfo`, `PortfolioLotEntry`, `ImportRowEcho`, `ImportRowError`,
  `AiClaim`, `AiSubject`… Ce sont les miroirs TypeScript du contrat OpenAPI.
  Chacun existe aussi dans `apps/api/openapi.json` et les schémas Python.
  Classe **RISKY** : le contrat commun n'est pas du code mort.
- **Interfaces de vue** (`GateView`, `AdviceView`, `SecCoverageView`,
  `RevisionView`…) — plusieurs sont nommées dans `docs/05-design/refonte/*.md`.
  Elles documentent une forme attendue.

**Knip est aveugle au monorepo.** Lancé sur `apps/web` seul, il a produit
**34 faux positifs sur 112** — des symboles bel et bien référencés par le
Python, l'OpenAPI ou les documents de conception. Et son unique « dépendance
inutilisée », `geist`, est chargée par `fonts.css` depuis `node_modules` :
la supprimer aurait cassé les polices.

**Python : rien à nettoyer.** Ruff passe sans une violation, mypy `--strict`
sans une issue, et les 271 candidats de Vulture sont intégralement des faux
positifs — y compris les 19 à 100 % de confiance, relus un par un.

## Ce que ce chantier n'a pas fait

- **Aucun déplacement de fichier.** La structure existante est cohérente ;
  déplacer aurait été du bruit.
- **Aucun découpage** des 71 fichiers de plus de 500 lignes. Le plus gros
  (`schema.d.ts`, 4 180 lignes) est généré. Les autres demandent une analyse de
  responsabilités qui n'a pas été faite.
- **Aucune dépendance retirée** — les 7 runtime et 16 dev sont toutes
  employées, `echarts` et `lightweight-charts` compris (usages disjoints).
- **Aucun test e2e exécuté** : ils demandent PostgreSQL et un navigateur servi.
- **Aucun test d'intégration Python** (`tests_integration/`) : PostgreSQL réel
  requis.
