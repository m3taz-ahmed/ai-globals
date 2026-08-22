"""Tests for the flat middleware pipeline and pre-compiled enhancer pipeline.

Covers Pattern 4 (tRPC-style flat middleware array + recursive execution)
and Pattern 5 (NestJS-style pre-compiled enhancer pipeline) from
``runtime/middleware.py``.
"""

from __future__ import annotations

import pytest

from runtime.middleware import (
    ActionContext,
    CompiledPipeline,
    EnhancerType,
    MiddlewarePipeline,
    MiddlewareResult,
    normalize_error,
)
from runtime.schemas import AizeeError, ErrorSeverity

# ---------------------------------------------------------------------------
# ActionContext
# ---------------------------------------------------------------------------


class TestActionContext:
    def test_default_context(self) -> None:
        ctx = ActionContext(action_type="read")
        assert ctx.action_type == "read"
        assert ctx.data == {}
        assert ctx.dry_run is False
        assert ctx.session_id is None
        assert ctx.overrides == {}

    def test_context_with_data(self) -> None:
        ctx = ActionContext(
            action_type="write",
            data={"key": "value"},
            dry_run=True,
            session_id="sess-1",
            overrides={"user": "admin"},
        )
        assert ctx.action_type == "write"
        assert ctx.data["key"] == "value"
        assert ctx.dry_run is True
        assert ctx.session_id == "sess-1"
        assert ctx.overrides["user"] == "admin"


# ---------------------------------------------------------------------------
# MiddlewareResult
# ---------------------------------------------------------------------------


class TestMiddlewareResult:
    def test_ok_result(self) -> None:
        result = MiddlewareResult(ok=True, data={"output": 42})
        assert result.ok is True
        assert result.data == {"output": 42}
        assert result.error is None

    def test_error_result(self) -> None:
        err = AizeeError(error_code="TEST", message="fail", severity=ErrorSeverity.LOW)
        result: MiddlewareResult[None] = MiddlewareResult(ok=False, error=err)
        assert result.ok is False
        assert result.data is None
        assert result.error is not None
        assert result.error.error_code == "TEST"


# ---------------------------------------------------------------------------
# normalize_error
# ---------------------------------------------------------------------------


class TestNormalizeError:
    def test_aizee_error_passthrough(self) -> None:
        err = AizeeError(error_code="CUSTOM", message="custom", severity=ErrorSeverity.LOW)
        result = normalize_error(err)
        assert result is err

    def test_generic_exception_wrapped(self) -> None:
        result = normalize_error(ValueError("boom"))
        assert isinstance(result, AizeeError)
        assert result.error_code == "INTERNAL"
        assert "boom" in str(result)

    def test_empty_message_uses_class_name(self) -> None:
        result = normalize_error(RuntimeError())
        assert isinstance(result, AizeeError)
        assert "RuntimeError" in str(result)


# ---------------------------------------------------------------------------
# MiddlewarePipeline (Pattern 4)
# ---------------------------------------------------------------------------


class TestMiddlewarePipeline:
    def test_empty_pipeline_runs_handler(self) -> None:
        pipe = MiddlewarePipeline()
        ctx = ActionContext(action_type="read")
        result = pipe.execute(ctx, lambda c: MiddlewareResult(ok=True, data="done"))
        assert result.ok is True
        assert result.data == "done"

    def test_has_middlewares_false_initially(self) -> None:
        pipe = MiddlewarePipeline()
        assert pipe.has_middlewares() is False

    def test_has_middlewares_true_after_use(self) -> None:
        pipe = MiddlewarePipeline()
        pipe.use(lambda ctx, next_fn: next_fn())
        assert pipe.has_middlewares() is True

    def test_middleware_calls_next(self) -> None:
        pipe = MiddlewarePipeline()
        order: list[str] = []

        def mw_a(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            order.append("a:before")
            res = next_fn()
            order.append("a:after")
            return res

        def mw_b(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            order.append("b:before")
            res = next_fn()
            order.append("b:after")
            return res

        pipe.use(mw_a)
        pipe.use(mw_b)
        ctx = ActionContext(action_type="read")
        result = pipe.execute(ctx, lambda c: MiddlewareResult(ok=True, data="ok"))
        assert result.ok is True
        assert order == ["a:before", "b:before", "b:after", "a:after"]

    def test_middleware_short_circuits(self) -> None:
        pipe = MiddlewarePipeline()
        called: list[str] = []

        def blocking_mw(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            called.append("block")
            return MiddlewareResult(ok=False, error=AizeeError(
                error_code="BLOCKED", message="blocked", severity=ErrorSeverity.HIGH,
            ))

        def passthrough_mw(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            called.append("pass")
            return next_fn()

        pipe.use(blocking_mw)
        pipe.use(passthrough_mw)
        ctx = ActionContext(action_type="write")
        result = pipe.execute(ctx, lambda c: MiddlewareResult(ok=True, data="done"))
        assert result.ok is False
        assert "pass" not in called  # second middleware never reached

    def test_handler_exception_wrapped(self) -> None:
        pipe = MiddlewarePipeline()
        ctx = ActionContext(action_type="read")

        def boom_handler(c: ActionContext) -> MiddlewareResult:  # type: ignore[type-arg]
            raise ValueError("handler exploded")

        result = pipe.execute(ctx, boom_handler)
        assert result.ok is False
        assert result.error is not None
        assert result.error.error_code == "INTERNAL"

    def test_middleware_aizee_error_wrapped(self) -> None:
        pipe = MiddlewarePipeline()
        ctx = ActionContext(action_type="read")

        def error_mw(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            raise AizeeError(
                error_code="CUSTOM", message="custom", severity=ErrorSeverity.MEDIUM,
            )

        pipe.use(error_mw)
        result = pipe.execute(ctx, lambda c: MiddlewareResult(ok=True, data="ok"))
        assert result.ok is False
        assert result.error is not None
        assert result.error.error_code == "CUSTOM"

    def test_middleware_can_modify_overrides(self) -> None:
        pipe = MiddlewarePipeline()

        def override_mw(ctx: ActionContext, next_fn) -> MiddlewareResult:  # type: ignore[type-arg]
            ctx.overrides["injected"] = True
            return next_fn()

        pipe.use(override_mw)
        ctx = ActionContext(action_type="read")
        captured: dict[str, bool] = {}

        def handler(c: ActionContext) -> MiddlewareResult:  # type: ignore[type-arg]
            captured["injected"] = c.overrides.get("injected", False)
            return MiddlewareResult(ok=True, data="ok")

        pipe.execute(ctx, handler)
        assert captured["injected"] is True


# ---------------------------------------------------------------------------
# CompiledPipeline (Pattern 5)
# ---------------------------------------------------------------------------


class TestCompiledPipeline:
    def test_compile_requires_handler(self) -> None:
        pipeline = CompiledPipeline()
        with pytest.raises(AizeeError, match="handler"):
            pipeline.compile()

    def test_is_compiled_false_initially(self) -> None:
        pipeline = CompiledPipeline()
        assert pipeline.is_compiled is False

    def test_compile_sets_compiled(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        pipeline.compile()
        assert pipeline.is_compiled is True

    def test_lazy_compile_on_execute(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        assert pipeline.is_compiled is False
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is True
        assert pipeline.is_compiled is True

    def test_pipe_transforms_context(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.add_pipe(lambda c: ActionContext(
            action_type=c.action_type, data={"transformed": True},
        ))
        captured: dict[str, bool] = {}
        pipeline.set_handler(lambda c: MiddlewareResult(
            ok=True, data=captured.update({"has_transformed": c.data.get("transformed", False)}) or "ok",
        ))
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is True
        assert captured["has_transformed"] is True

    def test_guard_denies(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.add_guard(lambda c: False)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        ctx = ActionContext(action_type="write")
        result = pipeline.execute(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.error_code == "GUARD_DENIED"

    def test_guard_allows(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.add_guard(lambda c: True)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is True

    def test_multiple_guards_all_must_pass(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.add_guard(lambda c: True)
        pipeline.add_guard(lambda c: False)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is False

    def test_interceptor_before_after(self) -> None:
        pipeline = CompiledPipeline()
        order: list[str] = []

        def interceptor(ctx: ActionContext, next_fn):  # type: ignore[type-arg]
            order.append("before")
            res = next_fn()
            order.append("after")
            return res

        pipeline.add_interceptor(interceptor)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is True
        assert order == ["before", "after"]

    def test_multiple_interceptors_onion(self) -> None:
        pipeline = CompiledPipeline()
        order: list[str] = []

        def outer(ctx: ActionContext, next_fn):  # type: ignore[type-arg]
            order.append("outer:before")
            res = next_fn()
            order.append("outer:after")
            return res

        def inner(ctx: ActionContext, next_fn):  # type: ignore[type-arg]
            order.append("inner:before")
            res = next_fn()
            order.append("inner:after")
            return res

        pipeline.add_interceptor(outer)
        pipeline.add_interceptor(inner)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        ctx = ActionContext(action_type="read")
        pipeline.execute(ctx)
        assert order == ["outer:before", "inner:before", "inner:after", "outer:after"]

    def test_pipe_guard_interceptor_order(self) -> None:
        """Pipes run first, then guards, then interceptors, then handler."""
        pipeline = CompiledPipeline()
        order: list[str] = []

        def pipe_fn(c: ActionContext) -> ActionContext:
            order.append("pipe")
            return c

        def guard_fn(c: ActionContext) -> bool:
            order.append("guard")
            return True

        def interceptor_fn(ctx: ActionContext, next_fn):  # type: ignore[type-arg]
            order.append("interceptor:before")
            return next_fn()

        def handler_fn(c: ActionContext) -> MiddlewareResult:  # type: ignore[type-arg]
            order.append("handler")
            return MiddlewareResult(ok=True, data="ok")

        pipeline.add_pipe(pipe_fn)
        pipeline.add_guard(guard_fn)
        pipeline.add_interceptor(interceptor_fn)
        pipeline.set_handler(handler_fn)
        ctx = ActionContext(action_type="read")
        pipeline.execute(ctx)
        assert order == ["pipe", "guard", "interceptor:before", "handler"]

    def test_counts(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.add_guard(lambda c: True)
        pipeline.add_guard(lambda c: True)
        pipeline.add_interceptor(lambda ctx, next_fn: next_fn())  # type: ignore[type-arg]
        pipeline.add_pipe(lambda c: c)
        pipeline.add_pipe(lambda c: c)
        pipeline.add_pipe(lambda c: c)
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        assert pipeline.guard_count == 2
        assert pipeline.interceptor_count == 1
        assert pipeline.pipe_count == 3

    def test_add_invalidates_compilation(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.set_handler(lambda c: MiddlewareResult(ok=True, data="ok"))
        pipeline.compile()
        assert pipeline.is_compiled is True
        pipeline.add_guard(lambda c: True)
        assert pipeline.is_compiled is False

    def test_handler_exception_wrapped(self) -> None:
        pipeline = CompiledPipeline()
        pipeline.set_handler(lambda c: (_ for _ in ()).throw(ValueError("boom")))  # type: ignore[misc]
        ctx = ActionContext(action_type="read")
        result = pipeline.execute(ctx)
        assert result.ok is False
        assert result.error is not None
        assert result.error.error_code == "INTERNAL"


# ---------------------------------------------------------------------------
# EnhancerType enum
# ---------------------------------------------------------------------------


class TestEnhancerType:
    def test_values(self) -> None:
        assert EnhancerType.GUARD.value == "guard"
        assert EnhancerType.INTERCEPTOR.value == "interceptor"
        assert EnhancerType.PIPE.value == "pipe"

    def test_from_string(self) -> None:
        assert EnhancerType("guard") is EnhancerType.GUARD
        assert EnhancerType("interceptor") is EnhancerType.INTERCEPTOR
        assert EnhancerType("pipe") is EnhancerType.PIPE
