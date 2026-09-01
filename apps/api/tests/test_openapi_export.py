"""Deterministic OpenAPI: byte-identical double export, committed file in
sync, explicit operation ids and complete component schemas."""

import importlib.util
import json
from pathlib import Path

from vertex_api.openapi_export import render_openapi_document_bytes
from vertex_core.version import ENGINE_VERSION

_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMITTED_DOCUMENT = _REPO_ROOT / "apps" / "api" / "openapi.json"
_EXPORT_TOOL = _REPO_ROOT / "tools" / "export_openapi.py"


def _load_export_tool():
    spec = importlib.util.spec_from_file_location("export_openapi_tool", _EXPORT_TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_double_export_is_byte_identical() -> None:
    first = render_openapi_document_bytes()
    second = render_openapi_document_bytes()
    assert first == second


def test_export_tool_writes_byte_identical_files_twice(tmp_path: Path) -> None:
    tool = _load_export_tool()
    first_target = tool.main(tmp_path / "openapi-first.json")
    second_target = tool.main(tmp_path / "openapi-second.json")
    first_bytes = first_target.read_bytes()
    assert first_bytes == second_target.read_bytes()
    assert first_bytes == render_openapi_document_bytes()


def test_committed_document_matches_current_application() -> None:
    """Drift guard: apps/api/openapi.json is exactly the current rendering."""
    assert _COMMITTED_DOCUMENT.is_file(), "run: python tools/export_openapi.py"
    assert _COMMITTED_DOCUMENT.read_bytes() == render_openapi_document_bytes()


def test_openapi_structure_is_explicit() -> None:
    schema = json.loads(render_openapi_document_bytes())
    assert schema["info"]["title"] == "Vertex One API"
    assert schema["info"]["version"] == ENGINE_VERSION

    operation_ids = {
        operation["operationId"]
        for path_item in schema["paths"].values()
        for operation in path_item.values()
    }
    assert operation_ids == {
        "get_health",
        "post_advice_preview",
        "get_system_engine",
        "get_today_attention",
        "get_markets_overview",
        "get_analysis",
        "get_option_chain",
        "get_system_capabilities",
        "get_events_stream",
        "post_simulations_preview",
        # Manual portfolio journal (accounting semantics, neutral operation
        # ids: these RECORD past facts, they never transmit anything).
        "get_portfolio",
        "record_transaction",
        "compensate_transaction",
        "preview_portfolio_import",
        "confirm_portfolio_import",
        "export_portfolio",
        # Follow-up (page 09): user-written theses, append-only revisions,
        # verbatim review-queue relay.
        "get_follow_up_queue",
        "create_thesis",
        "record_thesis_revision",
        # Performance (page 10): verbatim snapshot relay + reproducible export.
        "get_performance",
        "export_performance",
        # Calendar (page 02) and opportunities funnel (page 04): verbatim
        # snapshot relays, bounded window for the agenda.
        "get_calendar",
        "get_opportunities",
        # Risques : matrice de corrélation du périmètre DÉCLARÉ, relayée
        # verbatim (la grille arrive déjà rendue en chaînes, l'API ne
        # recalcule aucun coefficient). Clé `global` — elle décrit le
        # périmètre, pas un portefeuille.
        "get_risk_matrix",
        # Vertex AI (page 11): DETERMINISTIC template only while the AI
        # provider decision (B-05) is pending — no model is called.
        "post_ai_explain",
        "get_ai_status",
        "post_auth_register_options",
        "post_auth_register_verify",
        "post_auth_login_options",
        "post_auth_login_verify",
        "post_auth_logout",
    }

    components = schema["components"]["schemas"]
    assert "AdvicePreviewRequest" in components
    assert "AdviceResult" in components

    request_body = schema["paths"]["/api/v1/advice/preview"]["post"]["requestBody"]
    assert request_body["required"] is True
    request_ref = request_body["content"]["application/json"]["schema"]["$ref"]
    assert request_ref == "#/components/schemas/AdvicePreviewRequest"

    response_ref = schema["paths"]["/api/v1/advice/preview"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]["$ref"]
    assert response_ref == "#/components/schemas/AdviceResult"
