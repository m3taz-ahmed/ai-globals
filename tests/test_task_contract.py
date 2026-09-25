"""Tests for runtime/task_contract — enforced decompose/verify/review lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.task_contract import (
    PlanStatus,
    TaskContractError,
    TaskContractManager,
    TaskPlan,
    TaskStatus,
    classify_prompt,
)


def _mgr(tmp_path: Path) -> TaskContractManager:
    return TaskContractManager(tmp_path)


def _plan(mgr: TaskContractManager, tasks: list[dict] | None = None) -> TaskPlan:
    return mgr.decompose(
        "Test plan",
        "build a thing",
        tasks
        or [
            {
                "id": "impl",
                "title": "Implement",
                "files": ["src/x.py"],
                "acceptance": ["unit tests pass"],
                "produces": "src/x.py",
            },
            {
                "id": "verify",
                "title": "Verify",
                "depends_on": ["impl"],
                "files": ["tests/test_x.py"],
                "acceptance": ["coverage ok"],
            },
        ],
        "standard",
        "multi-step feature",
    )


class TestClassifier:
    def test_trivial_typo(self) -> None:
        assert classify_prompt("fix this typo in readme")["level"] == "trivial"

    def test_standard_build(self) -> None:
        result = classify_prompt("refactor the parser module")
        assert result["level"] in ("standard", "complex")

    def test_complex_multi_domain(self) -> None:
        result = classify_prompt(
            "build the auth system with database migration, then deploy the platform"
        )
        assert result["level"] == "complex"

    def test_arabic_signals(self) -> None:
        result = classify_prompt("اعمل سيستم auth وبعد كده اعمل deploy")
        assert result["level"] in ("standard", "complex")

    def test_empty_prompt_is_trivial(self) -> None:
        assert classify_prompt("   ")["level"] == "trivial"


class TestClassificationRecord:
    def test_records_to_jsonl(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        rec = mgr.record_classification("fix typo", "trivial", "single typo")
        assert rec["level"] == "trivial"
        assert (mgr.classifications_path).exists()
        line = mgr.classifications_path.read_text(encoding="utf-8").strip()
        assert json.loads(line)["reason"] == "single typo"

    def test_reason_required(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError) as exc:
            _mgr(tmp_path).record_classification("x", "trivial", "  ")
        assert exc.value.error_code == "CLASSIFICATION_REASON_REQUIRED"

    def test_invalid_level(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError) as exc:
            _mgr(tmp_path).record_classification("x", "huge", "reason")
        assert exc.value.error_code == "INVALID_CLASSIFICATION"

    def test_disagreement_flag(self, tmp_path: Path) -> None:
        rec = _mgr(tmp_path).record_classification(
            "build auth with database migration and deploy", "trivial", "trust me"
        )
        assert rec["disagreement"] is True


class TestDecompose:
    def test_creates_plan_file(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        plan = _plan(mgr)
        assert plan.status == PlanStatus.ACTIVE
        assert mgr.plan_path.exists()

    def test_second_plan_rejected(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            _plan(mgr)
        assert exc.value.error_code == "PLAN_EXISTS"

    def test_bad_id_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError) as exc:
            _plan(_mgr(tmp_path), [{"id": "Bad ID!", "title": "x", "acceptance": ["a"]}])
        assert exc.value.error_code == "INVALID_PLAN"

    def test_unknown_dep_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError) as exc:
            _plan(
                _mgr(tmp_path),
                [{"id": "a", "title": "x", "acceptance": ["a"], "depends_on": ["ghost"]}],
            )
        assert exc.value.error_code == "INVALID_PLAN"

    def test_cycle_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError) as exc:
            _plan(
                _mgr(tmp_path),
                [
                    {"id": "a", "title": "x", "acceptance": ["a"], "depends_on": ["b"]},
                    {"id": "b", "title": "y", "acceptance": ["b"], "depends_on": ["a"]},
                ],
            )
        assert exc.value.error_code == "INVALID_PLAN"

    def test_missing_acceptance_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(TaskContractError):
            _plan(_mgr(tmp_path), [{"id": "a", "title": "x"}])

    def test_invalid_classification(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        with pytest.raises(TaskContractError) as exc:
            mgr.decompose("t", "p", [{"id": "a", "title": "x", "acceptance": ["a"]}], "huge", "r")
        assert exc.value.error_code == "INVALID_PLAN"


class TestLifecycle:
    def test_full_lifecycle(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        mgr.verify("impl", "3 tests passed")
        mgr.complete("impl")
        assert mgr.status()["next_pending"] == "verify"
        mgr.start("verify")
        mgr.verify("verify", "coverage 95%")
        mgr.complete("verify")
        report = mgr.finish()
        assert report["tasks_done"] == 2
        assert report["evidence_gaps"] == []
        plan = mgr.load()
        assert plan is not None and plan.status == PlanStatus.DONE

    def test_start_requires_pending(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.start("verify")
        assert exc.value.error_code == "ALREADY_ACTIVE"

    def test_dep_blocked(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.start("verify")
        assert exc.value.error_code == "DEP_BLOCKED"

    def test_verify_requires_in_progress(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.verify("impl", "evidence")
        assert exc.value.error_code == "TASK_NOT_IN_PROGRESS"

    def test_verify_requires_evidence(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.verify("impl", "   ")
        assert exc.value.error_code == "EVIDENCE_REQUIRED"

    def test_complete_requires_verified(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.complete("impl")
        assert exc.value.error_code == "NOT_VERIFIED"

    def test_verify_runs_cmd(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(
            mgr,
            [
                {
                    "id": "impl",
                    "title": "x",
                    "acceptance": ["ok"],
                    "verify_cmd": f'"{__import__("sys").executable}" -c "print(1)"',
                }
            ],
        )
        mgr.start("impl")
        result = mgr.verify("impl", "", run_cmd=True)
        assert result["cmd"]["exit_code"] == 0

    def test_verify_cmd_failure_blocks(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(
            mgr,
            [
                {
                    "id": "impl",
                    "title": "x",
                    "acceptance": ["ok"],
                    "verify_cmd": f'"{__import__("sys").executable}" -c "import sys; sys.exit(3)"',
                }
            ],
        )
        mgr.start("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.verify("impl", "", run_cmd=True)
        assert exc.value.error_code == "VERIFY_CMD_FAILED"

    def test_review_artifact_written(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        mgr.verify("impl", "evidence here")
        artifact = mgr.review_dir / "impl.md"
        assert artifact.exists()
        assert "evidence here" in artifact.read_text(encoding="utf-8")

    def test_block_clears_active(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        mgr.block("impl", "waiting on API spec")
        plan = mgr.load()
        assert plan is not None
        assert plan.active_task_id == ""
        assert plan.task("impl").status == TaskStatus.BLOCKED

    def test_finish_requires_all_done(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.finish()
        assert exc.value.error_code == "NOT_FINISHED"

    def test_final_report_written(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        mgr.verify("impl", "ok")
        mgr.complete("impl")
        mgr.start("verify")
        mgr.verify("verify", "ok")
        mgr.complete("verify")
        report = mgr.finish()
        assert (mgr.review_dir / f"{report['plan_id']}-final.json").exists()

    def test_abandon(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.abandon("requirements changed")
        plan = mgr.load()
        assert plan is not None and plan.status == PlanStatus.ABANDONED

    def test_no_plan_errors(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        with pytest.raises(TaskContractError) as exc:
            mgr.start("x")
        assert exc.value.error_code == "NO_ACTIVE_PLAN"


class TestAmend:
    def test_add_task(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        plan = mgr.amend(
            [{"op": "add", "task": {"id": "docs", "title": "Docs", "acceptance": ["readme"]}}],
            "scope grew",
        )
        assert plan.task("docs").status == TaskStatus.PENDING
        assert plan.amendments[0]["reason"] == "scope grew"

    def test_reason_required(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.amend([], "  ")
        assert exc.value.error_code == "AMEND_REASON_REQUIRED"

    def test_cannot_update_done(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        mgr.verify("impl", "ok")
        mgr.complete("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.amend([{"op": "update", "id": "impl", "task": {"title": "new"}}], "late change")
        assert exc.value.error_code == "AMEND_INVALID"

    def test_remove_with_dependents_rejected(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.amend([{"op": "remove", "id": "impl"}], "shrink")
        assert exc.value.error_code == "AMEND_INVALID"

    def test_unknown_op_rejected(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        with pytest.raises(TaskContractError) as exc:
            mgr.amend([{"op": "frobnicate", "id": "impl"}], "why not")
        assert exc.value.error_code == "AMEND_INVALID"


class TestScopeEnforcement:
    def test_no_plan_allows(self, tmp_path: Path) -> None:
        assert _mgr(tmp_path).scope_check("src/any.py")["allowed"] is True

    def test_inside_scope(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        assert mgr.scope_check("src/x.py")["allowed"] is True

    def test_outside_scope_warns(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        result = mgr.scope_check("src/other.py")
        assert result["allowed"] is False
        assert result["task"] == "impl"

    def test_strict_mode_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIZEE_TASK_STRICT", "1")
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        with pytest.raises(TaskContractError) as exc:
            mgr.scope_check("src/other.py")
        assert exc.value.error_code == "SCOPE_VIOLATION"

    def test_hook_observe_edit_warns(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        mgr.start("impl")
        warning = mgr.hook_observe_edit("src/other.py")
        assert "scope warning" in warning
        assert mgr.hook_observe_edit("src/x.py") == ""

    def test_hook_inject_block(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        assert mgr.hook_inject_block() == ""
        _plan(mgr)
        assert "Next pending" in mgr.hook_inject_block()
        mgr.start("impl")
        block = mgr.hook_inject_block()
        assert "impl" in block and "Declared scope" in block


class TestStatus:
    def test_empty(self, tmp_path: Path) -> None:
        assert _mgr(tmp_path).status()["plan"] is None

    def test_active_plan_status(self, tmp_path: Path) -> None:
        mgr = _mgr(tmp_path)
        _plan(mgr)
        status = mgr.status()
        assert status["status"] == "active"
        assert len(status["tasks"]) == 2
        assert status["strict"] is False


class TestKernelWiring:
    def test_kernel_has_task_contract(self, tmp_path: Path) -> None:
        from runtime.kernel import Kernel

        k = Kernel(project_root=tmp_path)
        assert isinstance(k.task_contract, TaskContractManager)
        assert k.task_contract.project_root == tmp_path
