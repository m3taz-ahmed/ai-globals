"""Gap coverage batch 18: final residual arcs.

Covers: spec/engine unknown-delta-type validation + dead apply arc,
agentic_security explicit extensions/exclude_dirs args, approval_service
from_dict with non-string status, confidence_gate weight validation,
design_library + mobile_patterns neither-dir-nor-file walk entries,
funnel_tracker non-int/non-str reached elements, llm_attestation unknown
privacy-mode passthrough, settings unknown section, dashboard
_send_settings_restart cache-flush arcs + _send_sse_events loop exhaustion,
uninstaller_gui _confirm_uninstall without backup.
"""

from __future__ import annotations

import contextlib
import io
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from runtime.agentic_security import AgenticSecurityScanner
from runtime.approval_service import ApprovalRequest, ApprovalStatus
from runtime.confidence_gate import ConfidenceGate, Evidence
from runtime.design_library import DesignLibrary
from runtime.funnel_tracker import Funnel
from runtime.llm_attestation import LlmAttestor
from runtime.mobile_patterns import _iter_files_bounded
from runtime.settings import _validate_section
from runtime.spec import engine as spec_engine
from runtime.spec.models import SpecDelta


class TestSpecEngineDeltaType:
    def test_validate_rejects_unknown_delta_type(self) -> None:
        spec = SimpleNamespace(requirements=[], deltas=[])
        bogus = SpecDelta(requirement_id="FR-1", delta_type="bogus", description="d")  # type: ignore[arg-type]
        spec.deltas.append(bogus)
        errors = spec_engine._SpecValidator.validate_deltas(spec)
        assert any("unknown delta type" in e for e in errors)

    def test_apply_single_delta_unknown_type_is_noop(self, tmp_path: Path) -> None:
        # Defensive fallthrough: a delta whose type matches no branch is
        # ignored by the applier (apply_deltas validates before calling).
        engine = spec_engine.SpecEngine(tmp_path)
        spec = engine.init_spec("proj", "title", "desc")
        bogus = SpecDelta(requirement_id="FR-1", delta_type="bogus", description="d")  # type: ignore[arg-type]
        engine._apply_single_delta(spec, bogus)
        assert spec.requirements == []


class TestAgenticSecurity:
    def test_scan_directory_explicit_args(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        report = AgenticSecurityScanner().scan_directory(
            tmp_path, extensions={".py"}, exclude_dirs={"skipme"}
        )
        assert report is not None


class TestApprovalService:
    def test_from_dict_non_string_status_passthrough(self) -> None:
        # No "status" key -> data.get() is None -> str-conversion branch skipped.
        req = ApprovalRequest.from_dict({"id": "r1", "action": "deploy", "args": {}})
        assert req.status == ApprovalStatus.PENDING


class TestConfidenceGate:
    def test_add_evidence_weight_out_of_range_raises(self) -> None:
        # Evidence.__post_init__ validates at construction; the gate's own
        # check fires when a valid Evidence is mutated afterwards (non-frozen).
        gate = ConfidenceGate(0.5)
        evidence = Evidence(source="s", passed=True, weight=0.5)
        evidence.weight = 1.5
        with pytest.raises(ValueError, match="weight"):
            gate.add_evidence(evidence)


class _FakeScandir:
    """Stand-in for os.scandir yielding a path that is neither dir nor file."""

    def __init__(self, entries: list[SimpleNamespace]) -> None:
        self._entries = entries

    def __enter__(self) -> _FakeScandir:
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def __iter__(self):
        return iter(self._entries)


def _phantom_entry(tmp_path: Path) -> SimpleNamespace:
    phantom = tmp_path / "ghost"  # never created -> is_dir()/is_file() False
    return SimpleNamespace(is_symlink=lambda: False, path=str(phantom))


class TestDesignLibraryWalk:
    def test_walk_skips_neither_dir_nor_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "os.scandir", lambda p: _FakeScandir([_phantom_entry(tmp_path)])
        )
        result = DesignLibrary().detect_project_type(tmp_path)
        assert result is not None


class TestMobilePatternsWalk:
    def test_walk_skips_neither_dir_nor_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "os.scandir", lambda p: _FakeScandir([_phantom_entry(tmp_path)])
        )
        results = _iter_files_bounded(tmp_path)
        assert results == []


class TestFunnelTracker:
    def test_reached_non_int_non_str_elements_ignored(self) -> None:
        funnel = Funnel("f")
        funnel.add_step("landing")
        funnel.record({"step_index": 0, "reached": [None, 1.5, "landing"]})
        assert funnel.steps[0].reached == 1


class TestLlmAttestation:
    def test_apply_privacy_unknown_mode_passthrough(self) -> None:
        result = LlmAttestor._apply_privacy("bogus_mode", b"data", {"k": "v"})  # type: ignore[arg-type]
        assert result == {"k": "v"}


class TestSettings:
    def test_validate_section_unknown_section_noop(self) -> None:
        _validate_section("totally_unknown_section", {"anything": 1})


class TestDashboardResiduals:
    def test_settings_restart_flushes_caches(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import dashboard.server as srv

        monkeypatch.setattr(srv, "_kernel_cache", ("k", MagicMock()))
        monkeypatch.setattr(srv, "_memory_cache", ("m", MagicMock()))
        fake = SimpleNamespace(_send=MagicMock())
        srv.DashboardHandler._send_settings_restart(fake)  # type: ignore[arg-type]
        assert srv._kernel_cache is None
        assert srv._memory_cache is None
        # Second call: caches already None -> covers the skip-the-flush arcs.
        srv.DashboardHandler._send_settings_restart(fake)  # type: ignore[arg-type]
        assert fake._send.call_count == 2

    def test_sse_events_loop_exhaustion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import dashboard.server as srv

        monkeypatch.setattr(
            srv, "time", SimpleNamespace(sleep=lambda _s: None, time=time.time)
        )
        srv.DashboardHandler._sse_clients = 0
        fake = SimpleNamespace(
            _origin=lambda: "",
            send_response=MagicMock(),
            send_header=MagicMock(),
            end_headers=MagicMock(),
            kernel=SimpleNamespace(status=lambda: {}),
            wfile=io.BytesIO(),
            _sse_lock=threading.Lock(),
        )
        srv.DashboardHandler._send_sse_events(fake)  # type: ignore[arg-type]
        assert srv.DashboardHandler._sse_clients == 0
        assert fake.wfile.getvalue().count(b"data:") == 120


class TestUninstallerGui:
    def test_confirm_uninstall_without_backup(self, tmp_path: Path) -> None:
        pytest.importorskip("tkinter")
        from runtime.uninstaller_gui import UninstallerGUI

        (tmp_path / "pyproject.toml").write_text("[project]\nname='aizee'\n")
        (tmp_path / "aizee_cli.py").write_text("# cli")
        (tmp_path / "config.py").write_text("# config")
        (tmp_path / ".aizee-version").write_text("5.0.0")
        (tmp_path / "runtime").mkdir(exist_ok=True)
        (tmp_path / "runtime" / "kernel.py").write_text("# k")
        (tmp_path / "memory").mkdir(exist_ok=True)
        (tmp_path / "memory" / "store.db").write_bytes(b"fake")
        (tmp_path / "state").mkdir(exist_ok=True)
        try:
            gui = UninstallerGUI(tmp_path)
        except Exception:
            pytest.skip("tkinter not functional")
        try:
            gui.backup_var.set(False)
            with patch("runtime.uninstaller_gui.messagebox") as mb:
                mb.askyesno.return_value = True
                assert gui._confirm_uninstall([]) is True
        finally:
            with contextlib.suppress(Exception):
                gui.win.destroy()
