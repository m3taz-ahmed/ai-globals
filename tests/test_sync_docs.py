"""Tests for scripts/sync_docs.py — docs <-> reality sync."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "sync_docs", Path(__file__).resolve().parent.parent / "scripts" / "sync_docs.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_sync_docs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_sync_docs)

build_numbered_section = _sync_docs.build_numbered_section
describe_workflow = _sync_docs.describe_workflow
gather_counts = _sync_docs.gather_counts
rebuild_readme = _sync_docs.rebuild_readme
sync = _sync_docs.sync
_substitute_counts = _sync_docs._substitute_counts


@pytest.fixture
def mini_root(tmp_path: Path) -> Path:
    """Minimal aiZee-shaped tree for sync_docs tests."""
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "runtime" / "kernel.py").write_text("", encoding="utf-8")
    (tmp_path / "runtime" / "policy.py").write_text("", encoding="utf-8")

    skill_dir = tmp_path / "skills" / "alpha"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: alpha\n---\n", encoding="utf-8")
    (tmp_path / "skills" / "beta.md").write_text("---\nname: beta\n---\n", encoding="utf-8")

    wf = tmp_path / "workflows"
    wf.mkdir()
    (wf / "00-legacy.md").write_text(
        "[WORKFLOW] 00-legacy\n[OBJ] Legacy format purpose.\n[TRIGGER] legacy, alt-trigger\n[RULES]\n",
        encoding="utf-8",
    )
    (wf / "01-frontmatter.md").write_text(
        "---\nname: 01-frontmatter\ntrigger: yaml trigger, second\n---\n"
        "# Workflow 01\n\n> **Trigger:** quoted block to skip\n\nFrontmatter purpose text.\n",
        encoding="utf-8",
    )
    (wf / "README.md").write_text(
        "# Workflows\n\n"
        "## Numbered Workflows (Trigger-Based)\n\n"
        "stale content\n\n"
        "## Standards & Reference Files\n\n"
        "| File | Purpose |\n|---|---|\n",
        encoding="utf-8",
    )

    ts = tmp_path / "tech-stack"
    ts.mkdir()
    (ts / "laravel-11.md").write_text("x", encoding="utf-8")
    (ts / "spec-driven-templates").mkdir()

    (tmp_path / "AGENTS.md").write_text(
        "# aiZee\n- **Runtime Modules** - 88 governance modules in `runtime/`.\n"
        "- skills/ # 66 persona + lord skills\n"
        "- workflows/ # 30 trigger-based execution protocols\n"
        "- tech-stack/ # 162 version-locked stack references\n",
        encoding="utf-8",
    )
    return tmp_path


class TestGatherCounts:
    def test_counts_match_tree(self, mini_root: Path) -> None:
        counts = gather_counts(mini_root)
        assert counts["runtime"] == 2  # __init__.py excluded
        assert counts["skills"] == 2  # dir + flat
        assert counts["numbered"] == 2
        assert counts["stack"] == 1


class TestDescribeWorkflow:
    def test_legacy_format(self, mini_root: Path) -> None:
        trigger, purpose = describe_workflow(mini_root / "workflows" / "00-legacy.md")
        assert trigger == "legacy"
        assert purpose == "Legacy format purpose."

    def test_frontmatter_skips_blockquote(self, mini_root: Path) -> None:
        trigger, purpose = describe_workflow(mini_root / "workflows" / "01-frontmatter.md")
        assert trigger == "yaml trigger"
        assert purpose == "Frontmatter purpose text."


class TestSync:
    def test_updates_stale_counts(self, mini_root: Path) -> None:
        sync(mini_root)
        agents = (mini_root / "AGENTS.md").read_text(encoding="utf-8")
        assert "2 governance modules" in agents
        assert "88 governance modules" not in agents
        assert "2 persona + lord skills" in agents
        assert "1 version-locked stack references" in agents

    def test_readme_lists_every_workflow_once(self, mini_root: Path) -> None:
        sync(mini_root)
        readme = (mini_root / "workflows" / "README.md").read_text(encoding="utf-8")
        assert readme.count("`00-legacy.md`") == 1
        assert readme.count("`01-frontmatter.md`") == 1
        # Exactly one table header in the numbered section.
        numbered = readme.split("## Numbered Workflows")[1].split("## Standards")[0]
        assert numbered.count("| Trigger / Task Type |") == 1

    def test_idempotent(self, mini_root: Path) -> None:
        first = sync(mini_root)
        assert any(first.values())
        second = sync(mini_root)
        assert not any(second.values())

    def test_section_builder_row_count(self, mini_root: Path) -> None:
        section = build_numbered_section(
            gather_counts(mini_root),
            sorted((mini_root / "workflows").glob("0*.md")),
        )
        rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line]
        assert len(rows) == 3  # header + 2 workflows

    def test_rebuild_noop_without_section(self, mini_root: Path) -> None:
        """READMEs lacking the numbered section are returned unchanged."""
        readme = mini_root / "workflows" / "README.md"
        readme.write_text("# Just a title\n", encoding="utf-8")
        assert rebuild_readme(mini_root, gather_counts(mini_root)) == "# Just a title\n"


class TestBadgeSync:
    """Badge URL/alt-text sync — must update badges but NOT historical prose."""

    def test_updates_english_badge_urls(self) -> None:
        counts = {"runtime": 85, "skills": 72, "numbered": 36, "workflows_total": 50, "stack": 163, "tests": 3561}
        text = 'Workflows-50-0EA5E9" alt="50 Workflows"> Tests-4028%20passed'
        out = _substitute_counts(text, counts)
        assert "Workflows-36-0EA5E9" in out
        assert 'alt="36 Workflows"' in out
        assert "Tests-3561%20passed" in out

    def test_updates_arabic_badge_urls(self) -> None:
        counts = {"runtime": 85, "skills": 72, "numbered": 36, "workflows_total": 50, "stack": 163, "tests": 3561}
        text = '%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-50-0EA5E9" alt="50 سير عمل">'
        out = _substitute_counts(text, counts)
        assert "%D8%B3%D9%8A%D8%B1_%D8%A7%D9%84%D8%B9%D9%85%D9%84-36-0EA5E9" in out
        assert 'alt="36 سير عمل"' in out

    def test_preserves_historical_prose_arabic(self) -> None:
        """Historical What's New prose must NOT be touched by badge sync."""
        counts = {"runtime": 85, "skills": 72, "numbered": 36, "workflows_total": 50, "stack": 163, "tests": 3561}
        text = (
            "- **2 مهارة محدّثة**: backend-frameworks-lord\n"
            "- **3 سير عمل جديد**: 24-laravel-architecture-setup\n"
            "- **982 اختبار ناجح**، تغطية 97%، 0 فشل\n"
            "- **2773 اختبار ناجح**، تغطية 97%، 0 فشل\n"
        )
        out = _substitute_counts(text, counts)
        assert "2 مهارة محدّثة" in out
        assert "3 سير عمل جديد" in out
        assert "982 اختبار ناجح" in out
        assert "2773 اختبار ناجح" in out
        # Must NOT inject current counts into historical prose.
        assert "72 مهارة محدّثة" not in out
        assert "36 سير عمل جديد" not in out
        assert "3561 اختبار ناجح**، تغطية 97%" not in out

    def test_preserves_historical_prose_english(self) -> None:
        counts = {"runtime": 85, "skills": 72, "numbered": 36, "workflows_total": 50, "stack": 163, "tests": 3561}
        text = "- **2 skills updated** and **3 new workflows** added in v5.3.0.\n"
        out = _substitute_counts(text, counts)
        assert "2 skills updated" in out
        assert "3 new workflows" in out

    def test_skips_badge_sync_when_tests_none(self) -> None:
        """When tests count is None (collection failed), tests badges stay unchanged."""
        counts: dict[str, int | None] = {"runtime": 85, "skills": 72, "numbered": 36, "workflows_total": 50, "stack": 163, "tests": None}
        text = 'Tests-4028%20passed" alt="Tests: 4028 passed">'
        out = _substitute_counts(text, counts)
        # Tests badge must NOT be rewritten (tests key missing from safe_counts).
        assert "Tests-4028%20passed" in out
        assert "Tests: 4028 passed" in out
        # But workflows/skills badges still sync (their keys are present).
        wf_text = 'Workflows-50-0EA5E9" alt="50 Workflows">'
        wf_out = _substitute_counts(wf_text, counts)
        assert "Workflows-36-0EA5E9" in wf_out
