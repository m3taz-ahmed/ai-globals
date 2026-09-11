#!/usr/bin/env python3
"""SHA-256 fingerprinting for MCP server manifests (inspired by vault).

Computes and persists cryptographic fingerprints of an MCP server's
command, args, and tool descriptions so that rug-pulls — silent changes
to a previously-approved server — can be detected on subsequent runs.

Lock files are stored as individual JSON files inside ``lock_dir``, one
per server. All operations are thread-safe via an ``RLock``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)


# -- Fingerprint ------------------------------------------------------------


@dataclass
class ManifestFingerprint:
    """Cryptographic fingerprint of an MCP server manifest.

    Attributes:
        server_name: Name of the MCP server.
        command_hash: SHA-256 of the command string.
        args_hash: SHA-256 of the JSON-serialized, sorted args list.
        tools_hash: Dict mapping tool name -> SHA-256 of its description.
        locked_at: ISO-8601 timestamp of when the lock was created.
        locked_by: Optional identity that created the lock.
    """

    server_name: str
    command_hash: str
    args_hash: str
    tools_hash: dict[str, str] = field(default_factory=dict)
    locked_at: str = ""
    locked_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON storage."""
        return {
            "server_name": self.server_name,
            "command_hash": self.command_hash,
            "args_hash": self.args_hash,
            "tools_hash": self.tools_hash,
            "locked_at": self.locked_at,
            "locked_by": self.locked_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ManifestFingerprint:
        """Deserialize from a plain dict."""
        return cls(
            server_name=str(data["server_name"]),
            command_hash=str(data["command_hash"]),
            args_hash=str(data["args_hash"]),
            tools_hash={
                str(k): str(v) for k, v in data.get("tools_hash", {}).items()
            },
            locked_at=str(data.get("locked_at", "")),
            locked_by=(
                str(data["locked_by"]) if data.get("locked_by") else None
            ),
        )


# -- Lock manager -----------------------------------------------------------


class ManifestLock:
    """Manages SHA-256 fingerprint lock files for MCP servers.

    Each lock is stored as ``<lock_dir>/<server_name>.json``. The class
    is thread-safe; concurrent callers are serialized via an ``RLock``.
    """

    _SUFFIX = ".json"

    def __init__(self, lock_dir: Path) -> None:
        """Initialize the lock manager.

        Args:
            lock_dir: Directory where lock files are stored. Created if
                it does not exist.
        """
        self._lock_dir = lock_dir
        self._rlock = threading.RLock()
        self._lock_dir.mkdir(parents=True, exist_ok=True)

    # -- Path helpers -----------------------------------------------------

    def _lock_path(self, server_name: str) -> Path:
        """Return the lock-file path for a given server name."""
        safe_name = server_name.replace("/", "_").replace("\\", "_")
        return self._lock_dir / f"{safe_name}{self._SUFFIX}"

    # -- Hashing helpers --------------------------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        """Compute the SHA-256 hex digest of a string."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_args(args: list[str]) -> str:
        """Hash an args list using sorted JSON serialization."""
        serialized = json.dumps(args, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _hash_tools(tools: dict[str, str]) -> dict[str, str]:
        """Hash each tool description, returning a name->hash dict."""
        return {
            name: hashlib.sha256(desc.encode("utf-8")).hexdigest()
            for name, desc in tools.items()
        }

    # -- Public API -------------------------------------------------------

    def lock(
        self, server_name: str, command: str, args: list[str],
        tools: dict[str, str], locked_by: str | None = None,
    ) -> ManifestFingerprint:
        """Compute and persist a fingerprint for the given server.

        Args:
            server_name: Name of the MCP server.
            command: The command string used to launch the server.
            args: The argument list passed to the command.
            tools: Dict mapping tool name -> description.
            locked_by: Optional identity creating the lock.

        Returns:
            The computed ``ManifestFingerprint``.
        """
        fp = self._build_fingerprint(server_name, command, args, tools, locked_by)
        with self._rlock:
            self._write_lock(fp)
        _logger.info("Locked MCP server manifest",
                     extra={"server_name": server_name, "locked_by": locked_by or "unknown"})
        return fp

    def _build_fingerprint(
        self, server_name: str, command: str, args: list[str],
        tools: dict[str, str], locked_by: str | None,
    ) -> ManifestFingerprint:
        """Build a ManifestFingerprint from the given parameters."""
        return ManifestFingerprint(
            server_name=server_name,
            command_hash=self._sha256(command),
            args_hash=self._hash_args(args),
            tools_hash=self._hash_tools(tools),
            locked_at=datetime.now(timezone.utc).isoformat(),
            locked_by=locked_by,
        )

    def verify(
        self,
        server_name: str,
        command: str,
        args: list[str],
        tools: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Verify current server state against the saved lock.

        Args:
            server_name: Name of the MCP server.
            command: Current command string.
            args: Current argument list.
            tools: Current dict of tool name -> description.

        Returns:
            A list of drift findings. Empty if everything matches or
            no lock exists.
        """
        with self._rlock:
            saved = self.get_lock(server_name)
            if saved is None:
                return []
            return self._diff(saved, command, args, tools)

    def get_lock(self, server_name: str) -> ManifestFingerprint | None:
        """Load the saved fingerprint for a server, or ``None``."""
        with self._rlock:
            path = self._lock_path(server_name)
            if not path.exists():
                return None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return ManifestFingerprint.from_dict(data)
            except (json.JSONDecodeError, KeyError, OSError) as exc:
                _logger.warning(
                    "Failed to read manifest lock",
                    extra={"server_name": server_name, "error": str(exc)},
                )
                return None

    def list_locks(self) -> list[str]:
        """Return the names of all locked servers."""
        with self._rlock:
            names: list[str] = []
            for p in self._lock_dir.glob(f"*{self._SUFFIX}"):
                stem = p.stem
                names.append(stem)
            names.sort()
            return names

    def remove_lock(self, server_name: str) -> bool:
        """Remove the lock for a server. Returns ``True`` if removed."""
        with self._rlock:
            path = self._lock_path(server_name)
            if not path.exists():
                return False
            try:
                path.unlink()
            except OSError as exc:
                _logger.error(
                    "Failed to remove manifest lock",
                    extra={"server_name": server_name, "error": str(exc)},
                )
                return False
            _logger.info(
                "Removed MCP server manifest lock",
                extra={"server_name": server_name},
            )
            return True

    # -- Internal ---------------------------------------------------------

    def _write_lock(self, fp: ManifestFingerprint) -> None:
        """Persist a fingerprint to disk."""
        path = self._lock_path(fp.server_name)
        try:
            path.write_text(
                json.dumps(fp.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            _logger.error(
                "Failed to write manifest lock",
                extra={"server_name": fp.server_name, "error": str(exc)},
            )
            raise AizeeError(
                "MANIFEST_LOCK_WRITE_FAILED",
                f"Failed to write manifest lock for '{fp.server_name}'",
                ErrorSeverity.HIGH,
                {"server_name": fp.server_name, "error": str(exc)},
            ) from exc

    @staticmethod
    def _diff(
        saved: ManifestFingerprint, command: str,
        args: list[str], tools: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Compute drift findings between a saved lock and current state."""
        findings: list[dict[str, Any]] = []
        findings.extend(ManifestLock._diff_command(saved, command))
        findings.extend(ManifestLock._diff_args(saved, args))
        findings.extend(ManifestLock._diff_tools(saved, tools))
        return findings

    @staticmethod
    def _diff_command(
        saved: ManifestFingerprint, command: str,
    ) -> list[dict[str, Any]]:
        """Check if command hash changed."""
        cmd_hash = hashlib.sha256(command.encode("utf-8")).hexdigest()
        if cmd_hash != saved.command_hash:
            return [{
                "field": "command", "expected_hash": saved.command_hash,
                "actual_hash": cmd_hash, "severity": "critical",
                "message": "Command changed since lock.",
            }]
        return []

    @staticmethod
    def _diff_args(
        saved: ManifestFingerprint, args: list[str],
    ) -> list[dict[str, Any]]:
        """Check if args hash changed."""
        args_hash = hashlib.sha256(
            json.dumps(args, sort_keys=True, ensure_ascii=False).encode("utf-8"),
        ).hexdigest()
        if args_hash != saved.args_hash:
            return [{
                "field": "args", "expected_hash": saved.args_hash,
                "actual_hash": args_hash, "severity": "critical",
                "message": "Args changed since lock.",
            }]
        return []

    @staticmethod
    def _diff_tools(
        saved: ManifestFingerprint, tools: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Check for changed or removed tool descriptions."""
        findings: list[dict[str, Any]] = []
        for tname, desc in tools.items():
            desc_hash = hashlib.sha256(desc.encode("utf-8")).hexdigest()
            if tname in saved.tools_hash and desc_hash != saved.tools_hash[tname]:
                findings.append({
                    "field": f"tools.{tname}.description",
                    "expected_hash": saved.tools_hash[tname],
                    "actual_hash": desc_hash, "severity": "critical",
                    "message": f"Tool '{tname}' description changed since lock.",
                })
        for tname in saved.tools_hash:
            if tname not in tools:
                findings.append({
                    "field": f"tools.{tname}",
                    "expected_hash": saved.tools_hash[tname],
                    "actual_hash": None, "severity": "high",
                    "message": f"Tool '{tname}' removed since lock.",
                })
        return findings
