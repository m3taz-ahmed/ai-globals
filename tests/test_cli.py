import shutil
import tempfile
from pathlib import Path

from cli import main


def test_cli_status(capsys):
    tmp = Path(tempfile.mkdtemp(prefix="aios_cli_test_"))
    try:
        for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
            (tmp / sub).mkdir(parents=True, exist_ok=True)
        (tmp / "runtime/policies/default.yaml").write_text(
            "default_action: ask\nrules:\n"
            "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        )
        (tmp / "workflows/test.md").write_text(
            "[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n"
        )
        rc = main(["--root", str(tmp), "status"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "AI Global OS Status" in captured.out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cli_check(capsys):
    tmp = Path(tempfile.mkdtemp(prefix="aios_cli_test_"))
    try:
        for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
            (tmp / sub).mkdir(parents=True, exist_ok=True)
        (tmp / "runtime/policies/default.yaml").write_text(
            "default_action: ask\nrules:\n"
            "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        )
        rc = main(["--root", str(tmp), "check", "Read"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "allow" in captured.out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
