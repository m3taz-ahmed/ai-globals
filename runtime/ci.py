"""CI pipeline runner for AI Global OS quality gates."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError as exc:
        return 1, f"Command not found: {exc}"


class CIPipeline:
    """Runs the standard AI Global OS quality gates."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.results: list[dict[str, object]] = []

    def run(self, skip_pytest: bool = False) -> int:
        self.results = []
        all_ok = True

        checks: list[tuple[str, list[str]]] = [
            ("ruff", [sys.executable, "-m", "ruff", "check", "."]),
            ("mypy", [sys.executable, "-m", "mypy", "runtime", "memory", "aios_mcp", "cli.py", "config.py", "dashboard/server.py"]),
        ]
        if not skip_pytest:
            checks.append(("pytest", [sys.executable, "-m", "pytest", "-q"]))
        checks.append(("eval/harness", [sys.executable, "eval/harness.py"]))

        for name, cmd in checks:
            code, output = run_command(cmd, self.root)
            ok = code == 0
            self.results.append({"name": name, "ok": ok, "output": output})
            if not ok:
                all_ok = False

        return 0 if all_ok else 1

    def report(self) -> dict[str, object]:
        return {
            "ok": all(r["ok"] for r in self.results),
            "results": self.results,
        }
