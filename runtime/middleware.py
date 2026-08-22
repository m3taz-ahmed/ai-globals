"""Middleware pipeline and compiled enhancer pipeline for aiZee runtime.

Implements two architectural patterns:

Pattern 4 (from tRPC): Flat middleware array + recursive ``callRecursive``
execution. Middlewares are stored as a flat list and executed via a single
recursive function where each middleware calls ``next()`` to recurse to the
next index. Errors are caught at each level and wrapped into
``MiddlewareResult(ok=False, error)`` — the chain never raises.

Pattern 5 (from NestJS): Pre-compiled enhancer pipeline. Guards, interceptors,
and pipes are registered at configuration time and compiled into a single
execution chain once, then executed per-request without rebuilding.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
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
        message=str(cause) or cause.__class__.__name__,
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

        Uses a recursive ``callRecursive`` function: each middleware calls
        ``next()`` to recurse to the next index. When the index exceeds the
        array length, the terminal ``handler`` is invoked.
        """
        middlewares = self._middlewares

        def call_recursive(index: int) -> MiddlewareResult[Any]:
            try:
                if index >= len(middlewares):
                    return handler(context)
                mw = middlewares[index]

                def next_fn() -> MiddlewareResult[Any]:
                    return call_recursive(index + 1)

                return mw(context, next_fn)
            except AizeeError as e:
                return MiddlewareResult(ok=False, error=e)
            except Exception as e:  # intentional: wrap any error into MiddlewareResult
                return MiddlewareResult(ok=False, error=normalize_error(e))

        return call_recursive(0)


# -- Pattern 5: Pre-Compiled Enhancer Pipeline (NestJS) --------------------


class EnhancerType(str, Enum):
    """Types of enhancers in the NestJS-style pipeline."""

    GUARD = "guard"
    INTERCEPTOR = "interceptor"
    PIPE = "pipe"


@dataclass
class EnhancerMetadata:
    """Metadata describing a registered enhancer.

    Attributes:
        enhancer_type: The type of enhancer (guard/interceptor/pipe).
        priority: Execution priority (lower runs first).
        handler: The enhancer callable.
    """

    enhancer_type: EnhancerType
    priority: int
    handler: Callable[..., Any]


# Enhancer callable signatures.
GuardFn = Callable[[ActionContext], bool]
InterceptorFn = Callable[[ActionContext, NextFunction], MiddlewareResult[Any]]
PipeFn = Callable[[ActionContext], ActionContext]


def _wrap_interceptor(
    interceptor: InterceptorFn,
    context: ActionContext,
    next_fn: Callable[[], MiddlewareResult[Any]],
) -> Callable[[], MiddlewareResult[Any]]:
    """Wrap an interceptor around a next() callable (onion model)."""

    def wrapped() -> MiddlewareResult[Any]:
        return interceptor(context, next_fn)

    return wrapped


class CompiledPipeline:
    """Pre-compiled enhancer pipeline built once at registration.

    Inspired by NestJS's ``RouterExecutionContext.create()``: the enhancer
    chain (pipes → guards → interceptors → handler) is built once at
    registration time and executed per-request without rebuilding.

    - **Pipes**: input transform/validate. Each pipe receives the context
      and returns a (possibly transformed) context for the next stage.
    - **Guards**: binary allow/deny. If any guard returns False, the
      pipeline short-circuits with ``MiddlewareResult(ok=False, error)``.
    - **Interceptors**: before/after wrappers. Each interceptor receives
      the context and a ``next()`` callable, analogous to tRPC middleware.
    - **Handler**: the terminal function that produces the result.

    Mapping to existing aiZee modules:
    - Guards = ``guardian.py`` (binary allow/deny)
    - Interceptors = ``audit.py`` + ``budget.py`` (before/after observation)
    - Pipes = ``schemas.py`` validation (input transform/validate)
    """

    def __init__(self) -> None:
        self._guards: list[GuardFn] = []
        self._interceptors: list[InterceptorFn] = []
        self._pipes: list[PipeFn] = []
        self._handler: HandlerFn | None = None
        self._compiled: bool = False
        self._compiled_fn: Callable[[ActionContext], MiddlewareResult[Any]] | None = None

    def add_guard(self, fn: GuardFn) -> None:
        """Register a guard (binary allow/deny)."""
        self._guards.append(fn)
        self._compiled = False

    def add_interceptor(self, fn: InterceptorFn) -> None:
        """Register an interceptor (before/after wrapper)."""
        self._interceptors.append(fn)
        self._compiled = False

    def add_pipe(self, fn: PipeFn) -> None:
        """Register a pipe (input transform/validate)."""
        self._pipes.append(fn)
        self._compiled = False

    def set_handler(self, fn: HandlerFn) -> None:
        """Set the terminal handler that produces the final result."""
        self._handler = fn
        self._compiled = False

    @property
    def is_compiled(self) -> bool:
        """True if the pipeline has been compiled into a single callable."""
        return self._compiled

    @property
    def guard_count(self) -> int:
        return len(self._guards)

    @property
    def interceptor_count(self) -> int:
        return len(self._interceptors)

    @property
    def pipe_count(self) -> int:
        return len(self._pipes)

    def compile(self) -> None:
        """Pre-build the enhancer chain into a single callable.

        After compilation, ``execute()`` runs the pre-built function without
        rebuilding the chain on each call.
        """
        if self._handler is None:
            raise AizeeError(
                error_code="PIPELINE_NOT_CONFIGURED",
                message="Cannot compile pipeline without a handler",
                severity=ErrorSeverity.HIGH,
            )
        guards = list(self._guards)
        pipes = list(self._pipes)
        interceptors = list(self._interceptors)
        handler = self._handler

        def run(context: ActionContext) -> MiddlewareResult[Any]:
            try:
                # 1. Pipes — transform/validate input (NestJS pipes run first)
                ctx = context
                for pipe in pipes:
                    ctx = pipe(ctx)

                # 2. Guards — binary allow/deny (short-circuit on False)
                for guard in guards:
                    if not guard(ctx):
                        return MiddlewareResult(
                            ok=False,
                            error=AizeeError(
                                error_code="GUARD_DENIED",
                                message="Guard denied access",
                                severity=ErrorSeverity.HIGH,
                                context={"action_type": ctx.action_type},
                            ),
                        )

                # 3. Interceptors — onion model wrapping the handler
                def terminal() -> MiddlewareResult[Any]:
                    return handler(ctx)

                chain: Callable[[], MiddlewareResult[Any]] = terminal
                for interceptor in reversed(interceptors):
                    chain = _wrap_interceptor(interceptor, ctx, chain)
                return chain()
            except AizeeError as e:
                return MiddlewareResult(ok=False, error=e)
            except Exception as e:  # intentional: wrap any error into MiddlewareResult
                return MiddlewareResult(ok=False, error=normalize_error(e))

        self._compiled_fn = run
        self._compiled = True

    def execute(self, context: ActionContext) -> MiddlewareResult[Any]:
        """Execute the pre-compiled pipeline.

        If the pipeline has not been compiled yet, compiles it on first call
        (lazy compilation). Subsequent calls use the cached compiled function.
        """
        if not self._compiled or self._compiled_fn is None:
            self.compile()
        assert self._compiled_fn is not None
        return self._compiled_fn(context)
