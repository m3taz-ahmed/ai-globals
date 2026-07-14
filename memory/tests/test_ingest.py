"""Comprehensive tests for memory/ingest.py."""

from __future__ import annotations

import json
import tempfile
import warnings
from pathlib import Path

import pytest

from memory.ingest import _AI_TITLE_TAGS, Ingestor
from memory.store import MemoryStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="aios_ingest_"))


def _store(tmp: Path) -> MemoryStore:
    return MemoryStore(tmp, tmp / "memory.db", enable_vector=False)


def _ingestor(tmp: Path) -> Ingestor:
    return Ingestor(_store(tmp), tmp)


def _mkdir(root: Path, *parts: str) -> Path:
    p = root.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# _sig
# ---------------------------------------------------------------------------

class TestSig:
    def test_sig_is_sha256_hex(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        sig = ing._sig("hello world")
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_sig_same_content_same_hash(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        assert ing._sig("test") == ing._sig("test")

    def test_sig_different_content_different_hash(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        assert ing._sig("aaa") != ing._sig("bbb")


# ---------------------------------------------------------------------------
# _body_after_frontmatter
# ---------------------------------------------------------------------------

class TestBodyAfterFrontmatter:
    def test_strips_yaml_frontmatter(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "---\nname: foo\n---\n[FILE] body here"
        body = ing._body_after_frontmatter(content)
        assert "[FILE]" in body
        assert "name: foo" not in body

    def test_no_frontmatter_returns_content_as_is(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "[FILE] no frontmatter"
        assert ing._body_after_frontmatter(content) == content

    def test_incomplete_frontmatter_returns_content(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "---\nnot closed"
        assert ing._body_after_frontmatter(content) == content

    def test_frontmatter_without_name_key_returns_content(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "---\ntitle: no name key\n---\nbody"
        # Since 'name:' not in parts[1], returns original content
        assert ing._body_after_frontmatter(content) == content


# ---------------------------------------------------------------------------
# _is_ai_file / _validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_non_ai_file_always_valid(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        # Normal markdown file
        assert ing._validate("# Just a normal README", "docs/readme.md") is True

    def test_ai_file_with_obj_and_rules_valid(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "[FILE] core\n[OBJ] Description\n[RULES]\n1. [REQ] Rule one."
        assert ing._validate(content, "rules/core.md") is True

    @pytest.mark.parametrize("tag", list(_AI_TITLE_TAGS))
    def test_ai_file_missing_obj_is_invalid(self, tmp_path: Path, tag: str):
        ing = _ingestor(tmp_path)
        # Has [RULES] but no [OBJ]
        content = f"{tag} something\n[RULES]\n1. [REQ] Rule."
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = ing._validate(content, "rules/bad.md")
        assert result is False
        assert any("missing" in str(warning.message).lower() for warning in w)

    @pytest.mark.parametrize("tag", list(_AI_TITLE_TAGS))
    def test_ai_file_missing_rules_is_invalid(self, tmp_path: Path, tag: str):
        ing = _ingestor(tmp_path)
        # Has [OBJ] but no [RULES]
        content = f"{tag} something\n[OBJ] Description"
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            result = ing._validate(content, "rules/bad.md")
        assert result is False

    def test_ai_file_with_frontmatter_valid(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "---\nname: myskill\n---\n[SKILL] myskill\n[OBJ] Does things.\n[RULES]\n1. [REQ] Do this."
        assert ing._validate(content, "skills/myskill.md") is True


# ---------------------------------------------------------------------------
# _collect_dir
# ---------------------------------------------------------------------------

class TestCollectDir:
    def test_missing_directory_returns_empty(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        to_add, new_sigs, current = ing._collect_dir("nonexistent", "factual", False, {})
        assert to_add == []
        assert new_sigs == {}
        assert current == set()

    def test_new_file_is_collected(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        (rules_dir / "core.md").write_text("# Core Rules\nContent here.")
        to_add, _, current = ing._collect_dir("rules", "semantic", False, {})
        assert len(to_add) == 1
        assert to_add[0].kind == "semantic"
        assert "rules/core.md" in current

    def test_unchanged_file_not_re_added(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        content = "# Core Rules\nContent here."
        (rules_dir / "core.md").write_text(content)
        sig = ing._sig(content)
        manifest = {"rules/core.md": sig}
        to_add, _, _ = ing._collect_dir("rules", "semantic", False, manifest)
        assert to_add == []

    def test_changed_file_re_added(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        (rules_dir / "core.md").write_text("# Updated content")
        manifest = {"rules/core.md": "old_sha256_hash"}
        to_add, _, _ = ing._collect_dir("rules", "semantic", False, manifest)
        assert len(to_add) == 1

    def test_recursive_collects_nested_files(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        skills_dir = _mkdir(tmp_path, "skills", "nested")
        (skills_dir / "skill.md").write_text("# Skill\nContent.")
        to_add, _, current = ing._collect_dir("skills", "procedural", True, {})
        assert len(to_add) == 1
        assert any("nested/skill.md" in s for s in current)

    def test_malformed_ai_file_skipped(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        # Valid AI file
        (rules_dir / "good.md").write_text("[FILE] good\n[OBJ] desc\n[RULES]\n1. [REQ] rule.")
        # Malformed AI file (missing [OBJ])
        (rules_dir / "bad.md").write_text("[FILE] bad\n[RULES]\n1. [REQ] rule.")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            to_add, _, current = ing._collect_dir("rules", "semantic", False, {})
        assert len(to_add) == 1
        assert to_add[0].source == "rules/good.md"
        # Malformed file is NOT in current_sources
        assert "rules/bad.md" not in current


# ---------------------------------------------------------------------------
# _collect_agents
# ---------------------------------------------------------------------------

class TestCollectAgents:
    def test_no_agents_file_returns_empty(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        to_add, new_sigs, current = ing._collect_agents({})
        assert to_add == []
        assert new_sigs == {}
        assert current == set()

    def test_new_agents_file_collected(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Agents\nCross-tool rules.")
        to_add, _, current = ing._collect_agents({})
        assert len(to_add) == 1
        assert to_add[0].kind == "episodic"
        assert "AGENTS.md" in current

    def test_unchanged_agents_not_re_collected(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        content = "# Agents\nCross-tool rules."
        (tmp_path / "AGENTS.md").write_text(content)
        sig = ing._sig(content)
        to_add, _, _ = ing._collect_agents({"AGENTS.md": sig})
        assert to_add == []

    def test_changed_agents_re_collected(self, tmp_path: Path):
        ing = _ingestor(tmp_path)
        (tmp_path / "AGENTS.md").write_text("# Updated AGENTS content.")
        to_add, _, _ = ing._collect_agents({"AGENTS.md": "old_hash"})
        assert len(to_add) == 1


# ---------------------------------------------------------------------------
# ingest_all — full flow
# ---------------------------------------------------------------------------

class TestIngestAll:
    def test_ingest_all_returns_ids(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        (rules_dir / "core.md").write_text("# Core\nSome rules.")
        ids = ing.ingest_all()
        assert len(ids) == 1

    def test_ingest_all_idempotent(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        (rules_dir / "core.md").write_text("# Core\nSome rules.")
        ids1 = ing.ingest_all()
        ids2 = ing.ingest_all()  # second run — same content
        assert len(ids1) == 1
        assert len(ids2) == 0  # nothing changed, nothing re-ingested

    def test_ingest_all_tracks_agents_md(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        (tmp_path / "AGENTS.md").write_text("# AGENTS\nSystem instructions.")
        ids = ing.ingest_all()
        assert len(ids) == 1

    def test_ingest_all_removes_deleted_sources(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        rules_file = rules_dir / "temp.md"
        rules_file.write_text("# Temp rule.")
        ids = ing.ingest_all()
        assert len(ids) == 1
        # Delete the file, re-ingest
        rules_file.unlink()
        ing.ingest_all()
        # Memory should be removed from store
        assert store.search("Temp rule") == []

    def test_ingest_all_manifest_persisted(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        (rules_dir / "rule.md").write_text("# Rule")
        ing.ingest_all()
        assert (tmp_path / "brain" / "ingest_manifest.json").exists()
        manifest = json.loads((tmp_path / "brain" / "ingest_manifest.json").read_text())
        assert "rules/rule.md" in manifest

    def test_ingest_all_skills_recursive(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        skill_dir = _mkdir(tmp_path, "skills", "my-skill")
        (skill_dir / "SKILL.md").write_text("# Skill content")
        ids = ing.ingest_all()
        assert len(ids) == 1

    def test_ingest_all_tech_stack_kind_is_factual(self, tmp_path: Path):
        store = _store(tmp_path)
        ing = Ingestor(store, tmp_path)
        ts_dir = _mkdir(tmp_path, "tech-stack")
        (ts_dir / "laravel-11.md").write_text("# Laravel 11 Notes")
        ing.ingest_all()
        results = store.search("Laravel 11", kind="factual")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# _collect_dir — non-file entry (line 104: directory inside glob result)
# ---------------------------------------------------------------------------

class TestCollectDirNonFileSkip:
    def test_non_file_glob_entry_is_skipped(self, tmp_path: Path):
        """Line 104: `if not p.is_file(): continue` — cover by having a dir inside."""
        ing = _ingestor(tmp_path)
        rules_dir = _mkdir(tmp_path, "rules")
        # A subdirectory inside rules/ — non-recursive mode means glob yields it but it's not a file
        _mkdir(tmp_path, "rules", "subdir")
        (rules_dir / "valid.md").write_text("# Rule\nContent.")
        to_add, _, __ = ing._collect_dir("rules", "semantic", False, {})
        # Only valid.md should be collected; subdir should be silently skipped
        assert len(to_add) == 1
        assert to_add[0].source == "rules/valid.md"


# ---------------------------------------------------------------------------
# _collect_agents — malformed AGENTS.md (line 126)
# ---------------------------------------------------------------------------

class TestCollectAgentsMalformed:
    def test_malformed_agents_md_is_skipped(self, tmp_path: Path):
        """Line 126: AGENTS.md fails validation → return [], {}, set()."""
        ing = _ingestor(tmp_path)
        # Create an AGENTS.md that looks like an AI file but is missing [OBJ]
        (tmp_path / "AGENTS.md").write_text("[FILE] agents\n[RULES]\n1. [REQ] Rule.")
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            to_add, new_sigs, current = ing._collect_agents({})
        assert to_add == []
        assert new_sigs == {}
        assert current == set()

