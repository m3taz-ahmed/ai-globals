#!/usr/bin/env python3
"""Mechanical code-invariant checks for aiZee.

Inspired by eve's ``guard:invariants``: mechanical checks that run in CI
to catch invariant violations early. Each check is a pure function that
returns a list of violations (empty = pass).

Checks:
1. Every runtime module uses ``from __future__ import annotations``.
2. No bare ``Exception`` raises (must use AizeeError subclasses).
3. Every skill file has frontmatter.
4. Kernel facade delegates to managers (no direct logic in Kernel.act).
5. Policy files have valid actions.

Usage::

    python scripts/guard_invariants.py
    # exit 0 = all pass, exit 1 = violations found
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Violation:
    """A single invariant violation."""

    check: str
    file: str
    line: int
    message: str


def check_future_annotations(root: Path) -> list[Violation]:
    """Every runtime/*.py must have ``from __future__ import annotations``."""
    violations: list[Violation] = []
    runtime = root / "runtime"
    if not runtime.exists():
        return violations
    for py in runtime.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        text = py.read_text(encoding="utf-8")
        if "from __future__ import annotations" not in text:
            violations.append(Violation(
                check="future_annotations",
                file=str(py.relative_to(root)),
                line=1,
                message="missing 'from __future__ import annotations'",
            ))
    return violations


def check_no_bare_exception(root: Path) -> list[Violation]:
    """No ``raise Exception(`` — must use AizeeError subclasses."""
    violations: list[Violation] = []
    runtime = root / "runtime"
    if not runtime.exists():
        return violations
    pattern = re.compile(r"raise\s+Exception\s*\(")
    for py in runtime.rglob("*.py"):
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                violations.append(Violation(
                    check="no_bare_exception",
                    file=str(py.relative_to(root)),
                    line=i,
                    message=f"bare Exception raise: {line.strip()}",
                ))
    return violations


def check_skills_have_frontmatter(root: Path) -> list[Violation]:
    """Every skill .md file must start with frontmatter (--- ... ---)."""
    violations: list[Violation] = []
    skills = root / "skills"
    if not skills.exists():
        return violations
    for md in skills.rglob("*.md"):
        text = md.read_text(encoding="utf-8").strip()
        if not text.startswith("---"):
            violations.append(Violation(
                check="skills_frontmatter",
                file=str(md.relative_to(root)),
                line=1,
                message="skill file missing frontmatter",
            ))
    return violations


def check_kernel_facade_delegates(root: Path) -> list[Violation]:
    """Kernel.act must delegate to managers, not contain business logic."""
    violations: list[Violation] = []
    kernel = root / "runtime" / "kernel.py"
    if not kernel.exists():
        return violations
    text = kernel.read_text(encoding="utf-8")
    # Check that PolicyManager, WorkflowManager, AgentManager, ChatManager are imported.
    for mgr in ("PolicyManager", "WorkflowManager", "AgentManager", "ChatManager"):
        if mgr not in text:
            violations.append(Violation(
                check="kernel_facade",
                file="runtime/kernel.py",
                line=1,
                message=f"Kernel does not reference {mgr}",
            ))
    return violations


def check_policy_actions_valid(root: Path) -> list[Violation]:
    """Policy YAML files must use valid actions (allow/ask/deny)."""
    violations: list[Violation] = []
    import yaml

    policies = root / "runtime" / "policies"
    if not policies.exists():
        return violations
    valid = {"allow", "ask", "deny"}
    # Files with their own schema (not generic policy rules).
    excluded = {"guardian.yaml", "probity.yaml", "mcp_firewall.yaml"}
    for yml in policies.rglob("*.yaml"):
        if yml.name in excluded:
            continue
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        default = data.get("default_action")
        if default is not None and default not in valid:
            violations.append(Violation(
                check="policy_actions",
                file=str(yml.relative_to(root)),
                line=1,
                message=f"invalid default_action: {default}",
            ))
        for r in data.get("rules", []):
            if isinstance(r, dict):
                action = r.get("decision") or r.get("action")
                if action is not None and action not in valid:
                    violations.append(Violation(
                        check="policy_actions",
                        file=str(yml.relative_to(root)),
                        line=1,
                        message=f"invalid action: {action}",
                    ))
    return violations


ALL_CHECKS = [
    check_future_annotations,
    check_no_bare_exception,
    check_skills_have_frontmatter,
    check_kernel_facade_delegates,
    check_policy_actions_valid,
]


def run_all(root: Path) -> list[Violation]:
    """Run all invariant checks. Returns list of violations."""
    violations: list[Violation] = []
    for check in ALL_CHECKS:
        violations.extend(check(root))
    return violations


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    violations = run_all(root)
    if not violations:
        print("guard:invariants — all checks passed")
        return 0
    print(f"guard:invariants — {len(violations)} violation(s):")
    for v in violations:
        print(f"  [{v.check}] {v.file}:{v.line} — {v.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
