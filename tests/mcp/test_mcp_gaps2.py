"""Gap coverage for MCP tools: adapters, rbac, analytics, context, cro,
email, freelance, memory, policy, workflow tools."""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import aizee_mcp.rbac as rbac
from aizee_mcp._compat import FastMCP
from aizee_mcp.adapters import (
    AdapterError,
    LocalAdapter,
    RemoteA2AAdapter,
    Session,
    _A2ARedirectBlocker,
    _validate_endpoint,
)
from aizee_mcp.tools.common import reset_state

pytestmark = pytest.mark.mcp

_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _default_root(monkeypatch):
    """Default AIZEE_ROOT to the repo; tests needing isolation override it."""
    monkeypatch.setenv("AIZEE_ROOT", str(_ROOT))


def _call(mcp: FastMCP, name: str, arguments: dict) -> str:
    reset_state()
    tool = mcp._tool_manager.get_tool(name)
    assert tool is not None
    return tool.fn(**arguments)


class TestAdaptersGaps:
    def test_redirect_same_origin_private_ip(self):
        b = _A2ARedirectBlocker()
        req = MagicMock()
        req.full_url = "http://169.254.169.254/latest"
        with pytest.raises(urllib.error.HTTPError):
            b.redirect_request(req, MagicMock(), 301, "m", {}, "/meta-data")

    def test_local_public_session_strips_private(self):
        a = LocalAdapter()
        s = Session(session_id="x", backend=a.backend, profile="p")
        s.artifacts = {"_proc": "secret", "task": "t"}
        pub = a.public_session(s)
        assert "_proc" not in pub.artifacts
        assert pub.artifacts["task"] == "t"

    def test_validate_endpoint_literal_private_https(self):
        with pytest.raises(AdapterError):
            _validate_endpoint("https://10.0.0.1")

    def test_ssl_context_memoized(self):
        a = RemoteA2AAdapter({"endpoint": "https://example.com", "verify_ssl": True})
        ctx1 = a._create_ssl_context()
        ctx2 = a._create_ssl_context()
        assert ctx1 is ctx2

    def test_poll_non_str_remote_id(self):
        a = RemoteA2AAdapter({"endpoint": "http://localhost:9000"})
        s = Session(session_id="x", backend=a.backend, profile="p")
        s.artifacts = {"remote_session_id": 123}
        out = asyncio.run(a.poll(s))
        assert out.status == "failed"
        assert "Missing remote session id" in out.artifacts["error"]


class TestRbacGaps:
    def test_reload_rbac(self, tmp_path):
        cfg = tmp_path / "rbac.yaml"
        cfg.write_text("admin_required:\n  - danger_tool\n", encoding="utf-8")
        result = rbac.reload_rbac(cfg)
        assert "danger_tool" in result

    def test_strict_no_roles_denies_admin_tool(self, monkeypatch):
        monkeypatch.setenv("AIZEE_RBAC_STRICT", "1")
        monkeypatch.delenv("AIZEE_MCP_ROLES", raising=False)
        monkeypatch.setattr(rbac, "_ADMIN_REQUIRED", frozenset({"danger_tool"}))
        monkeypatch.setattr(rbac, "_warned_default_allow", True)
        assert rbac.check_tool_permission("danger_tool", roles=None) is False
        assert rbac.check_tool_permission("safe_tool", roles=None) is True


class TestAnalyticsGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.analytics_tools import register_analytics_tools
        self.mcp = FastMCP("t")
        register_analytics_tools(self.mcp)

    def test_win_rate_bad_bid(self):
        out = _call(self.mcp, "pipeline_win_rate",
                    {"bids": '[{"platform": "p", "niche": "n", "amount": "abc", "won": true}]'})
        data = json.loads(out)
        assert data["ok"] is False

    def test_funnel_dropoff_build_error(self):
        with patch("aizee_mcp.tools.analytics_tools.funnel_tracker.Funnel",
                   side_effect=ValueError("boom")):
            out = _call(self.mcp, "funnel_dropoff",
                        {"steps": '[{"label": "a", "count": 1}]'})
        assert json.loads(out)["ok"] is False


class TestContextGaps:
    @pytest.fixture()
    def ctx_mcp(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        (tmp_path / "skills").mkdir()
        (tmp_path / "CHANGELOG.md").write_text("## [1.0.0]\n- x\n", encoding="utf-8")
        from aizee_mcp.tools.context_tools import register_context_tools
        mcp = FastMCP("t")
        register_context_tools(mcp)
        return mcp, tmp_path

    def test_search_bad_limit(self, ctx_mcp):
        mcp, root = ctx_mcp
        (root / "skills" / "s.md").write_text("needle", encoding="utf-8")
        out = _call(mcp, "search_skills", {"query": "needle", "limit": "abc"})
        data = json.loads(out)
        assert isinstance(data, list) and len(data) == 1

    def test_search_folder_skill(self, ctx_mcp):
        mcp, root = ctx_mcp
        (root / "skills" / "docker").mkdir()
        (root / "skills" / "docker" / "SKILL.md").write_text("dockerize everything", encoding="utf-8")
        out = _call(mcp, "search_skills", {"query": "dockerize"})
        data = json.loads(out)
        assert data and data[0]["name"] == "docker"

    def test_search_skips_dirs_and_names(self, ctx_mcp):
        mcp, root = ctx_mcp
        (root / "skills" / "references").mkdir()
        (root / "skills" / "references" / "x.md").write_text("needle content", encoding="utf-8")
        (root / "skills" / "README.md").write_text("needle readme", encoding="utf-8")
        (root / "skills" / "EVAL.md").write_text("needle eval", encoding="utf-8")
        (root / "skills" / "big.md").write_text("needle " + "x" * 200_001, encoding="utf-8")
        out = _call(mcp, "search_skills", {"query": "needle"})
        assert json.loads(out) == []

    def test_search_500_cap(self, ctx_mcp):
        mcp, root = ctx_mcp
        for i in range(501):
            (root / "skills" / f"s{i:04d}.md").write_text("needle", encoding="utf-8")
        out = _call(mcp, "search_skills", {"query": "needle", "limit": 9999})
        data = json.loads(out)
        assert 0 < len(data) <= 100  # _MAX_RESULTS cap; scan break covered

    def test_changelog_missing_section(self, ctx_mcp):
        mcp, _ = ctx_mcp
        out = _call(mcp, "get_changelog", {"section": "9.9.9"})
        data = json.loads(out)
        assert data["ok"] is False


class TestCroGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.cro_tools import register_cro_tools
        self.mcp = FastMCP("t")
        register_cro_tools(self.mcp)

    def test_flag_bad_identifier(self):
        out = _call(self.mcp, "cro_evaluate_flag",
                    {"key": "k", "identifier": "", "segments": "{}"})
        assert json.loads(out)["ok"] is False

    def test_flag_eval_raises(self):
        out = _call(self.mcp, "cro_evaluate_flag",
                    {"key": "k", "identifier": "u1",
                     "segments": '{"s": {"pct": "abc"}}'})
        assert json.loads(out)["ok"] is False


class TestEmailGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.email_tools import register_email_tools
        self.mcp = FastMCP("t")
        register_email_tools(self.mcp)

    def test_send_non_str_body(self):
        out = _call(self.mcp, "email_send",
                    {"to": "a@b.com", "subject": "s", "html": 123, "text": ""})
        data = json.loads(out)
        assert data["ok"] is False
        assert "strings" in data["error"]

    def test_unsubscribe_bad_header(self):
        out = _call(self.mcp, "email_unsubscribe",
                    {"email": "a@b.com\nBcc: x", "list_id": "l"})
        assert json.loads(out)["ok"] is False

    def test_drip_create_engine_error(self):
        with patch("aizee_mcp.tools.email_tools.drip_engine.DripEngine",
                   side_effect=TypeError("boom")):
            out = _call(self.mcp, "drip_create_sequence", {"name": "seq1"})
        assert json.loads(out)["ok"] is False

    def test_drip_ready_engine_error(self):
        with patch("aizee_mcp.tools.email_tools.drip_engine.DripEngine",
                   side_effect=ValueError("boom")):
            out = _call(self.mcp, "drip_ready_steps",
                        {"sequence_name": "s", "steps": "[]"})
        assert json.loads(out)["ok"] is False


class TestFreelanceGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.freelance_tools import register_freelance_tools
        self.mcp = FastMCP("t")
        register_freelance_tools(self.mcp)

    def test_contract_bad_party_b(self):
        out = _call(self.mcp, "contract_create",
                    {"contract_type": "nda", "party_a": "A", "party_b": ""})
        assert json.loads(out)["ok"] is False

    def test_invoice_client_validation_error(self):
        from runtime.schemas import ValidationError
        with patch("aizee_mcp.tools.freelance_tools.Client",
                   side_effect=ValidationError("bad client")):
            out = _call(self.mcp, "invoice_create",
                        {"client_id": "c1", "client_name": "N", "amount": 10})
        assert json.loads(out)["ok"] is False

    def test_invoice_value_error(self):
        with patch("aizee_mcp.tools.freelance_tools.Invoice",
                   side_effect=ValueError("bad inv")):
            out = _call(self.mcp, "invoice_create",
                        {"client_id": "c1", "client_name": "N", "amount": 10})
        data = json.loads(out)
        assert data["ok"] is False
        assert "Invalid invoice data" in data["error"]

    def test_rates_validation_error(self):
        out = _call(self.mcp, "pricing_calc",
                    {"income_goal": -5, "billable_hours_per_week": 40})
        assert json.loads(out)["ok"] is False

    def test_arabic_platform_bad_query(self):
        out = _call(self.mcp, "arabic_platform_fetch",
                    {"platform": "mostaql", "query": 123})
        assert json.loads(out)["ok"] is False


class TestMemoryToolGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.memory_tools import register_memory_tools
        self.mcp = FastMCP("t")
        register_memory_tools(self.mcp)

    def test_coerce_limit_bad(self):
        out = _call(self.mcp, "search_memory_vector",
                    {"query": "q", "k": "abc"})
        # k falls back to 5; result shape depends on store but must not crash
        json.loads(out)

    def test_query_context_weird_vector_results(self):
        store = MagicMock()
        mem = MagicMock()
        mem.id, mem.kind, mem.source, mem.content = "m1", "k", "s", "c"
        other = MagicMock()
        other.id, other.kind, other.source, other.content = "other", "k", "s", "c2"
        store.search.return_value = [mem]
        store.get.return_value = other
        store.search_vector.return_value = [
            42, {"id": 5}, {"id": "m1", "score": 0.9},
            {"id": "other", "score": 0.1},
        ]
        with patch("aizee_mcp.tools.memory_tools.memory", return_value=store):
            out = _call(self.mcp, "query_context", {"query": "q"})
        data = json.loads(out)
        item = next(i for i in data if i["id"] == "m1")
        assert item["vector"] is True
        assert any(i["id"] == "other" for i in data)

    def test_db_schema_not_sqlite(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        f = tmp_path / "x.txt"
        f.write_text("hi")
        out = _call(self.mcp, "build_schema_graph", {"db_path": "x.txt"})
        assert "Not a SQLite" in json.loads(out)["error"]

    def test_db_schema_build_fails(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        f = tmp_path / "x.db"
        f.write_bytes(b"not sqlite at all")
        out = _call(self.mcp, "build_schema_graph", {"db_path": "x.db"})
        assert json.loads(out)["ok"] is False


class TestPolicyToolGaps:
    @pytest.fixture(autouse=True)
    def _mcp(self):
        from aizee_mcp.tools.policy_tools import register_policy_tools
        self.mcp = FastMCP("t")
        register_policy_tools(self.mcp)

    def test_analyze_budget_non_dict_val(self):
        k = MagicMock()
        k.budget.budgets = {"plain": 5}
        k.budget.usage = {}
        with patch("aizee_mcp.tools.policy_tools.kernel", return_value=k):
            out = _call(self.mcp, "analyze_budget", {})
        data = json.loads(out)
        assert data["budgets"]["plain"]["repr"] == "5"

    def test_lint_python_bad_limits(self):
        out = _call(self.mcp, "lint_python",
                    {"code": "x = 1", "max_lines": "abc", "max_params": "xyz"})
        data = json.loads(out)
        assert data["ok"] is True


class TestWorkflowToolGaps:
    @pytest.fixture()
    def wf_mcp(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        (tmp_path / "rules").mkdir()
        from aizee_mcp.tools.workflow_tools import register_workflow_tools
        mcp = FastMCP("t")
        register_workflow_tools(mcp)
        return mcp, tmp_path

    def test_rules_200_cap_and_skips(self, wf_mcp):
        mcp, root = wf_mcp
        for i in range(201):
            (root / "rules" / f"r{i:04d}.md").write_text("needle", encoding="utf-8")
        (root / "rules" / "big.md").write_text("needle" + "x" * 200_001, encoding="utf-8")
        (root / "rules" / "bad.md").write_bytes(b"\xff\xfe needle")
        out = _call(mcp, "query_rules", {"query": "needle"})
        data = json.loads(out)
        assert isinstance(data, list)

    def test_rules_stat_oserror(self, wf_mcp, monkeypatch):
        mcp, root = wf_mcp
        (root / "rules" / "r.md").write_text("needle", encoding="utf-8")
        orig = Path.stat

        def boom(self, *a, **k):
            if self.name == "r.md":
                raise OSError("io")
            return orig(self, *a, **k)
        monkeypatch.setattr(Path, "stat", boom)
        out = _call(mcp, "query_rules", {"query": "needle"})
        assert json.loads(out) == []

    def test_compile_globs_not_list(self, wf_mcp):
        mcp, _ = wf_mcp
        out = _call(mcp, "compile_rule_files", {"globs": "x"})
        assert json.loads(out)["ok"] is False

    def test_compile_globs_too_many(self, wf_mcp):
        mcp, _ = wf_mcp
        out = _call(mcp, "compile_rule_files", {"globs": ["a"] * 51})
        assert json.loads(out)["ok"] is False

    def test_compile_glob_traversal(self, wf_mcp):
        mcp, _ = wf_mcp
        out = _call(mcp, "compile_rule_files", {"globs": ["../x.md"]})
        assert json.loads(out)["ok"] is False

    def test_compile_rules_raises(self, wf_mcp):
        mcp, _ = wf_mcp
        with patch("aizee_mcp.tools.workflow_tools.compile_rules",
                   side_effect=RuntimeError("x")):
            out = _call(mcp, "compile_rule_files", {})
        assert "Rule compilation failed" in json.loads(out)["error"]

    def test_plan_too_many_steps(self, wf_mcp):
        mcp, _ = wf_mcp
        out = _call(mcp, "run_mcp_plan", {"steps": [{}] * 51})
        assert json.loads(out)["ok"] is False

    def test_plan_all_non_dict(self, wf_mcp):
        mcp, _ = wf_mcp
        out = _call(mcp, "run_mcp_plan", {"steps": [1, 2]})
        assert "non-empty list of objects" in json.loads(out)["error"]

    def test_plan_inside_running_loop(self, wf_mcp):
        mcp, _ = wf_mcp
        async def inner():
            return _call(mcp, "run_mcp_plan",
                         {"steps": [{"id": "s1", "tool": "x"}]})
        out = asyncio.run(inner())
        assert "running event loop" in json.loads(out)["error"]
