"""Vertex AI routes against real PostgreSQL, real passkey auth and CSRF.

No dependency override anywhere: the explained ``analysis/{instrument}``
snapshot is produced by a bounded run of the REAL worker over SYNTHETIC
bars and option chains, then ``POST /api/v1/ai/explain`` is called with a
real WebAuthn session cookie and the CSRF double-submit header.

Hard proofs:

- every ``evidence_ref`` of every claim is RESOLVED against the persisted
  snapshot — the referenced value is actually found at the path the
  evidence catalog declares, not merely present as a field;
- ``limitations`` carries the B-05 notice and ``provider`` is
  ``DETERMINISTIC_TEMPLATE`` (never presented as a model);
- no transaction vocabulary and no probability wording appears anywhere in
  the produced texts (full scan of claims, contradictions, missing data and
  limitations);
- an unknown subject is a clean 404, an anonymous call a generic 401, and
  ``GET /api/v1/ai/status`` reports DISABLED / B-05_HUMAN_DECISION_PENDING.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator, Mapping

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from soft_passkey import SoftPasskey, login_passkey, register_passkey
from vertex_core.synthetic import (
    generate_daily_bar_envelopes,
    generate_option_chain_envelopes,
)
from vertex_persistence.enums import OutboxStatus
from vertex_persistence.models import OutboxMessage
from vertex_persistence.repository.snapshots import get_current_snapshot
from vertex_worker.analysis import SNAPSHOT_KIND_ANALYSIS
from vertex_worker.handlers import DEV_SYNTHETIC_CONFIG, build_registry
from vertex_worker.ingest import ingest_envelope
from vertex_worker.runner import WorkerRunner

CSRF_HEADER = "X-Vertex-CSRF"
CSRF_COOKIE = "vertex_csrf"

INSTRUMENT = "SYN-TECH-01"
UNKNOWN_INSTRUMENT = "SYN-TECH-99"

NOW = datetime.now(timezone.utc).replace(microsecond=0)
BASE_TIME = NOW - timedelta(minutes=30)
SEED = 20260825

LIMITATION_B05 = (
    "Fournisseur IA désactivé — décision B-05 en attente ; "
    "explication par gabarit déterministe"
)

# Vocabulary that may NEVER appear in an explanation: transaction
# instructions and predictive-probability wording.
FORBIDDEN_WORDS = (
    "acheter",
    "achat",
    "achete",
    "vendre",
    "vente",
    "vends",
    "ordre",
    "ordres",
    "order",
    "orders",
    "buy",
    "sell",
    "trade",
    "trader",
    "executer",
    "execute",
    "position a prendre",
    "probabilite",
    "probabilites",
    "probability",
    "proba",
    "chance",
    "chances",
    "likelihood",
    "odds",
)


def _fold(text: str) -> str:
    """Lowercase, accent-folded text for a robust vocabulary scan."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


@pytest.fixture()
def authenticated(client: TestClient, passkey: SoftPasskey) -> TestClient:
    register_passkey(client, passkey)
    assert login_passkey(client, passkey).status_code == 200
    return client


@pytest.fixture()
def db_session(database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


@pytest.fixture()
def published_analysis(database_url: str) -> Any:
    """Seed SYNTHETIC bars + chains and run the REAL worker to completion."""
    engine = create_engine(database_url)

    def factory() -> Session:
        return Session(engine)

    try:
        with factory() as session:
            for envelope in (
                *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
                *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
            ):
                ingest_envelope(session, envelope)
            session.commit()

        clock = lambda: datetime.now(timezone.utc)  # noqa: E731
        runner = WorkerRunner(
            session_factory=factory,
            registry=build_registry(clock=clock, fusion_config=DEV_SYNTHETIC_CONFIG),
            poll_interval_seconds=0.05,
            clock=clock,
        )
        runner.drain(max_batches=60)
        stats = runner.stats()
        assert stats.failed == 0 and stats.dead == 0 and stats.lease_lost == 0
        with factory() as session:
            remaining = session.execute(
                select(func.count())
                .select_from(OutboxMessage)
                .where(OutboxMessage.status != OutboxStatus.DONE.value)
            ).scalar_one()
            assert remaining == 0
            snapshot = get_current_snapshot(
                session, kind=SNAPSHOT_KIND_ANALYSIS, key=INSTRUMENT
            )
        assert snapshot is not None
        yield snapshot
    finally:
        engine.dispose()


def _csrf(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(CSRF_COOKIE)
    assert token
    return {CSRF_HEADER: token}


def _resolve(
    evidence_id: str, path: str, *, content: Mapping[str, Any], self_ref: str
) -> bool:
    """Really resolve one catalog reference INSIDE the persisted snapshot.

    Walks to the declared path and compares the value found there with the
    referenced id — a missing path, a missing key or a different value is a
    failed resolution (a mere field presence proves nothing).
    """
    if path.startswith("analysis/"):  # the snapshot's own reference
        return evidence_id == self_ref
    if path == "advice.advice_id":
        return content.get("advice", {}).get("advice_id") == evidence_id
    if path == "bars.source_event_id":
        return content.get("bars", {}).get("source_event_id") == evidence_id
    if path == "scenarios.calculation":
        calculation = content.get("scenarios", {}).get("calculation")
        return (
            isinstance(calculation, Mapping)
            and calculation.get("input_hash") == evidence_id
        )
    if path == "evidence.clusters[]":
        clusters = content.get("evidence", {}).get("clusters", [])
        return any(
            isinstance(cluster, Mapping)
            and cluster.get("cluster_id") == evidence_id
            for cluster in clusters
        )
    raise AssertionError(f"unknown evidence path {path!r} for {evidence_id!r}")


class TestAiStatus:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        response = client.get("/api/v1/ai/status")
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_status_is_disabled_pending_b05(self, authenticated: TestClient) -> None:
        response = authenticated.get("/api/v1/ai/status")
        assert response.status_code == 200
        assert response.json() == {
            "provider": "DISABLED",
            "reason": "B-05_HUMAN_DECISION_PENDING",
            "deterministic_template_available": True,
        }


class TestAiExplain:
    def test_requires_a_real_session(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/ai/explain",
            json={"subject": {"kind": "analysis", "key": INSTRUMENT}, "locale": "fr"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_mutation_without_csrf_is_generic_401(
        self, authenticated: TestClient
    ) -> None:
        response = authenticated.post(
            "/api/v1/ai/explain",
            json={"subject": {"kind": "analysis", "key": INSTRUMENT}, "locale": "fr"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_unknown_subject_is_a_clean_404(
        self, authenticated: TestClient, published_analysis: Any
    ) -> None:
        response = authenticated.post(
            "/api/v1/ai/explain",
            json={
                "subject": {"kind": "analysis", "key": UNKNOWN_INSTRUMENT},
                "locale": "fr",
            },
            headers=_csrf(authenticated),
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "NO_SNAPSHOT_FOR_SUBJECT"

    def test_every_evidence_ref_resolves_in_the_published_snapshot(
        self, authenticated: TestClient, published_analysis: Any
    ) -> None:
        snapshot = published_analysis
        content = snapshot.content

        response = authenticated.post(
            "/api/v1/ai/explain",
            json={"subject": {"kind": "analysis", "key": INSTRUMENT}, "locale": "fr"},
            headers=_csrf(authenticated),
        )
        assert response.status_code == 200, response.text
        answer = response.json()

        # -- the answer is the deterministic template, never a model -------
        assert answer["provider"] == "DETERMINISTIC_TEMPLATE"
        assert answer["template_version"] == "vertex.ai-deterministic-template/1.0"
        assert answer["subject"] == {"kind": "analysis", "key": INSTRUMENT}
        assert answer["locale"] == "fr"
        assert answer["snapshot_version"] == snapshot.version

        # -- the B-05 notice is always carried ------------------------------
        assert LIMITATION_B05 in answer["limitations"]
        assert answer["limitations"][0] == LIMITATION_B05
        assert "SYNTHETIC development population" in answer["limitations"]

        # -- every catalog entry really resolves in the persisted snapshot --
        self_ref = f"snapshot:analysis/{INSTRUMENT}/v{snapshot.version}"
        catalog = answer["evidence_catalog"]
        assert catalog
        catalog_ids = {entry["evidence_id"] for entry in catalog}
        assert self_ref in catalog_ids
        for entry in catalog:
            assert _resolve(
                entry["evidence_id"],
                entry["path"],
                content=content,
                self_ref=self_ref,
            ), entry
        by_id = {entry["evidence_id"]: entry for entry in catalog}

        # The catalog covers the facts this dossier really holds.
        assert content["advice"]["advice_id"] in catalog_ids
        assert content["bars"]["source_event_id"] in catalog_ids
        assert content["scenarios"]["calculation"]["input_hash"] in catalog_ids

        # -- every claim reference resolves, claim by claim, ref by ref -----
        claims = answer["claims"]
        assert claims
        for claim in claims:
            assert claim["kind"] == "FACT"
            assert claim["evidence_refs"]
            for reference in claim["evidence_refs"]:
                assert reference in by_id, (claim, reference)
                assert _resolve(
                    reference,
                    by_id[reference]["path"],
                    content=content,
                    self_ref=self_ref,
                ), (claim, reference)

        # The verdict really explained is the persisted one, verbatim.
        status = content["advice"]["status"]
        assert f"Statut du verdict : {status}." in [c["text"] for c in claims]

        # -- contradictions mirror the snapshot's CLOSED gates --------------
        blocked = {
            gate["gate_id"]: gate["reason_code"]
            for gate in content["advice"]["gates"]
            if gate["status"] == "BLOCK"
        }
        assert blocked
        assert {
            contradiction["reference"] for contradiction in answer["contradictions"]
        } == set(blocked)
        for contradiction in answer["contradictions"]:
            assert contradiction["code"] == blocked[contradiction["reference"]]

        # -- no transaction vocabulary, no probability wording --------------
        texts = [
            *[claim["text"] for claim in claims],
            *[c["text"] for c in answer["contradictions"]],
            *answer["missing_data"],
            *answer["limitations"],
        ]
        assert texts
        for text in texts:
            folded = _fold(text)
            for word in FORBIDDEN_WORDS:
                assert re.search(rf"\b{re.escape(word)}\b", folded) is None, (
                    word,
                    text,
                )
            assert "%" not in text

    def test_answer_is_deterministic_for_one_snapshot(
        self, authenticated: TestClient, published_analysis: Any
    ) -> None:
        body = {"subject": {"kind": "analysis", "key": INSTRUMENT}, "locale": "fr"}
        first = authenticated.post(
            "/api/v1/ai/explain", json=body, headers=_csrf(authenticated)
        )
        second = authenticated.post(
            "/api/v1/ai/explain", json=body, headers=_csrf(authenticated)
        )
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()
