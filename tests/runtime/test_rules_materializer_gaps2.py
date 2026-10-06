"""Gap coverage round 2: rules_materializer emitters + dict paths."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.rules_materializer import (
    RuleEntry,
    RulesMaterializer,
    ScopeLevel,
    ToolTarget,
)
from runtime.schemas import ValidationError


class TestRuleEntry:
    def test_to_dict_with_globs(self) -> None:
        e = RuleEntry(key="k", content="c", scope=ScopeLevel.REPO,
                      globs=["*.py"], always_apply=True, description="d")
        d = e.to_dict()
        assert d["globs"] == ["*.py"] and d["scope"] == "repo"
        e2 = RuleEntry(key="k", content="c")
        assert "globs" not in e2.to_dict()


class TestEmitters:
    def _rules(self) -> list[RuleEntry]:
        return [
            RuleEntry(key="r1", content="content one"),
            RuleEntry(key="r2", content="content two"),
        ]

    def test_all_text_emitters(self, tmp_path: Path) -> None:
        m = RulesMaterializer(tmp_path)
        rules = self._rules()
        for target in (
            ToolTarget.CLINE, ToolTarget.WINDSURF, ToolTarget.COPILOT,
            ToolTarget.AIDER, ToolTarget.DEVIN,
        ):
            out = m._emitter_for(target)(rules)
            assert "r1" in out and "content one" in out

    def test_materialize_empty_raises(self, tmp_path: Path) -> None:
        m = RulesMaterializer(tmp_path)
        with pytest.raises(ValidationError):
            m.materialize([])

    def test_materialize_all_targets(self, tmp_path: Path) -> None:
        m = RulesMaterializer(tmp_path)
        results = m.materialize(self._rules())
        assert len(results) == len(list(ToolTarget))
        assert all(r.ok for r in results)

    def test_materialize_all_empty_raises(self, tmp_path: Path) -> None:
        m = RulesMaterializer(tmp_path)
        with pytest.raises(ValidationError):
            m.materialize_all({})

    def test_materialize_all_resolves(self, tmp_path: Path) -> None:
        m = RulesMaterializer(tmp_path)
        results = m.materialize_all(
            {ScopeLevel.REPO: [RuleEntry(key="k", content="c")]}
        )
        assert results and all(r.ok for r in results)
