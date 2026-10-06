"""Gap coverage for memory/: consolidation, decay, graph, hybrid, store,
temporal, vector, ingest, git_memory."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from memory.consolidation import ConsolidationEngine
from memory.decay_scheduler import DecayableEntry, Sector
from memory.git_memory import GitMemoryStore
from memory.graph import SchemaGraph
from memory.hybrid import extract_entities
from memory.ingest import Ingestor
from memory.temporal import TemporalFactStore


class TestConsolidation:
    def _engine(self):
        return ConsolidationEngine()

    def test_non_str_content(self):
        eng = self._engine()
        rep = eng.dedupe_entities([{"id": "a", "content": 123}])
        assert rep.examined == 1

    def test_empty_simhash_skips(self):
        eng = self._engine()
        rep = eng.dedupe_entities([{"id": "a", "content": "!!!"}])
        assert rep.examined == 1
        assert rep.merged_count == 0

    def test_dedupe_writes_index(self):
        eng = self._engine()
        rep = eng.dedupe_entities([{"id": "a", "content": "the quick fox"}], dry_run=False)
        assert rep.examined == 1
        assert eng.simhash_index.size() == 1

    def test_summarize_non_str(self):
        eng = self._engine()
        rep = eng.summarize_long_traces([{"id": "a", "content": 42}])
        assert rep.examined == 1


class TestDecayableEntry:
    def test_post_init_skips(self):
        e = DecayableEntry(id="x", sector=Sector.SEMANTIC,
                           initial_salience=0.5, created_at=100.0,
                           last_decayed_at=50.0, current_salience=0.7)
        assert e.current_salience == 0.7
        assert e.last_decayed_at == 50.0


class TestGraph:
    def test_missing_db(self, tmp_path):
        g = SchemaGraph(str(tmp_path / "nope.db")).build()
        assert len(g.nodes) == 0


class TestHybridEntities:
    def test_phrases_and_acronyms(self):
        ents = extract_entities('call "Quoted Thing" for New York Times API2')
        assert "quoted" in ents
        assert "york" in ents
        assert "api2" in ents


class TestStoreIntegrity:
    def _store(self, tmp_path, monkeypatch):
        from memory.store import MemoryStore
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY", raising=False)
        monkeypatch.delenv("AIZEE_INTEGRITY_KEY_FILE", raising=False)
        return MemoryStore(tmp_path)

    def test_ext_key_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AIZEE_INTEGRITY_KEY_FILE", str(tmp_path / "no.key"))
        s = self._store(tmp_path, monkeypatch)
        assert s._load_integrity_key()  # falls through to generated key

    def test_existing_key_file_empty(self, tmp_path, monkeypatch):
        s = self._store(tmp_path, monkeypatch)
        key_path = tmp_path / "brain" / ".integrity_key"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text("   ", encoding="utf-8")
        key = s._load_integrity_key()
        assert len(key) == 64  # regenerated


class TestTemporal:
    def test_closed_fact_skipped(self):
        store = TemporalFactStore()
        store.set_fact("s", "p", "v1", valid_from="2024-01-01T00:00:00")
        # second set closes v1 -> v1 now has valid_to
        store.set_fact("s", "p", "v2", valid_from="2024-02-01T00:00:00")
        # third set: v1 has valid_to -> 101->96 continue branch
        store.set_fact("s", "p", "v3", valid_from="2024-03-01T00:00:00")
        assert store.query_fact("s", "p") == "v3"


class TestVector:
    def test_search_embed_error(self, monkeypatch):
        import memory.vector as v
        vm = v.VectorMemory.__new__(v.VectorMemory)
        vm.index = MagicMock()
        vm.id_map = {}
        vm.embedder = MagicMock()
        vm.embedder.embed.side_effect = RuntimeError("no model")
        monkeypatch.setattr(v, "IdMapIndex", MagicMock())
        assert vm.search("q") == []

    def test_remove_batch_partial_restore(self, monkeypatch):
        import memory.vector as v
        vm = v.VectorMemory.__new__(v.VectorMemory)
        vm.id_map = {}
        vm.index = MagicMock()
        vm.index.remove.side_effect = RuntimeError("fail")
        vm.index_path = Path("x")
        monkeypatch.setattr(v, "IdMapIndex", MagicMock())
        with pytest.raises(RuntimeError):
            vm.remove_batch(["a", "b"])

    def test_store_brute_force_empty(self):
        from memory.vector import VectorStore
        vs = VectorStore.__new__(VectorStore)
        vs._vectors = {}
        assert vs._brute_force_search([0.1], 5) == []


class TestIngest:
    def _ingestor(self, tmp_path):
        return Ingestor(MagicMock(), root=tmp_path)

    def test_manifest_corrupt_and_non_dict(self, tmp_path):
        ing = self._ingestor(tmp_path)
        mp = ing.manifest_path
        mp.parent.mkdir(parents=True, exist_ok=True)
        mp.write_text("{bad json", encoding="utf-8")
        assert ing._load_manifest() == {}
        mp.write_text("[1,2]", encoding="utf-8")
        assert ing._load_manifest() == {}

    def test_oversize_file_skipped(self, tmp_path):
        ing = self._ingestor(tmp_path)
        (tmp_path / "rules").mkdir()
        big = tmp_path / "rules" / "big.md"
        big.write_text("x" * 500_001, encoding="utf-8")
        with pytest.warns(UserWarning):
            assert ing._read_tracked(big) is None

    def test_resolve_outside_root(self, tmp_path):
        ing = self._ingestor(tmp_path)
        (tmp_path / "rules").mkdir()
        p = tmp_path / "rules" / "a.md"
        p.write_text("x", encoding="utf-8")
        with patch.object(Path, "resolve", return_value=Path("/outside/x.md")):
            assert ing._read_tracked(p) is None

    def test_read_failure(self, tmp_path):
        ing = self._ingestor(tmp_path)
        (tmp_path / "rules").mkdir()
        p = tmp_path / "rules" / "a.md"
        p.write_bytes(b"\xff\xfe\x00")
        assert ing._read_tracked(p) is None

    def test_collect_dir_skips_unreadable(self, tmp_path):
        ing = self._ingestor(tmp_path)
        (tmp_path / "rules").mkdir()
        (tmp_path / "rules" / "bad.md").write_bytes(b"\xff\xfe")
        out = ing._collect_dir("rules", "semantic", False, {})
        assert out[0] == []

    def test_collect_agents_unreadable(self, tmp_path):
        ing = self._ingestor(tmp_path)
        (tmp_path / "AGENTS.md").write_bytes(b"\xff\xfe")
        out = ing._collect_agents({})
        assert out == ([], {}, set())


class TestGitMemory:
    @pytest.fixture()
    def gm(self, tmp_path):
        g = GitMemoryStore(tmp_path / "memrepo")
        return g

    def test_write_existing_corrupt_json(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        (gm.repo_path / "facts").mkdir()
        (gm.repo_path / "facts" / "e1.json").write_text("{corrupt")
        p = gm.write("facts", "e1", {"x": 1})
        assert p.exists()

    def test_read_corrupt(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        (gm.repo_path / "facts").mkdir()
        (gm.repo_path / "facts" / "bad.json").write_text("{corrupt")
        assert gm.read("facts", "bad") is None

    def test_list_missing_category_dir(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        assert gm.list_entries("nosuchcat") == []

    def test_commit_bad_message(self, gm):
        with pytest.raises(ValueError):
            gm.commit("")
        with pytest.raises(ValueError):
            gm.commit("x" * 501)

    def test_commit_status_fails(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        bad = subprocess.CompletedProcess([], 1, "", "err")
        with patch.object(gm, "_git", return_value=bad):
            with pytest.raises(RuntimeError):
                gm.commit("msg")

    def test_log_bad_limit(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        ok = subprocess.CompletedProcess([], 0, "h|a|d|m", "")
        with patch.object(gm, "_git", return_value=ok):
            out = gm.log(limit="abc")
        assert out == [{"hash": "h", "author": "a", "date": "d", "message": "m"}]

    def test_log_malformed_line(self, gm):
        gm.repo_path.mkdir(parents=True, exist_ok=True)
        ok = subprocess.CompletedProcess([], 0, "short|line\n\nh|a|d|m", "")
        with patch.object(gm, "_git", return_value=ok):
            out = gm.log()
        assert len(out) == 1

    def test_safe_ref_invalid(self, gm):
        with pytest.raises(ValueError):
            gm.diff("--all")
        with pytest.raises(ValueError):
            gm.checkout(123)  # type: ignore[arg-type]

    def test_remote_url_validation(self, gm):
        with pytest.raises(ValueError):
            gm._validate_remote_url("")
        with pytest.raises(ValueError):
            gm._validate_remote_url("ext::cmd")
        gm._validate_remote_url("git@github.com:user/repo")  # no raise
        with pytest.raises(ValueError):
            gm._validate_remote_url("file:///etc/passwd")
        with pytest.raises(ValueError):
            gm._validate_remote_url("ftp://x/y")
        with pytest.raises(ValueError):
            gm._validate_remote_url("/bare/path")
