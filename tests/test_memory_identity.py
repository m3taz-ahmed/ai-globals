"""Tests for memory store identity protection (from mem0)."""

from __future__ import annotations

import json
from pathlib import Path

from memory.store import _IDENTITY_KEYS, MemoryStore, _strip_identity_keys


def test_strip_identity_keys_removes_all() -> None:
    meta = {
        "user_id": "user1",
        "agent_id": "agent1",
        "run_id": "run1",
        "session_id": "sess1",
        "tenant_id": "tenant1",
        "actor_id": "actor1",
        "safe_key": "safe_value",
    }
    stripped = _strip_identity_keys(meta)
    assert "user_id" not in stripped
    assert "agent_id" not in stripped
    assert "run_id" not in stripped
    assert "session_id" not in stripped
    assert "tenant_id" not in stripped
    assert "actor_id" not in stripped
    assert stripped["safe_key"] == "safe_value"


def test_strip_identity_keys_empty() -> None:
    assert _strip_identity_keys({}) == {}


def test_identity_keys_set_contents() -> None:
    assert "user_id" in _IDENTITY_KEYS
    assert "agent_id" in _IDENTITY_KEYS
    assert "run_id" in _IDENTITY_KEYS
    assert "session_id" in _IDENTITY_KEYS
    assert "tenant_id" in _IDENTITY_KEYS
    assert "actor_id" in _IDENTITY_KEYS


def test_add_with_identity_params(tmp_path: Path) -> None:
    store = MemoryStore(root=tmp_path, enable_vector=False)
    mem = store.add(
        kind="episodic",
        content="test content",
        source="test",
        meta={"custom": "data"},
        user_id="user1",
        agent_id="agent1",
        session_id="sess1",
    )
    meta = json.loads(mem.meta)
    assert meta["user_id"] == "user1"
    assert meta["agent_id"] == "agent1"
    assert meta["session_id"] == "sess1"
    assert meta["custom"] == "data"


def test_add_strips_identity_from_metadata(tmp_path: Path) -> None:
    store = MemoryStore(root=tmp_path, enable_vector=False)
    # Caller tries to inject identity via metadata (attack)
    mem = store.add(
        kind="episodic",
        content="malicious",
        source="attacker",
        meta={"user_id": "victim_user", "tenant_id": "victim_tenant", "safe": "ok"},
        user_id="real_user",  # explicit param should win
    )
    meta = json.loads(mem.meta)
    # The explicit user_id should be used, not the one from metadata
    assert meta["user_id"] == "real_user"
    # tenant_id from metadata should be stripped (not passed as explicit param)
    assert "tenant_id" not in meta
    assert meta["safe"] == "ok"


def test_add_without_identity(tmp_path: Path) -> None:
    store = MemoryStore(root=tmp_path, enable_vector=False)
    mem = store.add(
        kind="semantic",
        content="no identity",
        source="test",
        meta={"data": "value"},
    )
    meta = json.loads(mem.meta)
    assert "user_id" not in meta
    assert "agent_id" not in meta
    assert meta["data"] == "value"
