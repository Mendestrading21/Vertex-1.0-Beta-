"""Scale proof: 10 000 SYNTHETIC observations, 30% multi-level duplicates.

Construction (fully deterministic, seeded shuffle before fusion):

- 7 000 unique base articles (ids ``base-0000`` .. ``base-6999``);
- 1 000 native-id duplicates of bases 0..999 (same source + native id);
- 1 000 canonical-url duplicates of bases 1000..1999 (URL variant that
  normalizes identically, received within the window);
- 1 000 title-fingerprint duplicates of bases 2000..2999 (accent, case and
  punctuation variants of the title, same entity).

Expected exactly: 7 000 clusters (3 000 pairs + 4 000 singletons), 1 000
decisions per linking level, 4 000 KEPT_DISTINCT, zero FLAGGED_SIMILAR and
zero deletion (all 10 000 members and observations retained).
"""

import random
from collections import Counter
from datetime import timedelta

from tests.fusion.factories import BASE_TIME, SOURCES, make_observation
from vertex_core.fusion import FusionAction, fuse


def _build_corpus():
    observations = []
    for i in range(7000):
        observations.append(
            make_observation(
                f"base-{i:04d}",
                source=SOURCES[i % 3],
                source_tier=f"P{i % 5}",
                native_id=f"nid-{i}",
                canonical_url=f"https://news.example.com/articles/{i}",
                title=f"Company {i} reports quarterly results {i}",
                entities=(f"ENT{i}",),
                published_at=BASE_TIME + timedelta(seconds=i),
                received_at=BASE_TIME + timedelta(seconds=i, minutes=5),
            )
        )
    for i in range(1000):
        observations.append(
            make_observation(
                f"dup-native-{i:04d}",
                source=SOURCES[i % 3],
                source_tier="P3",
                native_id=f"nid-{i}",
                title=f"Mirror headline {i} unrelated wording",
                entities=(f"ENT{i}",),
                received_at=BASE_TIME + timedelta(seconds=i, hours=1),
            )
        )
    for i in range(1000, 2000):
        observations.append(
            make_observation(
                f"dup-url-{i:04d}",
                source=SOURCES[(i + 1) % 3],
                source_tier="P4",
                canonical_url=(
                    f"HTTPS://NEWS.Example.COM/articles/{i}?utm_campaign=z&gclid=1#frag"
                ),
                title=f"Copy headline {i} distinct words",
                entities=(f"ENT{i}",),
                published_at=BASE_TIME + timedelta(seconds=i, hours=2),
                received_at=BASE_TIME + timedelta(seconds=i, hours=3),
            )
        )
    for i in range(2000, 3000):
        observations.append(
            make_observation(
                f"dup-fp-{i:04d}",
                source=SOURCES[(i + 2) % 3],
                source_tier="P2",
                title=f"COMPÀNY {i}, réports (quarterly) RESULTS {i}!!",
                entities=(f"ent{i}",),
                received_at=BASE_TIME + timedelta(seconds=i, hours=4),
            )
        )
    return observations


def test_ten_thousand_observations_thirty_percent_duplicates_exact_counts():
    observations = _build_corpus()
    assert len(observations) == 10000
    random.Random(42).shuffle(observations)  # seeded permutation before fusion

    result = fuse(observations)

    # Exact cluster accounting: 3000 pairs + 4000 singletons.
    sizes = Counter(len(cluster.member_ids) for cluster in result.clusters)
    assert len(result.clusters) == 7000
    assert sizes == {2: 3000, 1: 4000}

    # Exact decision accounting per level; similarity never fired.
    action_counts = Counter(
        decision.action for cluster in result.clusters for decision in cluster.decisions
    )
    assert action_counts == {
        FusionAction.LINKED_NATIVE_ID: 1000,
        FusionAction.LINKED_CANONICAL_URL: 1000,
        FusionAction.LINKED_FINGERPRINT: 1000,
        FusionAction.KEPT_DISTINCT: 4000,
    }

    # Zero deletion: every observation retained, each in exactly one cluster.
    member_ids = [m for cluster in result.clusters for m in cluster.member_ids]
    assert len(member_ids) == 10000
    assert len(set(member_ids)) == 10000
    assert set(member_ids) == {obs.content_id for obs in observations}
    assert len(result.observations) == 10000

    # Each duplicate landed next to its intended base.
    by_member = {m: cluster for cluster in result.clusters for m in cluster.member_ids}
    for i in (0, 500, 999):
        assert f"base-{i:04d}" in by_member[f"dup-native-{i:04d}"].member_ids
    for i in (1000, 1500, 1999):
        assert f"base-{i:04d}" in by_member[f"dup-url-{i:04d}"].member_ids
    for i in (2000, 2500, 2999):
        assert f"base-{i:04d}" in by_member[f"dup-fp-{i:04d}"].member_ids
