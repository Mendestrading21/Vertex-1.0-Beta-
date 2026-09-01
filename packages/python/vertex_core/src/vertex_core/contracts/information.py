"""Canonical, point-in-time contracts for regulatory information."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from vertex_core.contracts.types import (
    ContractModel,
    FiniteDecimal,
    FrozenStrMapping,
    NonEmptyStr,
    Sha256Ref,
    UtcDatetime,
)

__all__ = ["Filing", "FundamentalFact"]

Cik = Annotated[str, StringConstraints(pattern=r"^[0-9]{10}$")]
Accession = Annotated[
    str, StringConstraints(pattern=r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
]


class Filing(ContractModel):
    """One SEC filing version, available no earlier than ``available_at``."""

    authority: Literal["SEC_EDGAR"]
    source_observation_ids: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    source_payload_hashes: Annotated[tuple[Sha256Ref, ...], Field(min_length=1)]
    cik: Cik
    entity_name: NonEmptyStr
    accession: Accession
    form: NonEmptyStr
    report_date: date | None
    filed_date: date
    accepted_at: UtcDatetime | None
    available_at: UtcDatetime
    primary_document: NonEmptyStr
    primary_document_url: NonEmptyStr
    primary_document_description: NonEmptyStr | None
    is_xbrl: bool
    is_inline_xbrl: bool
    is_amendment: bool
    supersedes_accession: Accession | None


class FundamentalFact(ContractModel):
    """One XBRL fact tied to its filing, unit, period and dimensions."""

    authority: Literal["SEC_EDGAR"]
    source_observation_ids: Annotated[tuple[NonEmptyStr, ...], Field(min_length=1)]
    source_payload_hashes: Annotated[tuple[Sha256Ref, ...], Field(min_length=1)]
    cik: Cik
    entity_name: NonEmptyStr
    taxonomy: NonEmptyStr
    concept: NonEmptyStr
    label: NonEmptyStr
    description: NonEmptyStr | None
    value: FiniteDecimal
    unit: NonEmptyStr
    period_start: date | None
    period_end: date
    filed_date: date
    available_at: UtcDatetime
    accession: Accession
    form: NonEmptyStr
    fiscal_year: Annotated[int, Field(ge=1900, le=9999)] | None
    fiscal_period: NonEmptyStr | None
    frame: NonEmptyStr | None
    dimensions: FrozenStrMapping
    is_amendment: bool
