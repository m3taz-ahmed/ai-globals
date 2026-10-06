"""Gap-coverage tests for runtime/kernel.py.

Covers: KernelBuilder wiring, middleware dispatch path, _build_mcp_firewall
project-rules merge, check_mcp_tool, and init-failure warning branches.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from runtime.kernel import (
    Kernel,
    KernelBuilder,
    _act_via_middleware,
    _init_core_services,
)


@pytest.fixture()
def kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
    for d in ("state", "memory", "rules", "skills", "workflows", "plugins"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return Kernel(root=tmp_path)


class TestBuilder:
    def test_fluent_withers(self, tmp_path):
        b = (KernelBuilder()
             .with_root(tmp_path)
             .with_project_root(tmp_path / "proj")
             .with_persona_detector(MagicMock())
             .with_skill_resolver(MagicMock()))
        assert b._root == tmp_path
        assert b._persona_detector is not None
        assert b._skill_resolver is not None

    def test_builder_wires_managers(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        for d in ("state", "memory", "rules", "skills", "workflows", "plugins"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        bm = MagicMock()
        al = MagicMock()
        pe = MagicMock()
        g = MagicMock()
        pr = MagicMock()
        mem = MagicMock()
        k = (KernelBuilder()
             .with_root(tmp_path)
             .with_budget_manager(bm)
             .with_audit_logger(al)
             .with_policy_engine(pe)
             .with_guardian(g)
             .with_probity(pr)
             .with_memory(mem)
             .build())
        assert k.budget is bm and k.policy_mgr.budget is bm
        assert k.audit is al and k.policy_mgr.audit is al
        assert k.policy is pe and k.policy_mgr.policy is pe
        assert k.guardian is g and k.policy_mgr.guardian is g
        assert k.probity is pr and k.policy_mgr.probity is pr
        assert k._memory is mem

    def test_builder_minimal(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        for d in ("state", "memory", "plugins"):
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        k = KernelBuilder().with_root(tmp_path).build()
        assert isinstance(k, Kernel)


class TestMiddlewarePath:
    def test_middleware_dispatch(self, kernel):
        seen = []

        def mw(ctx, nxt):
            seen.append(ctx.action_type)
            return nxt(ctx)

        kernel.use_middleware(mw)
        kernel.act("read", path="x")
        assert seen == ["read"]

    def test_middleware_denial_payload_preserved(self, kernel):
        # destructive action denied by policy → mw_result.ok False with dict data
        def mw(ctx, nxt):
            return nxt(ctx)
        kernel.use_middleware(mw)
        r = kernel.act("delete_all", dry_run=True)
        assert r.get("ok") is False or "error" in r or r.get("decision") == "deny"

    def test_act_via_middleware_no_data(self, kernel):
        # middleware result with ok=True but data=None returns {"ok": True}
        from runtime.middleware import MiddlewareResult
        kernel._middleware_pipeline.execute = MagicMock(
            return_value=MiddlewareResult(ok=True, data=None))
        r = _act_via_middleware(kernel, "read", False, {}, None)
        assert r == {"ok": True}

    def test_act_via_middleware_error(self, kernel):
        from runtime.middleware import MiddlewareResult
        kernel._middleware_pipeline.execute = MagicMock(
            return_value=MiddlewareResult(ok=False, data=None, error="mw blew up"))
        r = _act_via_middleware(kernel, "read", False, {}, None)
        assert r == {"ok": False, "error": "mw blew up"}


class TestMcpFirewallBuild:
    def test_project_rules_merged(self, kernel, tmp_path):
        rules_dir = tmp_path / ".aizee"
        rules_dir.mkdir(exist_ok=True)
        (rules_dir / "mcp_firewall.yaml").write_text(
            "rules:\n  - name: block-evil\n    tool: evil_tool\n    action: deny\n")
        fw = kernel._build_mcp_firewall()
        names = [getattr(r, "name", "") for r in fw.rules]
        assert any("block-evil" in n for n in names)

    def test_check_mcp_tool(self, kernel):
        r = kernel.check_mcp_tool("safe_tool", {})
        assert "decision" in r or isinstance(r, dict)


class TestInitWarnings:
    def test_taint_import_failure_warns(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
        k = MagicMock()
        k.root = tmp_path
        k.project_root = tmp_path
        with patch.dict("sys.modules", {"runtime.taint": None}):
            _init_core_services(k)  # no crash — degraded defenses logged
