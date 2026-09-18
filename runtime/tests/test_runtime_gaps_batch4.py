"""Gap coverage batch: audit, commands, confidence_gate, context_manager, cost_attribution, cross_tool_taint."""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

import pytest

import runtime.audit as audit_mod
import runtime.cross_tool_taint as ctt
from runtime.audit import AuditLogger
from runtime.commands import Command, CommandBus, CommandError, CommandResult, CommandStatus
from runtime.confidence_gate import ConfidenceGate, ConfidenceLevel, Evidence
from runtime.context_manager import ContextManager, Message, Role
from runtime.cost_attribution import (
    CostAttribution,
    CostAttributionError,
    CostRecord,
)
from runtime.cross_tool_taint import (
    CrossToolTaintTracker,
    DataClassification,
    ToolCall,
)


class TestAudit:
    def test_audit_key_empty_file(self, tmp_path: Path, monkeypatch):
        (tmp_path / "state").mkdir()
        (tmp_path / "state" / "audit.key").write_bytes(b"")
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        monkeypatch.delenv("AIZEE_AUDIT_KEY", raising=False)
        monkeypatch.delenv("AIZEE_AUDIT_KEY_FILE", raising=False)
        audit_mod._audit_key_cache = None
        try:
            key = audit_mod._get_audit_key()
            assert len(key) == 32
        finally:
            audit_mod._audit_key_cache = None

    def test_retention_days_bad_env(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("AIZEE_AUDIT_RETENTION_DAYS", "garbage")
        logger = AuditLogger(tmp_path)
        assert logger._retention_days == AuditLogger._DEFAULT_RETENTION_DAYS

    def test_last_hash_empty_file(self, tmp_path: Path):
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text("")
        assert logger._last_hash() == audit_mod._GENESIS_HASH

    def test_last_hash_oserror_fallback(self, tmp_path: Path):
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text('{"hash": "abc123"}\n')
        real_open = Path.open

        def flaky(self, mode="r", *a, **k):
            if "b" in mode:
                raise OSError("denied")
            return real_open(self, mode, *a, **k)

        with patch.object(Path, "open", flaky):
            assert logger._last_hash() == "abc123"

    def test_read_entries_blank_lines(self, tmp_path: Path):
        logger = AuditLogger(tmp_path)
        logger.log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.log_file.write_text('\n\n{"type": "policy", "ts": "t"}\n\n')
        entries = logger.read_entries()
        assert len(entries) == 1


class _Cmd(Command):
    def __init__(self, name: str, result: CommandResult | None = None, exc: Exception | None = None, rb: CommandResult | None = None):
        self.name = name
        self._result = result
        self._exc = exc
        self._rb = rb

    def execute(self, context):
        if self._exc is not None:
            raise self._exc
        return self._result or CommandResult(status=CommandStatus.COMPLETED)

    def rollback(self, context):
        return self._rb or CommandResult(status=CommandStatus.SKIPPED)


class TestCommands:
    def test_command_error_reraise(self):
        bus = CommandBus([_Cmd("a", exc=CommandError("a", "bad"))])
        with pytest.raises(CommandError):
            bus.execute({})

    def test_generic_exception(self):
        bus = CommandBus([_Cmd("a", exc=RuntimeError("x"))])
        with pytest.raises(CommandError):
            bus.execute({})

    def test_skipped(self):
        bus = CommandBus([
            _Cmd("s", result=CommandResult(status=CommandStatus.SKIPPED)),
            _Cmd("ok", result=CommandResult(status=CommandStatus.COMPLETED)),
        ])
        res = bus.execute({})
        assert res[-1].status == CommandStatus.COMPLETED

    def test_failed_no_rollback(self):
        bus = CommandBus(
            [_Cmd("f", result=CommandResult(status=CommandStatus.FAILED, error="x"))],
            rollback_on_failure=False,
        )
        res = bus.execute({})
        assert res[0].status == CommandStatus.FAILED

    def test_rollback_skipped_not_appended(self):
        ok = _Cmd("ok", result=CommandResult(status=CommandStatus.COMPLETED))
        fail = _Cmd("f", result=CommandResult(status=CommandStatus.FAILED, error="x"))
        bus = CommandBus([ok, fail])
        res = bus.execute({})
        # rollback of ok returns SKIPPED -> not appended
        assert all(r.status != CommandStatus.SKIPPED for r in res)

    def test_rollback_exception(self):
        class BadRb(_Cmd):
            def rollback(self, context):
                raise RuntimeError("rb fail")

        ok = BadRb("ok", result=CommandResult(status=CommandStatus.COMPLETED))
        fail = _Cmd("f", result=CommandResult(status=CommandStatus.FAILED, error="x"))
        bus = CommandBus([ok, fail])
        res = bus.execute({})
        assert any("rollback error" in (r.error or "") for r in res)


class TestConfidenceGate:
    def test_bad_threshold(self):
        with pytest.raises(ValueError):
            ConfidenceGate(threshold=1.5)

    def test_bad_evidence_weight(self):
        g = ConfidenceGate()
        with pytest.raises(ValueError):
            g.add_evidence(Evidence(source="s", passed=True, weight=1.5))

    def test_weights_not_one(self):
        g = ConfidenceGate()
        g.add_evidence_simple("a", True, weight=0.3)
        g.add_evidence_simple("b", True, weight=0.3)
        with pytest.raises(ValueError):
            g.evaluate()

    def test_critical_level(self):
        g = ConfidenceGate(normalize=True)
        g.add_evidence_simple("a", False, weight=1.0)
        v = g.evaluate()
        assert v.level == ConfidenceLevel.CRITICAL
        assert v.confident is False


class TestContextManager:
    def test_split_fits_window(self):
        cm = ContextManager()
        msgs = [Message(role=Role.USER, content="hi")]
        recent, middle = cm._split_recent(msgs, 6)
        assert len(recent) == 1 and middle == []

    def test_split_group_boundary(self):
        cm = ContextManager()
        msgs = [
            Message(role=Role.USER, content="a", group_id="g1"),
            Message(role=Role.ASSISTANT, content="b", group_id="g1"),
            Message(role=Role.USER, content="c"),
            Message(role=Role.ASSISTANT, content="d"),
        ]
        _recent, middle = cm._split_recent(msgs, 2)
        # boundary must not split g1 group
        assert all(m.group_id == "g1" for m in middle if m.group_id)

    def test_compress_middle_empty(self):
        cm = ContextManager()
        assert cm._compress_middle([], 100) == []


class TestCostAttribution:
    def test_error_init(self):
        e = CostAttributionError("bad", context={"x": 1})
        assert "bad" in str(e)

    def test_nonfinite_cost(self):
        ca = CostAttribution()
        with pytest.raises(CostAttributionError):
            ca.record(CostRecord("a", "m/x", 1, 1, float("inf")))

    def test_negative_cost(self):
        ca = CostAttribution()
        with pytest.raises(CostAttributionError):
            ca.record(CostRecord("a", "m/x", 1, 1, -1.0))

    def test_unexpected_provider(self):
        ca = CostAttribution(expected_providers={"openai"})
        anomalies = ca.record(CostRecord("a", "anthropic/claude", 1, 1, 0.5))
        assert any(a.anomaly_type.value == "unexpected_provider" for a in anomalies)

    def test_budget_breach(self):
        ca = CostAttribution(budget_per_agent={"a": 1.0})
        ca.record(CostRecord("a", "m", 1, 1, 2.0))
        anomalies = ca.detect_anomalies()
        assert any(a.anomaly_type.value == "budget_breach" for a in anomalies)

    def test_set_budget_nonfinite(self):
        ca = CostAttribution()
        with pytest.raises(CostAttributionError):
            ca.set_budget("a", float("nan"))

    def test_set_budget_negative(self):
        ca = CostAttribution()
        with pytest.raises(CostAttributionError):
            ca.set_budget("a", -5.0)


class TestCrossToolTaint:
    def test_b64_token_extraction(self):
        blob = base64.b64encode(b"SECRETVALUE12345").decode()
        tokens = ctt._extract_tokens(f"data {blob} end")
        assert "SECRETVALUE12345" in tokens

    def test_hex_token_extraction(self):
        blob = b"HELLOTOKEN1234".hex()
        tokens = ctt._extract_tokens(f"data {blob} end")
        assert "HELLOTOKEN1234" in tokens

    def test_find_shared_token_arg_in_result(self):
        tok = ctt._find_shared_token(
            {"srctok123"}, "no match here", {"othertoken45"}, "xxothertoken45yy"
        )
        assert tok == "othertoken45"

    def test_result_overlaps_args_second_branch(self):
        assert ctt._result_overlaps_args(
            "prefixMYTOKENLONGsuffix", "nomatch", {"MYTOKENLONG"}
        ) is True

    def test_bfs_missing_call(self):
        call = ToolCall("s", "fetch_x", {}, "r", DataClassification.UNTRUSTED, 0.0)
        flows = ctt._bfs_toxic_paths(
            "s", {"s": call}, {"s": [("ghost", "e")]}, lambda t: None
        )
        assert flows == []

    def test_bfs_visited_skip(self):
        a = ToolCall("a", "read_x", {}, "r", DataClassification.SENSITIVE, 0.0)
        calls = {"a": a}
        adjacency = {"a": [("a", "e1")], }
        # self-loop: a -> a enqueued then visited
        flows = ctt._bfs_toxic_paths("a", calls, adjacency, lambda t: None)
        assert flows == []

    def test_find_path_exhausts(self):
        a = ToolCall("a", "read_x", {}, "r", DataClassification.NORMAL, 0.0)
        out = ctt._find_path_through_sensitive("a", "txt", {"t12345678"}, {"a": a}, {})
        assert out is None

    def test_enqueue_cycle_skips(self):
        a = ToolCall("a", "read_x", {}, "r", DataClassification.NORMAL, 0.0)
        b = ToolCall("b", "read_y", {}, "r", DataClassification.NORMAL, 0.0)
        calls = {"a": a, "b": b}
        adjacency = {"a": [("b", "e")], "b": [("a", "e")]}
        out = ctt._find_path_through_sensitive("a", "txt", {"t12345678"}, calls, adjacency)
        assert out is None

    def test_record_call_empty_arg_text(self):
        t = CrossToolTaintTracker()
        c = t.record_call("c1", "some_tool", {"a": ""}, result="x")
        assert c.call_id == "c1"

    def test_edge_skips_no_src_tokens(self):
        t = CrossToolTaintTracker()
        t.record_call("s", "read_secret", {}, result="ok")  # no long tokens
        t.record_call("n", "http_post", {"data": "sometoken123"}, result=None)
        # no edge should be drawn (source had no tokens)
        assert t._adjacency.get("s") == [] or t.stats()["edges"] == 0

    def test_egress_skips_non_untrusted(self):
        t = CrossToolTaintTracker()
        t.record_call("s", "read_file", {}, result="secrettoken99")
        out = t.check_egress("e1", "http_post", {"data": "secrettoken99"})
        assert out is None

    def test_egress_skips_none_result(self):
        t = CrossToolTaintTracker()
        t._calls["u"] = ToolCall("u", "fetch", {}, None, DataClassification.UNTRUSTED, 0.0)
        out = t.check_egress("e1", "http_post", {"data": "secrettoken99"})
        assert out is None

    def test_egress_no_src_tokens(self):
        t = CrossToolTaintTracker()
        t._calls["u"] = ToolCall("u", "fetch", {}, "ok", DataClassification.UNTRUSTED, 0.0)
        out = t.check_egress("e1", "http_post", {"data": "secrettoken99"})
        assert out is None

    def test_egress_evidence_no_path(self):
        t = CrossToolTaintTracker()
        t._calls["u"] = ToolCall(
            "u", "fetch", {}, "leaked secrettoken99", DataClassification.UNTRUSTED, 0.0
        )
        # token in args but no path through sensitive node -> None
        out = t.check_egress("e1", "http_post", {"data": "secrettoken99"})
        assert out is None
