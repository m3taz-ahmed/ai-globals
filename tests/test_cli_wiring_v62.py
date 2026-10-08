"""CLI tests for the v6.2 wiring fixes: policy lint, doctor wiring table,
audit verify with signatures."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from aizee_cli import main


def _tmp_root() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aizee_cli_v62_"))
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp / "workflows/test.md").write_text("[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n")
    return tmp


class TestPolicyLint:
    def test_lint_clean_policies(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "policy", "lint"])
            assert rc == 0
            assert "No error-level findings" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_lint_contradiction_errors(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            (tmp / "runtime/policies/bad.yaml").write_text(
                "rules:\n  - name: dead-rule\n"
                "    condition: \"type == 'a' and type == 'b'\"\n    action: deny\n"
            )
            rc = main(["--root", str(tmp), "policy", "lint"])
            assert rc == 1
            assert "error-level" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_lint_or_disjunction_not_flagged(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            (tmp / "runtime/policies/or.yaml").write_text(
                "rules:\n  - name: either\n"
                "    condition: \"type == 'a' or type == 'b'\"\n    action: deny\n"
            )
            rc = main(["--root", str(tmp), "policy", "lint", "--path", str(tmp / "runtime/policies/or.yaml")])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_lint_missing_dir(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "policy", "lint", "--path", str(tmp / "nope")])
            assert rc == 0
            assert "No policy files" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_policy_test_requires_action(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "policy", "test"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestAuditVerifyCli:
    def test_verify_empty_log(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "audit", "verify"])
            assert rc == 0
            assert "Chain valid" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_verify_signed_log(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            from runtime.audit import AuditLogger
            from runtime.audit_signing import AuditSigner

            logger = AuditLogger(tmp, signer=AuditSigner(key_path=tmp / "state" / "audit_signing.key"))
            logger.log("evt.test", {"a": 1})
            rc = main(["--root", str(tmp), "audit", "verify"])
            assert rc == 0
            assert "sigs: 1 ok" in capsys.readouterr().out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDoctorWiring:
    def test_doctor_reports_wiring_truth(self, capsys) -> None:
        tmp = _tmp_root()
        try:
            main(["--root", str(tmp), "doctor"])
            out = capsys.readouterr().out
            assert "Module wiring" in out
            # Minimal tmp root has no runtime/*.py — orphans report "absent",
            # kernel-constructed services still report constructed-only.
            assert "absent" in out and "constructed only" in out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_doctor_reports_orphans_on_real_root(self, capsys) -> None:
        repo = Path(__file__).resolve().parent.parent
        main(["--root", str(repo), "doctor"])
        out = capsys.readouterr().out
        assert "orphan" in out and "trajectory" in out
