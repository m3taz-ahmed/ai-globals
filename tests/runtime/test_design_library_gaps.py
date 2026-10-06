"""Gap tests for runtime/design_library.py."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from runtime.design_library import (
    BrandDesignSystem,
    DesignLibrary,
    DesignLibraryError,
    DesignSection,
    ProjectType,
)


def _brand_dir(root: Path, name: str, content: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    (d / "DESIGN.md").write_text(content, encoding="utf-8")
    return d


class TestGetSection:
    def test_cached_and_extracted(self, tmp_path):
        sys = BrandDesignSystem(name="b", path=tmp_path / "D.md", content="## Colors\nred\n\n## Type\nsans")
        assert "red" in sys.get_section(DesignSection.COLORS)
        # second call hits cache
        assert sys.get_section(DesignSection.COLORS) is sys.sections["colors"]

    def test_missing_section(self, tmp_path):
        sys = BrandDesignSystem(name="b", path=tmp_path / "D.md", content="nothing")
        assert sys.get_section(DesignSection.LAYOUT) == ""

    def test_section_at_end(self, tmp_path):
        sys = BrandDesignSystem(name="b", path=tmp_path / "D.md", content="## Head\n\n## Layout\ngrid")
        assert "grid" in sys.get_section(DesignSection.LAYOUT)


class TestLibrary:
    def test_available_brands_filesystem(self, tmp_path):
        _brand_dir(tmp_path, "MyBrand", "x")
        (tmp_path / "empty").mkdir()  # dir without DESIGN.md ignored
        lib = DesignLibrary(tmp_path)
        assert "mybrand" in lib.available_brands
        assert "stripe" in lib.available_brands  # catalog
        assert "empty" not in lib.available_brands

    def test_load_traversal_rejected(self, tmp_path):
        lib = DesignLibrary(tmp_path)
        assert lib.load("../etc") is None
        assert lib.load("a/b") is None
        assert lib.load("..") is None
        assert lib.load("") is None

    def test_load_no_dir(self):
        lib = DesignLibrary(None)
        assert lib.load("stripe") is None

    def test_load_missing_file(self, tmp_path):
        lib = DesignLibrary(tmp_path)
        assert lib.load("nonexistent") is None

    def test_load_read_oserror(self, tmp_path):
        _brand_dir(tmp_path, "b1", "content")
        lib = DesignLibrary(tmp_path)
        with patch.object(Path, "read_text", side_effect=OSError("locked")):
            assert lib.load("b1") is None

    def test_load_caches(self, tmp_path):
        _brand_dir(tmp_path, "b2", "cached content")
        lib = DesignLibrary(tmp_path)
        a = lib.load("B2")
        b = lib.load("b2")
        assert a is b

    def test_error_ctor(self):
        err = DesignLibraryError("x")
        assert err.error_code == "DESIGN_LIBRARY_ERROR"


class TestMix:
    def test_missing_brand_returns_none(self, tmp_path):
        lib = DesignLibrary(tmp_path)
        assert lib.mix(["nope1", "nope2"]) is None

    def test_unknown_brand_in_mapping_aborts(self, tmp_path):
        _brand_dir(tmp_path, "aa", "## Colors\nred")
        _brand_dir(tmp_path, "bb", "## Typography\nsans")
        lib = DesignLibrary(tmp_path)
        out = lib.mix(["aa", "bb"], section_mapping={DesignSection.COLORS: "ghost"})
        assert out is None

    def test_explicit_mapping_and_empty_section(self, tmp_path):
        _brand_dir(tmp_path, "aa", "## Colors\nred")
        _brand_dir(tmp_path, "bb", "no sections here")
        lib = DesignLibrary(tmp_path)
        out = lib.mix(["aa", "bb"], section_mapping={
            DesignSection.COLORS: "aa",
            DesignSection.LAYOUT: "bb",  # bb has no layout section -> skipped
        })
        assert out is not None
        assert "red" in out.content
        assert "layout" not in out.section_mapping

    def test_default_mapping(self, tmp_path):
        _brand_dir(tmp_path, "aa", "## Colors\nred\n## Components\nbtn")
        _brand_dir(tmp_path, "bb", "## Typography\nsans\n## Layout\ngrid")
        lib = DesignLibrary(tmp_path)
        out = lib.mix(["aa", "bb"])
        assert out is not None
        assert out.section_mapping["colors"] == "aa"
        assert out.section_mapping["typography"] == "bb"
        assert "Fusion: aa + bb" in out.rationale


class TestProjectType:
    def test_missing_dir(self, tmp_path):
        lib = DesignLibrary(tmp_path)
        assert lib.detect_project_type(tmp_path / "nope") is ProjectType.UNKNOWN

    def test_no_scores(self, tmp_path):
        lib = DesignLibrary(tmp_path)
        # empty scan result -> no keyword scores -> UNKNOWN
        with patch("runtime.design_library.os.scandir") as sc:
            ctx = sc.return_value.__enter__.return_value
            ctx.__iter__.return_value = iter([])
            assert lib.detect_project_type(tmp_path) is ProjectType.UNKNOWN

    def test_detects_mobile(self, tmp_path):
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "expo.json").write_text("{}")
        lib = DesignLibrary(tmp_path)
        assert lib.detect_project_type(tmp_path) is ProjectType.MOBILE_APP

    def test_skips_vendored_dirs(self, tmp_path):
        (tmp_path / "node_modules" / "x").mkdir(parents=True)
        (tmp_path / "node_modules" / "x" / "dashboard.js").write_text("x")
        lib = DesignLibrary(tmp_path)
        # dashboard.js under node_modules is skipped -> no dashboard score
        assert lib.detect_project_type(tmp_path) is not ProjectType.DASHBOARD

    def test_scandir_oserror(self, tmp_path):
        (tmp_path / "sub").mkdir()
        lib = DesignLibrary(tmp_path)
        orig = os.scandir
        def boom(p):
            if Path(p) == tmp_path / "sub":
                raise OSError("denied")
            return orig(p)
        with patch("runtime.design_library.os.scandir", side_effect=boom):
            assert lib.detect_project_type(tmp_path) is ProjectType.UNKNOWN

    def test_entry_is_symlink_skipped(self, tmp_path):
        # target outside scanned root holds the keyword; if the symlink were
        # followed the cart keyword would be found
        outside = tmp_path.parent / "outside_symlink_target"
        outside.mkdir(exist_ok=True)
        (outside / "cart.py").write_text("x")
        link = tmp_path / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            # no symlink privilege -> simulate via is_symlink patch
            lib = DesignLibrary(tmp_path)
            with patch.object(Path, "is_symlink", return_value=True):
                assert lib.detect_project_type(tmp_path) is ProjectType.UNKNOWN
            return
        lib = DesignLibrary(tmp_path)
        assert lib.detect_project_type(tmp_path) is not ProjectType.ECOMMERCE

    def test_symlink_entry_oserror(self, tmp_path):
        (tmp_path / "f.py").write_text("x")
        lib = DesignLibrary(tmp_path)
        with patch("os.DirEntry.is_symlink", side_effect=OSError("bad entry")):
            out = lib.detect_project_type(tmp_path)
        assert out is not None  # errored entries skipped, no crash

    def test_file_count_and_walk(self, tmp_path):
        (tmp_path / "deep" / "deeper").mkdir(parents=True)
        (tmp_path / "deep" / "deeper" / "cart.py").write_text("x")
        lib = DesignLibrary(tmp_path)
        assert lib.detect_project_type(tmp_path) is ProjectType.ECOMMERCE
