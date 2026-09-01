"""Read-only adapters for approved public and identifier sources.

This package performs no financial calculation and has no account, portfolio,
order or execution capability. Every response is wrapped in the canonical
``DataEnvelope`` before it may cross the adapter boundary.
"""

from vertex_edge_official.clients import (
    EcbDataClient,
    FredClient,
    OpenFigiClient,
    OpenFigiMapping,
    SecEdgarClient,
    SnbDataClient,
)
from vertex_edge_official.config import OfficialSourceConfig
from vertex_edge_official.transport import (
    HttpRequest,
    HttpResponse,
    HttpTransport,
    OfficialSourceError,
    UrllibTransport,
)

__all__ = [
    "EcbDataClient",
    "FredClient",
    "HttpRequest",
    "HttpResponse",
    "HttpTransport",
    "OfficialSourceError",
    "OfficialSourceConfig",
    "OpenFigiClient",
    "OpenFigiMapping",
    "SecEdgarClient",
    "SnbDataClient",
    "UrllibTransport",
]
