"""Trigger-routing evals — manifest trigger→artifact contract.

Adapted from addyosmani/agent-skills' per-skill eval cases: every positive
trigger must route to its expected artifact, negative triggers must not
misroute, and every manifest trigger target must exist on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
CASES = ROOT / "eval" / "trigger_cases.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _cases() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))


class TestManifestIntegrity:
    def test_every_trigger_target_exists(self) -> None:
        triggers = _manifest()["triggers"]
        missing = [t for t, target in triggers.items() if not (ROOT / target).exists()]
        assert missing == [], f"triggers with missing targets: {missing}"

    def test_every_feature_exists(self) -> None:
        features = _manifest()["features"]
        missing = [name for name, target in features.items() if not (ROOT / target).exists()]
        assert missing == [], f"features with missing targets: {missing}"


class TestTriggerCases:
    @pytest.mark.parametrize(
        "case",
        list(_cases()["positive"]),
        ids=[c["trigger"] for c in _cases()["positive"]],
    )
    def test_positive_routes(self, case: dict) -> None:
        triggers = _manifest()["triggers"]
        assert triggers.get(case["trigger"]) == case["expect"], (
            f"'{case['trigger']}' routes to {triggers.get(case['trigger'])}, "
            f"expected {case['expect']}"
        )

    @pytest.mark.parametrize(
        "case",
        list(_cases()["negative"]),
        ids=[c["trigger"] for c in _cases()["negative"]],
    )
    def test_negative_no_misroute(self, case: dict) -> None:
        triggers = _manifest()["triggers"]
        assert triggers.get(case["trigger"]) != case["must_not"], (
            f"'{case['trigger']}' must not route to {case['must_not']}"
        )
