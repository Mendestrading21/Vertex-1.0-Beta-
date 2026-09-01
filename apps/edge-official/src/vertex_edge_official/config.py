"""Environment configuration for official sources, with secret-safe repr."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = ["OfficialSourceConfig"]

SEC_USER_AGENT_ENV = "VERTEX_SEC_USER_AGENT"
FRED_API_KEY_ENV = "VERTEX_FRED_API_KEY"
OPENFIGI_API_KEY_ENV = "VERTEX_OPENFIGI_API_KEY"
TIMEOUT_ENV = "VERTEX_OFFICIAL_SOURCE_TIMEOUT_SECONDS"

_PLACEHOLDERS = {"", "CHANGE_ME", "changeme", "example", "api-key-example"}


def _configured(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped in _PLACEHOLDERS:
        return None
    return stripped


@dataclass(frozen=True, slots=True)
class OfficialSourceConfig:
    """Local configuration only; secrets are excluded from representations."""

    sec_user_agent: str | None
    fred_api_key: str | None = field(repr=False)
    openfigi_api_key: str | None = field(repr=False)
    timeout_seconds: float = 15.0

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> OfficialSourceConfig:
        raw_timeout = environ.get(TIMEOUT_ENV, "15").strip()
        try:
            timeout = float(raw_timeout)
        except ValueError:
            raise ValueError(f"{TIMEOUT_ENV} must be a number") from None
        if not 1 <= timeout <= 60:
            raise ValueError(f"{TIMEOUT_ENV} must be between 1 and 60 seconds")

        user_agent = _configured(environ.get(SEC_USER_AGENT_ENV))
        if user_agent is not None and "example.invalid" in user_agent:
            user_agent = None
        return cls(
            sec_user_agent=user_agent,
            fred_api_key=_configured(environ.get(FRED_API_KEY_ENV)),
            openfigi_api_key=_configured(environ.get(OPENFIGI_API_KEY_ENV)),
            timeout_seconds=timeout,
        )

    def capability_summary(self) -> dict[str, dict[str, str]]:
        """Return configuration availability without exposing any credential."""
        return {
            "sec_edgar": {
                "status": "AVAILABLE" if self.sec_user_agent is not None else "ERROR",
                "reason": "CONFIGURED" if self.sec_user_agent is not None else "USER_AGENT_MISSING",
            },
            "fred_alfred": {
                "status": "AVAILABLE" if self.fred_api_key is not None else "NOT_ENTITLED",
                "reason": "CONFIGURED" if self.fred_api_key is not None else "API_KEY_MISSING",
            },
            "openfigi": {
                "status": "AVAILABLE",
                "reason": (
                    "AUTHENTICATED_QUOTA"
                    if self.openfigi_api_key is not None
                    else "PUBLIC_REDUCED_QUOTA"
                ),
            },
            "ecb_data_portal": {"status": "AVAILABLE", "reason": "NO_AUTH_REQUIRED"},
            "snb_data_portal": {"status": "AVAILABLE", "reason": "NO_AUTH_REQUIRED"},
        }
