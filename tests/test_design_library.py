"""Tests for runtime.design_library - brand design system catalog and mixing."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.design_library import (
    BrandDesignSystem,
    DesignLibrary,
    DesignLibraryError,
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
    # colors -> first brand, typography -> second brand
    assert result.section_mapping.get("colors") == "acme"
    assert result.section_mapping.get("typography") == "beta"

# --- import_brand (Refero/external DESIGN.md import) ---

def test_import_brand_from_text(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    system = lib.import_brand("refero-apple", "# Apple\n\n## Colors\n- #0071e3\n")
    assert system.name == "refero-apple"
    assert "0071e3" in system.content
    assert (tmp_path / "refero-apple" / "DESIGN.md").exists()
    assert "refero-apple" in lib.available_brands


def test_import_brand_from_path_objects(tmp_path: Path) -> None:
    src = tmp_path / "export" / "DESIGN.md"
    src.parent.mkdir(parents=True)
    src.write_text("# Vercel-like\n\n## Typography\n- Inter\n", encoding="utf-8")
    lib = DesignLibrary(library_dir=tmp_path / "lib")
    system = lib.import_brand("vcl", src)
    assert "Inter" in system.content
    system2 = lib.import_brand("vcl2", str(src))
    assert system2.content == system.content


def test_import_brand_missing_path_object(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    with pytest.raises(DesignLibraryError):
        lib.import_brand("nope", tmp_path / "does-not-exist.md")


def test_import_brand_no_library_dir() -> None:
    lib = DesignLibrary()
    with pytest.raises(DesignLibraryError, match="no library directory"):
        lib.import_brand("x", "# X\n")


def test_import_brand_invalid_names(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    for bad in ("", " ", ".", "..", "../evil", "a/b", "a\\b"):
        with pytest.raises(DesignLibraryError):
            lib.import_brand(bad, "# X\n")


def test_import_brand_rejects_non_markdown(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    with pytest.raises(DesignLibraryError, match="no markdown heading"):
        lib.import_brand("plain", "just text without heading")


def test_import_brand_rejects_oversized(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    with pytest.raises(DesignLibraryError, match="too large"):
        lib.import_brand("huge", "# Big\n" + "x" * (512 * 1024))


def test_import_brand_duplicate_and_overwrite(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    lib.import_brand("dupe", "# Dupe v1\n")
    with pytest.raises(DesignLibraryError, match="already exists"):
        lib.import_brand("dupe", "# Dupe v2\n")
    system = lib.import_brand("dupe", "# Dupe v2\n", overwrite=True)
    assert "v2" in system.content
    loaded = lib.load("dupe")
    assert loaded is not None and "v2" in loaded.content


def test_import_brand_write_error(tmp_path: Path) -> None:
    (tmp_path / "blocked").write_text("not a dir", encoding="utf-8")
    lib = DesignLibrary(library_dir=tmp_path)
    with pytest.raises(DesignLibraryError, match="cannot write"):
        lib.import_brand("blocked", "# Blocked\n")


def test_import_brand_unusual_string_source(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    system = lib.import_brand("raw", "# Raw\x00Weird\n\ncontent")
    assert "Raw" in system.content


def test_import_brand_invalidates_cache(tmp_path: Path) -> None:
    lib = DesignLibrary(library_dir=tmp_path)
    lib.import_brand("cached", "# Cached v1\n")
    first = lib.load("cached")
    assert first is not None and "v1" in first.content
    lib.import_brand("cached", "# Cached v2\n", overwrite=True)
    second = lib.load("cached")
    assert second is not None and "v2" in second.content

