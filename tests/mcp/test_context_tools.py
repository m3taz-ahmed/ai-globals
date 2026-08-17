"""Tests for aizee_mcp/tools/context_tools.py — context discovery MCP tools."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp.server.fastmcp import FastMCP

# Set up isolated root BEFORE importing
_ROOT = tempfile.mkdtemp(prefix="aios_ctx_test_")
os.environ["AIZEE_ROOT"] = _ROOT
ROOT = Path(_ROOT)
for sub in ("tech-stack", "skills", "skills/python", "state", "brain"):
    (ROOT / sub).mkdir(parents=True, exist_ok=True)

# Create test files
(ROOT / "CHANGELOG.md").write_text(
    "# Changelog\n\n"
    "## [Unreleased]\n"
    "### Added\n"
    "- New feature A\n"
    "- New feature B\n\n"
    "## [1.0.0] - 2024-01-01\n"
    "### Fixed\n"
    "- Bug fix X\n",
    encoding="utf-8",
)
(ROOT / "ACTIVE_CONTEXT.md").write_text(
    "# Active Context\n\nCurrent task: testing.\n",
    encoding="utf-8",
)
(ROOT / "AGENTS.md").write_text(
    "# AGENTS\n\naiZee bootloader.\n",
    encoding="utf-8",
)
(ROOT / "tech-stack" / "react-18.md").write_text(
    "# React 18\nHooks and concurrent rendering.\n",
    encoding="utf-8",
)
(ROOT / "skills" / "python" / "testing.md").write_text(
    '---\ndescription: "Python testing skills"\n---\n'
    "# Python Testing\nUse pytest for testing Python code.\n",
    encoding="utf-8",
)
(ROOT / "skills" / "debugging.md").write_text(
    "# Debugging\nGeneral debugging techniques.\n",
    encoding="utf-8",
)

from aizee_mcp.tools.common import reset_state  # noqa: E402
from aizee_mcp.tools.context_tools import register_context_tools  # noqa: E402

# Build a dedicated FastMCP with only context tools
_mcp = FastMCP("test-context")
register_context_tools(_mcp)


def _call(name: str, arguments: dict) -> str:
    os.environ["AIZEE_ROOT"] = _ROOT
    reset_state()
    return _mcp._tool_manager.get_tool(name).fn(**arguments)


class TestGetTechStack:
    def test_existing_package(self):
        result = _call("get_tech_stack", {"pkg": "react", "ver": "18"})
        data = json.loads(result)
        assert data["exists"] is True
        assert "React 18" in data["content"]

    def test_missing_package(self):
        result = _call("get_tech_stack", {"pkg": "nonexistent", "ver": "1.0"})
        data = json.loads(result)
        assert data["exists"] is False

    def test_invalid_package_name(self):
        result = _call("get_tech_stack", {"pkg": "../etc/passwd", "ver": "1.0"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_invalid_version_name(self):
        result = _call("get_tech_stack", {"pkg": "react", "ver": "../../etc"})
        data = json.loads(result)
        assert data["ok"] is False

    def test_resolve_path_returns_none(self):
        """Cover line 33: resolve_path returns None for valid names."""
        with patch("aizee_mcp.tools.context_tools.resolve_path", return_value=None):
            result = _call("get_tech_stack", {"pkg": "react", "ver": "18"})
            data = json.loads(result)
            assert data["ok"] is False
            assert "Invalid path" in data["error"]


class TestSearchSkills:
    def test_search_finds_matching_skill(self):
        """Cover lines 41-67: search_skills with matching query."""
        result = _call("search_skills", {"query": "pytest"})
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any("testing" in item["name"] for item in data)

    def test_search_with_description(self):
        """Cover line 62: extract description from frontmatter."""
        result = _call("search_skills", {"query": "testing"})
        data = json.loads(result)
        # The python/testing.md skill has a description
        testing_results = [r for r in data if "testing" in r.get("name", "")]
        if testing_results:
            assert testing_results[0]["description"] != ""

    def test_search_no_match(self):
        result = _call("search_skills", {"query": "nonexistent_xyz_999"})
        data = json.loads(result)
        assert data == []

    def test_search_invalid_query(self):
        """Cover line 42-43: validate_query rejects invalid input."""
        result = _call("search_skills", {"query": ""})
        data = json.loads(result)
        assert data["ok"] is False

    def test_search_with_limit(self):
        """Cover line 65: limit truncates results."""
        result = _call("search_skills", {"query": "debug", "limit": 1})
        data = json.loads(result)
        assert len(data) <= 1

    def test_search_no_skills_dir(self):
        """Cover line 50: return empty list when skills dir missing."""
        # Point root to a temp dir without skills/
        tmp_root = tempfile.mkdtemp(prefix="aios_no_skills_")
        os.environ["AIZEE_ROOT"] = tmp_root
        reset_state()
        result = _mcp._tool_manager.get_tool("search_skills").fn(query="anything")
        data = json.loads(result)
        assert data == []
        # Restore
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()

    def test_search_oserror_on_read(self):
        """Cover line 55: OSError during file read is skipped."""
        with patch("pathlib.Path.read_text", side_effect=OSError("read error")):
            result = _call("search_skills", {"query": "testing"})
            data = json.loads(result)
            assert data == []


class TestGetChangelog:
    def test_unreleased_section(self):
        """Cover lines 72-100: get_changelog with unreleased section."""
        result = _call("get_changelog", {"section": "unreleased"})
        data = json.loads(result)
        assert data["ok"] is True
        assert data["section"] == "unreleased"
        assert "New feature" in data["content"]

    def test_latest_section(self):
        """Cover lines 90-92: get_changelog with latest section."""
        result = _call("get_changelog", {"section": "latest"})
        data = json.loads(result)
        assert data["ok"] is True
        assert data["section"] == "latest"
        assert "Bug fix" in data["content"]

    def test_full_section(self):
        """Cover line 79-80: get_changelog with full section."""
        result = _call("get_changelog", {"section": "full"})
        data = json.loads(result)
        assert data["ok"] is True
        assert "Changelog" in data["content"]

    def test_invalid_section(self):
        """Cover line 73: invalid section name."""
        result = _call("get_changelog", {"section": "invalid"})
        data = json.loads(result)
        assert data["ok"] is False
        assert "section must be" in data["error"]

    def test_changelog_not_found(self):
        """Cover line 77: CHANGELOG.md missing."""
        tmp_root = tempfile.mkdtemp(prefix="aios_no_cl_")
        os.environ["AIZEE_ROOT"] = tmp_root
        reset_state()
        result = _mcp._tool_manager.get_tool("get_changelog").fn(section="unreleased")
        data = json.loads(result)
        assert data["ok"] is False
        assert "not found" in data["error"]
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()

    def test_unreleased_section_break(self):
        """Cover lines 94-96: break when next section found while capturing."""
        # The changelog has [Unreleased] then [1.0.0], so capturing should break
        # at [1.0.0] section header
        result = _call("get_changelog", {"section": "unreleased"})
        data = json.loads(result)
        assert data["ok"] is True
        # Should NOT contain content from [1.0.0] section
        assert "Bug fix" not in data["content"]


class TestGetActiveContext:
    def test_existing_active_context(self):
        """Cover lines 105-109: get_active_context with existing file."""
        result = _call("get_active_context", {})
        data = json.loads(result)
        assert data["ok"] is True
        assert "Active Context" in data["content"]

    def test_missing_active_context(self):
        """Cover line 108: ACTIVE_CONTEXT.md not found."""
        tmp_root = tempfile.mkdtemp(prefix="aios_no_ac_")
        os.environ["AIZEE_ROOT"] = tmp_root
        reset_state()
        result = _mcp._tool_manager.get_tool("get_active_context").fn()
        data = json.loads(result)
        assert data["ok"] is False
        assert "not found" in data["error"]
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()


class TestGetAgents:
    def test_existing_agents(self):
        """Cover lines 113-115: get_agents resource with existing file."""
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
        # Get the resource function directly
        resources = _mcp._resource_manager._resources
        agents_fn = None
        for r in resources.values():
            if "AGENTS" in str(r.uri):
                agents_fn = r.fn
                break
        assert agents_fn is not None
        result = agents_fn()
        assert "aiZee" in result

    def test_missing_agents(self):
        """Cover line 115: get_agents returns empty string when file missing."""
        tmp_root = tempfile.mkdtemp(prefix="aios_no_agents_")
        os.environ["AIZEE_ROOT"] = tmp_root
        reset_state()
        resources = _mcp._resource_manager._resources
        agents_fn = None
        for r in resources.values():
            if "AGENTS" in str(r.uri):
                agents_fn = r.fn
                break
        assert agents_fn is not None
        result = agents_fn()
        assert result == ""
        os.environ["AIZEE_ROOT"] = _ROOT
        reset_state()
