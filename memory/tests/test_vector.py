"""Comprehensive tests for memory/vector.py using mocks for turbovec and sentence-transformers."""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import memory.vector as vector_module
from memory.vector import Embedder, VectorMemory, _mem_id_to_uint64

# ---------------------------------------------------------------------------
# _mem_id_to_uint64
# ---------------------------------------------------------------------------

class TestMemIdToUint64:
    def test_valid_uuid_string(self):
        uid = str(uuid.uuid4())
        result = _mem_id_to_uint64(uid)
        assert isinstance(result, int)
        assert 0 <= result < 2**64

    def test_non_uuid_uses_hash_fallback(self):
        result = _mem_id_to_uint64("not-a-uuid-string")
        assert isinstance(result, int)
        assert 0 <= result < 2**64

    def test_empty_string_uses_hash_fallback(self):
        result = _mem_id_to_uint64("")
        assert isinstance(result, int)

    def test_same_id_same_result(self):
        uid = str(uuid.uuid4())
        assert _mem_id_to_uint64(uid) == _mem_id_to_uint64(uid)

    def test_different_ids_usually_different(self):
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())
        assert _mem_id_to_uint64(id1) != _mem_id_to_uint64(id2)


# ---------------------------------------------------------------------------
# Helpers — build mocked VectorMemory
# ---------------------------------------------------------------------------

def _make_index_mock() -> MagicMock:
    """Return a mock turbovec IdMapIndex."""
    idx = MagicMock()
    idx.search.return_value = (
        np.array([[0.95, 0.80, 0.70, 0.60, 0.50]], dtype=np.float32),
        np.array([[1, 2, 3, 4, 5]], dtype=np.uint64),
    )
    return idx


def _make_st_mock() -> MagicMock:
    """Return a mock SentenceTransformer instance."""
    st = MagicMock()
    st.encode.return_value = np.zeros((1, 384), dtype=np.float32)
    return st


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="aios_vec_"))


def _mock_vm(tmp: Path, index_mock: MagicMock | None = None) -> VectorMemory:
    """Construct VectorMemory with fully mocked internals."""
    idx = index_mock or _make_index_mock()
    st_instance = _make_st_mock()

    mock_st_cls = MagicMock(return_value=st_instance)
    mock_idx_cls = MagicMock()
    mock_idx_cls.return_value = idx
    mock_idx_cls.load.return_value = idx

    with (
        patch.object(vector_module, "SentenceTransformer", mock_st_cls),
        patch.object(vector_module, "IdMapIndex", mock_idx_cls),
    ):
        vm = VectorMemory(tmp)
        vm.index = idx
        vm.embedder.model = st_instance

    return vm


# ---------------------------------------------------------------------------
# Embedder
# ---------------------------------------------------------------------------

class TestEmbedder:
    def test_embed_with_model(self):
        st_instance = _make_st_mock()
        mock_st_cls = MagicMock(return_value=st_instance)
        with patch.object(vector_module, "SentenceTransformer", mock_st_cls):
            emb = Embedder()
            result = emb.embed(["hello world"])
        assert result.shape[1] == 384

    def test_embed_without_model_raises(self):
        with patch.object(vector_module, "SentenceTransformer", None):
            emb = Embedder()
            emb.model = None
        with pytest.raises(RuntimeError, match="SentenceTransformer"):
            emb.embed(["test"])

    def test_is_available_true(self):
        st_instance = _make_st_mock()
        mock_st_cls = MagicMock(return_value=st_instance)
        with patch.object(vector_module, "SentenceTransformer", mock_st_cls):
            emb = Embedder()
        assert emb.is_available() is True

    def test_is_available_false_when_no_model(self):
        with patch.object(vector_module, "SentenceTransformer", None):
            emb = Embedder()
        assert emb.is_available() is False


# ---------------------------------------------------------------------------
# VectorMemory — is_available
# ---------------------------------------------------------------------------

class TestVectorMemoryAvailability:
    def test_is_available_false_when_no_index_class(self):
        tmp = _tmp()
        try:
            with patch.object(vector_module, "IdMapIndex", None):
                vm = VectorMemory(tmp)
            assert vm.is_available() is False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_is_available_true_with_mocked_index(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            assert vm.is_available() is True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# VectorMemory — add / add_batch
# ---------------------------------------------------------------------------

class TestVectorMemoryAdd:
    def test_add_single(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            uid = str(uuid.uuid4())
            vm.add(uid, "test text")
            assert vm.index.add_with_ids.called
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_persists_index(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            ids = [str(uuid.uuid4()) for _ in range(3)]
            texts = ["text one", "text two", "text three"]
            vm.add_batch(ids, texts)
            assert vm.index.write.called
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_empty_is_noop(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            vm.add_batch([], [])
            vm.index.add_with_ids.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_updates_id_map(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            uid = str(uuid.uuid4())
            vm.add_batch([uid], ["some text"])
            u64 = _mem_id_to_uint64(uid)
            assert str(u64) in vm.id_map
            assert vm.id_map[str(u64)] == uid
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_add_batch_embed_error_is_swallowed(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            vm.embedder.model = None  # causes RuntimeError in embed()
            uid = str(uuid.uuid4())
            vm.add_batch([uid], ["text"])  # should not raise
            vm.index.add_with_ids.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# VectorMemory — search
# ---------------------------------------------------------------------------

class TestVectorMemorySearch:
    def test_search_returns_results(self):
        tmp = _tmp()
        try:
            uid = str(uuid.uuid4())
            u64 = _mem_id_to_uint64(uid)

            idx_mock = _make_index_mock()
            idx_mock.search.return_value = (
                np.array([[0.95]], dtype=np.float32),
                np.array([[u64]], dtype=np.uint64),
            )

            vm = _mock_vm(tmp, idx_mock)
            vm.id_map[str(u64)] = uid

            results = vm.search("query text", k=1)
            assert len(results) == 1
            assert results[0]["id"] == uid
            assert results[0]["score"] == pytest.approx(0.95, abs=0.01)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_skips_unknown_u64(self):
        """u64 not in id_map is silently skipped."""
        tmp = _tmp()
        try:
            idx_mock = _make_index_mock()
            idx_mock.search.return_value = (
                np.array([[0.9]], dtype=np.float32),
                np.array([[99999999]], dtype=np.uint64),
            )
            vm = _mock_vm(tmp, idx_mock)
            # id_map is empty
            assert vm.search("query", k=1) == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_unavailable_returns_empty(self):
        tmp = _tmp()
        try:
            with patch.object(vector_module, "IdMapIndex", None):
                vm = VectorMemory(tmp)
            assert vm.search("query") == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_embed_error_returns_empty(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            vm.embedder.model = None
            assert vm.search("query") == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_with_allowlist(self):
        """ids allowlist is passed through to index.search."""
        tmp = _tmp()
        try:
            uid1 = str(uuid.uuid4())
            uid2 = str(uuid.uuid4())
            u64_1 = _mem_id_to_uint64(uid1)

            idx_mock = _make_index_mock()
            idx_mock.search.return_value = (
                np.array([[0.9]], dtype=np.float32),
                np.array([[u64_1]], dtype=np.uint64),
            )
            vm = _mock_vm(tmp, idx_mock)
            vm.id_map[str(u64_1)] = uid1
            vm.id_map[str(_mem_id_to_uint64(uid2))] = uid2

            vm.search("query", k=1, ids=[uid1])
            call_kwargs = idx_mock.search.call_args[1]
            assert call_kwargs.get("allowlist") is not None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_with_empty_allowlist_returns_empty(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            assert vm.search("query", k=5, ids=[]) == []
            vm.index.search.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# VectorMemory — remove / remove_batch
# ---------------------------------------------------------------------------

class TestVectorMemoryRemove:
    def test_remove_single(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            uid = str(uuid.uuid4())
            u64 = _mem_id_to_uint64(uid)
            vm.id_map[str(u64)] = uid
            vm.remove(uid)
            assert str(u64) not in vm.id_map
            vm.index.remove.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_remove_batch_empty_is_noop(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            vm.remove_batch([])
            vm.index.remove.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_remove_batch_clears_id_map(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            ids = [str(uuid.uuid4()), str(uuid.uuid4())]
            for uid in ids:
                u64 = _mem_id_to_uint64(uid)
                vm.id_map[str(u64)] = uid
            vm.remove_batch(ids)
            for uid in ids:
                assert str(_mem_id_to_uint64(uid)) not in vm.id_map
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_remove_batch_writes_index(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            uid = str(uuid.uuid4())
            u64 = _mem_id_to_uint64(uid)
            vm.id_map[str(u64)] = uid
            vm.remove_batch([uid])
            vm.index.write.assert_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_remove_unavailable_is_noop(self):
        tmp = _tmp()
        try:
            with patch.object(vector_module, "IdMapIndex", None):
                vm = VectorMemory(tmp)
            vm.remove("some-id")  # should not raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# VectorMemory — persistence (save_map / load_or_create)
# ---------------------------------------------------------------------------

class TestVectorMemoryPersistence:
    def test_save_and_reload_id_map(self):
        tmp = _tmp()
        try:
            vm = _mock_vm(tmp)
            uid = str(uuid.uuid4())
            u64 = _mem_id_to_uint64(uid)
            vm.id_map[str(u64)] = uid
            vm._save_map()

            map_path = tmp / "brain" / "vector_id_map.json"
            assert map_path.exists()
            data = json.loads(map_path.read_text())
            assert data.get(str(u64)) == uid
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_or_create_loads_existing_index(self):
        """Cover line 75: IdMapIndex.load() branch when index file exists."""
        tmp = _tmp()
        try:
            st_instance = _make_st_mock()
            mock_st_cls = MagicMock(return_value=st_instance)
            idx = _make_index_mock()
            mock_idx_cls = MagicMock()
            mock_idx_cls.return_value = MagicMock()  # fresh index (not used)
            mock_idx_cls.load.return_value = idx

            # Simulate existing index file
            db_dir = tmp / "brain"
            db_dir.mkdir(parents=True, exist_ok=True)
            index_path = db_dir / "vector_memory.tvim"
            index_path.write_bytes(b"fake_index_bytes")  # file must exist

            with (
                patch.object(vector_module, "SentenceTransformer", mock_st_cls),
                patch.object(vector_module, "IdMapIndex", mock_idx_cls),
            ):
                VectorMemory(tmp)

            # Should have called load() not the constructor
            mock_idx_cls.load.assert_called_once_with(str(index_path))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_or_create_loads_existing_map(self):
        """Cover lines 79-80: id_map loaded from file when map_path exists."""
        tmp = _tmp()
        try:
            st_instance = _make_st_mock()
            mock_st_cls = MagicMock(return_value=st_instance)
            mock_idx_cls = MagicMock()
            mock_idx_cls.return_value = _make_index_mock()

            # Simulate existing map file with known content
            db_dir = tmp / "brain"
            db_dir.mkdir(parents=True, exist_ok=True)
            uid = str(uuid.uuid4())
            u64 = _mem_id_to_uint64(uid)
            (db_dir / "vector_id_map.json").write_text(
                json.dumps({str(u64): uid}), encoding="utf-8"
            )

            with (
                patch.object(vector_module, "SentenceTransformer", mock_st_cls),
                patch.object(vector_module, "IdMapIndex", mock_idx_cls),
            ):
                vm = VectorMemory(tmp)

            assert vm.id_map.get(str(u64)) == uid
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_search_empty_index_returns_empty(self):
        """Cover new n_results guard: turbovec returns shape(1,0) for empty index."""
        tmp = _tmp()
        try:
            idx_mock = _make_index_mock()
            # Simulate empty index: shape (1, 0)
            idx_mock.search.return_value = (
                np.empty((1, 0), dtype=np.float32),
                np.empty((1, 0), dtype=np.uint64),
            )
            vm = _mock_vm(tmp, idx_mock)
            results = vm.search("any query", k=5)
            assert results == []
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

