"""Comprehensive tests for cli.py."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_root(with_vector: bool = False) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="aios_cli_test_"))
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[OBJ] Test workflow for CLI tests.\n[RULES]\n1. [REQ] Step one.\n"
    )
    (tmp / "rules/core.md").write_text("# Core rules\nAgent guidelines.")
    return tmp


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestCliStatus:
    def test_status_returns_zero(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "status"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "AI Global OS Status" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

class TestCliVersion:
    def test_version_output(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "version"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "AI Global OS" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------

class TestCliDoctor:
    def test_doctor_ok(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "doctor"])
            captured = capsys.readouterr()
            assert "AI Global OS Doctor" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------

class TestCliCheck:
    def test_check_allowed(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "Read"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "allow" in captured.out.lower()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_with_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "Read", "--args", '{"user": "alice"}'])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_check_with_approve_flag(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "check", "deploy", "--approve"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# run (workflow)
# ---------------------------------------------------------------------------

class TestCliRun:
    def test_run_workflow(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "run", "test"])
            captured = capsys.readouterr()
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_run_workflow_with_context(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "run", "test", "--context", '{"key": "val"}'])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory search
# ---------------------------------------------------------------------------

class TestCliMemorySearch:
    def test_memory_search_empty(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "search", "--query", "nonexistent"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Memory Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_search_with_kind(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "search", "--query", "rules", "--kind", "semantic"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory vector
# ---------------------------------------------------------------------------

class TestCliMemoryVector:
    def test_memory_vector_no_results(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "vector", "--query", "test"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Vector Search" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_vector_with_kind(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "vector", "--query", "test", "--kind", "factual"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory add
# ---------------------------------------------------------------------------

class TestCliMemoryAdd:
    def test_memory_add(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main([
                "--root", str(tmp), "memory", "add",
                "--kind", "episodic",
                "--content", "Test memory content",
                "--source", "test-source",
            ])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Added memory" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_memory_add_missing_required_args(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "add"])
            assert rc == 1
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# memory ingest
# ---------------------------------------------------------------------------

class TestCliMemoryIngest:
    def test_memory_ingest(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "memory", "ingest"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Ingested" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# query (hybrid search)
# ---------------------------------------------------------------------------

class TestCliQuery:
    def test_query_returns_table(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "agent rules"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Hybrid Context Query" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_query_with_kind_filter(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "rules", "--kind", "semantic"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_query_with_limit(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "query", "rules", "--limit", "5"])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------

class TestCliPolicy:
    def test_policy_test_dry_run(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "policy", "test", "Read"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "decision" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# budget
# ---------------------------------------------------------------------------

class TestCliBudget:
    def test_budget_list(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main(["--root", str(tmp), "budget", "list"])
            captured = capsys.readouterr()
            assert rc == 0
            assert "Budgets" in captured.out
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_budget_set(self, capsys):
        tmp = _tmp_root()
        try:
            rc = main([
                "--root", str(tmp), "budget", "set",
                "--scope", "test", "--max-tokens", "1000",
                "--period", "daily",
            ])
            assert rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# project
# ---------------------------------------------------------------------------

class TestCliProject:
    def test_project_init(self):
        tmp = Path(tempfile.mkdtemp(prefix="aios_project_test_"))
        try:
            rc = main(["project", "init", "--path", str(tmp)])
            assert rc == 0
            assert (tmp / ".ai" / "active-context.md").exists()
            assert (tmp / "runtime" / "policies" / "default.yaml").exists()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# no command → help
# ---------------------------------------------------------------------------

class TestCliNoCommand:
    def test_no_command_returns_1(self):
        rc = main([])
        assert rc == 1
