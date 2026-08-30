"""P1-1: a relayed VALUE carries a form contract, not merely a type.

The relays validated the STRUCTURE of the persisted content (the field
exists, it is a string) and never its CONTENT. A ``strike``, a
``greeks.delta`` or a ``population`` whose stored value was replaced by an
arbitrary 5038-character string carrying BEL and an ANSI colour escape was
served ``200`` with that value reproduced byte-for-byte on the wire.

Two distinct defects, closed here BY CLASS rather than field by field:

1. those are FINANCIAL values. ``financial-safety.md`` requires an amount, a
   price or a strike to be a decimal — not free text. The relay now applies
   the same admission discipline the worker already applies at ingestion
   (``vertex_worker.analysis._price_or_none`` and the currency / trading-day
   / basis-code allowlists);
2. ``population`` is the very field that separates SYNTHETIC from real.
   Left arbitrary, it lets synthetic content present itself as something
   else, which is exactly what ``financial-safety.md`` forbids. It — and
   every other nature label — now belongs to a CLOSED vocabulary.

Fields that are legitimately FREE PROSE (titles, reasons, labels, the user's
own thesis statement) cannot be given a vocabulary. Their contract is the
only one that holds for free text: a length bound and the refusal of control
characters — the escapes a terminal, a log viewer or a browser interprets
instead of displaying.

Everything below is SYNTHETIC and reaches nothing but the pure builders.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from vertex_api.snapshot_views import (
    MAX_RELAYED_DEPTH,
    MAX_RELAYED_TEXT_LENGTH,
    MAX_RELAYED_USER_TEXT_LENGTH,
    POPULATION_LABELS,
    SnapshotContentError,
    checked_relayed_content,
)

#: The exact payload the fourth adversarial audit relayed verbatim.
HOSTILE = "ACHETEZ MAINTENANT" + "\x07" + "\x1b" + "[31m gain garanti " + "Z" * 5000


def test_the_audited_payload_is_5038_characters() -> None:
    """Pins the reproducer itself: BEL + ANSI escape + 5000 filler."""
    assert len(HOSTILE) == 5038
    assert "\x07" in HOSTILE and "\x1b[31m" in HOSTILE


# ---------------------------------------------------------------------------
# Financial values: a decimal, never free text
# ---------------------------------------------------------------------------

#: Values a naive check (or ``Decimal()`` itself) accepts and the relay would
#: then publish AS A PRICE.
NOT_A_PLAIN_DECIMAL = [
    HOSTILE,
    "204,00",  # decimal comma
    " 204.00",  # leading space
    "204.00 ",  # trailing space
    "204.00\n",  # trailing newline
    "1e3",  # exponent
    "1E3",
    "0x10",
    "204_00",  # underscore separator (Decimal accepts it)
    "２０４.００",  # fullwidth digits (Decimal accepts them)
    "NaN",
    "Infinity",
    "-Infinity",
    "+204.00",  # explicit sign on a price
    "",
    "204.",
    ".50",
    "00204.00",  # leading zeros
]


@pytest.mark.parametrize("forged", NOT_A_PLAIN_DECIMAL)
@pytest.mark.parametrize(
    "field", ["strike", "last_close", "bid", "ask", "premium", "value"]
)
def test_a_financial_value_must_be_a_plain_decimal(field: str, forged: Any) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({field: forged})
    assert excinfo.value.field == field


@pytest.mark.parametrize("healthy", ["0", "204", "204.00", "0.9974588739230033"])
def test_a_well_formed_price_is_relayed_unchanged(healthy: str) -> None:
    content = {"strike": healthy}
    assert checked_relayed_content(content) == content


def test_a_price_may_not_be_negative_but_a_greek_may() -> None:
    """The sign is part of the class, not of the field name.

    A strike or a quote is non-negative by construction; a Greek, a rate or a
    scenario P&L is signed. Both remain plain decimals.
    """
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"strike": "-204.00"})
    assert excinfo.value.field == "strike"
    assert checked_relayed_content({"greeks": {"delta": "-0.9974588739230033"}})


@pytest.mark.parametrize("forged", [HOSTILE, "45,5", "45.5%", "abc"])
def test_a_published_percentage_must_be_a_decimal(forged: str) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"return_1d_pct": forged})
    assert excinfo.value.field == "return_1d_pct"


def test_a_published_percentage_keeps_its_explicit_sign() -> None:
    """``+1.74`` reads as a direction without a recomputation."""
    assert checked_relayed_content({"return_1d_pct": "+1.74"})
    assert checked_relayed_content({"return_1d_pct": "-1.74"})


# ---------------------------------------------------------------------------
# Nature labels: a CLOSED vocabulary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forged",
    [
        HOSTILE,
        "REEL",
        "PRODUCTION",
        "LIVE",
        "real",
        "Real",
        "REAL ",
        " REAL",
        "SYNTHETIC/REAL",
        "",
    ],
)
def test_population_belongs_to_a_closed_vocabulary(forged: str) -> None:
    """The field that separates synthetic from real may not be free text."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"population": forged})
    assert excinfo.value.field == "population"


@pytest.mark.parametrize("label", sorted(POPULATION_LABELS))
def test_every_declared_nature_label_is_relayable(label: str) -> None:
    assert checked_relayed_content({"population": label}) == {"population": label}


def test_the_closed_vocabulary_keeps_the_declared_natures_apart() -> None:
    """Real, delayed, theoretical, simulated and demonstration all exist and
    stay DISTINCT members — none of them is a synonym of another."""
    for label in ("REAL", "DELAYED", "THEORETICAL", "SIMULATED", "DEMO"):
        assert label in POPULATION_LABELS
    assert "SYNTHETIC" in POPULATION_LABELS


@pytest.mark.parametrize(
    "path,forged",
    [
        ({"value_nature": "OBSERVED"}, "value_nature"),
        ({"value_nature": HOSTILE}, "value_nature"),
        ({"data_state": "OK"}, "data_state"),
        ({"data_state": HOSTILE}, "data_state"),
        ({"delay_status": "REALTIME"}, "delay_status"),
        ({"delay_status": HOSTILE}, "delay_status"),
        ({"populations": {"theses": "GUESSED"}}, "populations.theses"),
    ],
)
def test_every_nature_label_is_closed(path: dict, forged: str) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(path)
    assert excinfo.value.field == forged


@pytest.mark.parametrize(
    "key,forged",
    [
        ("right", "call"),
        ("style", "BERMUDAN"),
        ("settlement", "NET"),
        ("direction", "UP"),
        ("quality", "FINE"),
        ("identity_status", "PROBABLY"),
    ],
)
def test_a_canonical_enumeration_is_read_from_vertex_core(
    key: str, forged: str
) -> None:
    """The relay never redefines a vocabulary ``vertex_core`` owns."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({key: forged})
    assert excinfo.value.field == key


# ---------------------------------------------------------------------------
# Technical codes, instants, calendar days, currencies, timezones
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key,forged",
    [
        ("currency", "SYNTHETIC"),
        ("currency", "syn"),
        ("currency", HOSTILE),
        ("trading_day", "2026-13-45"),
        ("trading_day", "29/08/2026"),
        ("trading_day", HOSTILE),
        ("expiration", HOSTILE),
        ("as_of", "2026-08-29T23:25:50"),  # naive
        ("as_of", HOSTILE),
        ("engine_version", "vertex core 0.1.0"),  # spaces
        ("engine_version", HOSTILE),
        ("ticker", "SYN TECH 01"),
        ("input_hash", "sha256:not-hex"),
        ("input_hash", HOSTILE),
        ("status", "ok"),  # a status token is uppercase
        ("status", HOSTILE),
    ],
)
def test_a_technical_code_must_match_its_declared_shape(
    key: str, forged: str
) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({key: forged})
    assert excinfo.value.field == key


def test_a_content_hash_follows_the_contract_type_of_vertex_core() -> None:
    """Exactly ``vertex_core.contracts.types.Sha256Ref``."""
    assert checked_relayed_content({"input_hash": "sha256:" + "a" * 64})
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"input_hash": "sha256:" + "a" * 63})


@pytest.mark.parametrize(
    "forged",
    ["Mars/Olympus", "Europe/Atlantis", "../../etc/passwd", "/etc/localtime", HOSTILE],
)
def test_an_exchange_timezone_must_be_a_resolvable_iana_zone(forged: str) -> None:
    """P2-1: the single leak of the calendar's 'unreadable value = refusal'."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"exchange_timezone": forged})
    assert excinfo.value.field == "exchange_timezone"


@pytest.mark.parametrize("zone", ["Europe/Zurich", "America/New_York", "UTC"])
def test_a_real_iana_zone_is_relayed(zone: str) -> None:
    assert checked_relayed_content({"exchange_timezone": zone})


# ---------------------------------------------------------------------------
# Prose: no vocabulary to impose, but a bound and no control characters
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "control",
    ["\x00", "\x07", "\x1b", "\x1b[31m", "\r", "\n", "\t", "\x7f", "​", "‮"],
)
@pytest.mark.parametrize("key", ["title", "label", "reason", "conclusion", "message"])
def test_prose_refuses_control_characters(key: str, control: str) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({key: f"synthetic{control}label"})
    assert excinfo.value.field == key


def test_prose_is_bounded() -> None:
    assert checked_relayed_content({"title": "T" * MAX_RELAYED_TEXT_LENGTH})
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"title": "T" * (MAX_RELAYED_TEXT_LENGTH + 1)})
    assert excinfo.value.field == "title"


def test_prose_keeps_accented_french_text() -> None:
    """The product speaks French: the bound is on length, not on alphabet."""
    content = {"label": "Énergie synthétique — secteur écarté"}
    assert checked_relayed_content(content) == content


def test_a_user_statement_may_span_lines_up_to_the_write_contract_bound() -> None:
    """The relay serves back exactly what ``POST /api/v1/theses`` accepted."""
    statement = "ligne une\nligne deux\tsuite"
    assert checked_relayed_content({"hypotheses": statement})
    assert checked_relayed_content(
        {"invalidation": "I" * MAX_RELAYED_USER_TEXT_LENGTH}
    )
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {"invalidation": "I" * (MAX_RELAYED_USER_TEXT_LENGTH + 1)}
        )
    assert excinfo.value.field == "invalidation"
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"hypotheses": "escape\x1b[31m here"})


def test_an_unknown_field_falls_back_to_the_prose_contract() -> None:
    """Deny-by-default: a key this map does not know is still bounded and
    control-free — it is simply not yet constrained as a decimal."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"a_field_nobody_declared": HOSTILE})
    assert excinfo.value.field == "a_field_nobody_declared"


# ---------------------------------------------------------------------------
# Structure of the relayed content itself
# ---------------------------------------------------------------------------


def test_a_relayed_mapping_key_is_checked_like_a_value() -> None:
    """A key travels to the wire exactly like the value it addresses."""
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"coverage": {HOSTILE: 1}})
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"coverage": {"": 1}})


def test_a_relayed_content_is_depth_bounded() -> None:
    node: Any = "SYNTHETIC"
    for _ in range(MAX_RELAYED_DEPTH + 4):
        node = {"nested": node}
    with pytest.raises(SnapshotContentError):
        checked_relayed_content(node)


def test_the_path_of_a_nested_refusal_is_named_exactly() -> None:
    content = {
        "expirations": [
            {"contracts": [{"strike": "204.00"}, {"strike": HOSTILE}]},
        ]
    }
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(content)
    assert excinfo.value.field == "expirations[0].contracts[1].strike"


# ---------------------------------------------------------------------------
# A refusal names the FIELD, never the stored value
# ---------------------------------------------------------------------------

_FORGED_CONTENTS = [
    {"strike": HOSTILE},
    {"population": HOSTILE},
    {"bars": {"last_close": HOSTILE}},
    {"greeks": {"delta": HOSTILE}},
    {"exchange_timezone": "Mars/Olympus"},
    {"title": HOSTILE},
    {"coverage": {HOSTILE: 1}},
]


@pytest.mark.parametrize("content", _FORGED_CONTENTS)
def test_a_refusal_never_quotes_the_stored_value(content: dict) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(content)
    message = str(excinfo.value)
    assert HOSTILE not in message
    assert "ACHETEZ" not in message
    assert "Mars/Olympus" not in message
    assert "\x1b" not in message and "\x07" not in message
    # The exception itself is what a log record may carry: only the path.
    assert excinfo.value.field is not None
    assert not re.search(r"[\x00-\x08\x0b-\x1f\x7f]", excinfo.value.field)
