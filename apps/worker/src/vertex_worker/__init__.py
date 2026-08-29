"""Vertex worker: outbox daemon loop and ingestion chain (dossier 12).

Consumes the transactional outbox (ADR-006) through the
``vertex_persistence`` repository API, dispatches registered topic handlers
and publishes versioned snapshots. Analysis only — this process has no order
capability and never touches broker account data.
"""

__version__ = "0.1.0"
