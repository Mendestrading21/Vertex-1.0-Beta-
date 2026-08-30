#!/usr/bin/env bash
# Sauvegarde chiffrée de la base Vertex.
#
# Objectifs (docs/08-runbooks/BACKUP_RESTORE.md) : RPO ≤ 5 min une fois le WAL
# archivé, RTO ≤ 30 min, rétention 7 quotidiennes / 4 hebdomadaires /
# 12 mensuelles, trois copies, deux supports, une hors machine.
#
# CE QUE FAIT CE SCRIPT : un `pg_dump` format custom, chiffré avant écriture,
# accompagné de l'empreinte du clair et d'un manifeste. RIEN D'AUTRE.
#
# CE QU'IL NE FAIT PAS, et qu'il ne faut pas croire fait :
#   - il ne copie pas hors machine (troisième copie) ;
#   - il n'archive pas le WAL (donc pas de PITR, donc pas de RPO 5 min) ;
#   - il ne met PAS à jour `last_verified_restore_at` : seule une RESTAURATION
#     vérifiée le fait, par `infra/backup/verify-restore.sh`.
# Une tâche de copie réussie ne vaut pas sauvegarde.
#
# RECENSEMENT DU CONTENU (ajouté après le 8e audit)
# Le manifeste ne portait que des empreintes d'OCTETS : il prouvait qu'un
# fichier n'avait pas bougé, jamais que la base restaurée contenait quelque
# chose. Il porte désormais, table par table, le nombre de lignes et une
# empreinte de contenu (`infra/backup/census.sql`), prises DANS LA MÊME
# TRANSACTION que `pg_dump` grâce à un snapshot exporté — donc exactement sur
# ce qui a été sauvegardé, sans fenêtre de course. `verify-restore.sh` les
# recompare sur la base restaurée et refuse d'estampiller sans concordance.
#
# RÔLE À UTILISER : celui des MIGRATIONS (`VERTEX_MIGRATION_DATABASE_URL`),
# propriétaire des tables. Le rôle de runtime ne possède rien et n'a pas
# vocation à lire l'intégralité du schéma.
set -euo pipefail

: "${VERTEX_DATABASE_URL:?VERTEX_DATABASE_URL requis (environnement uniquement)}"
: "${VERTEX_BACKUP_DIR:?VERTEX_BACKUP_DIR requis}"
: "${VERTEX_BACKUP_PASSPHRASE:?VERTEX_BACKUP_PASSPHRASE requis (jamais dans Git)}"

for tool in pg_dump psql gpg sha256sum python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "ERREUR: $tool absent" >&2; exit 2; }
done

# `VERTEX_DATABASE_URL` est en forme SQLAlchemy (`postgresql+psycopg://…`),
# celle qu'exige le runtime. Les outils libpq ne la comprennent pas — et ils
# n'échouent PAS dessus : `pg_dump` la prend pour un nom de base, se rabat sur
# la socket locale et sauvegarderait une AUTRE base sans rien dire. La
# conversion passe par l'autorité unique `vertex_persistence.dsn`.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
libpq_url="$(python3 "$repo_root/tools/db_url.py" libpq "$VERTEX_DATABASE_URL")"
intended_db="$(python3 "$repo_root/tools/db_url.py" dbname "$VERTEX_DATABASE_URL")"

# Ceinture ET bretelles : on demande à la base elle-même son nom. Si un
# repli silencieux se produisait quand même, il est attrapé ici.
connected_db="$(psql "$libpq_url" -tAc 'SELECT current_database()' | tr -d '[:space:]')"
if [[ "$connected_db" != "$intended_db" ]]; then
  echo "REFUS: connecté à « $connected_db » alors que l'URL désigne « $intended_db »." >&2
  echo "Une sauvegarde de la mauvaise base est pire que pas de sauvegarde." >&2
  exit 1
fi
echo "base visée et base jointe concordent : $intended_db"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
umask 077                      # les fichiers créés ne sont lisibles que par le propriétaire
mkdir -p "$VERTEX_BACKUP_DIR"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT     # le clair ne survit jamais au script

plain="$work/vertex-$stamp.dump"
target="$VERTEX_BACKUP_DIR/vertex-$stamp.dump.gpg"

echo "== pg_dump + recensement, sur UN SEUL ET MÊME snapshot =="
# `pg_dump` seul, puis un `psql` séparé pour compter les lignes, ne verraient
# PAS le même état : une écriture entre les deux ferait diverger le manifeste
# de l'artefact et déclencherait un faux échec à la vérification. On ouvre donc
# une transaction REPEATABLE READ READ ONLY, on exporte son snapshot, on le
# passe à `pg_dump --snapshot`, et on recense DANS la même transaction.
# --no-privileges/--no-owner : la sauvegarde est restaurable dans une base
# vide appartenant à un autre rôle, ce qu'exige la vérification mensuelle.
census="$work/census.txt"
dump_status="$work/dump.status"
export VERTEX_LIBPQ_URL="$libpq_url"
export VERTEX_PLAIN_FILE="$plain"
export VERTEX_DUMP_STATUS="$dump_status"
export VERTEX_CENSUS_SQL="$repo_root/infra/backup/census.sql"

psql -X -q -tA -v ON_ERROR_STOP=1 "$libpq_url" > "$census" <<'PSQL'
\getenv vertex_census_sql VERTEX_CENSUS_SQL
BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT pg_export_snapshot() AS vertex_snapshot \gset
\setenv VERTEX_DUMP_SNAPSHOT :vertex_snapshot
\! pg_dump --format=custom --compress=9 --no-owner --no-privileges --snapshot="$VERTEX_DUMP_SNAPSHOT" --file="$VERTEX_PLAIN_FILE" "$VERTEX_LIBPQ_URL"; echo $? > "$VERTEX_DUMP_STATUS"
\i :vertex_census_sql
COMMIT;
PSQL

# `\!` n'interrompt pas psql : le code de sortie de `pg_dump` est relu ici.
if [[ "$(cat "$dump_status" 2>/dev/null || echo absent)" != "0" ]]; then
  echo "ÉCHEC: pg_dump a échoué (statut $(cat "$dump_status" 2>/dev/null || echo absent))." >&2
  exit 1
fi
[[ -s "$plain" ]] || { echo "ÉCHEC: pg_dump n'a produit aucun contenu." >&2; exit 1; }
grep -q '|' "$census" || { echo "ÉCHEC: recensement vide — aucune table lue." >&2; exit 1; }
echo "tables recensées : $(grep -c '|' "$census")"

alembic_version="$(psql -X -tA -q "$libpq_url" -c 'SELECT version_num FROM alembic_version' | tr -d '[:space:]')"
[[ -n "$alembic_version" ]] || { echo "ÉCHEC: alembic_version illisible." >&2; exit 1; }

# État des déclencheurs à la SOURCE : nom, table et activation. `verify-restore`
# vérifie que la restauration les rend à l'identique — et, séparément, que les
# huit déclencheurs append-only attendus sont présents ET actifs.
triggers="$work/triggers.txt"
psql -X -tA -q -v ON_ERROR_STOP=1 "$libpq_url" > "$triggers" <<'PSQL'
SELECT c.relname || '.' || t.tgname || '=' || t.tgenabled::text
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE NOT t.tgisinternal AND n.nspname = 'public'
ORDER BY 1;
PSQL

plain_sha="$(sha256sum "$plain" | cut -d' ' -f1)"
plain_size="$(stat -c%s "$plain")"

echo "== chiffrement (AES-256, phrase hors Git) =="
# Chiffré AVANT tout transfert ; la phrase vient de l'environnement.
printf '%s' "$VERTEX_BACKUP_PASSPHRASE" | gpg --batch --quiet --yes \
  --symmetric --cipher-algo AES256 --passphrase-fd 0 \
  --output "$target" "$plain"

cipher_sha="$(sha256sum "$target" | cut -d' ' -f1)"

# Le manifeste sert la vérification : l'empreinte du CLAIR prouve qu'une
# restauration a porté sur CET artefact ; le recensement prouve ce que
# l'artefact doit RENDRE. Écrit par python3 : les valeurs sont échappées, pas
# concaténées à la main dans du JSON.
VERTEX_MANIFEST_PATH="$target.manifest.json" \
VERTEX_ARTIFACT_NAME="$(basename "$target")" \
VERTEX_PLAIN_SHA="$plain_sha" VERTEX_PLAIN_SIZE="$plain_size" \
VERTEX_CIPHER_SHA="$cipher_sha" \
VERTEX_PG_DUMP_VERSION="$(pg_dump --version | sed 's/^pg_dump (PostgreSQL) //')" \
VERTEX_SERVER_VERSION="$(psql -X -tA -q "$libpq_url" -c 'SHOW server_version' | tr -d '\n')" \
VERTEX_ALEMBIC_VERSION="$alembic_version" \
VERTEX_CENSUS_FILE="$census" VERTEX_TRIGGERS_FILE="$triggers" \
python3 - <<'PY'
import json, os
from datetime import datetime, timezone

tables = {}
with open(os.environ["VERTEX_CENSUS_FILE"], encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        name, rows, digest = line.split("|", 2)
        tables[name] = {"rows": int(rows), "digest": digest}

triggers = {}
with open(os.environ["VERTEX_TRIGGERS_FILE"], encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        name, enabled = line.rsplit("=", 1)
        triggers[name] = enabled

manifest = {
    "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "artifact": os.environ["VERTEX_ARTIFACT_NAME"],
    "plaintext_sha256": os.environ["VERTEX_PLAIN_SHA"],
    "plaintext_bytes": int(os.environ["VERTEX_PLAIN_SIZE"]),
    "ciphertext_sha256": os.environ["VERTEX_CIPHER_SHA"],
    "cipher": "AES256",
    "format": "pg_dump custom",
    "pg_dump_version": os.environ["VERTEX_PG_DUMP_VERSION"],
    "server_version": os.environ["VERTEX_SERVER_VERSION"],
    "alembic_version": os.environ["VERTEX_ALEMBIC_VERSION"],
    # Ce que la restauration DOIT rendre. `verify-restore.sh` refuse
    # d'estampiller un artefact dont ces deux blocs sont absents : sans eux, il
    # ne peut pas distinguer une base rendue complète d'une base rendue vide.
    "census_version": 1,
    "tables": tables,
    "triggers": triggers,
    "verified_restore_at": None,
    "offsite_copy_at": None,
    "wal_archived": False,
}
with open(os.environ["VERTEX_MANIFEST_PATH"], "w", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=2, ensure_ascii=False, sort_keys=False)
    handle.write("\n")
total = sum(entry["rows"] for entry in tables.values())
print(f"recensement : {len(tables)} tables, {total} lignes au total")
PY

echo "== fait =="
echo "artefact  : $target"
echo "manifeste : $target.manifest.json"
echo
echo "NON FAIT : copie hors machine, archivage WAL, vérification de restauration."
echo "Tant que verified_restore_at est null, cette sauvegarde n'est PAS prouvée."
