"""Tests for runtime/skill_lifecycle — deterministic skill-survival engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.schemas import ValidationError
from runtime.skill_lifecycle import (
    SkillLifecycleManager,
    SkillMember,
    evaluate,
)


def _member(
    name: str, *, use: int = 0, view: int = 0, anchor: int = 0, origin: str = "learned"
) -> SkillMember:
    return SkillMember(name=name, use=use, view=view, anchor=anchor, origin=origin)


class TestEvaluate:
    def test_probation_protects_zero_use(self):
        m = [_member("new", use=0, view=0, anchor=50)]
        assert evaluate(m, request_count=60, maturity=100) == []

    def test_zero_use_and_zero_view_archived_at_maturity(self):
        m = [_member("dormant", use=0, view=0, anchor=0)]
        assert evaluate(m, request_count=100, maturity=100) == ["dormant"]

    def test_zero_use_but_viewed_survives(self):
        m = [_member("seen", use=0, view=3, anchor=0)]
        assert evaluate(m, request_count=150, maturity=100) == []

    def test_review_suspended_parks_zero_use(self):
        m = [_member("dormant", use=0, view=0, anchor=0)]
        assert evaluate(m, request_count=150, maturity=100, review_suspended=True) == []

    def test_capacity_contention_archives_lowest_rate(self):
        members = [
            _member("hot", use=50, anchor=0),
            _member("warm", use=20, anchor=0),
            _member("cold", use=2, anchor=0),
        ]
        assert evaluate(members, request_count=200, maturity=10, capacity=2) == ["cold"]

    def test_hand_authored_never_archived(self):
        m = [_member("mine", use=0, view=0, anchor=0, origin="authored")]
        assert evaluate(m, request_count=500, maturity=100) == []

    def test_denominator_uses_anchor_offset(self):
        # Skill landed at request 190; only 10 requests since -> probation.
        m = [_member("late", use=0, view=0, anchor=190)]
        assert evaluate(m, request_count=200, maturity=100) == []

    def test_rate_uses_requests_since_anchor(self):
        # hot landed late: 10 uses / 10 requests = rate 1.0 beats
        # busy: 50 uses / 200 requests = 0.25 -> busy archived at capacity 1.
        members = [
            _member("busy", use=50, anchor=0),
            _member("hot", use=10, anchor=190),
        ]
        assert evaluate(members, request_count=200, maturity=10, capacity=1) == ["busy"]


@pytest.fixture()
def mgr(tmp_path: Path) -> SkillLifecycleManager:
    (tmp_path / "skills").mkdir()
    return SkillLifecycleManager(tmp_path, maturity=10, capacity=2)


class TestManager:
    def test_register_anchors_at_current_request(self, mgr):
        mgr.record_request(5)
        m = mgr.register("s1", reason="test")
        assert m.anchor == 5 and m.origin == "learned"
        ledger = mgr.ledger("s1")
        assert ledger[0]["event"] == "register"

    def test_register_requires_name(self, mgr):
        with pytest.raises(ValidationError):
            mgr.register("")

    def test_record_use_view_only_managed(self, mgr):
        mgr.record_use("ghost")  # unmanaged: no-op, no member created
        assert "ghost" not in {m.name for m in mgr.members()}
        mgr.register("s1")
        mgr.record_use("s1")
        mgr.record_view("s1", 2)
        m = next(x for x in mgr.members() if x.name == "s1")
        assert (m.use, m.view) == (1, 2)

    def test_persistence_roundtrip(self, tmp_path):
        (tmp_path / "skills").mkdir()
        m1 = SkillLifecycleManager(tmp_path)
        m1.register("s1")
        m1.record_request(3)
        m1.record_use("s1")
        m2 = SkillLifecycleManager(tmp_path)
        assert m2.request_count == 3
        assert m2.members()[0].use == 1

    def test_corrupt_state_failsafe(self, tmp_path):
        (tmp_path / "state").mkdir(parents=True)
        (tmp_path / "state" / "skill_lifecycle.json").write_text("{bad json", encoding="utf-8")
        m = SkillLifecycleManager(tmp_path)
        assert m.request_count == 0 and m.members() == []

    def test_archive_moves_file_and_records(self, mgr, tmp_path):
        skill = tmp_path / "skills" / "s1.md"
        skill.write_text("# s1", encoding="utf-8")
        mgr.register("s1")
        mgr.record_request(20)  # past maturity=10, zero use/view -> archive
        assert mgr.evaluate() == ["s1"]
        assert mgr.archive("s1") is True
        assert not skill.exists()
        assert (tmp_path / "skills" / "_archive" / "s1.md").exists()
        assert mgr.ledger("s1")[-1]["event"] == "archive"
        assert mgr.members() == []

    def test_archive_refuses_when_not_pending(self, mgr, tmp_path):
        (tmp_path / "skills" / "s1.md").write_text("# s1", encoding="utf-8")
        mgr.register("s1")  # still in probation -> not on archive list
        assert mgr.archive("s1") is False

    def test_archive_manual_override(self, mgr, tmp_path):
        (tmp_path / "skills" / "s1.md").write_text("# s1", encoding="utf-8")
        mgr.register("s1")
        assert mgr.archive("s1", reason="manual") is True

    def test_archive_dir_form(self, mgr, tmp_path):
        (tmp_path / "skills" / "s1").mkdir()
        (tmp_path / "skills" / "s1" / "SKILL.md").write_text("# s1", encoding="utf-8")
        mgr.register("s1")
        mgr.record_request(20)
        assert mgr.archive("s1") is True
        assert (tmp_path / "skills" / "_archive" / "s1" / "SKILL.md").exists()

    def test_fold_transfers_counters(self, mgr):
        mgr.register("winner")
        mgr.register("loser")
        mgr.record_use("loser", 4)
        mgr.record_view("loser", 2)
        mgr.fold("winner", "loser", reason="dup scenario")
        win = next(m for m in mgr.members() if m.name == "winner")
        assert (win.use, win.view) == (4, 2)
        assert "loser" not in {m.name for m in mgr.members()}
        ev = mgr.ledger("loser")[-1]
        assert ev["event"] == "fold" and "winner" in ev["evidence"]

    def test_status_snapshot(self, mgr):
        mgr.register("a")
        mgr.register("b")
        mgr.record_request(15)  # both past maturity=10, zero use/view
        st = mgr.status()
        assert st["managed"] == 2 and st["mature"] == 2 and st["probation"] == 0
        assert st["archive_pending"] == ["a", "b"]

    def test_state_file_schema(self, mgr, tmp_path):
        mgr.register("s1")
        mgr.record_request(2)
        data = json.loads((tmp_path / "state" / "skill_lifecycle.json").read_text(encoding="utf-8"))
        assert data["request_count"] == 2 and "s1" in data["members"]

    def test_load_restores_members_from_state(self, tmp_path):
        (tmp_path / "state").mkdir(parents=True)
        (tmp_path / "state" / "skill_lifecycle.json").write_text(
            json.dumps(
                {
                    "request_count": 7,
                    "members": {"s1": {"use": 3, "view": 1, "anchor": 2, "origin": "learned"}},
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / "skills").mkdir()
        m = SkillLifecycleManager(tmp_path)
        assert m.request_count == 7
        assert m.members()[0].use == 3

    def test_load_ignores_non_dict_state(self, tmp_path):
        (tmp_path / "state").mkdir(parents=True)
        (tmp_path / "state" / "skill_lifecycle.json").write_text("[1,2]", encoding="utf-8")
        (tmp_path / "skills").mkdir()
        assert SkillLifecycleManager(tmp_path).request_count == 0

    def test_save_failure_raises_storage_error(self, mgr, monkeypatch):
        from runtime.schemas import StorageError

        def _boom(*a: object, **k: object) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(Path, "write_text", _boom)
        with pytest.raises(StorageError):
            mgr.register("s1")

    def test_ledger_write_failure_warns_not_raises(self, mgr):
        from unittest.mock import patch

        mgr.register("s1")
        real_open = Path.open

        def _fail_jsonl(self: Path, *a: object, **k: object) -> object:
            if str(self).endswith(".jsonl"):
                raise OSError("ro fs")
            return real_open(self, *a, **k)

        with patch("runtime.skill_lifecycle._logger") as mock_log:
            with patch.object(Path, "open", _fail_jsonl):
                mgr.record_use("s1")  # ledger append fails -> warning only
        assert mock_log.warning.called

    def test_ledger_read_failure_returns_empty(self, mgr, monkeypatch):
        mgr.register("s1")
        from unittest.mock import patch

        with patch.object(Path, "read_text", side_effect=OSError("gone")):
            assert mgr.ledger("s1") == []

    def test_register_existing_member_is_idempotent(self, mgr):
        mgr.register("s1")
        first = mgr.register("s1")  # same member returned, no duplicate ledger grow
        assert first.name == "s1"
        assert len([m for m in mgr.members() if m.name == "s1"]) == 1

    def test_archive_move_failure_warns(self, mgr, tmp_path):
        from unittest.mock import patch

        (tmp_path / "skills" / "s1.md").write_text("# s1", encoding="utf-8")
        mgr.register("s1")
        mgr.record_request(20)
        with patch.object(Path, "rename", side_effect=OSError("locked")):
            assert mgr.archive("s1") is False

    def test_fold_with_missing_member_noop(self, mgr):
        mgr.register("winner")
        mgr.fold("winner", "ghost")
        win = next(m for m in mgr.members() if m.name == "winner")
        assert (win.use, win.view) == (0, 0)
        assert mgr.ledger("ghost")[-1]["event"] == "fold"

    def test_archive_unmanaged_returns_false(self, mgr):
        assert mgr.archive("ghost") is False

    def test_record_view_unmanaged_noop(self, mgr):
        mgr.record_view("ghost")
        assert mgr.members() == []

    def test_load_ignores_non_dict_members(self, tmp_path):
        (tmp_path / "state").mkdir(parents=True)
        (tmp_path / "state" / "skill_lifecycle.json").write_text(
            json.dumps({"request_count": 3, "members": "oops"}),
            encoding="utf-8",
        )
        (tmp_path / "skills").mkdir()
        m = SkillLifecycleManager(tmp_path)
        assert m.request_count == 3 and m.members() == []
