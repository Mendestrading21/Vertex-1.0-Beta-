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

echo "== pg_dump (format custom, compressé) =="
# --no-privileges/--no-owner : la sauvegarde est restaurable dans une base
# vide appartenant à un autre rôle, ce qu'exige la vérification mensuelle.
pg_dump --format=custom --compress=9 --no-owner --no-privileges \
        --file="$plain" "$libpq_url"

plain_sha="$(sha256sum "$plain" | cut -d' ' -f1)"
plain_size="$(stat -c%s "$plain")"

echo "== chiffrement (AES-256, phrase hors Git) =="
# Chiffré AVANT tout transfert ; la phrase vient de l'environnement.
printf '%s' "$VERTEX_BACKUP_PASSPHRASE" | gpg --batch --quiet --yes \
  --symmetric --cipher-algo AES256 --passphrase-fd 0 \
  --output "$target" "$plain"

cipher_sha="$(sha256sum "$target" | cut -d' ' -f1)"

# Le manifeste sert la vérification : l'empreinte du CLAIR permet de prouver
# qu'une restauration a bien porté sur cette sauvegarde-là.
cat > "$target.manifest.json" <<JSON
{
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "artifact": "$(basename "$target")",
  "plaintext_sha256": "$plain_sha",
  "plaintext_bytes": $plain_size,
  "ciphertext_sha256": "$cipher_sha",
  "cipher": "AES256",
  "format": "pg_dump custom v$(pg_dump --version | awk '{print $NF}')",
  "verified_restore_at": null,
  "offsite_copy_at": null,
  "wal_archived": false
}
JSON

echo "== fait =="
echo "artefact  : $target"
echo "manifeste : $target.manifest.json"
echo
echo "NON FAIT : copie hors machine, archivage WAL, vérification de restauration."
echo "Tant que verified_restore_at est null, cette sauvegarde n'est PAS prouvée."
