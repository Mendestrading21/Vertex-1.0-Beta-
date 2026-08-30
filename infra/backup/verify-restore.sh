#!/usr/bin/env bash
# Vérification de restauration — la SEULE preuve qu'une sauvegarde existe.
#
# Restaure l'artefact chiffré dans une base VIDE ET JETABLE, contrôle que le
# schéma, les invariants ET LE CONTENU tiennent, puis inscrit
# `verified_restore_at` dans le manifeste. Sans passage réussi ici, la
# sauvegarde reste non prouvée.
#
# CE QUI A CHANGÉ APRÈS LE 8e AUDIT — et pourquoi
# 1. Le contrôle des déclencheurs était
#        SELECT count(*) > 0 … WHERE tgname LIKE '%append_only%'
#    Un SEUL déclencheur suffisait. Il y en a QUATRE (`observations`,
#    `ledger_transactions`, `snapshots`, `thesis_revisions`), plus quatre
#    `_no_truncate` jamais contrôlés. Une base restaurée amputée de
#    `snapshots_append_only` recevait « RESTAURATION VÉRIFIÉE ». Les huit sont
#    désormais nommés un par un, et exigés PRÉSENTS ET ACTIFS (`tgenabled='O'`) :
#    un déclencheur DÉSACTIVÉ est toujours compté par `count(*)`, `pg_dump` le
#    restaure désactivé, et il ne protège rien.
# 2. AUCUN des contrôles ne comparait les DONNÉES à la source. Les quatre
#    contrôles rendaient un verdict identique sur une base de 25 lignes et sur
#    une base de 0 ligne : ils ne portaient aucune information sur la
#    restitution. Le manifeste porte maintenant un recensement par table
#    (`infra/backup/census.sql`, pris sous le même snapshot que `pg_dump`) et il
#    est recomparé ici, ligne à ligne et empreinte à empreinte.
# 3. Un artefact dont le manifeste n'a pas de recensement est REFUSÉ, pas
#    estampillé « vérifié faute de mieux ».
#
# Refus par défaut : la base cible doit être vide et son nom doit porter un
# marqueur de restauration. Ce script ne touche JAMAIS une base de production.
set -euo pipefail

: "${VERTEX_BACKUP_ARTIFACT:?VERTEX_BACKUP_ARTIFACT requis (chemin du .dump.gpg)}"
: "${VERTEX_RESTORE_DATABASE_URL:?VERTEX_RESTORE_DATABASE_URL requis (base jetable)}"
: "${VERTEX_BACKUP_PASSPHRASE:?VERTEX_BACKUP_PASSPHRASE requis}"

for tool in pg_restore psql gpg sha256sum python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERREUR: $tool absent" >&2; exit 2; }
done

# Même conversion que `backup.sh`, et pour la même raison : passée telle quelle
# à pg_restore, une URL SQLAlchemy ferait restaurer AILLEURS sans le dire.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
restore_url="$(python3 "$repo_root/tools/db_url.py" libpq "$VERTEX_RESTORE_DATABASE_URL")"
target_db="$(python3 "$repo_root/tools/db_url.py" dbname "$VERTEX_RESTORE_DATABASE_URL")"
census_sql="$repo_root/infra/backup/census.sql"
[[ -f "$census_sql" ]] || { echo "ERREUR: $census_sql introuvable" >&2; exit 2; }

manifest="$VERTEX_BACKUP_ARTIFACT.manifest.json"
[[ -f "$VERTEX_BACKUP_ARTIFACT" ]] || { echo "ERREUR: artefact introuvable" >&2; exit 2; }
[[ -f "$manifest" ]] || { echo "ERREUR: manifeste introuvable" >&2; exit 2; }

case "$target_db" in
  *restore*|*verify*|*scratch*) ;;
  *) echo "REFUS: « $target_db » ne porte aucun marqueur de restauration." >&2
     echo "La vérification n'écrit que dans une base jetable nommée *restore*/*verify*/*scratch*." >&2
     exit 2 ;;
esac

# `information_schema.tables` ne montre que les objets sur lesquels le rôle
# courant a un droit : une base contenant des tables d'un AUTRE propriétaire y
# apparaissait VIDE, et la restauration se serait faite par-dessus. `pg_class`
# n'est pas filtré par les droits.
existing="$(psql -X "$restore_url" -tAc \
  "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind IN ('r','p','v','m','f','S')
      AND n.nspname NOT IN ('pg_catalog','information_schema')
      AND n.nspname NOT LIKE 'pg_toast%'
      AND n.nspname NOT LIKE 'pg_temp%'")"
if [[ "$existing" != "0" ]]; then
  echo "REFUS: la base cible contient $existing objet(s). La vérification exige une base VIDE." >&2
  exit 2
fi

umask 077
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
plain="$work/restore.dump"

echo "== le manifeste doit porter de quoi vérifier la restitution =="
# Fail-closed : sans recensement, ce script ne peut pas distinguer une base
# rendue complète d'une base rendue vide. Il refuse plutôt que d'estampiller.
python3 - "$manifest" "$work/expected_census.txt" "$work/expected_triggers.txt" <<'PY'
import json, sys
manifest_path, census_out, triggers_out = sys.argv[1:4]
with open(manifest_path, encoding="utf-8") as handle:
    data = json.load(handle)
missing = [key for key in ("census_version", "tables", "triggers", "alembic_version")
           if not data.get(key)]
if missing:
    sys.exit(
        "REFUS: le manifeste n'a pas " + ", ".join(missing) + ".\n"
        "Cet artefact a été produit par une version de backup.sh qui ne recensait\n"
        "pas le contenu. Sa restitution ne peut pas être prouvée : refaire la\n"
        "sauvegarde avec le backup.sh courant. Aucun tampon n'est écrit.")
if data["census_version"] != 1:
    sys.exit(f"REFUS: census_version {data['census_version']} inconnue de ce script.")
with open(census_out, "w", encoding="utf-8") as handle:
    for name in sorted(data["tables"]):
        entry = data["tables"][name]
        handle.write(f"{name}|{entry['rows']}|{entry['digest']}\n")
with open(triggers_out, "w", encoding="utf-8") as handle:
    for name in sorted(data["triggers"]):
        handle.write(f"{name}={data['triggers'][name]}\n")
print(f"recensement attendu : {len(data['tables'])} tables, "
      f"{sum(e['rows'] for e in data['tables'].values())} lignes, "
      f"{len(data['triggers'])} déclencheurs, alembic {data['alembic_version']}")
PY

echo "== déchiffrement =="
printf '%s' "$VERTEX_BACKUP_PASSPHRASE" | gpg --batch --quiet --yes \
  --decrypt --passphrase-fd 0 --output "$plain" "$VERTEX_BACKUP_ARTIFACT"

echo "== intégrité : le clair restauré est bien celui qui a été sauvegardé =="
expected="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['plaintext_sha256'])" "$manifest")"
actual="$(sha256sum "$plain" | cut -d' ' -f1)"
if [[ "$expected" != "$actual" ]]; then
  echo "ÉCHEC: empreinte du clair différente du manifeste. Sauvegarde CORROMPUE." >&2
  exit 1
fi
echo "empreinte conforme"

echo "== restauration dans la base vide =="
# --exit-on-error : une seule erreur invalide la vérification. Pas de « surtout
# ça a presque marché ».
pg_restore --exit-on-error --no-owner --no-privileges \
           --dbname="$restore_url" "$plain"

echo "== contrôles sur la base restaurée =="
fail=0
check() {  # nom, requête, attendu
  local got; got="$(psql -X "$restore_url" -tAc "$2" | tr -d '[:space:]')"
  if [[ "$got" == "$3" ]]; then printf '  OK    %s\n' "$1"
  else printf '  ÉCHEC %s : attendu %s, obtenu %s\n' "$1" "$3" "$got"; fail=1; fi
}

# --- 1. version de migration : la VALEUR, pas seulement la présence ---------
# `count(*) = 1` passait sur une base restaurée à une révision ANTÉRIEURE.
manifest_alembic="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['alembic_version'])" "$manifest")"
check "alembic_version = $manifest_alembic (valeur, pas seulement présence)" \
  "SELECT version_num FROM alembic_version" "$manifest_alembic"

# --- 2. les huit déclencheurs append-only, NOMMÉS un par un et ACTIFS -------
# Liste explicite et FERMÉE. Si une future migration ajoute une cinquième table
# append-only, le contrôle 3 ci-dessous ÉCHOUE bruyamment et impose de mettre
# cette liste à jour — plutôt que de laisser un `LIKE '%append_only%'` déclarer
# vert une couverture partielle.
append_only_tables=(observations ledger_transactions snapshots thesis_revisions)
for tbl in "${append_only_tables[@]}"; do
  for suffix in append_only no_truncate; do
    check "${tbl}_${suffix} présent et ACTIF" \
      "SELECT coalesce((SELECT t.tgenabled::text FROM pg_trigger t
                          JOIN pg_class c ON c.oid = t.tgrelid
                          JOIN pg_namespace n ON n.oid = c.relnamespace
                         WHERE NOT t.tgisinternal AND n.nspname = 'public'
                           AND c.relname = '${tbl}' AND t.tgname = '${tbl}_${suffix}'), 'ABSENT')" \
      "O"
  done
done

# --- 3. aucune table append-only INCONNUE de la liste ci-dessus ------------
expected_list="$(printf "'%s'," "${append_only_tables[@]}")"
check "aucune table append-only hors des ${#append_only_tables[@]} attendues" \
  "SELECT count(*) FROM (
     SELECT DISTINCT c.relname FROM pg_trigger t
       JOIN pg_class c ON c.oid = t.tgrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE NOT t.tgisinternal AND n.nspname = 'public'
        AND t.tgname LIKE '%\_append\_only'
        AND c.relname NOT IN (${expected_list%,})) s" "0"

# --- 4. l'ensemble des déclencheurs rendu à l'identique de la source --------
psql -X -q -tA -v ON_ERROR_STOP=1 "$restore_url" > "$work/actual_triggers.txt" <<'PSQL'
SELECT c.relname || '.' || t.tgname || '=' || t.tgenabled::text
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT t.tgisinternal AND n.nspname = 'public'
ORDER BY 1;
PSQL
if diff -u "$work/expected_triggers.txt" "$work/actual_triggers.txt" > "$work/triggers.diff"; then
  printf '  OK    déclencheurs identiques à la source (%s)\n' "$(wc -l < "$work/actual_triggers.txt")"
else
  printf '  ÉCHEC les déclencheurs restaurés diffèrent de la source :\n'
  sed 's/^/        /' "$work/triggers.diff"
  fail=1
fi

# --- 5. LES DONNÉES : recensement recomparé table par table ----------------
# EXÉCUTÉ AVANT toute remise en état : la libération des baux plus bas MODIFIE
# `outbox`. Recenser après comparerait un état que la sauvegarde ne contenait
# pas.
psql -X -q -tA -v ON_ERROR_STOP=1 "$restore_url" -f "$census_sql" \
  | sed '/^$/d' | LC_ALL=C sort > "$work/actual_census.txt"
if diff -u "$work/expected_census.txt" "$work/actual_census.txt" > "$work/census.diff"; then
  printf '  OK    contenu restitué conforme (%s tables, %s lignes)\n' \
    "$(wc -l < "$work/actual_census.txt")" \
    "$(awk -F'|' '{s+=$2} END {print s+0}' "$work/actual_census.txt")"
else
  printf '  ÉCHEC le contenu restauré diffère de la source (- attendu, + obtenu) :\n'
  sed 's/^/        /' "$work/census.diff"
  fail=1
fi

# --- 6. remise en état : baux outbox hérités -------------------------------
# `pg_dump` capture légitimement l'état à l'instant de la sauvegarde, worker en
# vol compris. Ce n'est donc PAS un invariant à vérifier mais une remise en état
# à faire — un bail hérité désigne un processus qui n'existe plus et bloquerait
# son message jusqu'à expiration.
released="$(psql -X "$restore_url" -tAc \
  "UPDATE outbox SET lease_token = NULL, lease_until = NULL
   WHERE lease_token IS NOT NULL RETURNING 1" | grep -c 1 || true)"
echo "  INFO  baux hérités relâchés : $released (après recensement, donc hors comparaison)"
check "plus aucun bail hérité après remise en état" \
  "SELECT count(*) FROM outbox WHERE lease_token IS NOT NULL" "0"

if [[ "$fail" != "0" ]]; then
  echo >&2
  echo "ÉCHEC: la base restaurée ne satisfait pas les invariants ou ne rend pas" >&2
  echo "le contenu sauvegardé. AUCUN tampon n'est écrit : cette sauvegarde n'est" >&2
  echo "PAS prouvée." >&2
  exit 1
fi

echo "== inscription de la preuve dans le manifeste =="
python3 - "$manifest" <<'PY'
import json, sys
from datetime import datetime, timezone
path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)
data["verified_restore_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(path, "w", encoding="utf-8") as handle:
    json.dump(data, handle, indent=2, ensure_ascii=False)
    handle.write("\n")
print(f"verified_restore_at = {data['verified_restore_at']}")
PY

echo
echo "RESTAURATION VÉRIFIÉE : schéma, huit déclencheurs actifs, et contenu"
echo "restitué identique au recensement pris pendant la sauvegarde."
echo "Restent NON couverts par ce script : copie hors machine, PITR par WAL,"
echo "et la restitution des DROITS (pg_restore tourne --no-privileges : les"
echo "rôles et GRANT sont reposés par initdb + « alembic upgrade head », pas"
echo "par la sauvegarde)."
