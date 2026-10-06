"""Tests for runtime/cross_tool_taint.py — cross-tool provenance tracking."""

from __future__ import annotations

import base64

from runtime.cross_tool_taint import (
    CrossToolTaintTracker,
    DataClassification,
    ToolSensitivity,
    _args_to_text,
    _extract_tokens,
    _try_b64_decode,
    _try_hex_decode,
)


class TestClassifyTool:
    def test_egress_names(self):
        t = CrossToolTaintTracker()
        for name in ("http_post", "send_email", "write_file", "shell_exec", "curl", "publish"):
            assert t.classify_tool(name) == ToolSensitivity.EGRESS, name

    def test_sensitive_names(self):
        t = CrossToolTaintTracker()
        for name in ("read_secret", "get_credential", "fetch_token"):
            sens = t.classify_tool(name)
            assert sens in (ToolSensitivity.SENSITIVE, ToolSensitivity.EGRESS), name

    def test_sensitive_pure(self):
        t = CrossToolTaintTracker()
        assert t.classify_tool("read_secret") == ToolSensitivity.SENSITIVE

    def test_normal(self):
        t = CrossToolTaintTracker()
        assert t.classify_tool("summarize") == ToolSensitivity.NORMAL


class TestClassifyResult:
    def test_none_is_normal(self):
        t = CrossToolTaintTracker()
        assert t.classify_result(None, ToolSensitivity.NORMAL) == DataClassification.NORMAL

    def test_untrusted_web_result(self):
        t = CrossToolTaintTracker()
        assert t.classify_result(
            "fetched html from http://example.com", ToolSensitivity.NORMAL,
        ) == DataClassification.UNTRUSTED

    def test_secret_pattern(self):
        t = CrossToolTaintTracker()
        assert t.classify_result(
            "key: AKIAIOSFODNN7EXAMPLE", ToolSensitivity.NORMAL,
        ) == DataClassification.SENSITIVE

    def test_secret_kv(self):
        t = CrossToolTaintTracker()
        assert t.classify_result(
            "api_key = supersecretvalue123", ToolSensitivity.NORMAL,
        ) == DataClassification.SENSITIVE

    def test_sensitive_tool(self):
        t = CrossToolTaintTracker()
        assert t.classify_result(
            "some data", ToolSensitivity.SENSITIVE,
        ) == DataClassification.SENSITIVE

    def test_normal_result(self):
        t = CrossToolTaintTracker()
        assert t.classify_result("42", ToolSensitivity.NORMAL) == DataClassification.NORMAL


class TestTokenExtraction:
    def test_min_length(self):
        toks = _extract_tokens("short abctoolongtoken123")
        assert "abctoolongtoken123" in toks
        assert "short" not in toks

    def test_b64_decoded_tokens(self):
        inner = "secret_token_xyz_123"
        blob = base64.b64encode(inner.encode()).decode()
        toks = _extract_tokens(f"data {blob} end")
        assert "secret_token_xyz_123" in toks

    def test_hex_decoded_tokens(self):
        inner = "hex_secret_99"
        blob = inner.encode().hex()
        toks = _extract_tokens(f"data {blob} end")
        assert "hex_secret_99" in toks

    def test_b64_decode_invalid(self):
        assert _try_b64_decode("!!!notb64!!!") is None

    def test_hex_decode_invalid(self):
        assert _try_hex_decode("zzzz") is None

    def test_args_to_text(self):
        assert _args_to_text({"a": 1, "b": "x"}) == "1 x"


class TestEdgeDrawing:
    def test_edge_on_shared_token(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "web_fetch", {}, result="token_ABCDEFGH123 in page")
        t.record_call("c2", "send_email", {"body": "saw token_ABCDEFGH123"})
        assert t.stats()["edges"] >= 1

    def test_no_edge_no_shared_token(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "web_fetch", {}, result="alpha_unique_1")
        t.record_call("c2", "summarize", {"text": "beta_unique_2"})
        assert t.stats()["edges"] == 0

    def test_no_args_no_edge(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "web_fetch", {}, result="token_ABCDEFGH123")
        t.record_call("c2", "send_email", {})
        assert t.stats()["edges"] == 0

    def test_manual_draw_edge(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "web_fetch", {})
        t.record_call("c2", "send_email", {})
        t.draw_edge("c1", "c2", "manual_evidence")
        assert t.stats()["edges"] == 1


class TestToxicFlow:
    def _toxic_tracker(self) -> CrossToolTaintTracker:
        """untrusted fetch -> sensitive read -> egress send."""
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="marker_UNTRUSTED777 from web html")
        t.draw_edge("u1", "s1", "marker_UNTRUSTED777")
        t.record_call("s1", "read_secret", {}, result="api_key=leaked_secret_value_9")
        t.draw_edge("s1", "e1", "leaked_secret_value_9")
        t.record_call("e1", "send_email", {"body": "marker_UNTRUSTED777"})
        return t

    def test_detects_toxic_flow(self):
        t = self._toxic_tracker()
        flows = t.detect_toxic_flows()
        assert len(flows) >= 1
        f = flows[0]
        assert f.source_call_id == "u1" and f.sink_call_id == "e1"
        assert f.path[0] == "u1" and f.path[-1] == "e1"
        d = f.to_dict()
        assert d["path"] and d["byte_count"] >= 0

    def test_no_toxic_without_sensitive(self):
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="marker_xyz123 web")
        t.draw_edge("u1", "e1", "marker_xyz123")
        t.record_call("e1", "send_email", {"body": "marker_xyz123"})
        # untrusted -> egress directly, never passed a sensitive node
        assert t.detect_toxic_flows() == []

    def test_no_untrusted_source(self):
        t = CrossToolTaintTracker()
        t.record_call("n1", "summarize", {}, result="plain data result")
        assert t.detect_toxic_flows() == []

    def test_cycle_safe(self):
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="marker_cyc_999 web")
        t.draw_edge("u1", "m1", "e")
        t.record_call("m1", "read_secret", {}, result="api_key=s1")
        t.draw_edge("m1", "u1", "e")  # cycle back
        t.draw_edge("m1", "e1", "e")
        t.record_call("e1", "send_email", {})
        flows = t.detect_toxic_flows()
        assert isinstance(flows, list)  # terminates, no hang


class TestCheckEgress:
    def test_non_egress_returns_none(self):
        t = CrossToolTaintTracker()
        assert t.check_egress("x", "summarize", {"a": 1}) is None

    def test_empty_args(self):
        t = CrossToolTaintTracker()
        assert t.check_egress("x", "send_email", {}) is None

    def test_toxic_egress_detected(self):
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="marker_EGRESS88 web html")
        t.record_call("s1", "read_secret", {}, result="marker_EGRESS88 and api_key=k1")
        t.draw_edge("u1", "s1", "marker_EGRESS88")
        flow = t.check_egress("e1", "send_email", {"body": "marker_EGRESS88"})
        assert flow is not None
        assert flow.sink_call_id == "e1"
        assert "s1" in flow.path or "u1" in flow.path

    def test_benign_egress(self):
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="marker_DIFFERENT web")
        assert t.check_egress("e1", "send_email", {"body": "no_overlap_here_9"}) is None

    def test_reset(self):
        t = CrossToolTaintTracker()
        t.record_call("u1", "web_fetch", {}, result="x")
        t.reset()
        assert t.stats()["calls"] == 0
        assert t.stats()["edges"] == 0
        assert t.stats()["toxic_flows"] == 0
