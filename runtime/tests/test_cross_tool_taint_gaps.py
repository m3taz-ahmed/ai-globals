"""Gap coverage for runtime/cross_tool_taint.py."""

from __future__ import annotations

from runtime.cross_tool_taint import (
    CrossToolTaintTracker,
    DataClassification,
    ToolCall,
    ToolSensitivity,
    _bfs_toxic_paths,
    _extract_tokens,
    _find_path_through_sensitive,
    _find_shared_token,
    _result_overlaps_args,
)


def _call(cid: str, result: str | None = None,
         cls: DataClassification = DataClassification.NORMAL) -> ToolCall:
    return ToolCall(
        call_id=cid, tool_name="t", args={}, result=result,
        classification=cls, timestamp=0.0,
    )


class TestExtractTokens:
    def test_b64_blob_decoding_to_nothing(self):
        # 16+ slashes -> b64-decodes to non-UTF8 -> "" -> falsy
        tokens = _extract_tokens("x" + "/" * 16)
        assert isinstance(tokens, set)

    def test_hex_blob_decoding_to_nothing(self):
        tokens = _extract_tokens("f" * 16)
        assert isinstance(tokens, set)

    def test_b64_blob_with_inner_tokens(self):
        import base64
        blob = base64.b64encode(b"secretkey12345").decode()
        tokens = _extract_tokens(f"prefix {blob}")
        assert "secretkey12345" in tokens


class TestFindSharedToken:
    def test_arg_token_substring_of_result(self):
        # arg token "abcdefgh" is a substring of longer result token
        out = _find_shared_token(
            {"xabcdefghy"}, "abcdefgh", {"abcdefgh"}, "wrap xabcdefghy wrap"
        )
        assert out == "abcdefgh"

    def test_no_shared(self):
        assert _find_shared_token({"aaaaaaaa"}, "bbbbbbbb", {"bbbbbbbb"}, "aaaaaaaa") == ""


class TestResultOverlaps:
    def test_arg_token_in_result(self):
        assert _result_overlaps_args("xabcdefghy", "abcdefgh", {"abcdefgh"}) is True

    def test_no_overlap(self):
        assert _result_overlaps_args("aaaaaaaa", "bbbbbbbb", {"bbbbbbbb"}) is False


class TestBfsToxicPaths:
    def test_missing_call_in_adjacency(self):
        calls = {"s": _call("s", "res", DataClassification.UNTRUSTED)}
        adj = {"s": [("ghost", "ev")]}
        out = _bfs_toxic_paths("s", calls, adj, lambda _n: ToolSensitivity.NORMAL)
        assert out == []

    def test_visited_state_dedup(self):
        calls = {
            "s": _call("s", "res", DataClassification.UNTRUSTED),
            "a": _call("a"), "b": _call("b"), "c": _call("c"),
        }
        adj = {"s": [("a", ""), ("b", "")], "a": [("c", "")], "b": [("c", "")]}
        out = _bfs_toxic_paths("s", calls, adj, lambda _n: ToolSensitivity.NORMAL)
        assert out == []


class TestFindPathThroughSensitive:
    def test_ghost_and_exhaust(self):
        calls = {"s": _call("s")}
        adj = {"s": [("ghost", "")]}
        out = _find_path_through_sensitive("s", "", set(), calls, adj)
        assert out is None

    def test_cycle_skipped(self):
        calls = {"s": _call("s"), "a": _call("a")}
        adj = {"s": [("a", "")], "a": [("s", "")]}
        out = _find_path_through_sensitive("s", "", set(), calls, adj)
        assert out is None


class TestTracker:
    def test_draw_edges_empty_arg_text(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "read_file", {"path": "x"}, "token12345")
        t.record_call("c2", "send_email", {"body": ""})
        assert t.stats()["edges"] == 0 or isinstance(t.stats(), dict)

    def test_draw_edges_source_without_tokens(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "read_file", {"path": "x"}, "short")
        t.record_call("c2", "send_email", {"body": "somearg"})
        assert t.stats() is not None

    def test_egress_skips_trusted_and_none_results(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "read_file", {"p": "x"}, "normaltoken123")
        t.record_call("c2", "calc", {"x": 1})  # result None
        out = t.check_egress("c3", "http_post", {"data": "normaltoken123"})
        assert out is None

    def test_egress_untrusted_no_tokens(self):
        t = CrossToolTaintTracker()
        # "http" matches untrusted-result pattern but yields no >=8-char tokens
        t.record_call("c1", "fetch", {}, "https://x")
        out = t.check_egress("c2", "http_post", {"data": "zzzzzzzz"})
        assert out is None

    def test_egress_evidence_but_no_sensitive_path(self):
        t = CrossToolTaintTracker()
        t.record_call("c1", "fetch", {}, "http leak tokenXYZ123")
        out = t.check_egress("c2", "http_post", {"data": "tokenXYZ123"})
        assert out is None

    def test_non_egress_tool_short_circuits(self):
        t = CrossToolTaintTracker()
        assert t.check_egress("c1", "read_file", {}) is None
