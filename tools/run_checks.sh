#!/usr/bin/env bash
# Contrôles locaux Vertex 1.0 Beta — miroir minimal des gates CI (LOT-01).
# Usage : bash tools/run_checks.sh [--integration]
# --integration exige VERTEX_TEST_DATABASE_URL (PostgreSQL réel, jamais SQLite).
set -euo pipefail
cd "$(dirname "$0")/.."

# RÈGLE DE CE FICHIER : une porte s'invoque SEULE, sur sa propre ligne.
#
# Le motif `porte && echo OK` a été utilisé partout ici et il est SILENCIEUSEMENT
# CASSÉ : sous `set -e`, une commande placée à gauche d'un `&&` est exemptée de
# l'arrêt sur erreur, et la liste `&&` ne fait pas échouer le script non plus.
# Onze portes — dont la frontière financière et la détection de secrets — ont
# donc pu rendre 1 pendant que ce script affichait « TOUT VERT » et sortait 0.
# C'était le QUATRIÈME contournement de la frontière financière, cette fois par
# la sémantique du shell.
#
# Écrire la commande seule, puis `echo OK` à la ligne : sous `set -e`, ATTEINDRE
# le `echo` prouve que la commande a réussi.
# `tools/tests/test_run_checks_fails_closed.py` interdit le retour du motif.

echo "== rôle du dépôt =="
python3 tools/check_repository_role.py target .

echo "== blueprint =="
python3 tools/verify_blueprint.py >/dev/null
echo OK

echo "== frontière financière =="
python3 tools/check_financial_boundary.py >/dev/null
echo OK

echo "== registre des calculs =="
python3 tools/check_calculation_registry.py >/dev/null
echo OK

echo "== détection de secrets =="
python3 tools/check_secrets.py >/dev/null
echo OK

# Les portes `policy` et `release/notices` lisent des YAML : sans PyYAML elles
# ne peuvent PAS rendre de verdict. On échoue fermé plutôt que d'annoncer un
# vert sans preuve.
if ! python3 -c "import yaml" >/dev/null 2>&1; then
  echo "ERREUR: PyYAML absent — portes policy et release/notices NON EXÉCUTÉES (aucune preuve)." >&2
  exit 2
fi

echo "== politique CI et supply-chain (porte policy) =="
# Sortie NON masquée : cette porte imprime les portes dormantes déclarées.
# `--resolve-remote` (re-résolution des SHA d'Actions par le réseau) est
# réservé à la CI ; en local la preuve vient de manifests/actions-pins.yaml.
python3 tools/check_policy.py

echo "== traçabilité des interdictions absolues (porte traceability) =="
# Sortie NON masquée : cette porte imprime les interdictions qui ne sont PAS
# prouvées, à chaque exécution. Un manque qui cesse d'être visible cesse
# d'être un manque.
python3 tools/check_traceability.py

echo "== notices tierces (porte release/notices) =="
# Sortie NON masquée : cette porte imprime les licences non permissives
# reconnues avec leur motif.
python3 tools/check_notices.py

echo "== verrouillage supply-chain (uv.lock exact) =="
if command -v uv >/dev/null 2>&1; then
  uv lock --check >/dev/null
  echo OK
else
  echo "ERREUR: uv absent — porte supply-chain NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== compilation =="
python3 -m compileall -q packages/python
echo OK

echo "== contrat du Worker Cloudflare (ingress TradingView) =="
# Ces 53 tests n'étaient exécutés par AUCUNE porte, ni ici ni en CI : le
# contrat d'entrée du webhook public n'était donc vérifié nulle part.
# `node --test <répertoire>` n'est pas accepté par Node 22 — il faut nommer
# les fichiers.
if command -v node >/dev/null 2>&1; then
  (cd apps/ingress-tradingview/worker && node --test test/*.test.mjs >/dev/null)
  echo OK
else
  echo "ERREUR: node absent — porte du Worker NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== lint web (Biome — porte web-quality) =="
# Miroir local de la porte `web-quality` de docs/06-quality/CI_GATES.md.
# Biome est un devDependency épinglé exactement dans apps/web/package.json ;
# il n'est PAS installé globalement. Sans les dépendances verrouillées, la
# porte n'est pas exécutée — on échoue fermé plutôt que d'annoncer un vert
# sans preuve.
if command -v pnpm >/dev/null 2>&1; then
  if [[ -x apps/web/node_modules/.bin/biome ]]; then
    (cd apps/web && pnpm exec biome lint .)
    echo OK
  else
    echo "ERREUR: apps/web/node_modules absent — exécuter 'pnpm install --frozen-lockfile' dans apps/web ; porte Biome NON EXÉCUTÉE (aucune preuve)." >&2
    exit 2
  fi
else
  echo "ERREUR: pnpm absent — porte Biome NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== budgets de performance (porte performance) =="
# Miroir local. La mesure exige un build web AVEC manifeste Vite : sans lui, la
# distinction import statique / `import()` dynamique n'existe pas et le budget
# de charge initiale n'a plus de sens. On échoue fermé plutôt que de mesurer
# autre chose que ce que le budget désigne.
#
# Le profil P-CI exige `browser_version`. On le LIT sur le navigateur
# réellement installé ; on ne l'invente jamais et on n'accepte aucune valeur
# par défaut. Sans navigateur installé, la porte n'est pas exécutée.
if [[ -x apps/web/node_modules/.bin/vite ]]; then
  if [[ -z "${VERTEX_BROWSER_VERSION:-}" ]]; then
    _chrome="$(cd apps/web && pnpm exec node -e \
      "console.log(require('playwright-core').chromium.executablePath())" 2>/dev/null || true)"
    if [[ -n "${_chrome}" && -x "${_chrome}" ]]; then
      VERTEX_BROWSER_VERSION="$("${_chrome}" --version)"
      export VERTEX_BROWSER_VERSION
    else
      echo "ERREUR: aucun navigateur Chromium installé — exécuter 'pnpm exec playwright install chromium' dans apps/web ; porte performance NON EXÉCUTÉE (aucune preuve)." >&2
      exit 2
    fi
  fi
  (cd apps/web && pnpm exec vite build --manifest >/dev/null)
  python3 tools/build_performance_report.py --profile P-DEV \
    --out "${TMPDIR:-/tmp}/vertex-performance-report.json" >/dev/null
  python3 tools/check_performance_budgets.py \
    --report "${TMPDIR:-/tmp}/vertex-performance-report.json" >/dev/null
  echo OK
else
  echo "ERREUR: apps/web/node_modules absent — porte performance NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== lint et typage Python (porte python-quality) =="
# Miroir local de la porte `python-quality` de docs/06-quality/CI_GATES.md.
# Ruff et mypy sont épinglés en versions EXACTES dans pyproject.toml et
# verrouillés par uv.lock : les exécuter hors de cet environnement rendrait
# le compte de violations non reproductible — c'est précisément le défaut que
# cette porte corrige. Sans `uv`, la porte n'est PAS exécutée et on échoue
# fermé plutôt que d'annoncer un vert sans preuve.
# La porte échoue sur la MOINDRE violation : aucun avertissement toléré.
if command -v uv >/dev/null 2>&1; then
  uv run --no-sync ruff check .
  echo "OK ruff"
  uv run --no-sync mypy
  echo "OK mypy"
else
  echo "ERREUR: uv absent — porte python-quality NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== suite unitaire/propriétés/oracles =="
python3 -m pytest -q

if [[ "${1:-}" == "--integration" ]]; then
  if [[ -z "${VERTEX_TEST_DATABASE_URL:-}" ]]; then
    echo "ERREUR: VERTEX_TEST_DATABASE_URL absent — les tests d'intégration exigent un PostgreSQL réel." >&2
    exit 2
  fi
  # Les trois suites partagent la MÊME base PostgreSQL et recréent le schéma
  # dans leur fixture de session : les exécuter en parallèle (ou en une seule
  # invocation multi-répertoires distribuée) fait tomber les schémas les uns
  # des autres. Exécution SÉRIELLE obligatoire, une invocation par suite.
  for suite in \
    packages/python/vertex_persistence/tests_integration \
    apps/worker/tests_integration \
    apps/api/tests_integration
  do
    echo "== intégration PostgreSQL : ${suite} =="
    python3 -m pytest -q -p no:xdist "${suite}"
  done
fi

echo "== TOUT VERT =="
