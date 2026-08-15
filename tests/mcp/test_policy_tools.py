"""Tests for aios_mcp/tools/policy_tools.py — policy, budget, guardian, metrics."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mcp.server.fastmcp import FastMCP

# Set up isolated root BEFORE importing
_ROOT = tempfile.mkdtemp(prefix="aios_pol_test_")
os.environ["AGENT_OS_ROOT"] = _ROOT
ROOT = Path(_ROOT)
for sub in ("runtime/policies", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)
(ROOT / "runtime/policies/default.yaml").write_text(
    "default_action: ask\nrules:\n  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
)

from aios_mcp.tools.policy_tools import register_policy_tools  # noqa: E402
from aios_mcp.tools.common import reset_state  # noqa: E402

_mcp = FastMCP("test-policy")
register_policy_tools(_mcp)


def _call(name: str, arguments: dict) -> str:
    os.environ["AGENT_OS_ROOT"] = _ROOT
    reset_state()
    return _mcp._tool_manager.get_tool(name).fn(**arguments)


def _mock_kernel():
    """Return a mock Kernel with the attributes policy tools access."""
    k = MagicMock()
    k.budget.usage = {"global": {"tokens": 100, "calls": 5}}
    k.budget.budgets = {}
    k.guardian.config.default_decision = "allow"
    k.guardian.authorize.return_value = MagicMock(
        status="allow", rule_name="allow-read", reason="allowed by policy"
    )
    k.status.return_value = {"workflows": [], "rules": [], "budgets": []}
    k.capabilities.list.return_value = ["read", "write", "execute"]
    return k


class TestCheckPolicy:
    def test_check_policy_allowed(self):
        mock_k = _mock_kernel()
        mock_k.act.return_value = {"ok": True, "action": "allow"}
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("check_policy", {"action": "Read"})
            data = json.loads(result)
            assert data["ok"] is True

    def test_check_policy_with_args(self):
        mock_k = _mock_kernel()
        mock_k.act.return_value = {"ok": True}
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("check_policy", {"action": "Read", "args": {"user": "alice"}})
            data = json.loads(result)
            assert data["ok"] is True


class TestAnalyzeBudget:
    def test_analyze_budget(self):
        mock_k = _mock_kernel()
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("analyze_budget", {})
            data = json.loads(result)
            assert "usage" in data
            assert "budgets" in data
            assert data["usage"]["global"]["tokens"] == 100


class TestRunGuardianCheck:
    def test_invalid_tool_name(self):
        """Cover lines 43-44: reject unsafe tool name."""
        result = _call("run_guardian_check", {"tool": "../etc/passwd"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid tool name" in data["error"]

    def test_guardian_allows(self):
        """Cover lines 45-48: guardian authorizes the request."""
        mock_k = _mock_kernel()
        mock_k.guardian.config.default_decision = "deny"
        mock_k.guardian.authorize.return_value = MagicMock(
            status="allow", rule_name="allow-read", reason="allowed"
        )
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("run_guardian_check", {"tool": "Read", "attributes": {"file": "test.py"}})
            data = json.loads(result)
            # ok is True because decision.status != default_decision
            assert data["ok"] is True
            assert data["status"] == "allow"
            assert data["rule"] == "allow-read"

    def test_guardian_denies(self):
        """Cover lines 45-48: guardian denies the request."""
        mock_k = _mock_kernel()
        mock_k.guardian.config.default_decision = "allow"
        mock_k.guardian.authorize.return_value = MagicMock(
            status="deny", rule_name="block-write", reason="write not allowed"
        )
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("run_guardian_check", {"tool": "Write"})
            data = json.loads(result)
            assert data["ok"] is True
            assert data["status"] == "deny"

    def test_guardian_with_no_attributes(self):
        """Cover line 45: attributes defaults to empty dict."""
        mock_k = _mock_kernel()
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("run_guardian_check", {"tool": "Read"})
            data = json.loads(result)
            assert "status" in data


class TestGetMetrics:
    def test_get_metrics(self):
        """Cover line 61: format_metrics returns Prometheus text."""
        mock_k = _mock_kernel()
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k), \
             patch("aios_mcp.tools.policy_tools.format_metrics", return_value="# metrics here"):
            result = _call("get_metrics", {})
            assert "metrics" in result


class TestGetOsStatus:
    def test_get_os_status(self):
        """Cover line 66: returns kernel status JSON."""
        mock_k = _mock_kernel()
        mock_k.status.return_value = {"workflows": ["w1"], "rules": ["r1"], "budgets": ["b1"]}
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("get_os_status", {})
            data = json.loads(result)
            assert "workflows" in data
            assert data["workflows"] == ["w1"]


class TestListCapabilities:
    def test_list_capabilities(self):
        """Cover line 71: returns capabilities list."""
        mock_k = _mock_kernel()
        mock_k.capabilities.list.return_value = ["read", "write"]
        with patch("aios_mcp.tools.policy_tools.kernel", return_value=mock_k):
            result = _call("list_capabilities", {})
            data = json.loads(result)
            assert data == ["read", "write"]


class TestLintPython:
    def test_invalid_code_empty(self):
        """Cover lines 76-77: empty code rejected."""
        result = _call("lint_python", {"code": ""})
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid code" in data["error"]

    def test_invalid_code_non_string(self):
        """Cover lines 76-77: non-string code rejected."""
        result = _call("lint_python", {"code": 123})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_code_too_long(self):
        """Cover lines 76-77: overlong code rejected."""
        result = _call("lint_python", {"code": "x" * 100_001})
        data = json.loads(result)
        assert data["ok"] is False

    def test_lint_valid_code(self):
        """Cover lines 78-80: lint valid Python code."""
        code = "def hello():\n    print('hello')\n"
        result = _call("lint_python", {"code": code})
        data = json.loads(result)
        assert data["ok"] is True
        assert "findings" in data

    def test_lint_code_with_findings(self):
        """Cover lines 78-80: lint code that produces findings."""
        # Create a function with too many parameters
        code = "def f(a, b, c, d, e, f, g, h):\n    pass\n"
        result = _call("lint_python", {"code": code, "max_params": 7})
        data = json.loads(result)
        assert data["ok"] is True
        assert isinstance(data["findings"], list)
