from pathlib import Path

import config
from runtime.budget import Budget
from runtime.chat import ChatSession
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
    assert status["version"] == config.VERSION
    assert "workflows" in status


def test_act_read_allowed(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("Read")
    assert result["ok"]
    assert result["decision"]["decision"] == "allow"


def test_act_write_asked(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("edit")
    assert not result["ok"]
    assert result["decision"]["decision"] == "ask"
    assert result["requires_approval"]


def test_act_write_approved(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("edit", approved=True)
    assert result["ok"]
    assert result["decision"]["decision"] == "ask"


def test_act_destructive_denied(tmp_path):
    k = _kernel(tmp_path)
    result = k.act("rm", command="rm -rf /")
    assert not result["ok"]


def test_act_cached_after_approval(tmp_path):
    k = _kernel(tmp_path)
    first = k.act("write")
    assert not first["ok"]
    assert first["requires_approval"]

    approved = k.act("write", approved=True)
    assert approved["ok"]
    assert approved["decision"]["decision"] == "ask"

    cached = k.act("write")
    assert cached["ok"]
    assert cached["decision"]["decision"] == "ask"

    k.approval_cache.clear()
    after_clear = k.act("write")
    assert not after_clear["ok"]
    assert after_clear["requires_approval"]


def test_approval_cache_respects_fields(tmp_path):
    k = _kernel(tmp_path)
    r1 = k.act("write", path="/tmp/a", approved=True)
    assert r1["ok"]

    r2 = k.act("write", path="/tmp/b")
    assert not r2["ok"]
    assert r2["requires_approval"]

    r3 = k.act("write", path="/tmp/a")
    assert r3["ok"]


def test_dry_run_does_not_cache_approval(tmp_path):
    k = _kernel(tmp_path)
    dry = k.act("write", dry_run=True)
    assert not dry["ok"]
    assert dry.get("requires_approval")

    second = k.act("write")
    assert not second["ok"]
    assert second["requires_approval"]


def test_fresh_act_resets_budget_session(tmp_path):
    k = _kernel(tmp_path)
    k.budget.budgets["session"] = Budget(max_tokens=2, period="session")
    assert k.act("Read", tokens=1)["ok"]
    assert not k.act("Read", tokens=1)["ok"]
    assert k.act("Read", tokens=1, fresh_context=True)["ok"]


def test_fresh_chat_creates_new_session(tmp_path):
    k = _kernel(tmp_path)
    result = k.chat_message("hello", fresh_context=True)
    assert result["ok"]
    assert "session_id" in result
    session = ChatSession(tmp_path, result["session_id"])
    assert len(session.history()) == 2


def test_fresh_workflow_resets_derived_context(tmp_path):
    k = _kernel(tmp_path)
    context = {"message": "optimize react frontend", "persona": "ARCH", "skills": ["x"]}
    result = k.run_workflow("test", context, fresh_context=True)
    assert result["ok"]
    assert "session_id" in result
    assert context["persona"] == "ARCH"  # original not mutated
    assert result["context"]["persona"] != "ARCH"


def test_auto_persona_skips_when_persona_already_set(tmp_path):
    """Cover line 141: _auto_persona returns early when persona already in kwargs."""
    k = _kernel(tmp_path)
    result = k.act("Read", content="audit firewall", persona="DEV", approved=True)
    assert result["ok"]
    assert result["args"]["persona"] == "DEV"


def test_act_invalid_args_returns_error(tmp_path):
    """Cover lines 162-163: ValidationError handling in act."""
    k = _kernel(tmp_path)
    result = k.act("", approved=True)
    assert not result["ok"]
    assert "Invalid action arguments" in result["error"]


def test_save_persists_budget(tmp_path):
    """Cover line 240: Kernel.save() calls budget.save()."""
    k = _kernel(tmp_path)
    k.budget.budgets["session"] = Budget(max_tokens=100, period="session")
    k.save()
    assert (tmp_path / "state" / "budget.json").exists()


def test_main_block_prints_status(tmp_path, monkeypatch, capsys):
    """Cover lines 268-269: __main__ block creates Kernel and prints status JSON."""
    import json
    import os
    import subprocess
    import sys

    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    monkeypatch.setenv("AGENT_OS_ROOT", str(tmp_path))
    env = {**os.environ, "AGENT_OS_ROOT": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-m", "runtime.kernel"],
        capture_output=True, text=True, env=env,
    )
    data = json.loads(result.stdout)
    assert "version" in data
