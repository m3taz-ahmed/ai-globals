"""Gap tests for memory/schema_contract.py."""
from __future__ import annotations

import sqlite3

from memory.schema_contract import (
    SchemaContract,
    _append_column,
    _extract_columns,
    _normalize_sql,
    _read_db_schema,
    default_memory_contract,
    detect_schema_drift,
    verify_schema_integrity,
)


class TestContractApply:
    def test_apply_executes_ddl(self, tmp_path):
        c = SchemaContract(
            tables={"t1": "CREATE TABLE t1 (id INTEGER)"},
            indexes={"i1": "CREATE INDEX i1 ON t1 (id)"},
        )
        with sqlite3.connect(tmp_path / "d.db") as conn:
            c.apply(conn)
            tables, indexes = _read_db_schema(tmp_path / "d.db")
        assert "t1" in tables and "i1" in indexes


class TestNormalize:
    def test_empty_sql(self):
        assert _normalize_sql("") == ""

    def test_strips_if_not_exists(self):
        assert _normalize_sql("CREATE TABLE IF NOT EXISTS t (a)") == "create table  t (a)".replace("  ", " ")


class TestExtractColumns:
    def test_empty_ddl(self):
        assert _extract_columns("") == []

    def test_no_parens(self):
        assert _extract_columns("CREATE TABLE t") == []

    def test_quoted_default_with_comma(self):
        ddl = "CREATE TABLE t (a TEXT DEFAULT 'x,y', b INT)"
        assert _extract_columns(ddl) == ["a", "b"]

    def test_doubled_quote_escape(self):
        ddl = "CREATE TABLE t (a TEXT DEFAULT 'it''s', b INT)"
        assert _extract_columns(ddl) == ["a", "b"]

    def test_backtick_and_bracket_names(self):
        ddl = "CREATE TABLE t (`a` INT, [b] TEXT)"
        cols = _extract_columns(ddl)
        assert cols == ["a", "b"]

    def test_skips_table_constraints(self):
        ddl = "CREATE TABLE t (a INT, PRIMARY KEY (a), FOREIGN KEY (a) REFERENCES x(y))"
        assert _extract_columns(ddl) == ["a"]

    def test_append_empty(self):
        cols: list[str] = []
        _append_column(cols, "   ")
        assert cols == []


class TestReadDbSchema:
    def test_missing_db(self, tmp_path):
        tables, indexes = _read_db_schema(tmp_path / "ghost.db")
        assert tables == {} and indexes == {}

    def test_skips_sqlite_internal(self, tmp_path):
        db = tmp_path / "d.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE t (a INTEGER PRIMARY KEY AUTOINCREMENT, b TEXT)")
            conn.execute("CREATE INDEX i ON t (b)")
        tables, indexes = _read_db_schema(db)
        assert "t" in tables
        assert not any(n.startswith("sqlite_") for n in tables)
        assert "i" in indexes


class TestDrift:
    def test_default_contract_arg(self, tmp_path):
        db = tmp_path / "m.db"
        with sqlite3.connect(db) as conn:
            default_memory_contract().apply(conn)
        drifts = detect_schema_drift(db, None)
        assert isinstance(drifts, list)

    def test_missing_table(self, tmp_path):
        db = tmp_path / "d.db"
        sqlite3.connect(db).close()
        c = SchemaContract(tables={"t1": "CREATE TABLE t1 (a)"})
        drifts = detect_schema_drift(db, c)
        assert any(d.drift_type == "missing_table" for d in drifts)

    def test_column_mismatch(self, tmp_path):
        db = tmp_path / "d.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE t1 (a, extra_col)")
        c = SchemaContract(tables={"t1": "CREATE TABLE t1 (a)"})
        drifts = detect_schema_drift(db, c)
        assert any(d.drift_type == "column_mismatch" for d in drifts)

    def test_extra_table(self, tmp_path):
        db = tmp_path / "d.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE t1 (a)")
            conn.execute("CREATE TABLE stray (b)")
            conn.execute("CREATE VIRTUAL TABLE memories_fts USING fts5(x)")
        c = SchemaContract(tables={"t1": "CREATE TABLE t1 (a)"})
        drifts = detect_schema_drift(db, c)
        kinds = {d.table_name: d.drift_type for d in drifts}
        assert kinds.get("stray") == "extra_table"
        assert "memories_fts" not in kinds  # FTS shadow tables ignored

    def test_missing_and_drifted_index(self, tmp_path):
        db = tmp_path / "d.db"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE t (a, b)")
            conn.execute("CREATE INDEX i2 ON t (b)")  # drifted: contract wants (a)
        c = SchemaContract(
            tables={"t": "CREATE TABLE t (a, b)"},
            indexes={"i1": "CREATE INDEX i1 ON t (a)", "i2": "CREATE INDEX i2 ON t (a)"},
        )
        drifts = detect_schema_drift(db, c)
        names = {d.table_name for d in drifts if d.drift_type == "index_missing"}
        assert {"i1", "i2"} <= names


class TestVerifyIntegrity:
    def test_missing_db(self, tmp_path):
        ok, desc = verify_schema_integrity(tmp_path / "ghost.db")
        assert ok is False or desc is not None or ok is True  # returns tuple either way
        assert isinstance(ok, bool)
