"""Fusion contracts: strictness, immutability and fail-closed invariants."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from vertex_core.contracts import EnvelopeQuality
from vertex_core.fusion import (
    ContentCluster,
    ContentObservation,
    FusionAction,
    FusionDecision,
)
from tests.fusion.factories import BASE_TIME, make_observation


def _decision(**overrides) -> FusionDecision:
    values = dict(
        decision_id="d-1",
        rule_id="fusion.dedup.native_id",
        rule_version="1.0.0",
        inputs=("a", "b"),
        action=FusionAction.LINKED_NATIVE_ID,
        rationale="same provider native id",
        reversible=False,
    )
    values.update(overrides)
    return FusionDecision(**values)


def _cluster(**overrides) -> ContentCluster:
    values = dict(
        cluster_id="sha256:" + "0" * 64,
        member_ids=("a", "b"),
        sources=("ibkr_news",),
        tiers=("P1",),
        rights=("display_only",),
        first_published_at=None,
        last_received_at=BASE_TIME,
        decisions=(_decision(),),
    )
    values.update(overrides)
    return ContentCluster(**values)


class TestContentObservation:
    def test_absent_fields_stay_none_never_defaulted(self):
        observation = make_observation("a")
        assert observation.native_id is None
        assert observation.canonical_url is None
        assert observation.published_at is None
        assert observation.is_deleted is False

    def test_naive_received_at_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_observation("a", received_at=datetime(2026, 8, 1, 12, 0))

    def test_naive_published_at_rejected(self):
        with pytest.raises(ValidationError, match="naive datetime"):
            make_observation("a", published_at=datetime(2026, 8, 1, 11, 0))

    @pytest.mark.parametrize("tier", ["P5", "p0", "P", "X1", ""])
    def test_invalid_source_tier_rejected(self, tier):
        with pytest.raises(ValidationError):
            make_observation("a", source_tier=tier)

    @pytest.mark.parametrize("tier", ["P0", "P1", "P2", "P3", "P4"])
    def test_valid_source_tiers_accepted(self, tier):
        assert make_observation("a", source_tier=tier).source_tier == tier

    def test_empty_entity_label_rejected(self):
        with pytest.raises(ValidationError):
            make_observation("a", entities=("",))

    def test_frozen(self):
        observation = make_observation("a")
        with pytest.raises(ValidationError):
            observation.title = "changed"

    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            ContentObservation(
                content_id="a",
                source="ibkr_news",
                source_tier="P1",
                title="t",
                entities=(),
                received_at=BASE_TIME,
                rights="display_only",
                quality=EnvelopeQuality.VALID,
                ibkr_extra="forbidden",
            )


class TestFusionDecision:
    def test_flagged_similar_must_be_reversible(self):
        with pytest.raises(ValidationError, match="must be reversible"):
            _decision(action=FusionAction.FLAGGED_SIMILAR, reversible=False)

    def test_flagged_similar_reversible_accepted(self):
        decision = _decision(action=FusionAction.FLAGGED_SIMILAR, reversible=True)
        assert decision.reversible is True

    def test_kept_distinct_takes_exactly_one_input(self):
        with pytest.raises(ValidationError, match="exactly one input"):
            _decision(action=FusionAction.KEPT_DISTINCT, inputs=("a", "b"), reversible=True)

    def test_link_takes_exactly_two_inputs(self):
        with pytest.raises(ValidationError, match="exactly two inputs"):
            _decision(inputs=("a",))

    def test_unsorted_inputs_rejected(self):
        with pytest.raises(ValidationError, match="strictly sorted"):
            _decision(inputs=("b", "a"))

    def test_duplicate_inputs_rejected(self):
        with pytest.raises(ValidationError, match="strictly sorted"):
            _decision(inputs=("a", "a"))

    def test_frozen(self):
        decision = _decision()
        with pytest.raises(ValidationError):
            decision.reversible = True


class TestContentCluster:
    def test_unsorted_member_ids_rejected(self):
        with pytest.raises(ValidationError, match="member_ids must be strictly sorted"):
            _cluster(member_ids=("b", "a"))

    def test_duplicate_sources_rejected(self):
        with pytest.raises(ValidationError, match="sources must be strictly sorted"):
            _cluster(sources=("sec", "sec"))

    def test_empty_decisions_rejected(self):
        with pytest.raises(ValidationError):
            _cluster(decisions=())

    def test_decision_must_reference_a_member(self):
        stranger = _decision(inputs=("x", "y"))
        with pytest.raises(ValidationError, match="at least one member"):
            _cluster(decisions=(stranger,))

    def test_cross_cluster_flag_referencing_one_member_accepted(self):
        flag = _decision(
            action=FusionAction.FLAGGED_SIMILAR,
            reversible=True,
            inputs=("a", "z-other-cluster"),
        )
        cluster = _cluster(decisions=(_decision(), flag))
        assert flag in cluster.decisions

    def test_absent_first_published_at_stays_none(self):
        assert _cluster().first_published_at is None
