# Carte des sources officielles

Cette liste est le point de départ de Claude au LOT-01. Elle ne remplace pas la vérification des versions, licences, droits du compte et limites le jour de l'installation. Un lien communautaire est une référence, jamais l'autorité d'un protocole ou d'un droit de données.

## IBKR

| Besoin | Source | Usage |
|---|---|---|
| TWS API | https://ibkrcampus.com/campus/ibkr-api-page/twsapi-doc/ | Autorité protocoles, market data, options, scanner, news et WSH |
| Installation TWS/Gateway | https://www.interactivebrokers.com/docs/tws-api/doc/download-tws-or-ib-gateway/download-tws-or-ib-gateway | Binaire officiel uniquement |
| Adaptateur async | https://github.com/ib-api-reloaded/ib_async | Wrapper étroit, version/hash/licence audités |

Les droits visibles dans TWS sont testés séparément par capacité API. Aucun endpoint ordre, compte, position, P&L ou exécution n'est enveloppé.

## TradingView

| Besoin | Source | Usage |
|---|---|---|
| Webhooks | https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/ | Contraintes et livraison d'alertes |
| Données Pine `request.*()` | https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/ | Données ciblées finance/macro/événements |
| Limites Pine | https://www.tradingview.com/pine-script-docs/writing/limitations/ | Budget de requêtes et calcul |
| Export graphique | https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/ | CSV manuel avec provenance |
| Watchlist | https://www.tradingview.com/support/solutions/43000487233-how-to-import-or-export-a-watchlist/ | TXT manuel idempotent |
| Screener | https://www.tradingview.com/support/solutions/43000474432-how-to-export-screener-data/ | CSV manuel actions/ETF |

L'interface News Flow/Calendars n'est pas automatisée sans API officielle explicitement disponible au plan du compte.

## Sources primaires

| Domaine | Source | Usage |
|---|---|---|
| Filings et faits US | https://www.sec.gov/search-filings/edgar-application-programming-interfaces | Submissions et Company Facts avec politique SEC |
| Données macro | https://fred.stlouisfed.org/docs/api/fred/ | Séries et métadonnées FRED |
| Vintages macro | https://fred.stlouisfed.org/docs/api/fred/realtime_period.html | Point-in-time ALFRED/realtime periods |
| Données zone euro | https://data.ecb.europa.eu/help/api/data | Séries officielles BCE, sélectionnées par flow et clé |
| Données suisses | https://data.snb.ch/en/help_api | Cubes officiels BNS, sélectionnés explicitement |
| Identifiants | https://www.openfigi.com/api/documentation | Candidats FIGI, sans résolution automatique des ambiguïtés |
| Horaires de marché | https://www.nyse.com/markets/hours-calendars | Référence NYSE, complétée par calendrier instrument/exchange |

Les cinq adaptateurs correspondants vivent dans `apps/edge-official`. Leur
configuration et leur frontière actuelle sont décrites dans
`OFFICIAL_SOURCE_ADAPTERS.md`.

Les relations investisseurs et émetteurs restent des liens primaires ; un connecteur automatique exige robots/CGU/licence, schéma et tests dédiés.

## Architecture et runtime

| Brique | Source officielle |
|---|---|
| Python | https://www.python.org/downloads/ |
| uv | https://docs.astral.sh/uv/ |
| FastAPI | https://fastapi.tiangolo.com/ |
| PostgreSQL | https://www.postgresql.org/docs/current/ |
| Node LTS | https://nodejs.org/en/about/previous-releases |
| React | https://react.dev/versions |
| Vite | https://vite.dev/releases |
| Cloudflare Queues pull | https://developers.cloudflare.com/queues/configuration/pull-consumers/ |

La cible 1.0 Beta est une application web de bureau. Tailscale Serve, l'interface mobile et la PWA mobile sont différés.

## Données et calcul quantitatif

| Projet | Décision | Source |
|---|---|---|
| Polars | chemins chauds DataFrame lazy/streaming | https://github.com/pola-rs/polars |
| Apache Arrow/PyArrow | format colonne et interop mémoire/Parquet | https://github.com/apache/arrow |
| pandas | interop uniquement, pas chemin chaud par défaut | https://github.com/pandas-dev/pandas |
| QuantLib | moteur/oracle options | https://github.com/lballabio/QuantLib |
| SciPy | solveurs numériques | https://github.com/scipy/scipy |
| CVXPY | optimisation contrainte | https://github.com/cvxpy/cvxpy |
| exchange_calendars | calendriers de plus de 50 exchanges, à vérifier contre sources primaires | https://github.com/gerrymanoim/exchange_calendars |
| scikit-learn | calibration/baselines | https://github.com/scikit-learn/scikit-learn |
| River | shadow/recherche streaming et dérive | https://github.com/online-ml/river |
| ruptures | recherche hors ligne sur changements de régime | https://github.com/deepcharles/ruptures |
| arch | recherche hors ligne sur volatilité | https://github.com/bashtage/arch |
| MAPIE | recherche sur intervalles conformes | https://github.com/scikit-learn-contrib/MAPIE |
| LEAN | oracle de recherche, pas runtime | https://github.com/QuantConnect/Lean |

River n'est pas une autorité de décision. ruptures, arch et MAPIE restent hors runtime de production jusqu'à validation et promotion formelle. Aucune bibliothèque d'informatique quantique n'est autorisée dans cette cible.

## Interface de bureau

| Projet | Décision | Source officielle |
|---|---|---|
| Radix Primitives | primitives et comportements accessibles | https://www.radix-ui.com/primitives/docs/overview/accessibility |
| TanStack Table | modèles de tables longues | https://tanstack.com/table/latest |
| Lucide React | système d'icônes SVG | https://lucide.dev/guide/packages/lucide-react |
| Lightweight Charts | chandeliers | https://github.com/tradingview/lightweight-charts |
| Apache ECharts | visualisations analytiques | https://github.com/apache/echarts |
| ECharts ARIA | descriptions accessibles des graphiques analytiques | https://echarts.apache.org/handbook/en/best-practices/aria/ |
| Geist Sans/Mono | typographie interface et données | https://github.com/vercel/geist-font |

## Livraison sûre

| Contrôle | Source |
|---|---|
| Actions immuables et runners | https://docs.github.com/en/actions/reference/security/secure-use |
| CodeQL | https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql |
| Dependency review | https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-dependency-review |
| Claude Code | https://docs.anthropic.com/en/docs/claude-code/setup |
| Skills Claude Code | https://docs.anthropic.com/en/docs/claude-code/skills |
| Sous-agents Claude Code | https://docs.anthropic.com/en/docs/claude-code/sub-agents |
| Claude Code Remote Control | https://docs.anthropic.com/en/docs/claude-code/remote-control |
| Plugins officiels Claude Code | https://code.claude.com/docs/en/discover-plugins |
| Skill officiel `frontend-design` | https://github.com/anthropics/claude-code/tree/main/plugins/frontend-design |
| Plugin officiel `code-review` | https://github.com/anthropics/claude-code/tree/main/plugins/code-review |
| Plugin officiel `security-guidance` | https://github.com/anthropics/claude-code/tree/main/plugins/security-guidance |
| Action officielle de revue sécurité | https://github.com/anthropics/claude-code-security-review |
| Skill shadcn/ui | https://ui.shadcn.com/docs/skills |
| GitHub CLI | https://cli.github.com/ |

Remote Control est uniquement un moyen de piloter la session Claude depuis un téléphone ; il ne fait pas partie de l'interface Vertex. Les versions finales sont résolues, épinglées et enregistrées au LOT-01. Aucun dépôt tiers n'est copié dans Vertex.
