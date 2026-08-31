#!/usr/bin/env bash
# Démarrage local de Vertex 1.0 Beta — API, worker et interface, sur loopback.
#
# POURQUOI CE SCRIPT EXISTE. La pile entière démarrait déjà, mais uniquement
# depuis l'échafaudage Playwright (`apps/web/e2e/global.setup.ts`), sur une
# base jetable dont le schéma est détruit à chaque lancement. Le produit se
# lançait donc en CI et jamais pour son utilisateur, et
# `docs/08-runbooks/START_LOCAL.md` disait « ne pas inventer de commandes ».
# Ce script est la séquence RÉELLEMENT prouvée par cette campagne, promue hors
# des tests, sans base jetable et sans destruction de schéma.
#
# CE QU'IL N'EXPOSE PAS. Les trois services écoutent sur `127.0.0.1` et rien
# d'autre. Aucun `0.0.0.0`, aucun Tailscale Serve, aucun accès téléphone :
# `.claude/rules/security.md` réserve l'exposition applicative au statut
# LATER, et Remote Control pilote Claude, pas Vertex.
#
# CE QU'IL NE FAIT PAS. Il ne contacte ni TWS, ni IBKR, ni TradingView, ni
# Cloudflare. Sans source réelle connectée, le worker tourne en configuration
# synthétique de développement — et le DIT dans son journal. Tout ce qui
# s'affiche porte `population = SYNTHETIC`.
#
# Usage :
#   export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:…@127.0.0.1:5432/vertex'
#   bash tools/start_local.sh
#
# Arrêt : Ctrl-C. Les trois processus sont arrêtés proprement.

set -euo pipefail

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="${RACINE}/apps/web"
PORT_API="${VERTEX_API_PORT:-8000}"
PORT_WEB="${VERTEX_WEB_PORT:-4173}"
PYTHON="${RACINE}/.venv/bin/python"

export PYTHONPATH="${RACINE}/packages/python/vertex_core/src:${RACINE}/packages/python/vertex_persistence/src:${RACINE}/apps/worker/src:${RACINE}/apps/api/src:${PYTHONPATH:-}"

# ── 1. Configuration : fail-closed, jamais de valeur devinée ────────────────
if [[ -z "${VERTEX_DATABASE_URL:-}" ]]; then
  echo "ERREUR: VERTEX_DATABASE_URL n'est pas défini." >&2
  echo "        Vertex ne devine aucune base. Exemple :" >&2
  echo "        export VERTEX_DATABASE_URL='postgresql+psycopg://vertex:<mot-de-passe>@127.0.0.1:5432/vertex'" >&2
  exit 2
fi

if [[ ! "${PORT_API}" =~ ^[0-9]+$ ]] || (( PORT_API < 1 || PORT_API > 65535 )); then
  echo "ERREUR: VERTEX_API_PORT doit être un port TCP entre 1 et 65535." >&2
  exit 2
fi
if [[ ! "${PORT_WEB}" =~ ^[0-9]+$ ]] || (( PORT_WEB < 1 || PORT_WEB > 65535 )); then
  echo "ERREUR: VERTEX_WEB_PORT doit être un port TCP entre 1 et 65535." >&2
  exit 2
fi
if [[ "${PORT_API}" == "${PORT_WEB}" ]]; then
  echo "ERREUR: VERTEX_API_PORT et VERTEX_WEB_PORT doivent être différents." >&2
  exit 2
fi

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERREUR: environnement Python verrouillé absent : ${PYTHON}" >&2
  echo "        Exécuter : uv sync --locked --all-extras --python 3.13" >&2
  exit 2
fi
for commande in curl pg_isready corepack; do
  if ! command -v "${commande}" >/dev/null 2>&1; then
    echo "ERREUR: ${commande} est requis mais introuvable (voir FIRST_INSTALL.md)." >&2
    exit 2
  fi
done
if ! pg_isready -h 127.0.0.1 -p 5432 -t 5 >/dev/null 2>&1; then
  echo "ERREUR: PostgreSQL ne répond pas sur 127.0.0.1:5432. Le démarrer d'abord." >&2
  exit 2
fi

# ── 2. Migrations (idempotentes, aucun schéma détruit) ──────────────────────
echo "== préparation de la base =="
"${PYTHON}" "${RACINE}/tools/bootstrap_local.py"

# ── 3. Arrêt propre des trois processus, quoi qu'il arrive ──────────────────
PIDS=()
arreter() {
  echo ""
  echo "== arrêt =="
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      wait "${pid}" 2>/dev/null || true
    fi
  done
}
trap arreter EXIT INT TERM

attendre_http() {
  local url="$1" pid="$2" limite="${3:-60}" i=0
  while (( i < limite )); do
    if curl -fsS -o /dev/null "${url}" 2>/dev/null; then return 0; fi
    if ! kill -0 "${pid}" 2>/dev/null; then
      echo "ERREUR: le service ${pid} s'est arrêté avant de répondre sur ${url}." >&2
      return 1
    fi
    sleep 1
    i=$(( i + 1 ))
  done
  echo "ERREUR: ${url} n'a pas répondu en ${limite} s." >&2
  return 1
}

# ── 4. API réelle, loopback strict ──────────────────────────────────────────
echo "== API (uvicorn, 127.0.0.1:${PORT_API}) =="
"${PYTHON}" -m uvicorn vertex_api.app:create_app --factory \
  --host 127.0.0.1 --port "${PORT_API}" &
API_PID="$!"
PIDS+=("${API_PID}")
attendre_http "http://127.0.0.1:${PORT_API}/api/v1/health" "${API_PID}"

# ── 5. Worker réel ──────────────────────────────────────────────────────────
echo "== worker (python -m vertex_worker) =="
"${PYTHON}" -m vertex_worker &
WORKER_PID="$!"
PIDS+=("${WORKER_PID}")

# ── 6. Interface : build de production, servie sur loopback ─────────────────
echo "== build web =="
( cd "${WEB}" && corepack pnpm build )
echo "== interface (vite preview, 127.0.0.1:${PORT_WEB}) =="
( cd "${WEB}" && corepack pnpm exec vite preview --port "${PORT_WEB}" --strictPort --host 127.0.0.1 ) &
WEB_PID="$!"
PIDS+=("${WEB_PID}")
attendre_http "http://127.0.0.1:${PORT_WEB}/" "${WEB_PID}"

cat <<INFO

════════════════════════════════════════════════════════════════════
  Vertex 1.0 Beta tourne.

    http://127.0.0.1:${PORT_WEB}/system     ← ouvrir CETTE page d'abord
    http://127.0.0.1:${PORT_WEB}/today

  /system dit ce que le système sait de lui-même : base, migrations,
  horloge, sauvegarde, et l'état RÉEL de chaque capacité. Une capacité
  non sondée y reste NEVER_TESTED — ce n'est pas un défaut d'affichage.

  Aucune source réelle n'est connectée : tout porte SYNTHETIC.
  Pour peupler une base vide :
      .venv/bin/python tools/bootstrap_local.py --with-demo-data

  Ctrl-C pour arrêter les trois processus.
════════════════════════════════════════════════════════════════════

INFO

# Un service qui tombe rend la pile entière indisponible : ne jamais laisser
# l'utilisateur devant une interface partiellement vivante.
set +e
wait -n "${PIDS[@]}"
STATUT="$?"
set -e
echo "ERREUR: un service Vertex s'est arrêté ; arrêt coordonné de la pile." >&2
if (( STATUT == 0 )); then
  exit 1
fi
exit "${STATUT}"