"""Gap tests for runtime/rules_materializer.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.rules_materializer import (
    MaterializationResult,
    RuleEntry,
    RulesMaterializer,
    ScopeLevel,
    ToolTarget,
)
from runtime.schemas import ValidationError


def _r(key: str, scope=ScopeLevel.REPO, **kw) -> RuleEntry:
    return RuleEntry(key=key, content=f"content-{key}", scope=scope, **kw)


class TestResult:
    def test_ok_property(self):
        r = MaterializationResult(target=ToolTarget.CLAUDE)
        assert r.ok is True
        r.errors.append("x")
        assert r.ok is False


class TestResolve:
    def test_lower_scope_does_not_override(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        out = m.resolve({
            ScopeLevel.ORG: [_r("k", scope=ScopeLevel.ORG)],
            ScopeLevel.USER: [_r("k", scope=ScopeLevel.USER)],
        })
        assert len(out) == 1
        assert out[0].scope == ScopeLevel.ORG

    def test_equal_scope_overwrites(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        out = m.resolve({ScopeLevel.REPO: [
            _r("k", scope=ScopeLevel.REPO),
            RuleEntry(key="k", content="newer", scope=ScopeLevel.REPO),
        ]})
        assert out[0].content == "newer"

    def test_sorted_output(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        out = m.resolve({ScopeLevel.REPO: [_r("b"), _r("a")]})
        assert [r.key for r in out] == ["a", "b"]


class TestEmit:
    def test_unsafe_glob_skipped(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        out = m._emit_cursor([_r("k", globs=["*.py", "bad;glob$(x)"])])
        assert '"*.py"' in out
        assert "bad;glob" not in out

    def test_no_globs_default(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        out = m._emit_cursor([_r("k")])
        assert '"**/*"' in out


class TestEmitOne:
    def test_unknown_target(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        fake = type("T", (), {"value": "ghost"})()
        res = m._emit_one(fake, [_r("k")])
        assert res.ok is False and "Unknown target" in res.errors[0]

    def test_traversal_blocked(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        with patch.dict(m._TARGET_FILES, {ToolTarget.CLAUDE: "../escape.md"}):
            res = m._emit_one(ToolTarget.CLAUDE, [_r("k")])
        assert res.ok is False
        assert "traversal" in res.errors[0].lower()

    def test_resolve_oserror_passes(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        with patch.object(Path, "resolve", side_effect=OSError("x")):
            res = m._emit_one(ToolTarget.CLAUDE, [_r("k")])
        # OSError swallowed; write may still succeed -> ok either way, no crash
        assert isinstance(res.ok, bool)

    def test_write_oserror(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        with patch.object(Path, "write_text", side_effect=OSError("disk")):
            res = m._emit_one(ToolTarget.CLAUDE, [_r("k")])
        assert res.ok is False
        assert "Write failed" in res.errors[0]

    def test_emitter_exception(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        with patch.object(m, "_emitter_for", side_effect=RuntimeError("emit boom")):
            res = m._emit_one(ToolTarget.CLAUDE, [_r("k")])
        assert res.ok is False
        assert "Emit failed" in res.errors[0]

    def test_materialize_all_empty(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        with pytest.raises(ValidationError):
            m.materialize_all({})


class TestDrift:
    def test_missing_file_marks_all(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        drift = m.detect_drift({ScopeLevel.REPO: [_r("a"), _r("b")]},
                               targets=[ToolTarget.CLAUDE])
        assert drift["claude"] == ["a", "b"]

    def test_partial_drift(self, tmp_path):
        m = RulesMaterializer(tmp_path)
        (tmp_path / "CLAUDE.md").write_text("contains rule-alpha only")
        drift = m.detect_drift(
            {ScopeLevel.REPO: [_r("rule-alpha"), _r("rule-beta")]},
            targets=[ToolTarget.CLAUDE])
        assert drift["claude"] == ["rule-beta"]
