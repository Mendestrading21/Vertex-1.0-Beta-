"""Relevance engine: mandatory gates, lexicographic ranking, budgets, sync."""

import random
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from tests.fusion.factories import BASE_TIME, make_observation
from vertex_core.contracts import (
    EnvelopeQuality,
    IdentityStatus,
    canonical_json_hash,
)
from vertex_core.fusion import (
    ATTENTION_BUDGETS,
    PENALTY_CODES,
    POLICY_AUTHORITY,
    POLICY_VERSION,
    REQUIRED_GATES,
    UNLIMITED,
    RankedItem,
    RelevanceInput,
    RelevanceInputError,
    RelevanceSubscores,
    UnknownAttentionBudgetError,
    apply_attention_budget,
    evaluate_gates,
    rank_items,
)

AS_OF = BASE_TIME + timedelta(hours=1)

MANIFEST_PATH = Path(__file__).resolve().parents[5] / "manifests" / "relevance-policy.yaml"


def make_input(content_id: str, **overrides) -> RelevanceInput:
    observation_fields = {
        key: overrides.pop(key)
        for key in (
            "source",
            "source_tier",
            "title",
            "entities",
            "published_at",
            "received_at",
            "rights",
            "quality",
            "is_deleted",
        )
        if key in overrides
    }
    values = {
        "observation": make_observation(content_id, **observation_fields),
        "identity_status": IdentityStatus.RESOLVED,
        "rights_usable": True,
        "source_allowed": True,
    }
    values.update(overrides)
    return RelevanceInput(**values)


class TestGates:
    def test_all_gates_pass_for_clean_item(self):
        gates = evaluate_gates(make_input("a"), AS_OF)
        assert gates.all_ok
        assert gates.failed_gates == ()

    @pytest.mark.parametrize(
        ("overrides", "expected_gate"),
        [
            ({"rights_usable": False}, "RIGHTS_OK"),
            ({"identity_status": IdentityStatus.AMBIGUOUS}, "IDENTITY_OK"),
            ({"identity_status": IdentityStatus.UNRESOLVED}, "IDENTITY_OK"),
            ({"received_at": AS_OF + timedelta(minutes=1)}, "TIME_OK"),
            ({"published_at": AS_OF + timedelta(minutes=1)}, "TIME_OK"),
            ({"source_allowed": False}, "SOURCE_OK"),
            ({"quality": EnvelopeQuality.STALE}, "QUALITY_OK"),
            ({"quality": EnvelopeQuality.INVALID}, "QUALITY_OK"),
            ({"quality": EnvelopeQuality.CONFLICT}, "QUALITY_OK"),
            ({"quality": EnvelopeQuality.INSUFFICIENT_DATA}, "QUALITY_OK"),
            ({"is_deleted": True}, "QUALITY_OK"),
        ],
    )
    def test_each_gate_failure_excludes_with_stable_reason(self, overrides, expected_gate):
        ranking = rank_items([make_input("a", **overrides)], as_of=AS_OF)
        assert ranking.ranked == ()
        assert len(ranking.rejected) == 1
        rejection = ranking.rejected[0]
        assert rejection.filtered_reason == f"{expected_gate}_FAILED"
        assert expected_gate in rejection.failed_gates

    def test_partial_quality_passes_the_quality_gate(self):
        gates = evaluate_gates(make_input("a", quality=EnvelopeQuality.PARTIAL), AS_OF)
        assert gates.quality_ok

    def test_filtered_reason_is_first_failed_gate_in_canonical_order(self):
        item = make_input("a", rights_usable=False, quality=EnvelopeQuality.INVALID)
        ranking = rank_items([item], as_of=AS_OF)
        assert ranking.rejected[0].filtered_reason == "RIGHTS_OK_FAILED"
        assert ranking.rejected[0].failed_gates == ("RIGHTS_OK", "QUALITY_OK")

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError, match="naive datetime"):
            rank_items([make_input("a")], as_of=datetime(2026, 8, 1, 13, 0))  # noqa: DTZ001 (naïf délibéré : rejet vérifié)

    def test_duplicate_item_ids_rejected(self):
        with pytest.raises(RelevanceInputError, match="duplicate item_id"):
            rank_items([make_input("a"), make_input("a")], as_of=AS_OF)


class TestRightsNeverCrossed:
    def test_item_without_rights_never_ranked_even_with_maximum_priority(self):
        blocked = make_input(
            "critical",
            rights_usable=False,
            security_or_quality_incident=True,
            manual_position=True,
            active_thesis_or_alert=True,
            watchlist=True,
            recently_analyzed=True,
            global_market_event=True,
            novelty=True,
        )
        ranking = rank_items([blocked, make_input("ordinary")], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["ordinary"]
        assert ranking.rejected[0].item_id == "critical"
        assert ranking.rejected[0].filtered_reason == "RIGHTS_OK_FAILED"

    def test_unlimited_blocker_budget_never_resurrects_a_gated_item(self):
        blocked = make_input(
            "critical",
            rights_usable=False,
            security_or_quality_incident=True,
        )
        identity_blocked = make_input(
            "no-identity",
            identity_status=IdentityStatus.UNRESOLVED,
            security_or_quality_incident=True,
        )
        admitted = make_input("incident-ok", security_or_quality_incident=True)
        ranking = rank_items([blocked, identity_blocked, admitted], as_of=AS_OF)
        blockers = apply_attention_budget(ranking.ranked, "today", "blockers")
        assert ATTENTION_BUDGETS["today"]["blockers"] == UNLIMITED
        assert [item.item_id for item in blockers] == ["incident-ok"]


class TestLexicographicRanking:
    def test_documented_priority_order(self):
        fresh = BASE_TIME + timedelta(minutes=59)
        items = [
            make_input("g-fresh", received_at=fresh),
            make_input("f-global", global_market_event=True),
            make_input("e-recent", recently_analyzed=True),
            make_input("d-watchlist", watchlist=True),
            make_input("c-thesis", active_thesis_or_alert=True),
            make_input("b-position", manual_position=True),
            make_input("a-incident", security_or_quality_incident=True),
        ]
        ranking = rank_items(items, as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == [
            "a-incident",
            "b-position",
            "c-thesis",
            "d-watchlist",
            "e-recent",
            "f-global",
            "g-fresh",
        ]
        assert [item.priority_class for item in ranking.ranked] == [1, 2, 3, 4, 5, 6, 7]

    def test_higher_class_beats_any_freshness(self):
        # A very old manual-position item still outranks a brand-new
        # freshness-only item: lexicographic, never a weighted sum.
        old_position = make_input(
            "old-position",
            manual_position=True,
            received_at=BASE_TIME - timedelta(days=30),
        )
        fresh_item = make_input("fresh", received_at=AS_OF)
        ranking = rank_items([fresh_item, old_position], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["old-position", "fresh"]

    def test_within_class_fresher_first_then_tier_then_id(self):
        items = [
            make_input("older", watchlist=True, received_at=BASE_TIME - timedelta(hours=5)),
            make_input("newer", watchlist=True, received_at=BASE_TIME),
            make_input(
                "tie-b",
                watchlist=True,
                source_tier="P1",
                received_at=BASE_TIME - timedelta(hours=5),
            ),
        ]
        # "older" and "tie-b" share the age; P1 has the same tier so id decides.
        ranking = rank_items(items, as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["newer", "older", "tie-b"]

    def test_subscores_kept_separately_no_opaque_sum(self):
        ranking = rank_items(
            [make_input("a", watchlist=True, novelty=True, penalties=("stale",))],
            as_of=AS_OF,
        )
        subscores = ranking.ranked[0].subscores
        assert subscores.watchlist is True
        assert subscores.novelty is True
        assert subscores.age_seconds == 3600
        assert subscores.source_tier == "P1"
        assert subscores.penalties == ("stale",)
        forbidden = {"score", "total", "total_score", "weight", "sum"}
        assert not forbidden & set(RelevanceSubscores.model_fields)
        assert not forbidden & set(RankedItem.model_fields)

    def test_at_most_three_relevance_reasons_highest_first(self):
        item = make_input(
            "a",
            security_or_quality_incident=True,
            manual_position=True,
            active_thesis_or_alert=True,
            watchlist=True,
        )
        ranking = rank_items([item], as_of=AS_OF)
        assert ranking.ranked[0].relevance_reasons == (
            "SECURITY_OR_QUALITY_INCIDENT",
            "MANUAL_POSITION",
            "ACTIVE_THESIS_OR_ALERT",
        )

    def test_freshness_reason_when_nothing_else_applies(self):
        ranking = rank_items([make_input("a")], as_of=AS_OF)
        assert ranking.ranked[0].relevance_reasons == ("FRESHNESS",)

    def test_unknown_penalty_code_rejected(self):
        with pytest.raises(ValidationError, match="unknown penalty codes"):
            make_input("a", penalties=("made_up_penalty",))


class TestPenaltiesApplied:
    """Every manifest penalty code must have an observable effect.

    The manifest-sync test only proves the code lists are equal; these tests
    prove the penalty policy is actually applied: a penalized item is demoted
    behind an otherwise-identical clean item, and ``missing_rights`` expressed
    through the penalty vocabulary closes the RIGHTS_OK gate (fail-closed
    cross-invariant), never yielding a rankable item.
    """

    RANKING_PENALTIES = tuple(code for code in PENALTY_CODES if code != "missing_rights")

    def test_spam_item_ranks_after_identical_clean_item(self):
        # Reproducer for the confirmed finding: same flags, same age, and the
        # penalized item_id sorts first alphabetically — before the fix the
        # item_id tiebreak put the spam item ahead of the clean one.
        spam = make_input(
            "a_spam",
            watchlist=True,
            penalties=("probable_spam_or_bot", "duplicate", "syndicated_copy"),
        )
        clean = make_input("b_clean", watchlist=True)
        ranking = rank_items([spam, clean], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["b_clean", "a_spam"]

    @pytest.mark.parametrize("code", RANKING_PENALTIES)
    def test_every_ranking_penalty_code_demotes(self, code):
        penalized = make_input("a_penalized", watchlist=True, penalties=(code,))
        clean = make_input("b_clean", watchlist=True)
        ranking = rank_items([penalized, clean], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["b_clean", "a_penalized"]

    def test_more_penalties_rank_lower(self):
        two = make_input("a_two", penalties=("duplicate", "stale"))
        one = make_input("b_one", penalties=("duplicate",))
        none = make_input("c_none")
        ranking = rank_items([two, one, none], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["c_none", "b_one", "a_two"]

    def test_older_clean_item_beats_fresher_penalized_item_within_class(self):
        old_clean = make_input(
            "old_clean",
            watchlist=True,
            received_at=BASE_TIME - timedelta(hours=6),
        )
        fresh_spam = make_input(
            "fresh_spam",
            watchlist=True,
            received_at=AS_OF,
            penalties=("probable_spam_or_bot",),
        )
        ranking = rank_items([fresh_spam, old_clean], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["old_clean", "fresh_spam"]

    def test_penalty_never_overrides_documented_priority_ladder(self):
        # Penalties demote within the lexicographic flag profile; they never
        # promote a lower documented class above a higher one.
        penalized_position = make_input(
            "penalized_position",
            manual_position=True,
            penalties=("duplicate", "probable_spam_or_bot"),
        )
        clean_watchlist = make_input("clean_watchlist", watchlist=True)
        ranking = rank_items([clean_watchlist, penalized_position], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == [
            "penalized_position",
            "clean_watchlist",
        ]

    def test_missing_rights_penalty_closes_rights_gate_despite_rights_usable(self):
        # Cross-invariant: an upstream expressing a rights problem through the
        # penalty vocabulary instead of the gate boolean must NOT obtain a
        # rankable item (fail-closed).
        item = make_input("rights_conflict", rights_usable=True, penalties=("missing_rights",))
        ranking = rank_items([item], as_of=AS_OF)
        assert ranking.ranked == ()
        assert len(ranking.rejected) == 1
        rejection = ranking.rejected[0]
        assert rejection.filtered_reason == "RIGHTS_OK_FAILED"
        assert "RIGHTS_OK" in rejection.failed_gates

    def test_missing_rights_penalty_fails_gate_evaluation(self):
        gates = evaluate_gates(
            make_input("a", rights_usable=True, penalties=("missing_rights",)), AS_OF
        )
        assert gates.rights_ok is False
        assert "RIGHTS_OK" in gates.failed_gates

    def test_missing_rights_penalty_never_ranked_even_with_maximum_priority(self):
        blocked = make_input(
            "critical",
            rights_usable=True,
            penalties=("missing_rights",),
            security_or_quality_incident=True,
            manual_position=True,
            active_thesis_or_alert=True,
            watchlist=True,
            recently_analyzed=True,
            global_market_event=True,
            novelty=True,
        )
        ranking = rank_items([blocked, make_input("ordinary")], as_of=AS_OF)
        assert [item.item_id for item in ranking.ranked] == ["ordinary"]
        assert ranking.rejected[0].filtered_reason == "RIGHTS_OK_FAILED"

    def test_duplicate_penalty_codes_rejected(self):
        with pytest.raises(ValidationError, match="duplicate penalty codes"):
            make_input("a", penalties=("duplicate", "duplicate"))

    def test_budget_cuts_penalized_items_first_within_class(self):
        items = [
            make_input("a_spam", watchlist=True, penalties=("probable_spam_or_bot",)),
            make_input("b_clean", watchlist=True),
            make_input("c_clean", watchlist=True),
            make_input("d_clean", watchlist=True),
        ]
        ranking = rank_items(items, as_of=AS_OF)
        kept = apply_attention_budget(ranking.ranked, "today", "major_events")
        assert [item.item_id for item in kept] == ["b_clean", "c_clean", "d_clean"]


class TestAttentionBudgets:
    def _ranked(self, count: int):
        items = [make_input(f"item-{i:02d}", watchlist=True) for i in range(count)]
        return rank_items(items, as_of=AS_OF).ranked

    def test_today_major_events_budget_is_three(self):
        assert len(apply_attention_budget(self._ranked(10), "today", "major_events")) == 3

    def test_markets_dominant_narratives_budget_is_one(self):
        assert len(apply_attention_budget(self._ranked(4), "markets", "dominant_narratives")) == 1

    def test_unlimited_blockers_budget_returns_everything(self):
        ranked = self._ranked(50)
        assert apply_attention_budget(ranked, "today", "blockers") == tuple(ranked)

    def test_budget_keeps_rank_order(self):
        ranked = self._ranked(10)
        kept = apply_attention_budget(ranked, "opportunities", "qualified_candidates")
        assert kept == tuple(ranked[:5])

    def test_unknown_page_fails_closed(self):
        with pytest.raises(UnknownAttentionBudgetError, match="unknown attention-budget page"):
            apply_attention_budget(self._ranked(1), "portfolio", "major_events")

    def test_unknown_category_fails_closed(self):
        with pytest.raises(UnknownAttentionBudgetError, match="unknown attention-budget category"):
            apply_attention_budget(self._ranked(1), "today", "minor_events")


@pytest.fixture(scope="module")
def manifest():
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class TestPolicyManifestSync:
    """The manifest is authoritative; the Python constants must mirror it."""

    def test_policy_version_matches_schema_version(self, manifest):
        assert POLICY_VERSION == manifest["schema_version"]

    def test_authority_matches(self, manifest):
        assert POLICY_AUTHORITY == manifest["authority"]

    def test_required_gates_match_exactly_in_order(self, manifest):
        assert list(REQUIRED_GATES) == manifest["required_gates"]

    def test_penalty_codes_match_exactly_in_order(self, manifest):
        assert list(PENALTY_CODES) == manifest["penalties"]

    def test_attention_budgets_match_exactly(self, manifest):
        encoded = {page: dict(categories) for page, categories in ATTENTION_BUDGETS.items()}
        assert encoded == manifest["attention_budgets"]

    def test_manifest_declares_deterministic_and_replayable(self, manifest):
        assert manifest["deterministic_and_replayable"] is True


class TestDeterminism:
    def _random_items(self, rng: random.Random, count: int):
        items = []
        for index in range(count):
            items.append(
                make_input(
                    f"item-{index:03d}",
                    source_tier=rng.choice(("P0", "P1", "P2", "P3", "P4")),
                    received_at=BASE_TIME - timedelta(minutes=rng.randint(0, 500)),
                    quality=rng.choice(
                        (EnvelopeQuality.VALID, EnvelopeQuality.PARTIAL, EnvelopeQuality.STALE)
                    ),
                    rights_usable=rng.random() < 0.8,
                    source_allowed=rng.random() < 0.9,
                    identity_status=rng.choice((IdentityStatus.RESOLVED, IdentityStatus.AMBIGUOUS)),
                    security_or_quality_incident=rng.random() < 0.1,
                    manual_position=rng.random() < 0.2,
                    active_thesis_or_alert=rng.random() < 0.2,
                    watchlist=rng.random() < 0.3,
                    recently_analyzed=rng.random() < 0.3,
                    global_market_event=rng.random() < 0.2,
                    novelty=rng.random() < 0.5,
                    penalties=tuple(rng.sample(PENALTY_CODES, rng.randint(0, 3))),
                )
            )
        return items

    @pytest.mark.property
    @settings(max_examples=25, deadline=None)
    @given(
        data_seed=st.integers(min_value=0, max_value=2**31 - 1),
        permutation_seed=st.integers(min_value=0, max_value=2**31 - 1),
        count=st.integers(min_value=1, max_value=30),
    )
    def test_seeded_permutation_never_changes_the_ranking(self, data_seed, permutation_seed, count):
        items = self._random_items(random.Random(data_seed), count)
        shuffled = list(items)
        random.Random(permutation_seed).shuffle(shuffled)

        original = rank_items(items, as_of=AS_OF)
        permuted = rank_items(shuffled, as_of=AS_OF)

        assert original == permuted
        assert canonical_json_hash(original) == canonical_json_hash(permuted)

    def test_replaying_twice_is_identical(self):
        items = self._random_items(random.Random(99), 20)
        first = rank_items(items, as_of=AS_OF)
        second = rank_items(items, as_of=AS_OF)
        assert first == second
        assert canonical_json_hash(first) == canonical_json_hash(second)
