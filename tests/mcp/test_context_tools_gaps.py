"""Gap coverage for aizee_mcp/tools/context_tools.py edge paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import aizee_mcp.tools.context_tools as ct

pytestmark = pytest.mark.mcp


class _FakeTool:
    def __call__(self, fn: Any | None = None) -> Any:
        if fn is not None:
            _captured[fn.__name__] = fn
            return fn

        def decorator(inner: Any) -> Any:
            _captured[inner.__name__] = inner
            return inner

        return decorator


class _FakeMCP:
    def __init__(self) -> None:
        self.tool = _FakeTool()

    def resource(self, _uri: str) -> Any:
        return _FakeTool()


_captured: dict[str, Any] = {}
ct.register_context_tools(_FakeMCP())


def _call(name: str, **kwargs: Any) -> Any:
    return _captured[name](**kwargs)


@pytest.fixture()
def root_dir(tmp_path):
    with patch.object(ct, "root", return_value=tmp_path):
        yield tmp_path


# ---------------------------------------------------------------------------
# search_skills
# ---------------------------------------------------------------------------


class TestSearchSkillsGaps:
    def test_bad_limit_defaults(self, root_dir):
        (root_dir / "skills").mkdir()
        (root_dir / "skills" / "a.md").write_text("needle here")
        out = json.loads(_call("search_skills", query="needle", limit="junk"))
        assert len(out) == 1

    def test_scan_cap_breaks_at_500(self, root_dir):
        skills = root_dir / "skills"
        skills.mkdir()
        for i in range(505):
            (skills / f"s{i:03}.md").write_text("needle")
        out = json.loads(_call("search_skills", query="needle"))
        # Scan stopped at 500 files; every scanned file matched
        assert len(out) <= 500

    def test_excluded_dirs_skipped(self, root_dir):
        ref = root_dir / "skills" / "x" / "references"
        ref.mkdir(parents=True)
        (ref / "r.md").write_text("needle")
        out = json.loads(_call("search_skills", query="needle"))
        assert out == []

    def test_folder_skill_named_by_parent(self, root_dir):
        d = root_dir / "skills" / "myskill"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("needle content")
        out = json.loads(_call("search_skills", query="needle"))
        assert out[0]["name"] == "myskill"

    def test_flat_skill_named_by_stem(self, root_dir):
        (root_dir / "skills").mkdir()
        (root_dir / "skills" / "debugging.md").write_text("needle")
        out = json.loads(_call("search_skills", query="needle"))
        assert out[0]["name"] == "debugging"

    def test_oversized_file_skipped(self, root_dir):
        (root_dir / "skills").mkdir()
        (root_dir / "skills" / "big.md").write_text("needle " * 40_000)  # >200KB
        out = json.loads(_call("search_skills", query="needle"))
        assert out == []

    def test_read_error_skipped(self, root_dir):
        (root_dir / "skills").mkdir()
        (root_dir / "skills" / "a.md").write_text("needle")
        with patch.object(Path, "read_text", side_effect=OSError("io")):
            out = json.loads(_call("search_skills", query="needle"))
        assert out == []

    def test_no_description_line(self, root_dir):
        (root_dir / "skills").mkdir()
        (root_dir / "skills" / "a.md").write_text("needle\nmore needle\n")
        out = json.loads(_call("search_skills", query="needle"))
        assert out[0]["description"] == ""

    def test_limit_breaks_results(self, root_dir):
        skills = root_dir / "skills"
        skills.mkdir()
        for i in range(5):
            (skills / f"s{i}.md").write_text("needle")
        out = json.loads(_call("search_skills", query="needle", limit=2))
        assert len(out) == 2

    def test_mixed_matching_and_nonmatching(self, root_dir):
        skills = root_dir / "skills"
        skills.mkdir()
        (skills / "hit.md").write_text("needle")
        (skills / "miss.md").write_text("nothing relevant")
        out = json.loads(_call("search_skills", query="needle"))
        assert len(out) == 1


# ---------------------------------------------------------------------------
# get_changelog
# ---------------------------------------------------------------------------


CHANGELOG = (
    "# Changelog\n"
    "\n"
    "## [Unreleased]\n"
    "### Added\n"
    "- Feature A\n"
    "\n"
    "## [1.2.3] - 2024-05-01\n"
    "### Fixed\n"
    "- Bug B\n"
)


class TestChangelogGaps:
    def _mk(self, root_dir, text: str) -> None:
        (root_dir / "CHANGELOG.md").write_text(text, encoding="utf-8")

    def test_invalid_section(self, root_dir):
        self._mk(root_dir, CHANGELOG)
        out = json.loads(_call("get_changelog", section="bogus"))
        assert out["ok"] is False

    def test_full_section(self, root_dir):
        self._mk(root_dir, CHANGELOG)
        out = json.loads(_call("get_changelog", section="full"))
        assert out["ok"] is True
        assert "Bug B" in out["content"]

    def test_latest_section_captures(self, root_dir):
        self._mk(root_dir, CHANGELOG)
        out = json.loads(_call("get_changelog", section="latest"))
        assert out["ok"] is True
        assert "Bug B" in out["content"]

    def test_unreleased_stops_at_next_header(self, root_dir):
        self._mk(root_dir, CHANGELOG)
        out = json.loads(_call("get_changelog", section="unreleased"))
        assert "Feature A" in out["content"]
        assert "Bug B" not in out["content"]

    def test_latest_skips_unreleased_header(self, root_dir):
        self._mk(root_dir, CHANGELOG)
        out = json.loads(_call("get_changelog", section="latest"))
        assert "[Unreleased]" not in out["content"]
        assert "1.2.3" in out["content"]

    def test_no_matching_section(self, root_dir):
        self._mk(root_dir, "# Changelog\n\n## [1.0.0]\n- x\n")
        out = json.loads(_call("get_changelog", section="unreleased"))
        assert out["ok"] is False

    def test_missing_changelog(self, root_dir):
        out = json.loads(_call("get_changelog", section="full"))
        assert out["ok"] is False


# ---------------------------------------------------------------------------
# get_active_context / get_agents
# ---------------------------------------------------------------------------


class TestActiveContextGaps:
    def test_missing(self, root_dir):
        out = json.loads(_call("get_active_context"))
        assert out["ok"] is False

    def test_present(self, root_dir):
        (root_dir / "ACTIVE_CONTEXT.md").write_text("ctx")
        out = json.loads(_call("get_active_context"))
        assert out["ok"] is True
        assert out["content"] == "ctx"

    def test_agents_present(self, root_dir):
        (root_dir / "AGENTS.md").write_text("agents!")
        assert _call("get_agents") == "agents!"

    def test_agents_missing(self, root_dir):
        assert _call("get_agents") == ""
