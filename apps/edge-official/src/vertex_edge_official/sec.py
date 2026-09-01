"""SEC EDGAR point-in-time normalisation.

The raw SEC envelopes remain immutable observations.  This module derives one
new envelope per filing version and per XBRL fact.  Availability comes from
``acceptanceDateTime`` when submissions provides it; otherwise the conservative
next-UTC-day boundary after ``filed`` is used, never the start of the filing day.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from vertex_core.contracts import (
    DataEnvelope,
    DelayStatus,
    EnvelopeQuality,
    Filing,
    FundamentalFact,
    canonical_json_hash,
)

__all__ = [
    "SEC_FACT_SCHEMA",
    "SEC_FILING_SCHEMA",
    "SecNormalizationError",
    "normalize_sec_edgar",
]

SEC_FILING_SCHEMA = "sec.edgar.filing/1"
SEC_FACT_SCHEMA = "sec.edgar.fundamental-fact/1"
SEC_SOURCE = "sec_edgar"
SEC_RIGHTS = "R1_PUBLIC_FACT_SEC_EDGAR_POLICY_2026_08_28"
_RAW_SUBMISSIONS_SCHEMA = "sec.edgar.submissions/1"
_RAW_FACTS_SCHEMA = "sec.edgar.company-facts/1"
_ACCESSION_RE = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
_DOCUMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")


class SecNormalizationError(ValueError):
    """The provider payload cannot be mapped without inventing information."""


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SecNormalizationError(f"{field}: object required")
    return value


def _text(value: Any, field: str, *, optional: bool = False) -> str | None:
    if optional and (value is None or (isinstance(value, str) and not value.strip())):
        return None
    if not isinstance(value, str) or not value.strip():
        raise SecNormalizationError(f"{field}: non-empty string required")
    return value.strip()


def _day(value: Any, field: str, *, optional: bool = False) -> date | None:
    raw = _text(value, field, optional=optional)
    if raw is None:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise SecNormalizationError(f"{field}: ISO date required") from None


def _instant(value: Any, field: str, *, optional: bool = False) -> datetime | None:
    raw = _text(value, field, optional=optional)
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise SecNormalizationError(f"{field}: ISO instant required") from None
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise SecNormalizationError(f"{field}: timezone-aware instant required")
    return parsed.astimezone(UTC)


def _cik(value: Any, field: str) -> str:
    raw = str(value).strip()
    if not raw.isdigit() or not 1 <= len(raw) <= 10:
        raise SecNormalizationError(f"{field}: one to ten digits required")
    return raw.zfill(10)


def _accession(value: Any, field: str) -> str:
    raw = cast(str, _text(value, field))
    if _ACCESSION_RE.fullmatch(raw) is None:
        raise SecNormalizationError(f"{field}: SEC accession required")
    return raw


def _bool_flag(value: Any, field: str) -> bool:
    if value in (0, False):
        return False
    if value in (1, True):
        return True
    raise SecNormalizationError(f"{field}: 0/1 boolean required")


def _response(envelope: DataEnvelope[dict[str, Any]], schema: str) -> Mapping[str, Any]:
    if not isinstance(envelope, DataEnvelope):
        raise TypeError(f"envelope: expected DataEnvelope, got {type(envelope).__name__}")
    if envelope.source != SEC_SOURCE or envelope.schema_version != schema:
        raise SecNormalizationError(f"expected {SEC_SOURCE} {schema}")
    payload = _mapping(envelope.payload, "payload")
    return _mapping(payload.get("response"), "payload.response")


def _parallel_recent(response: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    filings = _mapping(response.get("filings"), "submissions.filings")
    recent = _mapping(filings.get("recent"), "submissions.filings.recent")
    names = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "acceptanceDateTime",
        "form",
        "primaryDocument",
        "primaryDocDescription",
        "isXBRL",
        "isInlineXBRL",
    )
    columns: dict[str, Sequence[Any]] = {}
    for name in names:
        value = recent.get(name)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise SecNormalizationError(f"submissions.{name}: array required")
        columns[name] = value
    sizes = {len(value) for value in columns.values()}
    if len(sizes) != 1:
        raise SecNormalizationError("submissions recent parallel arrays have different lengths")
    count = sizes.pop()
    return tuple({name: columns[name][index] for name in names} for index in range(count))


def _availability(filed: date, accepted: datetime | None) -> datetime:
    if accepted is not None:
        return accepted
    return datetime.combine(filed + timedelta(days=1), time.min, tzinfo=UTC)


def _filings(
    response: Mapping[str, Any],
    *,
    cik: str,
    entity_name: str,
    source_observation_ids: tuple[str, ...],
    source_payload_hashes: tuple[str, ...],
) -> tuple[Filing, ...]:
    parsed: list[Filing] = []
    for index, raw in enumerate(_parallel_recent(response)):
        accession = _accession(raw["accessionNumber"], f"filings[{index}].accession")
        filed = cast(date, _day(raw["filingDate"], f"filings[{index}].filingDate"))
        report = _day(raw["reportDate"], f"filings[{index}].reportDate", optional=True)
        accepted = _instant(
            raw["acceptanceDateTime"],
            f"filings[{index}].acceptanceDateTime",
            optional=True,
        )
        form = cast(str, _text(raw["form"], f"filings[{index}].form"))
        document = cast(
            str,
            _text(raw["primaryDocument"], f"filings[{index}].primaryDocument"),
        )
        if _DOCUMENT_RE.fullmatch(document) is None:
            raise SecNormalizationError(f"filings[{index}].primaryDocument: safe basename required")
        accession_path = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/{document}"
        parsed.append(
            Filing(
                authority="SEC_EDGAR",
                source_observation_ids=source_observation_ids,
                source_payload_hashes=source_payload_hashes,
                cik=cik,
                entity_name=entity_name,
                accession=accession,
                form=form,
                report_date=report,
                filed_date=filed,
                accepted_at=accepted,
                available_at=_availability(filed, accepted),
                primary_document=document,
                primary_document_url=url,
                primary_document_description=_text(
                    raw["primaryDocDescription"],
                    f"filings[{index}].primaryDocDescription",
                    optional=True,
                ),
                is_xbrl=_bool_flag(raw["isXBRL"], f"filings[{index}].isXBRL"),
                is_inline_xbrl=_bool_flag(
                    raw["isInlineXBRL"], f"filings[{index}].isInlineXBRL"
                ),
                is_amendment=form.endswith("/A"),
                supersedes_accession=None,
            )
        )
    parsed.sort(key=lambda item: (item.available_at, item.accession))
    latest_original: dict[tuple[str, date | None], str] = {}
    linked: list[Filing] = []
    for filing in parsed:
        base_form = filing.form.removesuffix("/A")
        key = (base_form, filing.report_date)
        supersedes = latest_original.get(key) if filing.is_amendment else None
        linked.append(filing.model_copy(update={"supersedes_accession": supersedes}))
        latest_original[key] = filing.accession
    return tuple(linked)


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise SecNormalizationError(f"{field}: finite JSON number required")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation:
        raise SecNormalizationError(f"{field}: finite decimal required") from None
    if not parsed.is_finite():
        raise SecNormalizationError(f"{field}: finite decimal required")
    return parsed


def _facts(
    response: Mapping[str, Any],
    *,
    cik: str,
    entity_name: str,
    filings_by_accession: Mapping[str, Filing],
    source_observation_ids: tuple[str, ...],
    source_payload_hashes: tuple[str, ...],
) -> tuple[FundamentalFact, ...]:
    facts_root = _mapping(response.get("facts"), "companyfacts.facts")
    parsed: list[FundamentalFact] = []
    for taxonomy in sorted(facts_root):
        concepts = _mapping(facts_root[taxonomy], f"facts.{taxonomy}")
        for concept in sorted(concepts):
            definition = _mapping(concepts[concept], f"facts.{taxonomy}.{concept}")
            label = _text(definition.get("label"), f"facts.{taxonomy}.{concept}.label")
            description = _text(
                definition.get("description"),
                f"facts.{taxonomy}.{concept}.description",
                optional=True,
            )
            units = _mapping(definition.get("units"), f"facts.{taxonomy}.{concept}.units")
            for unit in sorted(units):
                entries = units[unit]
                if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
                    raise SecNormalizationError(
                        f"facts.{taxonomy}.{concept}.{unit}: array required"
                    )
                for index, raw_value in enumerate(entries):
                    raw = _mapping(raw_value, f"facts.{taxonomy}.{concept}.{unit}[{index}]")
                    accession = _accession(raw.get("accn"), "fact.accn")
                    filed = cast(date, _day(raw.get("filed"), "fact.filed"))
                    period_end = cast(date, _day(raw.get("end"), "fact.end"))
                    filing = filings_by_accession.get(accession)
                    accepted = filing.accepted_at if filing is not None else None
                    form = cast(str, _text(raw.get("form"), "fact.form"))
                    fiscal_period = _text(raw.get("fp"), "fact.fp", optional=True)
                    frame = _text(raw.get("frame"), "fact.frame", optional=True)
                    fiscal_year_raw = raw.get("fy")
                    fiscal_year = None
                    if fiscal_year_raw is not None:
                        if isinstance(fiscal_year_raw, bool) or not isinstance(
                            fiscal_year_raw, int
                        ):
                            raise SecNormalizationError("fact.fy: integer required")
                        fiscal_year = fiscal_year_raw
                    parsed.append(
                        FundamentalFact(
                            authority="SEC_EDGAR",
                            source_observation_ids=source_observation_ids,
                            source_payload_hashes=source_payload_hashes,
                            cik=cik,
                            entity_name=entity_name,
                            taxonomy=taxonomy,
                            concept=concept,
                            label=cast(str, label),
                            description=description,
                            value=_decimal(raw.get("val"), "fact.val"),
                            unit=unit,
                            period_start=_day(raw.get("start"), "fact.start", optional=True),
                            period_end=period_end,
                            filed_date=filed,
                            available_at=_availability(filed, accepted),
                            accession=accession,
                            form=form,
                            fiscal_year=fiscal_year,
                            fiscal_period=fiscal_period,
                            frame=frame,
                            dimensions={},
                            is_amendment=form.endswith("/A"),
                        )
                    )
    parsed.sort(
        key=lambda item: (
            item.available_at,
            item.taxonomy,
            item.concept,
            item.unit,
            item.period_end,
            item.accession,
        )
    )
    return tuple(parsed)


def _derived_envelope(
    payload_model: Filing | FundamentalFact,
    *,
    schema: str,
    native_identity: str,
    instrument_ref: str,
    received_at: datetime,
) -> DataEnvelope[dict[str, Any]]:
    payload = payload_model.model_dump(mode="json")
    payload_hash = canonical_json_hash(payload)
    identity_hash = canonical_json_hash(native_identity).removeprefix("sha256:")[:24]
    # The provider may reorder unrelated arrays without changing this filing
    # or fact. Provenance hashes still travel in the payload, but idempotence
    # is based on the normalized business value, not on irrelevant raw order.
    business_payload = dict(payload)
    business_payload.pop("source_observation_ids", None)
    business_payload.pop("source_payload_hashes", None)
    event_digest = canonical_json_hash(business_payload).removeprefix("sha256:")[:24]
    return DataEnvelope[dict[str, Any]](
        event_id=f"sec_edgar:{identity_hash}:{event_digest}",
        schema_version=schema,
        source=SEC_SOURCE,
        source_event_id=native_identity,
        entitlement_id=None,
        instrument_id=instrument_ref,
        observed_at=(
            datetime.combine(payload_model.period_end, time.min, tzinfo=UTC)
            if isinstance(payload_model, FundamentalFact)
            else (
                datetime.combine(payload_model.report_date, time.min, tzinfo=UTC)
                if payload_model.report_date is not None
                else None
            )
        ),
        published_at=payload_model.available_at,
        received_at=received_at,
        as_of=payload_model.available_at,
        stale_after=payload_model.available_at + timedelta(days=7),
        quality_status=EnvelopeQuality.VALID,
        delay_status=DelayStatus.UNKNOWN,
        connection_epoch=None,
        rights=SEC_RIGHTS,
        payload_hash=payload_hash,
        payload=payload,
    )


def normalize_sec_edgar(
    submissions: DataEnvelope[dict[str, Any]],
    company_facts: DataEnvelope[dict[str, Any]],
    *,
    instrument_ref: str,
) -> tuple[DataEnvelope[dict[str, Any]], ...]:
    """Normalize one explicitly mapped SEC issuer without look-ahead."""
    instrument = cast(str, _text(instrument_ref, "instrument_ref"))
    submissions_response = _response(submissions, _RAW_SUBMISSIONS_SCHEMA)
    facts_response = _response(company_facts, _RAW_FACTS_SCHEMA)
    submissions_cik = _cik(submissions_response.get("cik"), "submissions.cik")
    facts_cik = _cik(facts_response.get("cik"), "companyfacts.cik")
    payload_cik = _cik(company_facts.payload.get("cik"), "payload.cik")
    if len({submissions_cik, facts_cik, payload_cik}) != 1:
        raise SecNormalizationError("SEC CIK mismatch between submissions and company facts")
    entity_name = cast(
        str,
        _text(facts_response.get("entityName"), "companyfacts.entityName"),
    )
    source_observation_ids = tuple(sorted((submissions.event_id, company_facts.event_id)))
    source_payload_hashes = tuple(
        sorted((submissions.payload_hash, company_facts.payload_hash))
    )
    filings = _filings(
        submissions_response,
        cik=facts_cik,
        entity_name=entity_name,
        source_observation_ids=source_observation_ids,
        source_payload_hashes=source_payload_hashes,
    )
    filings_by_accession = {filing.accession: filing for filing in filings}
    facts = _facts(
        facts_response,
        cik=facts_cik,
        entity_name=entity_name,
        filings_by_accession=filings_by_accession,
        source_observation_ids=source_observation_ids,
        source_payload_hashes=source_payload_hashes,
    )
    received_at = max(submissions.received_at, company_facts.received_at)
    # A same-day filing without acceptance time is deliberately unavailable
    # until the conservative next-day boundary. It is omitted now and will be
    # emitted by the next poll; assigning it a future reception would invent
    # an observation and violate the envelope chronology.
    filings = tuple(item for item in filings if item.available_at <= received_at)
    facts = tuple(item for item in facts if item.available_at <= received_at)
    envelopes = [
        _derived_envelope(
            filing,
            schema=SEC_FILING_SCHEMA,
            native_identity=f"filing:{filing.accession}",
            instrument_ref=instrument,
            received_at=received_at,
        )
        for filing in filings
    ]
    envelopes.extend(
        _derived_envelope(
            fact,
            schema=SEC_FACT_SCHEMA,
            native_identity=(
                f"fact:{fact.taxonomy}:{fact.concept}:{fact.unit}:"
                f"{fact.period_start or 'instant'}:{fact.period_end}:"
                f"{fact.frame or 'no-frame'}:{fact.accession}"
            ),
            instrument_ref=instrument,
            received_at=received_at,
        )
        for fact in facts
    )
    envelopes.sort(key=lambda item: (item.as_of, item.schema_version, item.source_event_id or ""))
    return tuple(envelopes)
