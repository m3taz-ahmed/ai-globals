"""Gap coverage: runtime/agent_catalog.py — all catalog paths."""

from __future__ import annotations

from runtime.agent_catalog import (
    AgentCatalog,
    AgentStatus,
    CatalogAgent,
    CatalogFlow,
    CatalogModel,
    ModelTier,
)


def _catalog() -> AgentCatalog:
    c = AgentCatalog()
    c.register_agent(
        CatalogAgent(
            agent_id="a1", name="Agent1", status=AgentStatus.ALLOWED,
            allowed_flows=["f1"], allowed_models=["m1"], owner="team",
        )
    )
    c.register_agent(
        CatalogAgent(agent_id="a2", name="Agent2", status=AgentStatus.BLOCKED)
    )
    c.register_flow(CatalogFlow(flow_id="f1", name="Flow1", allowed_agents=["a1"]))
    c.register_flow(CatalogFlow(flow_id="f2", name="Flow2"))  # unrestricted
    c.register_model(
        CatalogModel(model_id="m1", provider="p", tier=ModelTier.FRONTIER,
                     training_cutoff="2026-01", known_limitations=["no vision"])
    )
    c.register_model(CatalogModel(model_id="m2", provider="p", tier=ModelTier.LOCAL))
    return c


class TestAgentCatalog:
    def test_register_and_get(self) -> None:
        c = _catalog()
        assert c.get_agent("a1").name == "Agent1"  # type: ignore[union-attr]
        assert c.get_agent("nope") is None
        assert c.get_flow("f1").name == "Flow1"  # type: ignore[union-attr]
        assert c.get_flow("nope") is None
        assert c.get_model("m1").tier is ModelTier.FRONTIER  # type: ignore[union-attr]
        assert c.get_model("nope") is None

    def test_is_agent_allowed(self) -> None:
        c = _catalog()
        assert c.is_agent_allowed("a1")
        assert not c.is_agent_allowed("a2")  # blocked
        assert not c.is_agent_allowed("ghost")

    def test_flow_allowed_matrix(self) -> None:
        c = _catalog()
        assert c.is_flow_allowed_for_agent("a1", "f1")
        assert not c.is_flow_allowed_for_agent("a2", "f1")  # blocked agent
        assert not c.is_flow_allowed_for_agent("a1", "f2")  # not in agent allowlist
        assert not c.is_flow_allowed_for_agent("a1", "ghost")  # flow missing
        assert not c.is_flow_allowed_for_agent("ghost", "f1")

    def test_flow_side_restriction(self) -> None:
        c = _catalog()
        c.register_agent(
            CatalogAgent(agent_id="a3", name="A3", status=AgentStatus.ALLOWED,
                         allowed_flows=["f1"])
        )
        # f1.allowed_agents=["a1"] -> a3 rejected by flow-side list
        assert not c.is_flow_allowed_for_agent("a3", "f1")
        # f2 has no flow-side restriction -> allowed once agent lists it
        c.register_agent(
            CatalogAgent(agent_id="a4", name="A4", status=AgentStatus.ALLOWED,
                         allowed_flows=["f2"])
        )
        assert c.is_flow_allowed_for_agent("a4", "f2")

    def test_model_allowed_matrix(self) -> None:
        c = _catalog()
        assert c.is_model_allowed_for_agent("a1", "m1")
        assert not c.is_model_allowed_for_agent("a2", "m1")  # blocked
        assert not c.is_model_allowed_for_agent("a1", "m2")  # not in allowlist
        assert not c.is_model_allowed_for_agent("a1", "ghost")
        assert not c.is_model_allowed_for_agent("ghost", "m1")

    def test_listings_and_filters(self) -> None:
        c = _catalog()
        assert len(c.list_agents()) == 2
        allowed = c.list_agents(AgentStatus.ALLOWED)
        assert [a.agent_id for a in allowed] == ["a1"]
        assert len(c.list_flows()) == 2
        assert len(c.list_models()) == 2
        local = c.list_models(ModelTier.LOCAL)
        assert [m.model_id for m in local] == ["m2"]

    def test_block_and_clear(self) -> None:
        c = _catalog()
        assert c.block_agent("a1") is True
        assert not c.is_agent_allowed("a1")
        assert c.block_agent("ghost") is False
        c.clear()
        assert c.list_agents() == [] and c.list_flows() == [] and c.list_models() == []
