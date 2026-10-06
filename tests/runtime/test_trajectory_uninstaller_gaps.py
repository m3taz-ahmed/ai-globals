"""Gap coverage for runtime/trajectory.py and runtime/uninstaller.py."""

from __future__ import annotations

import builtins
import json
import os
import subprocess
from pathlib import Path

import pytest

from runtime.trajectory import (
    FailureCategory,
    StepStatus,
    TrajectoryTracker,
)
from runtime.uninstaller import (
    CategoryAction,
    UninstallCategory,
    _ask_backup,
    _execute_uninstall,
    _remove_path,
    create_backup,
    remove_cli_shim,
)


class TestTrajectoryGaps:
    def test_record_assumption_unknown(self) -> None:
        t = TrajectoryTracker("intent")
        with pytest.raises(KeyError):
            t.record_assumption("nope", "a")

    def test_is_stalled_unknown_and_converged(self) -> None:
        t = TrajectoryTracker("intent")
        assert t.is_stalled("nope") is False
        rid = t.start_run()
        t.mark_converged(rid)
        assert t.is_stalled(rid) is False

    def test_mark_converged_unknown_and_no_evidence(self) -> None:
        t = TrajectoryTracker("intent")
        with pytest.raises(KeyError):
            t.mark_converged("nope")
        rid = t.start_run()
        t.mark_converged(rid, "")
        assert t.get_run(rid).checks == {}  # type: ignore[union-attr]

    def test_abort_unknown_and_no_reason(self) -> None:
        t = TrajectoryTracker("intent")
        with pytest.raises(KeyError):
            t.abort("nope")
        rid = t.start_run()
        t.abort(rid, "")
        assert "abort_reason" not in t.get_run(rid).checks  # type: ignore[union-attr]

    def test_status_unknown(self) -> None:
        assert TrajectoryTracker().status("nope") == {"error": "unknown run"}

    def test_export_ndjson_full_step(self, tmp_path: Path) -> None:
        t = TrajectoryTracker("intent")
        rid = t.start_run()
        t.record_step(
            rid,
            "act",
            StepStatus.FAILED,
            file="f.py",
            failure_category=FailureCategory.INVALID_INVOCATION,
            tool_name="search",
            tool_input={"q": "x"},
            tool_output="result text",
            extra="meta",
        )
        out = tmp_path / "trace.ndjson"
        count = t.export_ndjson(rid, out)
        assert count == 3
        event = json.loads(out.read_text().splitlines()[1])
        assert event["tool_output"] == "result text"
        assert event["metadata"] == {"extra": "meta"}
        assert event["failure_category"] == FailureCategory.INVALID_INVOCATION.value


class TestUninstallerGaps:
    def test_total_size_skips_subdirs(self, tmp_path: Path) -> None:
        d = tmp_path / "keep"
        (d / "sub").mkdir(parents=True)
        (d / "f.txt").write_text("x")
        cat = UninstallCategory("k", "K", [d], is_learned=True)
        assert cat.total_size_bytes() == 1

    def test_create_backup_default_path(self, tmp_path: Path) -> None:
        d = tmp_path / "keep"
        (d / "sub").mkdir(parents=True)
        (d / "sub" / "f.txt").write_text("x")
        (d / "top.txt").write_text("y")
        cat = UninstallCategory("k", "K", [d], is_learned=True)
        out = create_backup(tmp_path, [cat], None)
        assert out is not None and out.exists()
        out.unlink()

    def test_remove_path_nonexistent(self, tmp_path: Path) -> None:
        assert _remove_path(tmp_path / "ghost") is False

    def test_remove_cli_shim_posix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import runtime.uninstaller as un

        bindir = tmp_path / "bin"
        bindir.mkdir()
        shim = bindir / "aizee"
        shim.write_text("shim")

        class _FakePath:
            """Path stand-in that does not dispatch on os.name."""

            def __init__(self, p: object) -> None:
                self.s = str(p)

            def __truediv__(self, other: object) -> _FakePath:
                return _FakePath(os.path.join(self.s, str(other)))

            def exists(self) -> bool:
                return os.path.exists(self.s)

            def is_file(self) -> bool:
                return os.path.isfile(self.s)

            def is_symlink(self) -> bool:
                return os.path.islink(self.s)

            def is_dir(self) -> bool:
                return os.path.isdir(self.s)

            def unlink(self) -> None:
                os.unlink(self.s)

        class _R:
            stdout = str(tmp_path)
            returncode = 0

        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr(un, "Path", _FakePath)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: _R())
        assert remove_cli_shim() is True
        assert not shim.exists()

    def test_ask_backup_eof_on_custom(self, tmp_path: Path) -> None:
        d = tmp_path / "keep"
        d.mkdir()
        (d / "f").write_text("x")
        cat = UninstallCategory("k", "K", [d], is_learned=True)
        calls = iter(["p"])

        def fake_input(prompt: str = "") -> str:
            try:
                return next(calls)
            except StopIteration:
                raise EOFError from None

        orig = builtins.input
        builtins.input = fake_input
        try:
            assert _ask_backup([cat]) is None
        finally:
            builtins.input = orig

    def test_execute_uninstall_empty_backup(self, tmp_path: Path) -> None:
        cat = UninstallCategory("k", "K", [tmp_path / "nonexistent"], is_learned=True)
        cat.action = CategoryAction.KEEP
        code = _execute_uninstall(tmp_path, [cat], tmp_path / "b.zip", assume_yes=True)
        assert isinstance(code, int)
