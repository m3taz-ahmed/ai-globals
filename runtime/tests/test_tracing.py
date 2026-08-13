"""Tests for runtime/tracing.py — distributed tracing primitives."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from runtime.tracing import (
    _CURRENT_SPAN,
    ConsoleSpanExporter,
    Span,
    SpanKind,
    SpanProcessor,
    TracerProvider,
    get_current_span,
    use_span,
    with_span,
)


@pytest.fixture(autouse=True)
def _reset_current_span() -> None:
    """Reset the ContextVar between tests to prevent leakage."""
    token = _CURRENT_SPAN.set(None)
    yield
    _CURRENT_SPAN.reset(token)


class TestSpan:
    """Tests for Span dataclass."""

    def test_create_span_with_defaults(self) -> None:
        span = Span(
            trace_id="trace1",
            span_id="span1",
            parent_id=None,
            name="test",
            kind=SpanKind.INTERNAL,
            start_time=time.time(),
        )
        assert span.end_time is None
        assert span.attributes == {}
        assert span.events == []
        assert span.status == "unset"
        assert span.status_description == ""

    def test_set_attribute(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

    def test_set_attributes(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.set_attributes({"a": 1, "b": 2})
        assert span.attributes == {"a": 1, "b": 2}

    def test_add_event(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.add_event("event1", {"attr": "val"})
        assert len(span.events) == 1
        assert span.events[0]["name"] == "event1"
        assert span.events[0]["attributes"] == {"attr": "val"}
        assert "timestamp" in span.events[0]

    def test_add_event_without_attributes(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.add_event("event1")
        assert span.events[0]["attributes"] == {}

    def test_set_status(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.set_status("ok", "all good")
        assert span.status == "ok"
        assert span.status_description == "all good"

    def test_end_sets_end_time(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        assert span.end_time is None
        span.end()
        assert span.end_time is not None

    def test_end_with_explicit_timestamp(self) -> None:
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        span.end(timestamp=12345.0)
        assert span.end_time == 12345.0


class TestSpanKind:
    """Tests for SpanKind constants."""

    def test_kind_values(self) -> None:
        assert SpanKind.INTERNAL == "internal"
        assert SpanKind.SERVER == "server"
        assert SpanKind.CLIENT == "client"
        assert SpanKind.PRODUCER == "producer"
        assert SpanKind.CONSUMER == "consumer"


class TestSpanProcessor:
    """Tests for SpanProcessor base class."""

    def test_default_on_start_noop(self) -> None:
        processor = SpanProcessor()
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        processor.on_start(span)  # should not raise

    def test_default_on_end_noop(self) -> None:
        processor = SpanProcessor()
        span = Span("t", "s", None, "n", SpanKind.INTERNAL, time.time())
        processor.on_end(span)  # should not raise


class TestConsoleSpanExporter:
    """Tests for ConsoleSpanExporter."""

    def test_writes_to_file(self, tmp_path: Path) -> None:
        path = tmp_path / "spans.jsonl"
        exporter = ConsoleSpanExporter(path)
        span = Span("t1", "s1", None, "test", SpanKind.INTERNAL, time.time())
        span.end()
        exporter.on_end(span)
        content = path.read_text(encoding="utf-8").strip()
        entry = json.loads(content)
        assert entry["trace_id"] == "t1"
        assert entry["span_id"] == "s1"
        assert entry["name"] == "test"

    def test_writes_multiple_spans(self, tmp_path: Path) -> None:
        path = tmp_path / "spans.jsonl"
        exporter = ConsoleSpanExporter(path)
        for i in range(3):
            span = Span(f"t{i}", f"s{i}", None, f"op{i}", SpanKind.INTERNAL, time.time())
            span.end()
            exporter.on_end(span)
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3


class TestTracer:
    """Tests for Tracer class."""

    def test_start_span(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        span = tracer.start_span("operation")
        assert span.name == "operation"
        assert span.kind == SpanKind.INTERNAL
        assert span.trace_id  # non-empty
        assert span.span_id  # non-empty
        assert span.parent_id is None

    def test_start_span_with_kind(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        span = tracer.start_span("op", kind=SpanKind.SERVER)
        assert span.kind == SpanKind.SERVER

    def test_start_span_with_parent(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", parent=parent)
        assert child.parent_id == parent.span_id
        assert child.trace_id == parent.trace_id

    def test_start_as_current_span_sets_context(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        span = tracer.start_as_current_span("op")
        assert get_current_span() is span

    def test_span_processor_on_start_called(self) -> None:
        calls: list[str] = []

        class RecordingProcessor(SpanProcessor):
            def on_start(self, span: Span) -> None:
                calls.append(span.name)

        provider = TracerProvider([RecordingProcessor()])
        tracer = provider.get_tracer("test")
        tracer.start_span("op1")
        assert calls == ["op1"]

    def test_span_processor_on_end_called(self) -> None:
        calls: list[str] = []

        class RecordingProcessor(SpanProcessor):
            def on_end(self, span: Span) -> None:
                calls.append(span.name)

        provider = TracerProvider([RecordingProcessor()])
        tracer = provider.get_tracer("test")
        span = tracer.start_span("op1")
        span.end()
        # Manually trigger on_end via the processor (as the exporter would).
        tracer.processor.on_end(span)
        assert calls == ["op1"]


class TestTracerProvider:
    """Tests for TracerProvider."""

    def test_get_tracer_returns_same_instance(self) -> None:
        provider = TracerProvider()
        t1 = provider.get_tracer("test")
        t2 = provider.get_tracer("test")
        assert t1 is t2

    def test_get_tracer_returns_different_for_different_names(self) -> None:
        provider = TracerProvider()
        t1 = provider.get_tracer("test1")
        t2 = provider.get_tracer("test2")
        assert t1 is not t2

    def test_add_span_processor(self) -> None:
        provider = TracerProvider()
        processor = SpanProcessor()
        provider.add_span_processor(processor)
        assert processor in provider.processors


class TestContextManagers:
    """Tests for use_span and with_span context managers."""

    def test_use_span_sets_and_resets_context(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        span = tracer.start_span("op")
        assert get_current_span() is None
        with use_span(span):
            assert get_current_span() is span
        assert get_current_span() is None

    def test_with_span_creates_and_ends_span(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        with with_span(tracer, "op") as span:
            assert span.name == "op"
            assert span.end_time is None
        assert span.end_time is not None

    def test_with_span_sets_kind(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        with with_span(tracer, "op", kind=SpanKind.SERVER) as span:
            assert span.kind == SpanKind.SERVER

    def test_with_span_resets_context_on_exception(self) -> None:
        provider = TracerProvider()
        tracer = provider.get_tracer("test")
        with pytest.raises(RuntimeError), with_span(tracer, "op"):
            raise RuntimeError("test")
        assert get_current_span() is None
