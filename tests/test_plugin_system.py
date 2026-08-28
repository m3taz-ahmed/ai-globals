"""Tests for runtime.plugin_system — PluginRegistry and PluginManifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.plugin_system import (
    PluginError,
    PluginManifest,
    PluginRegistry,
    PluginStatus,
    PluginType,
)

# --- Manifest parsing ---

def test_manifest_from_dict_valid() -> None:
    data = {
        "name": "my-plugin",
        "version": "1.2.0",
        "description": "A test plugin.",
        "type": "bundle",
        "author": "tester",
        "keywords": ["design", "ui"],
        "personas": ["frontend"],
        "skills": ["my-skill"],
        "dependencies": ["core"],
    }
    m = PluginManifest.from_dict(data)
    assert m.name == "my-plugin"
    assert m.version == "1.2.0"
    assert m.description == "A test plugin."
    assert m.type == PluginType.BUNDLE
    assert m.author == "tester"
    assert m.keywords == ["design", "ui"]
    assert m.personas == ["frontend"]
    assert m.skills == ["my-skill"]
    assert m.dependencies == ["core"]


def test_manifest_missing_name_raises() -> None:
    with pytest.raises(PluginError):
        PluginManifest.from_dict({"description": "no name"})


def test_manifest_missing_description_raises() -> None:
    with pytest.raises(PluginError):
        PluginManifest.from_dict({"name": "no-desc"})


# --- Registry discover / get / activate ---

def _write_plugin(dir: Path, name: str, **extra: object) -> None:
    pdir = dir / name
    pdir.mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "version": "0.1.0", "description": f"{name} plugin", **extra}
    (pdir / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_registry_discover(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    _write_plugin(tmp_path, "beta")
    reg = PluginRegistry(plugins_dir=tmp_path)
    assert reg.discover() == 2


def test_registry_get(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    plugin = reg.get("alpha")
    assert plugin is not None
    assert plugin.name == "alpha"


def test_registry_activate(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    assert reg.activate("alpha")
    assert reg.get("alpha").status == PluginStatus.ACTIVE


def test_registry_activate_missing_dependency(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha", dependencies=["nonexistent"])
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    assert not reg.activate("alpha")
    assert reg.get("alpha").status == PluginStatus.ERROR


def test_registry_deactivate(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    reg.activate("alpha")
    assert reg.deactivate("alpha")
    assert reg.get("alpha").status == PluginStatus.DISCOVERED


# --- Keyword / persona search ---

def test_registry_find_by_keyword(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha", keywords=["design", "ui"])
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    results = reg.find_by_keyword("design")
    assert len(results) == 1
    assert results[0].name == "alpha"


def test_registry_find_by_persona(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha", personas=["frontend"])
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    results = reg.find_by_persona("frontend")
    assert len(results) == 1
    assert results[0].name == "alpha"


# --- Skill loading ---

def test_registry_load_skill(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    skill_dir = tmp_path / "alpha" / "skills" / "my-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# My Skill\nDo things.", encoding="utf-8")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    reg.activate("alpha")
    content = reg.load_skill("alpha", "my-skill")
    assert content is not None
    assert "My Skill" in content


def test_registry_load_skill_not_found(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    reg.activate("alpha")
    assert reg.load_skill("alpha", "missing") is None


# --- Stats / empty ---

def test_registry_stats(tmp_path: Path) -> None:
    _write_plugin(tmp_path, "alpha")
    _write_plugin(tmp_path, "beta")
    reg = PluginRegistry(plugins_dir=tmp_path)
    reg.discover()
    stats = reg.stats()
    assert "total" in stats
    assert "active" in stats
    assert stats["total"] == 2


def test_registry_empty_dir(tmp_path: Path) -> None:
    reg = PluginRegistry(plugins_dir=tmp_path / "does-not-exist")
    assert reg.discover() == 0
