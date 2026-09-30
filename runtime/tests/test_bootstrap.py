"""Tests for runtime/bootstrap.py — PyPI bootstrap path (P2.5)."""

from __future__ import annotations

from pathlib import Path

from runtime.bootstrap import bootstrap


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "new-root"
    res = bootstrap(target, dry_run=True, mcp_sync=False)
    assert res.ok and not target.exists()
    assert "skills/" in res.created_dirs
    assert "runtime/policies/default.yaml" in res.written_files


def test_apply_creates_layout(tmp_path: Path) -> None:
    target = tmp_path / "root"
    res = bootstrap(target, mcp_sync=False)
    assert res.ok
    for d in ("skills", "workflows", "rules", "tech-stack", "state", "brain", "runtime/policies"):
        assert (target / d).is_dir(), d
    assert (target / ".aizee-version").exists()
    assert (target / ".env.example").exists()
    for name in ("default.yaml", "guardian.yaml", "probity.yaml", "mcp_firewall.yaml"):
        assert (target / "runtime" / "policies" / name).exists(), name


def test_policies_copied_from_source(tmp_path: Path) -> None:
    src = tmp_path / "src"
    (src / "runtime" / "policies").mkdir(parents=True)
    (src / "runtime" / "policies" / "default.yaml").write_text("name: custom\nrules: []\n")
    target = tmp_path / "dst"
    bootstrap(target, source_root=src, mcp_sync=False)
    assert "name: custom" in (target / "runtime" / "policies" / "default.yaml").read_text()


def test_idempotent_no_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "root"
    bootstrap(target, mcp_sync=False)
    (target / ".aizee-version").write_text("CUSTOM\n")
    res = bootstrap(target, mcp_sync=False)
    assert ".aizee-version" in res.skipped_existing
    assert (target / ".aizee-version").read_text() == "CUSTOM\n"


def test_force_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "root"
    bootstrap(target, mcp_sync=False)
    (target / ".aizee-version").write_text("CUSTOM\n")
    res = bootstrap(target, force=True, mcp_sync=False)
    assert ".aizee-version" in res.written_files
    assert (target / ".aizee-version").read_text() != "CUSTOM\n"


def test_embedded_defaults_without_source(tmp_path: Path) -> None:
    target = tmp_path / "root"
    bootstrap(target, source_root=tmp_path / "nonexistent", mcp_sync=False)
    text = (target / "runtime" / "policies" / "default.yaml").read_text()
    assert "default_action" in text and "allow-reads" in text


def test_result_to_dict(tmp_path: Path) -> None:
    res = bootstrap(tmp_path / "r", mcp_sync=False)
    d = res.to_dict()
    assert d["ok"] is True and d["target"] == str(tmp_path / "r")


def test_mcp_sync_script_missing(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    res = bootstrap(tmp_path / "r", source_root=src, mcp_sync=True)
    assert any("mcp_global_sync.py not found" in n for n in res.notes)


def test_mcp_sync_runs_script(tmp_path: Path, monkeypatch) -> None:
    from unittest.mock import MagicMock

    import runtime.bootstrap as bs

    src = tmp_path / "src"
    (src / "scripts").mkdir(parents=True)
    (src / "scripts" / "mcp_global_sync.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(bs.subprocess, "run", lambda *a, **k: MagicMock(returncode=0, stderr=""))
    res = bootstrap(tmp_path / "r1", source_root=src, mcp_sync=True)
    assert res.mcp_synced
    monkeypatch.setattr(bs.subprocess, "run", lambda *a, **k: MagicMock(returncode=1, stderr="boom"))
    res2 = bootstrap(tmp_path / "r2", source_root=src, mcp_sync=True)
    assert not res2.mcp_synced
    assert any("mcp sync failed" in n for n in res2.notes)
