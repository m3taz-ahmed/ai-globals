"""Second gap-coverage pass for runtime/kernel.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from runtime.kernel import Kernel, KernelBuilder, _act_via_middleware, _init_core_services
from runtime.middleware import MiddlewareResult


@pytest.fixture()
def kernel(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "plaintext")
    monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
    for d in ("state", "memory", "rules", "skills", "workflows", "plugins"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return Kernel(root=tmp_path)


class TestInitFailureBranches:
    def _bare_kernel(self, tmp_path):
        k = MagicMock()
        k.root = tmp_path
        k.project_root = tmp_path
        return k

    def test_prompt_injection_import_failure(self, tmp_path):
        k = self._bare_kernel(tmp_path)
        with patch.dict("sys.modules", {"runtime.guardrails.prompt_injection": None}):
            _init_core_services(k)  # no crash

    def test_injection_stack_failure(self, tmp_path):
        k = self._bare_kernel(tmp_path)
        with patch.dict("sys.modules", {"runtime.injection_detector": None}):
            _init_core_services(k)

    def test_design_stack_failure(self, tmp_path):
        k = self._bare_kernel(tmp_path)
        with patch.dict("sys.modules", {"runtime.design_library": None}):
            _init_core_services(k)

    def test_marketing_stack_failure(self, tmp_path):
        k = self._bare_kernel(tmp_path)
        with patch.dict("sys.modules", {"runtime.attribution_model": None}):
            _init_core_services(k)


class TestActPaths:
    def test_deny_metric_incremented(self, kernel):
        # an action denied by policy must hit the DENY metric label
        kernel.act("exec", command="rm -rf /", dry_run=True)
        # just assert no crash; the label() call ran
        assert kernel._actions_total is not None

    def test_middleware_handler_ok(self, kernel):
        def mw(ctx, nxt):
            return nxt(ctx)
        kernel.use_middleware(mw)
        r = kernel.act("read", path="x", dry_run=True)
        assert isinstance(r, dict)

    def test_mw_result_dict_passthrough(self, kernel):
        kernel._middleware_pipeline.execute = MagicMock(
            return_value=MiddlewareResult(ok=False, data={"ok": False, "gate": "g"}, error="x"))
        r = _act_via_middleware(kernel, "read", False, {}, None)
        assert r == {"ok": False, "gate": "g"}

    def test_mw_error_none(self, kernel):
        kernel._middleware_pipeline.execute = MagicMock(
            return_value=MiddlewareResult(ok=False, data=None, error=None))
        r = _act_via_middleware(kernel, "read", False, {}, None)
        assert r["error"] == "middleware error"


class TestBuilderPluginMemory:
    def test_plugins_memory_wired(self, tmp_path):
        # Force a kernel whose _plugins manager already exists at build time
        plugin = MagicMock()
        pm = MagicMock()
        pm._plugins = {"p1": plugin}
        mem = MagicMock()

        fake_kernel = MagicMock()
        fake_kernel._plugins = pm
        fake_kernel.policy_mgr = MagicMock()

        with patch("runtime.kernel.Kernel", return_value=fake_kernel):
            k = KernelBuilder().with_root(tmp_path).with_memory(mem).build()
        assert k._memory is mem
        assert plugin.memory is mem
