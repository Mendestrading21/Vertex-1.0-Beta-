"""Canonical instrument and option-contract identities.

A symbol alone is never an identity: every identity carries asset class,
exchange, currency and a validity window, and collisions stay ``UNRESOLVED``
until explicitly resolved. An option expiry is never identified by its date
alone: several ``trading_class`` values may coexist at the same expiry, and
each one is a distinct identity.

Both models are strict, frozen and hashable, so distinct identities compare
unequal and can be used as mapping keys.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import model_validator

from vertex_core.contracts.enums import (
    AssetClass,
    ExerciseStyle,
    IdentityStatus,
    OptionRight,
    SettlementType,
)
from vertex_core.contracts.types import (
    ContractModel,
    CurrencyCode,
    NonEmptyStr,
    PositiveDecimal,
    PositiveInt,
    UtcDatetime,
)

__all__ = ["InstrumentId", "OptionContractId"]


class InstrumentId(ContractModel):
    """Canonical identity of one instrument over one validity window.

    ``ibkr_con_id`` is a market-data reference identifier only; no account,
    position or transactional linkage exists anywhere in this contract.
    """

    instrument_id: NonEmptyStr
    asset_class: AssetClass
    canonical_symbol: NonEmptyStr
    exchange: NonEmptyStr
    currency: CurrencyCode
    ibkr_con_id: Optional[PositiveInt] = None
    tradingview_ticker_id: Optional[NonEmptyStr] = None
    isin: Optional[NonEmptyStr] = None
    cusip: Optional[NonEmptyStr] = None
    cik: Optional[NonEmptyStr] = None
    issuer_id: Optional[NonEmptyStr] = None
    valid_from: UtcDatetime
    valid_to: Optional[UtcDatetime] = None
    identity_status: IdentityStatus

    @model_validator(mode="after")
    def _check_validity_window(self) -> "InstrumentId":
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        return self


class OptionContractId(ContractModel):
    """Exact identity of one listed option contract.

    Expiry, strike, right, exchange, currency, multiplier AND ``trading_class``
    are all required: two contracts differing only by ``trading_class`` at the
    same expiry are two distinct identities.
    """

    underlying_id: NonEmptyStr
    ibkr_con_id: Optional[PositiveInt] = None
    expiry: date
    strike: PositiveDecimal
    right: OptionRight
    exercise_style: ExerciseStyle
    settlement_type: SettlementType
    multiplier: PositiveInt
    currency: CurrencyCode
    exchange: NonEmptyStr
    trading_class: NonEmptyStr
    adjustment_code: Optional[NonEmptyStr] = None
    deliverable: Optional[NonEmptyStr] = None
