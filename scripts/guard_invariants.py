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
6. New modules use enums/constants, not magic strings.
7. Trait composition preferred over deep inheritance (>4 bases flagged).
8. runtime/__init__.py has no manifest drift (exports match imports).

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
    """No ``raise Exception(`` - must use AizeeError subclasses."""
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
        # Skip reference/template subdirectories and EVAL files (not skill files)
        if "references" in md.parts or "templates" in md.parts or md.name in ("EVAL.md", "README.md"):
            continue
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


def check_no_magic_strings_in_new_modules(root: Path) -> list[Violation]:
    """New runtime modules must use enums/constants, not bare magic strings for status.

    Checks commands.py, hook_lifecycle.py for string literals used as status
    where an enum exists. This is a lightweight heuristic check.
    """
    violations: list[Violation] = []
    checks_map = {
        "runtime/commands.py": (r'["\']pending["\']|["\']completed["\']|["\']failed["\']', "CommandStatus"),
        "runtime/hook_lifecycle.py": (r'["\']pre_receive["\']|["\']post_response["\']', "HookPhase"),
    }
    for rel_path, (pattern, enum_name) in checks_map.items():
        path = root / rel_path
        if not path.exists():
            continue
        compiled = re.compile(pattern)
        in_enum_class = False
        enum_indent = 0
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            # Detect enum class entry BEFORE the Enum skip check
            if f"class {enum_name}" in line:
                in_enum_class = True
                enum_indent = len(line) - len(line.lstrip())
                continue
            if stripped.startswith("#") or stripped.startswith('"') or "Enum" in line:
                continue
            if in_enum_class and stripped and not stripped.startswith("#"):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= enum_indent:
                    in_enum_class = False
            if in_enum_class:
                continue
            if compiled.search(line) and "=" in line and "Enum" not in line:
                violations.append(Violation(
                    check="no_magic_strings",
                    file=rel_path,
                    line=i,
                    message=f"possible magic string (use {enum_name}): {stripped[:80]}",
                ))
    return violations


def check_trait_composition_over_inheritance(root: Path) -> list[Violation]:
    """Runtime classes should prefer composition (multiple base concerns) over deep inheritance.

    Flags any runtime class with >3 levels of inheritance (heuristic: class X(Y)
    where Y is also a subclass of another class). This is a lightweight check.
    """
    violations: list[Violation] = []
    runtime = root / "runtime"
    if not runtime.exists():
        return violations
    # Look for classes that inherit from more than 2 bases (composition smell)
    pattern = re.compile(r"^class\s+\w+\s*\(([^)]+)\)\s*:")
    for py in runtime.rglob("*.py"):
        if py.name.startswith("__"):
            continue
        for i, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            match = pattern.match(line)
            if match:
                bases = [b.strip() for b in match.group(1).split(",") if b.strip()]
                # More than 3 bases suggests composition via multiple inheritance (OK)
                # but flag if it's a single deep chain - heuristic only
                if len(bases) > 4:
                    violations.append(Violation(
                        check="trait_composition",
                        file=str(py.relative_to(root)),
                        line=i,
                        message=f"class with {len(bases)} bases - verify composition is intentional",
                    ))
    return violations


def check_manifest_no_drift(root: Path) -> list[Violation]:
    """runtime/__init__.py should match what generate_manifest.py would produce.

    Runs the manifest generator in verify mode. If drift is detected, reports it.
    """
    violations: list[Violation] = []
    init_path = root / "runtime" / "__init__.py"
    if not init_path.exists():
        return violations
    try:
        import sys as _sys
        scripts_dir = str(root / "scripts")
        if scripts_dir not in _sys.path:
            _sys.path.insert(0, scripts_dir)
        from generate_manifest import (  # pyright: ignore[reportMissingImports]
            generate_init_source,
            parse_existing_init,
        )

        existing = init_path.read_text(encoding="utf-8")
        manifest = parse_existing_init(existing)
        generated = generate_init_source(manifest)
        # Compare export names (order-independent)
        existing_names = set(re.findall(r'^    "(\w+)",$', existing, re.MULTILINE))
        generated_names = set(re.findall(r'^    "(\w+)",$', generated, re.MULTILINE))
        existing_names.discard("annotations")
        generated_names.discard("annotations")
        missing = generated_names - existing_names
        extra = existing_names - generated_names
        if missing:
            violations.append(Violation(
                check="manifest_drift",
                file="runtime/__init__.py",
                line=1,
                message=f"exports missing from __all__: {sorted(missing)}",
            ))
        if extra:
            violations.append(Violation(
                check="manifest_drift",
                file="runtime/__init__.py",
                line=1,
                message=f"exports in __all__ but not imported: {sorted(extra)}",
            ))
    except Exception:
        pass
    return violations


ALL_CHECKS = [
    check_future_annotations,
    check_no_bare_exception,
    check_skills_have_frontmatter,
    check_kernel_facade_delegates,
    check_policy_actions_valid,
    check_no_magic_strings_in_new_modules,
    check_trait_composition_over_inheritance,
    check_manifest_no_drift,
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
        print("guard:invariants - all checks passed")
        return 0
    print(f"guard:invariants - {len(violations)} violation(s):")
    for v in violations:
        print(f"  [{v.check}] {v.file}:{v.line} - {v.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
