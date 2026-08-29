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
