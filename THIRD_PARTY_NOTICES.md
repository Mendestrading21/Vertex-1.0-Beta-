# Third-party notices

Ce fichier a deux parties. Les **exigences rédigées** ci-dessous nomment les
obligations connues (textes de licence, fichiers NOTICE, attributions) ; elles
sont tenues à la main. Le **tableau des composants** en fin de fichier est
GÉNÉRÉ depuis `uv.lock` et `apps/web/pnpm-lock.yaml` et vérifié à chaque
exécution de la porte `release` (`tools/check_notices.py`, branchée dans
`.github/workflows/ci.yml` et `tools/run_checks.sh`).

Ce que le tableau garantit : chaque composant des verrous y figure, à la bonne
version, avec une licence SPDX lue dans la métadonnée publiée par PyPI ou npm.
Une licence absente, `UNKNOWN` ou non classée par `manifests/policy.yaml`
BLOQUE la fusion. Ce qu'il ne garantit PAS : ni la véracité de la métadonnée du
distributeur, ni la présence physique des textes de licence et des fichiers
NOTICE, ni la compatibilité des licences entre elles, ni le hash de chaque
composant — les hachages restent dans les verrous. Voir
`docs/99-status/DEBT.md`.

Exigences connues :

- Polars : conserver la licence MIT et l'avis de copyright de la version Python distribuée (https://github.com/pola-rs/polars).
- Apache Arrow/PyArrow : conserver `LICENSE.txt`, `NOTICE.txt` et les notices des dépendances embarquées, sous Apache-2.0 (https://github.com/apache/arrow).
- pandas, utilisé uniquement aux frontières d'interopérabilité : conserver la licence BSD-3-Clause (https://github.com/pandas-dev/pandas).
- TradingView Lightweight Charts : conserver LICENSE/NOTICE et afficher l'attribution/lien TradingView demandé par le projet.
- Apache ECharts : conserver LICENSE/NOTICE et les notices des sous-composants.
- Radix Primitives et TanStack Query/Table/Virtual : conserver leurs licences MIT.
- Lucide React : conserver la licence ISC et les avis associés ; ne pas traiter les icônes comme des logos de marque (https://github.com/lucide-icons/lucide).
- QuantLib : conserver la licence BSD et notices incluses.
- Les polices Geist Sans et Geist Mono : conserver le fichier OFL-1.1 de la
  source Vercel vérifiée (https://github.com/vercel/geist-font).
- axe-core/Hypothesis : enregistrer MPL-2.0 comme dépendances de test.
- Wrangler (outil de déploiement Cloudflare, `apps/ingress-tradingview/worker`) :
  version EXACTE `4.127.1`, publiée le 2026-08-28 sur le registre npm officiel,
  licence `MIT OR Apache-2.0`, `engines.node >= 22.0.0`. C'est un outil de
  DÉPLOIEMENT : le Worker lui-même n'a toujours aucune dépendance d'exécution et
  ses 53 tests de contrat s'exécutent avec `node --test` seul, sans installation.
  Arbre réellement installé : 31 paquets, licences toutes permissives — MIT (23),
  `MIT OR Apache-2.0` (3), Apache-2.0 (3), CC0-1.0 (1), ISC (1) ; aucun copyleft.
  **ÉCART D'INVENTAIRE ASSUMÉ** : `tools/check_notices.py` n'inventorie que
  `uv.lock` et `apps/web/pnpm-lock.yaml`. Le verrou
  `apps/ingress-tradingview/worker/pnpm-lock.yaml` n'est donc PAS couvert par la
  porte `release/notices`, et ces 31 paquets n'apparaissent pas dans le tableau
  généré plus bas. Étendre la porte à ce troisième verrou est un lot à part
  entière ; tant qu'il n'est pas fait, cette entrée est la SEULE trace de ces
  composants. Wrangler n'est requis que pour `wrangler deploy`, bloqué par B-03.

Composants de recherche, seulement s'ils sont installés dans un environnement livré : River (BSD-3-Clause), ruptures (BSD-2-Clause), arch (NCSA) et MAPIE (BSD-3-Clause). Leur présence en recherche ne les autorise pas dans le runtime de production.

Tailscale Serve, l'interface/PWA mobile et toute bibliothèque d'informatique quantique sont différés ou exclus ; ils ne font donc pas partie des composants distribués de Vertex 1.0 Beta. Claude Code Remote Control est un service d'orchestration externe, pas un composant de l'application.

Vertex 1.0 Beta ne publie aujourd'hui **aucun artefact** : ni paquet, ni image,
ni release. Le tableau ci-dessous décrit donc les composants que le produit
EMBARQUERAIT à l'exécution (`runtime`) et ceux qui ne servent qu'à le
construire et le tester (`development`), tels que les verrous les décrivent —
pas le contenu observé d'un artefact livré, puisqu'il n'y en a pas.

<!-- COMPOSANTS-DEBUT (genere par tools/check_notices.py --refresh) -->

Tableau **généré** : ne pas éditer à la main. `python3 tools/check_notices.py --refresh` le régénère depuis `uv.lock`, `apps/web/pnpm-lock.yaml` et `manifests/licenses.yaml` ; la porte `release` échoue s'il diverge.

### Composants distribués (rôle `runtime`)

Atteignables depuis les dépendances non optionnelles des membres du workspace, ou depuis les `dependencies` de `apps/web/package.json`.

| Composant | Version | Licence (SPDX) | Écosystème | Source |
|---|---|---|---|---|
| `@tanstack/query-core` | `5.102.8` | MIT | javascript | https://registry.npmjs.org/@tanstack/query-core/5.102.8 |
| `@tanstack/react-query` | `5.102.8` | MIT | javascript | https://registry.npmjs.org/@tanstack/react-query/5.102.8 |
| `cookie` | `1.1.1` | MIT | javascript | https://registry.npmjs.org/cookie/1.1.1 |
| `echarts` | `6.1.0` | Apache-2.0 | javascript | https://registry.npmjs.org/echarts/6.1.0 |
| `fancy-canvas` | `2.1.0` | MIT | javascript | https://registry.npmjs.org/fancy-canvas/2.1.0 |
| `geist` | `1.7.2` | OFL-1.1 | javascript | https://registry.npmjs.org/geist/1.7.2 |
| `lightweight-charts` | `5.2.1` | Apache-2.0 | javascript | https://registry.npmjs.org/lightweight-charts/5.2.1 |
| `react` | `19.2.8` | MIT | javascript | https://registry.npmjs.org/react/19.2.8 |
| `react-dom` | `19.2.8` | MIT | javascript | https://registry.npmjs.org/react-dom/19.2.8 |
| `react-router` | `7.18.3` | MIT | javascript | https://registry.npmjs.org/react-router/7.18.3 |
| `react-router-dom` | `7.18.3` | MIT | javascript | https://registry.npmjs.org/react-router-dom/7.18.3 |
| `scheduler` | `0.27.0` | MIT | javascript | https://registry.npmjs.org/scheduler/0.27.0 |
| `set-cookie-parser` | `2.7.2` | MIT | javascript | https://registry.npmjs.org/set-cookie-parser/2.7.2 |
| `tslib` | `2.3.0` | 0BSD | javascript | https://registry.npmjs.org/tslib/2.3.0 |
| `zrender` | `6.1.0` | BSD-3-Clause | javascript | https://registry.npmjs.org/zrender/6.1.0 |
| `aeventkit` | `2.1.0` | BSD-3-Clause | python | https://pypi.org/pypi/aeventkit/2.1.0/json |
| `alembic` | `1.19.1` | MIT | python | https://pypi.org/pypi/alembic/1.19.1/json |
| `annotated-doc` | `0.0.5` | MIT | python | https://pypi.org/pypi/annotated-doc/0.0.5/json |
| `annotated-types` | `0.8.0` | MIT | python | https://pypi.org/pypi/annotated-types/0.8.0/json |
| `anyio` | `4.14.2` | MIT | python | https://pypi.org/pypi/anyio/4.14.2/json |
| `cbor2` | `6.1.4` | MIT | python | https://pypi.org/pypi/cbor2/6.1.4/json |
| `cffi` | `2.1.1` | MIT-0 | python | https://pypi.org/pypi/cffi/2.1.1/json |
| `click` | `8.5.0` | BSD-3-Clause | python | https://pypi.org/pypi/click/8.5.0/json |
| `cryptography` | `50.0.1` | Apache-2.0 OR BSD-3-Clause | python | https://pypi.org/pypi/cryptography/50.0.1/json |
| `fastapi` | `0.141.1` | MIT | python | https://pypi.org/pypi/fastapi/0.141.1/json |
| `greenlet` | `3.5.5` | MIT AND PSF-2.0 | python | https://pypi.org/pypi/greenlet/3.5.5/json |
| `h11` | `0.16.0` | MIT | python | https://pypi.org/pypi/h11/0.16.0/json |
| `ib-async` | `2.1.0` | BSD-3-Clause | python | https://pypi.org/pypi/ib-async/2.1.0/json |
| `idna` | `3.19` | BSD-3-Clause | python | https://pypi.org/pypi/idna/3.19/json |
| `mako` | `1.4.1` | MIT | python | https://pypi.org/pypi/mako/1.4.1/json |
| `markupsafe` | `3.0.3` | BSD-3-Clause | python | https://pypi.org/pypi/markupsafe/3.0.3/json |
| `nest-asyncio` | `1.6.0` | BSD-3-Clause | python | https://pypi.org/pypi/nest-asyncio/1.6.0/json |
| `numpy` | `2.4.6` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | python | https://pypi.org/pypi/numpy/2.4.6/json |
| `numpy` | `2.5.2` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | python | https://pypi.org/pypi/numpy/2.5.2/json |
| `psycopg` | `3.3.4` | LGPL-3.0-only | python | https://pypi.org/pypi/psycopg/3.3.4/json |
| `pyasn1` | `0.6.4` | BSD-2-Clause | python | https://pypi.org/pypi/pyasn1/0.6.4/json |
| `pyasn1-modules` | `0.4.2` | BSD-3-Clause | python | https://pypi.org/pypi/pyasn1-modules/0.4.2/json |
| `pycparser` | `3.0` | BSD-3-Clause | python | https://pypi.org/pypi/pycparser/3.0/json |
| `pydantic` | `2.13.5` | MIT | python | https://pypi.org/pypi/pydantic/2.13.5/json |
| `pydantic-core` | `2.46.5` | MIT | python | https://pypi.org/pypi/pydantic-core/2.46.5/json |
| `pyopenssl` | `26.4.0` | Apache-2.0 | python | https://pypi.org/pypi/pyopenssl/26.4.0/json |
| `pyyaml` | `6.0.3` | MIT | python | https://pypi.org/pypi/pyyaml/6.0.3/json |
| `sqlalchemy` | `2.0.52` | MIT | python | https://pypi.org/pypi/sqlalchemy/2.0.52/json |
| `starlette` | `1.6.0` | BSD-3-Clause | python | https://pypi.org/pypi/starlette/1.6.0/json |
| `typing-extensions` | `4.16.0` | PSF-2.0 | python | https://pypi.org/pypi/typing-extensions/4.16.0/json |
| `typing-inspection` | `0.4.4` | MIT | python | https://pypi.org/pypi/typing-inspection/0.4.4/json |
| `tzdata` | `2025.3` | Apache-2.0 | python | https://pypi.org/pypi/tzdata/2025.3/json |
| `uvicorn` | `0.52.4` | BSD-3-Clause | python | https://pypi.org/pypi/uvicorn/0.52.4/json |
| `webauthn` | `3.0.0` | BSD-3-Clause | python | https://pypi.org/pypi/webauthn/3.0.0/json |

### Composants d'outillage et de test (rôle `development`)

Présents dans les verrous, non atteignables depuis un chemin runtime. Ils ne sont pas distribués ; leur licence est vérifiée quand même.

| Composant | Version | Licence (SPDX) | Écosystème | Source |
|---|---|---|---|---|
| `@asamuzakjp/css-color` | `6.0.7` | MIT | javascript | https://registry.npmjs.org/@asamuzakjp/css-color/6.0.7 |
| `@asamuzakjp/dom-selector` | `8.3.2` | MIT | javascript | https://registry.npmjs.org/@asamuzakjp/dom-selector/8.3.2 |
| `@axe-core/playwright` | `4.13.0` | MPL-2.0 | javascript | https://registry.npmjs.org/@axe-core/playwright/4.13.0 |
| `@babel/code-frame` | `7.29.7` | MIT | javascript | https://registry.npmjs.org/@babel/code-frame/7.29.7 |
| `@babel/helper-validator-identifier` | `7.29.7` | MIT | javascript | https://registry.npmjs.org/@babel/helper-validator-identifier/7.29.7 |
| `@babel/runtime` | `7.29.7` | MIT | javascript | https://registry.npmjs.org/@babel/runtime/7.29.7 |
| `@biomejs/biome` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/biome/2.5.11 |
| `@biomejs/cli-darwin-arm64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-darwin-arm64/2.5.11 |
| `@biomejs/cli-darwin-x64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-darwin-x64/2.5.11 |
| `@biomejs/cli-linux-arm64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-linux-arm64/2.5.11 |
| `@biomejs/cli-linux-arm64-musl` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-linux-arm64-musl/2.5.11 |
| `@biomejs/cli-linux-x64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-linux-x64/2.5.11 |
| `@biomejs/cli-linux-x64-musl` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-linux-x64-musl/2.5.11 |
| `@biomejs/cli-win32-arm64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-win32-arm64/2.5.11 |
| `@biomejs/cli-win32-x64` | `2.5.11` | MIT OR Apache-2.0 | javascript | https://registry.npmjs.org/@biomejs/cli-win32-x64/2.5.11 |
| `@bramus/specificity` | `2.4.2` | MIT | javascript | https://registry.npmjs.org/@bramus/specificity/2.4.2 |
| `@csstools/color-helpers` | `6.1.1` | MIT-0 | javascript | https://registry.npmjs.org/@csstools/color-helpers/6.1.1 |
| `@csstools/css-calc` | `3.3.0` | MIT | javascript | https://registry.npmjs.org/@csstools/css-calc/3.3.0 |
| `@csstools/css-color-parser` | `4.2.1` | MIT | javascript | https://registry.npmjs.org/@csstools/css-color-parser/4.2.1 |
| `@csstools/css-parser-algorithms` | `4.0.0` | MIT | javascript | https://registry.npmjs.org/@csstools/css-parser-algorithms/4.0.0 |
| `@csstools/css-syntax-patches-for-csstree` | `1.1.9` | MIT-0 | javascript | https://registry.npmjs.org/@csstools/css-syntax-patches-for-csstree/1.1.9 |
| `@csstools/css-tokenizer` | `4.0.0` | MIT | javascript | https://registry.npmjs.org/@csstools/css-tokenizer/4.0.0 |
| `@exodus/bytes` | `1.15.1` | MIT | javascript | https://registry.npmjs.org/@exodus/bytes/1.15.1 |
| `@jridgewell/sourcemap-codec` | `1.6.0` | MIT | javascript | https://registry.npmjs.org/@jridgewell/sourcemap-codec/1.6.0 |
| `@oxc-project/types` | `0.147.0` | MIT | javascript | https://registry.npmjs.org/@oxc-project/types/0.147.0 |
| `@playwright/test` | `1.56.1` | Apache-2.0 | javascript | https://registry.npmjs.org/@playwright/test/1.56.1 |
| `@redocly/ajv` | `8.11.2` | MIT | javascript | https://registry.npmjs.org/@redocly/ajv/8.11.2 |
| `@redocly/config` | `0.22.0` | MIT | javascript | https://registry.npmjs.org/@redocly/config/0.22.0 |
| `@redocly/openapi-core` | `1.34.19` | MIT | javascript | https://registry.npmjs.org/@redocly/openapi-core/1.34.19 |
| `@rolldown/binding-android-arm-eabi` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-android-arm-eabi/1.2.6 |
| `@rolldown/binding-android-arm64` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-android-arm64/1.2.6 |
| `@rolldown/binding-darwin-arm64` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-darwin-arm64/1.2.6 |
| `@rolldown/binding-darwin-x64` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-darwin-x64/1.2.6 |
| `@rolldown/binding-freebsd-x64` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-freebsd-x64/1.2.6 |
| `@rolldown/binding-linux-arm-gnueabihf` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-arm-gnueabihf/1.2.6 |
| `@rolldown/binding-linux-arm64-gnu` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-arm64-gnu/1.2.6 |
| `@rolldown/binding-linux-arm64-musl` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-arm64-musl/1.2.6 |
| `@rolldown/binding-linux-ppc64-gnu` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-ppc64-gnu/1.2.6 |
| `@rolldown/binding-linux-s390x-gnu` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-s390x-gnu/1.2.6 |
| `@rolldown/binding-linux-x64-gnu` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-x64-gnu/1.2.6 |
| `@rolldown/binding-linux-x64-musl` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-linux-x64-musl/1.2.6 |
| `@rolldown/binding-openharmony-arm64` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-openharmony-arm64/1.2.6 |
| `@rolldown/binding-win32-arm64-msvc` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-win32-arm64-msvc/1.2.6 |
| `@rolldown/binding-win32-x64-msvc` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/@rolldown/binding-win32-x64-msvc/1.2.6 |
| `@rolldown/pluginutils` | `1.0.1` | MIT | javascript | https://registry.npmjs.org/@rolldown/pluginutils/1.0.1 |
| `@standard-schema/spec` | `1.1.0` | MIT | javascript | https://registry.npmjs.org/@standard-schema/spec/1.1.0 |
| `@testing-library/dom` | `10.4.1` | MIT | javascript | https://registry.npmjs.org/@testing-library/dom/10.4.1 |
| `@testing-library/react` | `16.3.3` | MIT | javascript | https://registry.npmjs.org/@testing-library/react/16.3.3 |
| `@testing-library/user-event` | `14.6.6` | MIT | javascript | https://registry.npmjs.org/@testing-library/user-event/14.6.6 |
| `@types/aria-query` | `5.0.4` | MIT | javascript | https://registry.npmjs.org/@types/aria-query/5.0.4 |
| `@types/chai` | `5.2.3` | MIT | javascript | https://registry.npmjs.org/@types/chai/5.2.3 |
| `@types/deep-eql` | `4.0.2` | MIT | javascript | https://registry.npmjs.org/@types/deep-eql/4.0.2 |
| `@types/estree` | `1.0.9` | MIT | javascript | https://registry.npmjs.org/@types/estree/1.0.9 |
| `@types/node` | `22.20.1` | MIT | javascript | https://registry.npmjs.org/@types/node/22.20.1 |
| `@types/react` | `19.2.18` | MIT | javascript | https://registry.npmjs.org/@types/react/19.2.18 |
| `@types/react-dom` | `19.2.5` | MIT | javascript | https://registry.npmjs.org/@types/react-dom/19.2.5 |
| `@vitejs/plugin-react` | `6.1.1` | MIT | javascript | https://registry.npmjs.org/@vitejs/plugin-react/6.1.1 |
| `@vitest/expect` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/expect/4.1.11 |
| `@vitest/mocker` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/mocker/4.1.11 |
| `@vitest/pretty-format` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/pretty-format/4.1.11 |
| `@vitest/runner` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/runner/4.1.11 |
| `@vitest/snapshot` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/snapshot/4.1.11 |
| `@vitest/spy` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/spy/4.1.11 |
| `@vitest/utils` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/@vitest/utils/4.1.11 |
| `agent-base` | `7.1.4` | MIT | javascript | https://registry.npmjs.org/agent-base/7.1.4 |
| `ansi-colors` | `4.1.3` | MIT | javascript | https://registry.npmjs.org/ansi-colors/4.1.3 |
| `ansi-regex` | `5.0.1` | MIT | javascript | https://registry.npmjs.org/ansi-regex/5.0.1 |
| `ansi-styles` | `5.2.0` | MIT | javascript | https://registry.npmjs.org/ansi-styles/5.2.0 |
| `argparse` | `2.0.1` | Python-2.0 | javascript | https://registry.npmjs.org/argparse/2.0.1 |
| `aria-query` | `5.3.0` | Apache-2.0 | javascript | https://registry.npmjs.org/aria-query/5.3.0 |
| `assertion-error` | `2.0.1` | MIT | javascript | https://registry.npmjs.org/assertion-error/2.0.1 |
| `axe-core` | `4.13.0` | MPL-2.0 | javascript | https://registry.npmjs.org/axe-core/4.13.0 |
| `balanced-match` | `1.0.2` | MIT | javascript | https://registry.npmjs.org/balanced-match/1.0.2 |
| `bidi-js` | `1.0.3` | MIT | javascript | https://registry.npmjs.org/bidi-js/1.0.3 |
| `brace-expansion` | `2.1.4` | MIT | javascript | https://registry.npmjs.org/brace-expansion/2.1.4 |
| `chai` | `6.2.2` | MIT | javascript | https://registry.npmjs.org/chai/6.2.2 |
| `change-case` | `5.4.4` | MIT | javascript | https://registry.npmjs.org/change-case/5.4.4 |
| `colorette` | `1.4.0` | MIT | javascript | https://registry.npmjs.org/colorette/1.4.0 |
| `convert-source-map` | `2.0.0` | MIT | javascript | https://registry.npmjs.org/convert-source-map/2.0.0 |
| `css-tree` | `3.2.1` | MIT | javascript | https://registry.npmjs.org/css-tree/3.2.1 |
| `csstype` | `3.2.3` | MIT | javascript | https://registry.npmjs.org/csstype/3.2.3 |
| `data-urls` | `7.0.0` | MIT | javascript | https://registry.npmjs.org/data-urls/7.0.0 |
| `debug` | `4.4.3` | MIT | javascript | https://registry.npmjs.org/debug/4.4.3 |
| `decimal.js` | `10.6.0` | MIT | javascript | https://registry.npmjs.org/decimal.js/10.6.0 |
| `dequal` | `2.0.3` | MIT | javascript | https://registry.npmjs.org/dequal/2.0.3 |
| `detect-libc` | `2.1.2` | Apache-2.0 | javascript | https://registry.npmjs.org/detect-libc/2.1.2 |
| `dom-accessibility-api` | `0.5.16` | MIT | javascript | https://registry.npmjs.org/dom-accessibility-api/0.5.16 |
| `entities` | `8.0.0` | BSD-2-Clause | javascript | https://registry.npmjs.org/entities/8.0.0 |
| `es-module-lexer` | `2.3.2` | MIT | javascript | https://registry.npmjs.org/es-module-lexer/2.3.2 |
| `estree-walker` | `3.0.3` | MIT | javascript | https://registry.npmjs.org/estree-walker/3.0.3 |
| `expect-type` | `1.4.0` | Apache-2.0 | javascript | https://registry.npmjs.org/expect-type/1.4.0 |
| `fast-deep-equal` | `3.1.3` | MIT | javascript | https://registry.npmjs.org/fast-deep-equal/3.1.3 |
| `fdir` | `6.5.0` | MIT | javascript | https://registry.npmjs.org/fdir/6.5.0 |
| `fsevents` | `2.3.2` | MIT | javascript | https://registry.npmjs.org/fsevents/2.3.2 |
| `fsevents` | `2.3.3` | MIT | javascript | https://registry.npmjs.org/fsevents/2.3.3 |
| `html-encoding-sniffer` | `6.0.0` | MIT | javascript | https://registry.npmjs.org/html-encoding-sniffer/6.0.0 |
| `https-proxy-agent` | `7.0.6` | MIT | javascript | https://registry.npmjs.org/https-proxy-agent/7.0.6 |
| `index-to-position` | `1.2.0` | MIT | javascript | https://registry.npmjs.org/index-to-position/1.2.0 |
| `is-potential-custom-element-name` | `1.0.1` | MIT | javascript | https://registry.npmjs.org/is-potential-custom-element-name/1.0.1 |
| `js-levenshtein` | `1.1.6` | MIT | javascript | https://registry.npmjs.org/js-levenshtein/1.1.6 |
| `js-tokens` | `4.0.0` | MIT | javascript | https://registry.npmjs.org/js-tokens/4.0.0 |
| `js-yaml` | `4.3.1` | MIT | javascript | https://registry.npmjs.org/js-yaml/4.3.1 |
| `jsdom` | `30.0.1` | MIT | javascript | https://registry.npmjs.org/jsdom/30.0.1 |
| `json-schema-traverse` | `1.0.0` | MIT | javascript | https://registry.npmjs.org/json-schema-traverse/1.0.0 |
| `lightningcss` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss/1.33.0 |
| `lightningcss-android-arm64` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-android-arm64/1.33.0 |
| `lightningcss-darwin-arm64` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-darwin-arm64/1.33.0 |
| `lightningcss-darwin-x64` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-darwin-x64/1.33.0 |
| `lightningcss-freebsd-x64` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-freebsd-x64/1.33.0 |
| `lightningcss-linux-arm-gnueabihf` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-linux-arm-gnueabihf/1.33.0 |
| `lightningcss-linux-arm64-gnu` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-linux-arm64-gnu/1.33.0 |
| `lightningcss-linux-arm64-musl` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-linux-arm64-musl/1.33.0 |
| `lightningcss-linux-x64-gnu` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-linux-x64-gnu/1.33.0 |
| `lightningcss-linux-x64-musl` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-linux-x64-musl/1.33.0 |
| `lightningcss-win32-arm64-msvc` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-win32-arm64-msvc/1.33.0 |
| `lightningcss-win32-x64-msvc` | `1.33.0` | MPL-2.0 | javascript | https://registry.npmjs.org/lightningcss-win32-x64-msvc/1.33.0 |
| `lru-cache` | `11.5.2` | BlueOak-1.0.0 | javascript | https://registry.npmjs.org/lru-cache/11.5.2 |
| `lz-string` | `1.5.0` | MIT | javascript | https://registry.npmjs.org/lz-string/1.5.0 |
| `magic-string` | `0.30.21` | MIT | javascript | https://registry.npmjs.org/magic-string/0.30.21 |
| `mdn-data` | `2.27.1` | CC0-1.0 | javascript | https://registry.npmjs.org/mdn-data/2.27.1 |
| `minimatch` | `5.1.9` | ISC | javascript | https://registry.npmjs.org/minimatch/5.1.9 |
| `ms` | `2.1.3` | MIT | javascript | https://registry.npmjs.org/ms/2.1.3 |
| `nanoid` | `3.3.18` | MIT | javascript | https://registry.npmjs.org/nanoid/3.3.18 |
| `obug` | `2.1.4` | MIT | javascript | https://registry.npmjs.org/obug/2.1.4 |
| `openapi-typescript` | `7.13.0` | MIT | javascript | https://registry.npmjs.org/openapi-typescript/7.13.0 |
| `parse-json` | `8.3.0` | MIT | javascript | https://registry.npmjs.org/parse-json/8.3.0 |
| `parse5` | `8.0.1` | MIT | javascript | https://registry.npmjs.org/parse5/8.0.1 |
| `pathe` | `2.0.3` | MIT | javascript | https://registry.npmjs.org/pathe/2.0.3 |
| `picocolors` | `1.1.1` | ISC | javascript | https://registry.npmjs.org/picocolors/1.1.1 |
| `picomatch` | `4.0.7` | MIT | javascript | https://registry.npmjs.org/picomatch/4.0.7 |
| `playwright` | `1.56.1` | Apache-2.0 | javascript | https://registry.npmjs.org/playwright/1.56.1 |
| `playwright-core` | `1.56.1` | Apache-2.0 | javascript | https://registry.npmjs.org/playwright-core/1.56.1 |
| `pluralize` | `8.0.0` | MIT | javascript | https://registry.npmjs.org/pluralize/8.0.0 |
| `postcss` | `8.5.26` | MIT | javascript | https://registry.npmjs.org/postcss/8.5.26 |
| `pretty-format` | `27.5.1` | MIT | javascript | https://registry.npmjs.org/pretty-format/27.5.1 |
| `punycode` | `2.3.1` | MIT | javascript | https://registry.npmjs.org/punycode/2.3.1 |
| `react-is` | `17.0.2` | MIT | javascript | https://registry.npmjs.org/react-is/17.0.2 |
| `require-from-string` | `2.0.2` | MIT | javascript | https://registry.npmjs.org/require-from-string/2.0.2 |
| `rolldown` | `1.2.6` | MIT | javascript | https://registry.npmjs.org/rolldown/1.2.6 |
| `saxes` | `6.0.0` | ISC | javascript | https://registry.npmjs.org/saxes/6.0.0 |
| `siginfo` | `2.0.0` | ISC | javascript | https://registry.npmjs.org/siginfo/2.0.0 |
| `source-map-js` | `1.2.1` | BSD-3-Clause | javascript | https://registry.npmjs.org/source-map-js/1.2.1 |
| `stackback` | `0.0.2` | MIT | javascript | https://registry.npmjs.org/stackback/0.0.2 |
| `std-env` | `4.2.0` | MIT | javascript | https://registry.npmjs.org/std-env/4.2.0 |
| `supports-color` | `10.2.2` | MIT | javascript | https://registry.npmjs.org/supports-color/10.2.2 |
| `symbol-tree` | `3.2.4` | MIT | javascript | https://registry.npmjs.org/symbol-tree/3.2.4 |
| `tinybench` | `2.9.0` | MIT | javascript | https://registry.npmjs.org/tinybench/2.9.0 |
| `tinyexec` | `1.3.0` | MIT | javascript | https://registry.npmjs.org/tinyexec/1.3.0 |
| `tinyglobby` | `0.2.17` | MIT | javascript | https://registry.npmjs.org/tinyglobby/0.2.17 |
| `tinyrainbow` | `3.1.1` | MIT | javascript | https://registry.npmjs.org/tinyrainbow/3.1.1 |
| `tldts` | `7.4.11` | MIT | javascript | https://registry.npmjs.org/tldts/7.4.11 |
| `tldts-core` | `7.4.11` | MIT | javascript | https://registry.npmjs.org/tldts-core/7.4.11 |
| `tough-cookie` | `6.0.2` | BSD-3-Clause | javascript | https://registry.npmjs.org/tough-cookie/6.0.2 |
| `tr46` | `6.0.0` | MIT | javascript | https://registry.npmjs.org/tr46/6.0.0 |
| `type-fest` | `4.41.0` | (MIT OR CC0-1.0) | javascript | https://registry.npmjs.org/type-fest/4.41.0 |
| `typescript` | `5.9.3` | Apache-2.0 | javascript | https://registry.npmjs.org/typescript/5.9.3 |
| `undici` | `8.10.0` | MIT | javascript | https://registry.npmjs.org/undici/8.10.0 |
| `undici-types` | `6.21.0` | MIT | javascript | https://registry.npmjs.org/undici-types/6.21.0 |
| `uri-js-replace` | `1.0.1` | MIT | javascript | https://registry.npmjs.org/uri-js-replace/1.0.1 |
| `vite` | `8.2.2` | MIT | javascript | https://registry.npmjs.org/vite/8.2.2 |
| `vitest` | `4.1.11` | MIT | javascript | https://registry.npmjs.org/vitest/4.1.11 |
| `w3c-xmlserializer` | `5.0.0` | MIT | javascript | https://registry.npmjs.org/w3c-xmlserializer/5.0.0 |
| `webidl-conversions` | `8.0.1` | BSD-2-Clause | javascript | https://registry.npmjs.org/webidl-conversions/8.0.1 |
| `whatwg-mimetype` | `5.0.0` | MIT | javascript | https://registry.npmjs.org/whatwg-mimetype/5.0.0 |
| `whatwg-url` | `16.0.1` | MIT | javascript | https://registry.npmjs.org/whatwg-url/16.0.1 |
| `whatwg-url` | `17.1.0` | MIT | javascript | https://registry.npmjs.org/whatwg-url/17.1.0 |
| `why-is-node-running` | `2.3.0` | MIT | javascript | https://registry.npmjs.org/why-is-node-running/2.3.0 |
| `xml-name-validator` | `5.0.0` | Apache-2.0 | javascript | https://registry.npmjs.org/xml-name-validator/5.0.0 |
| `xmlchars` | `2.2.0` | MIT | javascript | https://registry.npmjs.org/xmlchars/2.2.0 |
| `yaml-ast-parser` | `0.0.43` | Apache-2.0 | javascript | https://registry.npmjs.org/yaml-ast-parser/0.0.43 |
| `yargs-parser` | `21.1.1` | ISC | javascript | https://registry.npmjs.org/yargs-parser/21.1.1 |
| `attrs` | `26.1.0` | MIT | python | https://pypi.org/pypi/attrs/26.1.0/json |
| `certifi` | `2026.7.22` | MPL-2.0 | python | https://pypi.org/pypi/certifi/2026.7.22/json |
| `colorama` | `0.4.6` | BSD-3-Clause | python | https://pypi.org/pypi/colorama/0.4.6/json |
| `httpcore` | `1.0.9` | BSD-3-Clause | python | https://pypi.org/pypi/httpcore/1.0.9/json |
| `httpx` | `0.28.1` | BSD-3-Clause | python | https://pypi.org/pypi/httpx/0.28.1/json |
| `hypothesis` | `6.165.10` | MPL-2.0 | python | https://pypi.org/pypi/hypothesis/6.165.10/json |
| `iniconfig` | `2.3.0` | MIT | python | https://pypi.org/pypi/iniconfig/2.3.0/json |
| `jsonschema` | `4.26.0` | MIT | python | https://pypi.org/pypi/jsonschema/4.26.0/json |
| `jsonschema-specifications` | `2025.9.1` | MIT | python | https://pypi.org/pypi/jsonschema-specifications/2025.9.1/json |
| `librt` | `0.15.0` | MIT | python | https://pypi.org/pypi/librt/0.15.0/json |
| `mypy` | `1.19.1` | MIT | python | https://pypi.org/pypi/mypy/1.19.1/json |
| `mypy-extensions` | `1.1.0` | MIT | python | https://files.pythonhosted.org/packages/79/7b/2c79738432f5c924bef5071f933bcc9efd0473bac3b4aa584a6f7c1c8df8/mypy_extensions-1.1.0-py3-none-any.whl |
| `packaging` | `26.3` | Apache-2.0 OR BSD-2-Clause | python | https://pypi.org/pypi/packaging/26.3/json |
| `pathspec` | `1.1.1` | MPL-2.0 | python | https://pypi.org/pypi/pathspec/1.1.1/json |
| `pluggy` | `1.6.0` | MIT | python | https://pypi.org/pypi/pluggy/1.6.0/json |
| `pygments` | `2.21.0` | BSD-2-Clause | python | https://pypi.org/pypi/pygments/2.21.0/json |
| `pytest` | `9.1.1` | MIT | python | https://pypi.org/pypi/pytest/9.1.1/json |
| `quantlib` | `1.43` | BSD-3-Clause | python | https://pypi.org/pypi/quantlib/1.43/json |
| `referencing` | `0.37.0` | MIT | python | https://pypi.org/pypi/referencing/0.37.0/json |
| `rpds-py` | `2026.6.3` | MIT | python | https://pypi.org/pypi/rpds-py/2026.6.3/json |
| `ruff` | `0.15.8` | MIT | python | https://pypi.org/pypi/ruff/0.15.8/json |
| `scipy` | `1.17.1` | BSD-3-Clause | python | https://pypi.org/pypi/scipy/1.17.1/json |
| `scipy` | `1.18.1` | BSD-3-Clause | python | https://pypi.org/pypi/scipy/1.18.1/json |
| `sortedcontainers` | `2.4.0` | Apache-2.0 | python | https://pypi.org/pypi/sortedcontainers/2.4.0/json |
| `types-pyyaml` | `6.0.12.20250915` | Apache-2.0 | python | https://pypi.org/pypi/types-pyyaml/6.0.12.20250915/json |

Total : 49 distribués, 196 outillage.

<!-- COMPOSANTS-FIN -->
