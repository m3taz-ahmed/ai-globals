"""Tests for runtime/saga_compensation.py — saga compensation."""

from __future__ import annotations

from runtime.saga_compensation import CompensationSaga


class TestCompensationSaga:
    def test_all_steps_succeed(self) -> None:
        saga = CompensationSaga()
        saga.add_step("s1", forward=lambda: "r1")
        saga.add_step("s2", forward=lambda: "r2")
        result = saga.execute()
        assert result.success is True
        assert result.completed_steps == ["s1", "s2"]

    def test_failure_triggers_compensation(self) -> None:
        compensated: list[str] = []
        saga = CompensationSaga()
        saga.add_step("s1", forward=lambda: "r1", compensate=lambda r: compensated.append(r))
        saga.add_step("s2", forward=lambda: "r2", compensate=lambda r: compensated.append(r))

        def fail() -> None:
            raise ValueError("fail")

        saga.add_step("s3", forward=fail, compensate=lambda r: compensated.append(r))
        result = saga.execute()
        assert result.success is False
        assert result.failed_step == "s3"
        saga.compensate()
        assert "r1" in compensated
        assert "r2" in compensated

    def test_no_compensation_on_success(self) -> None:
        saga = CompensationSaga()
        saga.add_step("s1", forward=lambda: "r1", compensate=lambda r: None)
        result = saga.execute()
        assert result.success is True
        comp_result = saga.compensate()
        assert comp_result.compensated is True

    def test_empty_saga_succeeds(self) -> None:
        saga = CompensationSaga()
        result = saga.execute()
        assert result.success is True
        assert result.completed_steps == []

    def test_compensate_best_effort(self) -> None:
        saga = CompensationSaga()
        saga.add_step("s1", forward=lambda: "r1", compensate=lambda r: (_ for _ in ()).throw(Exception("comp fail")))
        saga.execute()
        # Should not raise even if compensation fails
        saga.compensate()
