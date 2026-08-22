"""Scoped managers - request/context-isolated service instances.

Inspired by Filament's ``app()->scoped()`` pattern and Laravel Octane's
state-flushing listeners. Scoped managers create fresh instances per context
(request, session, test) to prevent state leakage in long-running processes.
"""
from __future__ import annotations

from collections.abc import Callable
from threading import local as thread_local
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class ScopedManagerError(AizeeError):
    """Raised when a scoped manager operation fails."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("SCOPED_MANAGER_ERROR", message, ErrorSeverity.MEDIUM, context)


class ScopedManager:
    """Base class for context-scoped managers.

    Subclasses define ``_create_instance`` to build a fresh instance.
    ``resolve()`` returns the instance for the current context, creating it
    on first access. ``flush()`` clears the current context's instance.
    """

    def __init__(self) -> None:
        self._storage: thread_local = thread_local()

    def _create_instance(self) -> Any:
        """Build a fresh instance for the current context. Override in subclass."""
        raise ScopedManagerError(f"{self.__class__.__name__} must implement _create_instance")

    def resolve(self) -> Any:
        """Get or create the instance for the current context."""
        if not hasattr(self._storage, "instance"):
            self._storage.instance = self._create_instance()
        return self._storage.instance

    def flush(self) -> None:
        """Clear the current context's instance (forces re-creation on next resolve)."""
        if hasattr(self._storage, "instance"):
            delattr(self._storage, "instance")


class ScopedRegistry:
    """Registry of named scoped managers with batch flush support.

    Usage::

        registry = ScopedRegistry()
        registry.register("cache", CacheManager())
        registry.register("search", SearchManager())
        instance = registry.resolve("cache")
        registry.flush_all()  # Octane request boundary
    """

    def __init__(self) -> None:
        self._managers: dict[str, ScopedManager] = {}

    def register(self, name: str, manager: ScopedManager) -> ScopedRegistry:
        """Register a scoped manager under a name. Returns self for chaining."""
        if name in self._managers:
            raise ScopedManagerError(f"Scoped manager '{name}' already registered")
        self._managers[name] = manager
        return self

    def resolve(self, name: str) -> Any:
        """Resolve the instance for a named scoped manager."""
        manager = self._managers.get(name)
        if manager is None:
            raise ScopedManagerError(f"Unknown scoped manager '{name}'")
        return manager.resolve()

    def flush(self, name: str) -> None:
        """Flush a single named scoped manager."""
        manager = self._managers.get(name)
        if manager is not None:
            manager.flush()

    def flush_all(self) -> None:
        """Flush all registered scoped managers (call at request/context boundary)."""
        for manager in self._managers.values():
            manager.flush()

    def names(self) -> list[str]:
        """List registered manager names."""
        return list(self._managers.keys())


def scoped_factory(
    factory_fn: Callable[[], Any],
) -> ScopedManager:
    """Create a ScopedManager from a factory function.

    Convenience for simple cases where a full subclass is overkill::

        cache = scoped_factory(lambda: build_cache_client())
        instance = cache.resolve()
    """

    class _FactoryScopedManager(ScopedManager):
        def _create_instance(self) -> Any:
            return factory_fn()

    return _FactoryScopedManager()
