"""P1.2: output.pre_send + memory.pre_write lifecycle hook phases."""
from __future__ import annotations

from pathlib import Path

import pytest

from runtime.hook_lifecycle import (
    HookContext,
    HookError,
    HookPhase,
    HookRegistry,
)
from runtime.kernel import Kernel


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: allow\nrules: []\n"
    )
    return Kernel(tmp_path)


def test_phases_exist():
    assert HookPhase.OUTPUT_PRE_SEND.value == "output.pre_send"
    assert HookPhase.MEMORY_PRE_WRITE.value == "memory.pre_write"


def test_new_phases_not_in_normal_pipeline():
    # Domain hooks are explicit invocation points, not linear stages.
    reg = HookRegistry()
    seen: list[str] = []
    reg.register(HookPhase.OUTPUT_PRE_SEND, lambda c: seen.append("ops"))
    reg.register(HookPhase.MEMORY_PRE_WRITE, lambda c: seen.append("mpw"))
    reg.run_lifecycle("anything")
    assert seen == []


def test_memory_pre_write_veto(tmp_path):
    from memory.store import MemoryStore

    reg = HookRegistry()
    reg.register(HookPhase.MEMORY_PRE_WRITE, lambda c: c.stop())
    store = MemoryStore(root=tmp_path, enable_vector=False, hooks=reg)
    with pytest.raises(HookError):
        store.add("note", "vetoed content")
    # Nothing persisted.
    assert store.list_all() == []


def test_memory_pre_write_allow(tmp_path):
    from memory.store import MemoryStore

    reg = HookRegistry()
    calls: list[dict] = []
    reg.register(HookPhase.MEMORY_PRE_WRITE, lambda c: calls.append(c.attributes))
    store = MemoryStore(root=tmp_path, enable_vector=False, hooks=reg)
    store.add("note", "allowed content")
    assert len(calls) == 1 and calls[0]["content"] == "allowed content"
    assert store.list_all()


def test_output_pre_send_veto(tmp_path):
    k = _kernel(tmp_path)
    k.hook_registry.register(HookPhase.OUTPUT_PRE_SEND, lambda c: c.stop())
    r = k.chat_message("hello")
    assert r["ok"] is False and r["gate"] == "hook"


def test_output_pre_send_pass_through(tmp_path):
    k = _kernel(tmp_path)
    k.hook_registry.register(HookPhase.OUTPUT_PRE_SEND, lambda c: None)
    r = k.chat_message("hello")
    assert r.get("ok", True) is not False or "hook" not in str(r)


def test_hook_error_propagates_fail_closed(tmp_path):
    from memory.store import MemoryStore

    def _boom(c: HookContext) -> None:
        raise RuntimeError("hook crashed")

    reg = HookRegistry()
    reg.register(HookPhase.MEMORY_PRE_WRITE, _boom)
    store = MemoryStore(root=tmp_path, enable_vector=False, hooks=reg)
    with pytest.raises(HookError):
        store.add("note", "content")


def test_hook_context_result_and_error():
    from runtime.hook_lifecycle import HookContext

    ctx = HookContext(action="x")
    ctx.add_result("k", 1)
    ctx.add_error("nonfatal")
    assert ctx.results["k"] == 1 and "nonfatal" in ctx.errors
