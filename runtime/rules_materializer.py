"""Rules materializer — emit aiZee rules to every AI coding tool's native format.

aiZee holds a single source of truth (``rules/``, ``global-roles.md``,
``global-workflow.md``, ``AGENTS.md``). This module materializes that source
into each tool's preferred file format so the same governance applies
regardless of which IDE/agent a developer uses:

- Claude Code      → ``CLAUDE.md`` + ``.claude/rules/*.md``
- Cursor           → ``.cursor/rules/*.mdc`` (with frontmatter)
- Cline            → ``.clinerules/*.md``
- Windsurf         → ``.windsurfrules``
- GitHub Copilot   → ``.github/copilot-instructions.md``
- Aider            → ``CONVENTIONS.md``
- Devin            → ``.devin/rules/*.md``

Scope precedence (highest → lowest): org → project → namespace → repo →
team → user. Higher scopes override lower ones; conflicts resolved by
last-writer-wins within the same scope.

Inspired by Elastra's centralized rules + materialization pattern.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from runtime.schemas import ValidationError

_logger = logging.getLogger(__name__)

# Safe glob pattern: word chars, hyphen, dot, star, slash, question mark,
# square brackets, curly braces. Rejects shell metacharacters and quotes.
_SAFE_GLOB = re.compile(r"^[\w\-\.\*/\?\[\]{}]+$")


class ToolTarget(str, Enum):
    """Supported AI coding tool targets for materialization."""

    CLAUDE = "claude"
    CURSOR = "cursor"
    CLINE = "cline"
    WINDSURF = "windsurf"
    COPILOT = "copilot"
    AIDER = "aider"
    DEVIN = "devin"


class ScopeLevel(str, Enum):
    """Rule scope precedence levels (highest → lowest)."""

    ORG = "org"
    PROJECT = "project"
    NAMESPACE = "namespace"
    REPO = "repo"
    TEAM = "team"
    USER = "user"

    @property
    def precedence(self) -> int:
        """Higher number = higher precedence (overrides lower)."""
        order = {
            ScopeLevel.USER: 1,
            ScopeLevel.TEAM: 2,
            ScopeLevel.REPO: 3,
            ScopeLevel.NAMESPACE: 4,
            ScopeLevel.PROJECT: 5,
            ScopeLevel.ORG: 6,
        }
        return order[self]


@dataclass(frozen=True)
class RuleEntry:
    """A single rule with scope metadata."""

    key: str
    content: str
    scope: ScopeLevel = ScopeLevel.REPO
    globs: list[str] | None = None
    always_apply: bool = False
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "key": self.key,
            "content": self.content,
            "scope": self.scope.value,
            "always_apply": self.always_apply,
            "description": self.description,
        }
        if self.globs:
            d["globs"] = list(self.globs)
        return d


@dataclass
class MaterializationResult:
    """Result of a materialization run."""

    target: ToolTarget
    files_written: list[Path] = field(default_factory=list)
    rules_emitted: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class RulesMaterializer:
    """Materialize aiZee rules into tool-specific files.

    Resolves rules by scope precedence, deduplicates by key, and emits
    each tool's native format. Idempotent: re-running overwrites stale files.
    """

    # Tool → (relative file path, format)
    _TARGET_FILES: ClassVar[dict[ToolTarget, str]] = {
        ToolTarget.CLAUDE: "CLAUDE.md",
        ToolTarget.CURSOR: ".cursor/rules/aizee.mdc",
        ToolTarget.CLINE: ".clinerules/aizee.md",
        ToolTarget.WINDSURF: ".windsurfrules",
        ToolTarget.COPILOT: ".github/copilot-instructions.md",
        ToolTarget.AIDER: "CONVENTIONS.md",
        ToolTarget.DEVIN: ".devin/rules/aizee.md",
    }

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._lock = threading.Lock()

    # -- Rule resolution --------------------------------------------------

    def resolve(
        self, rule_sets: dict[ScopeLevel, list[RuleEntry]]
    ) -> list[RuleEntry]:
        """Merge rule sets by scope precedence.

        Higher-scope rules override lower-scope rules with the same key.
        Returns a list ordered by key for deterministic output.
        """
        by_key: dict[str, RuleEntry] = {}
        # Process lowest → highest so higher overwrites lower.
        for level in sorted(ScopeLevel, key=lambda s: s.precedence):
            for entry in rule_sets.get(level, []):
                existing = by_key.get(entry.key)
                if existing is None or entry.scope.precedence >= existing.scope.precedence:
                    by_key[entry.key] = entry
        return sorted(by_key.values(), key=lambda r: r.key)

    # -- Per-tool emitters ------------------------------------------------

    def _emit_claude(self, rules: list[RuleEntry]) -> str:
        """Claude Code: single CLAUDE.md block."""
        lines = ["# aiZee Governance — Claude Code", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emit_cursor(self, rules: list[RuleEntry]) -> str:
        """Cursor: .mdc file with frontmatter."""
        front = "---\n"
        front += "description: aiZee governance rules\n"
        front += "globs:\n"
        globs = set()
        for r in rules:
            if r.globs:
                globs.update(r.globs)
        for g in sorted(globs):
            if not _SAFE_GLOB.match(g):
                continue  # skip unsafe globs
            front += f"  - \"{g}\"\n"
        if not globs:
            front += "  - \"**/*\"\n"
        front += "alwaysApply: true\n"
        front += "---\n\n"
        body = "# aiZee Governance — Cursor\n\n"
        for r in rules:
            body += f"## {r.key}\n\n{r.content.strip()}\n\n"
        return front + body

    def _emit_cline(self, rules: list[RuleEntry]) -> str:
        """Cline: plain markdown concatenated."""
        lines = ["# aiZee Governance — Cline", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emit_windsurf(self, rules: list[RuleEntry]) -> str:
        """Windsurf: single .windsurfrules file."""
        lines = ["# aiZee Governance — Windsurf", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emit_copilot(self, rules: list[RuleEntry]) -> str:
        """GitHub Copilot: copilot-instructions.md."""
        lines = ["# aiZee Governance — GitHub Copilot", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emit_aider(self, rules: list[RuleEntry]) -> str:
        """Aider: CONVENTIONS.md (read via --read)."""
        lines = ["# aiZee Governance — Aider Conventions", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emit_devin(self, rules: list[RuleEntry]) -> str:
        """Devin: .devin/rules/*.md."""
        lines = ["# aiZee Governance — Devin", ""]
        for r in rules:
            lines.append(f"## {r.key}")
            lines.append("")
            lines.append(r.content.strip())
            lines.append("")
        return "\n".join(lines) + "\n"

    def _emitter_for(self, target: ToolTarget) -> Any:
        return {
            ToolTarget.CLAUDE: self._emit_claude,
            ToolTarget.CURSOR: self._emit_cursor,
            ToolTarget.CLINE: self._emit_cline,
            ToolTarget.WINDSURF: self._emit_windsurf,
            ToolTarget.COPILOT: self._emit_copilot,
            ToolTarget.AIDER: self._emit_aider,
            ToolTarget.DEVIN: self._emit_devin,
        }[target]

    # -- Public API -------------------------------------------------------

    def materialize(
        self,
        rules: list[RuleEntry],
        targets: list[ToolTarget] | None = None,
    ) -> list[MaterializationResult]:
        """Materialize resolved rules into each target tool's file(s).

        Args:
            rules: Resolved rule list (use ``resolve()`` first).
            targets: Tools to emit. Defaults to all supported.

        Returns:
            One MaterializationResult per target.
        """
        if not rules:
            raise ValidationError("No rules to materialize")
        emit_targets = targets or list(ToolTarget)
        results: list[MaterializationResult] = []
        for target in emit_targets:
            results.append(self._emit_one(target, rules))
        return results

    def _emit_one(
        self, target: ToolTarget, rules: list[RuleEntry]
    ) -> MaterializationResult:
        result = MaterializationResult(target=target)
        with self._lock:
            rel = self._TARGET_FILES.get(target)
            if rel is None:
                result.errors.append(f"Unknown target: {target}")
                return result
            out_path = self.project_root / rel
            try:
                resolved = out_path.resolve()
                project_resolved = self.project_root.resolve()
                if not str(resolved).startswith(str(project_resolved)):
                    result.errors.append(f"Path traversal blocked: {rel}")
                    return result
            except OSError:
                pass
            try:
                emitter = self._emitter_for(target)
                content = emitter(rules)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(content, encoding="utf-8")
                result.files_written.append(out_path)
                result.rules_emitted = len(rules)
            except OSError as exc:
                result.errors.append(f"Write failed {out_path}: {exc}")
            except Exception as exc:
                _logger.debug("rules emit failed for %s: %s", target.value, exc, exc_info=True)
                result.errors.append(f"Emit failed {target.value}: {exc}")
            return result

    def materialize_all(
        self, rule_sets: dict[ScopeLevel, list[RuleEntry]]
    ) -> list[MaterializationResult]:
        """Resolve + materialize in one call."""
        resolved = self.resolve(rule_sets)
        if not resolved:
            raise ValidationError("No rules after resolution")
        return self.materialize(resolved)

    def detect_drift(
        self,
        rule_sets: dict[ScopeLevel, list[RuleEntry]],
        targets: list[ToolTarget] | None = None,
    ) -> dict[str, list[str]]:
        """Detect drift between source rules and emitted files.

        Returns a dict mapping target → list of rule keys missing from
        the emitted file. Empty lists mean no drift.
        """
        resolved = self.resolve(rule_sets)
        source_keys = {r.key for r in resolved}
        emit_targets = targets or list(ToolTarget)
        drift: dict[str, list[str]] = {}
        with self._lock:
            for target in emit_targets:
                rel = self._TARGET_FILES.get(target)
                if rel is None:
                    continue
                path = self.project_root / rel
                if not path.exists():
                    drift[target.value] = sorted(source_keys)
                    continue
                text = path.read_text(encoding="utf-8")
                missing = [k for k in sorted(source_keys) if k not in text]
                drift[target.value] = missing
        return drift


__all__ = [
    "MaterializationResult",
    "RuleEntry",
    "RulesMaterializer",
    "ScopeLevel",
    "ToolTarget",
]
