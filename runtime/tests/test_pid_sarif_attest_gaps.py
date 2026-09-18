"""Gap coverage: prompt_injection_detector + sarif_emitter + llm_attestation."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.llm_attestation import LlmAttestor, PrivacyMode
from runtime.prompt_injection_detector import (
    DetectionLevel,
    PromptInjectionDetector,
    PromptInjectionDetectorError,
    SemanticDetectionResult,
    _build_detection_messages,
    _heuristic_classify,
)
from runtime.sarif_emitter import _is_safe_path, build_sarif, write_sarif


class TestPidGaps:
    def test_is_suspicious_property(self) -> None:
        from runtime.injection_detector import InjectionDetector

        verdict = InjectionDetector().detect("clean text")
        res = SemanticDetectionResult(
            text="t", level=DetectionLevel.SUSPICIOUS, confidence=0.5,
            stage1_verdict=verdict,
        )
        assert res.is_suspicious is True
        assert res.is_injection is False

    def test_detector_error(self) -> None:
        err = PromptInjectionDetectorError("x")
        assert err.error_code == "PI_DETECTOR_ERROR"

    def test_build_detection_messages(self) -> None:
        msgs = _build_detection_messages("scan me")
        assert msgs[0]["role"] == "system" and msgs[1]["content"] == "scan me"

    def test_heuristic_high_hits(self) -> None:
        from runtime.injection_detector import InjectionDetector

        verdict = InjectionDetector().detect("hello")
        text = "ignore disregard forget override reveal extract bypass"
        level, conf, _reason = _heuristic_classify(text, verdict)
        assert level is DetectionLevel.SUSPICIOUS
        assert conf > 0.5

    def test_heuristic_medium_hits(self) -> None:
        from runtime.injection_detector import InjectionDetector

        verdict = InjectionDetector().detect("hello")
        level, _conf, _ = _heuristic_classify("please ignore and bypass", verdict)
        assert level is DetectionLevel.SUSPICIOUS

    def test_model_unknown_output_uncertain(self) -> None:
        det = PromptInjectionDetector(
            model_fn=lambda t: "maybe??", always_use_model=True
        )
        res = det.detect("some normal text")
        assert res.level is DetectionLevel.UNCERTAIN


class TestSarifGaps:
    def test_unsafe_paths(self) -> None:
        assert _is_safe_path("/etc/passwd") is False
        assert _is_safe_path("http://x/y") is False
        assert _is_safe_path("\\\\server\\s") is False
        assert _is_safe_path("src/../up") is False
        assert _is_safe_path("src/ok.py") is True

    def test_finding_without_line(self) -> None:
        doc = build_sarif([{"type": "issue", "file": "a.py", "message": "m"}])
        result = doc["runs"][0]["results"][0]
        assert "region" not in result["locations"][0]["physicalLocation"]

    def test_finding_with_fix_and_provenance(self) -> None:
        doc = build_sarif(
            [{"type": "issue", "file": "a.py", "line": 3, "message": "m", "fix": "do x"}],
            repo_url="https://r", commit_sha="abc", branch="main",
        )
        run = doc["runs"][0]
        assert run["results"][0]["fixes"][0]["description"]["text"] == "do x"
        prov = run["versionControlProvenance"][0]
        assert prov["repositoryUri"] == "https://r"
        assert prov["revisionId"] == "abc" and prov["branch"] == "main"

    def test_write_sarif_failure(self, tmp_path: Path) -> None:
        with patch("builtins.open", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                write_sarif([{"type": "t", "file": "a.py"}], str(tmp_path / "o.sarif"))


class TestAttestationGaps:
    def test_list_skips_nonfiles(self, tmp_path: Path) -> None:
        state = tmp_path / "att"
        (state / "weird.json").mkdir(parents=True)
        attestor = LlmAttestor(state)
        assert attestor.list_attestations() == []

    def test_verify_ed25519_no_pubkey(self, tmp_path: Path) -> None:
        attestor = LlmAttestor(tmp_path)
        with patch.object(attestor, "_get_ed25519_public_key", return_value=None):
            assert attestor._verify_ed25519(b"payload", b"sig") is False

    def test_ed25519_pubkey_none_when_no_key(self, tmp_path: Path) -> None:
        attestor = LlmAttestor(tmp_path)
        with patch.object(attestor, "_get_ed25519_key", return_value=None):
            assert attestor._get_ed25519_public_key() is None

    def test_persist_write_failure_cleans_tmp(self, tmp_path: Path) -> None:
        attestor = LlmAttestor(tmp_path)
        from runtime.llm_attestation import AttestationType

        env = attestor.attest(
            AttestationType.PROMPT, "subject-1", b"content", PrivacyMode.HASH_ONLY
        )
        with patch.object(os, "replace", side_effect=OSError("boom")):
            with pytest.raises(OSError):
                attestor._persist(env)
        leftovers = [p for p in tmp_path.iterdir() if ".tmp" in p.name or p.name.startswith("stmt")]
        assert not leftovers

    def test_apply_privacy_plaintext(self) -> None:
        out = LlmAttestor._apply_privacy(
            PrivacyMode.PLAINTEXT_EXPLICIT, b"secret", {"m": 1}
        )
        assert out["_privacy"] == "plaintext_explicit"
        assert out["_content"] == "secret"
        assert out["m"] == 1
