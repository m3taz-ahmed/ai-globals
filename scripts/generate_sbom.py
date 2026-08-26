#!/usr/bin/env python3
"""Generate a CycloneDX SBOM for aiZee (OWASP LLM03 supply-chain coverage).

Stdlib + importlib.metadata only — no external dependencies.

Covers:
  * First-party packages (python folders in the repo root).
  * Third-party distributions discoverable via importlib.metadata.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from importlib import metadata as importlib_metadata
except ImportError:  # pragma: no cover - Python <3.8 fallback
    import importlib_metadata  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parent.parent

CYCLONEDX_SPEC_VERSION = "1.5"

FIRST_PARTY_DIRS = ("runtime", "aizee_mcp", "memory", "eval", "scripts", "dashboard")


def _project_version() -> str:
    """Infer the project version from pyproject.toml or config.VERSION."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"\n]+)"', text, re.MULTILINE)
        if match:
            return match.group(1)
    config_py = REPO_ROOT / "config.py"
    if config_py.exists():
        text = config_py.read_text(encoding="utf-8")
        match = re.search(r'VERSION\s*[:=]\s*"([^"\n]+)"', text, re.MULTILINE)
        if match:
            return match.group(1)
    return "0.0.0"


def _is_python_package(directory: Path) -> bool:
    return (directory / "__init__.py").exists()


def _first_party_components(version: str) -> list[dict[str, object]]:
    """Build CycloneDX components for first-party python packages."""
    components: list[dict[str, object]] = []
    for name in FIRST_PARTY_DIRS:
        directory = REPO_ROOT / name
        if not directory.is_dir():
            continue
        is_package = _is_python_package(directory)
        # scripts/ has no __init__.py but is still a first-party source set.
        if not is_package and name != "scripts":
            continue
        components.append(
            {
                "type": "library",
                "name": f"aizee/{name}",
                "version": version,
                "group": "aizee",
                "description": f"aiZee first-party package: {name}",
                "scope": "required",
                "purl": f"pkg:python/aizee.{name}@{version}",
            }
        )
    return components


def _third_party_components() -> list[dict[str, object]]:
    """Build CycloneDX components for installed third-party distributions."""
    components: list[dict[str, object]] = []
    seen: set[str] = set()
    for dist in importlib_metadata.distributions():
        meta = dist.metadata
        try:
            name = meta["Name"]
        except KeyError:
            name = dist.name
        if not name:
            continue
        key = f"{name}@{dist.version}"
        if key in seen:
            continue
        seen.add(key)
        component: dict[str, object] = {
            "type": "library",
            "name": name,
            "version": dist.version,
            "scope": "required",
            "purl": f"pkg:pypi/{name}@{dist.version}",
        }
        try:
            license_value = meta["License"]
        except KeyError:
            license_value = None
        if license_value:
            component["licenses"] = [{"license": {"name": license_value}}]
        components.append(component)
    components.sort(key=lambda c: str(c["name"]).lower())
    return components


def build_sbom() -> dict[str, object]:
    """Assemble the full CycloneDX document."""
    version = _project_version()
    components = _first_party_components(version) + _third_party_components()
    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "version": 1,
        "serialNumber": "urn:uuid:00000000-0000-0000-0000-000000000000",
        "metadata": {
            "component": {
                "type": "application",
                "name": "aizee",
                "version": version,
            }
        },
        "components": components,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a CycloneDX SBOM for aiZee.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "state" / "sbom.json",
        help="Output path for the SBOM JSON (default: state/sbom.json).",
    )
    args = parser.parse_args(argv)

    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sbom = build_sbom()
    output_path.write_text(json.dumps(sbom, indent=2, ensure_ascii=True), encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
