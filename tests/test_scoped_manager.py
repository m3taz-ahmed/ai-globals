"""Tests for runtime/scoped_manager.py — ScopedManager + ScopedRegistry."""
from __future__ import annotations

import threading

import pytest

from runtime.scoped_manager import ScopedManager, ScopedManagerError, ScopedRegistry, scoped_factory


class _Counter:
    def __init__(self) -> None:
        self.count = 0


class _CounterManager(ScopedManager):
    def _create_instance(self) -> _Counter:
        return _Counter()


def test_scoped_manager_creates_on_first_resolve() -> None:
    mgr = _CounterManager()
    instance = mgr.resolve()
    assert isinstance(instance, _Counter)


def test_scoped_manager_returns_same_instance_within_context() -> None:
    mgr = _CounterManager()
    a = mgr.resolve()
    b = mgr.resolve()
    assert a is b


def test_scoped_manager_flush_forces_recreation() -> None:
    mgr = _CounterManager()
    a = mgr.resolve()
    mgr.flush()
    b = mgr.resolve()
    assert a is not b


def test_scoped_manager_isolation_across_threads() -> None:
    mgr = _CounterManager()
    main_instance = mgr.resolve()

    other_instance: list[object] = []

    def _thread_fn() -> None:
        other_instance.append(mgr.resolve())

    t = threading.Thread(target=_thread_fn)
    t.start()
    t.join()

    assert other_instance[0] is not main_instance


def test_scoped_manager_base_create_raises() -> None:
    mgr = ScopedManager()
    with pytest.raises(ScopedManagerError):
        mgr.resolve()


# --- ScopedRegistry ---

def test_registry_register_and_resolve() -> None:
    registry = ScopedRegistry()
    mgr = _CounterManager()
    registry.register("counter", mgr)
    instance = registry.resolve("counter")
    assert isinstance(instance, _Counter)


def test_registry_resolve_unknown_raises() -> None:
    registry = ScopedRegistry()
    with pytest.raises(ScopedManagerError):
        registry.resolve("nonexistent")


def test_registry_duplicate_register_raises() -> None:
    registry = ScopedRegistry()
    registry.register("counter", _CounterManager())
    with pytest.raises(ScopedManagerError):
        registry.register("counter", _CounterManager())


def test_registry_flush_single() -> None:
    registry = ScopedRegistry()
    registry.register("counter", _CounterManager())
    a = registry.resolve("counter")
    registry.flush("counter")
    b = registry.resolve("counter")
    assert a is not b


def test_registry_flush_all() -> None:
    registry = ScopedRegistry()
    registry.register("a", _CounterManager())
    registry.register("b", _CounterManager())
    a1 = registry.resolve("a")
    b1 = registry.resolve("b")
    registry.flush_all()
    a2 = registry.resolve("a")
    b2 = registry.resolve("b")
    assert a1 is not a2
    assert b1 is not b2


def test_registry_names() -> None:
    registry = ScopedRegistry()
    registry.register("a", _CounterManager())
    registry.register("b", _CounterManager())
    assert sorted(registry.names()) == ["a", "b"]


def test_registry_flush_unknown_is_noop() -> None:
    registry = ScopedRegistry()
    registry.flush("nonexistent")  # should not raise


# --- scoped_factory ---

def test_scoped_factory_creates_from_fn() -> None:
    counter = _Counter()
    mgr = scoped_factory(lambda: counter)
    assert mgr.resolve() is counter


def test_scoped_factory_recreates_after_flush() -> None:
    factory_calls: list[int] = []

    def _factory() -> _Counter:
        factory_calls.append(1)
        return _Counter()

    mgr = scoped_factory(_factory)
    a = mgr.resolve()
    mgr.flush()
    b = mgr.resolve()
    assert a is not b
    assert len(factory_calls) == 2
