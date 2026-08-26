#!/usr/bin/env python3
"""Check a generated CycloneDX SBOM against an optional deny list.

Exit code 0 if no banned packages are present, 1 otherwise.

The deny list is a plain-text file (one package name per line, '#'
comments allowed). If the file is missing, the check passes by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_deny_list(path: Path) -> set[str]:
    """Read the deny list; return empty set when the file is absent."""
    if not path.exists():
        return set()
    banned: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        banned.add(line.lower())
    return banned


def _component_names(sbom: dict[str, object]) -> list[str]:
    components = sbom.get("components", [])
    if not isinstance(components, list):
        return []
    names: list[str] = []
    for component in components:
        if isinstance(component, dict):
            name = component.get("name")
            if isinstance(name, str):
                names.append(name.lower())
    return names


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check SBOM against a deny list.")
    parser.add_argument(
        "--sbom",
        type=Path,
        default=REPO_ROOT / "state" / "sbom.json",
        help="Path to the CycloneDX SBOM (default: state/sbom.json).",
    )
    parser.add_argument(
        "--deny-list",
        type=Path,
        default=REPO_ROOT / "state" / "deny_list.txt",
        help="Path to the deny list (default: state/deny_list.txt).",
    )
    args = parser.parse_args(argv)

    banned = _load_deny_list(args.deny_list)
    if not banned:
        print("No deny list configured — nothing to block.")
        return 0

    sbom_text = args.sbom.read_text(encoding="utf-8")
    sbom = json.loads(sbom_text)
    present = _component_names(sbom)

    violations = sorted({name for name in present if name in banned})
    if violations:
        print(f"Blocked packages found: {', '.join(violations)}")
        return 1

    print("No blocked packages found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
