from pathlib import Path

from runtime.policy import PolicyEngine


def _engine(tmp_root: Path) -> PolicyEngine:
    (tmp_root / "runtime" / "policies").mkdir(parents=True, exist_ok=True)
    (tmp_root / "runtime" / "policies" / "default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read' or type == 'grep'\"\n    action: allow\n"
        "  - name: deny-destructive\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
        "  - name: ask-write\n    condition: \"type in ['edit', 'write']\"\n    action: ask\n"
    )
    return PolicyEngine(tmp_root)


def test_allow_read(tmp_path):
    e = _engine(tmp_path)
    assert e.can("Read")["decision"] == "allow"
    assert e.can("grep")["decision"] == "allow"


def test_deny_destructive(tmp_path):
    e = _engine(tmp_path)
    assert e.can("rm", command="rm -rf /")["decision"] == "deny"


def test_ask_write(tmp_path):
    e = _engine(tmp_path)
    assert e.can("edit")["decision"] == "ask"
    assert e.can("write")["decision"] == "ask"


def test_ask_default(tmp_path):
    e = _engine(tmp_path)
    assert e.can("deploy")["decision"] == "ask"


def test_safe_eval_no_eval_exploit(tmp_path):
    e = _engine(tmp_path)
    # should not execute code or raise; simply return False
    e.rules[0].condition = "__import__('os').system('echo pwned')"
    result = e.can("Read")
    assert result["decision"] == "ask"
