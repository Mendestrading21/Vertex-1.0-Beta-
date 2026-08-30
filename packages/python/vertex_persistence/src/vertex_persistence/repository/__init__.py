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
from vertex_persistence.repository.sessions import (
    CredentialRecord,
    IssuedSession,
    ValidatedSession,
    count_credentials,
    create_session,
    get_credential,
    list_active_credentials,
    purge_expired,
    register_credential,
    revoke_session,
    update_sign_count,
    validate_csrf,
    validate_session,
)
from vertex_persistence.repository.snapshots import (
    CurrentSnapshot,
    PublishedSnapshot,
    get_current_snapshot,
    publish_snapshot,
)
from vertex_persistence.repository.theses import (
    CreatedThesis,
    ProjectedThesis,
    RecordedRevision,
    ThesisRecord,
    ThesisRevisionRecord,
    ThesisState,
    ThesisStatus,
    create_thesis,
    list_revisions,
    list_theses,
    project_thesis_state,
    record_thesis_revision,
    review_queue_due,
)

__all__ = [
    "ClaimedOutboxMessage",
    "CreatedThesis",
    "CredentialRecord",
    "CurrentSnapshot",
    "IssuedSession",
    "PositionLotRecord",
    "ProjectedThesis",
    "PublishedSnapshot",
    "RecordedRevision",
    "ThesisRecord",
    "ThesisRevisionRecord",
    "ThesisState",
    "ThesisStatus",
    "ValidatedSession",
    "ack_outbox",
    "add_position_lot",
    "claim_outbox_batch",
    "compensate_ledger_event",
    "count_credentials",
    "create_portfolio",
    "create_session",
    "create_thesis",
    "enqueue_outbox",
    "fail_outbox",
    "get_credential",
    "get_current_snapshot",
    "insert_observation",
    "list_active_credentials",
    "list_position_lots",
    "list_revisions",
    "list_theses",
    "project_thesis_state",
    "publish_snapshot",
    "purge_expired",
    "reap_expired_leases",
    "record_ledger_event",
    "record_thesis_revision",
    "register_credential",
    "review_queue_due",
    "revoke_session",
    "update_sign_count",
    "validate_csrf",
    "validate_session",
]
