"""Tests for aios_mcp/tools/common.py helper functions."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Set up isolated root BEFORE importing the module
os.environ["AGENT_OS_ROOT"] = tempfile.mkdtemp(prefix="aios_common_test_")
ROOT = Path(os.environ["AGENT_OS_ROOT"])
(ROOT / "brain").mkdir(parents=True, exist_ok=True)

from aios_mcp.tools.common import (  # noqa: E402
    is_safe_name,
    kernel,
    memory,
    reset_state,
    resolve_path,
    root,
    truncate,
    validate_kind,
    validate_query,
)


class TestIsSafeName:
    def test_valid_name(self):
        assert is_safe_name("core") is True

    def test_valid_name_with_dots(self):
        assert is_safe_name("my.rule.v2") is True

    def test_empty_name(self):
        assert is_safe_name("") is False

    def test_parent_dir_ref(self):
        assert is_safe_name("..") is False

    def test_slash_in_name(self):
        assert is_safe_name("a/b") is False

    def test_backslash_in_name(self):
        assert is_safe_name("a\\b") is False

    def test_overlong_name(self):
        assert is_safe_name("a" * 129) is False

    def test_control_char(self):
        """Cover line 65: reject control characters."""
        assert is_safe_name("a\x01b") is False

    def test_del_char(self):
        """Cover line 65: reject DEL (0x7f) character."""
        assert is_safe_name("a\x7fb") is False


class TestResolvePath:
    def test_valid_relative_path(self):
        target = resolve_path(ROOT, Path("rules/core.md"))
        assert target is not None

    def test_parent_dir_in_parts(self):
        """resolve_path returns None for paths containing '..'."""
        result = resolve_path(ROOT, Path("../etc/passwd"))
        assert result is None

    def test_unc_path(self):
        """Cover line 74: reject UNC paths starting with \\\\."""
        result = resolve_path(ROOT, Path("\\\\server\\share"))
        assert result is None

    def test_double_slash_path(self):
        """Cover line 74: reject paths starting with //."""
        result = resolve_path(ROOT, Path("//server/share"))
        assert result is None

    def test_resolution_exception_returns_none(self, tmp_path):
        """Cover lines 79-80: ValueError during resolution returns None."""
        from unittest.mock import patch

        root_dir = tmp_path / "root"
        root_dir.mkdir()
        (root_dir / "safe.txt").write_text("ok")

        # Force relative_to to raise ValueError to simulate path escaping root
        with patch.object(Path, "relative_to", side_effect=ValueError("not under root")):
            result = resolve_path(root_dir, Path("safe.txt"))
            assert result is None


class TestTruncate:
    def test_short_content(self):
        assert truncate("hello") == "hello"

    def test_long_content(self):
        long = "x" * 600
        result = truncate(long, limit=500)
        assert len(result) == 503  # 500 + "..."
        assert result.endswith("...")

    def test_exact_limit(self):
        assert truncate("x" * 500, limit=500) == "x" * 500


class TestValidateQuery:
    def test_valid_query(self):
        assert validate_query("search term") is None

    def test_empty_query(self):
        """Cover line 93: empty query returns error JSON."""
        result = validate_query("")
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid query" in data["error"]

    def test_non_string_query(self):
        """Cover line 93: non-string query returns error JSON."""
        result = validate_query(123)  # type: ignore[arg-type]
        data = json.loads(result)
        assert data["ok"] is False

    def test_overlong_query(self):
        """Cover line 93: overlong query returns error JSON."""
        result = validate_query("x" * 100_001)
        data = json.loads(result)
        assert data["ok"] is False


class TestValidateKind:
    def test_none_kind(self):
        assert validate_kind(None) is None

    def test_valid_kind(self):
        assert validate_kind("semantic") is None

    def test_invalid_kind(self):
        """Cover line 102: unsafe kind name returns error JSON."""
        result = validate_kind("../etc")
        data = json.loads(result)
        assert data["ok"] is False
        assert "Invalid kind" in data["error"]


class TestInfrastructure:
    """Cover root(), reset_state(), kernel(), memory() functions."""

    def test_root_returns_path(self):
        """Cover line 28: root() returns discovered root."""
        result = root()
        assert isinstance(result, Path)

    def test_reset_state(self):
        """Cover lines 34-36: reset_state clears cached instances."""
        reset_state()
        # Verify it doesn't raise and clears state
        from aios_mcp.tools import common as common_mod

        assert common_mod._kernel_instance is None
        assert common_mod._memory_instance is None
        assert common_mod._current_root is None

    def test_kernel_returns_instance(self):
        """Cover lines 42-47: kernel() creates and caches Kernel."""
        reset_state()
        from unittest.mock import MagicMock

        mock_k = MagicMock()
        with patch("aios_mcp.tools.common.Kernel", return_value=mock_k):
            k1 = kernel()
            assert k1 is mock_k
            # Second call should return cached instance
            k2 = kernel()
            assert k2 is mock_k

    def test_kernel_recreates_on_root_change(self):
        """Cover lines 44-46: kernel recreates when root changes."""
        reset_state()
        from unittest.mock import MagicMock

        mock_k1 = MagicMock()
        mock_k2 = MagicMock()
        with patch("aios_mcp.tools.common.Kernel", side_effect=[mock_k1, mock_k2]):
            k1 = kernel()
            assert k1 is mock_k1
            # Change root to force recreation
            with patch("aios_mcp.tools.common.root", return_value=Path("/different/root")):
                k2 = kernel()
                assert k2 is mock_k2

    def test_memory_returns_instance(self):
        """Cover lines 53-57: memory() creates and caches MemoryStore."""
        reset_state()
        from unittest.mock import MagicMock

        mock_m = MagicMock()
        mock_m.root = ROOT
        with patch("aios_mcp.tools.common.MemoryStore", return_value=mock_m):
            m1 = memory()
            assert m1 is mock_m
            # Second call should return cached instance
            m2 = memory()
            assert m2 is mock_m

    def test_memory_recreates_on_root_change(self):
        """Cover lines 55-56: memory recreates when root changes."""
        reset_state()
        from unittest.mock import MagicMock

        mock_m1 = MagicMock()
        mock_m1.root = ROOT
        mock_m2 = MagicMock()
        mock_m2.root = Path("/different/root")
        with patch("aios_mcp.tools.common.MemoryStore", side_effect=[mock_m1, mock_m2]):
            m1 = memory()
            assert m1 is mock_m1
            # Change root to force recreation
            with patch("aios_mcp.tools.common.root", return_value=Path("/different/root")):
                m2 = memory()
                assert m2 is mock_m2
