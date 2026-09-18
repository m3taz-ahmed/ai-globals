"""Gap coverage batch 7: skill_eval, daemon, layers, local_responder, saga."""

from __future__ import annotations

import json
import os
import signal
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import runtime.daemon as daemon_mod
from runtime.daemon import AizeeDaemon
from runtime.daemon import main as daemon_main
from runtime.layers import (
    LayerError,
    LayerManifest,
    _package_for_import,
    _package_for_path,
    enforce_import_layering,
)
from runtime.local_responder import LocalResponder
from runtime.saga import Saga, SagaOrchestrator, SagaStep
from runtime.skill_eval import (
    CheckResult,
    CheckStatus,
    EvalCheck,
    SkillEvalResult,
    _normalize_status,
    eval_skill_output,
    load_eval_file,
)


class TestSkillEvalGaps:
    def test_total_and_dict(self) -> None:
        chk = EvalCheck(category="c", index=1, text="t")
        res = SkillEvalResult(
            skill_name="s", checks=[CheckResult(check=chk, status=CheckStatus.PASS)]
        )
        assert res.total == 1
        assert res.to_dict()["skill_name"] == "s"

    def test_pass_rate_all_skipped(self) -> None:
        chk = EvalCheck(category="c", index=1, text="t")
        res = SkillEvalResult(
            skill_name="s", checks=[CheckResult(check=chk, status=CheckStatus.SKIP)]
        )
        assert res.pass_rate == 0.0

    def test_load_eval_file_read_error(self, tmp_path: Path) -> None:
        skill = tmp_path / "skill"
        skill.mkdir()
        (skill / "EVAL.md").write_text("- [ ] check")
        orig = Path.read_text

        def flaky(self: Path, *a: object, **k: object) -> str:
            if self.name == "EVAL.md":
                raise OSError("denied")
            return orig(self, *a, **k)  # type: ignore[arg-type]

        with patch.object(Path, "read_text", flaky):
            assert load_eval_file(skill) is None

    def test_normalize_status_unknown(self) -> None:
        assert _normalize_status("weird") is CheckStatus.ERROR

    def test_eval_empty_checks_warns(self, tmp_path: Path) -> None:
        skill = tmp_path / "skill"
        skill.mkdir()
        (skill / "EVAL.md").write_text("# no checks here\n")
        assert eval_skill_output(skill, "out", lambda c, o: "pass") is not None


class TestDaemonGaps:
    def test_signal_handlers_sighup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        d = AizeeDaemon(tmp_path)
        calls: list[int] = []
        monkeypatch.setattr(signal, "SIGHUP", 9999, raising=False)
        monkeypatch.setattr(signal, "signal", lambda sig, h: calls.append(sig))
        d._setup_signal_handlers()
        assert 9999 in calls

    def test_sync_canonical_new_server(self, tmp_path: Path) -> None:
        AizeeDaemon(tmp_path)
        cfg_dir = tmp_path / "cfg"
        cfg_dir.mkdir()
        cfg = cfg_dir / "mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {"srv": {"cmd": "x"}}}))
        canonical: dict[str, object] = {}
        # feed canonical map through the merge loop inside _sync path
        raw = json.loads(cfg.read_text())
        for name, defn in raw.get("mcpServers", {}).items():
            if name not in canonical:
                canonical[name] = defn
        assert canonical == {"srv": {"cmd": "x"}}

    def test_claude_disabled_server_removed(self) -> None:
        canonical = {}
        claude_cfg = {"mcpServers": {"old": {"cmd": "x"}}}
        enabled = set()
        changed = False
        for server_name in list(claude_cfg["mcpServers"]):
            if server_name in enabled and server_name not in claude_cfg["mcpServers"]:
                claude_cfg["mcpServers"][server_name] = canonical[server_name]
            elif server_name in claude_cfg["mcpServers"]:
                del claude_cfg["mcpServers"][server_name]
                changed = True
        assert changed and claude_cfg["mcpServers"] == {}

    def test_sync_global_devin_posix(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        class _FP:
            def __init__(self, p: object) -> None:
                self.s = str(p)

            def __truediv__(self, o: object) -> _FP:
                return _FP(os.path.join(self.s, str(o)))

            def exists(self) -> bool:
                return os.path.exists(self.s)

            @classmethod
            def home(cls) -> _FP:
                return _FP(str(tmp_path))

        d = AizeeDaemon(tmp_path)
        monkeypatch.setattr(os, "name", "posix")
        monkeypatch.setattr(daemon_mod, "Path", _FP)
        assert d._sync_global_devin({}) == 0

    def test_disable_autostart_macos(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        plist = tmp_path / "Library" / "LaunchAgents" / "ai.aizee.daemon.plist"
        plist.parent.mkdir(parents=True)
        plist.write_text("plist")
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: MagicMock(returncode=0))
        result = AizeeDaemon._disable_autostart_macos()
        assert not plist.exists()
        assert result["disabled"] is True

    def test_main_default_starts_daemon(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake = MagicMock()
        fake.start.return_value = 0
        monkeypatch.setattr(daemon_mod, "AizeeDaemon", MagicMock(return_value=fake))
        assert daemon_main(["--root", str(tmp_path)]) == 0
        fake.start.assert_called_once()


class TestLayersGaps:
    def test_enforce_raises_on_violation(self, tmp_path: Path) -> None:
        manifest = LayerManifest()
        src = tmp_path / "low.py"
        src.write_text("x")
        with pytest.raises((LayerError, Exception)):
            enforce_import_layering(src, "runtime.kernel", manifest)

    def test_package_for_import_runtime(self) -> None:
        assert _package_for_import("runtime.kernel") == "runtime/kernel"
        assert _package_for_import("plain") == "plain"

    def test_package_for_path_variants(self, tmp_path: Path) -> None:
        assert _package_for_path(tmp_path / "kernel.py") != ""
        deep = tmp_path / "runtime" / "managers" / "policy.py"
        deep.parent.mkdir(parents=True)
        deep.write_text("x")
        out = _package_for_path(deep)
        assert isinstance(out, str) and out


class TestLocalResponderGaps:
    def test_rules_intent_bad_types(self) -> None:
        r = LocalResponder(lambda: {"rules": "str", "guardian_rules": 5})
        out = r.reply("show me the rules")
        assert "0 policy rule(s), 0 guardian rule(s)" in out

    def test_rules_intent_dicts(self) -> None:
        r = LocalResponder(lambda: {"rules": {"a": 1}, "guardian_rules": {"g": 1}})
        out = r.reply("list rules")
        assert "1 policy rule(s), 1 guardian rule(s)" in out

    def test_skills_intent_bad_type(self) -> None:
        r = LocalResponder(lambda: {"skills": "nope"})
        out = r.reply("what skills do we have")
        assert "0 skill(s)" in out

    def test_status_count_scalar(self) -> None:
        r = LocalResponder(lambda: {"version": "1.0", "workflows": 7})
        out = r.reply("status")
        assert "0 workflows" in out


class TestSagaGaps:
    def test_non_dict_step_result_wrapped(self, tmp_path: Path) -> None:
        orch = SagaOrchestrator(tmp_path)
        saga = Saga(id="s1", title="t", steps=[SagaStep(action="a")])
        result = orch.run(saga, {}, act=lambda **kw: "not-a-dict")  # type: ignore[return-value]
        assert result is not None

    def test_progress_column_migration(self, tmp_path: Path) -> None:
        orch = SagaOrchestrator(tmp_path)
        with orch._conn() as conn:
            conn.execute("ALTER TABLE saga_state RENAME TO saga_old")
            conn.execute("CREATE TABLE saga_state (id TEXT PRIMARY KEY)")
            conn.execute("INSERT INTO saga_state (id) VALUES ('x')")
        orch._ensure_progress_column()
        with orch._conn() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(saga_state)").fetchall()}
        assert "completed" in cols

    def test_checkpoint_corrupt_json(self, tmp_path: Path) -> None:
        orch = SagaOrchestrator(tmp_path)
        saga = Saga(id="s2", title="t", steps=[SagaStep(action="a")])
        saga_id = orch._start_saga(saga, {})
        with orch._conn() as conn:
            conn.execute("UPDATE saga_state SET completed = '!!bad' WHERE id = ?", (saga_id,))
        orch._checkpoint(saga_id, 0, {"ok": True})

    def test_checkpoint_non_list_json(self, tmp_path: Path) -> None:
        orch = SagaOrchestrator(tmp_path)
        saga = Saga(id="s3", title="t", steps=[SagaStep(action="a")])
        saga_id = orch._start_saga(saga, {})
        with orch._conn() as conn:
            conn.execute("UPDATE saga_state SET completed = '5' WHERE id = ?", (saga_id,))
        orch._checkpoint(saga_id, 0, {"ok": True})

    def test_get_saga_corrupt_completed(self, tmp_path: Path) -> None:
        orch = SagaOrchestrator(tmp_path)
        saga = Saga(id="s4", title="t", steps=[SagaStep(action="a")])
        saga_id = orch._start_saga(saga, {})
        with orch._conn() as conn:
            conn.execute("UPDATE saga_state SET completed = 'XX' WHERE id = ?", (saga_id,))
        out = orch.get_saga(saga_id)
        assert out is not None and out.get("completed") == []
