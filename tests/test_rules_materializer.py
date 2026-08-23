"""Tests for runtime/rules_materializer.py — rule materialization to AI tool files.

FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from runtime.rules_materializer import (
    RuleEntry,
    RulesMaterializer,
    ScopeLevel,
    ToolTarget,
)
from runtime.schemas import ValidationError

# -- RuleEntry ---------------------------------------------------------------


class TestRuleEntry:
    def test_creation_with_defaults(self) -> None:
        # Arrange + Act
        entry = RuleEntry(key="no_secrets", content="Never commit secrets.")
        # Assert
        assert entry.key == "no_secrets"
        assert entry.content == "Never commit secrets."
        assert entry.scope is ScopeLevel.REPO
        assert entry.globs is None
        assert entry.always_apply is False
        assert entry.description == ""

    def test_creation_with_all_fields(self) -> None:
        # Arrange + Act
        entry = RuleEntry(
            key="py_typed",
            content="Use strict typing.",
            scope=ScopeLevel.ORG,
            globs=["**/*.py"],
            always_apply=True,
            description="Enforce type hints",
        )
        # Assert
        assert entry.scope is ScopeLevel.ORG
        assert entry.globs == ["**/*.py"]
        assert entry.always_apply is True
        assert entry.description == "Enforce type hints"

    def test_to_dict_without_globs(self) -> None:
        # Arrange
        entry = RuleEntry(key="r1", content="c1", scope=ScopeLevel.TEAM)
        # Act
        d = entry.to_dict()
        # Assert
        assert d["key"] == "r1"
        assert d["content"] == "c1"
        assert d["scope"] == "team"
        assert d["always_apply"] is False
        assert d["description"] == ""
        assert "globs" not in d

    def test_to_dict_with_globs(self) -> None:
        # Arrange
        entry = RuleEntry(key="r2", content="c2", globs=["**/*.ts"])
        # Act
        d = entry.to_dict()
        # Assert
        assert d["globs"] == ["**/*.ts"]

    def test_frozen_dataclass_is_immutable(self) -> None:
        # Arrange
        entry = RuleEntry(key="r3", content="c3")
        # Act + Assert
        with pytest.raises(FrozenInstanceError):
            entry.key = "other"  # type: ignore[misc]


# -- ScopeLevel.precedence ---------------------------------------------------


class TestScopeLevelPrecedence:
    def test_org_is_highest(self) -> None:
        # Arrange + Act + Assert
        assert ScopeLevel.ORG.precedence > ScopeLevel.PROJECT.precedence

    def test_project_above_namespace(self) -> None:
        assert ScopeLevel.PROJECT.precedence > ScopeLevel.NAMESPACE.precedence

    def test_namespace_above_repo(self) -> None:
        assert ScopeLevel.NAMESPACE.precedence > ScopeLevel.REPO.precedence

    def test_repo_above_team(self) -> None:
        assert ScopeLevel.REPO.precedence > ScopeLevel.TEAM.precedence

    def test_team_above_user(self) -> None:
        assert ScopeLevel.TEAM.precedence > ScopeLevel.USER.precedence

    def test_full_ordering(self) -> None:
        # Arrange
        levels = [
            ScopeLevel.ORG,
            ScopeLevel.PROJECT,
            ScopeLevel.NAMESPACE,
            ScopeLevel.REPO,
            ScopeLevel.TEAM,
            ScopeLevel.USER,
        ]
        # Act
        precedences = [s.precedence for s in levels]
        # Assert
        assert precedences == sorted(precedences, reverse=True)


# -- resolve() ---------------------------------------------------------------


class TestResolve:
    def test_merge_by_scope_higher_overrides_lower_same_key(self) -> None:
        # Arrange
        user_rule = RuleEntry(key="style", content="user-level", scope=ScopeLevel.USER)
        org_rule = RuleEntry(key="style", content="org-level", scope=ScopeLevel.ORG)
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.USER: [user_rule],
            ScopeLevel.ORG: [org_rule],
        }
        mat = RulesMaterializer(Path("/tmp"))
        # Act
        resolved = mat.resolve(rule_sets)
        # Assert
        assert len(resolved) == 1
        assert resolved[0].content == "org-level"

    def test_dedup_by_key(self) -> None:
        # Arrange
        r1 = RuleEntry(key="a", content="a-content", scope=ScopeLevel.REPO)
        r2 = RuleEntry(key="a", content="a-dup", scope=ScopeLevel.REPO)
        r3 = RuleEntry(key="b", content="b-content", scope=ScopeLevel.REPO)
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.REPO: [r1, r2, r3],
        }
        mat = RulesMaterializer(Path("/tmp"))
        # Act
        resolved = mat.resolve(rule_sets)
        # Assert
        keys = [r.key for r in resolved]
        assert keys == ["a", "b"]

    def test_resolve_returns_sorted_by_key(self) -> None:
        # Arrange
        r_z = RuleEntry(key="z_rule", content="z", scope=ScopeLevel.REPO)
        r_a = RuleEntry(key="a_rule", content="a", scope=ScopeLevel.REPO)
        r_m = RuleEntry(key="m_rule", content="m", scope=ScopeLevel.REPO)
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.REPO: [r_z, r_a, r_m],
        }
        mat = RulesMaterializer(Path("/tmp"))
        # Act
        resolved = mat.resolve(rule_sets)
        # Assert
        assert [r.key for r in resolved] == ["a_rule", "m_rule", "z_rule"]

    def test_resolve_empty_rule_sets(self) -> None:
        # Arrange
        mat = RulesMaterializer(Path("/tmp"))
        # Act
        resolved = mat.resolve({})
        # Assert
        assert resolved == []


# -- materialize() -----------------------------------------------------------


class TestMaterialize:
    def test_writes_all_target_files(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="style", content="Use 4 spaces.")]
        mat = RulesMaterializer(tmp_path)
        # Act
        results = mat.materialize(rules)
        # Assert
        expected_files = {
            "CLAUDE.md",
            ".cursor/rules/aizee.mdc",
            ".clinerules/aizee.md",
            ".windsurfrules",
            ".github/copilot-instructions.md",
            "CONVENTIONS.md",
            ".devin/rules/aizee.md",
        }
        written = {str(p.relative_to(tmp_path)).replace("\\", "/") for r in results for p in r.files_written}
        assert expected_files <= written

    def test_raises_validation_error_on_empty_rules(self, tmp_path: Path) -> None:
        # Arrange
        mat = RulesMaterializer(tmp_path)
        # Act + Assert
        with pytest.raises(ValidationError):
            mat.materialize([])

    def test_materialize_specific_target_only(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="style", content="Use 4 spaces.")]
        mat = RulesMaterializer(tmp_path)
        # Act
        results = mat.materialize(rules, targets=[ToolTarget.CLAUDE])
        # Assert
        assert len(results) == 1
        assert results[0].target is ToolTarget.CLAUDE
        assert (tmp_path / "CLAUDE.md").exists()

    def test_materialize_result_has_rules_emitted(self, tmp_path: Path) -> None:
        # Arrange
        rules = [
            RuleEntry(key="r1", content="c1"),
            RuleEntry(key="r2", content="c2"),
        ]
        mat = RulesMaterializer(tmp_path)
        # Act
        results = mat.materialize(rules, targets=[ToolTarget.CLAUDE])
        # Assert
        assert results[0].rules_emitted == 2

    def test_materialize_is_idempotent(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="style", content="Use 4 spaces.")]
        mat = RulesMaterializer(tmp_path)
        # Act
        mat.materialize(rules, targets=[ToolTarget.CLAUDE])
        mat.materialize(rules, targets=[ToolTarget.CLAUDE])
        # Assert
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert content.count("## style") == 1


# -- materialize_all() -------------------------------------------------------


class TestMaterializeAll:
    def test_resolve_and_materialize_in_one_call(self, tmp_path: Path) -> None:
        # Arrange
        org_rule = RuleEntry(key="style", content="org-level", scope=ScopeLevel.ORG)
        user_rule = RuleEntry(key="style", content="user-level", scope=ScopeLevel.USER)
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.ORG: [org_rule],
            ScopeLevel.USER: [user_rule],
        }
        mat = RulesMaterializer(tmp_path)
        # Act
        results = mat.materialize_all(rule_sets)
        # Assert
        assert len(results) == len(list(ToolTarget))
        claude_content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "org-level" in claude_content
        assert "user-level" not in claude_content

    def test_raises_validation_error_when_no_rules_after_resolution(self, tmp_path: Path) -> None:
        # Arrange
        mat = RulesMaterializer(tmp_path)
        # Act + Assert
        with pytest.raises(ValidationError):
            mat.materialize_all({})


# -- detect_drift() ----------------------------------------------------------


class TestDetectDrift:
    def test_returns_missing_keys_when_file_missing(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="style", content="c"), RuleEntry(key="test", content="t")]
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.REPO: [rules[0]],
            ScopeLevel.TEAM: [rules[1]],
        }
        mat = RulesMaterializer(tmp_path)
        # Act
        drift = mat.detect_drift(rule_sets, targets=[ToolTarget.CLAUDE])
        # Assert
        assert "claude" in drift
        assert set(drift["claude"]) == {"style", "test"}

    def test_returns_empty_when_files_fresh(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="style", content="c")]
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.REPO: [rules[0]],
        }
        mat = RulesMaterializer(tmp_path)
        mat.materialize_all(rule_sets)
        # Act
        drift = mat.detect_drift(rule_sets, targets=[ToolTarget.CLAUDE])
        # Assert
        assert drift["claude"] == []

    def test_returns_stale_keys_when_file_missing_key(self, tmp_path: Path) -> None:
        # Arrange — materialize one rule, then check drift against two
        rule1 = RuleEntry(key="style", content="c")
        mat = RulesMaterializer(tmp_path)
        mat.materialize([rule1], targets=[ToolTarget.CLAUDE])
        rule_sets: dict[ScopeLevel, list[RuleEntry]] = {
            ScopeLevel.REPO: [rule1, RuleEntry(key="new_key", content="nc")],
        }
        # Act
        drift = mat.detect_drift(rule_sets, targets=[ToolTarget.CLAUDE])
        # Assert
        assert "new_key" in drift["claude"]
        assert "style" not in drift["claude"]


# -- _emit_cursor() frontmatter ----------------------------------------------


class TestEmitCursor:
    def test_frontmatter_has_description_globs_alwaysapply(self, tmp_path: Path) -> None:
        # Arrange
        rules = [
            RuleEntry(key="r1", content="c1", globs=["**/*.py"]),
        ]
        mat = RulesMaterializer(tmp_path)
        # Act
        mat.materialize(rules, targets=[ToolTarget.CURSOR])
        content = (tmp_path / ".cursor" / "rules" / "aizee.mdc").read_text(encoding="utf-8")
        # Assert
        assert content.startswith("---")
        frontmatter = content.split("---")[1]
        assert "description:" in frontmatter
        assert "globs:" in frontmatter
        assert "alwaysApply:" in frontmatter
        assert "**/*.py" in frontmatter

    def test_frontmatter_defaults_glob_when_none_specified(self, tmp_path: Path) -> None:
        # Arrange
        rules = [RuleEntry(key="r1", content="c1")]
        mat = RulesMaterializer(tmp_path)
        # Act
        mat.materialize(rules, targets=[ToolTarget.CURSOR])
        content = (tmp_path / ".cursor" / "rules" / "aizee.mdc").read_text(encoding="utf-8")
        # Assert
        frontmatter = content.split("---")[1]
        assert "**/*" in frontmatter
