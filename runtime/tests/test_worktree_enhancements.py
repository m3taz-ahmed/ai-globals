"""Tests for worktree_pool enhancements — StallDetector + TetherFile.

These tests don't require git; they test the new components directly.
"""

from __future__ import annotations

import time
from pathlib import Path

from runtime.worktree_pool import StallDetector, TetherFile, Worktree


class TestTetherFile:
    """Tests for tether file persistence (crash recovery)."""

    def test_write_and_read(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / ".tethers")
        assert tether.write("agent-1", "assignment-data") is True
        assert tether.read("agent-1") == "assignment-data"

    def test_read_nonexistent_returns_none(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / ".tethers")
        assert tether.read("nonexistent") is None

    def test_remove(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / ".tethers")
        tether.write("agent-1", "data")
        assert tether.remove("agent-1") is True
        assert tether.read("agent-1") is None

    def test_remove_nonexistent_returns_true(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / ".tethers")
        assert tether.remove("nonexistent") is True

    def test_overwrite_existing(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / ".tethers")
        tether.write("agent-1", "old")
        tether.write("agent-1", "new")
        assert tether.read("agent-1") == "new"

    def test_creates_directory(self, tmp_path: Path) -> None:
        tether = TetherFile(tmp_path / "nested" / "deep" / ".tethers")
        tether.write("agent-1", "data")
        assert tether.read("agent-1") == "data"


class TestStallDetector:
    """Tests for stall detection via output hashing."""

    def test_not_stalled_on_first_check(self) -> None:
        detector = StallDetector(stall_timeout_seconds=0.01)
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        assert detector.check_stalled(wt, "some output") is False

    def test_not_stalled_when_output_changes(self) -> None:
        detector = StallDetector(stall_timeout_seconds=0.01)
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        detector.check_stalled(wt, "output v1")
        time.sleep(0.02)
        assert detector.check_stalled(wt, "output v2") is False

    def test_stalled_when_output_unchanged(self) -> None:
        detector = StallDetector(stall_timeout_seconds=0.01)
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        detector.check_stalled(wt, "same output")
        time.sleep(0.02)
        assert detector.check_stalled(wt, "same output") is True

    def test_should_respawn_under_max(self) -> None:
        detector = StallDetector(max_respawns=2)
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        assert detector.should_respawn(wt) is True

    def test_should_not_respawn_at_max(self) -> None:
        detector = StallDetector(max_respawns=2)
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        detector.record_respawn(wt)
        detector.record_respawn(wt)
        assert detector.should_respawn(wt) is False

    def test_record_respawn_increments_count(self) -> None:
        detector = StallDetector()
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        assert wt.respawn_count == 0
        detector.record_respawn(wt)
        assert wt.respawn_count == 1

    def test_record_respawn_resets_hash(self) -> None:
        detector = StallDetector()
        wt = Worktree(id="1", agent_id="a1", branch="b", path=Path("/tmp"))
        wt.last_output_hash = "abc123"
        detector.record_respawn(wt)
        assert wt.last_output_hash == ""
