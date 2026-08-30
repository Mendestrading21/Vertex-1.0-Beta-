"""Registry tests: only registered alert_id + expected version may pass."""

from __future__ import annotations

import pytest
from conftest import make_alert_payload

from vertex_ingress_tv.registry import (
    AlertRegistry,
    RegisteredAlert,
    RegistryRejectionReason,
)
from vertex_ingress_tv.schema import parse_alert


def test_known_alert_with_expected_version_is_accepted(registry, registry_audit) -> None:
    decision = registry.check(parse_alert(make_alert_payload()))
    assert decision.accepted is True
    assert decision.entry is not None
    assert decision.entry.alert_id == "syn-market-regime-v1"
    assert decision.rejection is None
    assert registry_audit == []


def test_unknown_alert_id_rejected_and_audited(registry, registry_audit, clock) -> None:
    decision = registry.check(parse_alert(make_alert_payload(alert_id="forged-unknown-v1")))
    assert decision.accepted is False
    assert decision.rejection is not None
    assert decision.rejection.reason is RegistryRejectionReason.UNKNOWN_ALERT_ID
    # Auditable: the sink received the full rejection record.
    assert len(registry_audit) == 1
    audit = registry_audit[0]
    assert audit.alert_id == "forged-unknown-v1"
    assert audit.expected_script_version is None
    assert audit.occurred_at == clock.now
    assert audit.occurred_at.tzinfo is not None


def test_unexpected_script_version_rejected_and_audited(registry, registry_audit) -> None:
    decision = registry.check(parse_alert(make_alert_payload(script_version="2026-08-30.7")))
    assert decision.accepted is False
    assert decision.rejection.reason is RegistryRejectionReason.UNEXPECTED_SCRIPT_VERSION
    assert decision.rejection.observed_script_version == "2026-08-30.7"
    assert decision.rejection.expected_script_version == "2026-08-29.1"
    assert len(registry_audit) == 1


def test_revoked_alert_rejected(registry, registry_audit) -> None:
    decision = registry.check(parse_alert(make_alert_payload(alert_id="syn-revoked-v1")))
    assert decision.accepted is False
    assert decision.rejection.reason is RegistryRejectionReason.ALERT_REVOKED
    assert len(registry_audit) == 1


def test_symbol_mismatch_rejected(registry, registry_audit) -> None:
    decision = registry.check(parse_alert(make_alert_payload(ticker="OTHER")))
    assert decision.accepted is False
    assert decision.rejection.reason is RegistryRejectionReason.SYMBOL_MISMATCH

    decision = registry.check(parse_alert(make_alert_payload(exchange="ELSEWHERE")))
    assert decision.rejection.reason is RegistryRejectionReason.SYMBOL_MISMATCH
    assert len(registry_audit) == 2


def test_interval_mismatch_rejected(registry, registry_audit) -> None:
    decision = registry.check(parse_alert(make_alert_payload(interval="60")))
    assert decision.accepted is False
    assert decision.rejection.reason is RegistryRejectionReason.INTERVAL_MISMATCH


def test_unconstrained_symbol_entry_accepts_any_symbol(registry, registry_audit) -> None:
    alert = parse_alert(
        make_alert_payload(alert_id="syn-macro-cpi-v1", exchange="ANY", ticker="X", interval="D")
    )
    decision = registry.check(alert)
    assert decision.accepted is True
    assert registry_audit == []


def test_duplicate_registry_entries_are_refused(clock) -> None:
    entries = [
        RegisteredAlert(alert_id="dup", expected_script_version="2026-08-29.1"),
        RegisteredAlert(alert_id="dup", expected_script_version="2026-08-29.2"),
    ]
    with pytest.raises(ValueError, match="duplicate registry entry"):
        AlertRegistry(entries, clock=clock, audit_sink=lambda r: None)
