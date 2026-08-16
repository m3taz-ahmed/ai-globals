#!/usr/bin/env python3
"""Spec constitution validation and test scenarios (from spec-kit).

Constitution: Project governing principles that specs must comply with.
Test Scenarios: Gherkin-style acceptance criteria linked to requirements.
Linkage Graph: Track dependencies between specs, requirements, and code.

Usage::

    from runtime.spec_validation import ConstitutionValidator, TestScenario

    validator = ConstitutionValidator()
    violations = validator.validate(spec, constitution)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConstitutionRule:
    """A single constitution rule."""

    id: str
    description: str
    pattern: re.Pattern[str] | None = None
    forbidden_pattern: re.Pattern[str] | None = None


@dataclass
class ConstitutionValidator:
    """Validate specs against project constitution (from spec-kit).

    The constitution is a set of governing principles that all specs
    must comply with. Violations are reported as errors.
    """

    rules: list[ConstitutionRule] = field(default_factory=list)

    def add_rule(
        self,
        rule_id: str,
        description: str,
        *,
        pattern: str | None = None,
        forbidden: str | None = None,
    ) -> ConstitutionRule:
        """Add a constitution rule."""
        rule = ConstitutionRule(
            id=rule_id,
            description=description,
            pattern=re.compile(pattern) if pattern else None,
            forbidden_pattern=re.compile(forbidden) if forbidden else None,
        )
        self.rules.append(rule)
        return rule

    def validate(self, spec_content: str) -> list[str]:
        """Validate spec content against constitution rules.

        Returns list of violation messages (empty = compliant).
        """
        violations: list[str] = []
        for rule in self.rules:
            if rule.forbidden_pattern and rule.forbidden_pattern.search(spec_content):
                violations.append(f"[{rule.id}] Forbidden pattern: {rule.description}")
            if rule.pattern and not rule.pattern.search(spec_content):
                violations.append(f"[{rule.id}] Missing required: {rule.description}")
        return violations

    def validate_requirements(
        self,
        requirements: list[dict[str, Any]],
    ) -> list[str]:
        """Validate that requirements comply with constitution."""
        violations: list[str] = []
        for req in requirements:
            desc = req.get("description", "")
            for rule in self.rules:
                if rule.forbidden_pattern and rule.forbidden_pattern.search(desc):
                    violations.append(
                        f"[{rule.id}] {req.get('id', '?')}: {rule.description}"
                    )
        return violations


@dataclass
class TestScenario:
    """Gherkin-style acceptance criteria (from spec-kit).

    Linked to requirements via requirement_id.
    """

    id: str
    requirement_id: str
    name: str
    given: str = ""
    when: str = ""
    then: str = ""
    and_conditions: list[str] = field(default_factory=list)

    def to_gherkin(self) -> str:
        """Convert to Gherkin format."""
        lines = [f"Scenario: {self.name}"]
        if self.given:
            lines.append(f"  Given {self.given}")
        for cond in self.and_conditions:
            lines.append(f"    And {cond}")
        if self.when:
            lines.append(f"  When {self.when}")
        if self.then:
            lines.append(f"  Then {self.then}")
        return "\n".join(lines)


@dataclass
class ScenarioBuilder:
    """Build test scenarios for spec requirements."""

    _scenarios: list[TestScenario] = field(default_factory=list)

    def add_scenario(
        self,
        requirement_id: str,
        name: str,
        *,
        given: str = "",
        when: str = "",
        then: str = "",
        and_conditions: list[str] | None = None,
    ) -> TestScenario:
        """Add a test scenario for a requirement."""
        scenario = TestScenario(
            id=f"SCN-{len(self._scenarios) + 1:03d}",
            requirement_id=requirement_id,
            name=name,
            given=given,
            when=when,
            then=then,
            and_conditions=and_conditions or [],
        )
        self._scenarios.append(scenario)
        return scenario

    def for_requirement(self, requirement_id: str) -> list[TestScenario]:
        """Get all scenarios for a requirement."""
        return [s for s in self._scenarios if s.requirement_id == requirement_id]

    def all_scenarios(self) -> list[TestScenario]:
        return list(self._scenarios)

    def to_gherkin_feature(self, feature_name: str) -> str:
        """Convert all scenarios to a Gherkin feature file."""
        lines = [f"Feature: {feature_name}", ""]
        for s in self._scenarios:
            lines.append(s.to_gherkin())
            lines.append("")
        return "\n".join(lines)


@dataclass
class SpecLink:
    """A link between specs, requirements, and code artifacts."""

    source_type: str  # spec, requirement, code
    source_id: str
    target_type: str
    target_id: str
    link_type: str  # implements, depends_on, tests, references


@dataclass
class SpecLinkageGraph:
    """Track dependencies between specs, requirements, and code (from spec-kit).

    Enables impact analysis: "If requirement X changes, which specs
    and code files are affected?"
    """

    _links: list[SpecLink] = field(default_factory=list)

    def add_link(
        self,
        source_type: str,
        source_id: str,
        target_type: str,
        target_id: str,
        link_type: str,
    ) -> SpecLink:
        """Add a linkage between two artifacts."""
        link = SpecLink(
            source_type=source_type, source_id=source_id,
            target_type=target_type, target_id=target_id,
            link_type=link_type,
        )
        self._links.append(link)
        return link

    def impact_analysis(
        self,
        artifact_type: str,
        artifact_id: str,
    ) -> list[SpecLink]:
        """Find all artifacts affected by a change to the given artifact."""
        affected: list[SpecLink] = []
        visited: set[str] = set()
        self._traverse(artifact_type, artifact_id, affected, visited)
        return affected

    def _traverse(
        self,
        artifact_type: str,
        artifact_id: str,
        affected: list[SpecLink],
        visited: set[str],
    ) -> None:
        key = f"{artifact_type}:{artifact_id}"
        if key in visited:
            return
        visited.add(key)
        for link in self._links:
            if link.source_type == artifact_type and link.source_id == artifact_id:
                affected.append(link)
                self._traverse(link.target_type, link.target_id, affected, visited)

    def links_from(self, source_id: str) -> list[SpecLink]:
        """Get all links originating from a source."""
        return [link for link in self._links if link.source_id == source_id]

    def links_to(self, target_id: str) -> list[SpecLink]:
        """Get all links pointing to a target."""
        return [link for link in self._links if link.target_id == target_id]


if __name__ == "__main__":
    validator = ConstitutionValidator()
    validator.add_rule("SEC-01", "No hardcoded secrets", forbidden=r"password\s*=\s*['\"]")
    violations = validator.validate("password = 'secret123'")
    print(f"Violations: {violations}")
