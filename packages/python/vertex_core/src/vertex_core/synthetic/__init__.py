"""Deterministic synthetic development data (SYNTHETIC status, never live).

Everything produced here is explicitly labeled ``SYNTHETIC``: rights are
``SYNTHETIC``, the source is ``synthetic-dev``, tickers are ``SYN1..SYNn``
and every news title is prefixed ``[SYNTHETIC]``. Nothing generated here may
ever be presented as real, live or subscription-backed data, and the
SYNTHETIC status must never cross a production boundary.
"""

from vertex_core.synthetic.generator import (
    SYNTHETIC_RIGHTS,
    SYNTHETIC_SCHEMA_NEWS,
    SYNTHETIC_SCHEMA_QUOTE,
    SYNTHETIC_SOURCE,
    SYNTHETIC_TITLE_PREFIX,
    generate_envelopes,
    is_synthetic,
)
from vertex_core.synthetic.market import (
    SYNTHETIC_ADJUSTMENT_BASIS,
    SYNTHETIC_MARKET_CURRENCY,
    SYNTHETIC_SCHEMA_DAILY_QUOTE,
    SYNTHETIC_SECTOR_LABELS_FR,
    SYNTHETIC_SECTOR_TICKERS,
    SYNTHETIC_SECTORS,
    generate_daily_quote_envelopes,
)

__all__ = [
    "SYNTHETIC_ADJUSTMENT_BASIS",
    "SYNTHETIC_MARKET_CURRENCY",
    "SYNTHETIC_RIGHTS",
    "SYNTHETIC_SCHEMA_DAILY_QUOTE",
    "SYNTHETIC_SCHEMA_NEWS",
    "SYNTHETIC_SCHEMA_QUOTE",
    "SYNTHETIC_SECTOR_LABELS_FR",
    "SYNTHETIC_SECTOR_TICKERS",
    "SYNTHETIC_SECTORS",
    "SYNTHETIC_SOURCE",
    "SYNTHETIC_TITLE_PREFIX",
    "generate_daily_quote_envelopes",
    "generate_envelopes",
    "is_synthetic",
]
