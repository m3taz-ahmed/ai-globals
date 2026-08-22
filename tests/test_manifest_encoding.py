"""Tests for manifest.json encoding integrity.

Ensures manifest.json trigger keys are valid UTF-8 without mojibake
(UTF-8 bytes misread as Latin-1/CP1252), which would break Arabic triggers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Mojibake marker: high-byte Latin-1 chars (0xC0-0xFF) that signal
# UTF-8 was misread as Latin-1/CP1252.
_MOJIBAKE_RE = re.compile(r"[\xc0-\xff\u0152\u0153\u0160\u0161\u017d\u017e\u0192\u201a\u201e\u2026\u20ac\u2122]")


def _manifest_path() -> Path:
    """Locate manifest.json relative to the project root."""
    here = Path(__file__).resolve().parent
    return here.parent / "manifest.json"


class TestManifestEncoding:
    """Verify manifest.json is free of mojibake."""

    def test_manifest_is_valid_json(self) -> None:
        """manifest.json must parse as valid JSON."""
        path = _manifest_path()
        assert path.exists(), "manifest.json not found at project root"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "triggers" in data, "manifest.json missing 'triggers' section"
        assert len(data["triggers"]) > 0, "manifest.json has no triggers"

    def test_trigger_keys_no_mojibake(self) -> None:
        """No trigger key should contain mojibake characters."""
        path = _manifest_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        bad_keys = [k for k in data["triggers"] if _MOJIBAKE_RE.search(k)]
        assert not bad_keys, f"Mojibake detected in trigger keys: {bad_keys}"

    def test_arabic_triggers_present(self) -> None:
        """Arabic trigger keys should be valid Arabic, not mojibake."""
        path = _manifest_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        arabic_keys = [k for k in data["triggers"] if any(0x0600 <= ord(c) <= 0x06FF for c in k)]
        # We expect at least the SEO Arabic triggers.
        assert len(arabic_keys) >= 2, f"Expected >=2 Arabic triggers, got {len(arabic_keys)}: {arabic_keys}"
        # Verify they map to the SEO audit workflow.
        for key in arabic_keys:
            assert data["triggers"][key] == "workflows/28-seo-audit.md", (
                f"Arabic trigger '{key}' maps to {data['triggers'][key]}, expected workflows/28-seo-audit.md"
            )

    def test_all_trigger_paths_exist(self) -> None:
        """Every trigger value must point to an existing file."""
        path = _manifest_path()
        root = path.parent
        data = json.loads(path.read_text(encoding="utf-8"))
        missing = []
        for trigger, file_path in data["triggers"].items():
            full = root / file_path
            if not full.exists():
                missing.append(f"{trigger} -> {file_path}")
        assert not missing, f"Missing trigger target files: {missing}"
