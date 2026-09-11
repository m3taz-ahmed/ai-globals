#!/usr/bin/env python3
"""Safety analysis over Laravel database migration files.

Detects dangerous migration patterns that can cause data loss, downtime,
or lock contention in production: destructive operations without safeguards,
missing down() methods, non-concurrent index creation, and unsafe backfills.

Usage::

    from runtime.db_migration_safety import MigrationSafetyChecker
    checker = MigrationSafetyChecker()
    findings = checker.check_files(file_paths)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class MigrationSeverity(str, Enum):
    """Severity of a migration safety finding."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class MigrationFinding:
    """A single migration safety finding."""

    rule_id: str
    severity: MigrationSeverity
    message: str
    file_path: str
    line: int
    fix: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
            "fix": self.fix,
        }


# MG001: DROP COLUMN / DROP TABLE without safeguard
_DROP_COLUMN_RE = re.compile(r"->dropColumn\s*\(|->dropColumn\b")
_DROP_TABLE_RE = re.compile(r"->dropIfExists\s*\(|Schema::drop\s*\(")

# MG002: Missing down() method
_HAS_UP_RE = re.compile(r"public\s+function\s+up\s*\(")
_HAS_DOWN_RE = re.compile(r"public\s+function\s+down\s*\(")

# MG003: Non-concurrent index creation
_CREATE_INDEX_RE = re.compile(r"->index\s*\(|->unique\s*\(|->foreign\s*\(")
_CONCURRENT_RE = re.compile(r"CONCURRENTLY|concurrent")

# MG004: Model::all() in migration (memory bomb)
_MODEL_ALL_RE = re.compile(r"Model::all\(\)|::all\(\)")

# MG005: Raw SQL UPDATE without batch/limit
_RAW_UPDATE_RE = re.compile(r"DB::(update|statement)\s*\(\s*['\"]UPDATE", re.IGNORECASE)

# MG006: renameColumn (breaks running code)
_RENAME_COLUMN_RE = re.compile(r"->renameColumn\s*\(")

# MG007: Drop foreign key without dropForeign first
_DROP_FOREIGN_RE = re.compile(r"->dropForeign\s*\(")

# MG008: Change column type (may fail on PG)
_CHANGE_COLUMN_RE = re.compile(r"->change\s*\(")

# MG009: Using DB::raw in migration (DB-specific)
_DB_RAW_RE = re.compile(r"DB::raw\s*\(")

# MG010: Missing return type on up()/down() (PHP 8.5 strict)
_UP_NO_RETURN_RE = re.compile(r"public\s+function\s+up\s*\(\s*\)\s*\{")


class MigrationSafetyChecker:
    """Safety analysis over Laravel database migration files.

    Detects dangerous migration patterns:
    - MG001: Destructive operations (dropColumn, dropTable) without safeguard
    - MG002: Missing down() method (irreversible migration)
    - MG003: Non-concurrent index creation (table lock on large tables)
    - MG004: Model::all() in migration (memory bomb)
    - MG005: Raw SQL UPDATE without batching
    - MG006: renameColumn (breaks running code during deploy)
    - MG007: Drop column with foreign key without dropForeign first
    - MG008: Change column type (may fail on PostgreSQL)
    - MG009: DB::raw in migration (DB-specific SQL)
    - MG010: Missing return type on up()/down() (PHP 8.5 strict typing)
    """

    def check_file(self, file_path: str | Path) -> list[MigrationFinding]:
        """Check a single migration file for safety issues."""
        path = Path(file_path)
        if not path.is_file():
            return []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            _logger.warning("Cannot read %s: %s", path, exc)
            return []
        return self._check_content(content, str(path))

    def check_files(self, file_paths: list[str | Path]) -> list[MigrationFinding]:
        """Check multiple migration files."""
        findings: list[MigrationFinding] = []
        for fp in file_paths:
            findings.extend(self.check_file(fp))
        return findings

    def check_content(self, content: str, file_path: str = "<string>") -> list[MigrationFinding]:
        """Check raw PHP migration content."""
        return self._check_content(content, file_path)

    def _check_content(self, content: str, file_path: str) -> list[MigrationFinding]:
        findings: list[MigrationFinding] = []
        lines = content.splitlines()
        is_migration = "Migration" in content or "up(" in content or file_path.endswith("_table.php")

        if not is_migration:
            return findings

        for i, line in enumerate(lines, 1):
            # MG001: Destructive operations
            if _DROP_COLUMN_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG001",
                    severity=MigrationSeverity.CRITICAL,
                    message="dropColumn() is destructive — use 3-phase zero-downtime deploy (add nullable → migrate code → drop old)",
                    file_path=file_path,
                    line=i,
                    fix="Split into 3 migrations across 3 deploys: add nullable, backfill, drop old",
                ))

            if _DROP_TABLE_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG001",
                    severity=MigrationSeverity.CRITICAL,
                    message="dropIfExists()/Schema::drop() — data loss risk. Verify no references remain",
                    file_path=file_path,
                    line=i,
                    fix="Check all models, relations, and API routes reference this table before dropping",
                ))

            # MG003: Non-concurrent index
            if _CREATE_INDEX_RE.search(line) and not _CONCURRENT_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG003",
                    severity=MigrationSeverity.WARNING,
                    message="Index/unique/foreign creation without CONCURRENTLY — table lock on large tables",
                    file_path=file_path,
                    line=i,
                    fix="For PostgreSQL: use raw SQL 'CREATE INDEX CONCURRENTLY' outside transaction",
                ))

            # MG004: Model::all()
            if _MODEL_ALL_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG004",
                    severity=MigrationSeverity.ERROR,
                    message="Model::all() in migration — loads entire table into memory. Use chunked queries",
                    file_path=file_path,
                    line=i,
                    fix="Use DB::table('users')->chunkById(500, fn($chunk) => ...) for backfills",
                ))

            # MG005: Raw UPDATE without batch
            if _RAW_UPDATE_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG005",
                    severity=MigrationSeverity.WARNING,
                    message="Raw SQL UPDATE in migration — may lock table for large datasets. Batch with WHERE id BETWEEN",
                    file_path=file_path,
                    line=i,
                    fix="Use chunked updates: DB::table('x')->whereBetween('id', [$start, $end])->update([...])",
                ))

            # MG006: renameColumn
            if _RENAME_COLUMN_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG006",
                    severity=MigrationSeverity.ERROR,
                    message="renameColumn() breaks running code during deploy — use dual-column approach",
                    file_path=file_path,
                    line=i,
                    fix="Add new column → dual-write in code → backfill → switch reads → drop old column",
                ))

            # MG008: Change column type
            if _CHANGE_COLUMN_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG008",
                    severity=MigrationSeverity.WARNING,
                    message="->change() may fail on PostgreSQL (type cast needed) — use raw SQL with USING clause",
                    file_path=file_path,
                    line=i,
                    fix="On PG: ALTER TABLE x ALTER COLUMN y TYPE integer USING y::integer",
                ))

            # MG009: DB::raw
            if _DB_RAW_RE.search(line):
                findings.append(MigrationFinding(
                    rule_id="MG009",
                    severity=MigrationSeverity.WARNING,
                    message="DB::raw() in migration — DB-specific SQL may not work on MySQL + PostgreSQL",
                    file_path=file_path,
                    line=i,
                    fix="Branch on DB::getDriverName() or use schema builder methods",
                ))

        # MG002: Missing down()
        if _HAS_UP_RE.search(content) and not _HAS_DOWN_RE.search(content):
            findings.append(MigrationFinding(
                rule_id="MG002",
                severity=MigrationSeverity.ERROR,
                message="Migration has up() but no down() — irreversible, cannot rollback",
                file_path=file_path,
                line=1,
                fix="Add public function down() { Schema::dropIfExists('table'); }",
            ))

        return findings

    def summary(self, findings: list[MigrationFinding]) -> dict[str, Any]:
        """Return a summary dict of findings by severity."""
        by_severity: dict[str, int] = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        by_rule: dict[str, int] = {}
        for f in findings:
            by_severity[f.severity.value] = by_severity.get(f.severity.value, 0) + 1
            by_rule[f.rule_id] = by_rule.get(f.rule_id, 0) + 1
        return {
            "total": len(findings),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }
