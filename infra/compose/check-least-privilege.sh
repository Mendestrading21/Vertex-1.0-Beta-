#!/usr/bin/env bash
# Preuve, sur une base VIVANTE, que le rôle de runtime ne peut pas contourner
# les déclencheurs append-only.
#
# POURQUOI CE SCRIPT EXISTE
# La migration `0007_least_privilege_grants` ne peut pas resserrer les droits
# d'une base qui n'a qu'un seul rôle : elle émet un NOTICE et ne fait rien. Un
# NOTICE n'est pas une preuve. Ce script est la porte : il se connecte AVEC le
# rôle du runtime et tente réellement les contournements. Tout succès est un
# échec du contrôle.
#
# SANS EFFET DE BORD
# Chaque tentative interdite s'exécute dans une transaction systématiquement
# annulée. En PostgreSQL le DDL est transactionnel : même un `DISABLE TRIGGER`
# qui RÉUSSIRAIT serait annulé — et signalé comme défaut. Ce script peut donc
# être lancé contre la base réelle sans rien y modifier.
#
# Usage :
#   VERTEX_DATABASE_URL='postgresql+psycopg://<runtime>:<pw>@127.0.0.1:5432/vertex' \
#     bash infra/compose/check-least-privilege.sh
set -uo pipefail

: "${VERTEX_DATABASE_URL:?VERTEX_DATABASE_URL requis (DSN du rôle de RUNTIME)}"

for tool in psql python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERREUR: $tool absent" >&2; exit 2; }
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
url="$(python3 "$repo_root/tools/db_url.py" libpq "$VERTEX_DATABASE_URL")" || exit 2

fail=0
ok()   { printf '  OK    %s\n' "$1"; }
bad()  { printf '  ÉCHEC %s\n' "$1"; fail=1; }

q() { psql -tAX -q -v ON_ERROR_STOP=1 "$url" -c "$1" 2>/dev/null | tr -d '[:space:]'; }

role="$(q 'SELECT current_user')"
[[ -n "$role" ]] || { echo "ERREUR: connexion impossible avec le DSN fourni." >&2; exit 2; }
echo "== rôle de connexion : $role =="

# --- 1. attributs du rôle -------------------------------------------------
attrs="$(q "SELECT rolsuper::int::text || rolcreatedb::int::text || rolcreaterole::int::text
                || rolbypassrls::int::text || rolreplication::int::text
            FROM pg_roles WHERE rolname = current_user")"
[[ "$attrs" == "00000" ]] \
  && ok "le rôle n'est ni superutilisateur, ni createdb/createrole/bypassrls/replication" \
  || bad "attributs de rôle trop larges (super|createdb|createrole|bypassrls|replication = $attrs)"

# --- 2. propriété ---------------------------------------------------------
owned="$(q "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind IN ('r','p')
              AND pg_get_userbyid(c.relowner) = current_user")"
[[ "$owned" == "0" ]] \
  && ok "le rôle ne possède AUCUNE table de public (0)" \
  || bad "le rôle possède $owned table(s) : propriétaire = capable de retirer ses propres déclencheurs"

owns_schema="$(q "SELECT pg_get_userbyid(nspowner) = current_user FROM pg_namespace WHERE nspname='public'")"
[[ "$owns_schema" == "f" ]] \
  && ok "le rôle ne possède pas le schéma public" \
  || bad "le rôle possède le schéma public"

# --- 3. pas de création d'objet ------------------------------------------
[[ "$(q "SELECT has_schema_privilege(current_user,'public','CREATE')")" == "f" ]] \
  && ok "le rôle n'a pas CREATE sur public (aucune table fantôme à côté d'une table protégée)" \
  || bad "le rôle a CREATE sur le schéma public"

# --- 4. les déclencheurs existent ET sont ACTIFS --------------------------
# `count(*) > 0` ne prouve rien : un déclencheur DÉSACTIVÉ est toujours compté.
# On exige donc `tgenabled = 'O'`, un par un.
tables="$(psql -tAX -q -v ON_ERROR_STOP=1 "$url" -c \
  "SELECT DISTINCT c.relname FROM pg_trigger t
     JOIN pg_class c ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE NOT t.tgisinternal AND n.nspname='public'
      AND t.tgname LIKE '%\_append\_only' ORDER BY 1" 2>/dev/null)"
if [[ -z "$tables" ]]; then
  bad "aucune table append-only trouvée : soit le schéma est absent, soit les déclencheurs ont disparu"
else
  while read -r tbl; do
    [[ -n "$tbl" ]] || continue
    for suffix in append_only no_truncate; do
      state="$(q "SELECT coalesce((SELECT tgenabled FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
                   WHERE c.relname='${tbl}' AND t.tgname='${tbl}_${suffix}' AND NOT t.tgisinternal), 'ABSENT')")"
      [[ "$state" == "O" ]] \
        && ok "${tbl}_${suffix} présent et ACTIF" \
        || bad "${tbl}_${suffix} : état « $state » (attendu O = activé)"
    done
    for priv in UPDATE DELETE TRUNCATE; do
      [[ "$(q "SELECT has_table_privilege(current_user,'public.${tbl}','${priv}')")" == "f" ]] \
        && ok "aucun droit $priv sur $tbl" \
        || bad "le rôle détient $priv sur la table append-only $tbl"
    done
  done <<< "$tables"
fi

# --- 5. tentatives réelles, toutes annulées ------------------------------
first_table="$(head -n1 <<< "$tables")"
must_fail() {  # libellé, SQL
  local label="$1" sql="$2" out
  out="$(psql -X -q -v ON_ERROR_STOP=1 "$url" <<SQL 2>&1
BEGIN;
$sql
ROLLBACK;
SQL
)"
  if [[ $? -eq 0 ]]; then
    bad "$label a RÉUSSI (annulé, mais le chemin existe)"
  else
    ok "$label refusé : $(sed -n 's/^ERROR:  //p' <<< "$out" | head -1)"
  fi
}

if [[ -n "$first_table" ]]; then
  must_fail "ALTER TABLE $first_table DISABLE TRIGGER" \
            "ALTER TABLE $first_table DISABLE TRIGGER ${first_table}_append_only;"
  must_fail "DROP TRIGGER ${first_table}_append_only" \
            "DROP TRIGGER ${first_table}_append_only ON $first_table;"
  must_fail "ALTER TABLE $first_table OWNER TO <soi-même>" \
            "ALTER TABLE $first_table OWNER TO current_user;"
  must_fail "TRUNCATE $first_table" "TRUNCATE $first_table;"
fi
must_fail "SET session_replication_role = replica (désactivation globale)" \
          "SET session_replication_role = replica;"
must_fail "CREATE TABLE dans public" "CREATE TABLE vertex_probe_shadow (x int);"
must_fail "DROP FUNCTION vertex_forbid_mutation()" \
          "DROP FUNCTION vertex_forbid_mutation() CASCADE;"

echo
if [[ "$fail" != "0" ]]; then
  echo "MOINDRE PRIVILÈGE NON TENU. Les déclencheurs append-only sont contournables" >&2
  echo "par le rôle qui sert les requêtes. Provisionner les rôles avec" >&2
  echo "infra/compose/initdb/10-least-privilege-roles.sh puis « alembic upgrade head »." >&2
  exit 1
fi
echo "MOINDRE PRIVILÈGE TENU pour « $role » sur cette base."
echo "Non couvert ici : le rôle de MIGRATION reste propriétaire et peut, lui,"
echo "retirer un déclencheur — c'est son rôle. Sa DSN ne doit jamais servir l'API."
