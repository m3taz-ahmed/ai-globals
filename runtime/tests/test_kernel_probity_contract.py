"""Tests for GATE-B1 (structured probity denial) and GATE-B2 (Bash normalization)."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp_path / "runtime/policies/probity.yaml").write_text(
        "rules:\n"
        "  - kind: forbidCommandPattern\n"
        "    name: block-rm-rf\n"
        "    pattern: \"rm\\\\s+-rf\\\\s+/\"\n"
        "    message: \"rm -rf on root filesystem is forbidden\"\n"
        "  - kind: forbidCommandPattern\n"
        "    name: block-force-push\n"
        "    pattern: \"git\\\\s+push\\\\s+(-f|--force)\"\n"
        "    message: \"Force push is forbidden\"\n"
    )
    return Kernel(tmp_path)


# ---------------------------------------------------------------------------
# GATE-B1: Structured denial for probity violations
# ---------------------------------------------------------------------------


class TestProbityStructuredDenial:
    """Probity violations must return structured deny dicts, not raw tracebacks."""

    def test_rm_rf_returns_deny_dict(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        result = k.act("exec", command="rm -rf /")
        assert not result["ok"]
        assert result["decision"] == "deny"
        assert result.get("gate") == "probity"
        assert "probity_violation" in result["reason"]

    def test_force_push_returns_deny_dict(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        result = k.act("exec", command="git push --force origin main")
        assert not result["ok"]
        assert result["decision"] == "deny"
        assert result.get("gate") == "probity"

    def test_no_raw_traceback(self, tmp_path: Path) -> None:
        """The kernel must not raise GuardrailViolationError."""
        k = _kernel(tmp_path)
        # This should NOT raise — it should return a deny dict
        result = k.act("exec", command="rm -rf /")
        assert isinstance(result, dict)

    def test_audit_log_probity_deny(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        k.act("exec", command="rm -rf /")
        # Check audit log has probity.deny entry
        log_path = tmp_path / "logs" / "audit.jsonl"
        if log_path.exists():
            content = log_path.read_text(encoding="utf-8")
            assert "probity.deny" in content


# ---------------------------------------------------------------------------
# GATE-B2: Action type normalization (Bash bypasses Probity)
# ---------------------------------------------------------------------------


class TestProbityNormalization:
    """Actions typed as 'Bash', 'Shell', 'Apply' must be caught by probity."""

    def test_bash_caught_by_probity(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        result = k.act("Bash", command="rm -rf /")
        assert not result["ok"]
        assert result.get("gate") == "probity"

    def test_shell_caught_by_probity(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        result = k.act("Shell", command="rm -rf /")
        assert not result["ok"]
        assert result.get("gate") == "probity"

    def test_apply_caught_by_content_pattern(self, tmp_path: Path) -> None:
        """'Apply' normalizes to 'write' so content patterns match."""
        from runtime.probity import normalize_action_type

        assert normalize_action_type("Apply") == "write"
        assert normalize_action_type("Patch") == "write"

    def test_lowercase_regression(self, tmp_path: Path) -> None:
        """Lowercase 'exec' still works after normalization."""
        k = _kernel(tmp_path)
        result = k.act("exec", command="rm -rf /")
        assert not result["ok"]
        assert result.get("gate") == "probity"

    def test_normalize_various(self) -> None:
        from runtime.probity import normalize_action_type

        assert normalize_action_type("Bash") == "exec"
        assert normalize_action_type("SHELL") == "exec"
        assert normalize_action_type("Run") == "exec"
        assert normalize_action_type("write") == "write"
        assert normalize_action_type("Edit") == "write"
        assert normalize_action_type("read") == "read"  # unknown stays as-is
