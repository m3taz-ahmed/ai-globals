#!/usr/bin/env python3
"""MCP server and skill security scanner for aiZee.

Scans MCP server configurations, skill files, and plugin definitions
for security risks before installation or activation. Detects:

- Prompt injection in skill instructions
- Data exfiltration patterns (network calls, file uploads)
- Privilege escalation (sudo, chmod, credential access)
- Supply chain risks (unverified URLs, unpinned versions)
- Tool poisoning (hidden instructions in tool metadata)
- Dangerous code execution surfaces
- Over-broad permissions
- Credential theft patterns
- Crypto wallet targeting
- Anti-refusal bypass attempts

Usage::

    from runtime.mcp_security import MCPSecurityScanner
    scanner = MCPSecurityScanner()
    report = scanner.scan_config(Path(".devin/mcp_config.json"))
    if not report.passed:
        print("Security issues found!")
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Detection patterns organized by category ---

# Category 1: Prompt Injection
PROMPT_INJECTION = [
    re.compile(r"ignore\s+(all\s+)?previous\s+(instructions|rules|prompts)", re.IGNORECASE),
    re.compile(r"disregard\s+(the\s+)?above", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(free|unrestricted|jailbroken)", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"<\s*system\s*>.*?<\s*/\s*system\s*>", re.IGNORECASE | re.DOTALL),
    re.compile(r"forget\s+(everything|all\s+rules|all\s+instructions)", re.IGNORECASE),
    re.compile(r"act\s+as\s+if\s+you\s+have\s+no\s+(restrictions|rules|limits)", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"do\s+not\s+refuse", re.IGNORECASE),
    re.compile(r"override\s+(safety|security|content\s+policy)", re.IGNORECASE),
]

# Category 2: Data Exfiltration
DATA_EXFIL = [
    re.compile(r"curl\s+.*\|\s*(bash|sh|python|perl)", re.IGNORECASE),
    re.compile(r"wget\s+.*\|\s*(bash|sh|python|perl)", re.IGNORECASE),
    re.compile(r"upload\s+(to|file|data)\s+(ftp|s3|http|url)", re.IGNORECASE),
    re.compile(r"send\s+(data|file|content)\s+to\s+(http|https|ftp)", re.IGNORECASE),
    re.compile(r"exfiltrate", re.IGNORECASE),
    re.compile(r"post\s+.*\s+to\s+https?://(?!localhost|127\.0\.0\.1)", re.IGNORECASE),
    re.compile(r"webhook\.site|requestbin|ngrok\.io|burpcollaborator", re.IGNORECASE),
]

# Category 3: Privilege Escalation
PRIVILEGE_ESCALATION = [
    re.compile(r"sudo\s+", re.IGNORECASE),
    re.compile(r"chmod\s+[0-7]{3,4}\s+/", re.IGNORECASE),
    re.compile(r"chown\s+", re.IGNORECASE),
    re.compile(r"su\s+root", re.IGNORECASE),
    re.compile(r"/etc/sudoers", re.IGNORECASE),
    re.compile(r"setuid|setgid", re.IGNORECASE),
    re.compile(r"capability\s+CAP_SYS_ADMIN", re.IGNORECASE),
]

# Category 4: Supply Chain
SUPPLY_CHAIN = [
    re.compile(r"pip\s+install\s+(?!.*@|.*==)", re.IGNORECASE),  # unpinned
    re.compile(r"npm\s+install\s+(?!.*@|.*--save-exact)", re.IGNORECASE),  # unpinned
    re.compile(r"npx\s+-y\s+(?!.*@)", re.IGNORECASE),  # unpinned npx
    re.compile(r"uvx\s+(?!.*@|.*==)", re.IGNORECASE),  # unpinned uvx
    re.compile(r"http://(?!localhost|127\.0\.0\.1)", re.IGNORECASE),  # non-HTTPS
    re.compile(r"git\s+clone\s+https://github\.com/[^\s]+/(?!@)", re.IGNORECASE),  # unpinned git
]

# Category 5: Credential Theft
CREDENTIAL_THEFT = [
    re.compile(r"cat\s+/root/\.ssh/", re.IGNORECASE),
    re.compile(r"cat\s+~/\.ssh/", re.IGNORECASE),
    re.compile(r"cat\s+/home/[^/]+/\.ssh/", re.IGNORECASE),
    re.compile(r"\.aws/credentials", re.IGNORECASE),
    re.compile(r"\.env\b", re.IGNORECASE),
    re.compile(r"\.npmrc\b", re.IGNORECASE),
    re.compile(r"\.pypirc\b", re.IGNORECASE),
    re.compile(r"\.git-credentials", re.IGNORECASE),
    re.compile(r"keychain|keychain-db", re.IGNORECASE),
    re.compile(r"browser\s+cookies|chrome\s+cookies|firefox\s+cookies", re.IGNORECASE),
]

# Category 6: Crypto Wallet Targeting
CRYPTO_WALLET = [
    re.compile(r"wallet\.dat", re.IGNORECASE),
    re.compile(r"metamask|phantom|trust\s+wallet", re.IGNORECASE),
    re.compile(r"\.bitcoin/|\.ethereum/|\.solana/", re.IGNORECASE),
    re.compile(r"seed\s+phrase|mnemonic|recovery\s+phrase", re.IGNORECASE),
    re.compile(r"private\s+key.*0x[a-f0-9]{64}", re.IGNORECASE),
]

# Category 7: Dangerous Code Execution
DANGEROUS_EXEC = [
    re.compile(r"\beval\s*\(", re.IGNORECASE),
    re.compile(r"\bexec\s*\(", re.IGNORECASE),
    re.compile(r"os\.system\s*\(", re.IGNORECASE),
    re.compile(r"subprocess\.(call|run|Popen)\s*\(.*shell\s*=\s*True", re.IGNORECASE),
    re.compile(r"pickle\.loads?\s*\(", re.IGNORECASE),
    re.compile(r"marshal\.loads?\s*\(", re.IGNORECASE),
    re.compile(r"yaml\.load\s*\((?!.*Loader=)", re.IGNORECASE),  # unsafe yaml load
    re.compile(r"child_process\.exec\s*\(", re.IGNORECASE),
]

# Category 8: Anti-Refusal Bypass
ANTI_REFUSAL = [
    re.compile(r"do\s+not\s+(say\s+)?(you\s+)?can'?t", re.IGNORECASE),
    re.compile(r"don'?t\s+(say\s+)?(you\s+)?can'?t", re.IGNORECASE),
    re.compile(r"never\s+refuse", re.IGNORECASE),
    re.compile(r"always\s+comply", re.IGNORECASE),
    re.compile(r"no\s+refusals?\s+allowed", re.IGNORECASE),
    re.compile(r"you\s+must\s+(always|comply|do\s+it)", re.IGNORECASE),
]

# Category 9: Tool Poisoning (hidden instructions in tool descriptions)
TOOL_POISONING = [
    re.compile(r"description.*ignore.*rules", re.IGNORECASE | re.DOTALL),
    re.compile(r"description.*exfiltrate.*data", re.IGNORECASE | re.DOTALL),
    re.compile(r"tool.*description.*steal", re.IGNORECASE | re.DOTALL),
    re.compile(r"hidden.*instruction", re.IGNORECASE),
    re.compile(r"secret.*command.*in.*description", re.IGNORECASE),
]

# Category 10: Over-broad Permissions
OVERBROAD_PERMS = [
    re.compile(r"permissions?\s*:\s*\[?\s*['\"]\*['\"]", re.IGNORECASE),
    re.compile(r"access\s*:\s*['\"]all['\"]", re.IGNORECASE),
    re.compile(r"scope\s*:\s*['\"]global['\"]", re.IGNORECASE),
    re.compile(r"allow\s*:\s*['\"]\*['\"]", re.IGNORECASE),
]

ALL_CATEGORIES = {
    "prompt_injection": PROMPT_INJECTION,
    "data_exfiltration": DATA_EXFIL,
    "privilege_escalation": PRIVILEGE_ESCALATION,
    "supply_chain": SUPPLY_CHAIN,
    "credential_theft": CREDENTIAL_THEFT,
    "crypto_wallet": CRYPTO_WALLET,
    "dangerous_exec": DANGEROUS_EXEC,
    "anti_refusal": ANTI_REFUSAL,
    "tool_poisoning": TOOL_POISONING,
    "overbroad_permissions": OVERBROAD_PERMS,
}

# Severity mapping per category
CATEGORY_SEVERITY: dict[str, str] = {
    "prompt_injection": "critical",
    "data_exfiltration": "critical",
    "privilege_escalation": "high",
    "supply_chain": "high",
    "credential_theft": "critical",
    "crypto_wallet": "critical",
    "dangerous_exec": "high",
    "anti_refusal": "medium",
    "tool_poisoning": "critical",
    "overbroad_permissions": "medium",
}


@dataclass
class MCPFinding:
    """A security finding from MCP/skill scanning."""

    category: str
    severity: str
    pattern: str
    matched_text: str
    source: str  # file path or server name
    line: int | None = None
    remediation: str = ""


@dataclass
class MCPScanReport:
    """Aggregated MCP security scan report."""

    findings: list[MCPFinding] = field(default_factory=list)
    servers_scanned: int = 0
    skills_scanned: int = 0
    files_scanned: int = 0

    @property
    def passed(self) -> bool:
        """True if no critical or high findings."""
        return not any(f.severity in ("critical", "high") for f in self.findings)

    @property
    def risk_score(self) -> int:
        """Risk score 0-100 (100 = maximum risk)."""
        if not self.findings:
            return 0
        weights = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}
        total = sum(weights.get(f.severity, 0) for f in self.findings)
        return min(100, total)

    def summary(self) -> dict[str, Any]:
        """Return summary dict."""
        by_category: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for f in self.findings:
            by_category[f.category] = by_category.get(f.category, 0) + 1
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        return {
            "passed": self.passed,
            "risk_score": self.risk_score,
            "servers_scanned": self.servers_scanned,
            "skills_scanned": self.skills_scanned,
            "files_scanned": self.files_scanned,
            "total_findings": len(self.findings),
            "by_category": by_category,
            "by_severity": by_severity,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "pattern": f.pattern,
                    "matched_text": f.matched_text[:200],
                    "source": f.source,
                    "line": f.line,
                    "remediation": f.remediation,
                }
                for f in self.findings
            ],
        }


class MCPSecurityScanner:
    """Scanner for MCP servers, skills, and plugin definitions."""

    def __init__(self) -> None:
        self._findings: list[MCPFinding] = []

    def _scan_text(
        self,
        text: str,
        source: str,
    ) -> list[MCPFinding]:
        """Scan text against all pattern categories."""
        findings: list[MCPFinding] = []
        lines = text.split("\n")
        for line_num, line in enumerate(lines, 1):
            for category, patterns in ALL_CATEGORIES.items():
                for pattern in patterns:
                    match = pattern.search(line)
                    if match:
                        findings.append(MCPFinding(
                            category=category,
                            severity=CATEGORY_SEVERITY.get(category, "medium"),
                            pattern=pattern.pattern,
                            matched_text=match.group(0),
                            source=source,
                            line=line_num,
                            remediation=self._remediation_for(category),
                        ))
        return findings

    @staticmethod
    def _remediation_for(category: str) -> str:
        """Get remediation advice for a category."""
        remediations = {
            "prompt_injection": "Sanitize all inputs. Use structured prompts with delimiters. Reject instructions embedded in data.",
            "data_exfiltration": "Block outbound network access from MCP servers. Use allowlists for external URLs.",
            "privilege_escalation": "Run MCP servers with minimal privileges. Never allow sudo or chmod from agent context.",
            "supply_chain": "Pin all package versions with @<sha> or ==<version>. Verify checksums. Use HTTPS only.",
            "credential_theft": "Never allow file reads of ~/.ssh, ~/.aws, .env, or browser cookies from MCP servers.",
            "crypto_wallet": "Block access to wallet files and seed phrases. Flag any crypto-related file access.",
            "dangerous_exec": "Never eval/exec agent output. Use safe deserialization. Avoid shell=True.",
            "anti_refusal": "Do not include anti-refusal instructions in skills. Let the agent refuse unsafe requests.",
            "tool_poisoning": "Audit tool descriptions for hidden instructions. Verify tool metadata integrity.",
            "overbroad_permissions": "Use least-privilege permissions. Replace '*' with specific allowed actions.",
        }
        return remediations.get(category, "Review and remediate the identified security issue.")

    def scan_config(self, config_path: Path) -> MCPScanReport:
        """Scan an MCP server configuration file."""
        report = MCPScanReport()
        if not config_path.exists():
            return report
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return report
        servers = data.get("mcpServers", data.get("servers", {}))
        if not isinstance(servers, dict):
            return report
        for name, config in servers.items():
            if not isinstance(config, dict):
                continue
            report.servers_scanned += 1
            config_text = json.dumps(config)
            findings = self._scan_text(config_text, f"mcp:{name}")
            report.findings.extend(findings)
        return report

    def scan_skill_file(self, skill_path: Path) -> MCPScanReport:
        """Scan a single skill file (SKILL.md or similar)."""
        report = MCPScanReport()
        if not skill_path.exists() or not skill_path.is_file():
            return report
        report.skills_scanned = 1
        report.files_scanned = 1
        text = skill_path.read_text(encoding="utf-8", errors="replace")
        findings = self._scan_text(text, str(skill_path))
        report.findings.extend(findings)
        return report

    def scan_skills_directory(self, skills_dir: Path) -> MCPScanReport:
        """Scan all skill files in a directory tree."""
        report = MCPScanReport()
        if not skills_dir.exists() or not skills_dir.is_dir():
            return report
        for skill_file in skills_dir.rglob("*.md"):
            # Skip non-skill markdown files
            if skill_file.name not in ("SKILL.md", "README.md") and not skill_file.name.endswith(".md"):
                continue
            report.files_scanned += 1
            text = skill_file.read_text(encoding="utf-8", errors="replace")
            findings = self._scan_text(text, str(skill_file))
            if findings:
                report.skills_scanned += 1
            report.findings.extend(findings)
        return report

    def scan_all(self, root: Path) -> MCPScanReport:
        """Scan all MCP configs and skills in a project root."""
        report = MCPScanReport()
        # Scan MCP configs
        for config_name in (".devin/mcp_config.json", ".claude/settings.json", ".cursor/mcp.json"):
            config_path = root / config_name
            if config_path.exists():
                sub = self.scan_config(config_path)
                report.servers_scanned += sub.servers_scanned
                report.findings.extend(sub.findings)
                report.files_scanned += 1
        # Scan skills
        skills_dir = root / "skills"
        if skills_dir.exists():
            sub = self.scan_skills_directory(skills_dir)
            report.skills_scanned += sub.skills_scanned
            report.files_scanned += sub.files_scanned
            report.findings.extend(sub.findings)
        return report


def scan_before_install(target: Path | str) -> MCPScanReport:
    """Scan a target (file, directory, or URL string) before installation.

    This is the main entry point for the ``aizee mcp install`` security gate.
    """
    scanner = MCPSecurityScanner()
    target_path = Path(target)
    if target_path.is_dir():
        return scanner.scan_all(target_path)
    if target_path.is_file():
        if target_path.suffix == ".json":
            return scanner.scan_config(target_path)
        return scanner.scan_skill_file(target_path)
    # Treat as raw text (e.g., a URL or pasted config)
    report = MCPScanReport()
    findings = scanner._scan_text(str(target), "input")
    report.findings.extend(findings)
    return report


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    report = scan_before_install(target)
    print(json.dumps(report.summary(), indent=2))
    sys.exit(0 if report.passed else 1)
