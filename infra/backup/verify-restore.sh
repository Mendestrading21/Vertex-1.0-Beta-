#!/usr/bin/env bash
# Vérification de restauration — la SEULE preuve qu'une sauvegarde existe.
#
# Restaure l'artefact chiffré dans une base VIDE ET JETABLE, contrôle que le
# schéma et les invariants tiennent, puis inscrit `verified_restore_at` dans le
# manifeste. Sans passage réussi ici, la sauvegarde reste non prouvée.
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

manifest="$VERTEX_BACKUP_ARTIFACT.manifest.json"
[[ -f "$VERTEX_BACKUP_ARTIFACT" ]] || { echo "ERREUR: artefact introuvable" >&2; exit 2; }
[[ -f "$manifest" ]] || { echo "ERREUR: manifeste introuvable" >&2; exit 2; }

case "$target_db" in
  *restore*|*verify*|*scratch*) ;;
  *) echo "REFUS: « $target_db » ne porte aucun marqueur de restauration." >&2
     echo "La vérification n'écrit que dans une base jetable nommée *restore*/*verify*/*scratch*." >&2
     exit 2 ;;
esac

existing="$(psql "$restore_url" -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema')")"
if [[ "$existing" != "0" ]]; then
  echo "REFUS: la base cible contient $existing table(s). La vérification exige une base VIDE." >&2
  exit 2
fi

umask 077
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
plain="$work/restore.dump"

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

echo "== contrôles de cohérence sur la base restaurée =="
fail=0
check() {  # nom, requête, attendu
  local got; got="$(psql "$restore_url" -tAc "$2" | tr -d '[:space:]')"
  if [[ "$got" == "$3" ]]; then printf '  OK   %s\n' "$1"
  else printf '  ÉCHEC %s : attendu %s, obtenu %s\n' "$1" "$3" "$got"; fail=1; fi
}

# La version de migration doit exister : une base restaurée sans elle ne peut
# pas être remise sous Alembic.
check "version Alembic présente" \
  "SELECT count(*) FROM alembic_version" "1"
# Les tables append-only doivent retrouver leurs déclencheurs : sans eux, la
# base restaurée accepterait une réécriture d'historique.
check "déclencheurs append-only restaurés" \
  "SELECT count(*)>0 FROM pg_trigger WHERE NOT tgisinternal AND tgname LIKE '%append_only%'" "t"
# L'outbox restaurée peut légitimement contenir des baux : `pg_dump` capture
# l'état à l'instant de la sauvegarde, worker en vol compris. Ce n'est donc
# PAS un invariant à vérifier mais une remise en état à faire — un bail hérité
# désigne un processus qui n'existe plus et bloquerait son message jusqu'à
# expiration. On les relâche explicitement, puis on vérifie le résultat.
released="$(psql "$restore_url" -tAc \
  "UPDATE outbox SET lease_token = NULL, lease_until = NULL
   WHERE lease_token IS NOT NULL RETURNING 1" | grep -c 1 || true)"
echo "  INFO baux hérités relâchés : $released"
check "plus aucun bail hérité après remise en état" \
  "SELECT count(*) FROM outbox WHERE lease_token IS NOT NULL" "0"

if [[ "$fail" != "0" ]]; then
  echo "ÉCHEC: la base restaurée ne satisfait pas les invariants." >&2
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
echo "RESTAURATION VÉRIFIÉE. La sauvegarde est prouvée."
echo "Restent non couverts par ce script : copie hors machine et PITR par WAL."
