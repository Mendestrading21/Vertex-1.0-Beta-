"""Passkey (WebAuthn) authentication routes of the Vertex One API (LOT-09).

Five routes under ``/api/v1/auth``: registration ceremony (options/verify),
authentication ceremony (options/verify) and logout. All verification is
delegated to ``py_webauthn`` with ``rp_id='localhost'`` and the strict
loopback origin allowlist of :mod:`vertex_api.auth.config`; storage is the
``vertex_persistence`` sessions repository (hashes only, never a clear
token).

Fail-closed rules implemented here:

- every rejection answers the generic 401 (code ``AUTH_REQUIRED``) — no
  cause detail, no resource existence, no library error text ever reaches
  the client;
- bootstrap single-user rule: the FIRST registration is free ONLY while the
  credential table is completely empty (revoked credentials count); as soon
  as one credential exists — revoked or not — registering requires a valid
  authenticated session, re-checked at both the options AND the verify step
  so a race cannot widen the window;
- WebAuthn sign counters are enforced by the repository, not by the library:
  ``verify_authentication_response`` is called with
  ``credential_current_sign_count=0`` on purpose, because the library can
  only reject a regression, while ``update_sign_count`` rejects it AND
  revokes the cloned credential with all its sessions in the same
  transaction (committed even though the login fails);
- session and CSRF tokens travel exclusively as cookies (``vertex_session``
  HttpOnly, ``vertex_csrf`` readable for the double-submit header), both
  ``SameSite=Strict`` and ``Secure`` by default (see config for the
  documented loopback-dev opt-out), lifetime 8 h.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    options_to_json_dict,
    parse_authentication_credential_json,
    parse_registration_credential_json,
)
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
)

from vertex_api.auth.challenges import ChallengeStore
from vertex_api.auth.config import AuthConfig, load_auth_config
from vertex_api.auth.db import DatabaseNotConfiguredError, open_db_session
from vertex_api.auth.dependencies import (
    CSRF_COOKIE_NAME,
    SESSION_COOKIE_NAME,
    SessionContext,
    authenticate_request,
    require_session,
    unauthorized,
    utc_now,
)
from vertex_api.auth.schemas import (
    CeremonyOptionsResponse,
    LoginVerifyRequest,
    LoginVerifyResponse,
    LogoutResponse,
    RegisterVerifyRequest,
    RegisterVerifyResponse,
)
from vertex_persistence.errors import AuthStorageError, SignCountRegressionError
from vertex_persistence.repository.sessions import (
    count_credentials,
    create_session,
    get_credential,
    list_active_credentials,
    purge_expired,
    register_credential,
    revoke_session,
    update_sign_count,
)

__all__ = ["auth_router", "get_challenge_store"]

# Stable, non-secret user handle of the single local user (WebAuthn user id).
_USER_HANDLE = b"vertex-one-local-user"
_USER_NAME = "vertex"

auth_router = APIRouter(
    prefix="/api/v1/auth",
    responses={
        401: {
            "description": (
                "Authentication failed. Always the same generic body "
                "(code AUTH_REQUIRED) whatever the cause."
            )
        }
    },
)


def get_challenge_store(request: Request) -> ChallengeStore:
    """The per-application challenge store (created in ``create_app``)."""
    store = getattr(request.app.state, "challenge_store", None)
    if store is None:  # pragma: no cover - create_app always installs one
        raise unauthorized()
    return store


def _auth_config() -> AuthConfig:
    return load_auth_config(os.environ)


def _require_session_if_bootstrapped(request: Request, db: Session) -> None:
    """Registration gate: free ONLY while no credential exists at all."""
    if count_credentials(db) == 0:
        return
    # At least one credential (even revoked) exists: only an authenticated
    # session may add another one. authenticate_request enforces CSRF too
    # (POST is a mutating method).
    authenticate_request(request)


def _transports_of(credential: dict) -> Optional[str]:
    """Best-effort comma-joined transports hint from the client response."""
    response = credential.get("response")
    if not isinstance(response, dict):
        return None
    transports = response.get("transports")
    if not isinstance(transports, list):
        return None
    values = [item for item in transports if isinstance(item, str) and item]
    return ",".join(values) if values else None


def _set_session_cookies(
    response: Response, *, config: AuthConfig, session_token: str, csrf_token: str
) -> None:
    max_age = int(config.session_ttl.total_seconds())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        path="/",
        secure=config.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    # Readable by the page on purpose: its value must be echoed back in the
    # X-Vertex-CSRF header on every mutation (double submit).
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        path="/",
        secure=config.cookie_secure,
        httponly=False,
        samesite="strict",
    )


def _clear_session_cookies(response: Response, *, config: AuthConfig) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=config.cookie_secure,
        httponly=True,
        samesite="strict",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=config.cookie_secure,
        httponly=False,
        samesite="strict",
    )


@auth_router.post(
    "/register/options",
    operation_id="post_auth_register_options",
    response_model=CeremonyOptionsResponse,
    summary="Start a passkey registration ceremony",
)
def post_register_options(
    request: Request,
    store: ChallengeStore = Depends(get_challenge_store),
) -> CeremonyOptionsResponse:
    """Issue registration options. Free only for the very first credential."""
    config = _auth_config()
    try:
        with open_db_session(request.app) as db:
            _require_session_if_bootstrapped(request, db)
            exclude = [
                PublicKeyCredentialDescriptor(id=record.credential_id)
                for record in list_active_credentials(db)
            ]
    except DatabaseNotConfiguredError:
        raise unauthorized() from None
    flow_id, challenge = store.issue("register")
    options = generate_registration_options(
        rp_id=config.rp_id,
        rp_name=config.rp_name,
        user_id=_USER_HANDLE,
        user_name=_USER_NAME,
        challenge=challenge,
        exclude_credentials=exclude or None,
    )
    return CeremonyOptionsResponse(flow_id=flow_id, options=options_to_json_dict(options))


@auth_router.post(
    "/register/verify",
    operation_id="post_auth_register_verify",
    response_model=RegisterVerifyResponse,
    summary="Finish a passkey registration ceremony",
)
def post_register_verify(
    request: Request,
    body: RegisterVerifyRequest,
    store: ChallengeStore = Depends(get_challenge_store),
) -> RegisterVerifyResponse:
    """Verify the attestation response and store the credential."""
    config = _auth_config()
    challenge = store.consume(body.flow_id, "register")
    if challenge is None:
        raise unauthorized()
    try:
        with open_db_session(request.app) as db:
            # Re-checked here (not only at the options step): a registration
            # completed after someone else bootstrapped must not slip through.
            _require_session_if_bootstrapped(request, db)
            try:
                parsed = parse_registration_credential_json(body.credential)
                verification = verify_registration_response(
                    credential=parsed,
                    expected_challenge=challenge,
                    expected_rp_id=config.rp_id,
                    expected_origin=list(config.expected_origins),
                    require_user_verification=True,
                )
            except WebAuthnException:
                raise unauthorized() from None
            try:
                register_credential(
                    db,
                    credential_id=verification.credential_id,
                    public_key=verification.credential_public_key,
                    sign_count=verification.sign_count,
                    transports=_transports_of(body.credential),
                    label=body.label,
                    now=utc_now(),
                )
            except AuthStorageError:
                raise unauthorized() from None
            db.commit()
    except DatabaseNotConfiguredError:
        raise unauthorized() from None
    return RegisterVerifyResponse(registered=True, label=body.label)


@auth_router.post(
    "/login/options",
    operation_id="post_auth_login_options",
    response_model=CeremonyOptionsResponse,
    summary="Start a passkey authentication ceremony",
)
def post_login_options(
    request: Request,
    store: ChallengeStore = Depends(get_challenge_store),
) -> CeremonyOptionsResponse:
    """Issue authentication options restricted to the registered passkeys."""
    config = _auth_config()
    try:
        with open_db_session(request.app) as db:
            credentials = list_active_credentials(db)
    except DatabaseNotConfiguredError:
        raise unauthorized() from None
    if not credentials:
        # No registered passkey: nothing can authenticate. Same generic 401
        # (no enumeration of the server's registration state).
        raise unauthorized()
    flow_id, challenge = store.issue("login")
    options = generate_authentication_options(
        rp_id=config.rp_id,
        challenge=challenge,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=record.credential_id) for record in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    return CeremonyOptionsResponse(flow_id=flow_id, options=options_to_json_dict(options))


@auth_router.post(
    "/login/verify",
    operation_id="post_auth_login_verify",
    response_model=LoginVerifyResponse,
    summary="Finish a passkey authentication ceremony and open a session",
)
def post_login_verify(
    request: Request,
    body: LoginVerifyRequest,
    response: Response,
    store: ChallengeStore = Depends(get_challenge_store),
) -> LoginVerifyResponse:
    """Verify the assertion, enforce the sign counter, issue the session."""
    config = _auth_config()
    challenge = store.consume(body.flow_id, "login")
    if challenge is None:
        raise unauthorized()
    now = utc_now()
    try:
        with open_db_session(request.app) as db:
            try:
                parsed = parse_authentication_credential_json(body.credential)
            except WebAuthnException:
                raise unauthorized() from None
            record = get_credential(db, credential_id=parsed.raw_id)
            if record is None or record.revoked_at is not None:
                raise unauthorized()
            try:
                verification = verify_authentication_response(
                    credential=parsed,
                    expected_challenge=challenge,
                    expected_rp_id=config.rp_id,
                    expected_origin=list(config.expected_origins),
                    credential_public_key=record.public_key,
                    # 0 on purpose: the repository owns counter enforcement
                    # (regression -> revocation), see the module docstring.
                    credential_current_sign_count=0,
                    require_user_verification=True,
                )
            except WebAuthnException:
                raise unauthorized() from None
            try:
                update_sign_count(
                    db,
                    credential_id=record.credential_id,
                    new_sign_count=verification.new_sign_count,
                    now=now,
                )
            except SignCountRegressionError:
                # Clone detected: PERSIST the revocation of the credential and
                # all its sessions, then fail the login closed.
                db.commit()
                raise unauthorized() from None
            purge_expired(db, now=now)
            issued = create_session(
                db, credential_id=record.credential_id, now=now, ttl=config.session_ttl
            )
            db.commit()
    except DatabaseNotConfiguredError:
        raise unauthorized() from None
    _set_session_cookies(
        response,
        config=config,
        session_token=issued.session_token,
        csrf_token=issued.csrf_token,
    )
    expires_at = issued.expires_at.isoformat().replace("+00:00", "Z")
    return LoginVerifyResponse(authenticated=True, expires_at=expires_at)


@auth_router.post(
    "/logout",
    operation_id="post_auth_logout",
    response_model=LogoutResponse,
    summary="Revoke the current session and clear its cookies",
)
def post_logout(
    request: Request,
    response: Response,
    _session: SessionContext = Depends(require_session),
) -> LogoutResponse:
    """Revoke the presented session server-side (requires session + CSRF)."""
    config = _auth_config()
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:  # pragma: no cover - require_session already rejected this
        raise unauthorized()
    try:
        with open_db_session(request.app) as db:
            revoke_session(db, session_token=token, now=utc_now())
            db.commit()
    except DatabaseNotConfiguredError:
        raise unauthorized() from None
    _clear_session_cookies(response, config=config)
    return LogoutResponse(logged_out=True)
