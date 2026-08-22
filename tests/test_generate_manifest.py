"""Tests for scripts/generate_manifest.py — manifest parsing + generation."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

# scripts/ is not a package — load by file path
_spec = importlib.util.spec_from_file_location(
    "generate_manifest",
    Path(__file__).resolve().parent.parent / "scripts" / "generate_manifest.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
sys.modules["generate_manifest"] = _mod
_spec.loader.exec_module(_mod)

Manifest = _mod.Manifest
ManifestEntry = _mod.ManifestEntry
generate_init_source = _mod.generate_init_source
load_manifest_json = _mod.load_manifest_json
parse_existing_init = _mod.parse_existing_init
write_manifest_json = _mod.write_manifest_json


def test_manifest_entry_import_line_no_alias() -> None:
    entry = ManifestEntry(module="runtime.commands", symbol="Command")
    assert entry.import_line == "from runtime.commands import Command"


def test_manifest_entry_import_line_with_alias() -> None:
    entry = ManifestEntry(module="runtime.commands", symbol="Command", alias="Cmd")
    assert entry.import_line == "from runtime.commands import Command as Cmd"


def test_manifest_entry_export_name() -> None:
    assert ManifestEntry(module="m", symbol="X").export_name == "X"
    assert ManifestEntry(module="m", symbol="X", alias="Y").export_name == "Y"


def test_manifest_add_chaining() -> None:
    m = Manifest()
    ret = m.add("runtime.commands", "Command")
    assert ret is m
    assert len(m.entries) == 1


def test_manifest_export_names_sorted_unique() -> None:
    m = Manifest()
    m.add("a", "Zebra")
    m.add("b", "Apple")
    m.add("c", "Zebra", alias="Zebra")  # dup
    names = m.export_names
    assert names == ["Apple", "Zebra"]


def test_manifest_to_dict_from_dict_roundtrip() -> None:
    m = Manifest()
    m.add("runtime.commands", "Command")
    m.add("runtime.hook_lifecycle", "HookPhase", alias="Phase")
    data = m.to_dict()
    m2 = Manifest.from_dict(data)
    assert len(m2.entries) == 2
    assert m2.entries[0].module == "runtime.commands"
    assert m2.entries[1].alias == "Phase"


def test_generate_init_source_basic() -> None:
    m = Manifest()
    m.add("runtime.commands", "Command")
    src = generate_init_source(m)
    assert "from __future__ import annotations" in src
    assert "from runtime.commands import Command" in src
    assert '"Command"' in src
    assert "__all__" in src


def test_generate_init_source_with_version() -> None:
    m = Manifest()
    src = generate_init_source(m, version_module="config")
    assert "import config" in src
    assert "__version__ = config.VERSION" in src


def test_parse_existing_init_extracts_imports() -> None:
    source = '''"""test"""
import config
__version__ = config.VERSION
from runtime.commands import Command
from runtime.hook_lifecycle import HookPhase as Phase

__all__ = ["Command", "Phase"]
'''
    m = parse_existing_init(source)
    assert len(m.entries) == 2
    assert m.entries[0].module == "runtime.commands"
    assert m.entries[1].alias == "Phase"


def test_parse_existing_init_skips_config() -> None:
    source = "import config\nfrom runtime.commands import Command\n"
    m = parse_existing_init(source)
    assert all(e.module != "config" for e in m.entries)


def test_write_and_load_manifest_json() -> None:
    m = Manifest()
    m.add("runtime.commands", "Command")
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "manifest.json"
        write_manifest_json(m, path)
        assert path.exists()
        loaded = load_manifest_json(path)
        assert len(loaded.entries) == 1
        assert loaded.entries[0].symbol == "Command"
