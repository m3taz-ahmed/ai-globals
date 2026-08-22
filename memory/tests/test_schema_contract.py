"""Tests for memory/schema_contract.py — contract-first schema verification."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from memory.schema_contract import (
    SchemaContract,
    default_memory_contract,
    detect_schema_drift,
    verify_schema_integrity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(path: Path, tables: dict[str, str], indexes: dict[str, str] | None = None) -> None:
    with sqlite3.connect(path) as conn:
        for ddl in tables.values():
            conn.execute(ddl)
        for ddl in (indexes or {}).values():
            # Skip indexes referencing tables that were intentionally omitted
            # (e.g. when simulating a missing-table drift scenario).
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                continue


def _sample_contract() -> SchemaContract:
    return SchemaContract(
        tables={
            "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)",
            "posts": "CREATE TABLE posts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL)",
        },
        indexes={"idx_posts_user": "CREATE INDEX idx_posts_user ON posts(user_id)"},
        version="v1",
    )


# ---------------------------------------------------------------------------
# SchemaContract creation & hashing
# ---------------------------------------------------------------------------

class TestSchemaContract:
    def test_creation_and_hash_computed(self):
        contract = _sample_contract()
        h = contract.compute_hash()
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_content_hash_set_on_serialize(self):
        contract = _sample_contract()
        serialized = contract.serialize()
        assert contract.content_hash != ""
        assert contract.content_hash in serialized

    def test_hash_stable_for_same_content(self):
        c1 = _sample_contract()
        c2 = _sample_contract()
        assert c1.compute_hash() == c2.compute_hash()

    def test_hash_changes_when_schema_changes(self):
        base = _sample_contract()
        changed = SchemaContract(
            tables={**base.tables, "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)"},
            indexes=base.indexes,
            version="v1",
        )
        assert base.compute_hash() != changed.compute_hash()

    def test_hash_changes_when_table_added(self):
        base = _sample_contract()
        extended = SchemaContract(
            tables={**base.tables, "comments": "CREATE TABLE comments (id INTEGER PRIMARY KEY)"},
            indexes=base.indexes,
            version="v1",
        )
        assert base.compute_hash() != extended.compute_hash()

    def test_hash_independent_of_dict_order(self):
        c1 = SchemaContract(tables={"a": "CREATE TABLE a (x)", "b": "CREATE TABLE b (y)"}, version="v1")
        c2 = SchemaContract(tables={"b": "CREATE TABLE b (y)", "a": "CREATE TABLE a (x)"}, version="v1")
        assert c1.compute_hash() == c2.compute_hash()

    def test_serialize_deserialize_roundtrip(self):
        contract = _sample_contract()
        serialized = contract.serialize()
        restored = SchemaContract.deserialize(serialized)
        assert restored.tables == contract.tables
        assert restored.indexes == contract.indexes
        assert restored.version == contract.version
        assert restored.content_hash == contract.content_hash

    def test_deserialize_without_content_hash_recomputes(self):
        import json as _json
        contract = _sample_contract()
        payload = {**contract._payload()}
        data = _json.dumps(payload)
        restored = SchemaContract.deserialize(data)
        assert restored.content_hash == contract.compute_hash()


# ---------------------------------------------------------------------------
# verify_schema_integrity
# ---------------------------------------------------------------------------

class TestVerifySchemaIntegrity:
    def test_valid_when_schema_matches(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "match.db"
        _make_db(db, contract.tables, contract.indexes)
        is_valid, desc = verify_schema_integrity(db, contract)
        assert is_valid is True
        assert desc is None

    def test_drift_missing_table(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "missing.db"
        _make_db(db, {"users": contract.tables["users"]}, contract.indexes)
        is_valid, desc = verify_schema_integrity(db, contract)
        assert is_valid is False
        assert desc is not None
        assert "posts" in desc

    def test_drift_extra_table(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "extra.db"
        _make_db(
            db,
            {**contract.tables, "orphan": "CREATE TABLE orphan (id INTEGER)"},
            contract.indexes,
        )
        is_valid, desc = verify_schema_integrity(db, contract)
        assert is_valid is False
        assert desc is not None
        assert "orphan" in desc

    def test_drift_column_mismatch(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "mismatch.db"
        _make_db(
            db,
            {
                "users": "CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)",
                "posts": contract.tables["posts"],
            },
            contract.indexes,
        )
        is_valid, desc = verify_schema_integrity(db, contract)
        assert is_valid is False
        assert desc is not None
        assert "users" in desc

    def test_valid_for_nonexistent_db(self, tmp_path: Path):
        contract = _sample_contract()
        is_valid, desc = verify_schema_integrity(tmp_path / "nope.db", contract)
        # Nonexistent DB has no tables -> all expected tables missing -> drift.
        assert is_valid is False
        assert desc is not None


# ---------------------------------------------------------------------------
# detect_schema_drift
# ---------------------------------------------------------------------------

class TestDetectSchemaDrift:
    def test_returns_missing_table_drift(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "d.db"
        _make_db(db, {"users": contract.tables["users"]}, contract.indexes)
        drifts = detect_schema_drift(db, contract)
        types = {d.drift_type for d in drifts}
        assert "missing_table" in types
        missing = [d for d in drifts if d.drift_type == "missing_table"]
        assert any(d.table_name == "posts" for d in missing)

    def test_returns_extra_table_drift(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "d.db"
        _make_db(db, {**contract.tables, "junk": "CREATE TABLE junk (id INTEGER)"}, contract.indexes)
        drifts = detect_schema_drift(db, contract)
        extra = [d for d in drifts if d.drift_type == "extra_table"]
        assert len(extra) == 1
        assert extra[0].table_name == "junk"

    def test_returns_index_missing_drift(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "d.db"
        _make_db(db, contract.tables, {})  # no indexes created
        drifts = detect_schema_drift(db, contract)
        idx_drifts = [d for d in drifts if d.drift_type == "index_missing"]
        assert len(idx_drifts) == 1
        assert idx_drifts[0].table_name == "idx_posts_user"

    def test_no_drift_returns_empty(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "d.db"
        _make_db(db, contract.tables, contract.indexes)
        assert detect_schema_drift(db, contract) == []

    def test_drift_item_fields_populated(self, tmp_path: Path):
        contract = _sample_contract()
        db = tmp_path / "d.db"
        _make_db(db, {"users": contract.tables["users"]}, contract.indexes)
        drifts = detect_schema_drift(db, contract)
        missing = next(
            d for d in drifts if d.drift_type == "missing_table" and d.table_name == "posts"
        )
        assert missing.expected != ""
        assert missing.actual == ""


# ---------------------------------------------------------------------------
# default_memory_contract
# ---------------------------------------------------------------------------

class TestDefaultMemoryContract:
    def test_default_contract_has_memories_and_relations(self):
        contract = default_memory_contract()
        assert "memories" in contract.tables
        assert "relations" in contract.tables
        assert "idx_mem_kind" in contract.indexes
        assert contract.content_hash != ""

    def test_default_contract_self_consistent(self, tmp_path: Path):
        """A DB built from the default contract's DDL must verify as valid.

        This confirms the contract DDL and the normalization/comparison logic
        are self-consistent (SQLite stores the DDL in a form that round-trips
        through ``verify_schema_integrity``).
        """
        contract = default_memory_contract()
        db = tmp_path / "fresh.db"
        _make_db(db, contract.tables, contract.indexes)
        is_valid, desc = verify_schema_integrity(db, contract)
        assert is_valid is True, f"Expected valid schema, got drift: {desc}"

    def test_default_contract_drift_when_index_missing(self, tmp_path: Path):
        contract = default_memory_contract()
        db = tmp_path / "noindex.db"
        _make_db(db, contract.tables, {})  # tables present, indexes omitted
        drifts = detect_schema_drift(db, contract)
        assert any(d.drift_type == "index_missing" for d in drifts)
