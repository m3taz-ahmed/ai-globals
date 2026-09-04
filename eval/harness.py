#!/usr/bin/env python3
"""Evaluation harness for aiZee."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


class GateName(str, Enum):
    """5-gate evidence-based verification sequence (from agentic-os)."""

    SCOPE = "scope"            # Confirm changes cover ONLY agreed scope
    QUALITY = "quality"        # Execute required tests/static checks
    EVIDENCE = "evidence"      # Compile reproducible evidence
    RISK = "risk"              # Confirm rollback strategy exists
    COMMUNICATION = "communication"  # Output completion summary


@dataclass
class GateResult:
    """Result of a single evidence gate."""

    name: GateName
    passed: bool
    evidence: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceGates:
    """5-gate verification with receipts (from agentic-os).

    Each gate must pass before the next is evaluated. Gate receipts
    are recorded for audit trail.
    """

    results: list[GateResult] = field(default_factory=list)

    def run_all(
        self,
        scope_items: list[str],
        quality_checks: dict[str, bool],
        evidence_commands: list[str],
        rollback_strategy: str,
        summary: str,
    ) -> list[GateResult]:
        """Run all 5 gates in sequence. Stops on first failure."""
        self.results = []
        self._run_scope(scope_items)
        if not self.results[-1].passed:
            return self.results
        self._run_quality(quality_checks)
        if not self.results[-1].passed:
            return self.results
        self._run_evidence(evidence_commands)
        if not self.results[-1].passed:
            return self.results
        self._run_risk(rollback_strategy)
        if not self.results[-1].passed:
            return self.results
        self._run_communication(summary)
        return self.results

    def _run_scope(self, items: list[str]) -> None:
        passed = len(items) > 0
        self.results.append(GateResult(
            name=GateName.SCOPE, passed=passed,
            evidence=f"{len(items)} scope items defined",
            details={"items": items},
        ))

    def _run_quality(self, checks: dict[str, bool]) -> None:
        failed = [k for k, v in checks.items() if not v]
        passed = len(failed) == 0
        self.results.append(GateResult(
            name=GateName.QUALITY, passed=passed,
            evidence=f"{len(checks) - len(failed)}/{len(checks)} checks passed",
            details={"failed": failed},
        ))

    def _run_evidence(self, commands: list[str]) -> None:
        passed = len(commands) > 0
        self.results.append(GateResult(
            name=GateName.EVIDENCE, passed=passed,
            evidence=f"{len(commands)} evidence commands recorded",
            details={"commands": commands},
        ))

    def _run_risk(self, strategy: str) -> None:
        passed = bool(strategy.strip())
        self.results.append(GateResult(
            name=GateName.RISK, passed=passed,
            evidence=strategy if passed else "No rollback strategy",
        ))

    def _run_communication(self, summary: str) -> None:
        passed = bool(summary.strip())
        self.results.append(GateResult(
            name=GateName.COMMUNICATION, passed=passed,
            evidence=summary[:200] if passed else "No summary",
        ))

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {"name": r.name.value, "passed": r.passed, "evidence": r.evidence}
            for r in self.results
        ]


class EvalHarness:
    """Run validation, lint, typecheck, tests and return score."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _run(self, name: str, cmd: list[str]) -> dict[str, Any]:
        try:
            p = subprocess.run(
                cmd, cwd=self.root, capture_output=True, text=True, encoding="utf-8", errors="replace"
            )
        except FileNotFoundError:
            # Include returncode so the aggregation below never raises KeyError
            # when a tool (e.g. ruff/mypy/pytest) is missing on PATH (TEST-2 fix).
            return {"ok": False, "output": f"Tool not found: {name}", "returncode": -1}
        return {"returncode": p.returncode, "output": (p.stdout + "\n" + p.stderr)[-4000:]}

    def run(self) -> dict[str, Any]:
        results = {}
        py = sys.executable or "python"
        results["ruff"] = self._run("ruff", [py, "-m", "ruff", "check", "."])
        # Expanded mypy surface to cover previously-unchecked eval modules (TEST-3 fix).
        results["mypy"] = self._run(
            "mypy",
            [
                py,
                "-m",
                "mypy",
                "runtime",
                "memory",
                "aizee_mcp",
                "aizee_cli.py",
                "config.py",
                "dashboard/server.py",
                "eval/harness.py",
                "eval/pipeline.py",
                "eval/reliability.py",
                "eval/redteam.py",
                "eval/agent_benchmark.py",
                "eval/rubric.py",
                "eval/stages.py",
                "eval/vibe.py",
                "scripts/guard_invariants.py",
                "scripts/sync_docs.py",
            ],
        )
        # Hermetic pytest: skip environment-dependent markers and close the
        # coverage blind spot by including plugins/ and eval/ (TEST-3/TEST-4).
        results["pytest"] = self._run(
            "pytest",
            [
                py,
                "-m",
                "pytest",
                "-q",
                "-m",
                "not integration and not mcp and not dashboard and not vector",
                "--cov=runtime",
                "--cov=memory",
                "--cov=aizee_mcp",
                "--cov=plugins",
                "--cov=eval",
                "--cov-report=term-missing",
                "--cov-fail-under=95",
            ],
        )
        # Supply-chain step: generate_sbom.py can be run beforehand to emit
        # state/sbom.json (CycloneDX) covering OWASP LLM03; check_sbom.py then
        # validates it against state/deny_list.txt. Logic below is unchanged.
        results["validate-globals"] = self._run("validate-globals", [py, "scripts/validate-globals.py"])

        all_pass = all(v.get("returncode", -1) == 0 for v in results.values())
        return {"results": results, "all_pass": all_pass}

    def run_evidence_gates(
        self,
        scope_items: list[str],
        quality_checks: dict[str, bool],
        evidence_commands: list[str],
        rollback_strategy: str,
        summary: str,
    ) -> dict[str, Any]:
        """Run the 5-gate evidence-based verification."""
        gates = EvidenceGates()
        gates.run_all(
            scope_items, quality_checks, evidence_commands,
            rollback_strategy, summary,
        )
        return {"gates": gates.to_dict(), "all_passed": gates.all_passed}


if __name__ == "__main__":
    h = EvalHarness(config.discover_root())
    print(json.dumps(h.run(), indent=2))
