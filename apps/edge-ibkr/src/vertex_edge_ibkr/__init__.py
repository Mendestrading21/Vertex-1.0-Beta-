"""Vertex edge-ibkr — information-only IBKR market-data edge (LOT-04 socle).

Boundary contract (ADR-004, manifests/forbidden-capabilities.yaml):

- IBKR is a market-data and reference-data source ONLY;
- no order, account, position, P&L, execution or exercise capability exists
  anywhere in this package, in production code or in tests;
- every outgoing observation is a ``vertex_core`` ``DataEnvelope`` with
  ``source='ibkr'``, a connection epoch, aware UTC timestamps and an honest
  delay status;
- absent, sentinel (-1/-2/NaN) or refused values stay ``None`` — never zero.
"""

from vertex_edge_ibkr.port import IbkrInformationPort

__all__ = ["IbkrInformationPort"]
