#!/usr/bin/env python3
"""OpenTelemetry-inspired distributed tracing for aiZee.

Re-implements the API/SDK split pattern from opentelemetry-python so library
code depends only on this API, while the OS runtime supplies the SDK exporter.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class SpanKind:
    """Span kinds."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class Span:
    """A trace span."""

    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    kind: str
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "unset"
    status_description: str = ""

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def set_attributes(self, values: dict[str, Any]) -> None:
        self.attributes.update(values)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "timestamp": time.time(), "attributes": attributes or {}})

    def set_status(self, status: str, description: str = "") -> None:
        self.status = status
        self.status_description = description

    def end(self, timestamp: float | None = None) -> None:
        self.end_time = timestamp or time.time()


class SpanProcessor:
    """Hook interface for span lifecycle events."""

    def on_start(self, span: Span) -> None:
        pass

    def on_end(self, span: Span) -> None:
        pass


class ConsoleSpanExporter(SpanProcessor):
    """Exporter that prints spans as JSON lines to a file or stdout."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path

    def on_end(self, span: Span) -> None:
        line = json.dumps(
            {
                "trace_id": span.trace_id,
                "span_id": span.span_id,
                "parent_id": span.parent_id,
                "name": span.name,
                "kind": span.kind,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "attributes": span.attributes,
                "events": span.events,
                "status": span.status,
                "status_description": span.status_description,
            },
            default=str,
        )
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            print(line)


class _MultiProcessor(SpanProcessor):
    def __init__(self, processors: list[SpanProcessor]) -> None:
        self.processors = processors

    def on_start(self, span: Span) -> None:
        for processor in self.processors:
            processor.on_start(span)

    def on_end(self, span: Span) -> None:
        for processor in self.processors:
            processor.on_end(span)


_CURRENT_SPAN: ContextVar[Span | None] = ContextVar("current_span", default=None)


class Tracer:
    """Creates and manages spans."""

    def __init__(self, name: str, processor: SpanProcessor) -> None:
        self.name = name
        self.processor = processor

    @staticmethod
    def _ids() -> tuple[str, str]:
        return uuid.uuid4().hex, uuid.uuid4().hex[:16]

    def start_span(
        self,
        name: str,
        kind: str = SpanKind.INTERNAL,
        parent: Span | None = None,
    ) -> Span:
        parent_span = parent or _CURRENT_SPAN.get()
        trace_id, span_id = self._ids()
        if parent_span:
            trace_id = parent_span.trace_id
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_span.span_id if parent_span else None,
            name=name,
            kind=kind,
            start_time=time.time(),
        )
        self.processor.on_start(span)
        return span

    def start_as_current_span(
        self,
        name: str,
        kind: str = SpanKind.INTERNAL,
    ) -> Span:
        span = self.start_span(name, kind=kind)
        _CURRENT_SPAN.set(span)
        return span


class TracerProvider:
    """Global tracer provider with API/SDK split."""

    def __init__(self, processors: list[SpanProcessor] | None = None) -> None:
        self.processors = processors or []
        self._tracers: dict[str, Tracer] = {}

    def add_span_processor(self, processor: SpanProcessor) -> None:
        self.processors.append(processor)

    def get_tracer(self, name: str) -> Tracer:
        if name not in self._tracers:
            processor = _MultiProcessor(self.processors)
            self._tracers[name] = Tracer(name, processor)
        return self._tracers[name]


@contextmanager
def use_span(span: Span) -> Iterator[Span]:
    """Context manager to set the current active span."""
    token = _CURRENT_SPAN.set(span)
    try:
        yield span
    finally:
        _CURRENT_SPAN.reset(token)


@contextmanager
def with_span(tracer: Tracer, name: str, kind: str = SpanKind.INTERNAL) -> Iterator[Span]:
    """Context manager that starts, activates, and ends a span."""
    span = tracer.start_span(name, kind=kind)
    try:
        with use_span(span):
            yield span
    finally:
        span.end()


def get_current_span() -> Span | None:
    return _CURRENT_SPAN.get()

