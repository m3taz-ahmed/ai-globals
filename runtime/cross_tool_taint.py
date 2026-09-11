#!/usr/bin/env python3
"""Cross-tool provenance tracking with toxic-flow detection (inspired by cyclops).

Tracks data flow across MCP tool calls to detect untrusted→sensitive→egress
patterns. Every tool result is classified (untrusted/sensitive/normal), and
edges are drawn between calls when distinctive tokens from a prior result
appear in a later call's arguments (including base64/hex-decoded forms).

A flow is **toxic** iff a directed path untrusted→sensitive→egress exists in
the call graph. The tracker uses a simple dict-based adjacency list (no
networkx dependency) and BFS for path detection.
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

_logger = logging.getLogger(__name__)

# -- Classifications --------------------------------------------------------


class DataClassification(str, Enum):
    """Classification of a tool call's result data."""

    UNTRUSTED = "untrusted"
    SENSITIVE = "sensitive"
    NORMAL = "normal"


class ToolSensitivity(str, Enum):
    """Sensitivity category of a tool based on its name."""

    EGRESS = "egress"
    SENSITIVE = "sensitive"
    NORMAL = "normal"


# -- Data structures --------------------------------------------------------


@dataclass
class ToolCall:
    """A recorded tool call with classification.

    Attributes:
        call_id: Unique identifier for this call.
        tool_name: Name of the tool invoked.
        args: Arguments passed to the tool.
        result: The result string, if available.
        classification: Data classification of the result.
        timestamp: Unix timestamp of when the call was recorded.
        parent_call_id: Optional ID of the parent call in a chain.
    """

    call_id: str
    tool_name: str
    args: dict[str, Any]
    result: str | None
    classification: DataClassification
    timestamp: float
    parent_call_id: str | None = None


@dataclass
class ToxicFlow:
    """A detected toxic data flow from an untrusted source to an egress sink.

    Attributes:
        source_call_id: The originating untrusted call.
        sink_call_id: The terminating egress call.
        path: Ordered list of call IDs forming the flow.
        evidence: The token that linked calls in the flow.
        byte_count: Size of the evidence token in bytes.
    """

    source_call_id: str
    sink_call_id: str
    path: list[str]
    evidence: str
    byte_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "source_call_id": self.source_call_id,
            "sink_call_id": self.sink_call_id,
            "path": list(self.path),
            "evidence": self.evidence,
            "byte_count": self.byte_count,
        }


# -- Patterns ---------------------------------------------------------------

# Tool-name patterns for sensitivity classification.
# Use (?:^|[_\-.:/]) boundaries instead of \b because underscores are
# word characters and \b won't fire between "http" and "_post".
_EGRESS_PATTERNS = re.compile(
    r"(?:^|[_\-.:/\s])(?:http|post|send|write|upload|publish|deploy|exec|"
    r"run|shell|curl|fetch|request|submit|emit|flush|push|put)(?:$|[_\-.:/\s])",
    re.IGNORECASE,
)
_SENSITIVE_PATTERNS = re.compile(
    r"(?:^|[_\-.:/\s])(?:read|secret|credential|key|token|password|env|"
    r"config|vault|sensitive|private|auth)(?:$|[_\-.:/\s])",
    re.IGNORECASE,
)

# Result classification: untrusted if from web/fetch
_UNTRUSTED_RESULT_PATTERNS = re.compile(
    r"\b(?:web|fetch|scrape|crawl|url|http|html|rss|feed)\b",
    re.IGNORECASE,
)

# Sensitive content in results
_SECRET_RESULT_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(
        r"(?:api[_-]?key|secret|password|token|credential)\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
]

# Minimum token length to be considered "distinctive"
_MIN_TOKEN_LEN = 8


# -- Token extraction helpers -----------------------------------------------


def _try_b64_decode(blob: str) -> str | None:
    """Attempt base64 decode, returning a string or None."""
    try:
        padding = len(blob) % 4
        if padding:
            blob += "=" * (4 - padding)
        decoded = base64.b64decode(blob, validate=True)
        return decoded.decode("utf-8", errors="ignore")
    except (binascii.Error, ValueError):
        return None


def _try_hex_decode(blob: str) -> str | None:
    """Attempt hex decode, returning a string or None."""
    try:
        decoded = bytes.fromhex(blob)
        return decoded.decode("utf-8", errors="ignore")
    except ValueError:
        return None


def _extract_tokens(text: str) -> set[str]:
    """Extract distinctive tokens (>8 chars) from text.

    Also includes base64-decoded and hex-decoded forms when decodable.
    """
    tokens: set[str] = set()
    token_pattern = rf"[A-Za-z0-9_\-]{{{_MIN_TOKEN_LEN},}}"
    for m in re.finditer(token_pattern, text):
        tokens.add(m.group())
    for m in re.finditer(r"[A-Za-z0-9+/]{16,}={0,2}", text):
        decoded = _try_b64_decode(m.group())
        if decoded:
            for t in re.finditer(token_pattern, decoded):
                tokens.add(t.group())
    for m in re.finditer(r"[0-9a-fA-F]{16,}", text):
        decoded = _try_hex_decode(m.group())
        if decoded:
            for t in re.finditer(token_pattern, decoded):
                tokens.add(t.group())
    return tokens


def _args_to_text(args: dict[str, Any]) -> str:
    """Flatten args dict to a single searchable text string."""
    return " ".join(str(v) for v in args.values())


def _find_shared_token(
    src_tokens: set[str],
    arg_text: str,
    arg_tokens: set[str],
    src_result: str,
) -> str:
    """Find the best evidence token shared between source and args.

    Checks both directions: source token in arg text, and arg token
    in source result text. Returns the longest match or empty string.
    """
    for tok in sorted(src_tokens, key=len, reverse=True):
        if tok in arg_text:
            return tok
    for tok in sorted(arg_tokens, key=len, reverse=True):
        if tok in src_result:
            return tok
    return ""


def _result_overlaps_args(
    result: str, arg_text: str, arg_tokens: set[str],
) -> bool:
    """Check if result tokens appear in args or arg tokens in result."""
    result_tokens = _extract_tokens(result)
    if any(tok in arg_text for tok in result_tokens):
        return True
    return any(tok in result for tok in arg_tokens)


# -- BFS path-finding (module-level) ----------------------------------------


def _bfs_toxic_paths(
    source_id: str,
    calls: dict[str, ToolCall],
    adjacency: dict[str, list[tuple[str, str]]],
    classify_fn: Any,  # callable: str -> ToolSensitivity
) -> list[ToxicFlow]:
    """BFS from an untrusted source to find toxic paths to egress."""
    results: list[ToxicFlow] = []
    queue: list[tuple[str, list[str], bool, str]] = [
        (source_id, [source_id], False, ""),
    ]
    visited: set[tuple[str, bool]] = set()
    while queue:
        curr_id, path, passed_sensitive, evidence = queue.pop(0)
        state_key = (curr_id, passed_sensitive)
        if state_key in visited:
            continue
        visited.add(state_key)
        curr_call = calls.get(curr_id)
        if curr_call is None:
            continue
        now_sensitive = _check_node_toxic(
            curr_call, classify_fn, passed_sensitive, path, evidence,
            source_id, results,
        )
        for sink_id, ev in adjacency.get(curr_id, []):
            if sink_id in path:
                continue
            queue.append((sink_id, [*path, sink_id], now_sensitive, evidence or ev))
    return results


def _check_node_toxic(
    curr_call: ToolCall,
    classify_fn: Any,
    passed_sensitive: bool,
    path: list[str],
    evidence: str,
    source_id: str,
    results: list[ToxicFlow],
) -> bool:
    """Check if current node is a toxic egress; append to results if so.

    Returns the updated ``now_sensitive`` flag.
    """
    is_sensitive = curr_call.classification == DataClassification.SENSITIVE
    is_egress = classify_fn(curr_call.tool_name) == ToolSensitivity.EGRESS
    now_sensitive = passed_sensitive or is_sensitive
    if is_egress and now_sensitive and len(path) >= 2:
        results.append(ToxicFlow(
            source_call_id=source_id, sink_call_id=curr_call.call_id,
            path=list(path), evidence=evidence,
            byte_count=len(evidence.encode("utf-8")),
        ))
    return now_sensitive


def _find_path_through_sensitive(
    source_id: str, arg_text: str, arg_tokens: set[str],
    calls: dict[str, ToolCall], adjacency: dict[str, list[tuple[str, str]]],
) -> list[str] | None:
    """BFS from source; find a path through a sensitive node whose
    result tokens also appear in the egress args. Returns path or None.
    """
    queue: list[tuple[str, list[str], bool]] = [(source_id, [source_id], False)]
    visited: set[tuple[str, bool]] = set()
    while queue:
        curr_id, path, passed_sensitive = queue.pop(0)
        state_key = (curr_id, passed_sensitive)
        if state_key in visited:
            continue
        visited.add(state_key)
        curr_call = calls.get(curr_id)
        if curr_call is None:
            continue
        result = _check_sensitive_overlap(
            curr_call, passed_sensitive, path, arg_text, arg_tokens)
        if result is not None:
            return result
        _enqueue_neighbors(
            curr_id, path, curr_call, passed_sensitive, adjacency, queue)
    return None


def _enqueue_neighbors(
    curr_id: str, path: list[str], curr_call: ToolCall,
    passed_sensitive: bool,
    adjacency: dict[str, list[tuple[str, str]]],
    queue: list[tuple[str, list[str], bool]],
) -> None:
    """Enqueue unvisited neighbors with updated sensitive flag."""
    now_sensitive = passed_sensitive or (
        curr_call.classification == DataClassification.SENSITIVE)
    for sink_id, _ev in adjacency.get(curr_id, []):
        if sink_id not in path:
            queue.append((sink_id, [*path, sink_id], now_sensitive))


def _check_sensitive_overlap(
    curr_call: ToolCall, passed_sensitive: bool, path: list[str],
    arg_text: str, arg_tokens: set[str],
) -> list[str] | None:
    """Check if current node is sensitive and overlaps with egress args."""
    is_sensitive = curr_call.classification == DataClassification.SENSITIVE
    now_sensitive = passed_sensitive or is_sensitive
    if now_sensitive and curr_call.result is not None and _result_overlaps_args(
        curr_call.result, arg_text, arg_tokens
    ):
        return list(path)
    return None


# -- Tracker ----------------------------------------------------------------


class CrossToolTaintTracker:
    """Tracks cross-tool data flow and detects toxic flows.

    Uses a dict-based adjacency list (no external graph library). An edge
    is drawn from call A to call B when a distinctive token from A's result
    appears in B's arguments (checking base64/hex-decoded forms too).

    Thread-safe via ``RLock``.
    """

    def __init__(self) -> None:
        self._rlock = threading.RLock()
        self._calls: dict[str, ToolCall] = {}
        self._adjacency: dict[str, list[tuple[str, str]]] = {}
        self._edges: int = 0

    # -- Classification ---------------------------------------------------

    def classify_tool(self, tool_name: str) -> ToolSensitivity:
        """Classify a tool by its name patterns.

        - EGRESS: http/post/send/write/exec/shell/fetch/etc.
        - SENSITIVE: read/secret/credential/key/token/etc.
        - NORMAL: everything else.
        """
        if _EGRESS_PATTERNS.search(tool_name):
            return ToolSensitivity.EGRESS
        if _SENSITIVE_PATTERNS.search(tool_name):
            return ToolSensitivity.SENSITIVE
        return ToolSensitivity.NORMAL

    def classify_result(
        self, result: str, tool_sensitivity: ToolSensitivity,
    ) -> DataClassification:
        """Classify a tool result.

        - UNTRUSTED: result from a web/fetch-style tool.
        - SENSITIVE: result contains secret patterns.
        - NORMAL: otherwise.
        """
        if result is None:
            return DataClassification.NORMAL
        if _UNTRUSTED_RESULT_PATTERNS.search(result):
            return DataClassification.UNTRUSTED
        for pat in _SECRET_RESULT_PATTERNS:
            if pat.search(result):
                return DataClassification.SENSITIVE
        if tool_sensitivity == ToolSensitivity.SENSITIVE:
            return DataClassification.SENSITIVE
        return DataClassification.NORMAL

    # -- Recording --------------------------------------------------------

    def record_call(
        self, call_id: str, tool_name: str, args: dict[str, Any],
        result: str | None = None,
    ) -> ToolCall:
        """Record a tool call, classify it, and draw edges from prior calls."""
        sensitivity = self.classify_tool(tool_name)
        classification = (
            self.classify_result(result, sensitivity)
            if result is not None else DataClassification.NORMAL
        )
        call = ToolCall(
            call_id=call_id, tool_name=tool_name, args=args,
            result=result, classification=classification, timestamp=time.time(),
        )
        with self._rlock:
            self._calls[call_id] = call
            self._adjacency.setdefault(call_id, [])
            self._draw_edges_for_new_call(call)
        return call

    def _draw_edges_for_new_call(self, new_call: ToolCall) -> None:
        """Draw edges from prior calls whose result tokens appear in new args."""
        if not new_call.args:
            return
        arg_text = _args_to_text(new_call.args)
        if not arg_text:
            return
        arg_tokens = _extract_tokens(arg_text)
        for src_id, src_call in self._calls.items():
            if src_id == new_call.call_id or src_call.result is None:
                continue
            src_tokens = _extract_tokens(src_call.result)
            if not src_tokens:
                continue
            evidence = _find_shared_token(
                src_tokens, arg_text, arg_tokens, src_call.result,
            )
            if not evidence:
                continue
            self._adjacency.setdefault(src_id, []).append(
                (new_call.call_id, evidence),
            )
            self._edges += 1

    def draw_edge(
        self, source_call_id: str, sink_call_id: str, evidence: str,
    ) -> None:
        """Manually add an edge between two calls."""
        with self._rlock:
            self._adjacency.setdefault(source_call_id, []).append(
                (sink_call_id, evidence),
            )
            self._edges += 1

    # -- Detection --------------------------------------------------------

    def detect_toxic_flows(self) -> list[ToxicFlow]:
        """Find all untrusted→sensitive→egress paths in the call graph."""
        flows: list[ToxicFlow] = []
        with self._rlock:
            for src_id, src_call in self._calls.items():
                if src_call.classification != DataClassification.UNTRUSTED:
                    continue
                flows.extend(_bfs_toxic_paths(
                    src_id, self._calls, self._adjacency, self.classify_tool,
                ))
        return flows

    def check_egress(
        self, call_id: str, tool_name: str, args: dict[str, Any],
    ) -> ToxicFlow | None:
        """Check if an egress call would be toxic BEFORE execution."""
        if self.classify_tool(tool_name) != ToolSensitivity.EGRESS:
            return None
        with self._rlock:
            return self._check_egress_locked(call_id, args)

    def _check_egress_locked(
        self, call_id: str, args: dict[str, Any],
    ) -> ToxicFlow | None:
        """Inner check_egress logic (caller holds the lock)."""
        arg_text = _args_to_text(args)
        if not arg_text:
            return None
        arg_tokens = _extract_tokens(arg_text)
        for src_id, src_call in self._calls.items():
            if src_call.classification != DataClassification.UNTRUSTED:
                continue
            if src_call.result is None:
                continue
            flow = self._try_toxic_from_source(
                src_id, src_call, call_id, arg_text, arg_tokens,
            )
            if flow is not None:
                return flow
        return None

    def _try_toxic_from_source(
        self, src_id: str, src_call: ToolCall, call_id: str,
        arg_text: str, arg_tokens: set[str],
    ) -> ToxicFlow | None:
        """Check if a single untrusted source produces a toxic flow."""
        src_tokens = _extract_tokens(src_call.result or "")
        if not src_tokens:
            return None
        evidence = _find_shared_token(
            src_tokens, arg_text, arg_tokens, src_call.result or "",
        )
        if not evidence:
            return None
        path = _find_path_through_sensitive(
            src_id, arg_text, arg_tokens, self._calls, self._adjacency,
        )
        if path is not None:
            return ToxicFlow(
                source_call_id=src_id, sink_call_id=call_id,
                path=[*path, call_id], evidence=evidence,
                byte_count=len(evidence.encode("utf-8")),
            )
        return None

    # -- Utilities --------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded calls and edges."""
        with self._rlock:
            self._calls.clear()
            self._adjacency.clear()
            self._edges = 0

    def stats(self) -> dict[str, int]:
        """Return counts of calls, edges, and toxic flows."""
        with self._rlock:
            return {
                "calls": len(self._calls),
                "edges": self._edges,
                "toxic_flows": len(self.detect_toxic_flows()),
            }
