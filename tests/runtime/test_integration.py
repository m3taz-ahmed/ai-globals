
import pytest

from runtime.kernel import Kernel


@pytest.fixture
def k(tmp_path):
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        "  - name: deny-rm\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
    )
    (tmp_path / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n2. [CMD] Step two.\n"
    )
    return Kernel(tmp_path)


def test_policy_audit_and_budget(k, tmp_path):
    result = k.act("Read", tokens=10)
    assert result["ok"]
    assert result["decision"]["decision"] == "allow"
    assert (tmp_path / "state" / "budget.json").exists()
    assert (tmp_path / "state" / "audit.log").exists()


def test_workflow_durable_state(k, tmp_path):
    result = k.run_workflow("test", {"project": "demo"})
    assert result["ok"]
    assert "run_id" in result
    assert len(result["steps"]) == 2
    assert (tmp_path / "state" / "workflow.db").exists()
    run = k.workflows.get_run(result["run_id"])
    assert run is not None
    assert run["workflow_id"] == "test"
