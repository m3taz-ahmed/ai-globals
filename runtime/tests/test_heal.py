"""Tests for runtime/heal.py — safe autofix orchestrator."""

from __future__ import annotations

import json
from pathlib import Path

from runtime.heal import Healer, HealStatus, Severity


def _mk_roots(tmp_path: Path) -> tuple[Path, Path]:
    os_root = tmp_path / "os"
    project = tmp_path / "proj"
    (os_root / "runtime" / "policies").mkdir(parents=True)
    (os_root / "runtime" / "policies" / "default.yaml").write_text("rules: []\n")
    (os_root / "scripts").mkdir(parents=True)
    project.mkdir(parents=True)
    return os_root, project


def test_scan_finds_missing_dirs(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert findings["missing-state-dir"].severity == Severity.ERROR
    assert findings["missing-brain-dir"].auto_fixable
    assert findings["missing-version-file"].auto_fixable


def test_scan_clean_install_reports_info_only(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    (project / "state").mkdir()
    (project / "brain").mkdir()
    (os_root / ".aizee-version").write_text("0.0.0\n")
    (os_root / ".env").write_text("OK=1\n", encoding="utf-8")
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert findings["missing-state-dir"].severity == Severity.INFO
    assert "missing-brain-dir" not in findings
    assert "env-encoding" not in findings


def test_dry_run_default_apply_fixes_dirs(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["missing-state-dir"].status == HealStatus.APPLIED
    assert (project / "state").is_dir()
    assert results["missing-brain-dir"].status == HealStatus.APPLIED
    assert (project / "brain").is_dir()
    assert results["missing-version-file"].status == HealStatus.APPLIED
    assert (os_root / ".aizee-version").exists()


def test_env_encoding_fix(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    (os_root / ".env").write_bytes(b"A=1\n# bad \x97 byte\n")
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["env-encoding"].status == HealStatus.APPLIED
    (os_root / ".env").read_text(encoding="utf-8")
    assert (os_root / ".env.bak").exists()


def test_heal_log_written(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    Healer(os_root, project).apply(assume_yes=True)
    log = project / "state" / "heal.log"
    assert log.exists()
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert any(r["status"] == "applied" for r in rows)


def test_manual_finding_not_fixed(tmp_path: Path) -> None:
    os_root, project = _mk_roots(tmp_path)
    (os_root / "runtime" / "policies" / "default.yaml").unlink()
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["missing-default-policy"].status == HealStatus.MANUAL


def test_memory_schema_drift_fix(tmp_path: Path) -> None:
    import sqlite3

    os_root, project = _mk_roots(tmp_path)
    brain = project / "brain"
    brain.mkdir()
    conn = sqlite3.connect(brain / "memory.db")
    conn.execute(
        "CREATE TABLE memories (id TEXT PRIMARY KEY, kind TEXT, content TEXT, source TEXT, meta TEXT,"
        " created_at TEXT, valid_from TEXT, valid_to TEXT, integrity_sig TEXT)"
    )
    conn.commit()
    conn.close()
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["memory-schema-drift"].status == HealStatus.APPLIED


def _patch_appdata(monkeypatch, tmp_path: Path) -> Path:
    appdata = tmp_path / "appdata"
    appdata.mkdir(parents=True)
    monkeypatch.setenv("APPDATA", str(appdata))
    return appdata


def test_global_mcp_config_missing_finding_and_fix(tmp_path: Path, monkeypatch) -> None:
    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)  # no mcp_config.json -> finding fires
    (os_root / "scripts" / "mcp_global_sync.py").write_text("import sys\nsys.exit(0)\n")
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["global-mcp-config"].status == HealStatus.APPLIED


def test_global_mcp_config_fixer_failure(tmp_path: Path, monkeypatch) -> None:
    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    (os_root / "scripts" / "mcp_global_sync.py").write_text(
        "import sys\nsys.stderr.write('boom')\nsys.exit(3)\n"
    )
    results = {r.finding.id: r for r in Healer(os_root, project).apply(assume_yes=True)}
    assert results["global-mcp-config"].status == HealStatus.FAILED
    assert "boom" in (results["global-mcp-config"].detail or "")


def test_global_mcp_config_invalid_json(tmp_path: Path, monkeypatch) -> None:
    os_root, project = _mk_roots(tmp_path)
    appdata = _patch_appdata(monkeypatch, tmp_path)
    cfg_dir = appdata / "devin"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "mcp_config.json").write_text("{not json", encoding="utf-8")
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert "global-mcp-config" in findings


def test_memory_schema_healthy_no_finding(tmp_path: Path, monkeypatch) -> None:
    from memory.store import MemoryStore

    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    MemoryStore(project, enable_vector=False)  # creates migrated schema
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert "memory-schema-drift" not in findings


def test_memory_schema_verify_error_finding(tmp_path: Path, monkeypatch) -> None:
    import memory.schema_contract as sc

    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    brain = project / "brain"
    brain.mkdir()
    (brain / "memory.db").write_bytes(b"placeholder")

    def _raise(_p):
        raise RuntimeError("db locked")

    monkeypatch.setattr(sc, "verify_schema_integrity", _raise)
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert findings["memory-schema-drift"].severity == Severity.ERROR
    assert "verify error" in findings["memory-schema-drift"].description


def test_missing_pip_dependency_finding(tmp_path: Path, monkeypatch) -> None:
    import builtins

    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    real_import = builtins.__import__

    def _no_pydantic(name, *a, **kw):
        if name == "pydantic":
            raise ImportError("gone")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", _no_pydantic)
    findings = {f.id: f for f in Healer(os_root, project).scan()}
    assert findings["pip-pydantic"].severity == Severity.ERROR


def test_interactive_decline_skips(tmp_path: Path, monkeypatch) -> None:
    import builtins
    import sys

    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda _p="": "n")
    results = {r.finding.id: r for r in Healer(os_root, project).apply()}
    assert results["missing-state-dir"].status == HealStatus.SKIPPED
    assert not (project / "state").exists()


def test_interactive_accept_applies(tmp_path: Path, monkeypatch) -> None:
    import builtins
    import sys

    os_root, project = _mk_roots(tmp_path)
    _patch_appdata(monkeypatch, tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(builtins, "input", lambda _p="": "y")
    results = {r.finding.id: r for r in Healer(os_root, project).apply()}
    assert results["missing-state-dir"].status == HealStatus.APPLIED


def test_audit_noop_when_nothing_applied(tmp_path: Path, monkeypatch) -> None:
    os_root, project = _mk_roots(tmp_path)
    appdata = _patch_appdata(monkeypatch, tmp_path)
    cfg_dir = appdata / "devin"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "mcp_config.json").write_text('{"mcpServers": {"x": {}}}', encoding="utf-8")
    (project / "state").mkdir()
    (project / "brain").mkdir()
    (os_root / ".aizee-version").write_text("0.0.0\n")
    (os_root / ".env").write_text("OK=1\n", encoding="utf-8")
    Healer(os_root, project).apply(assume_yes=True)
    assert not (project / "state" / "heal.log").exists()
