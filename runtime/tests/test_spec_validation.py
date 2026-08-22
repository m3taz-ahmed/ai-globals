"""Tests for runtime/spec_validation.py."""

from __future__ import annotations

from runtime.spec_validation import (
    ConstitutionRule,
    ConstitutionValidator,
    ScenarioBuilder,
    SpecLinkageGraph,
    TestScenario,
)


class TestConstitutionRule:
    def test_rule_defaults_patterns_to_none(self) -> None:
        # Arrange & Act
        rule = ConstitutionRule(id="R1", description="Test rule")

        # Assert
        assert rule.pattern is None
        assert rule.forbidden_pattern is None

    def test_rule_stores_id_and_description(self) -> None:
        # Arrange & Act
        rule = ConstitutionRule(id="SEC-01", description="No secrets")

        # Assert
        assert rule.id == "SEC-01"
        assert rule.description == "No secrets"


class TestConstitutionValidatorAddRule:
    def test_add_rule_appends_to_rules_list(self) -> None:
        # Arrange
        validator = ConstitutionValidator()

        # Act
        rule = validator.add_rule("R1", "Test rule")

        # Assert
        assert len(validator.rules) == 1
        assert validator.rules[0] is rule

    def test_add_rule_with_pattern_compiles_regex(self) -> None:
        # Arrange
        validator = ConstitutionValidator()

        # Act
        rule = validator.add_rule("R1", "Must have X", pattern="X")

        # Assert
        assert rule.pattern is not None
        assert rule.pattern.search("X") is not None

    def test_add_rule_with_forbidden_compiles_regex(self) -> None:
        # Arrange
        validator = ConstitutionValidator()

        # Act
        rule = validator.add_rule("R1", "No secrets", forbidden=r"password\s*=")

        # Assert
        assert rule.forbidden_pattern is not None
        assert rule.forbidden_pattern.search("password = 'x'") is not None


class TestConstitutionValidatorValidate:
    def test_validate_no_violations_for_compliant_spec(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("REQ-01", "Must have acceptance criteria", pattern="acceptance")

        # Act
        violations = validator.validate("This spec has acceptance criteria defined.")

        # Assert
        assert violations == []

    def test_validate_detects_forbidden_pattern(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No hardcoded secrets", forbidden=r"password\s*=\s*['\"]")

        # Act
        violations = validator.validate("password = 'secret123'")

        # Assert
        assert len(violations) == 1
        assert "SEC-01" in violations[0]
        assert "Forbidden" in violations[0]

    def test_validate_detects_missing_required_pattern(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("REQ-01", "Must have acceptance criteria", pattern="acceptance")

        # Act
        violations = validator.validate("This spec has no criteria section.")

        # Assert
        assert len(violations) == 1
        assert "REQ-01" in violations[0]
        assert "Missing required" in violations[0]

    def test_validate_empty_rules_returns_no_violations(self) -> None:
        # Arrange
        validator = ConstitutionValidator()

        # Act
        violations = validator.validate("any content")

        # Assert
        assert violations == []

    def test_validate_multiple_rules_all_violated(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No secrets", forbidden=r"password\s*=")
        validator.add_rule("REQ-01", "Must have tests", pattern="test")

        # Act
        violations = validator.validate("password = 'x'")

        # Assert
        assert len(violations) == 2


class TestConstitutionValidatorValidateRequirements:
    def test_validate_requirements_detects_forbidden(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No secrets", forbidden=r"password")
        requirements = [{"id": "REQ-1", "description": "Store password in plaintext"}]

        # Act
        violations = validator.validate_requirements(requirements)

        # Assert
        assert len(violations) == 1
        assert "REQ-1" in violations[0]

    def test_validate_requirements_clean_requirements(self) -> None:
        # Arrange
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No secrets", forbidden=r"password")
        requirements = [{"id": "REQ-1", "description": "User login flow"}]

        # Act
        violations = validator.validate_requirements(requirements)

        # Assert
        assert violations == []


class TestTestScenario:
    def test_to_gherkin_with_all_fields(self) -> None:
        # Arrange
        scenario = TestScenario(
            id="SCN-001",
            requirement_id="REQ-1",
            name="User login",
            given="a registered user",
            when="they submit valid credentials",
            then="they are logged in",
            and_conditions=["the session is created"],
        )

        # Act
        gherkin = scenario.to_gherkin()

        # Assert
        assert "Scenario: User login" in gherkin
        assert "Given a registered user" in gherkin
        assert "When they submit valid credentials" in gherkin
        assert "Then they are logged in" in gherkin
        assert "And the session is created" in gherkin

    def test_to_gherkin_with_empty_fields(self) -> None:
        # Arrange
        scenario = TestScenario(id="SCN-1", requirement_id="REQ-1", name="Empty")

        # Act
        gherkin = scenario.to_gherkin()

        # Assert
        assert "Scenario: Empty" in gherkin
        assert "Given" not in gherkin
        assert "When" not in gherkin
        assert "Then" not in gherkin


class TestScenarioBuilder:
    def test_add_scenario_assigns_sequential_ids(self) -> None:
        # Arrange
        builder = ScenarioBuilder()

        # Act
        s1 = builder.add_scenario("REQ-1", "First")
        s2 = builder.add_scenario("REQ-1", "Second")

        # Assert
        assert s1.id == "SCN-001"
        assert s2.id == "SCN-002"

    def test_for_requirement_filters_scenarios(self) -> None:
        # Arrange
        builder = ScenarioBuilder()
        builder.add_scenario("REQ-1", "A")
        builder.add_scenario("REQ-2", "B")
        builder.add_scenario("REQ-1", "C")

        # Act
        scenarios = builder.for_requirement("REQ-1")

        # Assert
        assert len(scenarios) == 2
        assert all(s.requirement_id == "REQ-1" for s in scenarios)

    def test_to_gherkin_feature_includes_all_scenarios(self) -> None:
        # Arrange
        builder = ScenarioBuilder()
        builder.add_scenario("REQ-1", "First", given="x", when="y", then="z")
        builder.add_scenario("REQ-1", "Second", given="a", when="b", then="c")

        # Act
        feature = builder.to_gherkin_feature("My Feature")

        # Assert
        assert "Feature: My Feature" in feature
        assert "Scenario: First" in feature
        assert "Scenario: Second" in feature

    def test_all_scenarios_returns_copy(self) -> None:
        # Arrange
        builder = ScenarioBuilder()
        builder.add_scenario("REQ-1", "A")

        # Act
        all_s = builder.all_scenarios()
        all_s.clear()

        # Assert — internal list should be unaffected
        assert len(builder.all_scenarios()) == 1


class TestSpecLinkageGraph:
    def test_add_link_stores_link(self) -> None:
        # Arrange
        graph = SpecLinkageGraph()

        # Act
        link = graph.add_link("spec", "S1", "requirement", "R1", "implements")

        # Assert
        assert link.source_id == "S1"
        assert link.target_id == "R1"
        assert link.link_type == "implements"

    def test_links_from_returns_matching_links(self) -> None:
        # Arrange
        graph = SpecLinkageGraph()
        graph.add_link("spec", "S1", "requirement", "R1", "implements")
        graph.add_link("spec", "S1", "code", "C1", "references")
        graph.add_link("spec", "S2", "requirement", "R2", "implements")

        # Act
        links = graph.links_from("S1")

        # Assert
        assert len(links) == 2

    def test_links_to_returns_matching_links(self) -> None:
        # Arrange
        graph = SpecLinkageGraph()
        graph.add_link("spec", "S1", "requirement", "R1", "implements")
        graph.add_link("code", "C1", "requirement", "R1", "tests")

        # Act
        links = graph.links_to("R1")

        # Assert
        assert len(links) == 2

    def test_impact_analysis_traverses_chain(self) -> None:
        # Arrange
        graph = SpecLinkageGraph()
        graph.add_link("spec", "S1", "requirement", "R1", "implements")
        graph.add_link("requirement", "R1", "code", "C1", "implemented_by")

        # Act
        affected = graph.impact_analysis("spec", "S1")

        # Assert
        assert len(affected) == 2
        target_ids = [link.target_id for link in affected]
        assert "R1" in target_ids
        assert "C1" in target_ids

    def test_impact_analysis_handles_cycles(self) -> None:
        # Arrange
        graph = SpecLinkageGraph()
        graph.add_link("spec", "S1", "spec", "S2", "depends_on")
        graph.add_link("spec", "S2", "spec", "S1", "depends_on")

        # Act — should not infinite loop
        affected = graph.impact_analysis("spec", "S1")

        # Assert
        assert len(affected) >= 1
