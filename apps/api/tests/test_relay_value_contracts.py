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


# ---------------------------------------------------------------------------
# P1-1 sur les deux relais laissés ouverts par la première vague
# ---------------------------------------------------------------------------
#
# `performance/{id}` et `portfolio_valuation/{id}` n'appelaient pas le garde de
# classe : le 4e audit les mesurait à 90 % et 100 % de champs chaîne relayés
# verbatim, alors que les sept autres relais étaient descendus à 0 %. Ils y
# sont désormais soumis. Ces tests portent sur les VRAIES fixtures de contenu,
# pas sur des mappings inventés pour l'occasion.

import copy  # noqa: E402

from vertex_api.performance import checked_performance_content  # noqa: E402

from test_performance_routes import PERFORMANCE_CONTENT  # noqa: E402


def _replace_leaf(content: dict, path: tuple, value: str) -> dict:
    """Copie du contenu avec UNE feuille remplacée, comme le fuzz de l'audit."""
    mutated = copy.deepcopy(content)
    node: object = mutated
    for key in path[:-1]:
        node = node[key]  # type: ignore[index]
    node[path[-1]] = value  # type: ignore[index]
    return mutated


def test_the_honest_performance_content_is_still_accepted() -> None:
    """Anti-vacuité : le contrat n'est pas un refus systématique."""
    assert checked_performance_content(PERFORMANCE_CONTENT) is not None


@pytest.mark.parametrize(
    "path",
    [
        ("population",),
        ("currency",),
        ("engine_version",),
        ("lot_method",),
        ("series", "points", 0, "gross_value"),
        ("series", "points", 0, "net_value"),
        ("series", "points", 0, "cash"),
        ("series", "points", 0, "trading_day"),
    ],
    ids=lambda p: ".".join(str(part) for part in p),
)
def test_a_hostile_value_is_refused_by_the_performance_relay(path: tuple) -> None:
    """Chacun de ces champs était servi VERBATIM avec les 5038 caractères."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_performance_content(_replace_leaf(PERFORMANCE_CONTENT, path, HOSTILE))
    # Le refus nomme le CHEMIN, jamais la valeur stockée.
    assert HOSTILE not in str(excinfo.value)
    assert "\x07" not in str(excinfo.value) and "\x1b" not in str(excinfo.value)


def test_a_performance_population_outside_the_closed_set_is_refused() -> None:
    """`population` sépare SYNTHETIC du réel : il ne peut pas être libre."""
    with pytest.raises(SnapshotContentError):
        checked_performance_content(
            _replace_leaf(PERFORMANCE_CONTENT, ("population",), "REAL_LIVE_IBKR")
        )


def test_a_performance_amount_that_is_not_a_decimal_is_refused() -> None:
    """Une valeur monétaire est un décimal, jamais du texte libre."""
    with pytest.raises(SnapshotContentError):
        checked_performance_content(
            _replace_leaf(
                PERFORMANCE_CONTENT, ("series", "points", 0, "gross_value"), "beaucoup"
            )
        )


def test_the_portfolio_valuation_relay_applies_the_same_contract() -> None:
    """Le relais de valorisation ne validait RIEN : 100 % passait verbatim."""
    honest = {
        "schema_version": "vertex.portfolio-valuation/1.0",
        "population": "SYNTHETIC_MARKS_REAL_LEDGER",
        "currency": "SYN",
        "positions": [{"ticker": "SYN-TECH-01", "market_value": "1234.50"}],
    }
    assert checked_relayed_content(honest) is not None
    for path in (("population",), ("currency",), ("positions", 0, "market_value")):
        with pytest.raises(SnapshotContentError):
            checked_relayed_content(_replace_leaf(honest, path, HOSTILE))


# ---------------------------------------------------------------------------
# P0-5 — `population` : ce que le relais garantit, et ce qu'il ne garantit pas
# ---------------------------------------------------------------------------
#
# 5e audit adversarial. Le vocabulaire « fermé » contenait REAL et DELAYED :
# sur le pipeline RÉEL (contenu sain étiqueté SYNTHETIC), forger
# `population = REAL` ou `DELAYED` rendait 200 avec l'étiquette relayée
# verbatim. Le docstring prétendait que la fermeture empêchait « du contenu
# synthétique de se présenter comme autre chose ». Elle ne l'empêchait pas.
#
# Le relais NE PEUT PAS vérifier qu'une donnée étiquetée REAL l'est : cette
# vérité appartient au worker. Ce qui EST vérifiable, et qui est fait ici :
#   1. aucune étiquette hors vocabulaire n'est publiée (déjà couvert plus haut) ;
#   2. un contenu ne peut pas se CONTREDIRE — revendiquer une observation tout
#      en portant un marqueur de provenance synthétique ;
#   3. deux champs dont un seul producteur existe sont fermés par CHEMIN.
#
# Les tests de RÉSIDU en fin de section fixent, chiffre à l'appui, ce qui reste
# ouvert. Ils échouent si quelqu'un croit avoir fermé plus qu'il n'a fermé.

from datetime import datetime, timezone  # noqa: E402

from vertex_core.synthetic import SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE  # noqa: E402
from vertex_persistence.repository.snapshots import CurrentSnapshot  # noqa: E402

from vertex_api.snapshot_views import (  # noqa: E402
    BARS_STATUS_LABELS,
    MARKETS_DISPLAY_UNIT,
    MARKETS_UNIT,
    OBSERVATION_CLAIM_LABELS,
    SYNTHETIC_MARKER_VALUES,
    build_analysis_response,
    build_markets_overview_response,
)

from test_analysis import INSTRUMENT, analysis_content  # noqa: E402
from test_markets_overview import markets_content  # noqa: E402


AS_OF_FOR_RELAY_TESTS = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)


def _snapshot(content: dict) -> CurrentSnapshot:
    """Snapshot SYNTHETIC minimal, tel que le lit un builder de relais."""
    return CurrentSnapshot(
        kind="synthetic",
        key="synthetic",
        version=1,
        content=content,
        content_hash="sha256:" + "e" * 64,
        as_of=AS_OF_FOR_RELAY_TESTS,
    )


def _analysis(content: dict):
    return build_analysis_response(_snapshot(content), instrument=INSTRUMENT)


def _markets(content: dict):
    return build_markets_overview_response(_snapshot(content))


# --- 1. le vocabulaire est bien fermé, mais il ne PROUVE rien --------------


def test_the_closed_vocabulary_is_a_form_check_not_a_provenance_proof() -> None:
    """Anti-sur-promesse : REAL et DELAYED SONT des membres légitimes.

    Ils doivent le rester — un worker qui observe vraiment le marché les
    publie. Le relais ne les refuse donc pas *en tant que tels* ; il refuse
    uniquement un contenu qui se contredit (test suivant).
    """
    for label in OBSERVATION_CLAIM_LABELS:
        assert label in POPULATION_LABELS
        assert checked_relayed_content({"population": label}) == {"population": label}


# --- 2. l'invariant réellement vérifiable : la contradiction interne --------


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
def test_a_synthetic_analysis_may_not_relabel_itself_as_an_observation(
    claim: str,
) -> None:
    """Le défaut reproduit par le 5e audit, sur le VRAI builder d'analyse.

    Le contenu sain est étiqueté SYNTHETIC et porte les marqueurs du
    générateur (`rights = SYNTHETIC`, `sources = synthetic-dev`,
    `synthetic = true`). Le réétiqueter REAL/DELAYED rendait 200.
    """
    healthy = analysis_content()
    assert healthy["population"] == "SYNTHETIC"
    assert _analysis(healthy).population == "SYNTHETIC"

    forged = _replace_leaf(healthy, ("population",), claim)
    with pytest.raises(SnapshotContentError) as excinfo:
        _analysis(forged)
    assert excinfo.value.field == "population"


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
def test_a_synthetic_markets_overview_may_not_relabel_itself(claim: str) -> None:
    healthy = markets_content()
    assert healthy["population"] == "SYNTHETIC"
    assert _markets(healthy).population == "SYNTHETIC"

    with pytest.raises(SnapshotContentError) as excinfo:
        _markets(_replace_leaf(healthy, ("population",), claim))
    assert excinfo.value.field == "population"


@pytest.mark.parametrize(
    "marker",
    [
        {"population": "REAL", "provenance": {"rights": ["SYNTHETIC"]}},
        {"population": "REAL", "provenance": {"sources": ["synthetic-dev"]}},
        {"population": "DELAYED", "items": [{"synthetic": True}]},
        {"population": "REAL", "clusters": [{"source": "synthetic-dev"}]},
    ],
)
def test_an_observation_claim_beside_a_synthetic_marker_is_refused(
    marker: dict,
) -> None:
    """La seule affirmation qu'un relais a le droit de faire : « ce contenu se
    contredit ». Il ne dit pas que la donnée est fausse, il dit qu'elle ne
    peut pas être ce qu'elle prétend être ET porter ce marqueur."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(marker)
    assert excinfo.value.field == "population"


def test_the_contradiction_refusal_never_quotes_the_stored_value() -> None:
    message = None
    try:
        checked_relayed_content(
            {"population": "REAL", "provenance": {"rights": ["SYNTHETIC"]}}
        )
    except SnapshotContentError as exc:
        message = str(exc)
    assert message is not None
    # Le message nomme un CHEMIN (provenance.rights[0]), jamais une valeur.
    assert "provenance.rights[0]" in message


def test_the_markers_are_read_from_the_authority_that_stamps_them() -> None:
    """Anti-dérive : si `vertex_core.synthetic` change ses marqueurs, ce test
    échoue AVANT que le garde ne devienne silencieusement plus faible."""
    assert SYNTHETIC_MARKER_VALUES == frozenset({SYNTHETIC_RIGHTS, SYNTHETIC_SOURCE})


def test_an_honest_synthetic_content_is_never_refused_by_the_invariant() -> None:
    """Anti-vacuité : le contenu sain du worker passe toujours."""
    assert _analysis(analysis_content()) is not None
    assert _markets(markets_content()) is not None
    # Une population qui ANNONCE le mélange reste servie telle quelle.
    assert checked_relayed_content(
        {
            "population": "SYNTHETIC_MARKS_REAL_LEDGER",
            "provenance": {"rights": ["SYNTHETIC"]},
        }
    )


# --- 3. deux champs fermés par CHEMIN, là où un seul producteur existe ------


@pytest.mark.parametrize("forged", ["REAL_TIME_IBKR", "LIVE", "DELAYED", "OK_ISH"])
def test_bars_status_may_not_carry_a_delay_claim(forged: str) -> None:
    """`analysis.bars.status` valait OK|ABSENT et relayait `LIVE` verbatim."""
    healthy = analysis_content()
    assert healthy["bars"]["status"] in BARS_STATUS_LABELS

    with pytest.raises(SnapshotContentError) as excinfo:
        _analysis(_replace_leaf(healthy, ("bars", "status"), forged))
    assert excinfo.value.field == "bars.status"


@pytest.mark.parametrize("healthy_status", sorted(BARS_STATUS_LABELS))
def test_both_declared_bars_statuses_are_still_relayed(healthy_status: str) -> None:
    content = _replace_leaf(analysis_content(), ("bars", "status"), healthy_status)
    assert _analysis(content).bars["status"] == healthy_status


@pytest.mark.parametrize("forged", ["USD", "EUR", "percent", "return_pct"])
def test_the_markets_unit_may_not_turn_a_ratio_into_money(forged: str) -> None:
    """`markets_overview.unit` valait `return_ratio` et relayait `USD`."""
    healthy = markets_content()
    assert healthy["unit"] == MARKETS_UNIT

    with pytest.raises(SnapshotContentError) as excinfo:
        _markets(_replace_leaf(healthy, ("unit",), forged))
    assert excinfo.value.field == "unit"


def test_the_markets_display_unit_is_closed_on_its_single_producer() -> None:
    healthy = markets_content()
    assert healthy["display_unit"] == MARKETS_DISPLAY_UNIT
    with pytest.raises(SnapshotContentError) as excinfo:
        _markets(_replace_leaf(healthy, ("display_unit",), "USD"))
    assert excinfo.value.field == "display_unit"


# --- 4. RÉSIDU : ce qui reste ouvert, et pourquoi ---------------------------
#
# Ces tests ne célèbrent rien : ils FIGENT une faiblesse connue pour qu'elle
# ne puisse ni grandir ni être oubliée, et pour qu'aucun rapport ne prétende
# qu'elle est fermée. Chacun nomme l'autorité manquante.


def test_residue_rights_is_not_closed_because_no_authority_owns_it() -> None:
    """`rights` est AFFICHÉ (AttentionQueue, ThesisSheet, EventAgenda).

    Aucun module de `vertex_core` ne possède un vocabulaire d'habilitation :
    l'edge publie `IBKR_MARKET_DATA_DISPLAY_ONLY` (argument de constructeur,
    donc configurable), le générateur `SYNTHETIC`, une sonde `DEMO`. Fermer
    l'ensemble ici INVENTERAIT une autorité que le relais n'a pas. Le contrat
    reste une contrainte de FORME, et une habilitation forgée passe encore.
    """
    forged = _replace_leaf(
        analysis_content(),
        ("evidence", "clusters", 0, "rights", 0),
        "IBKR_REALTIME_ENTITLED",
    )
    relayed = _analysis(forged)
    assert relayed.evidence["clusters"][0]["rights"][0] == "IBKR_REALTIME_ENTITLED"
    # La seule chose garantie : la FORME (jeton majuscule borné, sans échappement).
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"rights": "ibkr realtime"})
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({"rights": HOSTILE})


@pytest.mark.parametrize(
    "key,plausible",
    [
        ("ticker", "AAPL"),
        ("exchange", "NASDAQ"),
        ("sector", "TECHNOLOGY"),
        ("source", "ibkr-live"),
    ],
)
def test_residue_open_universes_stay_open(key: str, plausible: str) -> None:
    """Univers ouverts par construction : aucun registre de tickers, de places,
    de secteurs ni de sources n'existe dans ce dépôt. Fermer sur les valeurs
    SYNTHETIC du générateur reviendrait à interdire la production."""
    assert checked_relayed_content({key: plausible}) == {key: plausible}
    with pytest.raises(SnapshotContentError):
        checked_relayed_content({key: HOSTILE})


@pytest.mark.parametrize("plausible", ["CROSSED", "AVAILABLE", "ESTIMATED", "ACTIVE"])
def test_residue_the_generic_status_key_stays_open(plausible: str) -> None:
    """`status` est publié par au moins huit espaces de noms non reliés
    (OK/ABSENT, CROSSED/STALE/MISSING, AdviceStatus, GateStatus,
    CalculationStatus, SourceCapabilityStatus, ESTIMATED/CONFIRMED,
    ACTIVE/SNOOZED/ARCHIVED). Leur union laisserait de toute façon un statut
    de cotation là où un verdict est attendu, et casserait la rétrogradation
    fail-closed VOULUE d'un statut de capacité inconnu en ERROR /
    INVALID_STATUS. Fermé par CHEMIN là où une autorité existe
    (`bars.status`, `scenarios.status`, `advice.status`), ouvert ailleurs."""
    assert checked_relayed_content({"status": plausible}) == {"status": plausible}


def test_residue_a_fully_scrubbed_payload_still_passes() -> None:
    """LIMITE HAUTE de l'invariant de contradiction, écrite noir sur blanc.

    Un producteur défaillant — ou une ligne falsifiée — qui étiquette REAL
    ET efface TOUS les marqueurs synthétiques n'est plus détectable par un
    relais. Il faudrait pour cela une provenance signée par le worker, qui
    n'existe pas. Ce test échouera le jour où elle existera : c'est voulu.
    """
    scrubbed = {
        "population": "REAL",
        "provenance": {"rights": ["IBKR_MARKET_DATA_DISPLAY_ONLY"], "sources": ["ibkr"]},
        "items": [{"synthetic": False}],
    }
    assert checked_relayed_content(scrubbed) == scrubbed


# ---------------------------------------------------------------------------
# P0-6 — la nature n'est pas UNE clé : c'est une CLASSE de champs
# ---------------------------------------------------------------------------
#
# 6e audit adversarial. Le correctif P0-5 fermait le vocabulaire et refusait
# la contradiction interne pour la clé LITTÉRALE `population`, au SOMMET du
# contenu seulement. Trois trous en découlaient :
#
#   1. `mark_population` — la nature des marks de valorisation
#      (`vertex_worker.portfolio.MARK_POPULATION_SYNTHETIC`, relayée par
#      `vertex_api.portfolio.build_portfolio_response`) n'était NI fermée NI
#      croisée : `mark_population = "REAL"` à côté de `rights = SYNTHETIC`
#      passait, et « DONNEES REELLES 100% FIABLES » aussi. La chaîne va
#      jusqu'à l'écran (`PortfolioPage` → bandeau « DONNÉES RÉELLES »).
#   2. une `population` IMBRIQUÉE (dossier d'opportunité, bloc `bars`) était
#      bien soumise au vocabulaire — `_leaf_key` ignore la profondeur — mais
#      n'était NI une revendication NI un marqueur pour la vérification
#      croisée. Une tête REAL au-dessus de dossiers SYNTHETIC passait.
#   3. le vocabulaire des marqueurs synthétiques ne connaissait que
#      {SYNTHETIC, synthetic-dev} sous {rights, sources, source}. Le
#      `schema_version` du générateur, son préfixe de titre, ses identifiants
#      et ses clés `generator`/`source_system` passaient inaperçus.
#
# RÈGLE ÉCRITE ICI pour deux natures qui coexistent et se contredisent :
# la nature d'un nœud GOUVERNE SON SOUS-ARBRE, et seule la SUR-REVENDICATION
# est refusée. Une tête qui revendique une observation au-dessus d'un
# marqueur synthétique est REFUSÉE ; une tête prudente (SYNTHETIC) au-dessus
# d'un dossier REAL est SERVIE, parce que c'est exactement la dégradation
# vers le plus prudent que le worker applique déjà
# (`vertex_worker.opportunities` : « a single synthetic dossier makes the
# whole snapshot synthetic »). Refuser cette seconde forme casserait un état
# produit légitime sans rien protéger : personne n'y lit « réel ».

from collections.abc import Mapping  # noqa: E402

from vertex_core.synthetic import (  # noqa: E402
    SYNTHETIC_ADJUSTMENT_BASIS,
    SYNTHETIC_FOCUS_TICKERS,
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_SCHEMA_QUOTE,
    SYNTHETIC_SECTOR_LABELS_FR,
    SYNTHETIC_SECTORS,
    SYNTHETIC_TITLE_PREFIX,
)

from vertex_api.snapshot_views import (  # noqa: E402
    GENERATED_NATURE_LABELS,
    NATURE_CENSUS_KEYS,
    NATURE_LEAF_KEYS,
    NATURE_PARENT_KEYS,
    is_synthetic_marker,
)


# --- 1. `mark_population` : le vecteur P0 exact du 6e audit -----------------


@pytest.mark.parametrize(
    "forged",
    [
        "IBKR_REALTIME_ENTITLED",
        "LIVE",
        "PRODUCTION",
        "real",
        "DONNEES REELLES 100% FIABLES",
    ],
)
def test_a_forged_mark_population_is_outside_the_closed_vocabulary(
    forged: str,
) -> None:
    """Le relais de valorisation acceptait n'importe quelle étiquette."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"mark_population": forged})
    assert excinfo.value.field == "mark_population"
    assert forged not in str(excinfo.value)


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
def test_a_mark_population_claim_beside_a_synthetic_marker_is_refused(
    claim: str,
) -> None:
    """`mark_population = REAL` + `rights = SYNTHETIC` rendait 200."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {
                "mark_population": claim,
                "provenance": {"rights": [SYNTHETIC_RIGHTS]},
            }
        )
    assert excinfo.value.field == "mark_population"
    assert "provenance.rights[0]" in str(excinfo.value)


def test_the_honest_portfolio_valuation_nature_is_still_relayed() -> None:
    """Anti-vacuité : la seule nature que le worker publie reste servie."""
    honest = {
        "schema_version": "vertex.portfolio-valuation/1.0",
        "mark_population": "SYNTHETIC",
    }
    assert checked_relayed_content(honest) == honest


# --- 2. la nature IMBRIQUÉE, à n'importe quelle profondeur ------------------


@pytest.mark.parametrize(
    "content",
    [
        {"population": "REAL", "dossiers": [{"population": "SYNTHETIC"}]},
        {"population": "REAL", "bars": {"population": "SYNTHETIC"}},
        {"population": "DELAYED", "a": {"b": {"c": {"population": "SYNTHETIC"}}}},
        {
            "population": "REAL",
            "population_components": {"marks": "SYNTHETIC", "ledger": "USER_DECLARED"},
        },
        {"population": "REAL", "populations": {"theses": "SYNTHETIC"}},
        {"mark_population": "REAL", "marks": {"population": "DEMO"}},
    ],
)
def test_a_nested_generated_nature_refuses_a_head_that_claims_an_observation(
    content: dict,
) -> None:
    """Une tête REAL au-dessus d'un sous-arbre synthétique se contredit."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(content)
    assert excinfo.value.field in NATURE_LEAF_KEYS


def test_a_nested_claim_is_refused_by_a_marker_inside_ITS_OWN_subtree() -> None:
    """La revendication imbriquée est gouvernée par son propre sous-arbre."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {
                "population": "SYNTHETIC",
                "dossiers": [
                    {"population": "REAL", "provenance": {"sources": [SYNTHETIC_SOURCE]}}
                ],
            }
        )
    assert excinfo.value.field == "dossiers[0].population"
    assert "dossiers[0].provenance.sources[0]" in str(excinfo.value)


def test_a_prudent_head_above_a_real_dossier_is_still_served() -> None:
    """RÈGLE : la dégradation vers le plus prudent n'est PAS une contradiction.

    `vertex_worker.opportunities` étiquette délibérément SYNTHETIC un
    snapshot dont un seul dossier est synthétique, et publie le mélange dans
    `limitations` + `population_counts`. Refuser cet état casserait le
    produit sans protéger personne : aucun lecteur n'y voit « réel ».
    """
    mixed = {
        "population": "SYNTHETIC",
        "dossiers": [{"population": "REAL"}, {"population": "SYNTHETIC"}],
        "coverage": {"population_counts": {"REAL": 1, "SYNTHETIC": 1}},
    }
    assert checked_relayed_content(mixed) == mixed


@pytest.mark.parametrize("forged", ["IBKR_REALTIME", "LIVE", "reel"])
def test_a_nature_under_a_grouping_key_obeys_the_closed_vocabulary(
    forged: str,
) -> None:
    """`population_components` / `populations` portent des natures dont les
    clés feuilles sont quelconques (`marks`, `ledger`) : le vocabulaire s'y
    applique par CHEMIN, pas par nom de feuille."""
    for parent in sorted(NATURE_PARENT_KEYS):
        with pytest.raises(SnapshotContentError) as excinfo:
            checked_relayed_content({parent: {"marks": forged}})
        assert excinfo.value.field == f"{parent}.marks"
        assert forged not in str(excinfo.value)


def test_a_population_census_key_obeys_the_closed_vocabulary() -> None:
    """`coverage.population_counts` est un recensement DE NATURES : ses CLÉS
    appartiennent au même vocabulaire fermé que la nature elle-même."""
    for census in sorted(NATURE_CENSUS_KEYS):
        with pytest.raises(SnapshotContentError) as excinfo:
            checked_relayed_content({census: {"IBKR_LIVE": 2}})
        assert excinfo.value.field == census
        assert "IBKR_LIVE" not in str(excinfo.value)


# --- 3. le vocabulaire ÉLARGI des marqueurs synthétiques --------------------


@pytest.mark.parametrize(
    "marker_content",
    [
        {"schema_version": SYNTHETIC_SCHEMA_QUOTE},
        {"generator": SYNTHETIC_SOURCE},
        {"source_system": SYNTHETIC_SOURCE},
        {"adjustment_basis": SYNTHETIC_ADJUSTMENT_BASIS},
        {"title": SYNTHETIC_TITLE_PREFIX + "Fictional company SYN1"},
        {"ticker": "SYN1"},
        {"ticker": SYNTHETIC_FOCUS_TICKERS[0]},
        {"sector": SYNTHETIC_SECTORS[0]},
        {"currency": SYNTHETIC_MARKET_CURRENCY},
        {"bars": {"population": "SYNTHETIC"}},
    ],
)
def test_the_widened_synthetic_markers_contradict_an_observation_claim(
    marker_content: dict,
) -> None:
    """Aucun de ces marqueurs n'était vu : tous étaient servis sous REAL."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"population": "REAL", **marker_content})
    assert excinfo.value.field == "population"


def test_the_widened_markers_alone_are_never_a_refusal() -> None:
    """Anti-vacuité : un contenu synthétique honnête reste servi entier."""
    honest = {
        "population": "SYNTHETIC",
        "schema_version": SYNTHETIC_SCHEMA_QUOTE,
        "ticker": SYNTHETIC_FOCUS_TICKERS[0],
        "currency": SYNTHETIC_MARKET_CURRENCY,
        "title": SYNTHETIC_TITLE_PREFIX + "Fictional company SYN1",
        "provenance": {"rights": [SYNTHETIC_RIGHTS], "sources": [SYNTHETIC_SOURCE]},
    }
    assert checked_relayed_content(honest) == honest


def test_a_real_ticker_that_merely_starts_with_syn_is_not_a_marker() -> None:
    """Anti-faux-positif : SYNA (Synaptics) n'est pas un identifiant du
    générateur. La détection est une FORME EXACTE, jamais un préfixe `SYN`."""
    real = {"population": "REAL", "ticker": "SYNA", "sector": "SYNDICATED"}
    assert checked_relayed_content(real) == real
    assert not is_synthetic_marker("SYNA", "ticker")
    assert not is_synthetic_marker("SYNDICATED", "sector")


# --- 4. anti-dérive contre l'autorité qui estampille -------------------------


def test_every_synthetic_identifier_of_the_authority_is_detected() -> None:
    """Anti-dérive EXHAUSTIVE : chaque constante chaîne exportée par
    `vertex_core.synthetic` (paquet ET sous-module `options`) est soit
    détectée comme marqueur, soit explicitement justifiée ci-dessous.
    Ajouter une constante au générateur sans l'une des deux CASSE ce test.

    C'est ce test — et non un import — qui rattache le relais à l'autorité :
    `snapshot_views` ne doit PAS charger un GÉNÉRATEUR de données dans le
    processus API (décision déjà inscrite dans son docstring). La dérive est
    donc épinglée depuis les tests, où l'import est sans conséquence runtime.
    """
    import vertex_core.synthetic as authority
    from vertex_core.synthetic import options as authority_options

    # Constantes qui ne sont PAS des marqueurs, et pourquoi.
    not_markers = {
        "Europe/Zurich",  # SYNTHETIC_EXCHANGE_TIMEZONE : vraie zone IANA
        "DIVIDEND", "EARNINGS", "MACRO", "OPTION_EXPIRATION",  # catégories réelles
        "GLOBAL", "TICKER",  # portées réelles
        "CONFIRMED", "ESTIMATED",  # statuts réels
        "EUROPEAN", "CASH",  # style/règlement canoniques, pas des identifiants
        "OI_DELAYED",  # statut d'open interest canonique
    }

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, (tuple, list)):
            for item in value:
                yield from strings(item)
        elif isinstance(value, Mapping):
            for key, item in value.items():
                yield from strings(key)
                yield from strings(item)

    checked = 0
    exported = [(authority, name) for name in authority.__all__]
    exported += [(authority_options, name) for name in authority_options.__all__]
    for module, name in exported:
        value = getattr(module, name)
        if callable(value):
            continue
        for text in strings(value):
            if text in not_markers:
                continue
            if text in SYNTHETIC_SECTOR_LABELS_FR.values():
                continue  # libellés FR d'affichage, prose et non identifiant
            checked += 1
            assert is_synthetic_marker(text, "ticker"), (
                f"{name}: constante du générateur non détectée comme marqueur"
            )
    assert checked >= 40


def test_the_generated_nature_labels_are_all_declared_natures() -> None:
    """Les natures qui VALENT marqueur restent membres du vocabulaire fermé
    et disjointes des deux revendications d'observation."""
    assert GENERATED_NATURE_LABELS <= POPULATION_LABELS
    assert not (GENERATED_NATURE_LABELS & OBSERVATION_CLAIM_LABELS)


# --- 5. le refus ne fuit jamais la valeur stockée ---------------------------


@pytest.mark.parametrize(
    "content",
    [
        {"mark_population": "DONNEES REELLES 100% FIABLES"},
        {"mark_population": "REAL", "provenance": {"rights": [SYNTHETIC_RIGHTS]}},
        {"population": "REAL", "dossiers": [{"population": "SYNTHETIC"}]},
        {"population_components": {"marks": HOSTILE}},
        {"population_counts": {"IBKR_LIVE": 1}},
    ],
)
def test_a_nature_refusal_names_a_path_and_never_a_value(content: dict) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(content)
    message = str(excinfo.value)
    assert HOSTILE not in message
    assert "\x07" not in message and "\x1b" not in message
    assert "DONNEES REELLES" not in message
    assert "IBKR_LIVE" not in message


# ===========================================================================
# 7e AUDIT — P0-2 : le RECENSEMENT était exclu du croisement claim/marqueur
# ===========================================================================
#
# VECTEUR REPRODUIT. `{"population": "REAL", "coverage":
# {"population_counts": {"SYNTHETIC": 24}}}` était SERVI `state = "ok"`, et
# `population = "REAL"` partait vers `SyntheticBanner` qui affichait
# « DONNÉES RÉELLES » en ton NEUTRE. Le contrôle
# `{"population": "REAL", "coverage": {"rights": "SYNTHETIC"}}` était, lui,
# déjà REFUSÉ : la seule différence entre les deux est que le marqueur est
# une CLÉ de recensement au lieu d'une valeur.
#
# POURQUOI L'EXCLUSION ÉTAIT FAUSSE. Le motif écrit — « un recensement DÉCRIT
# un mélange, il n'en revendique pas un » — est vrai du recensement pris
# SEUL. Il ne dit rien de la TÊTE placée au-dessus. Une tête qui revendique
# une observation au-dessus d'un recensement qui ne compte AUCUN membre
# observé revendique plus que ce que son propre recensement soutient : c'est
# exactement la SUR-REVENDICATION que la règle asymétrique refuse déjà
# ailleurs. La direction inverse — tête prudente au-dessus d'un recensement
# mixte — reste servie, et les tests d'anti-vacuité ci-dessous la tiennent.


CENSUS = "population_counts"


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
@pytest.mark.parametrize(
    "counts",
    [
        {"SYNTHETIC": 24},
        {"SIMULATED": 3},
        {"DEMO": 1},
        {"REAL": 3, "SYNTHETIC": 1},
        {"DELAYED": 2, "DEMO": 7},
    ],
)
def test_a_census_counting_a_generated_member_refuses_an_observation_claim(
    claim: str, counts: dict
) -> None:
    """Un membre GÉNÉRÉ compté sous une tête qui revendique une observation.

    `{"REAL": 3, "SYNTHETIC": 1}` est inclus délibérément : le producteur
    (`vertex_worker.opportunities`) dégrade tout le snapshot à SYNTHETIC dès
    UN dossier synthétique, donc une tête REAL au-dessus d'un tel mélange
    n'est aucun état produit — et c'est la direction que
    `financial-safety.md` interdit (réel et généré jamais confondus).
    """
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {"population": claim, "coverage": {CENSUS: counts}}
        )
    assert excinfo.value.field == "population"
    assert f"coverage.{CENSUS}." in str(excinfo.value)


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
@pytest.mark.parametrize(
    "counts",
    [
        {"EMPTY": 20},
        {"THEORETICAL": 4},
        {"USER_DECLARED": 2},
        {"EMPTY": 20, "THEORETICAL": 1},
    ],
)
def test_a_census_counting_zero_observed_member_refuses_an_observation_claim(
    claim: str, counts: dict
) -> None:
    """Aucun de ces membres n'est un marqueur synthétique — et pourtant la
    tête revendique une observation qu'AUCUN membre compté ne soutient."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {"population": claim, "coverage": {CENSUS: counts}}
        )
    assert excinfo.value.field == "population"
    assert f"coverage.{CENSUS}" in str(excinfo.value)


def test_a_nested_claim_is_refused_by_the_census_of_ITS_OWN_subtree() -> None:
    """Le recensement gouverne comme un marqueur : par SOUS-ARBRE."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(
            {
                "population": "SYNTHETIC",
                "dossiers": [
                    {"population": "REAL", "coverage": {CENSUS: {"SYNTHETIC": 2}}}
                ],
            }
        )
    assert excinfo.value.field == "dossiers[0].population"


# --- ANTI-VACUITÉ : la direction PRUDENTE reste servie ----------------------


def test_a_prudent_head_above_a_mixed_census_is_still_served() -> None:
    """RÈGLE ASYMÉTRIQUE, direction légitime : `vertex_worker.opportunities`
    publie EXACTEMENT ceci et doit continuer à être servi."""
    mixed = {
        "population": "SYNTHETIC",
        "limitations": ["mixed population"],
        "coverage": {CENSUS: {"REAL": 1, "SYNTHETIC": 1}},
    }
    assert checked_relayed_content(mixed) == mixed


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
@pytest.mark.parametrize(
    "counts",
    [
        {"REAL": 3},
        {"DELAYED": 2},
        {"REAL": 2, "EMPTY": 20},
        {"REAL": 1, "THEORETICAL": 5},
        {"REAL": 2, "SYNTHETIC": 0},
    ],
)
def test_a_census_that_supports_its_claim_is_served(
    claim: str, counts: dict
) -> None:
    """Anti-vacuité de la direction refusée : un recensement qui compte au
    moins un membre observé, et aucun membre généré, laisse passer la tête.

    `{"REAL": 2, "SYNTHETIC": 0}` est inclus exprès : un compteur à ZÉRO
    n'est PAS un membre. Sans cette ligne la règle refuserait sur la simple
    présence d'une clé, ce qui serait un contrôle de vocabulaire déguisé.
    """
    served = {"population": claim, "coverage": {CENSUS: counts}}
    assert checked_relayed_content(served) == served


@pytest.mark.parametrize("claim", sorted(OBSERVATION_CLAIM_LABELS))
def test_an_absent_or_empty_census_is_absence_not_contradiction(
    claim: str,
) -> None:
    """Un recensement VIDE ne porte aucune information : il ne contredit
    rien. Le refuser reviendrait à refuser aussi son ABSENCE, donc tout
    producteur qui n'en publie pas (`analysis`, `markets`, `calendar`)."""
    for content in (
        {"population": claim},
        {"population": claim, "coverage": {CENSUS: {}}},
    ):
        assert checked_relayed_content(content) == content


# --- les VALEURS du recensement : un compte, jamais de la prose -------------


@pytest.mark.parametrize(
    "forged",
    [
        "beaucoup",
        "24",
        HOSTILE,
        True,
        False,
        -4,
        1.5,
        None,
        [24],
        {"n": 24},
    ],
)
def test_a_census_count_must_be_a_non_negative_integer(forged: Any) -> None:
    """La règle ci-dessus LIT le compte : une valeur illisible la rendrait
    silencieusement inapplicable (`{"SYNTHETIC": "24"}` s'échapperait)."""
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content({"coverage": {CENSUS: {"SYNTHETIC": forged}}})
    assert excinfo.value.field == f"coverage.{CENSUS}.SYNTHETIC"


def test_a_census_count_of_zero_and_of_a_large_universe_are_both_relayed() -> None:
    """Anti-vacuité du contrôle de valeur : les comptes honnêtes passent."""
    honest = {"coverage": {CENSUS: {"SYNTHETIC": 0, "REAL": 10_000}}}
    assert checked_relayed_content(honest) == honest


# --- le refus ne fuit jamais la valeur stockée ------------------------------


@pytest.mark.parametrize(
    "content",
    [
        {"population": "REAL", "coverage": {CENSUS: {"SYNTHETIC": 24}}},
        {"population": "DELAYED", "coverage": {CENSUS: {"EMPTY": 20}}},
        {"coverage": {CENSUS: {"SYNTHETIC": HOSTILE}}},
        {"coverage": {CENSUS: {"IBKR_LIVE": 1}}},
    ],
)
def test_a_census_refusal_names_a_path_and_never_a_value(content: dict) -> None:
    with pytest.raises(SnapshotContentError) as excinfo:
        checked_relayed_content(content)
    message = str(excinfo.value)
    assert HOSTILE not in message
    assert "\x07" not in message and "\x1b" not in message
    assert "IBKR_LIVE" not in message
    assert "ACHETEZ" not in message
