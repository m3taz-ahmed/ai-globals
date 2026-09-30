#!/usr/bin/env python3
"""``aizee bootstrap`` — materialize a working aiZee OS root (P2.5).

The PyPI wheel ships the Python packages (``runtime/``, ``memory/``,
``aizee_mcp/``, ``eval/``) but not the doctrine content tree (``skills/``,
``workflows/``, ``rules/``, ``tech-stack/``, policy YAMLs). Bootstrap
scaffolds a minimal working OS root so ``pip install aizee`` is enough to
get a governed install:

- creates the required directory layout,
- copies policy YAMLs from the running install when available, else
  writes embedded minimal defaults,
- writes ``.aizee-version`` and ``.env.example``,
- optionally syncs the global MCP config,
- prints the ``AIZEE_ROOT`` export hint.

Idempotent: existing files are never overwritten unless ``force=True``.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_POLICY = """\
name: default
apiVersion: governance.aizee/v1
default_action: ask
rules:
  - name: allow-reads
    condition: "type in ['view', 'read', 'grep', 'search', 'query', 'list', 'get', 'status']"
    action: allow
    description: Read-only operations are always allowed.
  - name: block-destructive
    condition: "type in ['rm', 'delete', 'truncate', 'drop', 'destroy'] or 'rm -rf' in command"
    action: deny
    description: Destructive operations are blocked without explicit user command.
  - name: require-approval-for-write
    condition: "type in ['edit', 'write', 'apply', 'deploy']"
    action: ask
    description: Writes require approval unless explicitly approved.
"""

_GUARDIAN_POLICY = """\
name: guardian
apiVersion: governance.aizee/v1
rules:
  - name: no-secrets-in-output
    pattern: "(api[_-]?key|secret|password)\\s*[:=]"
    action: deny
"""

_PROBITY_POLICY = """\
name: probity
apiVersion: governance.aizee/v1
rules: []
"""

_MCP_FIREWALL = """\
name: mcp_firewall
apiVersion: governance.aizee/v1
default_action: ask
rules:
  - name: deny-destructive-commands
    condition: "'rm -rf' in command or 'mkfs' in command"
    action: deny
  - name: allow-reads
    condition: "action in ['read', 'search', 'query']"
    action: allow
"""

_EMBEDDED_POLICIES: dict[str, str] = {
    "default.yaml": _DEFAULT_POLICY,
    "guardian.yaml": _GUARDIAN_POLICY,
    "probity.yaml": _PROBITY_POLICY,
    "mcp_firewall.yaml": _MCP_FIREWALL,
}

_DIRS = [
    "skills",
    "workflows",
    "rules",
    "tech-stack",
    "scripts",
    "state",
    "brain",
    "memory/archive",
    "runtime/policies",
]

_ENV_EXAMPLE = """\
# aiZee environment template — copy to .env and fill in.
# AIZEE_INTEGRITY_KEY=           # 64-hex HMAC key for memory integrity (else auto-generated)
# AIZEE_ENFORCE_STRICT=0         # 1 = fail-closed when enforcement kernel is unavailable
# AIZEE_PR_ID=                   # set in CI to enforce per-PR spend limits
# AIZEE_RELEASE_TARGET=0.80      # reliability release-gate threshold
# AIZEE_RELEASE_KMIN=5           # min rollouts per task for the release gate
"""


@dataclass
class BootstrapResult:
    ok: bool
    target: str
    created_dirs: list[str] = field(default_factory=list)
    written_files: list[str] = field(default_factory=list)
    skipped_existing: list[str] = field(default_factory=list)
    mcp_synced: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "target": self.target,
            "created_dirs": self.created_dirs,
            "written_files": self.written_files,
            "skipped_existing": self.skipped_existing,
            "mcp_synced": self.mcp_synced,
            "notes": self.notes,
        }


def bootstrap(
    target: Path,
    source_root: Path | None = None,
    *,
    force: bool = False,
    mcp_sync: bool = True,
    dry_run: bool = False,
) -> BootstrapResult:
    """Materialize a minimal working aiZee OS root at ``target``.

    ``source_root``: a full install to copy policy files from (defaults to
    the running install's root). ``dry_run`` reports without writing.
    """
    import config

    result = BootstrapResult(ok=True, target=str(target))

    for rel in _DIRS:
        d = target / rel
        if d.exists():
            result.skipped_existing.append(rel + "/")
            continue
        result.created_dirs.append(rel + "/")
        if not dry_run:
            d.mkdir(parents=True, exist_ok=True)

    for name, embedded in _EMBEDDED_POLICIES.items():
        dest = target / "runtime" / "policies" / name
        if dest.exists() and not force:
            result.skipped_existing.append(str(dest.name))
            continue
        src = source_root / "runtime" / "policies" / name if source_root else None
        if not dry_run:
            if src and src.exists():
                shutil.copy2(src, dest)
            else:
                dest.write_text(embedded, encoding="utf-8", newline="\n")
        result.written_files.append(f"runtime/policies/{name}")

    version_file = target / ".aizee-version"
    if version_file.exists() and not force:
        result.skipped_existing.append(".aizee-version")
    else:
        if not dry_run:
            version_file.write_text(config.VERSION + "\n", encoding="utf-8")
        result.written_files.append(".aizee-version")

    env_example = target / ".env.example"
    if env_example.exists() and not force:
        result.skipped_existing.append(".env.example")
    else:
        if not dry_run:
            env_example.write_text(_ENV_EXAMPLE, encoding="utf-8", newline="\n")
        result.written_files.append(".env.example")

    if mcp_sync and not dry_run:
        sync_script = (source_root or Path(__file__).resolve().parent.parent) / "scripts" / "mcp_global_sync.py"
        if sync_script.exists():
            proc = subprocess.run(
                [sys.executable, str(sync_script)],
                capture_output=True, text=True, timeout=120,
            )
            result.mcp_synced = proc.returncode == 0
            if not result.mcp_synced:
                result.notes.append(f"mcp sync failed: {proc.stderr.strip()[:200]}")
        else:
            result.notes.append("mcp_global_sync.py not found — skipped")

    result.notes.append(f"set AIZEE_ROOT={target} to activate this OS root")
    return result


__all__ = ["BootstrapResult", "bootstrap"]
