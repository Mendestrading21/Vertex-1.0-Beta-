"""Bounded HTTPS transport shared by the official-source adapters.

Hosts are allowlisted by each client. Redirects are refused so a provider
cannot silently move a request (and its credentials) to another origin.
Errors never include URLs because FRED carries its API key in the query string.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit

__all__ = [
    "HttpRequest",
    "HttpResponse",
    "HttpTransport",
    "OfficialSourceError",
    "UrllibTransport",
]

DEFAULT_MAX_BODY_BYTES = 5 * 1024 * 1024


class OfficialSourceError(RuntimeError):
    """A redacted, fail-closed source or transport failure."""


@dataclass(frozen=True, slots=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None = None
    timeout_seconds: float = 15.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes
    received_at: datetime


@runtime_checkable
class HttpTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class UrllibTransport:
    """Small standard-library transport with an exact HTTPS host allowlist."""

    def __init__(
        self,
        *,
        allowed_hosts: frozenset[str],
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        if not allowed_hosts or any(not host for host in allowed_hosts):
            raise ValueError("allowed_hosts must contain at least one non-empty host")
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        self._allowed_hosts = allowed_hosts
        self._max_body_bytes = max_body_bytes
        self._opener = urllib.request.build_opener(_NoRedirect())

    def send(self, request: HttpRequest) -> HttpResponse:
        parsed = urlsplit(request.url)
        if parsed.scheme != "https" or parsed.hostname not in self._allowed_hosts:
            raise OfficialSourceError("request target is outside the approved HTTPS allowlist")
        if request.method not in {"GET", "POST"}:
            raise OfficialSourceError("request method is not allowed")
        if request.timeout_seconds <= 0:
            raise OfficialSourceError("request timeout must be positive")

        raw_request = urllib.request.Request(  # noqa: S310 (scheme + host validated above)
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with self._opener.open(
                raw_request, timeout=request.timeout_seconds
            ) as response:
                body = response.read(self._max_body_bytes + 1)
                if len(body) > self._max_body_bytes:
                    raise OfficialSourceError("provider response exceeds the configured body limit")
                return HttpResponse(
                    status_code=int(response.status),
                    headers={str(k).lower(): str(v) for k, v in response.headers.items()},
                    body=body,
                    received_at=datetime.now(UTC),
                )
        except urllib.error.HTTPError as exc:
            raise OfficialSourceError(f"provider returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise OfficialSourceError("provider transport failed") from None
