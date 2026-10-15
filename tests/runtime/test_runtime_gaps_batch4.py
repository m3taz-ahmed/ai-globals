"""Gap coverage batch: audit, commands, confidence_gate, context_manager, cost_attribution, cross_tool_taint."""
from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import patch

import runtime.audit as audit_mod
import runtime.cross_tool_taint as ctt
from runtime.audit import AuditLogger
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
