"""Session authentication dependency of the protected routes (fail-closed).

``require_session`` validates the opaque session cookie against the
``auth_sessions`` table (hash lookup, expiry, revocation, credential
revocation) and, for every mutating HTTP method, enforces the CSRF
double-submit contract: the ``X-Vertex-CSRF`` header must equal the
non-HttpOnly CSRF cookie AND hash to the value stored with the session.

Every rejection — missing cookie, unknown/expired/revoked session, CSRF
mismatch, even a missing database configuration — answers the same generic
401 with code ``AUTH_REQUIRED`` and no further detail (an authentication
error never reveals resource existence or server state).

UN SEUL contournement existe, et il est DECLARE : la variable
d'environnement ``VERTEX_AUTH_OPEN_LOCAL=1`` fait rendre a cette dependance
une session ``LOCAL_OPEN`` sans rien verifier. Elle a ete ajoutee le
2026-09-01 a la demande explicite du proprietaire du poste, qui ne voulait
plus saisir de passkey pour ouvrir SON terminal local.

Ce que cela coute, ecrit ici plutot que tu : l'API ecoute sur 127.0.0.1, donc
sans session TOUT ce qui atteint la boucle locale de cette machine lit le
portefeuille et les analyses. Sur un poste personnel c'est une decision
legitime de son proprietaire ; sur une machine partagee ce serait une faille.

En dehors de ce drapeau, rien n'a change : aucun en-tete, aucun cookie,
aucune autre configuration ne fait aboutir cette dependance sans une ligne de
session vivante en base. La valeur PAR DEFAUT reste fermee — une
installation qui ne declare pas la variable se comporte exactement comme
avant. Les tests, eux, surchargent la dependance explicitement (contexte
synthetique ``TEST_OVERRIDE``) ou creent une vraie session.
"""

from __future__ import annotations

import hmac
import os
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from vertex_api.auth.db import DatabaseNotConfiguredError, open_db_session
from vertex_core.contracts.types import NonEmptyStr
from vertex_persistence.repository.sessions import (
    ValidatedSession,
    validate_csrf,
    validate_session,
)

__all__ = [
    "AUTH_REQUIRED",
    "CSRF_COOKIE_NAME",
    "CSRF_HEADER_NAME",
    "OPEN_LOCAL_ENV_VAR",
    "OPEN_LOCAL_SUBJECT",
    "SESSION_COOKIE_NAME",
    "SessionContext",
    "authenticate_request",
    "open_local_access",
    "require_session",
    "unauthorized",
    "utc_now",
]

AUTH_REQUIRED = "AUTH_REQUIRED"
"""Error code of every generic 401: authentication required, no detail."""

SESSION_COOKIE_NAME = "vertex_session"
CSRF_COOKIE_NAME = "vertex_csrf"
CSRF_HEADER_NAME = "X-Vertex-CSRF"

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

OPEN_LOCAL_ENV_VAR = "VERTEX_AUTH_OPEN_LOCAL"
"""Ouvre les routes protegees SANS session. Voir l'en-tete du module."""

OPEN_LOCAL_SUBJECT = "acces-local-ouvert"
"""Sujet porte par la session ouverte : reconnaissable dans un journal."""


def open_local_access() -> bool:
    """L'acces local ouvert est-il demande ?

    Lu a CHAQUE appel plutot qu'au chargement du module : un test qui pose la
    variable avec `monkeypatch` doit voir l'effet, et un import fige rendrait
    ce comportement dependant de l'ordre des imports.

    SEULE la valeur "1" active l'ouverture. Ni "0", ni "false", ni une chaine
    vide, ni "true" : un drapeau de securite ne doit pas s'activer sur une
    valeur approchante posee par megarde.
    """
    return os.environ.get(OPEN_LOCAL_ENV_VAR) == "1"


class SessionContext(BaseModel):
    """An authenticated session principal.

    ``established_via`` dit COMMENT la session a ete etablie, et ne ment
    jamais :

    - ``"WEBAUTHN"`` : une vraie passkey, verifiee en base ;
    - ``"LOCAL_OPEN"`` : AUCUNE verification — l'acces local ouvert est
      declare par ``VERTEX_AUTH_OPEN_LOCAL=1``. Le nom le dit plutot que de
      se faire passer pour une authentification ;
    - ``"TEST_OVERRIDE"`` : uniquement pour un ``app.dependency_overrides``
      explicite en test ; aucun chemin de production ne le construit.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    subject: NonEmptyStr
    established_via: Literal["WEBAUTHN", "TEST_OVERRIDE", "LOCAL_OPEN"]


def utc_now() -> datetime:
    """Aware UTC instant — the only clock read of the auth adapter."""
    return datetime.now(UTC)


def unauthorized() -> HTTPException:
    """The single, generic 401. Same shape for every rejection cause."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": AUTH_REQUIRED, "message": "authentication required"},
        headers={"WWW-Authenticate": "Session"},
    )


def _check_csrf(request: Request, validated: ValidatedSession) -> None:
    """Enforce the CSRF double-submit contract on mutating methods."""
    header_value = request.headers.get(CSRF_HEADER_NAME)
    cookie_value = request.cookies.get(CSRF_COOKIE_NAME)
    if not header_value or not cookie_value:
        raise unauthorized()
    if not hmac.compare_digest(header_value, cookie_value):
        raise unauthorized()
    if not validate_csrf(validated, header_value):
        raise unauthorized()


def authenticate_request(request: Request) -> ValidatedSession:
    """Validate the session cookie (and CSRF for mutations) or raise 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise unauthorized()
    try:
        with open_db_session(request.app) as db:
            validated = validate_session(db, session_token=token, now=utc_now())
    except DatabaseNotConfiguredError:
        # Fail closed with the same generic 401: a server that cannot check
        # sessions authenticates nobody and explains nothing to the client.
        raise unauthorized() from None
    if validated is None:
        raise unauthorized()
    if request.method.upper() not in _SAFE_METHODS:
        _check_csrf(request, validated)
    return validated


def require_session(request: Request) -> SessionContext:
    """FastAPI dependency of every protected route (see module docstring).

    Avec ``VERTEX_AUTH_OPEN_LOCAL=1``, rend une session ``LOCAL_OPEN`` sans
    lire de cookie, sans toucher la base et sans verifier le CSRF. Le nom du
    sujet et de l'origine disent clairement que RIEN n'a ete authentifie :
    un journal qui montre ``LOCAL_OPEN`` ne doit pas se lire comme une
    connexion reussie.
    """
    if open_local_access():
        return SessionContext(
            subject=OPEN_LOCAL_SUBJECT, established_via="LOCAL_OPEN"
        )
    validated = authenticate_request(request)
    return SessionContext(subject=validated.credential_label, established_via="WEBAUTHN")
