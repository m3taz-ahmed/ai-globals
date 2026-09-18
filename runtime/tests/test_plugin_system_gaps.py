"""Gap-coverage tests for runtime/plugin_system.py — hooks, discovery edges."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.plugin_system import (
    HookPhase,
    PluginError,
    PluginManifest,
    PluginRegistry,
    PluginStatus,
    _as_str_list,
)


def _make_plugin(tmp_path: Path, name: str = "p1", **manifest_kw) -> Path:
    d = tmp_path / "plugins" / name
    d.mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "description": "test plugin"}
    manifest.update(manifest_kw)
    (d / "plugin.json").write_text(json.dumps(manifest))
    return d


class TestManifest:
    def test_non_dict(self):
        with pytest.raises(PluginError, match="JSON object"):
            PluginManifest.from_dict(["x"])

    def test_missing_name(self):
        with pytest.raises(PluginError, match="name"):
            PluginManifest.from_dict({"description": "d"})

    def test_invalid_name_chars(self):
        with pytest.raises(PluginError, match="Invalid plugin name"):
            PluginManifest.from_dict({"name": "bad name!", "description": "d"})

    def test_name_too_long(self):
        with pytest.raises(PluginError):
            PluginManifest.from_dict({"name": "x" * 200, "description": "d"})

    def test_bad_type(self):
        with pytest.raises(PluginError, match="Invalid plugin type"):
            PluginManifest.from_dict(
                {"name": "p", "description": "d", "type": "bogus"})

    def test_hooks_dict_parsed(self):
        m = PluginManifest.from_dict({
            "name": "p", "description": "d",
            "hooks": {"Stop": "hooks/stop.py", 123: 45}})
        assert m.hooks["Stop"] == "hooks/stop.py"
        assert m.hooks["123"] == "45"

    def test_hooks_non_dict_ignored(self):
        m = PluginManifest.from_dict(
            {"name": "p", "description": "d", "hooks": ["x"]})
        assert m.hooks == {}

    def test_as_str_list(self):
        assert _as_str_list(["a", 1]) == ["a", "1"]
        assert _as_str_list("single") == ["single"]
        assert _as_str_list(None) == []
        assert _as_str_list(5) == []


class TestDiscover:
    def test_no_dir(self):
        assert PluginRegistry(Path("/nonexistent-dir-xyz")).discover() == 0
        assert PluginRegistry(None).discover() == 0

    def test_skips_files_and_missing_manifest(self, tmp_path):
        pdir = tmp_path / "plugins"
        pdir.mkdir()
        (pdir / "afile.txt").write_text("x")
        (pdir / "no-manifest").mkdir()
        _make_plugin(tmp_path, "good")
        reg = PluginRegistry(pdir)
        assert reg.discover() == 1

    def test_broken_manifest_skipped(self, tmp_path):
        _make_plugin(tmp_path, "good")
        bad = tmp_path / "plugins" / "bad"
        bad.mkdir()
        (bad / "plugin.json").write_text("{corrupt")
        bad2 = tmp_path / "plugins" / "bad2"
        bad2.mkdir()
        (bad2 / "plugin.json").write_text(json.dumps({"name": "x"}))
        reg = PluginRegistry(tmp_path / "plugins")
        assert reg.discover() == 1


class TestLifecycle:
    def _reg(self, tmp_path):
        _make_plugin(tmp_path, "p1")
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        return reg

    def test_activate_and_deactivate(self, tmp_path):
        reg = self._reg(tmp_path)
        assert reg.activate("p1") is True
        assert reg.get("p1").is_active
        assert reg.deactivate("p1") is True
        assert reg.get("p1").status is PluginStatus.DISCOVERED
        assert reg.activate("missing") is False
        assert reg.deactivate("missing") is False

    def test_activate_missing_dependency(self, tmp_path):
        _make_plugin(tmp_path, "p1", dependencies=["dep-x"])
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert reg.activate("p1") is False
        assert reg.get("p1").status is PluginStatus.ERROR
        assert "Unmet" in reg.get("p1").error

    def test_activate_inactive_dependency(self, tmp_path):
        _make_plugin(tmp_path, "dep")
        _make_plugin(tmp_path, "p1", dependencies=["dep"])
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert reg.activate("p1") is False  # dep exists but inactive
        reg.activate("dep")
        assert reg.activate("p1") is True

    def test_list_by_status(self, tmp_path):
        reg = self._reg(tmp_path)
        reg.activate("p1")
        assert len(reg.list_plugins(status=PluginStatus.ACTIVE)) == 1
        assert len(reg.list_plugins(status=PluginStatus.DISCOVERED)) == 0
        assert len(reg.list_plugins()) == 1

    def test_stats(self, tmp_path):
        reg = self._reg(tmp_path)
        reg.activate("p1")
        s = reg.stats()
        assert s["total"] == 1 and s["active"] == 1 and s["active"] == 1


class TestSearch:
    def test_find_by_keyword(self, tmp_path):
        _make_plugin(tmp_path, "p1", keywords=["Flutter", "mobile"])
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert [p.name for p in reg.find_by_keyword("flutter")] == ["p1"]
        assert [p.name for p in reg.find_by_keyword("flutter app")] == ["p1"]
        assert reg.find_by_keyword("zzz") == []

    def test_find_by_persona(self, tmp_path):
        _make_plugin(tmp_path, "p1", personas=["arch"])
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert [p.name for p in reg.find_by_persona("arch")] == ["p1"]
        assert reg.find_by_persona("nope") == []


class TestLoadSkill:
    def _reg_active(self, tmp_path):
        pdir = _make_plugin(tmp_path, "p1")
        (pdir / "skills" / "sk").mkdir(parents=True)
        (pdir / "skills" / "sk" / "SKILL.md").write_text("# skill content")
        (pdir / "skills" / "flat.md").write_text("# flat")
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        reg.activate("p1")
        return reg

    def test_load_dir_skill(self, tmp_path):
        reg = self._reg_active(tmp_path)
        assert reg.load_skill("p1", "sk") == "# skill content"

    def test_load_flat_skill(self, tmp_path):
        reg = self._reg_active(tmp_path)
        assert reg.load_skill("p1", "flat") == "# flat"

    def test_inactive_plugin(self, tmp_path):
        _make_plugin(tmp_path, "p1")
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert reg.load_skill("p1", "sk") is None  # not active
        assert reg.load_skill("missing", "sk") is None

    def test_traversal_rejected(self, tmp_path):
        reg = self._reg_active(tmp_path)
        assert reg.load_skill("p1", "../outside") is None
        assert reg.load_skill("p1", "/abs") is None
        assert reg.load_skill("p1", "") is None
        assert reg.load_skill("p1", "nonexistent") is None

    def test_oversize_skill_rejected(self, tmp_path):
        pdir = _make_plugin(tmp_path, "p1")
        (pdir / "skills" / "big").mkdir(parents=True)
        (pdir / "skills" / "big" / "SKILL.md").write_text("x" * 200_001)
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        reg.activate("p1")
        assert reg.load_skill("p1", "big") is None

    def test_read_error(self, tmp_path):
        reg = self._reg_active(tmp_path)
        with patch.object(Path, "read_text", side_effect=OSError):
            assert reg.load_skill("p1", "sk") is None


class TestRunHook:
    def _reg_with_hook(self, tmp_path, hook_rel="hooks/stop.py", script=None):
        pdir = _make_plugin(
            tmp_path, "p1", hooks={"Stop": hook_rel})
        if script is not None:
            hp = pdir / hook_rel
            hp.parent.mkdir(parents=True, exist_ok=True)
            hp.write_text(script)
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        reg.activate("p1")
        return reg

    def test_hook_success(self, tmp_path):
        reg = self._reg_with_hook(
            tmp_path, script="import sys,json; d=json.load(sys.stdin); print('HOOK:'+d.get('k',''))")
        out = reg.run_hook("p1", HookPhase.STOP, {"k": "v"})
        assert out == "HOOK:v"

    def test_hook_no_output(self, tmp_path):
        reg = self._reg_with_hook(tmp_path, script="pass")
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_nonzero_exit(self, tmp_path):
        reg = self._reg_with_hook(tmp_path, script="import sys; sys.exit(2)")
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_timeout(self, tmp_path):
        import subprocess
        reg = self._reg_with_hook(tmp_path, script="pass")
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("x", 30)):
            assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_exception(self, tmp_path):
        reg = self._reg_with_hook(tmp_path, script="pass")
        with patch("subprocess.run", side_effect=OSError):
            assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_path_rejected(self, tmp_path):
        reg = self._reg_with_hook(tmp_path, hook_rel="../escape.py")
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_non_py_rejected(self, tmp_path):
        reg = self._reg_with_hook(tmp_path, hook_rel="hooks/x.sh")
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_missing_file(self, tmp_path):
        reg = self._reg_with_hook(tmp_path)  # script never written
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_no_phase_configured(self, tmp_path):
        _make_plugin(tmp_path, "p1")
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        reg.activate("p1")
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None

    def test_hook_inactive_plugin(self, tmp_path):
        _make_plugin(tmp_path, "p1", hooks={"Stop": "h.py"})
        reg = PluginRegistry(tmp_path / "plugins")
        reg.discover()
        assert reg.run_hook("p1", HookPhase.STOP, {}) is None
        assert reg.run_hook("missing", HookPhase.STOP, {}) is None
