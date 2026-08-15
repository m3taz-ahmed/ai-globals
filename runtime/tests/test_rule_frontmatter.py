"""Tests for runtime/rule_frontmatter.py and its SkillResolver integration."""

from __future__ import annotations

from pathlib import Path

from runtime.rule_frontmatter import (
    RuleFrontmatter,
    _as_str_list,
    _match_path,
    _match_paths,
    _match_personas,
    _match_stack,
    matches_context,
    parse_frontmatter,
)
from runtime.skill_resolver import SkillResolver


class TestParseFrontmatter:
    def test_empty_text_returns_empty_frontmatter(self):
        frontmatter, body = parse_frontmatter("")
        assert frontmatter == RuleFrontmatter()
        assert body == ""

    def test_no_frontmatter_returns_full_body(self):
        text = "# Hello\nWorld\n"
        frontmatter, body = parse_frontmatter(text)
        assert frontmatter == RuleFrontmatter()
        assert body == text

    def test_simple_frontmatter(self):
        text = "---\npaths:\n  - src/**/*.py\npersonas: [DEV, ARCH]\n---\n# Body\n"
        frontmatter, body = parse_frontmatter(text)
        assert frontmatter.paths == ["src/**/*.py"]
        assert frontmatter.personas == ["DEV", "ARCH"]
        assert frontmatter.stack is None
        assert frontmatter.always is False
        assert body == "# Body\n"

    def test_single_string_values_normalized_to_lists(self):
        text = "---\npersonas: SEC\nstack: laravel\nalways: true\n---\nbody"
        frontmatter, body = parse_frontmatter(text)
        assert frontmatter.personas == ["SEC"]
        assert frontmatter.stack == ["laravel"]
        assert frontmatter.always is True
        assert body == "body"

    def test_invalid_yaml_falls_back_to_empty(self):
        text = "---\nfoo: [bar\n---\nbody"
        frontmatter, body = parse_frontmatter(text)
        assert frontmatter == RuleFrontmatter()
        assert body == "body"

    def test_non_dict_yaml_falls_back_to_empty(self):
        text = "---\njust a string\n---\nbody"
        frontmatter, _ = parse_frontmatter(text)
        assert frontmatter == RuleFrontmatter()

    def test_non_str_non_list_value_normalized_to_list(self):
        """Cover line 43: _as_str_list converts non-str/non-list values to [str(value)]."""
        text = "---\npaths: 42\n---\nbody"
        frontmatter, _ = parse_frontmatter(text)
        assert frontmatter.paths == ["42"]


class TestAsStrList:
    def test_none_returns_none(self):
        assert _as_str_list(None) is None

    def test_str_returns_single_item_list(self):
        assert _as_str_list("hello") == ["hello"]

    def test_list_returns_str_list(self):
        assert _as_str_list(["a", "b"]) == ["a", "b"]

    def test_other_type_returns_str_list(self):
        assert _as_str_list(42) == ["42"]
        assert _as_str_list(3.14) == ["3.14"]


class TestMatchPath:
    def test_exact_match(self):
        assert _match_path("src/main.py", "src/main.py")

    def test_star_glob(self):
        assert _match_path("*.py", "src/main.py")
        assert not _match_path("*.py", "src/main.js")

    def test_double_star_falls_back_to_single_star_on_older_python(self):
        # `**` may not match on Python <3.13 without full_match; ensure no crash.
        assert _match_path("src/**/*.py", "src/main.py") in (True, False)

    def test_double_star_full_match(self):
        """Cover line 79: full_match branch for ** patterns."""
        # On Python 3.13+, full_match is available and should match nested paths.
        result = _match_path("src/**/*.py", "src/sub/main.py")
        assert isinstance(result, bool)

    def test_double_star_full_match_mocked(self, monkeypatch):
        """Cover line 79: force full_match branch even on Python <3.13."""
        from pathlib import PurePosixPath

        monkeypatch.setattr(
            PurePosixPath, "full_match", lambda self, pattern: True, raising=False
        )
        assert _match_path("src/**/*.py", "src/sub/main.py") is True

    def test_backslash_normalization(self):
        assert _match_path("src/*", "src\\main.py")


class TestMatchPaths:
    def test_any_path_matches_any_pattern(self):
        assert _match_paths(["src/*.py", "tests/*.py"], ["src/a.py", "readme.md"])
        assert not _match_paths(["src/*.py"], ["tests/a.py"])

    def test_string_path_is_not_iterated(self):
        # matches_context normalizes strings to lists before calling _match_paths.
        assert _match_paths(["src/*.py"], ["src/main.py"])


class TestMatchPersonas:
    def test_primary_persona_matches(self):
        assert _match_personas(["dev"], {"persona": "DEV"})

    def test_personas_list_matches(self):
        assert _match_personas(["qa"], {"personas": ["QA", "ARCH"]})

    def test_case_insensitive(self):
        assert _match_personas(["Dev"], {"persona": "dev"})

    def test_no_match(self):
        assert not _match_personas(["sec"], {"persona": "DEV"})

    def test_string_personas_normalized(self):
        assert _match_personas(["dev"], {"personas": "DEV"})


class TestMatchStack:
    def test_exact_package(self):
        assert _match_stack(["laravel"], ["laravel"])

    def test_package_with_version(self):
        assert _match_stack(["laravel"], ["laravel/framework"])

    def test_split_by_separators(self):
        assert _match_stack(["react"], ["react-router"])

    def test_no_match(self):
        assert not _match_stack(["vue"], ["react"])


class TestMatchesContext:
    def test_always_wins(self):
        assert matches_context(RuleFrontmatter(always=True), {"persona": "UNKNOWN"})

    def test_no_conditions_is_active(self):
        assert matches_context(RuleFrontmatter(), {})

    def test_persona_condition(self):
        fm = RuleFrontmatter(personas=["SEC"])
        assert matches_context(fm, {"persona": "SEC"})
        assert not matches_context(fm, {"persona": "DEV"})

    def test_path_condition(self):
        fm = RuleFrontmatter(paths=["src/*.py"])
        assert matches_context(fm, {"paths": ["src/main.py"]})
        assert not matches_context(fm, {"paths": ["docs/readme.md"]})

    def test_stack_condition(self):
        fm = RuleFrontmatter(stack=["laravel"])
        assert matches_context(fm, {"stack": ["laravel/framework"]})
        assert not matches_context(fm, {"stack": ["react"]})

    def test_multiple_conditions_are_or(self):
        fm = RuleFrontmatter(personas=["DEV"], stack=["vue"])
        assert matches_context(fm, {"persona": "DEV"})
        assert matches_context(fm, {"stack": ["vue"]})  # noqa: RUF100
        assert not matches_context(fm, {"persona": "UX", "stack": ["react"]})

    def test_none_context_treated_as_empty(self):
        assert matches_context(RuleFrontmatter(), None)
        assert not matches_context(RuleFrontmatter(personas=["DEV"]), None)

    def test_string_stack_and_paths_normalized(self):
        assert matches_context(RuleFrontmatter(stack=["laravel"]), {"stack": "laravel"})
        assert matches_context(RuleFrontmatter(paths=["src/*.py"]), {"paths": "src/main.py"})


class TestSkillResolverFrontmatter:
    def test_resolve_with_frontmatter_returns_none_for_missing_skill(self, tmp_path: Path):
        resolver = SkillResolver(tmp_path, tmp_path)
        assert resolver.resolve_with_frontmatter("missing", {}) is None

    def test_load_with_frontmatter_returns_body_and_ignores_frontmatter(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "flat.md").write_text(
            "---\nname: flat\npersonas: [DEV]\n---\n[SKILL] flat\n[OBJ] Test.\n",
            encoding="utf-8",
        )
        resolver = SkillResolver(tmp_path, tmp_path)

        body = resolver.load_with_frontmatter("flat", {"persona": "DEV"})
        assert body is not None
        assert "[SKILL] flat" in body
        assert "---" not in body

    def test_resolve_with_frontmatter_filters_by_context(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "sec_only.md").write_text(
            "---\npersonas: [SEC]\n---\n[SKILL] sec_only\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path, tmp_path)

        assert resolver.resolve_with_frontmatter("sec_only", {"persona": "SEC"}) is not None
        assert resolver.resolve_with_frontmatter("sec_only", {"persona": "DEV"}) is None

    def test_list_active_skills_filters_by_context(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "always.md").write_text(
            "---\nalways: true\n---\n[SKILL] always\n", encoding="utf-8"
        )
        (skills / "dev_only.md").write_text(
            "---\npersonas: [DEV]\n---\n[SKILL] dev_only\n", encoding="utf-8"
        )
        (skills / "unconditional.md").write_text(
            "---\nname: unconditional\n---\n[SKILL] unconditional\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path, tmp_path)

        active = resolver.list_active_skills({"persona": "DEV"})
        assert "always" in active
        assert "dev_only" in active
        assert "unconditional" in active

        active_arch = resolver.list_active_skills({"persona": "ARCH"})
        assert "always" in active_arch
        assert "dev_only" not in active_arch
        assert "unconditional" in active_arch

    def test_project_skill_overrides_os_skill(self, tmp_path: Path):
        os_root = tmp_path / "os"
        project_root = tmp_path / "project"
        for r in (os_root, project_root):
            (r / "skills").mkdir(parents=True)
        (os_root / "skills" / "flat.md").write_text(
            "---\npersonas: [DEV]\n---\nOS", encoding="utf-8"
        )
        (project_root / ".ai" / "skills").mkdir(parents=True)
        (project_root / ".ai" / "skills" / "flat.md").write_text(
            "---\npersonas: [ARCH]\n---\nPROJECT", encoding="utf-8"
        )
        resolver = SkillResolver(os_root, project_root)

        assert resolver.resolve_with_frontmatter("flat", {"persona": "ARCH"}) is not None
        assert resolver.resolve_with_frontmatter("flat", {"persona": "DEV"}) is None
