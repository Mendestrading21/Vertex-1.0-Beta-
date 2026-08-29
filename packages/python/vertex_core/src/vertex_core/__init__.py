"""vertex_core — sole Python authority for Vertex canonical contracts and financial calculations.

Analysis only: this package defines read-only analytical contracts. It contains
no brokerage, transactional, or account capability of any kind.
"""

from vertex_core.version import ENGINE_VERSION

__all__ = ["ENGINE_VERSION"]
