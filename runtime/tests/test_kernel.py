from pathlib import Path

from runtime.kernel import Kernel


def _kernel(tmp_path: Path) -> Kernel:
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


def test_status(tmp_path):
    k = _kernel(tmp_path)
    status = k.status()
    assert status["version"] == "4.21.0"
    assert "workflows" in status


def test_act_read_allowed(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("Read")
    assert result["ok"]
    assert result["decision"]["decision"] == "allow"


def test_act_write_asked(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("edit")
    assert result["ok"]
    assert result["decision"]["decision"] == "ask"


def test_act_destructive_denied(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("rm", command="rm -rf /")
    assert not result["ok"]
