"""Gap tests for memory/git_memory.py."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from memory.git_memory import GitMemoryStore


@pytest.fixture
def store(tmp_path):
    s = GitMemoryStore(tmp_path / "repo")
    s.init()
    return s


class TestWrite:
    def test_existing_bad_json_uses_now(self, store):
        f = store.repo_path / "facts" / "e1.json"
        f.write_text("{corrupt", encoding="utf-8")
        p = store.write("facts", "e1", {"c": 1})
        assert json.loads(p.read_text())["content"] == {"c": 1}

    def test_existing_good_json_keeps_created(self, store):
        store.write("facts", "e2", {"v": 1})
        first = json.loads((store.repo_path / "facts" / "e2.json").read_text())
        store.write("facts", "e2", {"v": 2})
        second = json.loads((store.repo_path / "facts" / "e2.json").read_text())
        assert second["created_at"] == first["created_at"]
        assert second["updated_at"] >= first["updated_at"]

    def test_unsafe_components(self, store):
        with pytest.raises(ValueError):
            store.write("../evil", "e", {})
        with pytest.raises(ValueError):
            store.write("facts", "a/b", {})


class TestReadDeleteList:
    def test_read_corrupt_returns_none(self, store):
        f = store.repo_path / "facts" / "bad.json"
        f.write_text("{not json", encoding="utf-8")
        assert store.read("facts", "bad") is None

    def test_read_missing(self, store):
        assert store.read("facts", "ghost") is None

    def test_delete(self, store):
        store.write("facts", "d1", {})
        assert store.delete("facts", "d1") is True
        assert store.delete("facts", "d1") is False

    def test_list_missing_category(self, store):
        assert store.list_entries("nosuchcat") == []

    def test_list_all_skips_git_and_files(self, store):
        store.write("facts", "a", {})
        store.write("preferences", "b", {})
        (store.repo_path / "stray.txt").write_text("x")
        entries = store.list_entries()
        assert set(entries) == {"a", "b"}


class TestCommit:
    def test_bad_message(self, store):
        with pytest.raises(ValueError):
            store.commit("")
        with pytest.raises(ValueError):
            store.commit("x" * 501)

    def test_status_failure_raises(self, store):
        fake = type("R", (), {"returncode": 1, "stderr": "git died", "stdout": ""})()
        with patch.object(store, "_git", return_value=fake):
            with pytest.raises(RuntimeError):
                store.commit("msg")

    def test_nothing_to_commit(self, store):
        # fresh repo with no *.json changes -> False (or True if auto-init wrote)
        res = store.commit("empty")
        assert res is False

    def test_commit_happy(self, store):
        store.write("facts", "c1", {"v": 1})
        assert store.commit("add c1") is True


class TestLog:
    def test_bad_limit_coerced(self, store):
        store.write("facts", "c1", {})
        store.commit("c")
        assert store.log(limit="bogus")  # coerced to 20
        assert store.log(limit=0)
        assert store.log(limit=99999)

    def test_log_no_commits(self, tmp_path):
        s = GitMemoryStore(tmp_path / "r2")
        s.init()
        assert s.log() == []

    def test_log_skips_malformed_lines(self, store):
        store.write("facts", "c1", {})
        store.commit("c")
        fake = type("R", (), {"returncode": 0, "stderr": "",
                              "stdout": "hash|auth|date|msg\nmalformed-no-pipes\n\nh2|a|d|m2"})()
        with patch.object(store, "_git", return_value=fake):
            out = store.log()
        assert len(out) == 2 and out[0]["hash"] == "hash"


class TestRefs:
    def test_safe_ref_rejects(self, store):
        for bad in ("-option", "not a ref", "--exec=x", "", 123):
            with pytest.raises(ValueError):
                store._safe_ref(bad)  # type: ignore[arg-type]

    def test_safe_ref_accepts(self, store):
        assert store._safe_ref("HEAD~1") == "HEAD~1"
        assert store._safe_ref("feature/x") == "feature/x"


class TestRemoteUrl:
    def test_empty(self, store):
        with pytest.raises(ValueError):
            store._validate_remote_url("")

    def test_ext_transport(self, store):
        with pytest.raises(ValueError):
            store._validate_remote_url("ext::sh -c evil")

    def test_scp_style_allowed(self, store):
        store._validate_remote_url("git@github.com:user/repo")  # no raise

    def test_file_scheme(self, store):
        with pytest.raises(ValueError):
            store._validate_remote_url("file:///etc/passwd")

    def test_unknown_scheme(self, store):
        with pytest.raises(ValueError):
            store._validate_remote_url("ftp://x/y")

    def test_bare_path(self, store):
        with pytest.raises(ValueError):
            store._validate_remote_url("/local/path")
        with pytest.raises(ValueError):
            store._validate_remote_url("relative/path")

    def test_https_ok(self, store):
        store._validate_remote_url("https://github.com/u/r.git")

    def test_add_remote_bad_name(self, store):
        with pytest.raises(ValueError):
            store.add_remote("bad name!", "https://x/y")


class TestBranchesAndStatus:
    def test_branch_ops(self, store):
        store.write("facts", "c1", {})
        store.commit("c")
        assert store.create_branch("feat-x") is True
        assert "feat-x" in store.list_branches()
        assert store.switch_branch("feat-x") is True
        st = store.status()
        assert st["branch"] == "feat-x"
        assert st["total_entries"] == 1

    def test_checkout_bad_ref(self, store):
        assert store.checkout("nonexistent-ref-xyz") is False

    def test_push_pull_no_remote(self, store):
        assert store.push("origin", "main") is False
        assert store.pull("origin", "main") is False
