#!/usr/bin/env python3
"""Evaluation harness for AI Global OS."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


class EvalHarness:
    """Run validation, lint, typecheck, tests and return score."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _run(self, name: str, cmd: list[str]) -> dict[str, Any]:
        p = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True)
        return {"returncode": p.returncode, "output": (p.stdout + "\n" + p.stderr)[-4000:]}

    def run(self) -> dict[str, Any]:
        results = {}
        results["ruff"] = self._run("ruff", ["python", "-m", "ruff", "check", "."])
        results["mypy"] = self._run("mypy", ["python", "-m", "mypy", "runtime", "memory", "aios_mcp", "cli.py", "config.py", "dashboard/server.py"])
        results["pytest"] = self._run("pytest", ["python", "-m", "pytest", "-q"])
        results["validate-globals"] = self._run("validate-globals", ["python", "scripts/validate-globals.py", "--fix"])

        all_pass = all(v["returncode"] == 0 for v in results.values())
        return {"results": results, "all_pass": all_pass}


if __name__ == "__main__":
    h = EvalHarness(config.discover_root())
    print(json.dumps(h.run(), indent=2))
