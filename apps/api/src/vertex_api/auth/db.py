"""Database access of the authentication routes (lazy, per-application).

The application factory stays free of environment reads so the OpenAPI export
remains deterministic; the engine is created lazily on the first request that
needs it, from ``VERTEX_DATABASE_URL``, and cached on ``app.state``. A missing
DSN raises :class:`DatabaseNotConfiguredError` — callers translate it into a
generic 401 (fail-closed: a misconfigured server authenticates nobody and
reveals nothing). DSNs are never stored in the repository.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

__all__ = ["DATABASE_URL_ENV_VAR", "DatabaseNotConfiguredError", "get_engine", "open_db_session"]

DATABASE_URL_ENV_VAR = "VERTEX_DATABASE_URL"

_STATE_ATTR = "vertex_auth_engine"


class DatabaseNotConfiguredError(RuntimeError):
    """``VERTEX_DATABASE_URL`` is not set; authentication cannot operate."""


def get_engine(app: FastAPI) -> Engine:
    """Return the application's engine, creating it from the environment once."""
    engine = getattr(app.state, _STATE_ATTR, None)
    if engine is not None:
        return engine
    url = os.environ.get(DATABASE_URL_ENV_VAR)
    if not url:
        raise DatabaseNotConfiguredError(
            f"{DATABASE_URL_ENV_VAR} is not set: passkey authentication requires "
            "the PostgreSQL runtime database (DSNs are never stored in the repository)"
        )
    engine = create_engine(url)
    setattr(app.state, _STATE_ATTR, engine)
    return engine


@contextmanager
def open_db_session(app: FastAPI) -> Iterator[Session]:
    """Yield an ORM session; the caller commits explicitly, errors roll back."""
    with Session(get_engine(app)) as session:
        yield session
