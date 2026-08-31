"""Enveloppes de cotation dérivées : identité stable, dates justes, provenance héritée.

DEUX DÉFAUTS QUE CES TESTS EMPÊCHENT, et qui seraient tous deux invisibles :

1. **Un identifiant instable.** `ingest_envelope` est idempotent sur
   `event_id`. Si l'identifiant dérivé venait d'un uuid, chaque relance du
   remplissage historique dupliquerait TOUT l'historique — sans erreur, juste
   une base qui double de taille à chaque nuit.

2. **Un décalage de dates.** `daily_quotes_from_bars` écarte les clôtures
   inutilisables. Apparier naïvement les charges utiles aux barres d'origine
   par leur index décalerait chaque date d'un cran après le premier écart :
   toutes les cotations suivantes porteraient le jour d'une autre. Un cours
   juste, sur la mauvaise journée, ne se voit pas à l'œil.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from vertex_core.contracts import DataEnvelope, DelayStatus, EnvelopeQuality
from vertex_core.contracts.hashing import canonical_json_hash
from vertex_core.contracts.market_quote import UNCLASSIFIED_SECTOR_CODE
from vertex_edge_ibkr.normalize import (
    DAILY_QUOTE_SCHEMA_VERSION,
    daily_quote_envelopes,
    daily_quote_event_id,
)
from vertex_edge_ibkr.port import BarObservation, BarsPayload, ContractSpec

SPEC = ContractSpec(
    sec_type="STK", con_id=208813720, symbol="GOOG", exchange="SMART", currency="USD"
)
RECU = datetime(2026, 8, 31, 12, 0, 0, tzinfo=UTC)


def barre(jour: int, close: str | None) -> BarObservation:
    return BarObservation(
        time=datetime(2026, 8, jour, 20, 0, 0, tzinfo=UTC),
        close=Decimal(close) if close is not None else None,
    )


def charge(*barres: BarObservation) -> BarsPayload:
    return BarsPayload(
        con_id=SPEC.con_id, bar_size="1 day", what_to_show="TRADES", use_rth=True, bars=barres
    )


def enveloppe_source() -> DataEnvelope[object]:
    payload = {"con_id": SPEC.con_id, "bars": "…"}
    return DataEnvelope(
        event_id="ibkr-bars-source-1",
        schema_version="ibkr.bars/1",
        source="ibkr",
        instrument_id=str(SPEC.con_id),
        observed_at=RECU - timedelta(minutes=5),
        received_at=RECU,
        as_of=RECU,
        stale_after=RECU + timedelta(hours=24),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.LIVE,
        connection_epoch=7,
        rights="IBKR_MARKET_DATA_DISPLAY_ONLY",
        payload_hash=canonical_json_hash(payload),
        payload=payload,
    )


def derive(*barres: BarObservation):
    return daily_quote_envelopes(
        enveloppe_source(), charge(*barres), SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )


# -- identité stable -------------------------------------------------------


def test_l_identifiant_est_STABLE_entre_deux_executions() -> None:
    """Sinon chaque relance du remplissage dupliquerait tout l'historique."""
    premiers = [e.event_id for e in derive(barre(26, "199"), barre(27, "200"))[0]]
    seconds = [e.event_id for e in derive(barre(26, "199"), barre(27, "200"))[0]]
    assert premiers == seconds


def test_l_identifiant_distingue_les_jours() -> None:
    enveloppes, _ = derive(barre(26, "199"), barre(27, "200"))
    assert len({e.event_id for e in enveloppes}) == 2


def test_l_identifiant_porte_le_contrat_et_le_jour() -> None:
    assert daily_quote_event_id(208813720, "2026-08-28") == (
        "ibkr:daily-quote:208813720:2026-08-28"
    )


# -- dates justes ----------------------------------------------------------


def test_une_barre_ECARTEE_ne_decale_pas_les_dates_suivantes() -> None:
    """LE test de non-régression : un cours juste au mauvais jour ne se voit pas."""
    enveloppes, resultat = derive(
        barre(26, "199.00"),
        barre(27, None),  # écartée
        barre(28, "201.25"),
    )
    assert resultat.skipped_bars == 1
    jours = [e.payload["trading_day"] for e in enveloppes]
    assert jours == ["2026-08-26", "2026-08-28"], "les dates ont glissé"
    # Et chaque cours reste attaché à SON jour.
    closes = {e.payload["trading_day"]: e.payload["close"] for e in enveloppes}
    assert closes["2026-08-26"] == "199.00"
    assert closes["2026-08-28"] == "201.25"


def test_l_horodatage_est_celui_de_la_BARRE_et_non_de_la_requete() -> None:
    """Dater une clôture ancienne à l'instant de la requête ferait mentir la fraîcheur."""
    enveloppes, _ = derive(barre(26, "199"))
    assert enveloppes[0].observed_at == datetime(2026, 8, 26, 20, 0, 0, tzinfo=UTC)
    assert enveloppes[0].as_of == enveloppes[0].observed_at
    assert enveloppes[0].received_at == RECU


# -- provenance héritée ----------------------------------------------------


def test_la_provenance_est_heritee_sans_promotion() -> None:
    """Une cotation dérivée ne peut pas être plus fiable que sa barre d'origine."""
    source = enveloppe_source()
    enveloppes, _ = derive(barre(26, "199"))
    derivee = enveloppes[0]
    assert derivee.source == source.source
    assert derivee.rights == source.rights
    assert derivee.connection_epoch == source.connection_epoch
    assert derivee.quality_status == source.quality_status
    assert derivee.delay_status == source.delay_status


def test_le_schema_est_celui_que_le_worker_reconnait() -> None:
    """C'est ce préfixe qui met `quotes.ingested` en file et réveille la page."""
    from vertex_worker.markets import is_daily_quote_schema

    enveloppes, _ = derive(barre(26, "199"))
    assert enveloppes[0].schema_version == DAILY_QUOTE_SCHEMA_VERSION
    assert is_daily_quote_schema(enveloppes[0].schema_version)


def test_l_instrument_reste_identifie_par_son_con_id() -> None:
    enveloppes, _ = derive(barre(26, "199"))
    assert enveloppes[0].instrument_id == "208813720"


# -- refus -----------------------------------------------------------------


def test_un_refus_ne_produit_aucune_enveloppe() -> None:
    horaires = BarsPayload(
        con_id=SPEC.con_id,
        bar_size="1 hour",
        what_to_show="TRADES",
        use_rth=True,
        bars=(barre(26, "199"),),
    )
    enveloppes, resultat = daily_quote_envelopes(
        enveloppe_source(), horaires, SPEC, sector=UNCLASSIFIED_SECTOR_CODE
    )
    assert enveloppes == ()
    assert resultat.refused_reason == "BAR_SIZE_NOT_DAILY"


def test_aucune_barre_utilisable_ne_produit_aucune_enveloppe() -> None:
    enveloppes, resultat = derive(barre(26, None), barre(27, "0"))
    assert enveloppes == ()
    assert resultat.skipped_bars == 2
    assert resultat.refused_reason is None
