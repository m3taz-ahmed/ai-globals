"""Tests for runtime/layers.py — LayerManifest + layer checking."""
from __future__ import annotations

from pathlib import Path

from runtime.layers import (
    DEFAULT_LAYERS,
    Layer,
    LayerError,
    LayerManifest,
    LayerViolation,
    check_import_layering,
)


def test_layer_enum_values() -> None:
    assert Layer.CORE < Layer.RUNTIME < Layer.MANAGERS < Layer.MCP < Layer.TOOLS < Layer.CLI


def test_default_layers_cover_core_packages() -> None:
    assert "runtime" in DEFAULT_LAYERS
    assert DEFAULT_LAYERS["runtime"] is Layer.RUNTIME
    assert DEFAULT_LAYERS["aizee_mcp"] is Layer.MCP


def test_manifest_layer_of_registered() -> None:
    manifest = LayerManifest()
    assert manifest.layer_of("runtime") is Layer.RUNTIME
    assert manifest.layer_of("aizee_mcp") is Layer.MCP


def test_manifest_layer_of_child_path() -> None:
    manifest = LayerManifest()
    assert manifest.layer_of("runtime/managers") is Layer.MANAGERS
    # Falls back to parent
    assert manifest.layer_of("runtime/some_new_module") is Layer.RUNTIME


def test_manifest_layer_of_unknown_returns_none() -> None:
    manifest = LayerManifest()
    assert manifest.layer_of("nonexistent_package") is None


def test_manifest_can_depend_same_or_lower() -> None:
    manifest = LayerManifest()
    # MCP (L4) can depend on RUNTIME (L2)
    assert manifest.can_depend("aizee_mcp", "runtime") is True
    # RUNTIME (L2) cannot depend on MCP (L4)
    assert manifest.can_depend("runtime", "aizee_mcp") is False
    # Same layer OK
    assert manifest.can_depend("runtime", "runtime") is True


def test_manifest_can_depend_unknown_is_allowed() -> None:
    manifest = LayerManifest()
    assert manifest.can_depend("unknown_a", "unknown_b") is True


def test_manifest_register_custom() -> None:
    manifest = LayerManifest()
    manifest.register("custom_pkg", Layer.TOOLS)
    assert manifest.layer_of("custom_pkg") is Layer.TOOLS


def test_check_import_layering_ok() -> None:
    manifest = LayerManifest()
    # A runtime file importing config (CORE) is fine
    result = check_import_layering(
        Path("D:/aizee/runtime/kernel.py"),
        "config",
        manifest,
    )
    assert result is None


def test_check_import_layering_violation() -> None:
    manifest = LayerManifest()
    # A config file importing aizee_mcp (MCP > CORE) is a violation
    result = check_import_layering(
        Path("D:/aizee/config.py"),
        "aizee_mcp",
        manifest,
    )
    assert result is not None
    assert isinstance(result, LayerViolation)
    assert result.target == "aizee_mcp"
    assert result.source_layer is Layer.CORE
    assert result.target_layer is Layer.MCP


def test_layer_violation_dataclass() -> None:
    v = LayerViolation(
        source="runtime",
        target="aizee_mcp",
        source_layer=Layer.RUNTIME,
        target_layer=Layer.MCP,
        detail="test",
    )
    assert v.source == "runtime"
    assert v.detail == "test"


def test_layer_error_is_aizee_error() -> None:
    err = LayerError("test violation")
    assert err.error_code == "LAYER_VIOLATION"
