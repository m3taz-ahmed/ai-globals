#!/usr/bin/env python3
"""Project security scanner — ``aizee security scan``.

Two-layer scanner for any project directory:

1. Built-in deterministic rules (always run, zero deps): secrets, injection
   sinks, crypto misuse, misconfiguration — mapped to OWASP Top 10:2025.
2. External scanners (gracefully skipped when absent): bandit, ruff -S,
   pip-audit, npm audit, composer audit, trivy.

Findings carry severity + OWASP category + file:line evidence, matching the
``tech-stack/appsec-hardening.md`` doctrine.

aizee-scan: ignore-file — this module IS the rule table; pattern strings here
are literal detection text, not executable sinks.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

_MAX_FILE_BYTES = 512_000
_TOOL_TIMEOUT_S = 120
# Inline suppression markers (bandit-style). `aizee-scan: ignore` suppresses
# every rule on that line; `aizee-scan: ignore RID1,RID2` suppresses only the
# listed rules. `aizee-scan: ignore-file` in the first 4 KiB skips the file.
_SUPPRESS_RE = re.compile(r"aizee-scan:\s*ignore\b([^\n]*)")
_SUPPRESS_FILE = "aizee-scan: ignore-file"
_SKIP_FILES = {"sbom.json"}  # generated artifacts, not source
_SKIP_DIRS = {
    ".git", "node_modules", "vendor", ".venv", "venv", "__pycache__",
    "dist", "build", ".next", ".nuxt", "coverage", ".mypy_cache",
    ".pytest_cache", ".idea", ".vscode", "target", "out",
    # Non-production trees — fixtures/examples dominate findings there.
    "tests", "test", "fixtures", "__fixtures__", "temp", "backups", "backup",
    # Generated artifacts — caches/reports, not source.
    "graphify-out", "htmlcov", "site", "env",
}
# Matched text suppressed even when a rule fires (canonical example values).
_ALLOWLIST = (re.compile(r"AKIAIOSFODNN7EXAMPLE"),)
_SCAN_EXTS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".php", ".env", ".ini",
    ".cfg", ".conf", ".yml", ".yaml", ".json", ".toml", ".sh",
}


class ScanSeverity(str, Enum):
    """Finding severity tiers."""

    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ScanFinding:
    """One security finding with evidence."""

    rule_id: str
    severity: ScanSeverity
    category: str  # OWASP 2025 category or domain label
    message: str
    file: str = ""
    line: int = 0
    scanner: str = "builtin"

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "category": self.category,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "scanner": self.scanner,
        }


@dataclass
class ScanReport:
    """Aggregate scan result."""

    target: str = ""
    files_scanned: int = 0
    tools_run: list[str] = field(default_factory=list)
    tools_skipped: list[str] = field(default_factory=list)
    suppressed: int = 0
    findings: list[ScanFinding] = field(default_factory=list)

    @property
    def blockers(self) -> list[ScanFinding]:
        return [f for f in self.findings if f.severity is ScanSeverity.BLOCKER]

    @property
    def ok(self) -> bool:
        return not self.blockers

    def summary(self) -> dict[str, int]:
        counts = {s.value: 0 for s in ScanSeverity}
        for f in self.findings:
            counts[f.severity.value] += 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "files_scanned": self.files_scanned,
            "tools_run": self.tools_run,
            "tools_skipped": self.tools_skipped,
            "suppressed": self.suppressed,
            "summary": self.summary(),
            "ok": self.ok,
            "findings": [f.to_dict() for f in self.findings],
        }


# (rule_id, severity, OWASP-2025 category, regex, message)
_BUILTIN_RULES: list[tuple[str, ScanSeverity, str, str, str]] = [
    # Secrets / credentials — A02/A04
    ("SEC-AWS-KEY", ScanSeverity.BLOCKER, "A04-secrets",
     r"AKIA[0-9A-Z]{16}", "AWS access key hardcoded"),
    ("SEC-PRIVKEY", ScanSeverity.BLOCKER, "A04-secrets",
     r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "Private key material in tree"),
    ("SEC-GENERIC-SECRET", ScanSeverity.HIGH, "A04-secrets",
     r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[=:]\s*['\"][^'\"]{8,}['\"]",
     "Possible hardcoded credential"),
    ("SEC-ENVFILE", ScanSeverity.BLOCKER, "A02-misconfig",
     r"(?m)^[^#\n]*(?:SECRET|PASSWORD|TOKEN|KEY)[ \t]*=[ \t]*[^\s#]",
     "Committed .env-style secrets"),
    # Injection — A05
    ("INJ-SHELL-TRUE", ScanSeverity.HIGH, "A05-injection",
     r"subprocess\.[^(]+\([^)]*shell\s*=\s*True", "subprocess with shell=True"),
    ("INJ-EVAL", ScanSeverity.HIGH, "A05-injection",
     r"\b(?:eval|exec)\s*\(", "eval/exec on dynamic input"),
    ("INJ-OS-SYSTEM", ScanSeverity.HIGH, "A05-injection",
     r"\bos\.system\s*\(", "os.system() shell injection risk"),
    ("INJ-YAML-LOAD", ScanSeverity.HIGH, "A05-injection",
     r"yaml\.load\s*\([^)]*\)", "yaml.load without SafeLoader — code execution risk"),
    ("INJ-PICKLE", ScanSeverity.HIGH, "A08-integrity",
     r"\bpickle\.loads?\s*\(", "pickle on untrusted data = RCE"),
    ("INJ-SQL-CONCAT", ScanSeverity.HIGH, "A05-injection",
     r"(?i)(?:execute|query)\s*\(\s*[^)]*\+", "Possible SQL string concatenation"),
    # TLS / crypto — A04
    ("TLS-VERIFY-OFF", ScanSeverity.HIGH, "A04-crypto",
     r"\bverify\s*=\s*False", "TLS verification disabled"),
    ("TLS-WEAK-HASH", ScanSeverity.MEDIUM, "A04-crypto",
     r"(?i)\b(?:md5|sha1)\s*\((?![^\n]*usedforsecurity\s*=\s*False)",
     "Weak hash (md5/sha1) — Argon2id/bcrypt for passwords"),
    ("JWT-NONE", ScanSeverity.HIGH, "A07-authn",
     r"(?i)algorithms?\s*[=:]\s*\[?\s*['\"]none['\"]", "JWT alg=none accepted"),
    # Misconfiguration — A02
    ("CFG-DEBUG", ScanSeverity.MEDIUM, "A02-misconfig",
     r"(?i)\b(?:debug|flask_debug|app_debug)\s*[=:]\s*(?:True|['\"]?true['\"]?|1)\b",
     "Debug mode enabled"),
    ("CFG-CORS-WILDCARD", ScanSeverity.MEDIUM, "A02-misconfig",
     r"(?i)(allow_origins|cors_origins|access-control-allow-origin)\s*[=:]\s*[^\n]*\*",
     "CORS wildcard origin"),
    ("CFG-BIND-ALL", ScanSeverity.MEDIUM, "A02-misconfig",
     r"host\s*=\s*['\"]0\.0\.0\.0['\"]", "Binding to 0.0.0.0 — verify exposure intent"),
    # Exceptional conditions — A10
    ("A10-SWALLOW", ScanSeverity.MEDIUM, "A10-exceptions",
     r"except[^\n:]*:\s*(?:pass|\.\.\.)", "Exception swallowed — fail-closed check"),
    # Deserialization/archive — A08
    ("A08-TAR-EXTRACT", ScanSeverity.MEDIUM, "A08-integrity",
     r"\.extractall\s*\(", "tarfile.extractall without filter (traversal)"),
    # Frontend XSS surface — A05
    ("XSS-INNERHTML", ScanSeverity.MEDIUM, "A05-injection",
     r"innerHTML\s*=|dangerouslySetInnerHTML", "Unescaped DOM sink — verify sanitization"),
    ("XSS-MARK-SAFE", ScanSeverity.MEDIUM, "A05-injection",
     r"mark_safe\(|\|safe\b|v-html=", "Raw HTML rendering — verify escaping"),
    # Redirects — A01
    ("REDIR-OPEN", ScanSeverity.MEDIUM, "A01-access-control",
     r"(?i)(redirect|location\.href)\s*\(?[^)]*(?:next|returnurl|redirect_uri|continue)",
     "Possible open redirect — allowlist targets"),
    # HTTP transport — A02
    ("HTTP-PLAINTEXT", ScanSeverity.LOW, "A02-misconfig",
     r"http://[a-zA-Z0-9-]+\.(?!localhost)[a-zA-Z]{2,}", "Plaintext http:// URL"),
]


class SecurityScanner:
    """Scan a project tree with built-in rules + optional external tools."""

    def __init__(self, extra_skip_dirs: set[str] | None = None) -> None:
        self._skip = set(_SKIP_DIRS) | (extra_skip_dirs or set())
        self._compiled = [
            (rid, sev, cat, re.compile(pat), msg)
            for rid, sev, cat, pat, msg in _BUILTIN_RULES
        ]
        self._root: Path | None = None
        self._gitignored: dict[Path, bool] = {}

    def scan(self, target: str | Path, use_tools: bool = True) -> ScanReport:
        root = Path(target).resolve()
        report = ScanReport(target=str(root))
        self._root = root
        self._gitignored = {}
        if not root.exists():
            report.findings.append(ScanFinding(
                "SCAN-TARGET", ScanSeverity.BLOCKER, "scan",
                f"Target does not exist: {root}",
            ))
            return report
        report.files_scanned = self._scan_files(root, report)
        self._check_env_files(root, report)
        if use_tools:
            self._run_tools(root, report)
        seen: set[tuple[str, str, int]] = set()
        uniq: list[ScanFinding] = []
        for f in report.findings:
            key = (f.rule_id, f.file, f.line)
            if key not in seen:
                seen.add(key)
                uniq.append(f)
        report.findings = uniq
        report.findings.sort(
            key=lambda f: (
                list(ScanSeverity).index(f.severity), f.file, f.line
            )
        )
        return report

    def _scan_files(self, root: Path, report: ScanReport) -> int:
        count = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file() or self._skipped(path):
                continue
            if path.name in _SKIP_FILES:
                continue
            if (path.suffix.lower() not in _SCAN_EXTS
                    and not path.name.lower().startswith(".env")):
                continue
            try:
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if _SUPPRESS_FILE in text[:4096]:
                report.suppressed += 1
                continue
            count += 1
            self._apply_rules(text, path, report)
        return count

    def _skipped(self, path: Path) -> bool:
        return any(part in self._skip for part in path.parts)

    def _apply_rules(
        self, text: str, path: Path, report: ScanReport
    ) -> None:
        rel = str(path)
        for rid, sev, cat, cre, msg in self._compiled:
            for match in cre.finditer(text):
                if rid == "SEC-ENVFILE" and ".env" not in path.name.lower():
                    continue
                if any(allow.search(match.group(0)) for allow in _ALLOWLIST):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                if self._suppressed(text, match.start(), rid, report):
                    continue
                severity = sev
                note = msg
                if rid == "SEC-ENVFILE" and self._is_git_ignored(path):
                    severity = ScanSeverity.LOW
                    note = ".env secrets in gitignored file — ensure never committed"
                report.findings.append(ScanFinding(
                    rid, severity, cat, note, file=rel, line=line,
                ))

    def _suppressed(
        self, text: str, pos: int, rid: str, report: ScanReport
    ) -> bool:
        start = text.rfind("\n", 0, pos) + 1
        end = text.find("\n", pos)
        line = text[start:end if end != -1 else len(text)]
        marker = _SUPPRESS_RE.search(line)
        if marker is None:
            return False
        listed = marker.group(1).strip()
        if listed and rid not in re.split(r"[,\s]+", listed):
            return False
        report.suppressed += 1
        return True

    def _is_git_ignored(self, path: Path) -> bool:
        if path in self._gitignored:
            return self._gitignored[path]
        ignored = False
        if self._root is not None and shutil.which("git") is not None:
            try:
                rel = path.relative_to(self._root)
            except ValueError:
                rel = path
            res = self._run_cmd(
                ["git", "check-ignore", "-q", str(rel)], self._root
            )
            ignored = res is not None and res.returncode == 0
        self._gitignored[path] = ignored
        return ignored

    def _check_env_files(self, root: Path, report: ScanReport) -> None:
        env = root / ".env"
        if not env.is_file():
            return
        try:
            if _SUPPRESS_FILE in env.read_text(encoding="utf-8", errors="replace")[:4096]:
                report.suppressed += 1
                return
        except OSError:  # aizee-scan: ignore A10-SWALLOW — unreadable env file, presence check proceeds
            pass
        already = any(
            f.rule_id == "SEC-ENVFILE" and f.file == str(env)
            for f in report.findings
        )
        if not already:
            if self._is_git_ignored(env):
                report.findings.append(ScanFinding(
                    "SEC-ENV-COMMITTED", ScanSeverity.LOW, "A02-misconfig",
                    ".env present but gitignored — ensure never committed",
                    file=str(env),
                ))
            else:
                report.findings.append(ScanFinding(
                    "SEC-ENV-COMMITTED", ScanSeverity.BLOCKER, "A02-misconfig",
                    ".env present in project tree — verify it is gitignored",
                    file=str(env),
                ))

    def _run_tools(self, root: Path, report: ScanReport) -> None:
        runners = (
            ("bandit", self._bandit),
            ("ruff", self._ruff_s),
            ("pip-audit", self._pip_audit),
            ("npm", self._npm_audit),
            ("composer", self._composer_audit),
            ("trivy", self._trivy),
        )
        for name, fn in runners:
            if shutil.which(name) is None:
                report.tools_skipped.append(name)
                continue
            report.tools_run.append(name)
            fn(root, report)

    @staticmethod
    def _run_cmd(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                argv, cwd=str(cwd), capture_output=True, text=True,
                timeout=_TOOL_TIMEOUT_S, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None

    def _bandit(self, root: Path, report: ScanReport) -> None:
        res = self._run_cmd(
            ["bandit", "-r", str(root), "-f", "json", "-q"], root
        )
        if res is None or not res.stdout.strip():
            return
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        for item in data.get("results", []):
            sev = {
                "HIGH": ScanSeverity.HIGH,
                "MEDIUM": ScanSeverity.MEDIUM,
                "LOW": ScanSeverity.LOW,
            }.get(item.get("issue_severity", ""), ScanSeverity.LOW)
            report.findings.append(ScanFinding(
                item.get("test_id", "B???"), sev, "A05-injection",
                item.get("issue_text", "bandit finding"),
                file=item.get("filename", ""),
                line=int(item.get("line_number") or 0),
                scanner="bandit",
            ))

    def _ruff_s(self, root: Path, report: ScanReport) -> None:
        res = self._run_cmd(
            ["ruff", "check", str(root), "--select", "S", "--output-format", "json"],
            root,
        )
        if res is None or not res.stdout.strip():
            return
        try:
            items = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        for item in items:
            loc = item.get("location", {})
            report.findings.append(ScanFinding(
                item.get("code", "S???"), ScanSeverity.MEDIUM, "A05-injection",
                item.get("message", "ruff S finding"),
                file=item.get("filename", ""),
                line=int(loc.get("row") or 0),
                scanner="ruff",
            ))

    def _pip_audit(self, root: Path, report: ScanReport) -> None:
        req = root / "requirements.txt"
        if not req.is_file():
            return
        res = self._run_cmd(
            ["pip-audit", "-r", str(req), "-f", "json"], root
        )
        if res is None or not res.stdout.strip():
            return
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        for dep in data.get("dependencies", data if isinstance(data, list) else []):
            for vuln in dep.get("vulns", []):
                report.findings.append(ScanFinding(
                    vuln.get("id", "CVE"), ScanSeverity.HIGH, "A03-supply-chain",
                    f"{dep.get('name', '?')} {dep.get('version', '')}: "
                    f"{vuln.get('description', vuln.get('id', ''))[:140]}",
                    scanner="pip-audit",
                ))

    def _npm_audit(self, root: Path, report: ScanReport) -> None:
        if not (root / "package.json").is_file():
            return
        res = self._run_cmd(
            ["npm", "audit", "--json", "--audit-level=low"], root
        )
        if res is None or not res.stdout.strip():
            return
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        for name, v in (data.get("vulnerabilities") or {}).items():
            sev = {
                "critical": ScanSeverity.BLOCKER,
                "high": ScanSeverity.HIGH,
                "moderate": ScanSeverity.MEDIUM,
                "low": ScanSeverity.LOW,
            }.get(str(v.get("severity", "")).lower(), ScanSeverity.MEDIUM)
            report.findings.append(ScanFinding(
                name, sev, "A03-supply-chain",
                f"npm vulnerability: {name} ({v.get('severity')})",
                scanner="npm-audit",
            ))

    def _composer_audit(self, root: Path, report: ScanReport) -> None:
        if not (root / "composer.lock").is_file():
            return
        res = self._run_cmd(
            ["composer", "audit", "--format=json", "--no-interaction"], root
        )
        if res is None or not res.stdout.strip():
            return
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        advisories = data.get("advisories", {})
        entries = advisories.values() if isinstance(advisories, dict) else advisories
        for adv in entries:
            for item in adv if isinstance(adv, list) else [adv]:
                report.findings.append(ScanFinding(
                    item.get("advisoryId", "ADV"), ScanSeverity.HIGH,
                    "A03-supply-chain",
                    f"composer advisory: {item.get('packageName', '?')}",
                    scanner="composer-audit",
                ))

    def _trivy(self, root: Path, report: ScanReport) -> None:
        res = self._run_cmd(
            ["trivy", "fs", str(root), "--format", "json",
             "--severity", "HIGH,CRITICAL", "--quiet"],
            root,
        )
        if res is None or not res.stdout.strip():
            return
        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            return
        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities") or []:
                sev = (ScanSeverity.BLOCKER
                       if vuln.get("Severity") == "CRITICAL"
                       else ScanSeverity.HIGH)
                report.findings.append(ScanFinding(
                    vuln.get("VulnerabilityID", "CVE"), sev,
                    "A03-supply-chain",
                    f"{vuln.get('PkgName', '?')}: {vuln.get('Title', '')[:140]}",
                    file=result.get("Target", ""),
                    scanner="trivy",
                ))


def scan_project(
    target: str | Path,
    use_tools: bool = True,
    extra_skip_dirs: set[str] | None = None,
) -> ScanReport:
    """Scan a project directory and return a severity-ranked report."""
    return SecurityScanner(extra_skip_dirs=extra_skip_dirs).scan(
        target, use_tools=use_tools
    )
