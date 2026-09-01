from __future__ import annotations

import pytest

from vertex_edge_official import OfficialSourceConfig


def test_configuration_summary_is_honest_and_never_exposes_keys() -> None:
    config = OfficialSourceConfig.from_environ(
        {
            "VERTEX_SEC_USER_AGENT": "Vertex One dev@example.invalid",
            "VERTEX_FRED_API_KEY": "synthetic-fred-key",
            "VERTEX_OPENFIGI_API_KEY": "synthetic-figi-key",
            "VERTEX_OFFICIAL_SOURCE_TIMEOUT_SECONDS": "12",
        }
    )
    summary = config.capability_summary()
    assert summary["sec_edgar"] == {"status": "ERROR", "reason": "USER_AGENT_MISSING"}
    assert summary["fred_alfred"]["status"] == "AVAILABLE"
    assert summary["openfigi"]["reason"] == "AUTHENTICATED_QUOTA"
    assert "synthetic-fred-key" not in repr(config)
    assert "synthetic-figi-key" not in repr(config)
    assert config.timeout_seconds == 12


def test_placeholders_and_missing_optional_key_have_explicit_statuses() -> None:
    config = OfficialSourceConfig.from_environ(
        {
            "VERTEX_SEC_USER_AGENT": "CHANGE_ME",
            "VERTEX_FRED_API_KEY": "CHANGE_ME",
            "VERTEX_OPENFIGI_API_KEY": "",
        }
    )
    summary = config.capability_summary()
    assert summary["sec_edgar"]["status"] == "ERROR"
    assert summary["fred_alfred"]["status"] == "NOT_ENTITLED"
    assert summary["openfigi"] == {
        "status": "AVAILABLE",
        "reason": "PUBLIC_REDUCED_QUOTA",
    }
    assert summary["ecb_data_portal"]["status"] == "AVAILABLE"
    assert summary["snb_data_portal"]["status"] == "AVAILABLE"


@pytest.mark.parametrize("value", ["0", "61", "not-a-number"])
def test_timeout_fails_closed(value: str) -> None:
    with pytest.raises(ValueError, match="VERTEX_OFFICIAL_SOURCE_TIMEOUT_SECONDS"):
        OfficialSourceConfig.from_environ({"VERTEX_OFFICIAL_SOURCE_TIMEOUT_SECONDS": value})
