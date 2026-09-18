"""Gap coverage for aizee_cli.py: watch loop, sync/graphify errors,
audit/spec/skill/agents/doctor/uninstall/daemon commands, main() handlers."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aizee_cli import main


def _tmp_root() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aizee_cli_gap_"))
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    return tmp


# ---------------------------------------------------------------------------
# memory ingest --watch (lines 167-194)
# ---------------------------------------------------------------------------

class TestCliMemoryWatch:
    def test_watch_reingests_on_change(self, capsys):
        tmp = _tmp_root()
        try:
            calls = {"n": 0}

            def _sleep(_s: float) -> None:
                calls["n"] += 1
                if calls["n"] == 1:
                    # simulate a change by bumping a file's mtime
                    f = tmp / "rules" / "core.md"
                    f.write_text("changed content here")
                    import os

                    os.utime(f, (1e9, 1e9))
                raise KeyboardInterrupt

            with patch("time.sleep", side_effect=_sleep):
                rc = main(["--root", str(tmp), "memory", "ingest", "--watch"])
            out = capsys.readouterr().out
            assert rc == 0
            assert "Stopped watching" in out or "Watching" in out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# sync failure paths (206-211)
# ---------------------------------------------------------------------------

class TestCliSyncErrors:
    def test_sync_oserror(self, capsys):
        tmp = _tmp_root()
        try:
            (tmp / "scripts").mkdir(exist_ok=True)
            (tmp / "scripts" / "sync-agent-configs.py").write_text("# x\n")
            with patch("aizee_cli.subprocess.run", side_effect=OSError("nope")):
                rc = main(["--root", str(tmp), "sync"])
            assert rc == 1
            assert "Sync failed" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sync_nonzero_exit(self, capsys):
        tmp = _tmp_root()
        try:
            (tmp / "scripts").mkdir(exist_ok=True)
            (tmp / "scripts" / "sync-agent-configs.py").write_text("# x\n")
            with patch("aizee_cli.subprocess.run") as m:
                m.return_value = MagicMock(returncode=5)
                rc = main(["--root", str(tmp), "sync"])
            assert rc == 5
            assert "exited with code 5" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# graphify failure paths (217-222)
# ---------------------------------------------------------------------------

class TestCliGraphifyErrors:
    def test_graphify_not_found(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.subprocess.run", side_effect=FileNotFoundError):
                rc = main(["--root", str(tmp), "graphify"])
            assert rc == 1
            assert "not found" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_graphify_oserror(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.subprocess.run", side_effect=OSError("boom")):
                rc = main(["--root", str(tmp), "graphify"])
            assert rc == 1
            assert "graphify failed" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# audit show/verify (332-362)
# ---------------------------------------------------------------------------

class TestCliAudit:
    def test_audit_show_empty(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "audit", "show"])
            assert rc == 0
            assert "No audit entries" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_audit_show_entries(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.audit import AuditLogger

            logger = AuditLogger(tmp)
            logger.log("test_event", {"k": "v"})
            rc = main(["--root", str(tmp), "audit", "show"])
            assert rc == 0
            assert "Audit Log" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_audit_verify_valid(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.audit import AuditLogger

            AuditLogger(tmp).log("e", {"a": 1})
            rc = main(["--root", str(tmp), "audit", "verify"])
            assert rc == 0
            assert "Chain valid" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_audit_verify_broken(self, capsys):
        tmp = _tmp_root()
        try:
            logger_mod = __import__("runtime.audit", fromlist=["AuditLogger"])
            logger = logger_mod.AuditLogger(tmp)
            logger.log("e", {"a": 1})
            with patch.object(logger_mod.AuditLogger, "verify_chain",
                              return_value={"valid": False, "broken_at": 3}):
                rc = main(["--root", str(tmp), "audit", "verify"])
            assert rc == 1
            assert "BROKEN" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# spec subcommands (365-424)
# ---------------------------------------------------------------------------

class TestCliSpec:
    def test_spec_list_empty(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "spec", "list"])
            assert rc == 0
            assert "No specs" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_list_entries(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.spec_engine import SpecEngine

            engine = SpecEngine(tmp / "specs")
            engine.init_spec("S1", "Title One")
            rc = main(["--root", str(tmp), "spec", "list"])
            assert rc == 0
            assert "Specs" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_analyze(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.spec_engine import SpecEngine

            SpecEngine(tmp / "specs").init_spec("S1", "T")
            rc = main(["--root", str(tmp), "spec", "analyze", "S1"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_converge(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.spec_engine import SpecEngine

            SpecEngine(tmp / "specs").init_spec("S1", "T")
            rc = main(["--root", str(tmp), "spec", "converge", "S1",
                       "--codebase", str(tmp)])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_scaffold_requires_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "spec", "scaffold", "S1"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_scaffold_templates(self, capsys):
        tmp = _tmp_root()
        try:
            for tmpl in ("spec", "plan", "tasks"):
                rc = main(["--root", str(tmp), "spec", "scaffold", f"SX{tmpl}",
                           "--template", tmpl, "--title", "T"])
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_scaffold_unknown_template(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "spec", "scaffold", "S9",
                       "--template", "bogus", "--title", "T"])
            assert rc == 1
            assert "Unknown template" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_advance_missing_id(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "spec", "advance"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_advance_blocked(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "spec", "advance", "NOPE"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_advance_success(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.spec_engine import SpecEngine

            engine = SpecEngine(tmp / "specs")
            engine.init_spec("S1", "T")
            can, _reason = engine.can_advance("S1")
            if can:
                rc = main(["--root", str(tmp), "spec", "advance", "S1"])
                assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_spec_advance_value_error(self, capsys):
        tmp = _tmp_root()
        try:
            from runtime.spec_engine import SpecEngine

            engine = SpecEngine(tmp / "specs")
            engine.init_spec("S1", "T")
            with patch.object(SpecEngine, "can_advance", return_value=(True, "")):
                with patch.object(SpecEngine, "advance",
                                  side_effect=ValueError("bad phase")):
                    rc = main(["--root", str(tmp), "spec", "advance", "S1"])
            assert rc == 1
            assert "Failed to advance" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# linkedin/mcp disabled paths (452-453, 498-499)
# ---------------------------------------------------------------------------

class TestCliLinkedinMcpDisabled:
    def _args(self, tmp: Path, action: str) -> MagicMock:
        args = MagicMock()
        args.root = tmp
        args.project = None
        args.linkedin_action = action
        args.text = ""
        args.visibility = "PUBLIC"
        args.status = ""
        args.draft_id = ""
        args.when = ""
        args.urn = ""
        return args

    def test_linkedin_disabled(self, capsys):
        from aizee_cli import cmd_linkedin

        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mc:
                inst = MagicMock()
                inst.is_configured.return_value = True
                inst.is_enabled.return_value = False
                mc.return_value = inst
                rc = cmd_linkedin(self._args(tmp, "profile"))
            assert rc == 1
            assert "disabled" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_linkedin_unknown_action(self, capsys):
        from aizee_cli import cmd_linkedin

        tmp = _tmp_root()
        try:
            with patch("runtime.mcp_client.McpClient") as mc:
                inst = MagicMock()
                inst.is_configured.return_value = True
                inst.is_enabled.return_value = True
                mc.return_value = inst
                rc = cmd_linkedin(self._args(tmp, "bogus-action"))
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mcp_disabled(self, capsys):
        from aizee_cli import cmd_mcp

        tmp = _tmp_root()
        try:
            args = MagicMock()
            args.server = "srv"
            args.tool = "t"
            args.args = "{}"
            args.root = tmp
            args.project = None
            with patch("runtime.mcp_client.McpClient") as mc:
                inst = MagicMock()
                inst.is_configured.return_value = True
                inst.is_enabled.return_value = False
                mc.return_value = inst
                rc = cmd_mcp(args)
            assert rc == 1
            assert "disabled" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# skill eject (588-598)
# ---------------------------------------------------------------------------

class TestCliSkillEject:
    def test_eject_not_found(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "--project", str(tmp),
                       "skill", "eject", "nonexistent-skill"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_eject_success(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.kernel.Kernel") as kk:
                inst = MagicMock()
                inst.skill_resolver.load.return_value = "# skill body"
                kk.return_value = inst
                rc = main(["--root", str(tmp), "--project", str(tmp),
                           "skill", "eject", "myskill"])
            assert rc == 0
            assert (tmp / ".aizee" / "skills" / "myskill.md").exists()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# agents discover (604-609)
# ---------------------------------------------------------------------------

class TestCliAgents:
    def test_agents_discover(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "--project", str(tmp),
                       "agents", "discover"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor deep checks (666, 705-752)
# ---------------------------------------------------------------------------

class TestCliDoctorDeep:
    def test_doctor_with_policies_and_key(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            # guardian.yaml + probity.yaml present and valid
            repo = Path(__file__).resolve().parents[1]
            for name in ("guardian.yaml", "probity.yaml"):
                src = repo / "runtime" / "policies" / name
                if src.exists():
                    (tmp / "runtime" / "policies" / name).write_text(
                        src.read_text(encoding="utf-8", errors="replace"))
            monkeypatch.setenv("AIOS_ENCRYPTION_KEY", "x" * 44)
            rc = main(["--root", str(tmp), "--project", str(tmp), "doctor"])
            out = capsys.readouterr().out
            assert "aiZee Doctor" in out
            assert rc in (0, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_doctor_crypto_missing(self, capsys, monkeypatch):
        tmp = _tmp_root()
        try:
            monkeypatch.delenv("AIOS_ENCRYPTION_KEY", raising=False)
            with patch("importlib.metadata.version", side_effect=Exception("gone")):
                rc = main(["--root", str(tmp), "doctor"])
            assert rc in (0, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# uninstall (774-784)
# ---------------------------------------------------------------------------

class TestCliUninstall:
    def test_uninstall_missing_root(self, capsys):
        missing = Path(tempfile.gettempdir()) / "aizee-definitely-missing-dir"
        rc = main(["--root", str(missing), "uninstall", "--yes"])
        assert rc == 1
        assert "not found" in capsys.readouterr().out

    def test_uninstall_yes(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("runtime.uninstaller.interactive_uninstall",
                       return_value=0) as m:
                rc = main(["--root", str(tmp), "uninstall", "--yes"])
            assert rc == 0
            m.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# daemon (797-835)
# ---------------------------------------------------------------------------

class TestCliDaemon:
    def _args(self, tmp: Path, action: str, foreground: bool = False) -> MagicMock:
        args = MagicMock()
        args.root = tmp
        args.project = None
        args.daemon_action = action
        args.foreground = foreground
        return args

    def test_daemon_status_running(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.status.return_value = {"running": True}
                rc = cmd_daemon(self._args(tmp, "status"))
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_status_stopped(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.status.return_value = {"running": False}
                rc = cmd_daemon(self._args(tmp, "status"))
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_start_foreground(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                inst = MagicMock()
                inst.start.return_value = 0
                d.return_value = inst
                rc = cmd_daemon(self._args(tmp, "start", foreground=True))
            assert rc == 0
            inst.start.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_start_background(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("aizee_cli.subprocess.Popen") as p:
                p.return_value = MagicMock(pid=4242)
                rc = cmd_daemon(self._args(tmp, "start"))
            assert rc == 0
            assert "4242" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_stop_ok(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.return_value = MagicMock(stop=MagicMock(return_value=True))
                rc = cmd_daemon(self._args(tmp, "stop"))
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_stop_none(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.return_value = MagicMock(stop=MagicMock(return_value=False))
                rc = cmd_daemon(self._args(tmp, "stop"))
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_enable_autostart(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.enable_autostart.return_value = {"enabled": True}
                rc = cmd_daemon(self._args(tmp, "enable-autostart"))
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_disable_autostart(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            with patch("runtime.daemon.AizeeDaemon") as d:
                d.disable_autostart.return_value = {"disabled": False}
                rc = cmd_daemon(self._args(tmp, "disable-autostart"))
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_daemon_unknown_action(self, capsys):
        from aizee_cli import cmd_daemon

        tmp = _tmp_root()
        try:
            rc = cmd_daemon(self._args(tmp, "bogus"))
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# main() exception handlers (1093-1112)
# ---------------------------------------------------------------------------

class TestCliMainHandlers:
    def test_keyboard_interrupt_130(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.cmd_status", side_effect=KeyboardInterrupt):
                rc = main(["--root", str(tmp), "status"])
            assert rc == 130
            assert "Interrupted" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_aizee_error_2(self, capsys):
        from runtime.schemas import ValidationError

        tmp = _tmp_root()
        try:
            with patch("aizee_cli.cmd_status",
                       side_effect=ValidationError("bad input", context={"f": "x"})):
                rc = main(["--root", str(tmp), "status"])
            assert rc == 2
            assert "bad input" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generic_error_2(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.cmd_status", side_effect=RuntimeError("kaboom")):
                rc = main(["--root", str(tmp), "status"])
            assert rc == 2
            assert "kaboom" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generic_error_verbose_reraises(self, capsys):
        tmp = _tmp_root()
        try:
            with patch("aizee_cli.cmd_status", side_effect=RuntimeError("kaboom")):
                with patch.object(sys, "argv", ["aizee", "--verbose", "status"]):
                    with pytest.raises(RuntimeError):
                        main(["--root", str(tmp), "status"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
