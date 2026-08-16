"""Tests for review_engine FileFilter — 5-gate deterministic pre-filtering."""

from __future__ import annotations

from pathlib import Path

from runtime.review_engine import ExcludeReason, FileFilter


class TestFileFilter:
    """Tests for the 5-gate file filter (from open-code-review)."""

    def test_python_file_passes(self) -> None:
        f = FileFilter()
        assert f.should_review(Path("src/main.py")) is True

    def test_binary_file_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("assets/logo.png")) == ExcludeReason.BINARY

    def test_non_code_extension_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("README.md")) == ExcludeReason.EXTENSION

    def test_user_exclude_pattern(self) -> None:
        f = FileFilter(user_excludes=["migrations/"])
        assert f.why_excluded(Path("src/migrations/001.py")) == ExcludeReason.USER_EXCLUDE

    def test_user_include_overrides_exclude(self) -> None:
        f = FileFilter(
            user_excludes=["migrations/"],
            user_includes=["migrations/important.py"],
        )
        assert f.should_review(Path("src/migrations/important.py")) is True

    def test_default_path_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("node_modules/lib/index.js")) == ExcludeReason.DEFAULT_PATH

    def test_vendor_dir_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("vendor/pkg/lib.go")) == ExcludeReason.DEFAULT_PATH

    def test_generated_dir_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("generated/proto.py")) == ExcludeReason.DEFAULT_PATH

    def test_custom_extensions(self) -> None:
        f = FileFilter(allowed_extensions={".py"})
        assert f.should_review(Path("src/app.py")) is True
        assert f.why_excluded(Path("src/app.js")) == ExcludeReason.EXTENSION

    def test_nested_source_file_passes(self) -> None:
        f = FileFilter()
        assert f.should_review(Path("src/deep/nested/module/file.py")) is True

    def test_pycache_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("src/__pycache__/module.cpython-39.py")) == ExcludeReason.DEFAULT_PATH

    def test_git_dir_excluded(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path(".git/hooks/post-commit")) == ExcludeReason.DEFAULT_PATH

    def test_why_excluded_returns_none_for_valid(self) -> None:
        f = FileFilter()
        assert f.why_excluded(Path("src/app.py")) == ExcludeReason.NONE
