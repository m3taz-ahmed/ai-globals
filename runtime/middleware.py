"""Middleware pipeline for aiZee runtime.

Implements Pattern 4 (from tRPC): Flat middleware array + recursive
``callRecursive`` execution. Middlewares are stored as a flat list and
executed via a single recursive function where each middleware calls
``next()`` to recurse to the next index. Errors are caught at each level
and wrapped into ``MiddlewareResult(ok=False, error)`` — the chain never
raises.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from runtime.schemas import AizeeError, ErrorSeverity

T = TypeVar("T")


# -- Pattern 4: Flat Middleware Array + Recursive Execution (tRPC) ----------


@dataclass
class ActionContext:
    """Mutable context object carried through the middleware/enhancer pipeline.

    Attributes:
        action_type: The action being evaluated (e.g., "Read", "write").
        data: Action data / kwargs forwarded to the handler.
        dry_run: If True, the action is simulated without side effects.
        session_id: Optional session identifier for budget tracking.
        overrides: Mutable context overrides propagated by middlewares
            (analogous to tRPC's ``next({ ctx: { user } })``).
    """

    action_type: str
    data: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    session_id: str | None = None
    overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class MiddlewareResult(Generic[T]):
    """Discriminated result from middleware/pipeline execution.

    Inspired by tRPC's ``MiddlewareResult<T>``: either ``{ok: true, data}``
    or ``{ok: false, error}``. Forces callers to handle both success and
    error cases, eliminating unhandled error paths.
    """

    ok: bool
    data: T | None = None
    error: AizeeError | None = None


# Type aliases for the middleware contract.
NextFunction = Callable[[], MiddlewareResult[Any]]
Middleware = Callable[[ActionContext, NextFunction], MiddlewareResult[Any]]
HandlerFn = Callable[[ActionContext], MiddlewareResult[Any]]


def _truncate_cause(text: str, limit: int = 500) -> str:
    if len(text) > limit:
        return text[:limit] + "...[truncated]"
    return text


def normalize_error(cause: BaseException) -> AizeeError:
    """Convert any thrown value into an AizeeError.

    Analogous to tRPC's ``getTRPCErrorFromUnknown()``: any exception (Error,
    string, object) is converted to an ``AizeeError`` so the pipeline never
    lets raw exceptions escape.
    """
    if isinstance(cause, AizeeError):
        return cause
    return AizeeError(
        error_code="INTERNAL",
        message=_truncate_cause(str(cause) or cause.__class__.__name__),
        severity=ErrorSeverity.HIGH,
    )


class MiddlewarePipeline:
    """Flat middleware array executed via recursive ``callRecursive``.

    Inspired by tRPC's procedure builder: middlewares are stored as a flat
    list and executed via a single recursive function. Each middleware calls
    ``next()`` to recurse to the next index. Errors are caught at each level
    and wrapped into ``MiddlewareResult(ok=False, error)``.
    """

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def use(self, mw: Middleware) -> None:
        """Append a middleware to the flat array."""
        self._middlewares.append(mw)

    def has_middlewares(self) -> bool:
        """True if at least one middleware is registered."""
        return len(self._middlewares) > 0

    def execute(
        self,
        context: ActionContext,
        handler: HandlerFn,
    ) -> MiddlewareResult[Any]:
        """Execute the middleware chain with ``handler`` as the terminal step.

        Iterative loop (no recursion): each middleware receives a ``next()``
        closure that advances an explicit index stack, avoiding RecursionError
        on long chains.
        """
        middlewares = self._middlewares

        def _handler_call() -> MiddlewareResult[Any]:
            try:
                return handler(context)
            except AizeeError as e:
                return MiddlewareResult(ok=False, error=e)
            except Exception as e:
                return MiddlewareResult(ok=False, error=normalize_error(e))

        # Iteratively compose the onion chain backwards (no recursive dispatcher).
        nxt: Callable[[], MiddlewareResult[Any]] = _handler_call
        for rev in range(len(middlewares) - 1, -1, -1):
            mw = middlewares[rev]
            prev_nxt = nxt

            def _make_call(
                m: Middleware = mw,
                n: Callable[[], MiddlewareResult[Any]] = prev_nxt,
            ) -> Callable[[], MiddlewareResult[Any]]:
                def _call() -> MiddlewareResult[Any]:
                    try:
                        return m(context, n)
                    except AizeeError as e:
                        return MiddlewareResult(ok=False, error=e)
                    except Exception as e:
                        return MiddlewareResult(ok=False, error=normalize_error(e))

                return _call

            nxt = _make_call()
        try:
            return nxt()
        except AizeeError as e:
            return MiddlewareResult(ok=False, error=e)
        except Exception as e:
            return MiddlewareResult(ok=False, error=normalize_error(e))

