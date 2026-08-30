"""Deterministic deduplication: the five levels, replay and zero deletion."""

import random
from datetime import timedelta

import pytest
from hypothesis import given, settings, strategies as st

from vertex_core.contracts import EnvelopeQuality
from vertex_core.fusion import (
    FUSION_RULESET_VERSION,
    FusionAction,
    FusionInputError,
    fuse,
    fusion_result_hash,
    RULE_POLARITY_CONFLICT,
    normalize_canonical_url,
    normalize_title,
    opposed_markers,
    title_fingerprint,
    title_polarity_markers,
)
from tests.fusion.factories import BASE_TIME, make_observation, make_random_observations


def _actions(result):
    return [
        decision.action
        for cluster in result.clusters
        for decision in cluster.decisions
    ]


class TestNormalization:
    def test_url_host_and_scheme_lowercased_fragment_stripped(self):
        assert (
            normalize_canonical_url("HTTPS://News.Example.COM/Path/A#section")
            == "https://news.example.com/Path/A"
        )

    def test_url_path_case_preserved(self):
        assert normalize_canonical_url("https://a.example/CaseSensitive") == (
            "https://a.example/CaseSensitive"
        )

    def test_listed_tracking_params_stripped_and_rest_sorted(self):
        assert (
            normalize_canonical_url(
                "https://a.example/x?utm_campaign=z&b=2&gclid=123&a=1&fbclid=9"
            )
            == "https://a.example/x?a=1&b=2"
        )

    def test_utm_prefix_stripped_case_insensitively(self):
        assert (
            normalize_canonical_url("https://a.example/x?UTM_Source=mail&id=5")
            == "https://a.example/x?id=5"
        )

    def test_title_accents_case_punctuation_whitespace_normalized(self):
        assert (
            normalize_title("  Compàny-1:  RÉPORTS   qúarterly, results!! ")
            == "company 1 reports quarterly results"
        )

    def test_punctuation_only_title_has_no_fingerprint(self):
        assert title_fingerprint("!!! ---", ("ACME",)) is None

    def test_fingerprint_sorts_and_normalizes_entities(self):
        assert title_fingerprint("Same title", ("Beta", "ACME")) == title_fingerprint(
            "same TITLE!", ("acme", "béta")
        )


class TestLevel1NativeId:
    def test_same_source_same_native_id_linked(self):
        result = fuse(
            [
                make_observation("a", native_id="n1", title="First wording", entities=("E1",)),
                make_observation("b", native_id="n1", title="Second wording", entities=("E2",)),
            ]
        )
        assert len(result.clusters) == 1
        assert result.clusters[0].member_ids == ("a", "b")
        assert _actions(result) == [FusionAction.LINKED_NATIVE_ID]
        decision = result.clusters[0].decisions[0]
        assert decision.rule_version == FUSION_RULESET_VERSION
        assert decision.inputs == ("a", "b")
        assert decision.reversible is False

    def test_same_native_id_different_source_not_linked(self):
        result = fuse(
            [
                make_observation("a", source="ibkr_news", native_id="n1", title="One", entities=("E1",)),
                make_observation("b", source="sec", native_id="n1", title="Two", entities=("E2",)),
            ]
        )
        assert len(result.clusters) == 2


class TestLevel2CanonicalUrl:
    def test_normalized_url_within_window_linked(self):
        result = fuse(
            [
                make_observation(
                    "a",
                    canonical_url="HTTPS://News.Example.com/x?utm_source=z#frag",
                    title="Alpha wording",
                    entities=("E1",),
                    received_at=BASE_TIME,
                ),
                make_observation(
                    "b",
                    source="sec",
                    canonical_url="https://news.example.com/x",
                    title="Beta wording",
                    entities=("E2",),
                    received_at=BASE_TIME + timedelta(hours=47),
                ),
            ]
        )
        assert len(result.clusters) == 1
        assert _actions(result) == [FusionAction.LINKED_CANONICAL_URL]

    def test_same_url_outside_window_not_linked(self):
        result = fuse(
            [
                make_observation(
                    "a",
                    canonical_url="https://news.example.com/x",
                    title="Alpha wording",
                    entities=("E1",),
                    received_at=BASE_TIME,
                ),
                make_observation(
                    "b",
                    canonical_url="https://news.example.com/x",
                    title="Beta wording",
                    entities=("E2",),
                    received_at=BASE_TIME + timedelta(hours=49),
                ),
            ]
        )
        assert len(result.clusters) == 2

    def test_published_at_preferred_over_received_at_for_window(self):
        result = fuse(
            [
                make_observation(
                    "a",
                    canonical_url="https://news.example.com/x",
                    title="Alpha wording",
                    entities=("E1",),
                    published_at=BASE_TIME,
                    received_at=BASE_TIME + timedelta(hours=100),
                ),
                make_observation(
                    "b",
                    canonical_url="https://news.example.com/x",
                    title="Beta wording",
                    entities=("E2",),
                    published_at=BASE_TIME + timedelta(hours=1),
                    received_at=BASE_TIME + timedelta(hours=200),
                ),
            ]
        )
        assert len(result.clusters) == 1

    def test_chain_within_window_links_transitively(self):
        result = fuse(
            [
                make_observation(
                    "a",
                    canonical_url="https://news.example.com/x",
                    title="T one",
                    entities=("E1",),
                    received_at=BASE_TIME,
                ),
                make_observation(
                    "b",
                    canonical_url="https://news.example.com/x",
                    title="T two",
                    entities=("E2",),
                    received_at=BASE_TIME + timedelta(hours=40),
                ),
                make_observation(
                    "c",
                    canonical_url="https://news.example.com/x",
                    title="T three",
                    entities=("E3",),
                    received_at=BASE_TIME + timedelta(hours=80),
                ),
            ]
        )
        assert len(result.clusters) == 1
        assert result.clusters[0].member_ids == ("a", "b", "c")


class TestLevel3Fingerprint:
    def test_title_variants_with_same_entities_linked(self):
        result = fuse(
            [
                make_observation("a", title="Compàny One réports, quarterly results!", entities=("ACME",)),
                make_observation("b", source="sec", title="company one REPORTS quarterly results", entities=("acme",)),
            ]
        )
        assert len(result.clusters) == 1
        assert _actions(result) == [FusionAction.LINKED_FINGERPRINT]

    def test_same_title_different_entities_not_linked(self):
        result = fuse(
            [
                make_observation("a", title="Quarterly results announced", entities=("ACME",), received_at=BASE_TIME + timedelta(hours=30)),
                make_observation("b", title="Quarterly results announced", entities=("GLOBEX",), received_at=BASE_TIME),
            ]
        )
        assert len(result.clusters) == 2


class TestLevel4SimilarityFlag:
    def _similar_pair(self, gap=timedelta(hours=2)):
        return [
            make_observation(
                "a",
                title="Acme Corp beats earnings estimates",
                entities=("ACME",),
                received_at=BASE_TIME,
            ),
            make_observation(
                "b",
                source="sec",
                title="Acme Corp beats earnings expectations",
                entities=("ACME",),
                received_at=BASE_TIME + gap,
            ),
        ]

    def test_flag_is_reversible_and_never_merges(self):
        result = fuse(self._similar_pair())
        assert len(result.clusters) == 2  # never a destructive merge
        flags = [d for d in _actions(result) if d is FusionAction.FLAGGED_SIMILAR]
        assert len(flags) == 2  # the same decision is visible on both clusters
        flag_decisions = {
            decision.decision_id
            for cluster in result.clusters
            for decision in cluster.decisions
            if decision.action is FusionAction.FLAGGED_SIMILAR
        }
        assert len(flag_decisions) == 1
        for cluster in result.clusters:
            for decision in cluster.decisions:
                if decision.action is FusionAction.FLAGGED_SIMILAR:
                    assert decision.reversible is True
                    assert decision.inputs == ("a", "b")

    def test_no_flag_outside_time_window(self):
        result = fuse(self._similar_pair(gap=timedelta(hours=25)))
        assert FusionAction.FLAGGED_SIMILAR not in _actions(result)

    def test_no_flag_without_shared_entity(self):
        observations = [
            make_observation("a", title="Acme Corp beats earnings estimates", entities=("ACME",)),
            make_observation(
                "b",
                title="Acme Corp beats earnings expectations",
                entities=("GLOBEX",),
                received_at=BASE_TIME + timedelta(hours=1),
            ),
        ]
        result = fuse(observations)
        assert FusionAction.FLAGGED_SIMILAR not in _actions(result)

    def test_no_flag_for_dissimilar_titles(self):
        observations = [
            make_observation("a", title="Acme Corp beats earnings estimates", entities=("ACME",)),
            make_observation(
                "b",
                title="Regulator opens antitrust inquiry into Acme",
                entities=("ACME",),
                received_at=BASE_TIME + timedelta(hours=1),
            ),
        ]
        result = fuse(observations)
        assert FusionAction.FLAGGED_SIMILAR not in _actions(result)


class TestLevel5ClusterConstruction:
    def test_cluster_preserves_all_providers_rights_and_dates(self):
        result = fuse(
            [
                make_observation(
                    "a",
                    native_id="n1",
                    source_tier="P2",
                    rights="display_only",
                    title="First wording",
                    entities=("E1",),
                    published_at=BASE_TIME - timedelta(hours=1),
                    received_at=BASE_TIME,
                ),
                make_observation(
                    "b",
                    native_id="n1",
                    source_tier="P0",
                    rights="redistribute",
                    title="Second wording",
                    entities=("E2",),
                    received_at=BASE_TIME + timedelta(hours=3),
                ),
            ]
        )
        cluster = result.clusters[0]
        assert cluster.sources == ("ibkr_news",)
        assert cluster.tiers == ("P0", "P2")
        assert cluster.rights == ("display_only", "redistribute")
        assert cluster.first_published_at == BASE_TIME - timedelta(hours=1)
        assert cluster.last_received_at == BASE_TIME + timedelta(hours=3)

    def test_no_member_published_at_stays_none(self):
        result = fuse([make_observation("a", title="Solo", entities=("E1",))])
        assert result.clusters[0].first_published_at is None

    def test_singleton_gets_kept_distinct_decision(self):
        result = fuse([make_observation("a", title="Solo", entities=("E1",))])
        cluster = result.clusters[0]
        assert [d.action for d in cluster.decisions] == [FusionAction.KEPT_DISTINCT]
        assert cluster.decisions[0].inputs == ("a",)
        assert cluster.decisions[0].reversible is True

    def test_deleted_member_keeps_its_observation(self):
        deleted = make_observation(
            "b", native_id="n1", title="Deleted wording", entities=("E2",), is_deleted=True
        )
        result = fuse(
            [
                make_observation("a", native_id="n1", title="Live wording", entities=("E1",)),
                deleted,
            ]
        )
        assert result.clusters[0].member_ids == ("a", "b")
        assert deleted in result.observations  # zero physical deletion

    def test_duplicate_content_id_rejected(self):
        with pytest.raises(FusionInputError, match="duplicate content_id"):
            fuse([make_observation("a"), make_observation("a")])

    def test_empty_input_yields_empty_result(self):
        result = fuse([])
        assert result.clusters == ()
        assert result.observations == ()


class TestDeterminism:
    @pytest.mark.property
    @settings(max_examples=25, deadline=None)
    @given(
        data_seed=st.integers(min_value=0, max_value=2**31 - 1),
        permutation_seed=st.integers(min_value=0, max_value=2**31 - 1),
        count=st.integers(min_value=2, max_value=40),
    )
    def test_seeded_permutation_never_changes_the_result(
        self, data_seed, permutation_seed, count
    ):
        observations = make_random_observations(random.Random(data_seed), count)
        shuffled = list(observations)
        random.Random(permutation_seed).shuffle(shuffled)

        original = fuse(observations)
        permuted = fuse(shuffled)

        assert [c.cluster_id for c in original.clusters] == [
            c.cluster_id for c in permuted.clusters
        ]
        assert [c.decisions for c in original.clusters] == [
            c.decisions for c in permuted.clusters
        ]
        assert original == permuted
        assert fusion_result_hash(original) == fusion_result_hash(permuted)

    def test_replaying_twice_is_identical(self):
        observations = make_random_observations(random.Random(1234), 30)
        first, second = fuse(observations), fuse(observations)
        assert first == second
        assert fusion_result_hash(first) == fusion_result_hash(second)


class TestPolarityIsData:
    """The sign of a financial variation is data, never punctuation.

    Reproducer for the erased-sign defect: two OPPOSITE headlines used to
    normalize to one string, share one fingerprint and fuse into a single
    cluster, so a rise could be published in place of a fall with no
    contradiction signalled anywhere.
    """

    OPPOSITE_PAIRS = (
        ("SPX -3,2 % sur la seance", "SPX +3,2 % sur la seance"),
        ("Apple : resultat trimestriel -5 %", "Apple : resultat trimestriel +5 %"),
        ("SPX ↓3,2 % sur la seance", "SPX ↑3,2 % sur la seance"),
        ("SPX ▼3,2 % sur la seance", "SPX ▲3,2 % sur la seance"),
        ("Benefice > attentes", "Benefice < attentes"),
    )

    @pytest.mark.parametrize("negative,positive", OPPOSITE_PAIRS)
    def test_opposite_titles_never_share_a_normalized_form(self, negative, positive):
        assert normalize_title(negative) != normalize_title(positive)

    @pytest.mark.parametrize("negative,positive", OPPOSITE_PAIRS)
    def test_opposite_titles_never_share_a_fingerprint(self, negative, positive):
        assert title_fingerprint(negative, ("SPX",)) != title_fingerprint(
            positive, ("SPX",)
        )

    @pytest.mark.parametrize("negative,positive", OPPOSITE_PAIRS)
    def test_opposite_titles_are_never_fused_by_the_fingerprint(
        self, negative, positive
    ):
        result = fuse(
            [
                make_observation("c1", title=negative, entities=("SPX",)),
                make_observation("c2", title=positive, entities=("SPX",)),
            ]
        )
        assert len(result.clusters) == 2
        assert FusionAction.LINKED_FINGERPRINT not in _actions(result)

    def test_polarity_markers_are_exposed_and_canonicalized(self):
        assert title_polarity_markers("SPX -3,2 %") == ("-",)
        assert title_polarity_markers("SPX −3,2 %") == ("-",)  # U+2212 minus
        assert title_polarity_markers("SPX ↓ 3,2 %") == ("-",)  # down arrow
        assert title_polarity_markers("SPX +3,2 %") == ("+",)
        assert title_polarity_markers("SPX ↑ 3,2 %") == ("+",)
        assert title_polarity_markers("Benefice > attentes") == (">",)
        assert title_polarity_markers("Benefice ≤ attentes") == ("<",)
        assert title_polarity_markers("Resultat trimestriel publie") == ()

    def test_sign_variants_of_one_dispatch_still_merge(self):
        """Typography must not split one event: U+2212, ASCII '-' and the
        down arrow all assert the same polarity on the same figure."""
        reference = title_fingerprint("SPX -3,2 % sur la seance", ("SPX",))
        for variant in (
            "SPX −3,2 % sur la seance",
            "SPX ↓3,2 % sur la seance",
            "SPX ↓ 3,2 % sur la seance",
            "spx  -3.2 %,  SUR la  seance!",
        ):
            assert title_fingerprint(variant, ("SPX",)) == reference

    def test_hyphen_between_words_stays_punctuation(self):
        """The existing normalization must not be broken by the sign fix."""
        assert (
            normalize_title("  Compàny-1:  RÉPORTS   qúarterly, results!! ")
            == "company 1 reports quarterly results"
        )
        assert normalize_title("COVID-19 impact") == "covid 19 impact"
        assert title_polarity_markers("COVID-19 impact") == ()
        # A dash used as a separator (space-separated) is not a sign either.
        assert title_polarity_markers("Apple - 3 nouveaux produits") == ()

    def test_unsigned_figure_is_not_declared_opposite_of_a_signed_one(self):
        """Absent is not the opposite of negative: distinct, but no conflict."""
        result = fuse(
            [
                make_observation(
                    "c1", title="Apple : resultat trimestriel -5 %", entities=("AAPL",)
                ),
                make_observation(
                    "c2", title="Apple : resultat trimestriel 5 %", entities=("AAPL",)
                ),
            ]
        )
        assert len(result.clusters) == 2
        assert FusionAction.FLAGGED_POLARITY_CONFLICT not in _actions(result)


class TestPolarityConflictInsideACluster:
    """Provider identity (levels 1 and 2) still links; the contradiction is
    published instead of being silently represented by one member."""

    def _opposite_pair(self, **kwargs):
        return [
            make_observation(
                "c1", title="SPX -3,2 % sur la seance", entities=("SPX",), **kwargs
            ),
            make_observation(
                "c2", title="SPX +3,2 % sur la seance", entities=("SPX",), **kwargs
            ),
        ]

    def _conflicts(self, result):
        return [
            decision
            for cluster in result.clusters
            for decision in cluster.decisions
            if decision.action is FusionAction.FLAGGED_POLARITY_CONFLICT
        ]

    def test_same_native_id_cluster_publishes_a_polarity_conflict(self):
        result = fuse(self._opposite_pair(native_id="n1"))
        assert len(result.clusters) == 1  # provider identity is not overridden
        assert result.clusters[0].member_ids == ("c1", "c2")
        conflicts = self._conflicts(result)
        assert len(conflicts) == 1
        conflict = conflicts[0]
        assert conflict.inputs == ("c1", "c2")
        assert conflict.reversible is True
        assert conflict.rule_id == RULE_POLARITY_CONFLICT
        assert "'-'" in conflict.rationale and "'+'" in conflict.rationale

    def test_same_canonical_url_cluster_publishes_a_polarity_conflict(self):
        result = fuse(self._opposite_pair(canonical_url="https://news.example.com/x"))
        assert len(result.clusters) == 1
        assert len(self._conflicts(result)) == 1

    def test_agreeing_cluster_publishes_no_conflict(self):
        result = fuse(
            [
                make_observation(
                    "c1",
                    native_id="n1",
                    title="SPX -3,2 % sur la seance",
                    entities=("SPX",),
                ),
                make_observation(
                    "c2",
                    native_id="n1",
                    title="SPX −3,2 % a la cloture",
                    entities=("SPX",),
                ),
            ]
        )
        assert len(result.clusters) == 1
        assert self._conflicts(result) == []

    def test_conflict_never_deletes_and_never_splits(self):
        observations = self._opposite_pair(native_id="n1")
        result = fuse(observations)
        assert len(result.observations) == 2
        assert [obs.content_id for obs in result.observations] == ["c1", "c2"]

    def test_opposite_polarity_pair_is_flagged_conflict_not_similar(self):
        """Calling two contradictory headlines 'similar' is the misleading
        label; across clusters the pair is named a polarity conflict."""
        result = fuse(
            [
                make_observation(
                    "c1",
                    title="Acme Corp resultat annuel -12 %",
                    entities=("ACME",),
                    received_at=BASE_TIME,
                ),
                make_observation(
                    "c2",
                    source="sec",
                    title="Acme Corp resultat annuel +12 %",
                    entities=("ACME",),
                    received_at=BASE_TIME + timedelta(hours=2),
                ),
            ]
        )
        assert len(result.clusters) == 2
        actions = _actions(result)
        assert FusionAction.FLAGGED_SIMILAR not in actions
        assert actions.count(FusionAction.FLAGGED_POLARITY_CONFLICT) == 2


class TestPolarityProperties:
    def test_marker_only_title_has_no_fingerprint(self):
        """A title reduced to markers must not become a wildcard bucket."""
        assert title_fingerprint("↑↓", ("ACME",)) is None
        assert title_fingerprint("> <", ("ACME",)) is None
        assert title_fingerprint("!!! ---", ("ACME",)) is None

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        head=st.text(alphabet="abcdefgh ", min_size=1, max_size=12),
        digits=st.text(alphabet="0123456789", min_size=1, max_size=6),
        tail=st.text(alphabet="ijklmnop ", min_size=1, max_size=12),
    )
    def test_a_sign_flip_always_changes_the_fingerprint(self, head, digits, tail):
        negative = f"{head} -{digits} % {tail}"
        positive = f"{head} +{digits} % {tail}"
        assert normalize_title(negative) != normalize_title(positive)
        assert title_fingerprint(negative, ("ACME",)) != title_fingerprint(
            positive, ("ACME",)
        )

    @pytest.mark.property
    @settings(max_examples=100, deadline=None)
    @given(
        head=st.text(alphabet="abcdefgh ", min_size=1, max_size=12),
        digits=st.text(alphabet="0123456789", min_size=1, max_size=6),
    )
    def test_opposed_markers_is_symmetric_and_never_self_opposed(self, head, digits):
        negative = title_polarity_markers(f"{head} -{digits} %")
        positive = title_polarity_markers(f"{head} +{digits} %")
        assert opposed_markers(negative, negative) is None
        assert opposed_markers(positive, positive) is None
        assert (opposed_markers(negative, positive) is None) == (
            opposed_markers(positive, negative) is None
        )
