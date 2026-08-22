"""Tests for runtime/enums.py."""

from __future__ import annotations

from enum import Enum

from runtime.enums import (
    ActionResultStatus,
    Decision,
    ExceedAction,
    SagaStatus,
    StepType,
)


class TestStepType:
    def test_step_type_values(self) -> None:
        # Assert
        assert StepType.REQ.value == "REQ"
        assert StepType.CMD.value == "CMD"
        assert StepType.PROHIBIT.value == "PROHIBIT"

    def test_step_type_is_str_enum(self) -> None:
        # Assert
        assert isinstance(StepType.REQ, str)
        assert isinstance(StepType.REQ, Enum)

    def test_step_type_string_comparison(self) -> None:
        # Assert — str enum compares directly to string value
        assert StepType.REQ == "REQ"
        assert StepType.CMD == "CMD"

    def test_step_type_membership(self) -> None:
        # Assert
        assert StepType.REQ in StepType
        assert StepType.CMD in StepType
        assert StepType.PROHIBIT in StepType

    def test_step_type_has_three_members(self) -> None:
        # Assert
        assert len(list(StepType)) == 3


class TestSagaStatus:
    def test_saga_status_values(self) -> None:
        # Assert
        assert SagaStatus.RUNNING.value == "running"
        assert SagaStatus.COMPLETED.value == "completed"
        assert SagaStatus.COMPENSATED.value == "compensated"
        assert SagaStatus.FAILED.value == "failed"

    def test_saga_status_is_str_enum(self) -> None:
        # Assert
        assert isinstance(SagaStatus.RUNNING, str)
        assert isinstance(SagaStatus.RUNNING, Enum)

    def test_saga_status_string_comparison(self) -> None:
        # Assert
        assert SagaStatus.RUNNING == "running"
        assert SagaStatus.FAILED == "failed"

    def test_saga_status_has_four_members(self) -> None:
        # Assert
        assert len(list(SagaStatus)) == 4


class TestDecision:
    def test_decision_values(self) -> None:
        # Assert
        assert Decision.ALLOW.value == "allow"
        assert Decision.ASK.value == "ask"
        assert Decision.DENY.value == "deny"

    def test_decision_is_str_enum(self) -> None:
        # Assert
        assert isinstance(Decision.ALLOW, str)
        assert isinstance(Decision.ALLOW, Enum)

    def test_decision_string_comparison(self) -> None:
        # Assert
        assert Decision.ALLOW == "allow"
        assert Decision.DENY == "deny"

    def test_decision_has_three_members(self) -> None:
        # Assert
        assert len(list(Decision)) == 3


class TestActionResultStatus:
    def test_action_result_status_values(self) -> None:
        # Assert
        assert ActionResultStatus.OK.value == "ok"
        assert ActionResultStatus.ALLOWED.value == "allowed"
        assert ActionResultStatus.DENIED.value == "denied"
        assert ActionResultStatus.ERROR.value == "error"
        assert ActionResultStatus.TIMEOUT.value == "timeout"

    def test_action_result_status_is_str_enum(self) -> None:
        # Assert
        assert isinstance(ActionResultStatus.OK, str)
        assert isinstance(ActionResultStatus.OK, Enum)

    def test_action_result_status_has_eleven_members(self) -> None:
        # Assert
        assert len(list(ActionResultStatus)) == 11


class TestExceedAction:
    def test_exceed_action_values(self) -> None:
        # Assert
        assert ExceedAction.WARN.value == "warn"
        assert ExceedAction.FALLBACK.value == "fallback"
        assert ExceedAction.BLOCK.value == "block"

    def test_exceed_action_is_str_enum(self) -> None:
        # Assert
        assert isinstance(ExceedAction.WARN, str)
        assert isinstance(ExceedAction.WARN, Enum)

    def test_exceed_action_has_three_members(self) -> None:
        # Assert
        assert len(list(ExceedAction)) == 3


class TestEnumCrossModule:
    def test_all_enums_are_str_subclass(self) -> None:
        # Assert — all enums inherit from str for JSON serialization
        assert all(isinstance(m.value, str) for m in StepType)
        assert all(isinstance(m.value, str) for m in SagaStatus)
        assert all(isinstance(m.value, str) for m in Decision)
        assert all(isinstance(m.value, str) for m in ActionResultStatus)
        assert all(isinstance(m.value, str) for m in ExceedAction)
