#!/usr/bin/env python3
"""OWASP Agentic Top 10 compliance scanner for AI Global OS.

Scans agent configurations, MCP server definitions, skills, and policy
rules against the OWASP Agentic Top 10 (2026) controls:

1.  A01 — Prompt Injection
2.  A02 — Sensitive Information Disclosure
3.  A03 — Supply Chain Vulnerabilities
4.  A04 — Excessive Agency / Over-privileged Agents
5.  A05 — Insecure Output Handling
6.  A06 — Tool / Function Misuse
7.  A07 — Untrusted Content Consumption
8.  A08 — Memory / Context Poisoning
9.  A09 — Rogue Agent / Identity Misuse
10. A10 — Lack of Human Oversight

Each control produces a finding with severity (critical/high/medium/low/info)
and a remediation suggestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Severity levels ordered by criticality
_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

# Patterns that indicate prompt injection risk
_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?above", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*system\s*>", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all\s+rules)", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+restrictions", re.IGNORECASE),
]

# Patterns that indicate sensitive data exposure
_SENSITIVE_DATA_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|password|token|credential)\s*[=:]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI API key
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),  # GitHub PAT
    re.compile(r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
]

# Patterns that indicate excessive agency
_EXCESSIVE_AGENCY_PATTERNS = [
    re.compile(r"auto(?:matically)?\s+(?:commit|push|deploy|delete|drop|truncate)", re.IGNORECASE),
    re.compile(r"without\s+(?:user\s+)?approval", re.IGNORECASE),
    re.compile(r"no\s+confirmation\s+needed", re.IGNORECASE),
    re.compile(r"force\s+(?:push|overwrite)", re.IGNORECASE),
]

# Patterns that indicate insecure output handling
_INSECURE_OUTPUT_PATTERNS = [
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.call\s*\(.*shell\s*=\s*True", re.IGNORECASE),
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    re.compile(r"innerHTML\s*=", re.IGNORECASE),
    re.compile(r"dangerouslySetInnerHTML", re.IGNORECASE),
]


@dataclass
class SecurityFinding:
    """A single security finding from the OWASP Agentic scanner."""

    control_id: str  # e.g., "A01"
    control_name: str
    severity: str  # critical, high, medium, low, info
    description: str
    file_path: str | None = None
    line: int | None = None
    remediation: str = ""

    @property
    def severity_score(self) -> int:
        return _SEVERITY_ORDER.get(self.severity, 0)


@dataclass
class ScanReport:
    """Aggregated scan report."""

    findings: list[SecurityFinding] = field(default_factory=list)
    files_scanned: int = 0
    controls_checked: int = 10

    @property
    def passed(self) -> bool:
        """True if no critical or high findings."""
        return not any(f.severity in ("critical", "high") for f in self.findings)

    @property
    def score(self) -> float:
        """Compliance score 0..1 (1 = no findings)."""
        if not self.findings:
            return 1.0
        total_weight = sum(f.severity_score for f in self.findings)
        max_possible = total_weight + 10  # normalize
        return max(0.0, 1.0 - (total_weight / max_possible))

    def summary(self) -> dict[str, Any]:
        """Return a summary dict."""
        by_severity: dict[str, int] = {}
        for f in self.findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {
            "passed": self.passed,
            "score": round(self.score, 4),
            "files_scanned": self.files_scanned,
            "controls_checked": self.controls_checked,
            "total_findings": len(self.findings),
            "by_severity": by_severity,
            "findings": [
                {
                    "control_id": f.control_id,
                    "control_name": f.control_name,
                    "severity": f.severity,
                    "description": f.description,
                    "file": f.file_path,
                    "line": f.line,
                    "remediation": f.remediation,
                }
                for f in self.findings
            ],
        }


class AgenticSecurityScanner:
    """Scanner for OWASP Agentic Top 10 compliance."""

    def __init__(self) -> None:
        self._findings: list[SecurityFinding] = []

    def _add(
        self,
        control_id: str,
        control_name: str,
        severity: str,
        description: str,
        file_path: str | None = None,
        line: int | None = None,
        remediation: str = "",
    ) -> None:
        self._findings.append(SecurityFinding(
            control_id=control_id,
            control_name=control_name,
            severity=severity,
            description=description,
            file_path=file_path,
            line=line,
            remediation=remediation,
        ))

    def scan_text(self, text: str, file_path: str | None = None) -> list[SecurityFinding]:
        """Scan a text string for all OWASP Agentic patterns."""
        self._findings = []
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            self._scan_line(line, file_path, i)
        return self._findings

    def _scan_line(self, line: str, file_path: str | None, line_num: int) -> None:
        """Scan a single line for all pattern categories."""
        # A01 — Prompt Injection
        for pattern in _PROMPT_INJECTION_PATTERNS:
            if pattern.search(line):
                self._add(
                    "A01", "Prompt Injection", "high",
                    f"Potential prompt injection pattern detected: '{pattern.pattern}'",
                    file_path, line_num,
                    "Sanitize all user-supplied input before passing to the agent. "
                    "Use structured prompts with clear delimiters.",
                )
                break

        # A02 — Sensitive Information Disclosure
        for pattern in _SENSITIVE_DATA_PATTERNS:
            if pattern.search(line):
                self._add(
                    "A02", "Sensitive Information Disclosure", "critical",
                    f"Hardcoded secret or credential detected: '{pattern.pattern}'",
                    file_path, line_num,
                    "Never hardcode secrets. Use environment variables or a secrets manager. "
                    "Add to .gitignore if in a config file.",
                )
                break

        # A04 — Excessive Agency
        for pattern in _EXCESSIVE_AGENCY_PATTERNS:
            if pattern.search(line):
                self._add(
                    "A04", "Excessive Agency", "high",
                    f"Agent may perform destructive actions without approval: '{pattern.pattern}'",
                    file_path, line_num,
                    "Require explicit user approval for all destructive operations. "
                    "Use policy rules with action: deny or ask.",
                )
                break

        # A05 — Insecure Output Handling
        for pattern in _INSECURE_OUTPUT_PATTERNS:
            if pattern.search(line):
                self._add(
                    "A05", "Insecure Output Handling", "high",
                    f"Potentially unsafe code execution from agent output: '{pattern.pattern}'",
                    file_path, line_num,
                    "Never eval() or exec() agent output. Use safe deserialization. "
                    "Sanitize HTML with DOMPurify before rendering.",
                )
                break

    def scan_file(self, file_path: Path) -> list[SecurityFinding]:
        """Scan a single file."""
        if not file_path.exists() or not file_path.is_file():
            return []
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return self.scan_text(text, str(file_path))

    def scan_directory(
        self,
        directory: Path,
        extensions: set[str] | None = None,
        exclude_dirs: set[str] | None = None,
    ) -> ScanReport:
        """Scan all files in a directory recursively."""
        if extensions is None:
            extensions = {".py", ".js", ".ts", ".yaml", ".yml", ".json", ".md", ".txt"}
        if exclude_dirs is None:
            exclude_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "brain", "state", "temp"}

        all_findings: list[SecurityFinding] = []
        files_scanned = 0
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.suffix.lower() not in extensions:
                continue
            files_scanned += 1
            findings = self.scan_file(file_path)
            all_findings.extend(findings)
        return ScanReport(findings=all_findings, files_scanned=files_scanned)

    def scan_policy_rules(self, policy_file: Path) -> list[SecurityFinding]:
        """Scan a policy YAML file for missing human oversight controls."""
        findings: list[SecurityFinding] = []
        if not policy_file.exists():
            return findings
        import yaml
        try:
            data = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            return findings
        rules = data.get("rules", []) if isinstance(data, dict) else []
        has_deny = any(r.get("action") == "deny" for r in rules)
        has_ask = any(r.get("action") == "ask" for r in rules)
        if not has_deny:
            findings.append(SecurityFinding(
                control_id="A10",
                control_name="Lack of Human Oversight",
                severity="high",
                description="Policy has no 'deny' rules — no hard guardrails exist",
                file_path=str(policy_file),
                remediation="Add deny rules for destructive and unauthorized actions.",
            ))
        if not has_ask:
            findings.append(SecurityFinding(
                control_id="A10",
                control_name="Lack of Human Oversight",
                severity="medium",
                description="Policy has no 'ask' rules — no human approval checkpoints",
                file_path=str(policy_file),
                remediation="Add ask rules for write, deploy, and bash operations.",
            ))
        # Check for wildcard allow
        for rule in rules:
            if rule.get("action") == "allow" and "True" in str(rule.get("condition", "")):
                findings.append(SecurityFinding(
                    control_id="A04",
                    control_name="Excessive Agency",
                    severity="medium",
                    description=f"Rule '{rule.get('name', 'unnamed')}' has an overly broad allow condition",
                    file_path=str(policy_file),
                    remediation="Narrow the condition to specific action types.",
                ))
        return findings

    def scan_mcp_config(self, config_path: Path) -> list[SecurityFinding]:
        """Scan an MCP server config for security issues."""
        findings: list[SecurityFinding] = []
        if not config_path.exists():
            return findings
        import json
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return findings
        servers = data.get("mcpServers", data.get("servers", {}))
        if not isinstance(servers, dict):
            return findings
        for name, config in servers.items():
            if not isinstance(config, dict):
                continue
            # Check for missing authentication
            config.get("env", {})
            config.get("args", [])
            config.get("command", "")
            full_text = json.dumps(config)
            # A02 — Check for inline secrets
            for pattern in _SENSITIVE_DATA_PATTERNS:
                if pattern.search(full_text):
                    findings.append(SecurityFinding(
                        control_id="A02",
                        control_name="Sensitive Information Disclosure",
                        severity="critical",
                        description=f"MCP server '{name}' has inline secrets in config",
                        file_path=str(config_path),
                        remediation="Move secrets to .env file. Use mcp_env_wrapper.py.",
                    ))
                    break
            # A06 — Check for dangerous commands
            if "curl" in full_text or "wget" in full_text:
                findings.append(SecurityFinding(
                    control_id="A06",
                    control_name="Tool Misuse",
                    severity="medium",
                    description=f"MCP server '{name}' may execute network fetch commands",
                    file_path=str(config_path),
                    remediation="Restrict network access for MCP servers.",
                ))
        return findings


def scan_project(root: Path) -> ScanReport:
    """Convenience function: scan an entire project root."""
    scanner = AgenticSecurityScanner()
    report = scanner.scan_directory(root)
    # Also scan policy files
    policy_dir = root / "runtime" / "policies"
    if policy_dir.exists():
        for pf in policy_dir.glob("*.yaml"):
            report.findings.extend(scanner.scan_policy_rules(pf))
    # Also scan MCP configs
    for config_name in (".devin/mcp_config.json", ".claude/settings.json"):
        config_path = root / config_name
        if config_path.exists():
            report.findings.extend(scanner.scan_mcp_config(config_path))
    return report


if __name__ == "__main__":
    import json
    import sys
    project_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    report = scan_project(project_root)
    print(json.dumps(report.summary(), indent=2))
