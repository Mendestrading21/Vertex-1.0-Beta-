"""Fail-closed session authentication for the Vertex One API.

Real user authentication (passkey/WebAuthn) ships with the full LOT-09; it
does NOT exist yet. The honest consequence, per the fail-closed rule, is that
:func:`require_session` ALWAYS raises HTTP 401 with error code
``AUTH_NOT_IMPLEMENTED``:

- there is no home-grown token, API key or bypass flag;
- no production code path can construct a :class:`SessionContext`;
- tests inject an explicit synthetic session exclusively through
  ``app.dependency_overrides[require_session]``.

An unimplemented capability is named as such — never presented as a pending
automation and never silently allowed through.
"""

from typing import Literal, NoReturn

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict

from vertex_core.contracts.types import NonEmptyStr

__all__ = ["AUTH_NOT_IMPLEMENTED", "SessionContext", "require_session"]

AUTH_NOT_IMPLEMENTED = "AUTH_NOT_IMPLEMENTED"
"""Error code carried by every 401 until a real authenticator exists (LOT-09)."""


class SessionContext(BaseModel):
    """An authenticated session principal.

    ``established_via`` has exactly one member today: ``"TEST_OVERRIDE"``.
    No value representing production authentication exists, so no production
    request can ever carry a valid session; a real member (e.g. WebAuthn) may
    only be added when LOT-09 ships an actual authenticator.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    subject: NonEmptyStr
    established_via: Literal["TEST_OVERRIDE"]


def require_session() -> NoReturn:
    """Reject every request: authentication is not implemented (fail-closed).

    Raises ``HTTPException`` 401 with detail code ``AUTH_NOT_IMPLEMENTED``,
    always. Tests provide an explicit :class:`SessionContext` via
    ``app.dependency_overrides``; production has no session source at all.
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": AUTH_NOT_IMPLEMENTED,
            "message": (
                "authentication is not implemented yet (WebAuthn arrives with LOT-09); "
                "every request is rejected fail-closed"
            ),
        },
        headers={"WWW-Authenticate": "Session"},
    )
