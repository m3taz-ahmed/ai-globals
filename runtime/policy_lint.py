#!/usr/bin/env python3
"""Static analysis over policy rule sets (inspired by mcpkernel).

Detects common policy authoring mistakes that can lead to security gaps
or unreachable rules. Runs 7 checks (PL001-PL007) over a rule list.

Usage::

    from runtime.policy_lint import PolicyLinter
    linter = PolicyLinter()
    findings = linter.lint(rules)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

_logger = logging.getLogger(__name__)


class LintSeverity(str, Enum):
    """Severity of a policy lint finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class LintFinding:
    """A single policy lint finding."""

    rule_id: str
    severity: LintSeverity
    message: str
    rule_name: str
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "rule_name": self.rule_name,
            "fix": self.fix,
        }


# ReDoS pattern: nested quantifiers like (a+)+, (a*)*, (a+)*, (a*)+
_REDOS_RE = re.compile(r"\([^)]*[+*?][^)]*\)[+*]")


class PolicyLinter:
    """Static analysis over policy rule sets.

    Detects common policy authoring mistakes:
    - PL001: duplicate rule names
    - PL002: unmatchable conditions
    - PL003: ReDoS-vulnerable regex patterns
    - PL004: shadowed deny rules
    - PL005: missing OWASP mapping metadata
    - PL006: unreachable rules after catch-all
    - PL007: empty or always-true conditions
    """

    def lint(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """Run all checks over a list of policy rules.

        Args:
            rules: List of rule dicts, each with at least ``name`` and
                ``condition`` keys, optionally ``action`` and ``owasp``.

        Returns:
            List of findings sorted by severity (errors first).
        """
        findings: list[LintFinding] = []
        findings.extend(self._check_duplicate_ids(rules))
        findings.extend(self._check_unmatchable(rules))
        findings.extend(self._check_redos(rules))
        findings.extend(self._check_shadowed_denies(rules))
        findings.extend(self._check_missing_owasp(rules))
        findings.extend(self._check_unreachable(rules))
        findings.extend(self._check_empty_conditions(rules))
        # Sort: errors first, then warnings, then info
        severity_order = {LintSeverity.ERROR: 0, LintSeverity.WARNING: 1, LintSeverity.INFO: 2}
        findings.sort(key=lambda f: severity_order.get(f.severity, 3))
        return findings

    def _check_duplicate_ids(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL001: duplicate rule names."""
        findings: list[LintFinding] = []
        seen: dict[str, int] = {}
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            if name in seen:
                findings.append(LintFinding(
                    rule_id="PL001",
                    severity=LintSeverity.ERROR,
                    message=f"Duplicate rule name '{name}' (first at index {seen[name]})",
                    rule_name=name,
                    fix="Rename one of the duplicate rules to be unique",
                ))
            else:
                seen[name] = i
        return findings

    def _check_unmatchable(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL002: conditions that can never match.

        Detects contradictions like ``action.type == 'read' and action.type == 'write'``.
        """
        findings: list[LintFinding] = []
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            condition = rule.get("condition", "")
            if not condition:
                continue
            # Check for same field with different values (X == A and X == B)
            eq_pairs = re.findall(r"(\w+(?:\.\w+)*)\s*==\s*['\"]?(\w+)['\"]?", condition)
            field_values: dict[str, set[str]] = {}
            for field, value in eq_pairs:
                field_values.setdefault(field, set()).add(value)
            for field, values in field_values.items():
                if len(values) > 1:
                    findings.append(LintFinding(
                        rule_id="PL002",
                        severity=LintSeverity.ERROR,
                        message=f"Condition for '{field}' requires contradictory values: {values}",
                        rule_name=name,
                        fix=f"Remove the contradiction on '{field}' — it can never match",
                    ))
        return findings

    def _check_redos(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL003: regex patterns vulnerable to ReDoS."""
        findings: list[LintFinding] = []
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            condition = rule.get("condition", "")
            if not condition:
                continue
            # Extract regex patterns from matches_pattern / regex conditions
            regex_patterns = re.findall(r"matches_pattern\s*:\s*['\"](.+?)['\"]", condition)
            regex_patterns.extend(re.findall(r"regex\s*:\s*['\"](.+?)['\"]", condition))
            for pattern in regex_patterns:
                if _REDOS_RE.search(pattern):
                    findings.append(LintFinding(
                        rule_id="PL003",
                        severity=LintSeverity.WARNING,
                        message=f"Regex pattern '{pattern}' may be vulnerable to ReDoS (nested quantifiers)",
                        rule_name=name,
                        fix="Simplify the regex to avoid nested quantifiers like (a+)+",
                    ))
        return findings

    def _check_shadowed_denies(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL004: a deny rule that comes after an allow for the same condition."""
        findings: list[LintFinding] = []
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            action = rule.get("action", "")
            condition = rule.get("condition", "")
            if action != "deny" or not condition:
                continue
            # Check if any earlier allow rule has the same or broader condition
            for j in range(i):
                prev = rules[j]
                if prev.get("action") == "allow" and prev.get("condition") == condition:
                    findings.append(LintFinding(
                        rule_id="PL004",
                        severity=LintSeverity.ERROR,
                        message=f"Deny rule '{name}' is shadowed by earlier allow rule '{prev.get('name', f'rule_{j}')}' with the same condition",
                        rule_name=name,
                        fix="Move the deny rule before the allow rule, or remove the duplicate",
                    ))
                    break
        return findings

    def _check_missing_owasp(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL005: rules without OWASP mapping metadata."""
        findings: list[LintFinding] = []
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            owasp = rule.get("owasp") or rule.get("owasp_mapping") or rule.get("metadata", {}).get("owasp")
            if not owasp:
                findings.append(LintFinding(
                    rule_id="PL005",
                    severity=LintSeverity.INFO,
                    message=f"Rule '{name}' has no OWASP mapping metadata",
                    rule_name=name,
                    fix="Add an 'owasp' field mapping the rule to an OWASP LLM Top-10 category",
                ))
        return findings

    def _check_unreachable(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL006: rules after a catch-all that can never be reached."""
        findings: list[LintFinding] = []
        catch_all_index: int | None = None
        catch_all_name = ""
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            condition = rule.get("condition", "")
            # A catch-all is a rule with an always-true or empty condition
            is_catch_all = (
                not condition
                or condition.strip() in ("true", "True", "1", "*")
                or condition.strip() == "default"
            )
            if is_catch_all and catch_all_index is None:
                catch_all_index = i
                catch_all_name = name
            elif catch_all_index is not None and not is_catch_all:
                findings.append(LintFinding(
                    rule_id="PL006",
                    severity=LintSeverity.WARNING,
                    message=f"Rule '{name}' is unreachable (after catch-all '{catch_all_name}' at index {catch_all_index})",
                    rule_name=name,
                    fix="Move this rule before the catch-all, or remove it",
                ))
        return findings

    def _check_empty_conditions(self, rules: list[dict[str, Any]]) -> list[LintFinding]:
        """PL007: rules with empty or always-true conditions."""
        findings: list[LintFinding] = []
        for i, rule in enumerate(rules):
            name = rule.get("name", f"rule_{i}")
            condition = rule.get("condition", "")
            if not condition or condition.strip() in ("true", "True", "1"):
                findings.append(LintFinding(
                    rule_id="PL007",
                    severity=LintSeverity.INFO,
                    message=f"Rule '{name}' has an empty or always-true condition",
                    rule_name=name,
                    fix="Add a specific condition or document that this is intentionally a catch-all",
                ))
        return findings
