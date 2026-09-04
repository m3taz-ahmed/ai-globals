#!/usr/bin/env python3
"""Workflow, rules, and MCP plan tools."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from aizee_mcp._compat import FastMCP
from aizee_mcp.agent import McpAgent
from runtime.mcp_orchestrator import McpOrchestrator, Plan, Step
from runtime.rule_compiler import compile_rules
from runtime.rule_frontmatter import matches_context, parse_frontmatter

from .common import (
    _MAX_RESULTS,
    is_safe_name,
    kernel,
    memory,
    resolve_path,
    root,
    truncate,
    validate_query,
)

logger = logging.getLogger(__name__)


def register_workflow_tools(mcp: FastMCP) -> None:
    """Register workflow, rules, and MCP plan tools."""

    @mcp.tool()
    def query_rules(query: str, context: dict[str, Any] | None = None) -> str:
        """Query aiZee rules by keyword, returning only active rules for the context."""
        err = validate_query(query)
        if err:
            return err
        if context is not None and not isinstance(context, dict):
            return json.dumps({"ok": False, "error": "Invalid context"})
        active_context = context or {}
        r = root()

        fts_results: list[dict[str, Any]] = []
        try:
            store = memory()
            for mem in store.search(query, kind="semantic", limit=_MAX_RESULTS):
                if "rules" not in mem.source.replace("\\", "/"):
                    continue
                fts_results.append(
                    {"file": mem.source, "match": query, "content": truncate(mem.content, 200), "score": "fts"}
                )
        except Exception:
            logger.debug("FTS search failed in workflow query", exc_info=True)
            fts_results = []

        results: list[dict[str, Any]] = fts_results
        seen_files = {item["file"] for item in results}
        # Capped scan: one unreadable/oversize file must not crash the tool
        # or stall the server on huge rules dirs.
        scanned = 0
        for p in sorted(r.glob("rules/*.md")):
            if scanned >= 200:
                break
            scanned += 1
            try:
                if p.stat().st_size > 200_000:
                    continue
                rel = str(p.relative_to(r))
            except (OSError, ValueError):
                continue
            if rel in seen_files:
                continue
            try:
                content = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            frontmatter, body = parse_frontmatter(content)
            if not matches_context(frontmatter, active_context):
                continue
            if query.lower() in body.lower():
                results.append({"file": rel, "match": query})
        return json.dumps(results, indent=2)

    @mcp.tool()
    def run_workflow(id: str, context: dict[str, Any] | None = None) -> str:
        """Run a workflow by ID with optional context."""
        if not is_safe_name(id):
            return json.dumps({"ok": False, "error": f"Invalid workflow ID: {id!r}"})
        clean = dict(context or {})
        # Persona keys are server-routed, never caller-supplied: strip them
        # so MCP callers cannot spoof persona/skill/lords via context.
        for spoofable in ("persona", "personas", "skill", "skills", "lords"):
            clean.pop(spoofable, None)
        result = kernel().run_workflow(id, clean)
        return json.dumps(result, indent=2, default=str)

    @mcp.tool()
    def list_rules() -> str:
        """List available rule files."""
        r = root()
        results = [{"id": p.stem, "file": str(p.relative_to(r))} for p in sorted(r.glob("rules/*.md"))]
        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_rule(id: str) -> str:
        """Get a rule file by its stem (id)."""
        if not is_safe_name(id):
            return json.dumps({"ok": False, "error": "Invalid rule id"})
        r = root()
        path = resolve_path(r, Path("rules") / f"{id}.md")
        if path is None:
            return json.dumps({"ok": False, "error": "Invalid path"})
        if not path.exists():
            return json.dumps({"exists": False, "path": str(path.relative_to(r))})
        return json.dumps({"exists": True, "path": str(path.relative_to(r)), "content": path.read_text(encoding="utf-8")})

    @mcp.tool()
    def list_workflows() -> str:
        """List available workflow files."""
        r = root()
        results = [{"id": p.stem, "file": str(p.relative_to(r))} for p in sorted(r.glob("workflows/*.md"))]
        return json.dumps(results, indent=2)

    @mcp.tool()
    def get_workflow(id: str) -> str:
        """Get a workflow file by its stem (id)."""
        if not is_safe_name(id):
            return json.dumps({"ok": False, "error": "Invalid workflow id"})
        r = root()
        path = resolve_path(r, Path("workflows") / f"{id}.md")
        if path is None:
            return json.dumps({"ok": False, "error": "Invalid path"})
        if not path.exists():
            return json.dumps({"exists": False, "path": str(path.relative_to(r))})
        return json.dumps({"exists": True, "path": str(path.relative_to(r)), "content": path.read_text(encoding="utf-8")})

    @mcp.resource("rules://{id}")
    def get_rule_resource(id: str) -> str:
        if not is_safe_name(id):
            return ""
        r = root()
        path = resolve_path(r, Path("rules") / f"{id}.md")
        if path is None or not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    @mcp.resource("workflows://{id}")
    def get_workflow_resource(id: str) -> str:
        if not is_safe_name(id):
            return ""
        r = root()
        path = resolve_path(r, Path("workflows") / f"{id}.md")
        if path is None or not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    @mcp.tool()
    def compile_rule_files(globs: list[str] | None = None) -> str:
        """Compile rule/skill/workflow markdown files into Rule IR."""
        if globs is not None:
            if not isinstance(globs, list) or len(globs) > 50:
                return json.dumps({"ok": False, "error": "globs must be a list of at most 50 patterns"})
            for g in globs:
                if not isinstance(g, str) or not g or len(g) > 256 or ".." in g or g.startswith(("/", "\\")):
                    return json.dumps({"ok": False, "error": f"Invalid glob pattern: {g!r}"})
        try:
            rules = compile_rules(root(), globs=globs)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Rule compilation failed: {exc!s}"})
        return json.dumps(
            [{"file": r.file, "obj": r.obj, "rules_count": len(r.rules)} for r in rules],
            indent=2,
            default=str,
        )

    @mcp.tool()
    def run_mcp_plan(steps: list[dict[str, Any]]) -> str:
        """Execute a multi-step plan across MCP tools."""
        if not isinstance(steps, list) or not steps:
            return json.dumps({"ok": False, "error": "steps must be a non-empty list"})
        if len(steps) > 50:
            return json.dumps({"ok": False, "error": "steps must contain at most 50 entries"})
        try:
            plan = Plan(
                id="mcp-plan",
                steps=[Step(**s) for s in steps if isinstance(s, dict)],
            )
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Invalid plan: {exc!s}"})
        if not plan.steps:
            return json.dumps({"ok": False, "error": "steps must be a non-empty list of objects"})
        agent = McpAgent("mcp-server")
        orchestrator = McpOrchestrator(agent)

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None:
            return json.dumps({"ok": False, "error": "run_mcp_plan cannot nest inside a running event loop"})
        result = asyncio.run(orchestrator.execute_async(plan))
        return json.dumps(
            {step: {"status": r.status.value, "output": r.output, "error": r.error} for step, r in result.items()},
            indent=2,
            default=str,
        )
