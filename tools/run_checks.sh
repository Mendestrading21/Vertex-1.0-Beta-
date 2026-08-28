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

echo "== compilation =="
python3 -m compileall -q packages/python && echo OK

echo "== suite unitaire/propriétés/oracles =="
python3 -m pytest -q

if [[ "${1:-}" == "--integration" ]]; then
  if [[ -z "${VERTEX_TEST_DATABASE_URL:-}" ]]; then
    echo "ERREUR: VERTEX_TEST_DATABASE_URL absent — les tests d'intégration exigent un PostgreSQL réel." >&2
    exit 2
  fi
  echo "== intégration PostgreSQL =="
  python3 -m pytest -q packages/python/vertex_persistence/tests_integration
fi

echo "== TOUT VERT =="
