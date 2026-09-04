"""Tests for the flat middleware pipeline.

Covers Pattern 4 (tRPC-style flat middleware array + recursive execution)
from ``runtime/middleware.py``.
"""

from __future__ import annotations

from runtime.middleware import (
    ActionContext,
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


