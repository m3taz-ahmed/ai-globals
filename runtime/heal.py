#!/usr/bin/env python3
"""Self-healing orchestrator: safe auto-fixes with dry-run default.

``aizee heal`` diagnoses the same surface as ``aizee doctor`` but splits
findings into auto-fixable repairs and manual-only items. Applying a fix
requires the explicit ``--apply`` flag; in a TTY the operator is prompted
per-fix unless ``--yes`` is passed. Every applied fix is appended to
``state/heal.log`` (JSONL) so repairs are auditable.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class HealStatus(str, Enum):
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"
    MANUAL = "manual"


class Severity(str, Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True)
class HealFinding:
    id: str
    title: str
    severity: Severity
    description: str
    auto_fixable: bool
    fix_hint: str = ""


@dataclass
class HealResult:
    finding: HealFinding
    status: HealStatus
    detail: str = ""


Fixer = Callable[[Path, Path], str]


def _fix_state_dir(os_root: Path, project_root: Path) -> str:
    (project_root / "state").mkdir(parents=True, exist_ok=True)
    return f"created {project_root / 'state'}"


def _fix_brain_dir(os_root: Path, project_root: Path) -> str:
    (project_root / "brain").mkdir(parents=True, exist_ok=True)
    return f"created {project_root / 'brain'}"


def _fix_version_file(os_root: Path, project_root: Path) -> str:
    import config

    target = os_root / ".aizee-version"
    target.write_text(config.VERSION + "\n", encoding="utf-8")
    return f"wrote {target} (version {config.VERSION})"


def _fix_env_encoding(os_root: Path, project_root: Path) -> str:
    env_path = os_root / ".env"
    raw = env_path.read_bytes()
    backup = env_path.with_name(env_path.name + ".bak")
    shutil.copy2(env_path, backup)
    text = raw.decode("utf-8", errors="replace")
    env_path.write_text(text, encoding="utf-8")
    return f"re-encoded {env_path.name} as UTF-8 (backup: {backup.name})"


def _fix_memory_schema(os_root: Path, project_root: Path) -> str:
    from memory.store import MemoryStore

    MemoryStore(project_root, enable_vector=False)
    return "applied additive memory schema migration (pinned/deleted_at)"


def _fix_global_mcp_config(os_root: Path, project_root: Path) -> str:
    script = os_root / "scripts" / "mcp_global_sync.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(os_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"mcp_global_sync failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return "global MCP config synced"


_FIXERS: dict[str, Fixer] = {
    "missing-state-dir": _fix_state_dir,
    "missing-brain-dir": _fix_brain_dir,
    "missing-version-file": _fix_version_file,
    "env-encoding": _fix_env_encoding,
    "memory-schema-drift": _fix_memory_schema,
    "global-mcp-config": _fix_global_mcp_config,
}


def _env_is_broken_utf8(os_root: Path) -> bool:
    env_path = os_root / ".env"
    if not env_path.exists():
        return False
    try:
        env_path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _global_mcp_config_missing() -> bool:
    import os

    if os.name == "nt":
        g_dir = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "devin"
    else:  # pragma: no cover - POSIX-only branch, CI runs Windows
        g_dir = Path.home() / ".config" / "devin"
    g_cfg = g_dir / "mcp_config.json"
    if not g_cfg.exists():
        return True
    try:
        return not json.loads(g_cfg.read_text(encoding="utf-8")).get("mcpServers")
    except (OSError, json.JSONDecodeError):
        return True


class Healer:
    """Diagnose + repair the aiZee installation. Dry-run by default."""

    def __init__(self, os_root: Path, project_root: Path) -> None:
        self.os_root = os_root
        self.project_root = project_root

    def scan(self) -> list[HealFinding]:
        findings: list[HealFinding] = []

        state_dir = self.project_root / "state"
        findings.append(
            HealFinding(
                "missing-state-dir",
                "state directory",
                Severity.ERROR if not state_dir.exists() else Severity.INFO,
                "Project state directory absent — audit/budget/daemon state cannot persist.",
                auto_fixable=True,
                fix_hint="mkdir state/",
            )
            if not state_dir.exists()
            else HealFinding("missing-state-dir", "state directory", Severity.INFO, "Present.", True)
        )

        brain_dir = self.project_root / "brain"
        if not brain_dir.exists():
            findings.append(
                HealFinding(
                    "missing-brain-dir",
                    "brain directory",
                    Severity.ERROR,
                    "Memory DB directory absent — MemoryStore cannot initialise.",
                    True,
                    "mkdir brain/",
                )
            )

        if not (self.os_root / ".aizee-version").exists():
            findings.append(
                HealFinding(
                    "missing-version-file",
                    ".aizee-version marker",
                    Severity.WARN,
                    "Installed-version marker missing — doctor reports 'installed version' as failed.",
                    True,
                    "write current version",
                )
            )

        if _env_is_broken_utf8(self.os_root):
            findings.append(
                HealFinding(
                    "env-encoding",
                    ".env encoding",
                    Severity.ERROR,
                    ".env is not valid UTF-8 — crashes dotenv/pydantic-settings and MCP secret loading.",
                    True,
                    "backup + re-encode UTF-8",
                )
            )

        db_path = self.project_root / "brain" / "memory.db"
        if db_path.exists():
            try:
                from memory.schema_contract import verify_schema_integrity

                ok, drift = verify_schema_integrity(db_path)
            except Exception as exc:
                ok, drift = False, f"verify error: {exc}"
            if not ok:
                findings.append(
                    HealFinding(
                        "memory-schema-drift",
                        "memory schema drift",
                        Severity.ERROR,
                        f"memory.db schema drift: {drift}",
                        True,
                        "additive column migration via MemoryStore",
                    )
                )

        if _global_mcp_config_missing():
            findings.append(
                HealFinding(
                    "global-mcp-config",
                    "global MCP config",
                    Severity.WARN,
                    "Global mcp_config.json missing/empty — external MCP servers unreachable in other workspaces.",
                    True,
                    "run scripts/mcp_global_sync.py",
                )
            )

        findings.extend(self._manual_checks())
        return findings

    def _manual_checks(self) -> list[HealFinding]:
        out: list[HealFinding] = []
        for pkg in ("yaml", "mcp", "pydantic", "rich", "cryptography"):
            try:
                __import__(pkg)
            except ImportError:
                out.append(
                    HealFinding(
                        f"pip-{pkg}",
                        f"missing dependency: {pkg}",
                        Severity.ERROR,
                        f"Required package '{pkg}' is not importable.",
                        False,
                        f"pip install {pkg}",
                    )
                )
        if not (self.os_root / "runtime" / "policies" / "default.yaml").exists():
            out.append(
                HealFinding(
                    "missing-default-policy",
                    "default policy file",
                    Severity.ERROR,
                    "runtime/policies/default.yaml missing — policy engine cannot evaluate.",
                    False,
                    "restore from repo",
                )
            )
        return out

    def apply(
        self,
        findings: list[HealFinding] | None = None,
        *,
        assume_yes: bool = False,
        interactive: bool = True,
    ) -> list[HealResult]:
        """Apply auto-fixable findings. ``interactive`` prompts per fix in a TTY."""
        findings = findings if findings is not None else self.scan()
        results: list[HealResult] = []
        for f in findings:
            if f.severity == Severity.INFO or not f.auto_fixable:
                status = HealStatus.SKIPPED if f.severity == Severity.INFO else HealStatus.MANUAL
                results.append(HealResult(f, status))
                continue
            fixer = _FIXERS[f.id]
            if interactive and not assume_yes and sys.stdin.isatty():
                answer = input(f"Apply fix '{f.id}' ({f.fix_hint})? [y/N] ")
                if answer.strip().lower() not in {"y", "yes"}:
                    results.append(HealResult(f, HealStatus.SKIPPED, "declined"))
                    continue
            try:
                detail = fixer(self.os_root, self.project_root)
                results.append(HealResult(f, HealStatus.APPLIED, detail))
            except Exception as exc:
                results.append(HealResult(f, HealStatus.FAILED, str(exc)))
        self._audit(results)
        return results

    def _audit(self, results: list[HealResult]) -> None:
        applied = [r for r in results if r.status in {HealStatus.APPLIED, HealStatus.FAILED}]
        if not applied:
            return
        state = self.project_root / "state"
        state.mkdir(parents=True, exist_ok=True)
        log = state / "heal.log"
        with log.open("a", encoding="utf-8") as fh:
            for r in applied:
                fh.write(
                    json.dumps(
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "finding": r.finding.id,
                            "status": r.status.value,
                            "detail": r.detail,
                        }
                    )
                    + "\n"
                )
