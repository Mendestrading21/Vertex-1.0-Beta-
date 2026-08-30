"""Application factory of the Vertex One API.

``create_app`` builds a deterministic FastAPI application: fixed route order,
explicit ``operation_id`` on every route and an OpenAPI document whose
component set is completed with the request contract — so two fresh
applications always render byte-identical OpenAPI output (see
``vertex_api.openapi_export``).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import PendingRollbackError, StatementError

from vertex_api.ai_explain import AiExplainRequest, AiGroundingError
from vertex_api.auth import auth_router
from vertex_api.auth.challenges import ChallengeStore
from vertex_api.capability_manifest import load_capability_manifest
from vertex_api.follow_up import CreateThesisRequest, ThesisRevisionRequest
from vertex_api.portfolio import (
    CompensateTransactionRequest,
    CsvImportPreviewRequest,
    ImportConfirmRequest,
    RecordTransactionRequest,
)
from vertex_api.routes import protected_router, public_router
from vertex_api.schemas import AdvicePreviewRequest
from vertex_api.simulation import SimulationPreviewRequest
from vertex_api.snapshot_views import SnapshotContentError
from vertex_core.version import ENGINE_VERSION

__all__ = ["OpenApiComponentCollisionError", "create_app"]

_API_TITLE = "Vertex One API"
_API_DESCRIPTION = (
    "Local, analysis-only API of Vertex One. It serves the canonical "
    "contracts of vertex_core and delegates every verdict to the single "
    "AdviceEngine. No transactional capability exists; the human remains the "
    "sole decision maker, acting outside Vertex."
)


class OpenApiComponentCollisionError(RuntimeError):
    """Two different schema definitions claimed the same component name."""


def _build_openapi_schema(app: FastAPI) -> dict[str, Any]:
    """Render the OpenAPI document, adding the request contract components.

    The advice route parses its body manually (see
    ``vertex_api.routes.parse_advice_preview_request``), so FastAPI does not
    collect ``AdvicePreviewRequest`` on its own. Its validation schema (and
    the sub-schemas it references) are merged into ``components.schemas``
    deterministically; a name carried by both sources must be identical,
    otherwise the build fails (no silent overwrite).
    """
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    definitions: dict[str, Any] = {}
    for name, model in (
        ("AdvicePreviewRequest", AdvicePreviewRequest),
        ("AiExplainRequest", AiExplainRequest),
        ("SimulationPreviewRequest", SimulationPreviewRequest),
        ("RecordTransactionRequest", RecordTransactionRequest),
        ("CompensateTransactionRequest", CompensateTransactionRequest),
        ("CsvImportPreviewRequest", CsvImportPreviewRequest),
        ("ImportConfirmRequest", ImportConfirmRequest),
        ("CreateThesisRequest", CreateThesisRequest),
        ("ThesisRevisionRequest", ThesisRevisionRequest),
    ):
        request_schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
        for def_name, definition in request_schema.pop("$defs", {}).items():
            existing = definitions.get(def_name)
            if existing is not None and existing != definition:
                raise OpenApiComponentCollisionError(
                    f"OpenAPI component {def_name!r} has two different definitions"
                )
            definitions[def_name] = definition
        definitions[name] = request_schema

    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for name in sorted(definitions):
        definition = definitions[name]
        existing = components.get(name)
        if existing is not None and existing != definition:
            raise OpenApiComponentCollisionError(
                f"OpenAPI component {name!r} has two different definitions"
            )
        components[name] = definition
    return schema


_AI_ANSWER_REFUSED_DETAIL = (
    "the deterministic explanation of this snapshot breaks a grounding or "
    "completeness invariant and is refused"
)

_DATABASE_STATEMENT_REJECTED_DETAIL = (
    "the database refused this statement; nothing was written and no detail "
    "of the request is disclosed"
)


def _snapshot_content_response() -> JSONResponse:
    """The single fail-closed answer of a snapshot that cannot be served.

    Stable, typed and value-free: the client renders an honest error state
    and no fragment of the persisted payload travels in the response.
    """
    return JSONResponse(
        status_code=500,
        content={
            "code": "SNAPSHOT_CONTENT_INVALID",
            "detail": (
                "a published snapshot cannot be served: its stored content "
                "does not match the published schema"
            ),
        },
    )


def create_app() -> FastAPI:
    """Build the Vertex One API application.

    Health, the passkey authentication ceremonies (``/api/v1/auth``), and the
    protected advice/system routes behind the fail-closed WebAuthn session
    dependency. Each application carries its own in-memory challenge store
    and the capability manifest parsed once from
    ``manifests/ibkr-market-data-capabilities.yaml`` (a committed file — the
    read stays deterministic); no environment is read here, so the OpenAPI
    document stays deterministic.
    """
    app = FastAPI(
        title=_API_TITLE,
        version=ENGINE_VERSION,
        description=_API_DESCRIPTION,
    )
    app.state.challenge_store = ChallengeStore()
    app.state.capability_manifest = load_capability_manifest()
    app.include_router(public_router)
    app.include_router(auth_router)
    app.include_router(protected_router)

    @app.exception_handler(SnapshotContentError)
    async def _snapshot_content_rejected(
        request: Request, exc: SnapshotContentError
    ) -> JSONResponse:
        """Refuse a stored snapshot whose content breaks its published schema.

        Serving such content would present an unverified payload as a
        canonical result, so the relay fails closed. The client receives a
        stable code it can render as an honest error state; the trace keeps
        the RESOURCE and the offending FIELD PATH only — never the exception
        message, which may quote a stored value
        (``.claude/rules/security.md`` forbids any payload fragment in a
        log, and ``SnapshotContentError.field`` is the sanitized part).
        """
        logging.getLogger("vertex_api.snapshot").error(
            "snapshot content rejected on %s: invalid field %s",
            request.url.path,
            exc.field or "unknown",
        )
        return _snapshot_content_response()

    @app.exception_handler(AiGroundingError)
    async def _ai_answer_rejected(
        request: Request, exc: AiGroundingError
    ) -> JSONResponse:
        """Refuse an AI answer that breaks a grounding/completeness invariant.

        Without this handler ``AiGroundingError`` reached the default one:
        an UNTYPED ``500 "Internal Server Error"``, indistinguishable from a
        crash, plus a stack trace whose message quoted ``claim.text`` — a
        fragment of PERSISTED CONTENT in the server log
        (``.claude/rules/security.md``). The client now gets the exception's
        typed ``code`` (``AI_ANSWER_UNGROUNDED`` or ``AI_ANSWER_INCOMPLETE``)
        and a static detail.

        The trace keeps the ROUTE, the typed code and a COUNT of the
        canonical references involved — deliberately not the references
        themselves: an evidence id or a gate id is still a value read from a
        snapshot, and a count is enough to tell a total failure from a
        partial one.
        """
        logging.getLogger("vertex_api.ai").error(
            "ai answer refused on %s: %s (%d canonical reference(s))",
            request.url.path,
            exc.code,
            len(exc.references),
        )
        return JSONResponse(
            status_code=500,
            content={"code": exc.code, "detail": _AI_ANSWER_REFUSED_DETAIL},
        )

    @app.exception_handler(StatementError)
    @app.exception_handler(PendingRollbackError)
    async def _database_statement_rejected(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Refuse a statement the database rejected — WITHOUT logging the row.

        ``sqlalchemy.exc.StatementError`` is the CLASS that carries
        ``.statement`` and ``.params``; every subclass (``DataError``,
        ``IntegrityError``, ``OperationalError``, ``ProgrammingError``,
        ``InternalError``, ``NotSupportedError``) renders them in its own
        ``str()`` as ``[SQL: …]`` and ``[parameters: …]``. None of them had a
        handler, so any write the database refused reached the DEFAULT one:
        an UNTYPED ``500 "Internal Server Error"`` — a plain-text body, not
        even a code — and uvicorn wrote the full traceback to the server log.

        On ``POST /portfolio/transactions`` that traceback was the user's
        FINANCIAL JOURNAL in clear text: the INSERT into
        ``ledger_transactions`` with every bound parameter — amount, currency
        and the free-text note, which is where the name of their brokerage
        account lives. ``.claude/rules/security.md`` forbids any real payload
        or personal datum in a log; this was the whole row.

        The handler is registered on the BASE class deliberately: closing
        only the reported vector (``DataError`` on an oversized numeric)
        would leave every sibling leaking the same way. The client now gets a
        stable code, and the trace keeps the ROUTE, the exception CLASS and
        the SQLSTATE — technical identifiers, and nothing that was in the
        statement or its parameters.

        ``PendingRollbackError`` is registered alongside it although it is
        NOT a ``StatementError``: it interpolates the original exception into
        its own message (``"Original exception was: {…}"``), so a session
        reused after a caught database error — the shape of
        ``record_ledger_event``, which catches ``IntegrityError`` to detect a
        duplicate compensation — relays the very same ``[parameters: …]``
        under a different class.

        It covers EVERY route of the application, not only the portfolio
        ones: the passkey ceremonies write ``webauthn_credentials`` and the
        follow-up routes write user free text, and both leaked identically.
        """
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
        logging.getLogger("vertex_api.persistence").error(
            "database statement rejected on %s: %s (sqlstate %s)",
            request.url.path,
            type(exc).__name__,
            sqlstate or "unknown",
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "DATABASE_STATEMENT_REJECTED",
                "detail": _DATABASE_STATEMENT_REJECTED_DETAIL,
            },
        )

    @app.exception_handler(ValidationError)
    async def _snapshot_content_validation_rejected(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """LAST RAMPART: persisted content refused by a wire contract itself.

        Every relay validates the content it relays and raises
        ``SnapshotContentError`` (the handler above). Should one field escape
        that review, pydantic still refuses to build the DTO — and its
        ``ValidationError`` carries ``input_value``, i.e. THE STORED VALUE.
        Letting it reach the default handler would answer an untyped 500 and
        write that payload fragment into the server log. It is caught here
        instead: same typed code, and a trace reduced to the failing model
        and the pydantic error TYPES (``string_type``, ``greater_than``...),
        never a ``loc`` (a mapping key is itself stored data) and never an
        input value.

        A malformed REQUEST never reaches this handler: every request-parsing
        site converts its ``ValidationError`` into a ``RequestValidationError``
        (422), a distinct class — a client error therefore stays a 4xx.
        """
        kinds = sorted(
            {
                str(error.get("type", "unknown"))
                for error in exc.errors(
                    include_url=False, include_context=False, include_input=False
                )
            }
        )
        logging.getLogger("vertex_api.snapshot").error(
            "snapshot content rejected on %s: %s violated by %s",
            request.url.path,
            exc.title,
            ", ".join(kinds) or "unknown",
        )
        return _snapshot_content_response()

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _build_openapi_schema(app)
        return app.openapi_schema

    # Surcharge documentée par FastAPI : `app.openapi` est un attribut
    # d'instance destiné à être remplacé, pas une méthode à redéfinir.
    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app
