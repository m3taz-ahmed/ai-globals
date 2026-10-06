"""Gap tests for runtime/learning_loop.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from runtime.hook_lifecycle import HookContext, HookPhase, HookRegistry
from runtime.learning_loop import LearningLoop, Outcome, _coerce_ok, _parse_ts


class TestHelpers:
    def test_parse_ts_garbage(self):
        assert _parse_ts("garbage").year == 1970
        assert _parse_ts(None).year == 1970  # type: ignore[arg-type]

    def test_coerce_ok(self):
        for v in ("false", "0", "no", "off", "none", "null", "", " FALSE "):
            assert _coerce_ok(v) is False
        assert _coerce_ok("true") is True
        assert _coerce_ok(1) is True
        assert _coerce_ok(0) is False
        assert _coerce_ok(None) is False

    def test_outcome_to_dict_and_pattern(self):
        o = Outcome(action="a", result={"k": 1}, success=True, gate="g",
                    timestamp="t", session_id="s")
        d = o.to_dict()
        assert d["action"] == "a" and d["session_id"] == "s"


class TestHooks:
    def test_bind_and_record_outcome(self):
        reg = HookRegistry()
        loop = LearningLoop()
        loop.bind_to_hooks(reg)
        ctx = MagicMock(spec=HookContext)
        ctx.action = "exec"
        ctx.results = {"response": {"ok": True, "gate": "probity"}}
        ctx.errors = []
        for h in reg._hooks.get(HookPhase.POST_RESPONSE, []):
            h(ctx)
        assert loop.outcome_count == 1

    def test_record_outcome_non_dict(self):
        reg = HookRegistry()
        loop = LearningLoop()
        loop.bind_to_hooks(reg)
        ctx = MagicMock(spec=HookContext)
        ctx.action = "exec"
        ctx.results = {"response": "not-a-dict"}
        ctx.errors = []
        for h in reg._hooks.get(HookPhase.POST_RESPONSE, []):
            h(ctx)
        assert loop.outcome_count == 0

    def test_record_error_hook(self):
        reg = HookRegistry()
        loop = LearningLoop()
        loop.bind_to_hooks(reg)
        ctx = MagicMock(spec=HookContext)
        ctx.action = "exec"
        ctx.errors = ["boom"]
        for h in reg._hooks.get(HookPhase.ON_ERROR, []):
            h(ctx)
        assert loop.outcome_count == 1
        # no errors -> skip
        ctx.errors = []
        for h in reg._hooks.get(HookPhase.ON_ERROR, []):
            h(ctx)
        assert loop.outcome_count == 1


class TestRecord:
    def test_non_dict_result_raises(self):
        with pytest.raises(TypeError):
            LearningLoop().record("a", result="x")  # type: ignore[arg-type]

    def test_batch_persist(self, tmp_path):
        p = tmp_path / "outcomes.json"
        loop = LearningLoop(persist_path=p)
        loop._persist_batch_size = 3
        for _i in range(3):
            loop.record("a", {"ok": True})
        assert p.exists()  # persisted at batch size

    def test_redacts_sensitive(self):
        loop = LearningLoop()
        o = loop.record("a", {"ok": True, "password": "x", "note": "y"})
        assert "password" not in o.result and o.result["note"] == "y"


class TestConsolidateRankInject:
    def test_consolidate_flushes_dirty(self, tmp_path):
        p = tmp_path / "o.json"
        loop = LearningLoop(persist_path=p)
        loop.record("a", {"ok": True})
        loop.record("a", {"ok": False})
        pats = loop.consolidate()
        assert len(pats) == 1 and pats[0].total == 2
        assert p.exists()

    def test_rank_default_patterns(self):
        loop = LearningLoop()
        loop.record("a", {"ok": True})
        loop.record("b", {"ok": False})
        loop.record("b", {"ok": False})
        ranked = loop.rank()
        assert ranked[0].action == "b"  # higher total first

    def test_inject(self):
        loop = LearningLoop()
        loop.record("a", {"ok": True})
        loop.record("a", {"ok": True})
        out = loop.inject()
        assert "Learned Patterns" in out and "reliable" in out

    def test_inject_none_when_few(self):
        loop = LearningLoop()
        loop.record("a", {"ok": True})
        assert loop.inject() == ""

    def test_inject_unreliable(self):
        loop = LearningLoop()
        loop.record("a", {"ok": False})
        loop.record("a", {"ok": False})
        assert "unreliable" in loop.inject()


class TestPersist:
    def test_persist_no_path(self):
        LearningLoop()._persist()  # no-op

    def test_persist_oserror(self, tmp_path):
        loop = LearningLoop(persist_path=tmp_path / "o.json")
        with patch("pathlib.Path.write_text", side_effect=OSError):
            loop._persist()  # warns only

    def test_flush_not_dirty(self, tmp_path):
        loop = LearningLoop(persist_path=tmp_path / "o.json")
        loop.flush()  # dirty False -> skip

    def test_clear_persists(self, tmp_path):
        p = tmp_path / "o.json"
        loop = LearningLoop(persist_path=p)
        loop.record("a", {})
        loop.clear()
        assert loop.outcome_count == 0
        assert json.loads(p.read_text()) == []

    def test_load_existing(self, tmp_path):
        p = tmp_path / "o.json"
        p.write_text(json.dumps([{"action": "x", "success": True}]))
        loop = LearningLoop(persist_path=p)
        assert loop.outcome_count == 1
        assert loop._outcomes[0].action == "x"

    def test_load_corrupt(self, tmp_path):
        p = tmp_path / "o.json"
        p.write_text("{bad json")
        loop = LearningLoop(persist_path=p)
        assert loop.outcome_count == 0

    def test_load_missing(self, tmp_path):
        loop = LearningLoop(persist_path=tmp_path / "none.json")
        assert loop.outcome_count == 0
