#!/usr/bin/env python3
"""Deterministic MCP server security scanner (inspired by mcp-sentinel).

Scans MCP server configs and tool manifests for 14 classes of security
issues, returning structured ``Finding`` objects with severity, detector
name, offending path/value, reason, and a concrete fix suggestion.

Detectors
----------
1.  UNPINNED_PACKAGE      — npx/uvx without exact version
2.  REMOTE_SCRIPT         — curl|wget piped to shell, raw URL as command
3.  WRITABLE_PATH         — command under group/other-writable path
4.  NON_HTTPS_URL         — HTTP URL not on loopback
5.  PLAINTEXT_SECRET      — API key/token in env block (redacted)
6.  OVERBROAD_ROOT        — filesystem server rooted at /, ~, or home
7.  CREDENTIAL_DIR        — path includes .ssh/.aws/.config/etc.
8.  APPROVAL_BYPASS       — flags that skip approval/sandbox
9.  IMPERATIVE_INJECTION — imperative phrasing in tool description
10. HIDDEN_CONTENT        — HTML comment or long base64/hex blob
11. INVISIBLE_UNICODE     — zero-width/bidi/tag/homoglyph chars
12. CROSS_SERVER_REF      — description names a tool from another server
13. NAME_COLLISION        — same tool name exposed by multiple servers
14. RUGPULL               — locked server's command/description changed
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)

# -- Severity ---------------------------------------------------------------


class FindingSeverity(str, Enum):
    """Severity levels for audit findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# -- Finding ----------------------------------------------------------------


@dataclass
class Finding:
    """A single security finding produced by a detector.

    Attributes:
        detector: Name of the detector that produced this finding.
        severity: Severity of the finding.
        server_name: Name of the MCP server involved.
        path: Dotted path into the config/manifest where the issue was found.
        value: Offending value (REDACTED for secret detectors).
        reason: Human-readable explanation of why this is a problem.
        fix: Concrete remediation suggestion.
    """

    detector: str
    severity: FindingSeverity
    server_name: str
    path: str
    value: str
    reason: str
    fix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize this finding to a plain dict."""
        return {
            "detector": self.detector,
            "severity": self.severity.value,
            "server_name": self.server_name,
            "path": self.path,
            "value": self.value,
            "reason": self.reason,
            "fix": self.fix,
        }


# -- Regex patterns ---------------------------------------------------------

# npx/uvx without exact version: @latest or bare package name (no @ver)
_UNPINNED_PACKAGE = re.compile(
    r"^(?:npx|uvx)\s+(?:-y\s+|--yes\s+)*"
    r"(?P<pkg>@?[^\s@/]+(?:/[^\s@/]+)?(?:@[^\s]+)?)",
    re.IGNORECASE,
)
_PINED_PACKAGE = re.compile(r"@(\d+\.\d+\.\d+)", re.IGNORECASE)

# curl/wget piped to shell
_REMOTE_SCRIPT_PIPE = re.compile(
    r"(?:curl|wget)\b.*?\|\s*(?:sh|bash|zsh|python|perl|ruby)\b",
    re.IGNORECASE,
)
_RAW_URL_COMMAND = re.compile(r"^(?:https?|ftp)://", re.IGNORECASE)

# HTTP (non-HTTPS) URL not on loopback
_NON_HTTPS_URL = re.compile(
    r"^http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)", re.IGNORECASE,
)

# Plaintext secret in env block
_SECRET_KEY_PATTERNS = re.compile(
    r"(?:api[_-]?key|secret|password|token|credential|auth)",
    re.IGNORECASE,
)
_SECRET_VALUE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"),
    re.compile(r"xox[baprs]-[a-zA-Z0-9-]{10,}"),
    re.compile(r"[a-zA-Z0-9_\-]{32,}"),
]

# Overbroad filesystem root
_OVERBROAD_ROOTS = {"/", "~", "$HOME", "${HOME}", "%USERPROFILE%", "C:\\", "C:/"}

# Credential directories
_CREDENTIAL_DIRS = (
    ".ssh", ".aws", ".config", ".gnupg", ".kube", ".docker", ".azure", ".netrc",
)

# Approval-bypass flags
_APPROVAL_BYPASS_PATTERNS = re.compile(
    r"(--dangerously-skip-permissions|autoApprove|disableSandbox|--yolo|"
    r"--no-approval|--yes-to-all|--allow-all)",
    re.IGNORECASE,
)

# Imperative injection phrasing
_IMPERATIVE_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"do\s+not\s+tell\s+the\s+user", re.IGNORECASE),
    re.compile(r"before\s+using\s+any\s+other\s+tool,?\s*first", re.IGNORECASE),
    re.compile(r"<IMPORTANT>", re.IGNORECASE),
    re.compile(r"disregard\s+(?:the\s+)?above", re.IGNORECASE),
    re.compile(r"forget\s+(?:everything|all\s+rules)", re.IGNORECASE),
]

# Hidden content: HTML comment or long base64/hex blob
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_LONG_BLOB = re.compile(r"(?:[A-Za-z0-9+/]{60,}={0,2}|[0-9a-fA-F]{60,})")

# Invisible unicode ranges
_INVISIBLE_UNICODE_RANGES = [
    (0x200B, 0x200D), (0x202A, 0x202E), (0x2066, 0x2069), (0xE0000, 0xE007F),
]
_HOMOGLYPHS = {
    "\u0430", "\u0435", "\u043E", "\u0440", "\u0441", "\u0445",
    "\u0410", "\u0415", "\u041E", "\u0420", "\u0421", "\u0425",
}

# Cross-server tool reference
_CROSS_SERVER_REF = re.compile(
    r"(?:use\s+(?:the\s+)?|call\s+(?:the\s+)?|invoke\s+(?:the\s+)?)"
    r"(?P<tool>[a-zA-Z_][a-zA-Z0-9_-]*)\s+(?:tool|function|command)",
    re.IGNORECASE,
)


# -- Helpers ----------------------------------------------------------------


def _redact(value: str) -> str:
    """Redact a secret value, keeping only first 2 and last 2 chars."""
    if len(value) <= 8:
        return "REDACTED"
    return f"{value[:2]}…{value[-2:]} (REDACTED)"


def _is_writable_path(path_str: str) -> tuple[bool, str]:
    """Check if a path is group/other-writable. Returns (is_writable, who)."""
    try:
        p = Path(path_str).expanduser()
        if not p.exists():
            return False, ""
        mode = p.stat().st_mode
        if mode & 0o022:
            who = []
            if mode & 0o020:
                who.append("group")
            if mode & 0o002:
                who.append("other")
            return True, "/".join(who)
    except OSError:
        pass
    return False, ""


def _has_invisible_unicode(text: str) -> list[str]:
    """Return list of invisible-unicode char descriptions found in text."""
    found: list[str] = []
    for ch in text:
        cp = ord(ch)
        for lo, hi in _INVISIBLE_UNICODE_RANGES:
            if lo <= cp <= hi:
                found.append(f"U+{cp:04X}")
                break
        if ch in _HOMOGLYPHS:
            found.append(f"U+{cp:04X} (homoglyph)")
    return found


# -- Config detectors (module-level) ----------------------------------------


def _det_unpinned_package(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect npx/uvx without a pinned exact version."""
    findings: list[Finding] = []
    full = f"{cmd} {' '.join(args)}".strip()
    m = _UNPINNED_PACKAGE.match(full)
    if m:
        pkg = m.group("pkg")
        if ("@" not in pkg or "@latest" in pkg.lower()) and not _PINED_PACKAGE.search(pkg):
            findings.append(Finding(
                detector="UNPINNED_PACKAGE", severity=FindingSeverity.HIGH,
                server_name=server, path="command", value=full[:120],
                reason="Package invoked without a pinned exact version; supply-chain risk.",
                fix=f"Pin to an exact version: {pkg.split('@')[0]}@<version>",
            ))
    return findings


def _det_remote_script(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect curl|wget piped to shell or raw URL as command."""
    findings: list[Finding] = []
    full = f"{cmd} {' '.join(args)}".strip()
    if _REMOTE_SCRIPT_PIPE.search(full):
        findings.append(Finding(
            detector="REMOTE_SCRIPT", severity=FindingSeverity.CRITICAL,
            server_name=server, path="command", value=full[:120],
            reason="Remote script piped directly to a shell interpreter.",
            fix="Download, inspect, then execute — never pipe curl|wget to sh.",
        ))
    if _RAW_URL_COMMAND.match(cmd):
        findings.append(Finding(
            detector="REMOTE_SCRIPT", severity=FindingSeverity.CRITICAL,
            server_name=server, path="command", value=cmd[:120],
            reason="Raw URL used as the command — remote code execution.",
            fix="Use a local interpreter with a pinned, reviewed script.",
        ))
    return findings


def _det_writable_path(server: str, cmd: str) -> list[Finding]:
    """Detect command under a group/other-writable path."""
    findings: list[Finding] = []
    is_w, who = _is_writable_path(cmd)
    if is_w:
        sev = FindingSeverity.HIGH if "other" in who else FindingSeverity.MEDIUM
        findings.append(Finding(
            detector="WRITABLE_PATH", severity=sev,
            server_name=server, path="command", value=cmd[:120],
            reason=f"Command path is {who}-writable; tampering risk.",
            fix="Move the binary to a root-owned, non-writable location.",
        ))
    return findings


def _det_non_https_url(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect HTTP URLs not on loopback."""
    findings: list[Finding] = []
    for i, token in enumerate([cmd, *args]):
        if _NON_HTTPS_URL.match(token):
            findings.append(Finding(
                detector="NON_HTTPS_URL", severity=FindingSeverity.HIGH,
                server_name=server, path=f"args[{i}]" if i > 0 else "command",
                value=token[:120],
                reason="Non-HTTPS URL outside loopback; MITM risk.",
                fix="Use https:// or restrict to localhost/127.0.0.1.",
            ))
    return findings


def _det_plaintext_secret(server: str, env: dict[str, Any]) -> list[Finding]:
    """Detect API keys/tokens in env block (redacted in output)."""
    findings: list[Finding] = []
    for key, val in env.items():
        val_str = str(val)
        if _SECRET_KEY_PATTERNS.search(key):
            findings.append(Finding(
                detector="PLAINTEXT_SECRET", severity=FindingSeverity.HIGH,
                server_name=server, path=f"env.{key}", value=_redact(val_str),
                reason=f"Environment variable '{key}' appears to hold a secret in plaintext.",
                fix="Use a secrets manager or OS keyring instead of env.",
            ))
            continue
        for pat in _SECRET_VALUE_PATTERNS:
            if pat.search(val_str):
                findings.append(Finding(
                    detector="PLAINTEXT_SECRET", severity=FindingSeverity.HIGH,
                    server_name=server, path=f"env.{key}", value=_redact(val_str),
                    reason=f"Environment variable '{key}' contains a recognized secret pattern.",
                    fix="Rotate the secret and load it from a secrets manager.",
                ))
                break
    return findings


def _det_overbroad_root(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect filesystem server rooted at overbroad path."""
    findings: list[Finding] = []
    for i, token in enumerate([cmd, *args]):
        if token in _OVERBROAD_ROOTS or token.rstrip("/\\") in _OVERBROAD_ROOTS:
            findings.append(Finding(
                detector="OVERBROAD_ROOT", severity=FindingSeverity.CRITICAL,
                server_name=server, path=f"args[{i}]" if i > 0 else "command",
                value=token[:120],
                reason="Filesystem server rooted at an overbroad path.",
                fix="Scope to a project-specific subdirectory.",
            ))
    return findings


def _det_credential_dir(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect paths including credential directories."""
    findings: list[Finding] = []
    for i, token in enumerate([cmd, *args]):
        for cred in _CREDENTIAL_DIRS:
            if cred in token:
                findings.append(Finding(
                    detector="CREDENTIAL_DIR", severity=FindingSeverity.CRITICAL,
                    server_name=server, path=f"args[{i}]" if i > 0 else "command",
                    value=token[:120],
                    reason=f"Path references credential directory '{cred}'.",
                    fix="Never expose credential directories to MCP servers.",
                ))
                break
    return findings


def _det_approval_bypass(server: str, cmd: str, args: list[str]) -> list[Finding]:
    """Detect flags that skip approval/sandbox."""
    findings: list[Finding] = []
    full = f"{cmd} {' '.join(args)}".strip()
    m = _APPROVAL_BYPASS_PATTERNS.search(full)
    if m:
        findings.append(Finding(
            detector="APPROVAL_BYPASS", severity=FindingSeverity.CRITICAL,
            server_name=server, path="command", value=m.group(0),
            reason="Flag bypasses approval/sandbox — removes human oversight.",
            fix="Remove the bypass flag and require explicit approval.",
        ))
    return findings


def _scan_server_config(server: str, cfg: dict[str, Any]) -> list[Finding]:
    """Run all config-level detectors on a single server config."""
    cmd = str(cfg.get("command", ""))
    raw_args = cfg.get("args", [])
    if isinstance(raw_args, str):
        args: list[str] = [raw_args]
    elif isinstance(raw_args, list):
        args = [str(a) for a in raw_args]
    else:
        args = []
    env = cfg.get("env", {})
    if not isinstance(env, dict):
        env = {}
    findings: list[Finding] = []
    findings.extend(_det_unpinned_package(server, cmd, args))
    findings.extend(_det_remote_script(server, cmd, args))
    findings.extend(_det_writable_path(server, cmd))
    findings.extend(_det_non_https_url(server, cmd, args))
    findings.extend(_det_plaintext_secret(server, env))
    findings.extend(_det_overbroad_root(server, cmd, args))
    findings.extend(_det_credential_dir(server, cmd, args))
    findings.extend(_det_approval_bypass(server, cmd, args))
    return findings


# -- Manifest detectors (module-level) --------------------------------------


def _det_imperative_injection(server: str, name: str, desc: str) -> list[Finding]:
    """Detect imperative injection phrasing in tool description."""
    for pat in _IMPERATIVE_INJECTION_PATTERNS:
        m = pat.search(desc)
        if m:
            return [Finding(
                detector="IMPERATIVE_INJECTION", severity=FindingSeverity.CRITICAL,
                server_name=server, path=f"tools.{name}.description", value=m.group(0),
                reason="Imperative injection phrasing in tool description.",
                fix="Rewrite the description in declarative, neutral tone.",
            )]
    return []


def _det_hidden_content(server: str, name: str, desc: str) -> list[Finding]:
    """Detect HTML comments or long base64/hex blobs in description."""
    findings: list[Finding] = []
    if _HTML_COMMENT.search(desc):
        findings.append(Finding(
            detector="HIDDEN_CONTENT", severity=FindingSeverity.HIGH,
            server_name=server, path=f"tools.{name}.description", value="<!--…-->",
            reason="HTML comment hidden in tool description.",
            fix="Remove all HTML comments from tool descriptions.",
        ))
    if _LONG_BLOB.search(desc):
        findings.append(Finding(
            detector="HIDDEN_CONTENT", severity=FindingSeverity.HIGH,
            server_name=server, path=f"tools.{name}.description",
            value="<long base64/hex blob>",
            reason="Long base64/hex blob in tool description.",
            fix="Remove encoded blobs from tool descriptions.",
        ))
    return findings


def _det_invisible_unicode(server: str, name: str, desc: str) -> list[Finding]:
    """Detect zero-width/bidi/tag/homoglyph Unicode characters."""
    chars = _has_invisible_unicode(desc)
    if chars:
        return [Finding(
            detector="INVISIBLE_UNICODE", severity=FindingSeverity.CRITICAL,
            server_name=server, path=f"tools.{name}.description",
            value=", ".join(chars[:5]),
            reason="Invisible/homoglyph Unicode characters in description.",
            fix="Strip all non-printable and confusable Unicode.",
        )]
    return []


def _det_cross_server_ref(server: str, name: str, desc: str) -> list[Finding]:
    """Detect description naming a tool from a different server."""
    m = _CROSS_SERVER_REF.search(desc)
    if m:
        ref_tool = m.group("tool")
        return [Finding(
            detector="CROSS_SERVER_REF", severity=FindingSeverity.MEDIUM,
            server_name=server, path=f"tools.{name}.description", value=ref_tool,
            reason=f"Description references tool '{ref_tool}' which may belong to a different server.",
            fix="Remove cross-server tool references from descriptions.",
        )]
    return []


def _scan_tool_manifest(server: str, tool: dict[str, str]) -> list[Finding]:
    """Run all manifest-level detectors on a single tool."""
    name = str(tool.get("name", ""))
    desc = str(tool.get("description", ""))
    findings: list[Finding] = []
    findings.extend(_det_imperative_injection(server, name, desc))
    findings.extend(_det_hidden_content(server, name, desc))
    findings.extend(_det_invisible_unicode(server, name, desc))
    findings.extend(_det_cross_server_ref(server, name, desc))
    return findings


def _detect_name_collisions(
    manifest: dict[str, list[dict[str, str]]],
) -> list[Finding]:
    """Detect same tool name exposed by multiple servers."""
    name_to_servers: dict[str, list[str]] = {}
    for server_name, tools in manifest.items():
        for tool in tools:
            tname = str(tool.get("name", ""))
            if tname:
                name_to_servers.setdefault(tname, []).append(server_name)
    findings: list[Finding] = []
    for tname, servers in name_to_servers.items():
        if len(servers) > 1:
            findings.append(Finding(
                detector="NAME_COLLISION", severity=FindingSeverity.HIGH,
                server_name=",".join(servers), path=f"tools.{tname}", value=tname,
                reason=f"Tool name '{tname}' exposed by multiple servers: {', '.join(servers)}.",
                fix="Rename tools to include a server-specific prefix.",
            ))
    return findings


# -- Baseline ---------------------------------------------------------------


@dataclass
class _ServerBaseline:
    """SHA-256 baseline for rug-pull detection."""

    command_hash: str
    args_hash: str
    tools_hash: dict[str, str]


# -- Auditor ----------------------------------------------------------------


class McpAuditor:
    """Deterministic MCP server security scanner.

    Thread-safe. Uses an optional lock directory to persist SHA-256
    baselines for rug-pull detection across sessions.
    """

    _LOCK_FILE_NAME = "mcp_auditor_baselines.json"

    def __init__(self, lock_dir: Path | None = None) -> None:
        self._lock_dir = lock_dir
        self._baselines: dict[str, _ServerBaseline] = {}
        self._rlock = threading.RLock()
        if lock_dir is not None:
            self._load_baselines()

    def scan_config(self, config: dict[str, Any]) -> list[Finding]:
        """Scan an ``mcpServers`` config dict and return findings."""
        findings: list[Finding] = []
        with self._rlock:
            for name, cfg in config.items():
                findings.extend(_scan_server_config(name, cfg))
        return findings

    def scan_manifest(
        self, manifest: dict[str, list[dict[str, str]]],
    ) -> list[Finding]:
        """Scan tool manifests and return findings."""
        findings: list[Finding] = []
        with self._rlock:
            for name, tools in manifest.items():
                for tool in tools:
                    findings.extend(_scan_tool_manifest(name, tool))
            findings.extend(_detect_name_collisions(manifest))
        return findings

    def scan_all(
        self, config: dict[str, Any],
        manifest: dict[str, list[dict[str, str]]],
    ) -> list[Finding]:
        """Combine config and manifest scans, sorted by severity."""
        findings = self.scan_config(config) + self.scan_manifest(manifest)
        order = {
            FindingSeverity.CRITICAL: 0, FindingSeverity.HIGH: 1,
            FindingSeverity.MEDIUM: 2, FindingSeverity.LOW: 3,
        }
        findings.sort(key=lambda f: (order[f.severity], f.detector))
        return findings

    def lock_server(
        self, server_name: str, command: str, args: list[str],
        tool_descriptions: dict[str, str],
    ) -> None:
        """Save a SHA-256 baseline for a server for future rug-pull checks."""
        with self._rlock:
            self._baselines[server_name] = _ServerBaseline(
                command_hash=self._sha256(command),
                args_hash=self._sha256(json.dumps(args, sort_keys=True)),
                tools_hash={
                    n: self._sha256(d) for n, d in tool_descriptions.items()
                },
            )
            self._save_baselines()

    def check_rugpull(
        self, server_name: str, command: str, args: list[str],
        tool_descriptions: dict[str, str],
    ) -> list[Finding]:
        """Diff current server state against the locked baseline."""
        with self._rlock:
            baseline = self._baselines.get(server_name)
            if baseline is None:
                return []
            return self._diff_baseline(server_name, command, args, tool_descriptions, baseline)

    def to_dict(self, findings: list[Finding]) -> list[dict[str, Any]]:
        """Serialize a list of findings to plain dicts."""
        return [f.to_dict() for f in findings]

    # -- Internal helpers (kept short) -----------------------------------

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _diff_baseline(
        self, server: str, command: str, args: list[str],
        tools: dict[str, str], bl: _ServerBaseline,
    ) -> list[Finding]:
        """Diff current state against a saved baseline."""
        findings: list[Finding] = []
        if self._sha256(command) != bl.command_hash:
            findings.append(Finding(
                detector="RUGPULL", severity=FindingSeverity.CRITICAL,
                server_name=server, path="command", value=command,
                reason="Server command changed since approval baseline.",
                fix="Re-approve the server after reviewing the new command.",
            ))
        if self._sha256(json.dumps(args, sort_keys=True)) != bl.args_hash:
            findings.append(Finding(
                detector="RUGPULL", severity=FindingSeverity.CRITICAL,
                server_name=server, path="args", value=json.dumps(args),
                reason="Server args changed since approval baseline.",
                fix="Re-approve the server after reviewing the new args.",
            ))
        findings.extend(self._diff_tool_descs(server, tools, bl))
        return findings

    @staticmethod
    def _diff_tool_descs(
        server: str, tools: dict[str, str], bl: _ServerBaseline,
    ) -> list[Finding]:
        """Diff tool descriptions against baseline."""
        findings: list[Finding] = []
        for tname, desc in tools.items():
            h = hashlib.sha256(desc.encode("utf-8")).hexdigest()
            if tname in bl.tools_hash and h != bl.tools_hash[tname]:
                findings.append(Finding(
                    detector="RUGPULL", severity=FindingSeverity.CRITICAL,
                    server_name=server, path=f"tools.{tname}.description",
                    value=desc[:120],
                    reason=f"Tool '{tname}' description changed since approval baseline.",
                    fix=f"Re-approve tool '{tname}' after reviewing the new description.",
                ))
        return findings

    def _load_baselines(self) -> None:
        """Load baselines from the lock directory."""
        if self._lock_dir is None:
            return
        path = self._lock_dir / self._LOCK_FILE_NAME
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for name, entry in data.items():
                self._baselines[name] = _ServerBaseline(
                    command_hash=entry["command_hash"],
                    args_hash=entry["args_hash"],
                    tools_hash=entry["tools_hash"],
                )
        except (json.JSONDecodeError, KeyError, OSError) as exc:
            _logger.warning("Failed to load MCP auditor baselines",
                            extra={"error": str(exc), "path": str(path)})

    def _save_baselines(self) -> None:
        """Persist baselines to the lock directory."""
        if self._lock_dir is None:
            return
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        path = self._lock_dir / self._LOCK_FILE_NAME
        data = {
            name: {"command_hash": bl.command_hash, "args_hash": bl.args_hash,
                   "tools_hash": bl.tools_hash}
            for name, bl in self._baselines.items()
        }
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as exc:
            _logger.error("Failed to save MCP auditor baselines",
                          extra={"error": str(exc), "path": str(path)})
