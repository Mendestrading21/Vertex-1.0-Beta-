"""SYNTHETIC observation factories for fusion tests (no real market data)."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from vertex_core.contracts import EnvelopeQuality
from vertex_core.fusion import ContentObservation

BASE_TIME = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

SOURCES = ("ibkr_news", "sec", "primary_ir")


def make_observation(
    content_id: str,
    *,
    source: str = "ibkr_news",
    source_tier: str = "P1",
    native_id: str | None = None,
    canonical_url: str | None = None,
    title: str = "Synthetic headline",
    entities: tuple[str, ...] = (),
    published_at: datetime | None = None,
    received_at: datetime | None = None,
    rights: str = "display_only",
    quality: EnvelopeQuality = EnvelopeQuality.VALID,
    is_deleted: bool = False,
) -> ContentObservation:
    return ContentObservation(
        content_id=content_id,
        source=source,
        source_tier=source_tier,
        native_id=native_id,
        canonical_url=canonical_url,
        title=title,
        entities=entities,
        published_at=published_at,
        received_at=received_at if received_at is not None else BASE_TIME,
        rights=rights,
        quality=quality,
        is_deleted=is_deleted,
    )


def make_random_observations(rng: random.Random, count: int) -> list[ContentObservation]:
    """Random SYNTHETIC observations drawn from small pools to force
    collisions across every deduplication level (deterministic per seed)."""
    titles = (
        "Acme Corp beats earnings estimates",
        "Acme Corp beats earnings expectations",
        "Globex announces dividend increase",
        "Regulator opens inquiry into Initech",
        "Márket recap: indices close mixed!",
    )
    urls = (
        None,
        "https://news.example.com/a?utm_source=x",
        "HTTPS://News.Example.com/a",
        "https://news.example.com/b?id=2#frag",
        "https://other.example.org/c",
    )
    native_ids = (None, "n-1", "n-2", "n-3")
    entity_pool = ("ACME", "GLOBEX", "INITECH", "SPX")
    observations = []
    for index in range(count):
        entity_count = rng.randint(0, 2)
        observations.append(
            make_observation(
                f"obs-{index:04d}",
                source=rng.choice(SOURCES),
                source_tier=rng.choice(("P0", "P1", "P2", "P3", "P4")),
                native_id=rng.choice(native_ids),
                canonical_url=rng.choice(urls),
                title=rng.choice(titles),
                entities=tuple(rng.sample(entity_pool, entity_count)),
                published_at=(
                    BASE_TIME + timedelta(minutes=rng.randint(-3000, 0))
                    if rng.random() < 0.7
                    else None
                ),
                received_at=BASE_TIME + timedelta(minutes=rng.randint(0, 3000)),
                rights=rng.choice(("display_only", "redistribute")),
                quality=rng.choice((EnvelopeQuality.VALID, EnvelopeQuality.PARTIAL)),
                is_deleted=rng.random() < 0.05,
            )
        )
    return observations
