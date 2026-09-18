"""Gap coverage batch 8: tech_stack, telemetry, attribution_model, quality, bounder, repository."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import runtime.tech_stack as ts
from runtime.attribution_model import first_click, last_click, linear, position_based
from runtime.quality import (
    Bounder,
    CostProvider,
    ReflexionEntry,
    ReflexionLog,
    WitnessRecorder,
)
from runtime.repository import BaseRepository
from runtime.schemas import ValidationError
from runtime.telemetry import TelemetryCollector
from runtime.tool_output_bounder import BoundedOutput, OutputBounds, bound_output


class TestTechStackGaps:
    def test_package_lock_root_deps_and_skips(self, tmp_path: Path) -> None:
        lock = tmp_path / "package-lock.json"
        lock.write_text(
            json.dumps(
                {
                    "packages": {
                        "": {"dependencies": {"a": "^1.0", "b": "^2.0"}},
                        "node_modules/x": {"version": 5},
                        "legacy_a": {"noversion": 1},
                        "legacy_b": {"version": "2.0"},
                        "non_dict": "skip",
                    }
                }
            )
        )
        versions = ts._parse_package_lock(lock)
        assert versions["a"] == "1.0" and versions["b"] == "2.0"
        assert "x" not in versions and versions["legacy_b"] == "2.0"

    def test_composer_lock_missing_fields(self, tmp_path: Path) -> None:
        lock = tmp_path / "composer.lock"
        lock.write_text(
            json.dumps(
                {
                    "packages": [
                        {"name": "", "version": "1.0"},
                        {"name": "pkg/b", "version": "2.0"},
                    ],
                    "packages-dev": [{"name": "pkg/c", "version": "3.0"}],
                }
            )
        )
        versions = ts._parse_composer_lock(lock)
        assert versions == {"pkg/b": "2.0", "pkg/c": "3.0"}

    def test_composer_json_unclean_constraint(self, tmp_path: Path) -> None:
        f = tmp_path / "composer.json"
        f.write_text(json.dumps({"require": {"a": "*", "b": "^2.0"}}))
        versions = ts._parse_composer_json(f)
        assert versions == {"b": "2.0"}

    def test_pyproject_unclean_requires_python(self, tmp_path: Path) -> None:
        f = tmp_path / "pyproject.toml"
        f.write_text('[project]\nrequires-python = "nightly"\ndependencies = ["x>=1.0"]\n')
        versions = ts._parse_pyproject_toml(f)
        assert "python" not in versions

    def test_pep508_dead_clean(self) -> None:
        versions: dict[str, str] = {}
        ts._parse_pep508("pkg>=1.2", versions)
        assert versions == {"pkg": "1.2"}

    def test_detect_stack_unresolved_path(self, tmp_path: Path) -> None:
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "composer.lock").write_text(
            json.dumps({"packages": [{"name": "unknown/pkg", "version": "1.0"}]})
        )
        os_root = tmp_path / "os"
        os_root.mkdir()
        detected = ts.detect_stack(proj, os_root)
        assert isinstance(detected, dict)

    def test_load_stack_docs_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            ts,
            "detect_stack",
            lambda pr, osr: {"x": {"version": "1.0", "path": "missing/doc.md"}},
        )
        assert ts.load_stack_docs(tmp_path, tmp_path) == {}


class TestTelemetryGaps:
    def test_rotation(self, tmp_path: Path) -> None:
        tc = TelemetryCollector(tmp_path)
        tc.log_path.write_bytes(b"x" * 10)
        (tmp_path / "state" / "telemetry.jsonl.1").write_bytes(b"old")
        object.__setattr__  # noqa: B018 - keep linter quiet
        tc._MAX_LOG_SIZE = 0
        tc._rotate_if_needed()
        assert (tmp_path / "state" / "telemetry.jsonl.1").exists()
        assert (tmp_path / "state" / "telemetry.jsonl.2").exists()


class TestAttributionGaps:
    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError):
            linear([])

    def test_position_based_single(self) -> None:
        assert position_based([{"channel": "a"}]) == {"a": 1.0}

    def test_position_based_two(self) -> None:
        assert position_based([{"channel": "a"}, {"channel": "b"}]) == {"a": 0.5, "b": 0.5}

    def test_others_smoke(self) -> None:
        tps = [{"channel": "x"}, {"channel": "y"}, {"channel": "x"}]
        assert sum(first_click(tps).values()) == pytest.approx(1.0)
        assert sum(last_click(tps).values()) == pytest.approx(1.0)
        assert sum(linear(tps).values()) == pytest.approx(1.0)
        pb = position_based(tps)
        assert set(pb) == {"x", "y"}


class TestQualityGaps:
    def test_base_cost_provider(self) -> None:
        p = CostProvider()
        assert p.cost_per_token("m", 10, 10) == 0.0
        assert p.cost_per_call("m", 5) == 0.0

    def test_bounder_list_value(self) -> None:
        b = Bounder(max_items=2)
        out = b.bound_dict({"k": [1, 2, 3, 4]})
        assert len(out["k"]) == 2

    def test_witness_recorder_clear(self) -> None:
        w = WitnessRecorder()
        w.clear()
        assert w.all() == []

    def test_reflexion_entry_dict(self) -> None:
        e = ReflexionEntry(task="t", outcome="o", reflection="r", lesson="l")
        assert e.to_dict()["task"] == "t"

    def test_reflexion_log_clear(self) -> None:
        log = ReflexionLog()
        log.add("t", "o", "r", "l")
        log.clear()
        assert log.all() == []


class TestBounderGaps:
    def test_to_dict(self) -> None:
        o = BoundedOutput(
            text="t", truncated=True, original_lines=3, original_bytes=20,
            bounded_lines=1, bounded_bytes=5, reason="r",
        )
        assert o.to_dict()["reason"] == "r"

    def test_utf8_boundary_walkback(self) -> None:
        # Cut lands mid-character on a 2-byte char -> single-step walkback succeeds.
        text = "a" * 9 + "é" + "a" * 50
        out = bound_output(text, OutputBounds(max_lines=1000, max_bytes=10))
        assert out.truncated

    def test_utf8_boundary_replace_fallback(self) -> None:
        # Cut 1 byte into a 4-byte emoji -> all walkbacks fail -> errors="replace".
        text = "a" * 9 + "🐍" + "a" * 50
        out = bound_output(text, OutputBounds(max_lines=1000, max_bytes=10))
        assert out.truncated


class TestRepositoryGaps:
    def test_close_all_closes_pooled(self, tmp_path: Path) -> None:
        repo = BaseRepository(tmp_path / "t.db")
        conn = MagicMock()
        repo._pool.put(conn)
        repo.close_all()
        conn.close.assert_called_once()
