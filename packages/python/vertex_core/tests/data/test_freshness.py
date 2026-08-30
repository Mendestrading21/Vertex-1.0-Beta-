"""Freshness policies: registry, session-aware TTLs, fail-closed evaluation."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from vertex_core.data import (
    FRESHNESS_POLICIES,
    FRESHNESS_REGISTRY_VERSION,
    FreshnessPolicy,
    FreshnessStatus,
    SessionState,
    UnknownFreshnessPolicyError,
    evaluate_freshness,
    get_freshness_policy,
)

T0 = datetime(2026, 8, 28, 14, 0, tzinfo=UTC)

EXPECTED_POLICY_NAMES = {
    "intraday_quote",
    "selected_option_quote",
    "option_surface",
    "daily_bar",
    "news_attention",
    "corporate_event",
    "fundamental_filing",
    "portfolio_mark",
}


class TestRegistry:
    def test_registry_contains_exactly_the_eight_documented_policies(self):
        assert set(FRESHNESS_POLICIES) == EXPECTED_POLICY_NAMES
        assert len(FRESHNESS_POLICIES) == 8

    def test_registry_is_versioned(self):
        assert FRESHNESS_REGISTRY_VERSION == "1.0.0"
        for policy in FRESHNESS_POLICIES.values():
            assert policy.version == "1.0.0"

    def test_every_policy_key_matches_its_name(self):
        for name, policy in FRESHNESS_POLICIES.items():
            assert policy.name == name

    def test_registry_is_read_only(self):
        with pytest.raises(TypeError):
            FRESHNESS_POLICIES["intraday_quote"] = FRESHNESS_POLICIES["daily_bar"]

    def test_policies_are_frozen_models(self):
        policy = FRESHNESS_POLICIES["intraday_quote"]
        with pytest.raises(ValidationError):
            policy.ttl_open_seconds = 1

    def test_unknown_policy_raises_never_a_default_ttl(self):
        with pytest.raises(UnknownFreshnessPolicyError):
            get_freshness_policy("nonexistent_policy")

    def test_unknown_policy_error_is_a_keyerror(self):
        # Typed error stays catchable as KeyError for mapping-style callers.
        with pytest.raises(KeyError):
            get_freshness_policy("intraday_quote_v2")

    def test_non_string_policy_name_rejected(self):
        with pytest.raises(TypeError):
            get_freshness_policy(None)

    def test_intraday_quote_initial_ttls(self):
        policy = get_freshness_policy("intraday_quote")
        assert policy.ttl_open_seconds == 5
        assert policy.ttl_closed_seconds == 900

    def test_ttl_seconds_for_selects_by_session(self):
        policy = get_freshness_policy("intraday_quote")
        assert policy.ttl_seconds_for(SessionState.OPEN) == 5
        assert policy.ttl_seconds_for(SessionState.CLOSED) == 900

    def test_ttl_seconds_for_rejects_non_session_state(self):
        policy = get_freshness_policy("intraday_quote")
        with pytest.raises(TypeError):
            policy.ttl_seconds_for("OPEN")


class TestPolicyModel:
    def test_non_positive_ttl_rejected(self):
        for bad in (0, -5):
            with pytest.raises(ValidationError):
                FreshnessPolicy(
                    name="x", version="1.0.0", ttl_open_seconds=bad, ttl_closed_seconds=10
                )

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            FreshnessPolicy(name="", version="1.0.0", ttl_open_seconds=1, ttl_closed_seconds=1)

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            FreshnessPolicy(
                name="x", version="1.0.0", ttl_open_seconds=1, ttl_closed_seconds=1, ttl_default=1
            )


class TestEvaluateFreshness:
    @pytest.fixture()
    def policy(self):
        return get_freshness_policy("intraday_quote")

    def test_fresh_within_open_ttl(self, policy):
        status = evaluate_freshness(
            policy, as_of=T0, now=T0 + timedelta(seconds=4), session_state=SessionState.OPEN
        )
        assert status is FreshnessStatus.FRESH

    def test_boundary_age_equal_to_ttl_is_fresh(self, policy):
        status = evaluate_freshness(
            policy, as_of=T0, now=T0 + timedelta(seconds=5), session_state=SessionState.OPEN
        )
        assert status is FreshnessStatus.FRESH

    def test_stale_beyond_open_ttl(self, policy):
        status = evaluate_freshness(
            policy, as_of=T0, now=T0 + timedelta(seconds=6), session_state=SessionState.OPEN
        )
        assert status is FreshnessStatus.STALE

    def test_same_age_fresh_when_closed_session_ttl_applies(self, policy):
        # 6 seconds is stale for OPEN (5s TTL) but fresh for CLOSED (900s TTL).
        now = T0 + timedelta(seconds=6)
        assert (
            evaluate_freshness(policy, as_of=T0, now=now, session_state=SessionState.CLOSED)
            is FreshnessStatus.FRESH
        )

    def test_stale_beyond_closed_ttl(self, policy):
        status = evaluate_freshness(
            policy, as_of=T0, now=T0 + timedelta(seconds=901), session_state=SessionState.CLOSED
        )
        assert status is FreshnessStatus.STALE

    def test_zero_age_is_fresh(self, policy):
        assert (
            evaluate_freshness(policy, as_of=T0, now=T0, session_state=SessionState.OPEN)
            is FreshnessStatus.FRESH
        )

    def test_future_observation_is_invalid(self, policy):
        status = evaluate_freshness(
            policy, as_of=T0, now=T0 - timedelta(microseconds=1), session_state=SessionState.OPEN
        )
        assert status is FreshnessStatus.INVALID

    def test_future_observation_invalid_in_both_sessions(self, policy):
        for session in SessionState:
            status = evaluate_freshness(
                policy, as_of=T0, now=T0 - timedelta(hours=1), session_state=session
            )
            assert status is FreshnessStatus.INVALID

    def test_naive_as_of_rejected(self, policy):
        with pytest.raises(ValueError, match="naive datetime"):
            evaluate_freshness(
                policy,
                as_of=datetime(2026, 8, 28, 14, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
                now=T0,
                session_state=SessionState.OPEN,
            )

    def test_naive_now_rejected(self, policy):
        with pytest.raises(ValueError, match="naive datetime"):
            evaluate_freshness(
                policy,
                as_of=T0,
                now=datetime(2026, 8, 28, 14, 0),  # noqa: DTZ001 (naïf délibéré : rejet vérifié)
                session_state=SessionState.OPEN,
            )

    def test_aware_non_utc_datetimes_compared_as_instants(self, policy):
        # 16:00+02:00 == 14:00 UTC: zero age, fresh — no wall-clock confusion.
        offset = timezone(timedelta(hours=2))
        as_of_local = datetime(2026, 8, 28, 16, 0, tzinfo=offset)
        assert (
            evaluate_freshness(policy, as_of=as_of_local, now=T0, session_state=SessionState.OPEN)
            is FreshnessStatus.FRESH
        )

    def test_non_policy_rejected(self):
        with pytest.raises(TypeError):
            evaluate_freshness(
                {"ttl_open_seconds": 5}, as_of=T0, now=T0, session_state=SessionState.OPEN
            )

    def test_non_session_state_rejected(self, policy):
        with pytest.raises(TypeError):
            evaluate_freshness(policy, as_of=T0, now=T0, session_state="OPEN")

    def test_non_datetime_rejected(self, policy):
        with pytest.raises(TypeError):
            evaluate_freshness(policy, as_of=None, now=T0, session_state=SessionState.OPEN)

    def test_determinism_same_inputs_same_result(self, policy):
        args = {"as_of": T0, "now": T0 + timedelta(seconds=3), "session_state": SessionState.OPEN}
        results = {evaluate_freshness(policy, **args) for _ in range(10)}
        assert results == {FreshnessStatus.FRESH}
