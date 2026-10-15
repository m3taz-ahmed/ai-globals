from __future__ import annotations

from pathlib import Path

import pytest

from memory.handoff import (
    ensure_vault_guard,
    list_handoffs,
    new_handoff_id,
    render_handoff,
    scope_root,
    write_handoff,
)


class TestScopeRoot:
    def test_project_returns_root(self, tmp_path: Path) -> None:
        assert scope_root("project", tmp_path) == tmp_path

    def test_user_returns_home_aizee(self, tmp_path: Path) -> None:
        assert scope_root("user", tmp_path) == Path.home() / ".aizee"


class TestVaultGuard:
    def test_creates_gitignore_when_missing(self, tmp_path: Path) -> None:
        ensure_vault_guard(tmp_path)
        assert "brain/" in (tmp_path / ".gitignore").read_text()

    def test_appends_when_brain_not_ignored(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        ensure_vault_guard(tmp_path)
        assert "brain/" in (tmp_path / ".gitignore").read_text()

    def test_ok_when_already_guarded(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("brain/\n", encoding="utf-8")
        ensure_vault_guard(tmp_path)  # no raise

    def test_fail_closed_on_negation(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("brain/\n!brain/\n", encoding="utf-8")
        with pytest.raises(ValueError, match="fail-closed"):
            ensure_vault_guard(tmp_path)


class TestHandoff:
    def test_id_format(self) -> None:
        hid = new_handoff_id("devin", "cursor")
        assert hid.endswith("-devin-to-cursor")
        assert hid[:8].isdigit()

    def test_invalid_harness_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            new_handoff_id("bad name!", "x")

    def test_render_schema(self) -> None:
        doc = render_handoff("h1", "T", "body", "a", "b", "proj")
        assert "schema: aizee.handoff.v1" in doc
        assert "from: a" in doc and "to: b" in doc
        assert "# Handoff: T" in doc and "body" in doc

    def test_write_and_list(self, tmp_path: Path) -> None:
        res = write_handoff(tmp_path, "devin", "cursor", "Rollout", "step 3")
        assert res["scope"] == "project"
        assert Path(res["path"]).is_file()
        assert "brain/" in (tmp_path / ".gitignore").read_text()

        rows = list_handoffs(tmp_path)
        assert len(rows) == 1
        assert rows[0]["title"] == "Rollout"
        assert rows[0]["id"] == res["id"]

    def test_write_indexed_in_store(self, tmp_path: Path) -> None:
        res = write_handoff(tmp_path, "a", "b", "T", "content body")
        assert res["memory_id"].startswith("mem_")
        from memory.store import MemoryStore
        store = MemoryStore(tmp_path)
        hits = [m for m in store.search("content body") if m.id == res["memory_id"]]
        assert hits and hits[0].kind == "handoff"

    def test_user_scope_writes_home(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        res = write_handoff(tmp_path, "a", "b", "T", "x", scope="user")
        assert res["scope"] == "user"
        assert str(tmp_path / ".aizee") in res["path"]

    def test_list_empty(self, tmp_path: Path) -> None:
        assert list_handoffs(tmp_path) == []

    def test_list_skips_unreadable_docs(self, tmp_path: Path, monkeypatch) -> None:
        write_handoff(tmp_path, "a", "b", "T", "x")
        # doc without a title line — loop exhausts, title stays ""
        notitle = tmp_path / "brain" / "handoffs" / "88888888-notitle.md"
        notitle.write_text("---\nschema: x\n---\nno title here", encoding="utf-8")
        bad = tmp_path / "brain" / "handoffs" / "99999999-bad.md"
        bad.write_text("---\ntitle: broken\n---", encoding="utf-8")
        orig = Path.read_text

        def explode(self: Path, *a, **k):  # type: ignore[no-untyped-def]
            if self == bad:
                raise OSError("denied")
            return orig(self, *a, **k)

        monkeypatch.setattr(Path, "read_text", explode)
        rows = list_handoffs(tmp_path)
        titles = {r["title"] for r in rows}
        assert titles == {"T", ""} and len(rows) == 2
