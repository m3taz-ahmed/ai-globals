#!/usr/bin/env python3
"""Lightweight Prometheus-compatible metrics registry for aiZee.

Re-implements the core patterns from prometheus/client_python without the
external dependency, keeping the OS sovereign and offline-capable.
"""

from __future__ import annotations

import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Generic, TypeVar

from runtime.schemas import AizeeError, ErrorSeverity, ValidationError


class MetricNameError(AizeeError):
    """Raised when a metric or label name is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__("METRIC_NAME_ERROR", message, ErrorSeverity.LOW)


class MetricDuplicationError(AizeeError):
    """Raised when a metric is registered twice."""

    def __init__(self, message: str) -> None:
        super().__init__("METRIC_DUPLICATION", message, ErrorSeverity.LOW)


class LabelValueError(AizeeError):
    """Raised when a metric is used with missing or unexpected labels."""

    def __init__(self, message: str) -> None:
        super().__init__("LABEL_VALUE_ERROR", message, ErrorSeverity.LOW)


_VALID_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_VALID_LABEL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_RESERVED_LABELS = {"__name__"}


def _validate_name(name: str) -> None:
    if not _VALID_NAME.match(name):
        raise MetricNameError(f"Invalid metric name: {name!r}")


def _validate_label_names(label_names: tuple[str, ...]) -> None:
    for label in label_names:
        if label in _RESERVED_LABELS or not _VALID_LABEL_NAME.match(label):
            raise MetricNameError(f"Invalid label name: {label!r}")


@dataclass
class Sample:
    """A single time-series sample."""

    name: str
    labels: dict[str, str]
    value: float


class _MetricChild:
    """Base for a concrete metric child (time series)."""

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        raise NotImplementedError  # pragma: no cover


T = TypeVar("T", bound=_MetricChild, covariant=True)


class Metric(Generic[T]):
    """Base class for all metrics."""

    _type: ClassVar[str] = ""
    # Bound cardinality: max distinct label-sets per metric family.
    # Summary children each hold a bounded deque (see _SummaryChild);
    # this caps the number of children so total memory stays bounded.
    MAX_CHILDREN: ClassVar[int] = 1000

    def __init__(self, name: str, documentation: str, labels: tuple[str, ...] = ()) -> None:
        _validate_name(name)
        _validate_label_names(labels)
        self._name = name
        self._documentation = documentation
        self._label_names = labels
        self._children: dict[tuple[str, ...], T] = {}
        self._default_child: T | None = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def documentation(self) -> str:
        return self._documentation

    @property
    def type(self) -> str:
        return self._type

    def labels(self, **kwargs: str) -> T:
        if not self._label_names:
            if kwargs:
                raise LabelValueError(f"Metric {self._name!r} has no labels")
            with self._lock:
                if self._default_child is None:
                    self._default_child = self._new_child()
                return self._default_child

        missing = [k for k in self._label_names if k not in kwargs]
        if missing:
            raise LabelValueError(f"Metric {self._name!r} missing labels: {missing}")
        label_values = tuple(str(kwargs[k]) for k in self._label_names)
        with self._lock:
            if label_values not in self._children:
                if len(self._children) >= self.MAX_CHILDREN:
                    raise LabelValueError(
                        f"Metric {self._name!r} exceeds max cardinality ({self.MAX_CHILDREN})"
                    )
                self._children[label_values] = self._new_child()
            return self._children[label_values]

    def _new_child(self) -> T:
        raise NotImplementedError  # pragma: no cover

    def collect(self) -> list[Sample]:
        samples: list[Sample] = []
        with self._lock:
            children = list(self._children.items())
            if self._default_child is not None:
                children.append(((), self._default_child))
            for label_values, child in children:
                labels = (
                    dict(zip(self._label_names, label_values, strict=False))
                    if self._label_names
                    else {}
                )
                samples.extend(child._samples(self._name, labels))
        return samples


class _CounterChild(_MetricChild):
    def __init__(self) -> None:
        self._value = 0.0
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0) -> None:
        if amount < 0:
            raise ValidationError(f"Counter.inc amount must be >= 0, got {amount}")
        with self._lock:
            self._value += amount

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        return [Sample(name=name + "_total", labels=labels, value=self._value)]


class Counter(Metric[_CounterChild]):
    """A counter metric that only increases."""

    _type = "counter"

    def _new_child(self) -> _CounterChild:
        return _CounterChild()

    def inc(self, amount: float = 1.0) -> None:
        self.labels().inc(amount)


class _GaugeChild(_MetricChild):
    def __init__(self) -> None:
        self._value = 0.0
        self._lock = threading.Lock()

    def set(self, value: float) -> None:
        with self._lock:
            self._value = value

    def inc(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value += amount

    def dec(self, amount: float = 1.0) -> None:
        with self._lock:
            self._value -= amount

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        return [Sample(name=name, labels=labels, value=self._value)]


class Gauge(Metric[_GaugeChild]):
    """A gauge metric that can go up or down."""

    _type = "gauge"

    def _new_child(self) -> _GaugeChild:
        return _GaugeChild()

    def set(self, value: float) -> None:
        self.labels().set(value)

    def inc(self, amount: float = 1.0) -> None:
        self.labels().inc(amount)

    def dec(self, amount: float = 1.0) -> None:
        self.labels().dec(amount)


class _HistogramChild(_MetricChild):
    DEFAULT_BUCKETS: ClassVar[tuple[float, ...]] = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        float("inf"),
    )

    def __init__(self, buckets: tuple[float, ...] = DEFAULT_BUCKETS) -> None:
        sorted_buckets = sorted(set(buckets) | {float("inf")})
        self._buckets = sorted_buckets
        self._counts = [0.0] * len(sorted_buckets)
        self._sum = 0.0
        self._count = 0.0
        self._lock = threading.Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    self._counts[i] += 1

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        samples = [
            Sample(name=name + "_sum", labels=labels, value=self._sum),
            Sample(name=name + "_count", labels=labels, value=self._count),
        ]
        cumulative = 0.0
        for bound, count in zip(self._buckets, self._counts, strict=False):
            cumulative += count
            bucket_labels = {**labels, "le": "+Inf" if bound == float("inf") else str(bound)}
            samples.append(Sample(name=name + "_bucket", labels=bucket_labels, value=cumulative))
        return samples


class Histogram(Metric[_HistogramChild]):
    """A histogram metric that observes values into buckets."""

    _type = "histogram"

    def __init__(
        self,
        name: str,
        documentation: str,
        labels: tuple[str, ...] = (),
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        super().__init__(name, documentation, labels)
        self._buckets = buckets

    def _new_child(self) -> _HistogramChild:
        return _HistogramChild(self._buckets or _HistogramChild.DEFAULT_BUCKETS)

    def observe(self, value: float) -> None:
        self.labels().observe(value)


class _SummaryChild(_MetricChild):
    # Max number of observations kept for quantile calculation.
    # Older values are evicted automatically by the deque.
    _MAX_WINDOW = 10000

    def __init__(self, quantiles: tuple[float, ...] = (0.5, 0.9, 0.99)) -> None:
        self._quantiles = quantiles
        self._values: deque[float] = deque(maxlen=self._MAX_WINDOW)
        self._sum = 0.0
        self._count = 0.0
        self._lock = threading.Lock()

    def observe(self, value: float) -> None:
        with self._lock:
            self._values.append(value)
            self._sum += value
            self._count += 1

    def _quantile(self, q: float, sorted_values: list[float] | None = None) -> float:
        if not self._values:
            return 0.0
        if sorted_values is None:
            sorted_values = sorted(self._values)
        idx = q * (len(sorted_values) - 1)
        lower = int(idx)
        upper = lower + 1
        if upper >= len(sorted_values):
            return sorted_values[-1]
        return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (idx - lower)

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        samples = [
            Sample(name=name + "_sum", labels=labels, value=self._sum),
            Sample(name=name + "_count", labels=labels, value=self._count),
        ]
        # Sort values once and reuse for all quantiles (avoids O(k·n log n)).
        sorted_values = sorted(self._values) if self._values else None
        for q in self._quantiles:
            q_labels = {**labels, "quantile": str(q)}
            samples.append(Sample(name=name, labels=q_labels, value=self._quantile(q, sorted_values)))
        return samples


class Summary(Metric[_SummaryChild]):
    """A summary metric that tracks quantiles."""

    _type = "summary"

    def __init__(
        self,
        name: str,
        documentation: str,
        labels: tuple[str, ...] = (),
        quantiles: tuple[float, ...] = (0.5, 0.9, 0.99),
    ) -> None:
        super().__init__(name, documentation, labels)
        self._quantiles = quantiles

    def _new_child(self) -> _SummaryChild:
        return _SummaryChild(self._quantiles)

    def observe(self, value: float) -> None:
        self.labels().observe(value)


class _InfoChild(_MetricChild):
    def __init__(self) -> None:
        self._info: dict[str, str] = {}

    def info(self, value: dict[str, str]) -> None:
        self._info = value

    def _samples(self, name: str, labels: dict[str, str]) -> list[Sample]:
        combined = {**labels, **self._info}
        return [Sample(name=name, labels=combined, value=1.0)]


class Info(Metric[_InfoChild]):
    """An info metric that exposes a static set of key-value labels."""

    _type = "gauge"

    def _new_child(self) -> _InfoChild:
        return _InfoChild()

    def info(self, value: dict[str, str]) -> None:
        self.labels().info(value)


class CollectorRegistry:
    """Registry for metric collectors."""

    def __init__(self) -> None:
        self._collectors: dict[str, Metric[_MetricChild]] = {}
        self._lock = threading.Lock()

    def register(self, metric: Metric[_MetricChild]) -> None:
        _validate_name(metric.name)
        with self._lock:
            if metric.name in self._collectors:
                raise MetricDuplicationError(f"Metric {metric.name!r} already registered")
            self._collectors[metric.name] = metric

    def unregister(self, metric: Metric[_MetricChild]) -> None:
        with self._lock:
            self._collectors.pop(metric.name, None)

    def collect(self) -> list[Sample]:
        samples: list[Sample] = []
        with self._lock:
            for metric in self._collectors.values():
                samples.extend(metric.collect())
        return samples

    def names(self) -> list[str]:
        with self._lock:
            return sorted(self._collectors)

    def restricted_registry(self, names: list[str]) -> RestrictedRegistry:
        return RestrictedRegistry(self, names)


class RestrictedRegistry(CollectorRegistry):
    """A view that only exposes a subset of metrics."""

    def __init__(self, parent: CollectorRegistry, names: list[str]) -> None:
        super().__init__()
        self._parent = parent
        self._names = set(names)

    def collect(self) -> list[Sample]:
        return [s for s in self._parent.collect() if _base_name(s.name) in self._names]


_GLOBAL_REGISTRY = CollectorRegistry()


def register(metric: Metric[_MetricChild]) -> None:
    _GLOBAL_REGISTRY.register(metric)


def unregister(metric: Metric[_MetricChild]) -> None:
    _GLOBAL_REGISTRY.unregister(metric)


def _base_name(sample_name: str) -> str:
    """Return the metric family base name from a sample name."""
    for suffix in ("_total", "_sum", "_count", "_bucket", "_info"):
        if sample_name.endswith(suffix):
            return sample_name[: -len(suffix)]
    return sample_name


def _escape_label_value(value: str) -> str:
    """Escape backslash, double-quote, and newline for exposition format."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    return "{" + ",".join(f'{k}="{_escape_label_value(str(v))}"' for k, v in labels.items()) + "}"


def generate_latest(registry: CollectorRegistry | None = None) -> str:
    """Generate Prometheus exposition text for the registry."""
    registry = registry or _GLOBAL_REGISTRY
    lines: list[str] = []
    seen_help: set[str] = set()
    seen_type: set[str] = set()

    # Iterate collectors properly: RestrictedRegistry exposes only a subset
    # via its parent, so resolve visible collectors explicitly to emit HELP/TYPE.
    if isinstance(registry, RestrictedRegistry):
        visible: list[Metric[_MetricChild]] = [
            m for name, m in registry._parent._collectors.items() if name in registry._names
        ]
    else:
        with registry._lock:
            visible = list(registry._collectors.values())
    for metric in visible:
        if metric.name not in seen_help:
            lines.append(f"# HELP {metric.name} {metric.documentation}")
            seen_help.add(metric.name)
        if metric.name not in seen_type:
            lines.append(f"# TYPE {metric.name} {metric.type}")
            seen_type.add(metric.name)

    for sample in registry.collect():
        lines.append(f"{sample.name}{_format_labels(sample.labels)} {sample.value}")

    return "\n".join(lines) + "\n"


class Timer:
    """Context manager to time a block and report to a Histogram or Summary."""

    def __init__(self, metric: Histogram | Summary) -> None:
        self.metric = metric

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        elapsed = time.perf_counter() - self._start
        self.metric.observe(elapsed)


class ExceptionCounter(Counter):
    """Counter that increments when an exception is raised inside a with block."""

    def __enter__(self) -> ExceptionCounter:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, *exc: Any) -> None:
        if exc_type is not None:
            self.inc()


def inprogress(metric: Gauge) -> _InProgress:
    """Decorator / context manager to track in-progress operations."""
    return _InProgress(metric)


class _InProgress:
    def __init__(self, metric: Gauge) -> None:
        self.metric = metric

    def __enter__(self) -> _InProgress:
        self.metric.inc()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.metric.dec()


if TYPE_CHECKING:
    from runtime.kernel import Kernel


def format_metrics(k: Kernel) -> str:
    """Return Prometheus exposition text for key runtime metrics (dashboard)."""
    status = k.status()
    workflows = status.get("workflows", [])
    rules = status.get("rules", [])
    budgets = status.get("budgets", [])
    try:
        n_workflows = len(workflows)
    except TypeError:
        n_workflows = 0
    try:
        n_rules = len(rules)
    except TypeError:
        n_rules = 0
    try:
        n_budgets = len(budgets)
    except TypeError:
        n_budgets = 0
    lines: list[str] = [
        "# HELP aizee_workflows_total Total number of registered workflows",
        "# TYPE aizee_workflows_total gauge",
        f"aizee_workflows_total {n_workflows}",
        "",
        "# HELP aizee_rules_total Total number of loaded policy rules",
        "# TYPE aizee_rules_total gauge",
        f"aizee_rules_total {n_rules}",
        "",
        "# HELP aizee_budgets_total Total number of configured budgets",
        "# TYPE aizee_budgets_total gauge",
        f"aizee_budgets_total {n_budgets}",
        "",
    ]

    for scope, usage in k.budget.usage.items():
        labels = f'scope="{scope}"'
        lines.append(f"# HELP aizee_budget_tokens_total Total tokens used for scope {scope}")
        lines.append("# TYPE aizee_budget_tokens_total counter")
        lines.append(f"aizee_budget_tokens_total{{{labels}}} {usage.get('tokens', 0)}")
        lines.append("")
        lines.append(f"# HELP aizee_budget_calls_total Total calls for scope {scope}")
        lines.append("# TYPE aizee_budget_calls_total counter")
        lines.append(f"aizee_budget_calls_total{{{labels}}} {usage.get('calls', 0)}")
        lines.append("")

    return "\n".join(lines)
