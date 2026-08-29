"""POST /api/v1/advice/preview: pass-through to the single AdviceEngine.

Covers the all-PASS case, the fail-closed family (missing gate input ->
INSUFFICIENT_DATA; rule violation -> BLOCKED), the single-authority proof
(API result == direct engine result, same advice_id) and the canonical wire
serialization (Decimal -> string, datetime -> ISO UTC)."""

import json
from typing import Any

from fastapi.testclient import TestClient

from vertex_api.schemas import AdvicePreviewRequest
from vertex_core.decision import GATE_ORDER, AdviceEngine
from vertex_core.version import ENGINE_VERSION


def _post_preview(client: TestClient, payload: dict[str, Any]) -> Any:
    return client.post("/api/v1/advice/preview", json=payload)


def _gate(body: dict[str, Any], gate_id: str) -> dict[str, Any]:
    matches = [gate for gate in body["gates"] if gate["gate_id"] == gate_id]
    assert len(matches) == 1
    return matches[0]


class TestAllPass:
    def test_all_gates_pass_yields_qualified(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        response = _post_preview(authenticated_client, all_pass_payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "QUALIFIED"
        assert body["direction"] == "NEUTRAL"
        assert body["engine_version"] == ENGINE_VERSION
        assert [gate["gate_id"] for gate in body["gates"]] == list(GATE_ORDER)
        assert all(gate["status"] == "PASS" for gate in body["gates"])
        assert body["limitations"] == []

    def test_wire_serialization_decimal_string_and_iso_utc(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        body = _post_preview(authenticated_client, all_pass_payload).json()
        assert body["as_of"] == "2026-08-01T12:00:00Z"
        assert body["valid_until"] == "2026-08-01T13:00:00Z"
        liquidity_gate = _gate(body, "minimum_liquidity")
        assert liquidity_gate["observed_values"]["observed_liquidity"] == "1000000.50"
        assert liquidity_gate["thresholds"]["required_minimum"] == "500000"


class TestFailClosed:
    def test_missing_gate_input_blocks_fail_closed(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        """An absent snapshot input closes its gate (BLOCK UNEVALUABLE); the
        verdict is the missing-data member of the blocked family."""
        payload = dict(all_pass_payload)
        del payload["snapshot"]
        response = _post_preview(authenticated_client, payload)
        assert response.status_code == 200
        body = response.json()
        snapshot_gate = _gate(body, "snapshot_fresh_and_coherent")
        assert snapshot_gate["status"] == "BLOCK"
        assert snapshot_gate["reason_code"] == "UNEVALUABLE"
        assert body["status"] == "INSUFFICIENT_DATA"

    def test_rule_violation_yields_blocked(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        payload = dict(all_pass_payload)
        payload["instrument"] = {"identity_status": "UNRESOLVED", "resolved_with_conid": None}
        response = _post_preview(authenticated_client, payload)
        assert response.status_code == 200
        body = response.json()
        identity_gate = _gate(body, "instrument_resolved")
        assert identity_gate["status"] == "BLOCK"
        assert identity_gate["reason_code"] == "UNRESOLVED_IDENTITY"
        assert body["status"] == "BLOCKED"

    def test_naive_datetime_is_rejected_422(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        payload = dict(all_pass_payload)
        payload["as_of"] = "2026-08-01T12:00:00"
        response = _post_preview(authenticated_client, payload)
        assert response.status_code == 422

    def test_unknown_field_is_rejected_422(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        payload = dict(all_pass_payload)
        payload["unexpected_field"] = "value"
        response = _post_preview(authenticated_client, payload)
        assert response.status_code == 422

    def test_invalid_json_body_is_rejected_422(
        self, authenticated_client: TestClient
    ) -> None:
        response = authenticated_client.post(
            "/api/v1/advice/preview",
            content=b"not json at all",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 422


class TestSingleAuthority:
    def test_api_result_equals_direct_engine_result(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        """Proof of the unique authority: the API returns exactly what the
        engine computes — same advice_id, byte-equivalent content."""
        api_body = _post_preview(authenticated_client, all_pass_payload).json()

        request = AdvicePreviewRequest.model_validate_json(json.dumps(all_pass_payload))
        direct_result = AdviceEngine().evaluate(request)

        assert api_body["advice_id"] == direct_result.advice_id
        assert api_body == json.loads(direct_result.model_dump_json())

    def test_identical_inputs_yield_identical_advice_id(
        self, authenticated_client: TestClient, all_pass_payload: dict[str, Any]
    ) -> None:
        first = _post_preview(authenticated_client, all_pass_payload).json()
        second = _post_preview(authenticated_client, all_pass_payload).json()
        assert first == second
        assert first["advice_id"] == second["advice_id"]


class TestSystemEngine:
    def test_engine_info_reports_versions_only(
        self, authenticated_client: TestClient
    ) -> None:
        from vertex_core.decision import GATE_VERSIONS

        response = authenticated_client.get("/api/v1/system/engine")
        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"engine_version", "contracts_version", "gate_versions"}
        assert body["engine_version"] == ENGINE_VERSION
        assert body["contracts_version"] == ENGINE_VERSION
        assert body["gate_versions"] == dict(GATE_VERSIONS)
