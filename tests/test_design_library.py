"""Tests for runtime.design_library — brand design system catalog and mixing."""

from __future__ import annotations

from pathlib import Path

from runtime.design_library import (
    BrandDesignSystem,
    DesignLibrary,
    DesignSection,
    FusionResult,
    ProjectType,
)

# --- Catalog ---

def test_available_brands_includes_catalog() -> None:
    lib = DesignLibrary()
    brands = lib.available_brands
    assert "stripe" in brands
    assert "linear" in brands
    assert "vercel" in brands


# --- Loading ---

def _write_brand(dir: Path, name: str, content: str = "# Brand\n") -> Path:
    brand_dir = dir / name
    brand_dir.mkdir(parents=True, exist_ok=True)
    design_file = brand_dir / "DESIGN.md"
    design_file.write_text(content, encoding="utf-8")
    return design_file


def test_load_brand_from_filesystem(tmp_path: Path) -> None:
    _write_brand(tmp_path, "acme", "# Acme\n\nA custom brand.\n")
    lib = DesignLibrary(library_dir=tmp_path)
    system = lib.load("acme")
    assert system is not None
    assert isinstance(system, BrandDesignSystem)
    assert "Acme" in system.content


def test_load_brand_not_found(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    assert lib.load("nonexistent") is None


def test_load_brand_caches(tmp_path: Path) -> None:
    _write_brand(tmp_path, "acme", "# Acme\n")
    lib = DesignLibrary(library_dir=tmp_path)
    first = lib.load("acme")
    second = lib.load("acme")
    assert first is not None
    assert first is second


# --- Mixing ---

def test_mix_two_brands(tmp_path: Path) -> None:
    _write_brand(tmp_path, "acme", "# Acme\n\n## Colors\nred\n\n## Typography\nsans\n")
    _write_brand(tmp_path, "beta", "# Beta\n\n## Colors\nblue\n\n## Typography\nserif\n")
    lib = DesignLibrary(library_dir=tmp_path)
    result = lib.mix(["acme", "beta"])
    assert result is not None
    assert isinstance(result, FusionResult)
    assert "acme" in result.brands
    assert "beta" in result.brands


def test_mix_missing_brand(tmp_path: Path) -> None:
    _write_brand(tmp_path, "acme", "# Acme\n")
    lib = DesignLibrary(library_dir=tmp_path)
    assert lib.mix(["acme", "nonexistent"]) is None


# --- Suggestions ---

def test_suggest_for_landing_page() -> None:
    lib = DesignLibrary()
    suggestions = lib.suggest(ProjectType.LANDING_PAGE)
    assert isinstance(suggestions, list)
    assert "linear" in suggestions or "vercel" in suggestions


def test_suggest_unknown_type() -> None:
    lib = DesignLibrary()
    suggestions = lib.suggest(ProjectType.UNKNOWN)
    assert len(suggestions) > 0


# --- Project type detection ---

def test_detect_project_type_ecommerce(tmp_path: Path) -> None:
    (tmp_path / "shop.py").write_text("print('shop')", encoding="utf-8")
    (tmp_path / "cart.py").write_text("print('cart')", encoding="utf-8")
    lib = DesignLibrary()
    assert lib.detect_project_type(tmp_path) == ProjectType.ECOMMERCE


def test_detect_project_type_empty(tmp_path: Path) -> None:
    lib = DesignLibrary()
    assert lib.detect_project_type(tmp_path) == ProjectType.UNKNOWN


# --- Section extraction ---

def test_get_section_extracts_content(tmp_path: Path) -> None:
    content = "# Acme\n\n## Colors\n- red\n- blue\n\n## Typography\n- sans\n"
    _write_brand(tmp_path, "acme", content)
    lib = DesignLibrary(library_dir=tmp_path)
    system = lib.load("acme")
    assert system is not None
    section = system.get_section(DesignSection.COLORS)
    assert "Colors" in section
    assert "red" in section


# --- Default mapping ---

def test_default_mapping(tmp_path: Path) -> None:
    _write_brand(tmp_path, "acme", "# Acme\n\n## Colors\nred\n\n## Typography\nsans\n")
    _write_brand(tmp_path, "beta", "# Beta\n\n## Colors\nblue\n\n## Typography\nserif\n")
    lib = DesignLibrary(library_dir=tmp_path)
    result = lib.mix(["acme", "beta"])
    assert result is not None
    # colors → first brand, typography → second brand
    assert result.section_mapping.get("colors") == "acme"
    assert result.section_mapping.get("typography") == "beta"
