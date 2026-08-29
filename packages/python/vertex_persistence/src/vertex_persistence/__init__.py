"""Vertex persistence package — PostgreSQL storage, migrations and outbox.

Owns SQLAlchemy models, Alembic migrations, the transactional outbox and the
manual-ledger storage. Per ``docs/02-architecture/MODULE_BOUNDARIES.md`` this
package contains **no financial rules and no decision logic**: it stores and
retrieves versioned facts fail-closed, nothing more.

Hard guarantees enforced here:

- ``observations`` and ``ledger_transactions`` are append-only (SQL triggers
  forbid UPDATE and DELETE; corrections are compensating writes);
- every datetime crossing this boundary must be timezone-aware (naive values
  are rejected, never guessed);
- absence is never coerced to zero; unsupported values raise typed errors;
- no broker-account concept exists anywhere: no account identifier, balance,
  broker position, order or execution column is defined or accepted.
"""

from vertex_persistence.version import PERSISTENCE_VERSION

__all__ = ["PERSISTENCE_VERSION"]
