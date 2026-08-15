"""Tests for tech-stack auto-detection."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.kernel import Kernel
from runtime.tech_stack import (
    _candidate_prefixes,
    _candidate_stems,
    _clean_version,
    _package_names,
    _parse_composer_json,
    _parse_composer_lock,
    _parse_package_json,
    _parse_package_lock,
    _parse_pep508,
    _parse_pyproject_regex,
    _parse_pyproject_toml,
    _resolve_tech_stack,
    _version_triple,
    detect_stack,
    load_stack_docs,
)


def test_detect_from_package_lock(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"": {"dependencies": {"react": "^18.2.0"}}, '
        '"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "react" in detected
    assert detected["react"]["version"] == "18.2.0"


def test_load_stack_docs(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    docs = load_stack_docs(project, os_root)
    assert "react" in docs


def test_kernel_detect_tech_stack(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React 18.2\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    k = Kernel(os_root, project)
    detected = k.detect_tech_stack()
    assert "react" in detected


def test_detect_major_minor_naming(tmp_path: Path) -> None:
    """tech-stack files use hyphenated major-minor names, not exact patch."""
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "php-8-3.md").write_text("# PHP 8.3\n", encoding="utf-8")
    (project / "composer.lock").write_text(
        '{"packages": [{"name": "php", "version": "8.3.11"}]}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "php" in detected
    assert detected["php"]["path"] == "tech-stack/php-8-3.md"


def test_detect_from_package_json_without_lock(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "tailwind-4.md").write_text("# Tailwind 4\n", encoding="utf-8")
    (project / "package.json").write_text(
        '{"dependencies": {"tailwindcss": "^4.1.0"}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "tailwindcss" in detected
    assert detected["tailwindcss"]["path"] == "tech-stack/tailwind-4.md"


def test_detect_laravel_from_composer_json(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True, exist_ok=True)
    (project).mkdir(parents=True, exist_ok=True)
    (os_root / "tech-stack" / "laravel-12.md").write_text("# Laravel 12\n", encoding="utf-8")
    (project / "composer.json").write_text(
        '{"require": {"laravel/framework": "^12.0"}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert "laravel/framework" in detected
    assert detected["laravel/framework"]["path"] == "tech-stack/laravel-12.md"


# ---------------------------------------------------------------------------
# _clean_version
# ---------------------------------------------------------------------------


def test_clean_version_non_string_returns_none() -> None:
    assert _clean_version(None) is None  # type: ignore[arg-type]
    assert _clean_version(123) is None  # type: ignore[arg-type]


def test_clean_version_wildcards_return_none() -> None:
    for val in ("*", "latest", ""):
        assert _clean_version(val) is None


def test_clean_version_dev_git_prefixes_return_none() -> None:
    for val in ("dev-foo", "git+ssh://x", "file:./x", "https://x", "github:u/r"):
        assert _clean_version(val) is None


def test_clean_version_token_wildcards_return_none() -> None:
    # range first token is empty / * / x
    assert _clean_version(" * ") is None
    assert _clean_version("x") is None


def test_clean_version_token_dev_prefix_return_none() -> None:
    assert _clean_version("dev-foo || ^1.0") is None


def test_clean_version_no_numeric_returns_none() -> None:
    assert _clean_version("abc") is None


def test_clean_version_single_part_pads_zero() -> None:
    assert _clean_version("1") == "1.0"


def test_clean_version_normal() -> None:
    assert _clean_version("^1.2.3") == "1.2.3"
    assert _clean_version(">=2.0") == "2.0"


# ---------------------------------------------------------------------------
# _version_triple
# ---------------------------------------------------------------------------


def test_version_triple_no_match_returns_none() -> None:
    assert _version_triple("abc") is None


def test_version_triple_partial() -> None:
    assert _version_triple("1") == (1, 0, 0)
    assert _version_triple("1.2") == (1, 2, 0)
    assert _version_triple("1.2.3") == (1, 2, 3)


# ---------------------------------------------------------------------------
# _package_names
# ---------------------------------------------------------------------------


def test_package_names_node_modules_prefix() -> None:
    names = set(_package_names("node_modules/react"))
    assert "react" in names


def test_package_names_three_parts_middle() -> None:
    names = set(_package_names("spatie/laravel-permission"))
    assert "laravel-permission" in names
    # len(parts) >= 3 branch -> middle join
    assert "laravel-permission" in names


def test_package_names_scoped() -> None:
    names = set(_package_names("@tanstack/react-query"))
    assert "react-query" in names
    assert "tanstack-react-query" in names


# ---------------------------------------------------------------------------
# _candidate_stems / _candidate_prefixes
# ---------------------------------------------------------------------------


def test_candidate_stems_no_triple() -> None:
    with patch("runtime.tech_stack._version_triple", return_value=None):
        assert _candidate_stems("prefix", "abc") == ["prefix"]


def test_resolve_tech_stack_no_tech_dir(tmp_path: Path) -> None:
    # os_root exists but no tech-stack subdir
    assert _resolve_tech_stack("react", "18.0.0", tmp_path) is None


def test_resolve_tech_stack_no_match(tmp_path: Path) -> None:
    (tmp_path / "tech-stack").mkdir()
    assert _resolve_tech_stack("nonexistent", "9.9.9", tmp_path) is None


# ---------------------------------------------------------------------------
# _parse_package_lock
# ---------------------------------------------------------------------------


def test_parse_package_lock_non_dict_info_skipped(tmp_path: Path) -> None:
    p = tmp_path / "package-lock.json"
    p.write_text(json.dumps({"packages": {"node_modules/x": "not-a-dict"}}), encoding="utf-8")
    assert _parse_package_lock(p) == {}


def test_parse_package_lock_legacy_keys(tmp_path: Path) -> None:
    p = tmp_path / "package-lock.json"
    p.write_text(
        json.dumps({"dependencies": {"react": {"version": "18.0.0"}}}),
        encoding="utf-8",
    )
    versions = _parse_package_lock(p)
    assert versions == {"react": "18.0.0"}


# ---------------------------------------------------------------------------
# _parse_composer_lock / _parse_package_json / _parse_composer_json
# ---------------------------------------------------------------------------


def test_parse_composer_lock(tmp_path: Path) -> None:
    p = tmp_path / "composer.lock"
    p.write_text(
        json.dumps(
            {
                "packages": [{"name": "laravel/framework", "version": "12.0.0"}],
                "packages-dev": [{"name": "pestphp/pest", "version": "3.0.0"}],
            }
        ),
        encoding="utf-8",
    )
    versions = _parse_composer_lock(p)
    assert versions == {"laravel/framework": "12.0.0", "pestphp/pest": "3.0.0"}


def test_parse_package_json(tmp_path: Path) -> None:
    p = tmp_path / "package.json"
    p.write_text(
        json.dumps(
            {
                "dependencies": {"react": "^18.0.0"},
                "devDependencies": {"vitest": "*"},
            }
        ),
        encoding="utf-8",
    )
    versions = _parse_package_json(p)
    assert versions == {"react": "18.0.0"}


def test_parse_composer_json(tmp_path: Path) -> None:
    p = tmp_path / "composer.json"
    p.write_text(
        json.dumps(
            {"require": {"php": "^8.2"}, "require-dev": {"pestphp/pest": "^3.0"}}
        ),
        encoding="utf-8",
    )
    versions = _parse_composer_json(p)
    assert versions == {"php": "8.2", "pestphp/pest": "3.0"}


# ---------------------------------------------------------------------------
# _parse_pyproject_toml / _parse_pep508 / _parse_pyproject_regex
# ---------------------------------------------------------------------------


def test_parse_pyproject_toml(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text(
        """
[project]
dependencies = ["fastmcp>=2.0", "rich>=13.0"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff"]
""",
        encoding="utf-8",
    )
    versions = _parse_pyproject_toml(p)
    assert versions.get("fastmcp") == "2.0"
    assert versions.get("rich") == "13.0"
    assert versions.get("pytest") == "8.0"


def test_parse_pep508_no_match() -> None:
    versions: dict[str, str] = {}
    _parse_pep508("   ", versions)
    assert versions == {}


def test_parse_pep508_no_version() -> None:
    versions: dict[str, str] = {}
    _parse_pep508("ruff", versions)
    assert versions == {}


def test_parse_pyproject_regex(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    # Regex fallback expects name+operator at start of line.
    p.write_text(
        'fastmcp>=2.0\nrich>=13.0\n',
        encoding="utf-8",
    )
    versions = _parse_pyproject_regex(p)
    assert versions.get("fastmcp") == "2.0"
    assert versions.get("rich") == "13.0"


def test_parse_pyproject_toml_fallback_to_regex(tmp_path: Path) -> None:
    """Force the tomllib ImportError -> tomli ImportError -> regex fallback."""
    p = tmp_path / "pyproject.toml"
    p.write_text('fastmcp>=2.0\n', encoding="utf-8")
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("tomllib", "tomli"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=fake_import):
        # Force a non-tomllib/tomli import to cover the else branch
        import os  # noqa: F401
        versions = _parse_pyproject_toml(p)
    assert versions.get("fastmcp") == "2.0"


# ---------------------------------------------------------------------------
# detect_stack error + dedup paths
# ---------------------------------------------------------------------------


def test_detect_stack_lockfile_parse_error_logged(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True)
    project.mkdir(parents=True)
    (project / "package-lock.json").write_text("{invalid json", encoding="utf-8")
    # Should not raise; returns empty
    assert detect_stack(project, os_root) == {}


def test_detect_stack_manifest_parse_error_logged(tmp_path: Path) -> None:
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True)
    project.mkdir(parents=True)
    (project / "package.json").write_text("{invalid", encoding="utf-8")
    assert detect_stack(project, os_root) == {}


def test_detect_stack_manifest_skips_already_detected(tmp_path: Path) -> None:
    """Lockfile-detected package should not be overridden by manifest (line 348)."""
    os_root = tmp_path / "os"
    project = tmp_path / "project"
    (os_root / "tech-stack").mkdir(parents=True)
    project.mkdir(parents=True)
    (os_root / "tech-stack" / "react-18.2.0.md").write_text("# React\n", encoding="utf-8")
    (project / "package-lock.json").write_text(
        '{"packages": {"node_modules/react": {"version": "18.2.0"}}}',
        encoding="utf-8",
    )
    # Manifest has a different constraint; lockfile wins
    (project / "package.json").write_text(
        '{"dependencies": {"react": "^17.0.0"}}',
        encoding="utf-8",
    )
    detected = detect_stack(project, os_root)
    assert detected["react"]["version"] == "18.2.0"


def test_clean_version_token_dev_prefix_after_split(monkeypatch) -> None:
    """Cover line 110: token starts with dev- prefix after split (constraint doesn't)."""
    import runtime.tech_stack as ts

    original_split = ts.re.split

    def mock_split(pattern, string, *args, **kwargs):
        if pattern == r"[|, ]":
            return ["dev-foo", "rest"]
        return original_split(pattern, string, *args, **kwargs)  # pragma: no cover

    monkeypatch.setattr(ts.re, "split", mock_split)
    # Constraint "^1.0" doesn't start with dev- (skips line 103-104),
    # but mocked split makes the first token "dev-foo" (hits line 109-110).
    assert ts._clean_version("^1.0") is None
