"""Unit tests of the topic-to-handler registry."""

from __future__ import annotations

import pytest

from vertex_worker.errors import HandlerError, UnregisteredTopicError
from vertex_worker.registry import HandlerRegistry


def _handler(session, message) -> None:  # pragma: no cover - never called
    return None


class TestHandlerRegistry:
    def test_register_and_get(self) -> None:
        registry = HandlerRegistry()
        registry.register("observation.ingested", _handler)
        assert registry.get("observation.ingested") is _handler

    def test_topics_sorted_deterministically(self) -> None:
        registry = HandlerRegistry()
        registry.register("z.topic", _handler)
        registry.register("a.topic", _handler)
        assert registry.topics == ("a.topic", "z.topic")

    def test_unknown_topic_returns_none(self) -> None:
        assert HandlerRegistry().get("nope") is None

    def test_duplicate_registration_refused(self) -> None:
        registry = HandlerRegistry()
        registry.register("t", _handler)
        with pytest.raises(ValueError):
            registry.register("t", _handler)

    def test_empty_topic_refused(self) -> None:
        with pytest.raises(ValueError):
            HandlerRegistry().register("  ", _handler)

    def test_non_callable_refused(self) -> None:
        with pytest.raises(TypeError):
            HandlerRegistry().register("t", object())  # type: ignore[arg-type]


class TestErrorTypes:
    def test_handler_error_requires_canonical_code(self) -> None:
        with pytest.raises(ValueError):
            HandlerError("boom", code="not canonical")

    def test_handler_error_keeps_code(self) -> None:
        assert HandlerError("boom", code="MY_CODE").code == "MY_CODE"

    def test_unregistered_topic_error_code(self) -> None:
        error = UnregisteredTopicError("some.topic")
        assert error.code == "UNREGISTERED_TOPIC"
        assert "some.topic" in str(error)
