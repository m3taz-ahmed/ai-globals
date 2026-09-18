"""Tests for `aizee hook` - IDE lifecycle hook entry point."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from aizee_cli import main
from memory.observations import ObservationStore, default_db_path


def _stdin(monkeypatch: pytest.MonkeyPatch, payload: object) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))


def test_hook_inject_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _stdin(monkeypatch, {})
    rc = main(["--project", str(tmp_path), "hook", "inject"])
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_hook_observe_then_inject(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _stdin(monkeypatch, {"session_id": "s1", "file_path": "app.py"})
    assert main(["--project", str(tmp_path), "hook", "observe", "--kind", "file_edit"]) == 0
    _stdin(monkeypatch, {"session_id": "s1"})
    assert main(["--project", str(tmp_path), "hook", "inject"]) == 0
    out = capsys.readouterr().out
    assert "### Recent observations" in out
    assert "app.py" in out
    store = ObservationStore(default_db_path(tmp_path))
    assert store.count() == 1


def test_hook_observe_with_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, {"session_id": "s1", "command": "ls"})
    rc = main(["--project", str(tmp_path), "hook", "observe", "--event", "afterShellExecution"])
    assert rc == 0
    store = ObservationStore(default_db_path(tmp_path))
    assert store.recent()[0].kind == "shell"


def test_hook_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    _stdin(monkeypatch, {"session_id": "s1", "file_path": "x.py"})
    main(["--project", str(tmp_path), "hook", "observe", "--kind", "file_edit"])
    _stdin(monkeypatch, {"session_id": "s1"})
    assert main(["--project", str(tmp_path), "hook", "summary"]) == 0
    assert "Session summary: 1 observations" in capsys.readouterr().out


def test_hook_malformed_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not valid json"))
    rc = main(["--project", str(tmp_path), "hook", "inject"])
    assert rc == 0
    capsys.readouterr()


def test_hook_non_dict_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stdin(monkeypatch, [1, 2, 3])
    assert main(["--project", str(tmp_path), "hook", "observe", "--kind", "shell"]) == 0


def test_hook_empty_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert main(["--project", str(tmp_path), "hook", "summary"]) == 0


def test_hook_never_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Even when the project root is unusable, hooks exit 0."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    _stdin(monkeypatch, {})
    assert main(["--project", str(blocker / "state"), "hook", "observe"]) == 0
