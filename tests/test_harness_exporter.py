"""Tests for runtime.harness_exporter — skill install into agent harnesses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.harness_exporter import (
    harnesses,
    install_skill,
    resolve_harness_dir,
)


@pytest.fixture()
def skills_root(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    (root / "dirskill").mkdir(parents=True)
    (root / "dirskill" / "SKILL.md").write_text("---\nname: dirskill\n---\nbody", encoding="utf-8")
    (root / "dirskill" / "extra.txt").write_text("x", encoding="utf-8")
    (root / "flatskill.md").write_text("---\nname: flatskill\n---\nbody", encoding="utf-8")
    return root


def test_harnesses_resolve_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    hs = harnesses()
    assert hs["cursor"] == str(tmp_path / ".cursor" / "skills")
    assert set(hs) == {"cursor", "claude", "codex", "opencode"}


def test_resolve_harness_dir_path_and_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert resolve_harness_dir("path", str(tmp_path / "x")) == tmp_path / "x"
    monkeypatch.chdir(tmp_path)
    assert resolve_harness_dir("project") == tmp_path / ".agents" / "skills"
    with pytest.raises(ValueError):
        resolve_harness_dir("path", "")
    with pytest.raises(ValueError):
        resolve_harness_dir("bogus")


def test_install_dir_skill_recursive(skills_root: Path, tmp_path: Path) -> None:
    r = install_skill(skills_root, "dirskill", "path", str(tmp_path / "out"))
    assert r.ok
    assert set(r.files) == {"SKILL.md", "extra.txt"}
    assert (Path(r.dest) / "extra.txt").exists()


def test_install_flat_skill(skills_root: Path, tmp_path: Path) -> None:
    r = install_skill(skills_root, "flatskill", "path", str(tmp_path / "out"))
    assert r.ok and r.files == ["flatskill.md"]
    assert (tmp_path / "out" / "flatskill.md").exists()


def test_install_refuses_overwrite_then_force(skills_root: Path, tmp_path: Path) -> None:
    dest = str(tmp_path / "out")
    install_skill(skills_root, "dirskill", "path", dest)
    r = install_skill(skills_root, "dirskill", "path", dest)
    assert not r.ok and "force" in r.error
    r2 = install_skill(skills_root, "dirskill", "path", dest, force=True)
    assert r2.ok and r2.overwritten


def test_install_missing_skill_errors(skills_root: Path, tmp_path: Path) -> None:
    r = install_skill(skills_root, "nope", "path", str(tmp_path / "out"))
    assert not r.ok and "not found" in r.error


def test_main_list_outputs_json(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from runtime.harness_exporter import main

    assert main(["--list"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "cursor" in out
