"""Repository functions of the persistence package (all operate on a Session).

Every function runs inside the caller's transaction and never commits: the
application layer owns transaction boundaries, so a business write and its
outbox message live or die together (ADR-006).
"""

from vertex_persistence.repository.ledger import (
    PositionLotRecord,
    add_position_lot,
    compensate_ledger_event,
    create_portfolio,
    list_position_lots,
    record_ledger_event,
)
from vertex_persistence.repository.observations import insert_observation
from vertex_persistence.repository.outbox import (
    ClaimedOutboxMessage,
    ack_outbox,
    claim_outbox_batch,
    enqueue_outbox,
    fail_outbox,
    reap_expired_leases,
)
from vertex_persistence.repository.snapshots import (
    CurrentSnapshot,
    PublishedSnapshot,
    get_current_snapshot,
    publish_snapshot,
)

__all__ = [
    "insert_observation",
    "PublishedSnapshot",
    "CurrentSnapshot",
    "publish_snapshot",
    "get_current_snapshot",
    "ClaimedOutboxMessage",
    "enqueue_outbox",
    "claim_outbox_batch",
    "ack_outbox",
    "fail_outbox",
    "reap_expired_leases",
    "PositionLotRecord",
    "create_portfolio",
    "add_position_lot",
    "record_ledger_event",
    "compensate_ledger_event",
    "list_position_lots",
]
