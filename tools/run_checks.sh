#!/usr/bin/env bash
# Contrôles locaux Vertex 1.0 Beta — miroir minimal des gates CI (LOT-01).
# Usage : bash tools/run_checks.sh [--integration]
# --integration exige VERTEX_TEST_DATABASE_URL (PostgreSQL réel, jamais SQLite).
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== rôle du dépôt =="
python3 tools/check_repository_role.py target .

echo "== blueprint =="
python3 tools/verify_blueprint.py >/dev/null && echo OK

echo "== frontière financière =="
python3 tools/check_financial_boundary.py >/dev/null && echo OK

echo "== registre des calculs =="
python3 tools/check_calculation_registry.py >/dev/null && echo OK

echo "== détection de secrets =="
python3 tools/check_secrets.py >/dev/null && echo OK

echo "== verrouillage supply-chain (uv.lock exact) =="
if command -v uv >/dev/null 2>&1; then
  uv lock --check >/dev/null && echo OK
else
  echo "ERREUR: uv absent — porte supply-chain NON EXÉCUTÉE (aucune preuve)." >&2
  exit 2
fi

echo "== compilation =="
python3 -m compileall -q packages/python && echo OK

echo "== contrat du Worker Cloudflare (ingress TradingView) =="
# Ces 53 tests n'étaient exécutés par AUCUNE porte, ni ici ni en CI : le
# contrat d'entrée du webhook public n'était donc vérifié nulle part.
# `node --test <répertoire>` n'est pas accepté par Node 22 — il faut nommer
# les fichiers.
if command -v node >/dev/null 2>&1; then
  (cd apps/ingress-tradingview/worker && node --test test/*.test.mjs >/dev/null) && echo OK
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
    (cd apps/web && pnpm exec biome lint .) && echo OK
  else
    echo "ERREUR: apps/web/node_modules absent — exécuter 'pnpm install --frozen-lockfile' dans apps/web ; porte Biome NON EXÉCUTÉE (aucune preuve)." >&2
    exit 2
  fi
else
  echo "ERREUR: pnpm absent — porte Biome NON EXÉCUTÉE (aucune preuve)." >&2
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
