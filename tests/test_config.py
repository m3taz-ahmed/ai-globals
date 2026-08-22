"""Tests for config.py — root discovery and version parsing."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

import config as config_mod


class TestDiscoverRoot:
    """Tests for config.discover_root()."""

    def test_uses_agent_os_root_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        assert config_mod.discover_root() == tmp_path.resolve()

    def test_falls_back_to_config_parent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AIZEE_ROOT", raising=False)
        result = config_mod.discover_root()
        assert result == Path(config_mod.__file__).resolve().parent

    def test_raises_on_nonexistent_env_dir(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AIZEE_ROOT", "/nonexistent/path/that/should/not/exist")
        with pytest.raises(ValueError, match="AIZEE_ROOT"):
            config_mod.discover_root()

    def test_resolves_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AIZEE_ROOT", ".")
        result = config_mod.discover_root()
        assert result == tmp_path.resolve()


class TestDiscoverProjectRoot:
    """Tests for config.discover_project_root()."""

    def test_uses_agent_project_root_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AGENT_PROJECT_ROOT", str(tmp_path))
        result = config_mod.discover_project_root()
        assert result == tmp_path.resolve()

    def test_falls_back_to_agent_os_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.setenv("AIZEE_ROOT", str(tmp_path))
        result = config_mod.discover_project_root()
        assert result == tmp_path.resolve()

    def test_falls_back_to_cwd_with_active_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AIZEE_ROOT", raising=False)
        ai_dir = tmp_path / ".ai"
        ai_dir.mkdir()
        (ai_dir / "active-context.md").write_text("test", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        result = config_mod.discover_project_root()
        assert result == tmp_path.resolve()

    def test_falls_back_to_discover_root(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AIZEE_ROOT", raising=False)
        monkeypatch.chdir(Path(config_mod.__file__).resolve().parent)
        result = config_mod.discover_project_root()
        assert result == Path(config_mod.__file__).resolve().parent

    def test_raises_on_nonexistent_project_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("AGENT_PROJECT_ROOT", "/nonexistent/project/path")
        with pytest.raises(ValueError, match="AGENT_PROJECT_ROOT"):
            config_mod.discover_project_root()


class TestVersion:
    """Tests for config._version() and VERSION constant."""

    def test_version_is_string(self) -> None:
        assert isinstance(config_mod.VERSION, str)
        assert len(config_mod.VERSION) > 0

    def test_version_format(self) -> None:
        # Should match semver-like pattern (e.g. "4.22.0")
        parts = config_mod.VERSION.split(".")
        assert len(parts) >= 2
        for part in parts:
            assert part.isdigit() or any(c.isdigit() for c in part)

    def test_version_reads_from_pyproject(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Create a fake pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nversion = "9.9.9"\n', encoding="utf-8"
        )
        # Mock __file__ to point to tmp_path
        with mock.patch.object(config_mod, "__file__", str(tmp_path / "config.py")):
            assert config_mod._version() == "9.9.9"

    def test_version_defaults_when_no_pyproject(self, tmp_path: Path) -> None:
        with mock.patch.object(config_mod, "__file__", str(tmp_path / "config.py")):
            result = config_mod._version()
            assert result == "5.0.0"


class TestResolveEnvDir:
    """Tests for config._resolve_env_dir()."""

    def test_returns_env_path_when_dir_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_VAR", str(tmp_path))
        result = config_mod._resolve_env_dir("TEST_VAR", Path("/fallback"))
        assert result == tmp_path.resolve()

    def test_returns_fallback_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_VAR", raising=False)
        fallback = Path("/some/fallback")
        result = config_mod._resolve_env_dir("TEST_VAR", fallback)
        assert result == fallback

    def test_raises_when_env_dir_does_not_exist(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_VAR", "/nonexistent/xyz")
        with pytest.raises(ValueError, match="TEST_VAR"):
            config_mod._resolve_env_dir("TEST_VAR", Path("/fallback"))


class TestDiscoverProjectRootCwdFallback:
    """Test line 39: the cwd fallback in discover_project_root."""

    def test_cwd_without_active_context_falls_back_to_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Line 39: when cwd has no .ai/active-context.md, falls back to discover_root()."""
        monkeypatch.delenv("AGENT_PROJECT_ROOT", raising=False)
        monkeypatch.delenv("AIZEE_ROOT", raising=False)
        # Use a temp dir that has no .ai/active-context.md
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="aizee_cfg_test_"))
        monkeypatch.chdir(tmp)
        result = config_mod.discover_project_root()
        # Should fall back to discover_root() which is the config.py parent
        assert result == Path(config_mod.__file__).resolve().parent
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
