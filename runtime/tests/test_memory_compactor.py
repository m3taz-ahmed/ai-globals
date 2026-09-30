"""Tests for memory/compactor.py — Memory.md auto-compaction (P2.4)."""

from __future__ import annotations

from pathlib import Path

from memory.compactor import compact_memory


def _mk(tmp_path: Path, sections: int, lines_per: int = 20) -> Path:
    p = tmp_path / "Memory.md"
    parts = ["[FILE] Memory", "[OBJ] context", "[RULES]", "1. keep small", ""]
    for i in range(sections):
        parts.append(f"[UPDATED] 2026-09-{20 - i:02d}")
        parts.append("[NOTES]")
        for j in range(lines_per):
            parts.append(f"- note {i}-{j} lorem ipsum")
        if i == sections - 1:
            parts.append("- keep this forever [PINNED]")
    p.write_text("\n".join(parts), encoding="utf-8")
    return p


def test_under_budget_noop(tmp_path: Path) -> None:
    p = tmp_path / "Memory.md"
    p.write_text("[FILE] Memory\n[UPDATED] 2026-09-29\n- one\n", encoding="utf-8")
    r = compact_memory(p)
    assert r.ok and not r.needed


def test_structureless_file_untouched(tmp_path: Path) -> None:
    p = tmp_path / "Memory.md"
    p.write_text("\n".join(f"line {i}" for i in range(1000)), encoding="utf-8")
    r = compact_memory(p, max_lines=100)
    assert r.ok and not r.needed and len(p.read_text().splitlines()) == 1000


def test_dry_run_reports_without_writing(tmp_path: Path) -> None:
    p = _mk(tmp_path, 10)
    before = p.read_text()
    r = compact_memory(p, max_lines=60, dry_run=True)
    assert r.ok and r.needed and r.dry_run
    assert p.read_text() == before
    assert r.archived_sections > 0


def test_apply_compacts_and_archives(tmp_path: Path) -> None:
    p = _mk(tmp_path, 10)
    r = compact_memory(p, max_lines=60, dry_run=False)
    assert r.ok and r.after_lines <= 60 + 3  # pinned block overhead allowed
    assert r.kept_sections >= 1
    assert r.archive_path and Path(r.archive_path).exists()
    text = p.read_text()
    assert "[FILE] Memory" in text  # preamble preserved
    assert "keep this forever [PINNED]" in text  # pinned rescued
    archive = Path(r.archive_path).read_text()
    assert "[UPDATED] 2026-09-18" in archive  # oldest sections archived


def test_pinned_rescue(tmp_path: Path) -> None:
    p = _mk(tmp_path, 8)
    r = compact_memory(p, max_lines=50, dry_run=True)
    assert r.pinned_rescued == 1


def test_missing_file(tmp_path: Path) -> None:
    r = compact_memory(tmp_path / "nope.md")
    assert not r.ok


def test_result_to_dict(tmp_path: Path) -> None:
    p = _mk(tmp_path, 4)
    r = compact_memory(p, max_lines=50, dry_run=True)
    d = r.to_dict()
    assert d["ok"] is True and d["needed"] is True and "before_lines" in d


def test_compact_without_pinned_lines(tmp_path: Path) -> None:
    # Dropped sections exist but none carry [PINNED] -> no rescue block.
    p = tmp_path / "Memory.md"
    parts = ["[FILE] Memory", ""]
    for i in range(10):
        parts.append(f"[UPDATED] 2026-09-{20 - i:02d}")
        for j in range(15):
            parts.append(f"- plain note {i}-{j}")
    p.write_text("\n".join(parts), encoding="utf-8")
    r = compact_memory(p, max_lines=40, dry_run=True)
    assert r.pinned_rescued == 0 and r.archived_sections > 0


def test_apply_all_kept_no_archive(tmp_path: Path) -> None:
    # Over budget but only 1 section -> kept by MIN_KEEP -> nothing archived.
    p = _mk(tmp_path, 1, lines_per=200)
    r = compact_memory(p, max_lines=50, dry_run=False)
    assert r.ok and r.needed and r.archive_path == ""


def test_atomic_write_failure_cleans_tmp(tmp_path: Path, monkeypatch) -> None:
    import os


    p = _mk(tmp_path, 10)
    monkeypatch.setattr(os, "replace", lambda *_a, **_k: (_ for _ in ()).throw(OSError("locked")))
    try:
        compact_memory(p, max_lines=60, dry_run=False)
    except OSError:
        pass
    else:
        raise AssertionError("expected OSError")
    assert not list(tmp_path.glob("*.tmp"))
