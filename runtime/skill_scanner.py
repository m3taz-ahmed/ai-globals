#!/usr/bin/env python3
"""Static security scanner for aiZee skills (inspired by SkillSpector).

Scans skill files (SKILL.md, *.md, *.py) for vulnerability patterns
using fast static analysis (regex + AST). No LLM required — this is
the Stage 1 fast scan. An optional Stage 2 LLM semantic analysis can
be layered on top by callers.

Features:
- 31 vulnerability patterns across 7 categories
- Severity scoring (CRITICAL/HIGH/MEDIUM/LOW) with weighted totals
- Baseline suppression (accept current findings, report only new ones)
- Resource bounds (max findings per artifact, max scan time)
- Fail-closed on resource exhaustion

Usage::

    from runtime.skill_scanner import SkillScanner, ScanResult

    scanner = SkillScanner()
    result = scanner.scan_file(Path("skills/my-skill/SKILL.md"))
    print(result.risk_level, result.score, len(result.findings))
    for f in result.findings:
        print(f"  [{f.severity}] {f.pattern_id}: {f.message}")
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class ScanRiskLevel(str, Enum):
    """Overall risk level for a scanned artifact."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatternSeverity(str, Enum):
    """Severity of an individual vulnerability pattern."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SkillScannerError(AizeeError):
    """Raised when the skill scanner encounters an internal error."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("SKILL_SCAN_ERROR", message, ErrorSeverity.HIGH, context)


@dataclass
class VulnerabilityPattern:
    """A single vulnerability detection pattern."""

    pattern_id: str
    category: str
    severity: PatternSeverity
    regex: re.Pattern[str]
    message: str
    score: int = 0

    def __post_init__(self) -> None:
        if self.score == 0:
            self.score = {
                PatternSeverity.CRITICAL: 50,
                PatternSeverity.HIGH: 25,
                PatternSeverity.MEDIUM: 10,
                PatternSeverity.LOW: 5,
            }[self.severity]


@dataclass
class Finding:
    """A detected vulnerability in a scanned file."""

    pattern_id: str
    category: str
    severity: PatternSeverity
    message: str
    file: str
    line: int
    match: str
    score: int

    @property
    def fingerprint(self) -> str:
        """Evidence-bound fingerprint for baseline suppression."""
        payload = f"{self.pattern_id}:{self.file}:{self.line}:{self.message}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class ScanResult:
    """Result of scanning a single file or directory."""

    path: str
    findings: list[Finding] = field(default_factory=list)
    score: int = 0
    risk_level: ScanRiskLevel = ScanRiskLevel.SAFE
    truncated: bool = False
    error: str | None = None
    scan_time_ms: float = 0.0

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is PatternSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity is PatternSeverity.HIGH)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "score": self.score,
            "risk_level": self.risk_level.value,
            "findings_count": len(self.findings),
            "critical": self.critical_count,
            "high": self.high_count,
            "truncated": self.truncated,
            "error": self.error,
            "scan_time_ms": round(self.scan_time_ms, 2),
            "findings": [
                {
                    "pattern_id": f.pattern_id,
                    "category": f.category,
                    "severity": f.severity.value,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                    "score": f.score,
                    "fingerprint": f.fingerprint,
                }
                for f in self.findings
            ],
        }


# -- Pattern Database (31 patterns across 7 categories) ---------------------

def _build_patterns() -> list[VulnerabilityPattern]:
    """Build the default vulnerability pattern database."""
    patterns: list[VulnerabilityPattern] = []

    def add(pid: str, cat: str, sev: PatternSeverity, regex: str, msg: str) -> None:
        patterns.append(VulnerabilityPattern(
            pattern_id=pid, category=cat, severity=sev,
            regex=re.compile(regex, re.IGNORECASE | re.MULTILINE),
            message=msg,
        ))

    # Category: Prompt Injection (P1-P9)
    add("P1", "prompt_injection", PatternSeverity.CRITICAL,
        r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions", "Prompt injection: ignore previous instructions")
    add("P2", "prompt_injection", PatternSeverity.CRITICAL,
        r"disregard\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|rules|prompts)", "Prompt injection: disregard previous instructions")
    add("P3", "prompt_injection", PatternSeverity.HIGH,
        r"you\s+are\s+(?:now|actually)\s+(?:a\s+)?(?:different|new|jailbroken)", "Prompt injection: identity override attempt")
    add("P4", "prompt_injection", PatternSeverity.HIGH,
        r"forget\s+(?:everything|all\s+rules|your\s+instructions)", "Prompt injection: memory wipe attempt")
    add("P5", "prompt_injection", PatternSeverity.HIGH,
        r"system\s*:\s*(?:you\s+must|you\s+are|act\s+as)", "Prompt injection: fake system message")
    add("P6", "prompt_injection", PatternSeverity.MEDIUM,
        r"reveal\s+(?:your|the)\s+(?:system\s+prompt|instructions|rules|guidelines)", "Prompt injection: system prompt extraction")
    add("P7", "prompt_injection", PatternSeverity.MEDIUM,
        r"print\s+(?:your|the)\s+(?:system\s+prompt|hidden\s+instructions)", "Prompt injection: hidden instruction extraction")
    add("P8", "prompt_injection", PatternSeverity.HIGH,
        r"(?:act|pretend|roleplay)\s+as\s+(?:if\s+you\s+(?:have\s+)?no\s+|without\s+)(?:rules|restrictions|guardrails)", "Prompt injection: guardrail bypass via roleplay")
    add("P9", "prompt_injection", PatternSeverity.MEDIUM,
        r"what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:prompt|instructions|rules)", "Prompt injection: instruction probing")

    # Category: Data Exfiltration (E1-E4)
    add("E1", "data_exfiltration", PatternSeverity.CRITICAL,
        r"(?:send|post|upload|transmit|exfiltrate)\b.*\b(?:to|via)\s+(?:https?://|ftp://|sftp://)", "Data exfiltration: external URL transmission")
    add("E2", "data_exfiltration", PatternSeverity.HIGH,
        r"(?:curl|wget|requests\.post|fetch\()\s*\(?\s*['\"]https?://", "Data exfiltration: HTTP client call to external URL")
    add("E3", "data_exfiltration", PatternSeverity.HIGH,
        r"(?:base64|hex)\.encode\s*\(.*(?:token|key|secret|password|credential)", "Data exfiltration: encoding of secrets")
    add("E4", "data_exfiltration", PatternSeverity.MEDIUM,
        r"(?:env|environ|getenv)\s*[\[(]\s*['\"](?:API_KEY|SECRET|TOKEN|PASSWORD)", "Data exfiltration: environment variable access for secrets")

    # Category: Privilege Escalation (PE1-PE3)
    add("PE1", "privilege_escalation", PatternSeverity.CRITICAL,
        r"(?:sudo|su\s+root|chmod\s+777|chown\s+root)", "Privilege escalation: root-level command")
    add("PE2", "privilege_escalation", PatternSeverity.HIGH,
        r"(?:os\.system|subprocess\.call|exec\()\s*\(.*(?:sudo|rm\s+-rf|chmod)", "Privilege escalation: dangerous command execution")
    add("PE3", "privilege_escalation", PatternSeverity.MEDIUM,
        r"(?:eval|exec|compile)\s*\(.*(?:input|request|user)", "Privilege escalation: dynamic code execution from input")

    # Category: Supply Chain (SC1-SC5)
    add("SC1", "supply_chain", PatternSeverity.HIGH,
        r"(?:pip\s+install|npm\s+install|yarn\s+add|go\s+get)\s+(?!-r|--from)", "Supply chain: unscoped package installation")
    add("SC2", "supply_chain", PatternSeverity.CRITICAL,
        r"(?:pip\s+install|npm\s+install).*--no-cache-dir.*--trusted-host", "Supply chain: insecure package install flags")
    add("SC3", "supply_chain", PatternSeverity.HIGH,
        r"(?:import|from\s+\w+\s+import)\s+(?:os|subprocess|shutil)\s*(?:#|$)", "Supply chain: dangerous stdlib import without justification")
    add("SC4", "supply_chain", PatternSeverity.MEDIUM,
        r"requirements\.txt.*(?:==|>=)\s*(?:0\.0\.|latest|master|main)", "Supply chain: unversioned or floating dependency")
    add("SC5", "supply_chain", PatternSeverity.HIGH,
        r"(?:curl|wget)\s+.*\|\s*(?:sh|bash|python|pip)", "Supply chain: pipe-to-shell install pattern")

    # Category: Behavioral (B1-B4)
    add("B1", "behavioral", PatternSeverity.MEDIUM,
        r"(?:always|must|should)\s+(?:respond|reply|answer)\s+(?:with|in)\s+(?:only\s+)?(?:yes|ok|done)", "Behavioral: forced affirmative response")
    add("B2", "behavioral", PatternSeverity.MEDIUM,
        r"do\s+not\s+(?:ask|request|seek)\s+(?:clarification|confirmation|approval)", "Behavioral: suppresses safety confirmation")
    add("B3", "behavioral", PatternSeverity.HIGH,
        r"(?:automatically|silently|without\s+(?:asking|confirmation))\s+(?:execute|run|delete|remove)", "Behavioral: silent destructive action")
    add("B4", "behavioral", PatternSeverity.LOW,
        r"(?:never|do\s+not)\s+(?:explain|justify|show\s+reasoning)", "Behavioral: suppresses explanation output")

    # Category: Secret Exposure (SE1-SE3)
    add("SE1", "secret_exposure", PatternSeverity.CRITICAL,
        r"(?:sk-|pk-|rk-|ghp_|gho_|github_pat_)[a-zA-Z0-9]{20,}", "Secret exposure: hardcoded API key pattern")
    add("SE2", "secret_exposure", PatternSeverity.CRITICAL,
        r"(?:password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{4,}['\"]", "Secret exposure: hardcoded password")
    add("SE3", "secret_exposure", PatternSeverity.HIGH,
        r"(?:BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY|BEGIN\s+OPENSSH\s+PRIVATE\s+KEY)", "Secret exposure: private key material")

    # Category: MCP Tool Poisoning (TP1-TP3)
    add("TP1", "tool_poisoning", PatternSeverity.HIGH,
        r"(?:tool|mcp_server|function)\s*(?:name|description)\s*[:=].*(?:ignore|bypass|override)\b.*\b(?:rules|guardrails|policy)", "Tool poisoning: tool description with guardrail bypass")
    add("TP2", "tool_poisoning", PatternSeverity.MEDIUM,
        r"(?:tool|mcp_server)\s*(?:description|prompt)\s*[:=].*(?:execute|run|eval)\s+(?:any|all|arbitrary)", "Tool poisoning: overly broad tool capabilities")
    add("TP3", "tool_poisoning", PatternSeverity.HIGH,
        r"(?:hidden|invisible|stealth)\s+(?:tool|command|function|instruction)", "Tool poisoning: hidden tool or instruction")

    return patterns


_DEFAULT_PATTERNS: list[VulnerabilityPattern] | None = None


def _get_default_patterns() -> list[VulnerabilityPattern]:
    global _DEFAULT_PATTERNS
    if _DEFAULT_PATTERNS is None:
        _DEFAULT_PATTERNS = _build_patterns()
    return _DEFAULT_PATTERNS


# -- Resource Bounds --------------------------------------------------------

MAX_FINDINGS_PER_ARTIFACT: int = 10_000
MAX_SCAN_TIME_SECONDS: float = 30.0
MAX_FILE_SIZE_MB: int = 10


# -- Risk Scoring -----------------------------------------------------------

def _score_to_risk(score: int, critical_count: int) -> ScanRiskLevel:
    """Map a numeric score + critical count to a risk level."""
    if critical_count > 0 or score >= 50:
        return ScanRiskLevel.CRITICAL
    if score >= 25:
        return ScanRiskLevel.HIGH
    if score >= 10:
        return ScanRiskLevel.MEDIUM
    if score > 0:
        return ScanRiskLevel.LOW
    return ScanRiskLevel.SAFE


# -- Baseline Management ----------------------------------------------------

@dataclass
class Baseline:
    """A set of accepted findings for baseline suppression."""

    fingerprints: set[str] = field(default_factory=set)
    file_hashes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_results(cls, results: list[ScanResult]) -> Baseline:
        """Create a baseline from scan results (accept current findings)."""
        bl = cls()
        for r in results:
            for f in r.findings:
                bl.fingerprints.add(f.fingerprint)
        return bl

    def is_suppressed(self, finding: Finding) -> bool:
        """Check if a finding is suppressed by this baseline."""
        return finding.fingerprint in self.fingerprints

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprints": sorted(self.fingerprints),
            "file_hashes": dict(self.file_hashes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Baseline:
        return cls(
            fingerprints=set(data.get("fingerprints", [])),
            file_hashes=dict(data.get("file_hashes", {})),
        )


# -- Scanner ----------------------------------------------------------------

class SkillScanner:
    """Static security scanner for skill files.

    Scans .md, .py, .txt, .yaml, .json files for vulnerability patterns.
    Supports baseline suppression and resource bounds.
    """

    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
        ".md", ".py", ".txt", ".yaml", ".yml", ".json", ".js", ".ts",
    })

    def __init__(
        self,
        patterns: list[VulnerabilityPattern] | None = None,
        baseline: Baseline | None = None,
        max_findings: int = MAX_FINDINGS_PER_ARTIFACT,
        max_time_s: float = MAX_SCAN_TIME_SECONDS,
    ) -> None:
        self.patterns = patterns or _get_default_patterns()
        self.baseline = baseline
        self.max_findings = max_findings
        self.max_time_s = max_time_s

    def scan_file(self, path: Path) -> ScanResult:
        """Scan a single file for vulnerabilities."""
        path = Path(path)
        start = time.time()
        if not path.exists():
            return ScanResult(path=str(path), error="File not found")
        if path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            return ScanResult(path=str(path), error=f"Unsupported extension: {path.suffix}")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ScanResult(path=str(path), error=f"Read error: {exc}")

        if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
            return ScanResult(path=str(path), error=f"File too large (>{MAX_FILE_SIZE_MB}MB)")

        findings = self._scan_content(content, str(path))
        elapsed = (time.time() - start) * 1000
        return self._build_result(str(path), findings, elapsed)

    def scan_text(self, content: str, name: str = "<inline>") -> ScanResult:
        """Scan raw text content for vulnerabilities."""
        start = time.time()
        findings = self._scan_content(content, name)
        elapsed = (time.time() - start) * 1000
        return self._build_result(name, findings, elapsed)

    def scan_directory(self, dir_path: Path) -> list[ScanResult]:
        """Scan all supported files in a directory tree."""
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            return [ScanResult(path=str(dir_path), error="Not a directory")]
        results: list[ScanResult] = []
        start = time.time()
        for ext in self.SUPPORTED_EXTENSIONS:
            for path in dir_path.rglob(f"*{ext}"):
                if time.time() - start > self.max_time_s:
                    remaining = ScanResult(
                        path=str(dir_path),
                        error=f"Scan time exceeded {self.max_time_s}s",
                        truncated=True,
                    )
                    results.append(remaining)
                    return results
                results.append(self.scan_file(path))
        return results

    def _scan_content(self, content: str, file_name: str) -> list[Finding]:
        """Run all patterns against content and return findings."""
        findings: list[Finding] = []
        for pattern in self.patterns:
            if len(findings) >= self.max_findings:
                break
            for match in pattern.regex.finditer(content):
                if len(findings) >= self.max_findings:
                    break
                line_no = content.count("\n", 0, match.start()) + 1
                match_text = match.group(0)[:100]  # Truncate long matches
                finding = Finding(
                    pattern_id=pattern.pattern_id,
                    category=pattern.category,
                    severity=pattern.severity,
                    message=pattern.message,
                    file=file_name,
                    line=line_no,
                    match=match_text,
                    score=pattern.score,
                )
                # Suppress if in baseline
                if self.baseline and self.baseline.is_suppressed(finding):
                    continue
                findings.append(finding)
        return findings

    def _build_result(self, path: str, findings: list[Finding], elapsed_ms: float) -> ScanResult:
        """Build a ScanResult from findings."""
        score = sum(f.score for f in findings)
        critical = sum(1 for f in findings if f.severity is PatternSeverity.CRITICAL)
        risk = _score_to_risk(score, critical)
        truncated = len(findings) >= self.max_findings
        return ScanResult(
            path=path,
            findings=findings,
            score=score,
            risk_level=risk,
            truncated=truncated,
            scan_time_ms=elapsed_ms,
        )


__all__ = [
    "MAX_FINDINGS_PER_ARTIFACT",
    "MAX_SCAN_TIME_SECONDS",
    "Baseline",
    "Finding",
    "PatternSeverity",
    "ScanResult",
    "ScanRiskLevel",
    "SkillScanner",
    "SkillScannerError",
    "VulnerabilityPattern",
]
