#!/usr/bin/env bash
# Provisionnement des rôles PostgreSQL de Vertex — moindre privilège.
#
# POURQUOI CE FICHIER EXISTE
# `POSTGRES_USER` de l'image officielle PostgreSQL est un SUPERUTILISATEUR, et
# c'est aussi le propriétaire de tout ce que la première connexion crée. Tant
# que l'API et le worker se connectaient avec ce rôle, ils étaient PROPRIÉTAIRES
# des tables append-only — donc capables de :
#     ALTER TABLE snapshots DISABLE TRIGGER snapshots_append_only;
#     UPDATE snapshots SET content = ...;      -- historique réécrit
#     DROP TRIGGER snapshots_append_only ON snapshots;
# Les déclencheurs de `0001`/`0003`/`0006` étaient AUTO-CONTOURNABLES par le
# rôle qui sert les requêtes : la garantie « holds for every SQL client » ne
# tenait contre AUCUN client du runtime.
#
# TROIS RÔLES DISTINCTS, JAMAIS CONFONDUS
#   `POSTGRES_USER` (VERTEX_DB_SUPERUSER) — amorçage uniquement. Superutilisateur.
#       Crée les deux autres rôles puis n'est plus utilisé. Ni l'API, ni le
#       worker, ni les sauvegardes ne s'en servent.
#   VERTEX_DB_MIGRATE_USER — PROPRIÉTAIRE du schéma et des tables. Seul Alembic
#       l'utilise. Peut créer, altérer, poser et retirer un déclencheur.
#   VERTEX_DB_RUNTIME_USER — rôle de SERVICE (api, worker). Ne possède RIEN.
#       Peut lire et insérer ; ne peut ni désactiver, ni retirer un déclencheur,
#       ni changer un propriétaire, ni créer un objet dans `public`, ni poser
#       `session_replication_role`.
#
# QUAND CE SCRIPT S'EXÉCUTE
# L'entrypoint officiel ne lance `/docker-entrypoint-initdb.d/*` qu'à la
# PREMIÈRE initialisation d'un volume vide. Le script est écrit idempotent pour
# pouvoir être rejoué à la main sur une installation existante :
#     docker compose -f infra/compose/compose.yaml exec -T db \
#       bash /docker-entrypoint-initdb.d/10-least-privilege-roles.sh
#
# CE QU'IL NE FAIT PAS
# Il ne pose AUCUN droit sur les tables : elles n'existent pas encore à cet
# instant. Il installe les DROITS PAR DÉFAUT, et la migration Alembic
# `0007_least_privilege_grants` resserre ensuite table par table.
set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER requis}"
: "${POSTGRES_DB:?POSTGRES_DB requis}"
: "${VERTEX_DB_MIGRATE_USER:?VERTEX_DB_MIGRATE_USER requis}"
: "${VERTEX_DB_MIGRATE_PASSWORD:?VERTEX_DB_MIGRATE_PASSWORD requis}"
: "${VERTEX_DB_RUNTIME_USER:?VERTEX_DB_RUNTIME_USER requis}"
: "${VERTEX_DB_RUNTIME_PASSWORD:?VERTEX_DB_RUNTIME_PASSWORD requis}"

# Identifiants SQL : contraints à un motif sûr AVANT toute interpolation.
for pair in "VERTEX_DB_MIGRATE_USER=$VERTEX_DB_MIGRATE_USER" \
            "VERTEX_DB_RUNTIME_USER=$VERTEX_DB_RUNTIME_USER" \
            "POSTGRES_USER=$POSTGRES_USER" \
            "POSTGRES_DB=$POSTGRES_DB"; do
  name="${pair%%=*}"; value="${pair#*=}"
  if ! [[ "$value" =~ ^[a-z_][a-z0-9_]{0,62}$ ]]; then
    echo "REFUS: $name = « $value » n'est pas un identifiant SQL sûr ([a-z_][a-z0-9_]*)." >&2
    exit 2
  fi
done

# L'invariant central : le rôle qui SERT les requêtes n'est ni le
# superutilisateur d'amorçage, ni le propriétaire des tables.
if [[ "$VERTEX_DB_RUNTIME_USER" == "$POSTGRES_USER" ]]; then
  echo "REFUS: le rôle de runtime ne peut pas être le superutilisateur d'amorçage." >&2
  echo "Il posséderait les tables et pourrait désactiver les déclencheurs append-only." >&2
  exit 2
fi
if [[ "$VERTEX_DB_RUNTIME_USER" == "$VERTEX_DB_MIGRATE_USER" ]]; then
  echo "REFUS: le rôle de runtime ne peut pas être le rôle de migration." >&2
  echo "Le propriétaire des tables peut toujours retirer ses propres déclencheurs." >&2
  exit 2
fi
if [[ "$VERTEX_DB_MIGRATE_USER" == "$POSTGRES_USER" ]]; then
  echo "REFUS: le rôle de migration ne peut pas être le superutilisateur d'amorçage." >&2
  exit 2
fi

for secret in VERTEX_DB_MIGRATE_PASSWORD VERTEX_DB_RUNTIME_PASSWORD; do
  value="${!secret}"
  if [[ -z "$value" || "$value" == "CHANGE_ME" ]]; then
    echo "REFUS: $secret est vide ou vaut la valeur d'exemple. Aucun démarrage." >&2
    exit 2
  fi
done

echo "provisionnement des rôles : migration=$VERTEX_DB_MIGRATE_USER runtime=$VERTEX_DB_RUNTIME_USER"

# Les mots de passe ne transitent JAMAIS par la ligne de commande (`ps` les
# verrait) : psql les lit lui-même dans l'environnement avec `\getenv`, et
# `:'var'` les échappe en littéral SQL.
psql --set ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'PSQL'
\getenv migrate_role VERTEX_DB_MIGRATE_USER
\getenv migrate_pw   VERTEX_DB_MIGRATE_PASSWORD
\getenv runtime_role VERTEX_DB_RUNTIME_USER
\getenv runtime_pw   VERTEX_DB_RUNTIME_PASSWORD

-- Création idempotente : `\gexec` n'exécute la commande que si la ligne existe.
SELECT format('CREATE ROLE %I LOGIN', :'migrate_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'migrate_role') \gexec
SELECT format('CREATE ROLE %I LOGIN', :'runtime_role')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'runtime_role') \gexec

-- Aucun des deux n'est superutilisateur, ne crée de base, ni de rôle, ni ne
-- contourne RLS, ni ne réplique. Rejoué, ce bloc réaffirme l'état voulu.
SELECT format(
  'ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION PASSWORD %L',
  :'migrate_role', :'migrate_pw') \gexec
SELECT format(
  'ALTER ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOREPLICATION PASSWORD %L',
  :'runtime_role', :'runtime_pw') \gexec

-- Le schéma applicatif appartient au rôle de MIGRATION, pas au runtime.
SELECT format('ALTER SCHEMA public OWNER TO %I', :'migrate_role') \gexec

-- Refus par défaut : PUBLIC ne garde aucun droit sur la base ni sur le schéma.
SELECT format('REVOKE ALL ON DATABASE %I FROM PUBLIC', current_database()) \gexec
REVOKE ALL ON SCHEMA public FROM PUBLIC;

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'migrate_role') \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'runtime_role') \gexec

-- Le rôle de migration crée ; le runtime traverse seulement.
SELECT format('GRANT USAGE, CREATE ON SCHEMA public TO %I', :'migrate_role') \gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'runtime_role') \gexec
SELECT format('REVOKE CREATE ON SCHEMA public FROM %I', :'runtime_role') \gexec

-- Droits PAR DÉFAUT : toute table créée PLUS TARD par le rôle de migration est
-- immédiatement lisible/écrivable par le runtime. Sans cela, une table ajoutée
-- par une future migration serait invisible au runtime jusqu'à un GRANT oublié.
-- La migration `0007` RESSERRE ensuite : elle retire UPDATE/DELETE/TRUNCATE sur
-- toute table portant un déclencheur append-only.
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
  :'migrate_role', :'runtime_role') \gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
     GRANT USAGE, SELECT ON SEQUENCES TO %I',
  :'migrate_role', :'runtime_role') \gexec
PSQL

echo "rôles provisionnés. Les droits table par table sont posés par la migration 0007."
