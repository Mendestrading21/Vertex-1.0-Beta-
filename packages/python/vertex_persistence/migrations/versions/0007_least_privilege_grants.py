"""Least-privilege grants: the runtime role must not be able to disable a trigger.

Revision ID: 0007_least_privilege_grants
Revises: 0006_theses
Create Date: 2026-08-30

WHAT THIS CLOSES
``0001``/``0003``/``0006`` attach ``vertex_forbid_mutation`` triggers and claim
the append-only guarantee "holds for every SQL client, not only the ORM". It
did not. The API and the worker connected with the very role that OWNS the
tables (``POSTGRES_USER`` of the official PostgreSQL image, a SUPERUSER), and a
table owner can always::

    ALTER TABLE snapshots DISABLE TRIGGER snapshots_append_only;
    UPDATE snapshots SET content = '{"population":"REAL"}';   -- history rewritten
    DROP TRIGGER snapshots_append_only ON snapshots;

The trigger is not a guarantee against its own owner. The guarantee is
OWNERSHIP: the role that serves requests must not own the tables.

THE ROLE MODEL (provisioned by ``infra/compose/initdb/10-least-privilege-roles.sh``)
  bootstrap superuser  creates the two roles below, then is never used again;
  migration role       owns schema ``public`` and every table; runs Alembic;
  runtime role         used by ``api`` and ``worker``; owns nothing.

WHAT THIS MIGRATION DOES
Grants the runtime role exactly the DML it needs, then REVOKES
``UPDATE``/``DELETE``/``TRUNCATE`` on every table that carries an
``*_append_only`` trigger — so those tables refuse a rewrite at the PRIVILEGE
layer, before the trigger even fires. The append-only table list is DISCOVERED
from ``pg_trigger``, never hardcoded: a future append-only table is covered the
day its trigger exists, with no second list to keep in sync.

WHEN IT DOES NOTHING, AND WHY THAT IS SAID OUT LOUD
When the runtime role does not exist, or when the migration is being run BY the
runtime role itself (single-role development and integration-test databases),
this migration RAISEs a NOTICE and changes nothing. It cannot invent a
separation that the deployment did not provision, and it must not revoke rights
from the only role present — that would break the very database it is fixing.
Such a database is NOT protected. ``infra/compose/check-least-privilege.sh``
is the gate that proves, against a live database, that the separation actually
holds; a NOTICE here is not a pass.
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0007_least_privilege_grants"
down_revision: str | None = "0006_theses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Name of the role used by ``api`` and ``worker``. Overridable so a deployment
#: that renamed it stays covered; validated below because it reaches SQL.
_RUNTIME_ROLE_ENV = "VERTEX_DB_RUNTIME_USER"
_DEFAULT_RUNTIME_ROLE = "vertex_api"
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")

_TIGHTEN = r"""
DO $$
DECLARE
    runtime_role text := current_setting('vertex.runtime_role', true);
    tbl text;
BEGIN
    IF runtime_role IS NULL OR runtime_role = '' THEN
        RAISE NOTICE 'vertex: no runtime role declared; privileges NOT tightened';
        RETURN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = runtime_role) THEN
        RAISE NOTICE 'vertex: role % does not exist; privileges NOT tightened. '
                     'This database is NOT protected against an owner-side '
                     'trigger bypass.', runtime_role;
        RETURN;
    END IF;
    IF runtime_role = current_user THEN
        RAISE NOTICE 'vertex: migrations are running AS the runtime role (%); '
                     'privileges NOT tightened. A single-role database cannot '
                     'enforce append-only against its own owner.', runtime_role;
        RETURN;
    END IF;

    -- Traverse only: no CREATE, so no shadow table beside a protected one.
    EXECUTE format('GRANT USAGE ON SCHEMA public TO %I', runtime_role);
    EXECUTE format('REVOKE CREATE ON SCHEMA public FROM %I', runtime_role);

    -- Baseline DML on everything that exists today.
    EXECUTE format(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I',
        runtime_role);
    EXECUTE format(
        'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I',
        runtime_role);

    -- Append-only tables, DISCOVERED from their own triggers.
    FOR tbl IN
        SELECT DISTINCT c.relname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal
          AND n.nspname = 'public'
          AND t.tgname LIKE '%\_append\_only'
        ORDER BY 1
    LOOP
        EXECUTE format(
            'REVOKE UPDATE, DELETE, TRUNCATE ON public.%I FROM %I', tbl, runtime_role);
        RAISE NOTICE 'vertex: % is append-only for %', tbl, runtime_role;
    END LOOP;

    -- The migration ledger is read-only for the runtime: a service that can
    -- rewrite alembic_version can lie about which schema it is running on.
    EXECUTE format(
        'REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.alembic_version FROM %I',
        runtime_role);

    -- Tables created by LATER migrations inherit the baseline automatically.
    -- (initdb sets the same default; repeated here so a database provisioned
    -- by hand is covered too.)
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
           GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I',
        current_user, runtime_role);
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
           GRANT USAGE, SELECT ON SEQUENCES TO %I',
        current_user, runtime_role);

    RAISE NOTICE 'vertex: privileges tightened for %', runtime_role;
END $$;
"""

_RELAX = """
DO $$
DECLARE
    runtime_role text := current_setting('vertex.runtime_role', true);
BEGIN
    IF runtime_role IS NULL OR runtime_role = ''
       OR NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = runtime_role)
       OR runtime_role = current_user THEN
        RETURN;
    END IF;
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
           REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM %I',
        current_user, runtime_role);
    EXECUTE format(
        'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public
           REVOKE USAGE, SELECT ON SEQUENCES FROM %I',
        current_user, runtime_role);
    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', runtime_role);
    EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM %I', runtime_role);
    EXECUTE format('REVOKE ALL ON SCHEMA public FROM %I', runtime_role);
END $$;
"""


def _runtime_role() -> str:
    role = os.environ.get(_RUNTIME_ROLE_ENV, _DEFAULT_RUNTIME_ROLE).strip()
    if not _IDENTIFIER.match(role):
        raise RuntimeError(
            f"{_RUNTIME_ROLE_ENV} = {role!r} is not a safe SQL identifier "
            "([a-z_][a-z0-9_]*); refusing to build a GRANT statement from it."
        )
    return role


def _run(statement: str) -> None:
    if context.is_offline_mode():
        # Offline (--sql) cannot inspect pg_roles, so it cannot decide whether
        # tightening is safe. Emitting a blind REVOKE could lock a single-role
        # database out of its own tables. The generated script says so instead
        # of pretending.
        op.execute(
            "-- 0007_least_privilege_grants: SKIPPED in offline mode. "
            "Privileges depend on roles that only a live connection can see. "
            "Run this migration online, or apply "
            "infra/compose/initdb/10-least-privilege-roles.sh then "
            "`alembic upgrade head` against the database."
        )
        return
    bind = op.get_bind()
    bind.execute(
        sa.text("SELECT set_config('vertex.runtime_role', :role, true)"),
        {"role": _runtime_role()},
    )
    bind.execute(sa.text(statement))


def upgrade() -> None:
    _run(_TIGHTEN)


def downgrade() -> None:
    _run(_RELAX)
