"""Registry of authorized TradingView alerts (fail-closed, auditable).

Only alerts that were explicitly registered (``alert_id`` + expected
``script_version``) may enter the ingestion pipeline. Anything else — unknown
id, unexpected script version, revoked entry, mismatching symbol/interval — is
rejected with an auditable :class:`RegistryRejection` pushed to the injected
audit sink. A rejection is never silent and never guessed away.

The registry never fetches anything remotely and holds no secret: it is a pure
in-memory policy object, hydrated by the caller (later: from PostgreSQL).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Callable, Dict, Iterable, Optional

from vertex_ingress_tv.schema import TradingViewAlertV1

__all__ = [
    "AlertRegistry",
    "RegisteredAlert",
    "RegistryDecision",
    "RegistryRejection",
    "RegistryRejectionReason",
]


@unique
class RegistryRejectionReason(str, Enum):
    """Auditable rejection reasons (no payload content, safe to log)."""

    UNKNOWN_ALERT_ID = "UNKNOWN_ALERT_ID"
    ALERT_REVOKED = "ALERT_REVOKED"
    UNEXPECTED_SCRIPT_VERSION = "UNEXPECTED_SCRIPT_VERSION"
    SYMBOL_MISMATCH = "SYMBOL_MISMATCH"
    INTERVAL_MISMATCH = "INTERVAL_MISMATCH"


@dataclass(frozen=True)
class RegisteredAlert:
    """One authorized alert configuration.

    ``expected_script_version`` pins the exact Pine script version: any script
    or parameter change requires recreating the TradingView alert AND updating
    this entry (docs/08-runbooks/TRADINGVIEW_SETUP.md).
    Optional expectations (exchange/ticker/interval) tighten the check when
    provided; ``None`` means "not constrained", never "anything goes silently".
    """

    alert_id: str
    expected_script_version: str
    expected_exchange: Optional[str] = None
    expected_ticker: Optional[str] = None
    expected_interval: Optional[str] = None
    active: bool = True


@dataclass(frozen=True)
class RegistryRejection:
    """Auditable record of one refused alert."""

    reason: RegistryRejectionReason
    alert_id: str
    observed_script_version: str
    expected_script_version: Optional[str]
    occurred_at: datetime
    detail: str = ""


@dataclass(frozen=True)
class RegistryDecision:
    """Outcome of a registry check: accepted entry or auditable rejection."""

    accepted: bool
    entry: Optional[RegisteredAlert] = None
    rejection: Optional[RegistryRejection] = None


class AlertRegistry:
    """In-memory registry with an injected clock and audit sink.

    ``clock`` must return a timezone-aware UTC datetime (no real clock in
    tests). ``audit_sink`` receives EVERY rejection before the decision is
    returned, which makes each refusal auditable by construction.
    """

    def __init__(
        self,
        entries: Iterable[RegisteredAlert],
        *,
        clock: Callable[[], datetime],
        audit_sink: Callable[[RegistryRejection], None],
    ) -> None:
        self._entries: Dict[str, RegisteredAlert] = {}
        for entry in entries:
            if entry.alert_id in self._entries:
                raise ValueError(f"duplicate registry entry for alert_id {entry.alert_id!r}")
            self._entries[entry.alert_id] = entry
        self._clock = clock
        self._audit_sink = audit_sink

    def _reject(
        self,
        reason: RegistryRejectionReason,
        alert: TradingViewAlertV1,
        expected_script_version: Optional[str],
        detail: str = "",
    ) -> RegistryDecision:
        now = self._clock()
        if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
            raise ValueError("registry clock must return timezone-aware UTC datetimes")
        rejection = RegistryRejection(
            reason=reason,
            alert_id=alert.alert_id,
            observed_script_version=alert.script_version,
            expected_script_version=expected_script_version,
            occurred_at=now,
            detail=detail,
        )
        self._audit_sink(rejection)
        return RegistryDecision(accepted=False, rejection=rejection)

    def check(self, alert: TradingViewAlertV1) -> RegistryDecision:
        """Decide whether ``alert`` is authorized (fail-closed)."""
        entry = self._entries.get(alert.alert_id)
        if entry is None:
            return self._reject(
                RegistryRejectionReason.UNKNOWN_ALERT_ID, alert, None, "alert_id not registered"
            )
        if not entry.active:
            return self._reject(
                RegistryRejectionReason.ALERT_REVOKED,
                alert,
                entry.expected_script_version,
                "entry is revoked/inactive",
            )
        if alert.script_version != entry.expected_script_version:
            return self._reject(
                RegistryRejectionReason.UNEXPECTED_SCRIPT_VERSION,
                alert,
                entry.expected_script_version,
                "script_version differs from the registered version",
            )
        if entry.expected_exchange is not None and alert.exchange != entry.expected_exchange:
            return self._reject(
                RegistryRejectionReason.SYMBOL_MISMATCH,
                alert,
                entry.expected_script_version,
                "exchange differs from the registered exchange",
            )
        if entry.expected_ticker is not None and alert.ticker != entry.expected_ticker:
            return self._reject(
                RegistryRejectionReason.SYMBOL_MISMATCH,
                alert,
                entry.expected_script_version,
                "ticker differs from the registered ticker",
            )
        if entry.expected_interval is not None and alert.interval != entry.expected_interval:
            return self._reject(
                RegistryRejectionReason.INTERVAL_MISMATCH,
                alert,
                entry.expected_script_version,
                "interval differs from the registered interval",
            )
        return RegistryDecision(accepted=True, entry=entry)
