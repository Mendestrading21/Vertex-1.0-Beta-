"""Vertex One API — thin, analysis-only FastAPI shell over ``vertex_core``.

The API validates wire payloads, delegates every verdict to the single
``AdviceEngine`` of ``vertex_core.decision`` and serializes the canonical
contracts. It owns no financial logic, reaches no broker account capability
and exposes nothing transactional (READONLY / ANALYSIS_ONLY).
"""

from vertex_api.app import create_app

__all__ = ["create_app"]
