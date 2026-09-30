#!/usr/bin/env python3
"""Unified Enforcement Path (UEP) - puts controls on the action path.

Closes the governance-theater gap (ARCH-06): ``AgentGateway`` and
``McpFirewall`` previously existed but no live traffic flowed through them.
This module is the single choke point every MCP tool call traverses:

    outbound call  -> firewall (allow/ask/deny) -> gateway PRE_LLM -> spawn
    inbound result -> gateway POST_EXECUTION (injection / secret redaction)

Layering by direction:
- Outbound (McpClient -> external servers): McpFirewall + AgentGateway.
  The firewall catch-all may return ``ask`` -> resolved via ApprovalCache
  or an explicit ``approved=True`` argument (HITL gate).
- Inbound (aizee_mcp server tools): RBAC (aizee_mcp/rbac.py) + AgentGateway
  request/response guardrails. The firewall is NOT applied to the server's
  own tools - its catch-all is ``require_approval`` for *external* calls.

Kernel.act() applies the PRE_LLM phase (secret leakage in prompt fields).
Destructive-command policy for local exec stays with Probity/Guardian,
which carry deny/ask semantics; the gateway governs the MCP wire path.

Enforcement degrades safely: when no kernel can be built the helper warns
and returns ``None`` (allow) unless ``AIZEE_ENFORCE_STRICT=1`` is set, in
which case construction failure denies the call (fail-closed).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from runtime.agent_gateway import (
    GuardrailContext,
    Verdict,
    redact_secrets,
)
from runtime.enums import Decision

_logger = logging.getLogger(__name__)

_KERNELS: dict[str, Any] = {}
_KERNELS_LOCK = threading.Lock()

# Action kwargs that carry user/agent prompt text. File payloads (``content``,
# ``command``) are deliberately excluded - they are governed by
# Probity/Guardian, not by prompt-level secret scanning.
_PROMPT_KEYS = ("message", "prompt", "query", "request", "task")


def _strict() -> bool:
    """True when enforcement failures must deny instead of degrade."""
    return os.environ.get("AIZEE_ENFORCE_STRICT") == "1"


def shared_kernel(root: Path) -> Any | None:
    """Return a process-wide cached Kernel for ``root``, or None on failure.

    Kernel construction touches the filesystem (state/, policies/). A failure
    is logged and returns None so callers can apply their degrade policy.
    """
    key = str(Path(root).resolve())
    with _KERNELS_LOCK:
        k = _KERNELS.get(key)
        if k is not None:
            return k
    try:
        from runtime.kernel import Kernel

        k = Kernel(Path(root))
    except Exception as exc:  # pragma: no cover - depends on env failure modes
        _logger.warning("enforcement kernel unavailable for %s: %s", key, exc, exc_info=True)
        return None
    with _KERNELS_LOCK:
        _KERNELS.setdefault(key, k)
        return _KERNELS[key]


def reset_shared_kernels() -> None:
    """Drop cached kernels (tests / env changes)."""
    with _KERNELS_LOCK:
        _KERNELS.clear()


def _prompt_text(args: dict[str, Any]) -> str:
    """Serialize tool arguments for the secret-leak guardrail."""
    try:
        return json.dumps(args, default=str, ensure_ascii=False)
    except (TypeError, ValueError):  # pragma: no cover - default=str catches most
        return str(args)


def _deny(
    kernel: Any, direction: str, server: str, tool: str,
    rule: str, reason: str, gate: str,
) -> dict[str, Any]:
    """Audit + build a denial decision dict."""
    try:
        kernel.audit.log(
            f"enforcement.{direction}.deny",
            {"server": server, "tool": tool, "rule": rule, "reason": reason, "gate": gate},
        )
    except Exception as exc:  # pragma: no cover - audit must never break the gate
        _logger.debug("enforcement audit log failed: %s", exc)
    return {
        "ok": False,
        "decision": Decision.DENY.value,
        "gate": gate,
        "rule": rule,
        "reason": reason,
        "error": f"{gate} denied {tool}: {reason}",
    }


def _is_approved(kernel: Any, server: str, tool: str, args: dict[str, Any]) -> bool:
    """Resolve a ``require_approval``/``ask`` verdict to a boolean."""
    if args.get("approved") is True or args.get("_approved") is True:
        return True
    action = {"type": "mcp", "server": server, "tool": tool, "args": args}
    try:
        if kernel.approval_cache.is_approved(action):
            return True
    except Exception as exc:  # pragma: no cover - cache failure -> deny (fail-closed)
        _logger.debug("approval cache check failed: %s", exc)
        return False
    return False


def approve_tool_call(kernel: Any, server: str, tool: str, args: dict[str, Any]) -> None:
    """Record approval for an MCP tool call in the session cache."""
    kernel.approval_cache.approve({"type": "mcp", "server": server, "tool": tool, "args": args})


def enforce_tool_call(
    kernel: Any,
    server: str,
    tool: str,
    args: dict[str, Any],
    *,
    agent_id: str = "",
    user_id: str = "",
    session_id: str = "",
) -> dict[str, Any] | None:
    """Run the outbound enforcement stack on a tool call.

    Returns ``None`` when the call may proceed, or a decision dict
    (``decision`` = deny / ask-with-requires_approval) when gated.
    """
    try:
        fw = kernel.mcp_firewall.check(tool, args)
    except Exception as exc:
        # Fail-closed: a broken firewall never silently allows.
        _logger.warning("mcp firewall evaluation failed (fail-closed): %s", exc)
        return _deny(kernel, "request", server, tool, "firewall_error", str(exc), "mcp_firewall")
    decision = fw.get("decision")
    if decision == Decision.DENY.value:
        return _deny(
            kernel, "request", server, tool,
            str(fw.get("rule", "unknown")), str(fw.get("reason", "")), "mcp_firewall",
        )
    if decision == Decision.ASK.value and not _is_approved(kernel, server, tool, args):
        try:
            kernel.audit.log(
                "enforcement.request.ask",
                {"server": server, "tool": tool, "rule": fw.get("rule"), "reason": fw.get("reason")},
            )
        except Exception as exc:  # pragma: no cover
            _logger.debug("enforcement audit log failed: %s", exc)
        return {
            "ok": False,
            "decision": Decision.ASK.value,
            "gate": "mcp_firewall",
            "rule": fw.get("rule"),
            "reason": fw.get("reason"),
            "requires_approval": True,
            "error": f"MCP tool '{tool}' requires approval (rule: {fw.get('rule')})",
        }
    ctx = GuardrailContext(
        prompt=_prompt_text(args),
        tool_name=tool,
        tool_payload=args,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )
    verdict, results = kernel.agent_gateway.check_request(ctx)
    if verdict is Verdict.BLOCK:
        blocking = next((r for r in results if r.verdict is Verdict.BLOCK), None)
        return _deny(
            kernel, "request", server, tool,
            blocking.guardrail_name if blocking else "agent_gateway",
            blocking.reason if blocking else "blocked",
            "agent_gateway",
        )
    return None


def enforce_tool_result(
    kernel: Any,
    server: str,
    tool: str,
    result_text: str,
    *,
    agent_id: str = "",
    user_id: str = "",
    session_id: str = "",
) -> tuple[bool, str]:
    """Run post-execution guardrails on a tool result.

    Returns ``(ok, text)``: ``ok=False`` blocks the result from reaching the
    caller; on REDACT the returned text has secrets stripped.
    """
    ctx = GuardrailContext(
        response=result_text,
        tool_name=tool,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
    )
    verdict, results = kernel.agent_gateway.check_response(ctx)
    if verdict is Verdict.BLOCK:
        blocking = next((r for r in results if r.verdict is Verdict.BLOCK), None)
        _deny(
            kernel, "response", server, tool,
            blocking.guardrail_name if blocking else "agent_gateway",
            blocking.reason if blocking else "blocked",
            "agent_gateway",
        )
        return False, blocking.reason if blocking else "blocked by agent_gateway"
    if verdict is Verdict.REDACT:
        redacted, _ = redact_secrets(result_text)
        try:
            kernel.audit.log(
                "enforcement.response.redact",
                {"server": server, "tool": tool, "verdicts": [r.to_dict() for r in results]},
            )
        except Exception as exc:  # pragma: no cover
            _logger.debug("enforcement audit log failed: %s", exc)
        return True, redacted
    return True, result_text


def enforce_tool_call_root(
    root: Path, server: str, tool: str, args: dict[str, Any], **ids: Any
) -> dict[str, Any] | None:
    """Root-based entry point for callers without a kernel reference."""
    kernel = shared_kernel(root)
    if kernel is None:
        if _strict():  # pragma: no cover - env-gated
            return {
                "ok": False,
                "decision": Decision.DENY.value,
                "gate": "enforcement",
                "error": "enforcement kernel unavailable (AIZEE_ENFORCE_STRICT=1)",
            }
        return None
    return enforce_tool_call(kernel, server, tool, args, **ids)


def enforce_tool_result_root(
    root: Path, server: str, tool: str, result_text: str, **ids: Any
) -> tuple[bool, str]:
    """Root-based result enforcement for callers without a kernel reference."""
    kernel = shared_kernel(root)
    if kernel is None:
        return not _strict(), result_text  # pragma: no cover - env-gated
    return enforce_tool_result(kernel, server, tool, result_text, **ids)


__all__ = [
    "approve_tool_call",
    "enforce_tool_call",
    "enforce_tool_call_root",
    "enforce_tool_result",
    "enforce_tool_result_root",
    "reset_shared_kernels",
    "shared_kernel",
]
