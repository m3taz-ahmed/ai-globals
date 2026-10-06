"""Gap coverage batch 10: settings, taint, reasoning_graph, plugin, budget_escalation,
blast_radius, middleware, service_catalog residuals, ci."""

from __future__ import annotations

from pathlib import Path

import pytest

import runtime.settings as settings_mod
from runtime.blast_radius import (
    BlastEdge,
    BlastNode,
    BlastRadiusGraph,
    NodeType,
    _bfs_shortest,
    _reachable_nodes,
)
from runtime.budget_escalation import (
    EscalationConfig,
    EscalationDirective,
    EscalationStage,
    recomputed_budget_flags,
)
from runtime.ci import run_command
from runtime.middleware import MiddlewareResult
from runtime.plugin import PluginManager, _is_plugin_source_safe
from runtime.reasoning_graph import NodeKind, ReasoningGraph
from runtime.schemas import ValidationError
from runtime.service_catalog import (
    REL_DEPENDS_ON,
    CatalogEntity,
    CatalogStore,
    EntityMeta,
    EntityRelation,
)
from runtime.settings import SettingsManager, _migrate_v1_to_v2, _validate_section


class TestSettingsGaps:
    def test_migrate_v1_dash_already_has_proxies(self) -> None:
        out = _migrate_v1_to_v2({"dashboard": {"trusted_proxies": ["1.2.3.4"]}, "version": 1})
        assert out["dashboard"]["trusted_proxies"] == ["1.2.3.4"]

    def test_validate_dashboard_bad_proxies(self) -> None:
        with pytest.raises(ValidationError):
            _validate_section("dashboard", {"trusted_proxies": "notalist"})

    def test_validate_plugins_section(self) -> None:
        _validate_section("plugins", {"p": {"enabled": True}})
        with pytest.raises(ValidationError):
            _validate_section("plugins", {"p": "x"})
        with pytest.raises(ValidationError):
            _validate_section("plugins", {"p": {"enabled": "yes"}})

    def test_migration_missing_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings_mod, "_MIGRATIONS", {})
        mgr = SettingsManager.__new__(SettingsManager)
        mgr._settings_file = tmp_path / "settings.json"
        mgr._settings_file.write_text('{"version": 1}')
        mgr._state_dir = tmp_path
        mgr._data = {}
        out = mgr._migrate_if_needed({"version": 1})
        assert out["version"] == 1


class TestTaintGuardrail:
    def _fn(self):
        from runtime.policy import default_guardrail_registry
        return default_guardrail_registry._guardrails["input"]["taint_flow_check"]

    def test_iter_strings_nested_and_empty(self) -> None:
        fn = self._fn()
        res = fn({
            "tool": "write",
            "args": {"items": ["plain", {"k": "v"}, ["deep"]], "empty": ""},
        })
        assert res.tripwire_triggered is False

    def test_non_sensitive_tool(self) -> None:
        assert self._fn()({"tool": "read", "x": "v"}).tripwire_triggered is False

    def test_action_dict_tool(self) -> None:
        res = self._fn()({"action": {"type": "exec"}, "args": {"q": "echo hi"}})
        assert res.tripwire_triggered is False


class TestReasoningGraph:
    def _g(self) -> ReasoningGraph:
        g = ReasoningGraph()
        g.add_node("a", NodeKind.FINDING)
        g.add_node("b", NodeKind.ACTION)
        g.add_node("c", NodeKind.ACTION)
        return g

    def test_add_edge_unknown_target(self) -> None:
        g = self._g()
        with pytest.raises(KeyError):
            g.add_edge("a", "ghost")

    def test_propagate_cycle_and_paths(self) -> None:
        g = self._g()
        g.add_node("r", NodeKind.FINDING)
        g.add_edge("a", "b")
        g.add_edge("b", "a")  # cycle back-edge
        g.add_edge("a", "c")
        g.add_edge("r", "a")  # root reaches the cycle -> exercises visited guard
        g.activate("a")
        g.activate("r")
        newly = g.propagate()
        assert set(newly) >= {"b", "c"}
        assert g.active_path()  # must not recurse forever on the cycle

    def test_longest_path_inactive_edge(self) -> None:
        g = self._g()
        g.add_node("d", NodeKind.ACTION)
        g.add_edge("a", "b")
        g.add_edge("b", "c")
        g.add_edge("a", "c")  # shorter sibling -> sub path not longer
        g.add_edge("a", "d")  # inactive target edge
        g.activate("a")
        g.propagate()
        path = g.active_path()
        assert path[0] == "a"
        assert len(path) == 3

    def test_two_roots_longest(self) -> None:
        g = ReasoningGraph()
        g.add_node("r1", NodeKind.FINDING)
        g.add_node("r2", NodeKind.FINDING)
        g.add_node("x", NodeKind.ACTION)
        g.add_edge("r2", "x")
        for n in ("r1", "r2", "x"):
            g.activate(n)
        g.propagate()
        assert len(g.active_path()) >= 2


class TestPluginGaps:
    def test_builtins_import_blocked(self) -> None:
        safe, reason = _is_plugin_source_safe("from builtins import globals\n", "p.py")
        assert safe is False and "builtins" in reason

    def test_rglob_oserror(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pm = PluginManager.__new__(PluginManager)
        pm.root = tmp_path
        pm.plugins_dir = tmp_path / "plugins"
        pkg = tmp_path / "plugins" / "mypkg"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("x = 1")
        monkeypatch.setattr(Path, "rglob", lambda self, pat: (_ for _ in ()).throw(OSError("x")))
        assert pm._load_plugin_module("mypkg") is None

    def test_file_read_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        pm = PluginManager.__new__(PluginManager)
        pm.root = tmp_path
        pm.plugins_dir = tmp_path / "plugins"
        pkg = tmp_path / "plugins" / "mypkg2"
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("x = 1")
        (pkg / "sub.py").write_text("y = 1")
        orig = Path.read_text

        def flaky(self: Path, *a: object, **k: object) -> str:
            if self.name == "sub.py":
                raise OSError("denied")
            return orig(self, *a, **k)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", flaky)
        assert pm._load_plugin_module("mypkg2") is None


class TestBudgetEscalation:
    def test_unsorted_bands_raise(self) -> None:
        with pytest.raises(ValueError, match="sorted"):
            EscalationConfig(root_bands=(0.9, 0.5, 0.95))

    def test_event_to_dict(self) -> None:
        e = EscalationDirective(
            stage=EscalationStage.NOTICE, label="l", message="m",
            utilization=0.7, is_root=True,
        )
        assert e.to_dict()["stage"] == "notice"

    def test_recomputed_flags(self) -> None:
        assert recomputed_budget_flags(0, 0) == (False, False)
        assert recomputed_budget_flags(50, 100) == (False, False)
        assert recomputed_budget_flags(95, 100)[1] is True


class TestBlastRadius:
    def _graph(self) -> BlastRadiusGraph:
        g = BlastRadiusGraph()
        g.add_node(BlastNode(node_id="a", node_type=NodeType.AGENT, name="a"))
        g.add_node(BlastNode(node_id="b", node_type=NodeType.TOOL, name="b"))
        g.add_node(BlastNode(node_id="c", node_type=NodeType.CREDENTIAL, name="c"))
        g.add_edge(BlastEdge(source_id="a", target_id="b", relationship="uses"))
        g.add_edge(BlastEdge(source_id="b", target_id="a", relationship="x"))
        g.add_edge(BlastEdge(source_id="b", target_id="c", relationship="exposes"))
        return g

    def test_bfs_visited_and_dup(self) -> None:
        g = self._graph()
        assert g.impact("a") is not None
        # self-loop edge queues a duplicate -> `current in visited` continue
        adj = {"s": [("s", None)], "x": []}
        out = _reachable_nodes(adj, "s")
        assert out == {"s"}

    def test_bfs_shortest_visited(self) -> None:
        # adjacency with a cycle forces the `target_id in visited` continue
        nodes = {
            "a": BlastNode(node_id="a", node_type=NodeType.AGENT, name="a"),
            "b": BlastNode(node_id="b", node_type=NodeType.TOOL, name="b"),
        }
        adj = {"a": [("b", BlastEdge(source_id="a", target_id="b", relationship="r")),
                     ("a", BlastEdge(source_id="a", target_id="a", relationship="s"))], "b": []}
        out = _bfs_shortest(nodes, adj, "a", NodeType.CREDENTIAL)
        assert out is None

    def test_agent_credential_autocreate(self) -> None:
        g = BlastRadiusGraph()
        g.add_agent("agent1", [], ["aws_key"])
        assert "cred:aws_key" in g._nodes


class TestMiddleware:
    def test_aizee_error_in_handler(self) -> None:
        import runtime.middleware as mw

        pipe = mw.MiddlewarePipeline()
        err = ValidationError("nope")

        def handler(ctx: mw.ActionContext) -> mw.MiddlewareResult[object]:
            raise err

        out = pipe.execute(mw.ActionContext(action_type="t"), handler)
        assert isinstance(out, MiddlewareResult) and out.ok is False and out.error is err

    def test_generic_error_normalized(self) -> None:
        import runtime.middleware as mw

        pipe = mw.MiddlewarePipeline()

        def handler(ctx: mw.ActionContext) -> mw.MiddlewareResult[object]:
            raise RuntimeError("boom")

        out = pipe.execute(mw.ActionContext(action_type="t"), handler)
        assert out.ok is False and out.error is not None
        assert "boom" in out.error.message

    def test_middleware_error_wrapped(self) -> None:
        import runtime.middleware as mw

        pipe = mw.MiddlewarePipeline()

        def bad_mw(ctx: mw.ActionContext, nxt: object) -> mw.MiddlewareResult[object]:
            raise ValueError("mw-fail")

        def handler(ctx: mw.ActionContext) -> mw.MiddlewareResult[object]:
            return mw.MiddlewareResult(ok=True, data="done")

        pipe.use(bad_mw)
        out = pipe.execute(mw.ActionContext(action_type="t"), handler)
        assert out.ok is False and out.error is not None
        assert "mw-fail" in out.error.message


class TestServiceCatalogResiduals:
    def test_diamond_visited_skip(self) -> None:
        s = CatalogStore()
        s.add(CatalogEntity(api_version="v", kind="Skill", metadata=EntityMeta(name="b"),
                            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/d")]))
        s.add(CatalogEntity(api_version="v", kind="Skill", metadata=EntityMeta(name="c"),
                            relations=[EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/d")]))
        s.add(CatalogEntity(api_version="v", kind="Skill", metadata=EntityMeta(name="d")))
        s.add(CatalogEntity(api_version="v", kind="Skill", metadata=EntityMeta(name="a"),
                            relations=[
                                EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/b"),
                                EntityRelation(type=REL_DEPENDS_ON, target_ref="skill:default/c"),
                            ]))
        deps = s.get_dependencies("skill:default/a")
        assert {d.metadata.name for d in deps} == {"b", "c", "d"}

    def test_dependents_non_dep_relation_skipped(self) -> None:
        s = CatalogStore()
        s.add(CatalogEntity(
            api_version="v", kind="Skill", metadata=EntityMeta(name="x"),
            relations=[EntityRelation(type="partOf", target_ref="skill:default/y")],
        ))
        assert s.get_dependents("skill:default/y") == []


class TestCIMore:
    def test_command_not_found(self, tmp_path: Path) -> None:
        code, _out = run_command(["nonexistent-cmd-xyz-123"], tmp_path)
        assert code == 1

