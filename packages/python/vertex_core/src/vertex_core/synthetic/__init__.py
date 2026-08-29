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

__all__ = [
    "SYNTHETIC_RIGHTS",
    "SYNTHETIC_SCHEMA_NEWS",
    "SYNTHETIC_SCHEMA_QUOTE",
    "SYNTHETIC_SOURCE",
    "SYNTHETIC_TITLE_PREFIX",
    "generate_envelopes",
    "is_synthetic",
]
