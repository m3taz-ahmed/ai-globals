"""Tests for runtime/skill_resolver.py."""

from __future__ import annotations

from pathlib import Path

from runtime.skill_resolver import SkillResolver


class TestSkillResolverFlatSkill:
    def test_resolve_flat_skill(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill.md").write_text("# My Skill", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("my-skill")

        # Assert
        assert path is not None
        assert path.name == "my-skill.md"

    def test_exists_flat_skill(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill.md").write_text("# My Skill", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act & Assert
        assert resolver.exists("my-skill") is True

    def test_load_flat_skill_returns_content(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "my-skill.md").write_text("# My Skill Body", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        content = resolver.load("my-skill")

        # Assert
        assert content is not None
        assert "My Skill Body" in content


class TestSkillResolverNestedSkill:
    def test_resolve_nested_skill(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        nested = skills_dir / "nested-skill"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("# Nested Skill", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("nested-skill")

        # Assert
        assert path is not None
        assert path.name == "SKILL.md"

    def test_load_nested_skill_returns_content(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        nested = skills_dir / "nested-skill"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("# Nested Content", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        content = resolver.load("nested-skill")

        # Assert
        assert content is not None
        assert "Nested Content" in content


class TestSkillResolverInvalidNames:
    def test_resolve_path_traversal_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("../../../etc/passwd")

        # Assert
        assert path is None

    def test_resolve_with_slash_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("foo/bar")

        # Assert
        assert path is None

    def test_resolve_with_backslash_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("foo\\bar")

        # Assert
        assert path is None

    def test_resolve_empty_name_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("")

        # Assert
        assert path is None


class TestSkillResolverMissingSkill:
    def test_resolve_missing_skill_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        path = resolver.resolve("nonexistent")

        # Assert
        assert path is None

    def test_exists_missing_skill_returns_false(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act & Assert
        assert resolver.exists("nonexistent") is False

    def test_load_missing_skill_returns_none(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        content = resolver.load("nonexistent")

        # Assert
        assert content is None


class TestSkillResolverListSkills:
    def test_list_skills_returns_sorted_names(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "zebra.md").write_text("# Zebra", encoding="utf-8")
        (skills_dir / "alpha.md").write_text("# Alpha", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        names = resolver.list_skills()

        # Assert
        assert names == ["alpha", "zebra"]

    def test_list_skills_includes_nested_skills(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        nested = skills_dir / "nested"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("# Nested", encoding="utf-8")
        (skills_dir / "flat.md").write_text("# Flat", encoding="utf-8")
        resolver = SkillResolver(root=tmp_path)

        # Act
        names = resolver.list_skills()

        # Assert
        assert "nested" in names
        assert "flat" in names

    def test_list_skills_empty_directory(self, tmp_path: Path) -> None:
        # Arrange
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        resolver = SkillResolver(root=tmp_path)

        # Act
        names = resolver.list_skills()

        # Assert
        assert names == []


class TestSkillResolverProjectSkills:
    def test_project_skill_resolved_before_os_skill(self, tmp_path: Path) -> None:
        # Arrange
        os_skills = tmp_path / "skills"
        os_skills.mkdir()
        (os_skills / "shared.md").write_text("# OS Skill", encoding="utf-8")

        project_root = tmp_path / "project"
        project_skills = project_root / ".ai" / "skills"
        project_skills.mkdir(parents=True)
        (project_skills / "shared.md").write_text("# Project Skill", encoding="utf-8")

        resolver = SkillResolver(root=tmp_path, project_root=project_root)

        # Act
        content = resolver.load("shared")

        # Assert
        assert content is not None
        assert "Project Skill" in content
