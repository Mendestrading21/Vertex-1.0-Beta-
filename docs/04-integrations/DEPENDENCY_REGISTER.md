# Registre des dépendances et références officielles

Les versions exactes et hashes sont résolus au LOT-01, puis verrouillés dans `uv.lock`, `pnpm-lock.yaml`, digests d'images et SHA d'Actions. Aucun `latest`. La cible produit est une application web de bureau ; aucune interface mobile ou PWA mobile n'entre dans la version 1.0 Beta.

## Socle adopté

| Brique | Rôle | Ligne cible | Licence | Source officielle |
|---|---|---:|---|---|
| Python | runtime financier | 3.13 ; test 3.14 en CI | PSF | https://www.python.org/downloads/ |
| uv | workspace/lock Python | stable épinglée | MIT/Apache-2.0 | https://docs.astral.sh/uv/ |
| FastAPI | REST, SSE, OpenAPI | stable épinglée | MIT | https://github.com/fastapi/fastapi |
| Pydantic | contrats stricts | v2 | MIT | https://github.com/pydantic/pydantic |
| SQLAlchemy | transactions SQL | v2 | MIT | https://github.com/sqlalchemy/sqlalchemy |
| Alembic | migrations | stable | MIT | https://github.com/sqlalchemy/alembic |
| Psycopg | driver PostgreSQL | v3 | LGPL-3.0 | https://github.com/psycopg/psycopg |
| HTTPX | client HTTP strict pour sources officielles | stable épinglée | BSD-3-Clause | https://github.com/encode/httpx |
| py_webauthn | vérification serveur des cérémonies WebAuthn/passkey (LOT-09) ; adopter | 3.0.0 épinglée | BSD-3-Clause | https://github.com/duo-labs/py_webauthn |
| OpenTelemetry SDK | traces/métriques corrélées | stable épinglée | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python |
| Prometheus client | métriques locales bornées | stable épinglée | Apache-2.0 | https://github.com/prometheus/client_python |
| PostgreSQL | vérité transactionnelle/outbox | 18 | PostgreSQL | https://www.postgresql.org/docs/current/ |
| DuckDB + Parquet | recherche locale | stable | MIT | https://github.com/duckdb/duckdb |
| QuantLib + SWIG | options/oracle | stable | BSD-3-Clause | https://github.com/lballabio/QuantLib |
| NumPy/SciPy | numérique/solveurs | stable | BSD | https://github.com/scipy/scipy |
| Polars | moteur DataFrame des chemins chauds, lazy/streaming | stable épinglée | MIT | https://github.com/pola-rs/polars |
| PyArrow | format colonne, IPC et interop Parquet/Arrow | stable épinglée | Apache-2.0 | https://github.com/apache/arrow |
| pandas | interop avec l'écosystème quant ; pas moteur par défaut des chemins chauds | stable | BSD-3-Clause | https://github.com/pandas-dev/pandas |
| exchange_calendars | séances, jours fériés et clôtures spéciales | stable épinglée | Apache-2.0 | https://github.com/gerrymanoim/exchange_calendars |
| scikit-learn | calibration/baselines | stable | BSD-3-Clause | https://github.com/scikit-learn/scikit-learn |
| statsmodels | diagnostics/séries | stable | BSD-3-Clause | https://github.com/statsmodels/statsmodels |
| CVXPY | optimisation contrainte | stable | Apache-2.0 | https://github.com/cvxpy/cvxpy |
| PyPortfolioOpt | portfolio benchmarké | stable | MIT | https://github.com/PyPortfolio/PyPortfolioOpt |
| ib_async | adaptateur TWS async | stable épinglée | BSD-2-Clause ; notice à revérifier au pin | https://github.com/ib-api-reloaded/ib_async |
| Node.js | toolchain web | 24 LTS | MIT | https://nodejs.org/en/about/previous-releases |
| pnpm | workspace JS | stable épinglée | MIT | https://github.com/pnpm/pnpm |
| React | interface | 19.2 | MIT | https://react.dev/versions |
| TypeScript | typage strict | stable | Apache-2.0 | https://github.com/microsoft/TypeScript |
| Vite | build de l'application web bureau | 8, patch supporté | MIT | https://vite.dev/releases |
| TanStack Query | cache serveur | stable | MIT | https://github.com/TanStack/query |
| TanStack Table/Virtual | tables longues | stable | MIT | https://github.com/TanStack/table |
| Radix Primitives | comportements UI | stable | MIT | https://github.com/radix-ui/primitives |
| Lucide React | icônes UI cohérentes et accessibles | stable épinglée | ISC | https://github.com/lucide-icons/lucide |
| ECharts | visualisations analytiques | stable | Apache-2.0 | https://github.com/apache/echarts |
| Lightweight Charts | prix/chandeliers | stable | Apache-2.0 + attribution | https://github.com/tradingview/lightweight-charts |
| Geist Sans/Mono | typographie interface et données | fichiers vérifiés et épinglés | OFL-1.1 | https://github.com/vercel/geist-font |
| openapi-typescript/fetch | client généré | stable | MIT | https://openapi-ts.dev/ |
| Cloudflare Workers/Queues | ingress TV | stable | service | https://developers.cloudflare.com/queues/ |

Polars et PyArrow sont adoptés uniquement après benchmarks sur les charges Vertex et tests différentiels. Les frontières vers pandas restent explicites : conversion tardive pour une bibliothèque qui l'exige, puis retour immédiat vers un contrat Arrow/Polars.

## Tests et qualité

| Outil | Usage | Licence | Source |
|---|---|---|---|
| Ruff | format/lint Python | MIT | https://github.com/astral-sh/ruff |
| mypy | types Python | MIT | https://github.com/python/mypy |
| pytest | tests Python | MIT | https://github.com/pytest-dev/pytest |
| Hypothesis | propriétés financières | MPL-2.0 | https://github.com/HypothesisWorks/hypothesis |
| Testcontainers Python | intégration PostgreSQL | Apache-2.0 | https://github.com/testcontainers/testcontainers-python |
| Biome + tsc | format/lint/types web | MIT/Apache-2.0 | https://github.com/biomejs/biome |
| Vitest | tests web | MIT | https://github.com/vitest-dev/vitest |
| Storybook | états/composants | MIT | https://github.com/storybookjs/storybook |
| Playwright | E2E multi-navigateurs | Apache-2.0 | https://github.com/microsoft/playwright |
| axe-core | accessibilité auto | MPL-2.0 | https://github.com/dequelabs/axe-core |
| mutmut | mutation Python | BSD-3-Clause | https://github.com/boxed/mutmut |
| Locust | charge API | MIT | https://github.com/locustio/locust |
| Lighthouse CI | budgets web | Apache-2.0 | https://github.com/GoogleChrome/lighthouse-ci |

## Sécurité/supply chain

| Outil | Décision | Source |
|---|---|---|
| GitHub CodeQL/dependency review | adopter si disponible | https://docs.github.com/en/code-security |
| Gitleaks CLI | adopter, pas l'Action sous EULA sans revue | https://github.com/gitleaks/gitleaks |
| pip-audit | adopter | https://github.com/pypa/pip-audit |
| OSV-Scanner | adopter | https://github.com/google/osv-scanner |
| Syft + Grype | SBOM + vulnérabilités | https://github.com/anchore/syft |
| Cosign | signatures keyless | https://github.com/sigstore/cosign |
| Trivy | différer ; incident supply-chain 2026 à prendre en compte | https://github.com/aquasecurity/trivy/security/advisories/GHSA-69fq-xp46-6x23 |

## Recherche contrôlée, jamais autorité de décision

| Projet | Statut 1.0 Beta | Licence | Source officielle |
|---|---|---|---|
| River | environnement shadow/recherche pour apprentissage en flux et dérive ; aucune sortie directement exposée comme décision | BSD-3-Clause | https://github.com/online-ml/river |
| ruptures | recherche hors ligne sur points de rupture ; promotion seulement après protocole OOS | BSD-2-Clause | https://github.com/deepcharles/ruptures |
| arch | recherche hors ligne GARCH/volatilité | NCSA | https://github.com/bashtage/arch |
| MAPIE | recherche sur intervalles conformes et contrôle du risque ; pas de promesse de couverture hors hypothèses testées | BSD-3-Clause | https://github.com/scikit-learn-contrib/MAPIE |

Ces paquets ne sont pas des dépendances runtime de production. Toute promotion suit le registre des modèles, les tests point-in-time, le walk-forward purgé, la calibration et une phase shadow mesurée.

## Références, pas dépendances runtime

| Projet | Usage autorisé | Licence/raison |
|---|---|---|
| QuantConnect LEAN | oracle de backtest/réalisme | Apache-2.0 ; ne pas créer un second moteur |
| NautilusTrader | architecture event/replay | LGPL-3.0-only ; revue avant intégration |
| Microsoft Qlib | sandbox recherche | MIT ; données d'exemple non production |
| Riskfolio-Lib | benchmarks risque | BSD-3-Clause ; grande surface |
| vectorbt | exclu runtime/redistribution | Apache 2.0 + Commons Clause |
| TimescaleDB | différé après benchmark | licence mixte Apache/Timescale |
| Redis/Celery | différé | PostgreSQL outbox suffit d'abord |

## Différé hors cible 1.0 Beta

- Tailscale Serve, l'interface mobile, la navigation mobile et une PWA mobile sont différés. Ils ne doivent pas influer sur les composants ou critères de recette bureau.
- Claude Code Remote Control peut servir à piloter Claude depuis un téléphone, mais reste un outil d'orchestration externe : il ne transforme pas Vertex en produit mobile. Source : https://docs.anthropic.com/en/docs/claude-code/remote-control
- Aucune bibliothèque d'informatique quantique n'est retenue. « Quantitatif » désigne ici des modèles statistiques, numériques et probabilistes validés ; il n'existe aucune garantie de précision parfaite.

## Règle d'ajout

Paquet officiel publié → licence/mainteneur vérifiés → version et hash → dépendances transitives → wrapper interne → tests différentiels/propriétés → notice tierce. Aucun clone/copier-coller de dépôt tiers.
