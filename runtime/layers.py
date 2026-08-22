"""Numbered package layering — enforce dependency direction via numeric prefixes.

Inspired by Prisma's numbered package prefixes (``1-framework``, ``2-sql``,
``3-targets``) which encode dependency direction and prevent circular deps.
Applied to aiZee runtime modules to keep the architecture layered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity


class Layer(IntEnum):
    """Architectural layers in dependency order (lower = more foundational)."""

    CORE = 1
    RUNTIME = 2
    MANAGERS = 3
    MCP = 4
    TOOLS = 5
    CLI = 6


# Default layer assignment for aiZee top-level packages.
DEFAULT_LAYERS: dict[str, Layer] = {
    "config": Layer.CORE,
    "runtime": Layer.RUNTIME,
    "runtime/managers": Layer.MANAGERS,
    "aizee_mcp": Layer.MCP,
    "aizee_mcp/tools": Layer.TOOLS,
    "aizee_cli": Layer.CLI,
    "memory": Layer.CORE,
    "eval": Layer.TOOLS,
    "dashboard": Layer.TOOLS,
    "scripts": Layer.TOOLS,
    "skills": Layer.TOOLS,
    "workflows": Layer.TOOLS,
    "tech-stack": Layer.TOOLS,
    "rules": Layer.CORE,
}


class LayerError(AizeeError):
    """Raised when a layer dependency violation is detected."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("LAYER_VIOLATION", message, ErrorSeverity.MEDIUM, context)


@dataclass
class LayerViolation:
    """A single layer dependency violation."""

    source: str
    target: str
    source_layer: Layer
    target_layer: Layer
    detail: str = ""


@dataclass
class LayerManifest:
    """Manifest of package → layer assignments."""

    layers: dict[str, Layer] = field(default_factory=lambda: dict(DEFAULT_LAYERS))

    def layer_of(self, package: str) -> Layer | None:
        """Return the layer for a package, or None if unregistered."""
        if package in self.layers:
            return self.layers[package]
        # Try parent package (e.g. "runtime/managers" → "runtime")
        parts = package.split("/")
        for i in range(len(parts), 0, -1):
            candidate = "/".join(parts[:i])
            if candidate in self.layers:
                return self.layers[candidate]
        return None

    def can_depend(self, source: str, target: str) -> bool:
        """True if source package may depend on target package (layer order)."""
        src_layer = self.layer_of(source)
        tgt_layer = self.layer_of(target)
        if src_layer is None or tgt_layer is None:
            return True  # unregistered packages are unconstrained
        # A package may depend on same or lower layer, never higher.
        return src_layer >= tgt_layer

    def register(self, package: str, layer: Layer) -> LayerManifest:
        """Register a package under a layer. Returns self for chaining."""
        self.layers[package] = layer
        return self


def check_import_layering(
    source_file: Path,
    import_target: str,
    manifest: LayerManifest | None = None,
) -> LayerViolation | None:
    """Check if an import from source_file to import_target violates layering.

    ``import_target`` is the top-level module name (e.g. ``runtime``, ``aizee_mcp``).
    Returns a LayerViolation if the dependency is illegal, None if OK.
    """
    man = manifest or LayerManifest()
    source_pkg = _package_for_path(source_file)
    target_pkg = import_target.split(".")[0]
    if not man.can_depend(source_pkg, target_pkg):
        src_layer = man.layer_of(source_pkg) or Layer.CORE
        tgt_layer = man.layer_of(target_pkg) or Layer.CORE
        return LayerViolation(
            source=source_pkg,
            target=target_pkg,
            source_layer=src_layer,
            target_layer=tgt_layer,
            detail=f"{source_pkg} (L{src_layer.value}) imports {target_pkg} (L{tgt_layer.value})",
        )
    return None


def _package_for_path(path: Path) -> str:
    """Derive the aiZee package name from a file path (best effort)."""
    parts = path.parts
    for key in ("runtime", "aizee_mcp", "memory", "eval", "dashboard", "scripts", "aizee_cli", "config"):
        if key in parts:
            idx = parts.index(key)
            sub = "/".join(parts[idx : idx + 2])
            return sub if idx + 1 < len(parts) else key
    # Check if the file stem itself is a known package (e.g. config.py → "config")
    stem = path.stem
    if stem in DEFAULT_LAYERS:
        return stem
    return "unknown"
