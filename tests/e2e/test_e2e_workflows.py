"""End-to-end tests for aiZee core workflows.

Tests the full lifecycle: kernel initialization → persona detection →
policy evaluation → workflow execution → memory ingestion → search.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.kernel import Kernel


@pytest.fixture
def kernel(tmp_path: Path) -> Kernel:
    """Create a kernel with a temporary project root."""
    # Create minimal directory structure
    (tmp_path / "rules").mkdir(exist_ok=True)
    (tmp_path / "workflows").mkdir(exist_ok=True)
    (tmp_path / "skills").mkdir(exist_ok=True)
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "brain").mkdir(exist_ok=True)
    (tmp_path / "runtime" / "policies").mkdir(parents=True, exist_ok=True)
    # Create a policy that allows Read actions
    (tmp_path / "runtime" / "policies" / "default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        "  - name: deny-rm\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
    )
    return Kernel(root=tmp_path, project_root=tmp_path)


class TestKernelLifecycle:
    """E2E: Kernel initialization and status."""

    def test_kernel_initializes_successfully(self, kernel: Kernel) -> None:
        status = kernel.status()
        assert "version" in status
        assert "personas" in status
        assert "workflows" in status
        assert "budgets" in status

    def test_kernel_has_default_budgets(self, kernel: Kernel) -> None:
        status = kernel.status()
        assert "global" in status["budgets"]
        assert "session" in status["budgets"]


class TestPolicyEvaluation:
    """E2E: Policy evaluation through the full gate pipeline."""

    def test_allowed_action_passes_all_gates(self, kernel: Kernel) -> None:
        result = kernel.act("Read", tokens=1, approved=True)
        assert result["ok"] is True
        assert "decision" in result

    def test_budget_exceeded_blocks_action(self, kernel: Kernel) -> None:
        from runtime.budget import Budget

        kernel.budget.budgets["session"] = Budget(max_tokens=2, period="session")
        assert kernel.act("Read", tokens=1, approved=True)["ok"] is True
        assert kernel.act("Read", tokens=1, approved=True)["ok"] is False

    def test_fresh_context_resets_budget(self, kernel: Kernel) -> None:
        from runtime.budget import Budget

        kernel.budget.budgets["session"] = Budget(max_tokens=2, period="session")
        assert kernel.act("Read", tokens=1, approved=True)["ok"] is True
        assert not kernel.act("Read", tokens=1, approved=True)["ok"]
        assert kernel.act("Read", tokens=1, approved=True, fresh_context=True)["ok"]


class TestChatLifecycle:
    """E2E: Chat session lifecycle."""

    def test_chat_creates_session_and_replies(self, kernel: Kernel) -> None:
        result = kernel.chat_message("hello")
        assert result["ok"] is True
        assert "reply" in result

    def test_fresh_chat_creates_new_session(self, kernel: Kernel) -> None:
        result = kernel.chat_message("hello", fresh_context=True)
        assert result["ok"] is True
        assert "session_id" in result


class TestMemoryLifecycle:
    """E2E: Memory add → search → invalidate lifecycle."""

    def test_add_and_search_memory(self, kernel: Kernel) -> None:
        from memory.store import MemoryStore

        store = MemoryStore(kernel.root)
        mem = store.add("semantic", "Python is a programming language", source="test")
        results = store.search("Python")
        assert any(r.id == mem.id for r in results)

    def test_invalidate_memory(self, kernel: Kernel) -> None:
        from memory.store import MemoryStore

        store = MemoryStore(kernel.root)
        mem = store.add("semantic", "Temporary fact", source="test")
        store.invalidate(mem.id)
        results = store.search("Temporary")
        assert not any(r.id == mem.id for r in results)


class TestWorkflowLifecycle:
    """E2E: Workflow listing and execution."""

    def test_list_workflows_returns_list(self, kernel: Kernel) -> None:
        workflows = kernel.list_workflows()
        assert isinstance(workflows, list)

    def test_run_nonexistent_workflow_returns_error(self, kernel: Kernel) -> None:
        result = kernel.run_workflow("nonexistent", {})
        assert result["ok"] is False
        assert "error" in result or "not found" in result.get("error", "")


class TestMetricsExport:
    """E2E: Prometheus metrics export."""

    def test_metrics_export_contains_expected_keys(self, kernel: Kernel) -> None:
        from runtime.metrics import format_metrics

        output = format_metrics(kernel)
        assert "aizee_workflows_total" in output
        assert "aizee_rules_total" in output
        assert "aizee_budgets_total" in output
