"""Tests for runtime/agent_catalog.py — allowlist of agents/flows/models.

Covers: enums, dataclasses, AgentCatalog CRUD, permission checks,
filtering, thread safety, clear. AAA pattern, one behavior per test.
FAST tier — no MCP, no kernel, no model loading.
"""

from __future__ import annotations

import threading

import pytest

from runtime.agent_catalog import (
    AgentCatalog,
    AgentStatus,
    CatalogAgent,
    CatalogFlow,
    CatalogModel,
    ModelTier,
)

# -- enums ----------------------------------------------------------------


class TestAgentStatus:
    def test_values(self) -> None:
        assert AgentStatus.ALLOWED.value == "allowed"
        assert AgentStatus.BLOCKED.value == "blocked"
        assert AgentStatus.DEPRECATED.value == "deprecated"

    def test_is_str(self) -> None:
        assert isinstance(AgentStatus.ALLOWED, str)


class TestModelTier:
    def test_values(self) -> None:
        assert ModelTier.FRONTIER.value == "frontier"
        assert ModelTier.STANDARD.value == "standard"
        assert ModelTier.LOCAL.value == "local"


# -- dataclasses ----------------------------------------------------------


class TestCatalogAgent:
    def test_defaults(self) -> None:
        agent = CatalogAgent(
            agent_id="a1", name="A1", status=AgentStatus.ALLOWED,
        )
        assert agent.allowed_flows == []
        assert agent.allowed_models == []
        assert agent.owner == ""

    def test_explicit_fields(self) -> None:
        agent = CatalogAgent(
            agent_id="a1", name="A1", status=AgentStatus.ALLOWED,
            allowed_flows=["f1"], allowed_models=["m1"], owner="team",
        )
        assert agent.allowed_flows == ["f1"]
        assert agent.owner == "team"


class TestCatalogFlow:
    def test_default_max_steps(self) -> None:
        flow = CatalogFlow(flow_id="f1", name="F1", allowed_agents=["a1"])
        assert flow.max_steps == 50


class TestCatalogModel:
    def test_default_max_tokens(self) -> None:
        model = CatalogModel(
            model_id="m1", provider="openai", tier=ModelTier.FRONTIER,
        )
        assert model.max_tokens == 200000


# -- fixtures -------------------------------------------------------------


@pytest.fixture
def catalog() -> AgentCatalog:
    return AgentCatalog()


@pytest.fixture
def populated_catalog() -> AgentCatalog:
    cat = AgentCatalog()
    cat.register_agent(CatalogAgent(
        agent_id="coder", name="Coder", status=AgentStatus.ALLOWED,
        allowed_flows=["code-gen", "review"], allowed_models=["gpt-4o"],
        owner="team-a",
    ))
    cat.register_agent(CatalogAgent(
        agent_id="legacy", name="Legacy", status=AgentStatus.DEPRECATED,
        allowed_flows=["code-gen"], allowed_models=["gpt-3.5"],
    ))
    cat.register_flow(CatalogFlow(
        flow_id="code-gen", name="Code Gen", allowed_agents=["coder"],
    ))
    cat.register_model(CatalogModel(
        model_id="gpt-4o", provider="openai", tier=ModelTier.FRONTIER,
    ))
    cat.register_model(CatalogModel(
        model_id="llama3", provider="local", tier=ModelTier.LOCAL,
    ))
    return cat


# -- registration / CRUD --------------------------------------------------


class TestRegisterAndGet:
    def test_register_and_get_agent(self, catalog: AgentCatalog) -> None:
        agent = CatalogAgent(
            agent_id="a1", name="A1", status=AgentStatus.ALLOWED,
        )
        catalog.register_agent(agent)
        assert catalog.get_agent("a1") is agent

    def test_get_agent_missing_returns_none(self, catalog: AgentCatalog) -> None:
        assert catalog.get_agent("nope") is None

    def test_register_replaces_agent(self, catalog: AgentCatalog) -> None:
        catalog.register_agent(CatalogAgent(
            agent_id="a1", name="Old", status=AgentStatus.ALLOWED,
        ))
        catalog.register_agent(CatalogAgent(
            agent_id="a1", name="New", status=AgentStatus.BLOCKED,
        ))
        got = catalog.get_agent("a1")
        assert got is not None and got.name == "New"

    def test_register_and_get_flow(self, catalog: AgentCatalog) -> None:
        flow = CatalogFlow(flow_id="f1", name="F1", allowed_agents=["a1"])
        catalog.register_flow(flow)
        assert catalog.get_flow("f1") is flow

    def test_get_flow_missing_returns_none(self, catalog: AgentCatalog) -> None:
        assert catalog.get_flow("nope") is None

    def test_register_and_get_model(self, catalog: AgentCatalog) -> None:
        model = CatalogModel(
            model_id="m1", provider="p", tier=ModelTier.STANDARD,
        )
        catalog.register_model(model)
        assert catalog.get_model("m1") is model

    def test_get_model_missing_returns_none(self, catalog: AgentCatalog) -> None:
        assert catalog.get_model("nope") is None


# -- permission checks ----------------------------------------------------


class TestPermissionChecks:
    def test_is_agent_allowed_true(self, populated_catalog: AgentCatalog) -> None:
        assert populated_catalog.is_agent_allowed("coder") is True

    def test_is_agent_allowed_for_deprecated(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.is_agent_allowed("legacy") is False

    def test_is_agent_allowed_missing(self, catalog: AgentCatalog) -> None:
        assert catalog.is_agent_allowed("nope") is False

    def test_is_flow_allowed_for_agent_true(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.is_flow_allowed_for_agent("coder", "code-gen") is True

    def test_is_flow_allowed_for_agent_not_in_list(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.is_flow_allowed_for_agent("coder", "missing") is False

    def test_is_flow_allowed_for_blocked_agent(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        populated_catalog.block_agent("coder")
        assert populated_catalog.is_flow_allowed_for_agent("coder", "code-gen") is False

    def test_is_model_allowed_for_agent_true(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.is_model_allowed_for_agent("coder", "gpt-4o") is True

    def test_is_model_allowed_for_agent_not_in_list(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.is_model_allowed_for_agent("coder", "llama3") is False


# -- listings / filtering -------------------------------------------------


class TestListings:
    def test_list_agents_all(self, populated_catalog: AgentCatalog) -> None:
        ids = {a.agent_id for a in populated_catalog.list_agents()}
        assert ids == {"coder", "legacy"}

    def test_list_agents_filtered_by_status(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        allowed = populated_catalog.list_agents(status=AgentStatus.ALLOWED)
        assert {a.agent_id for a in allowed} == {"coder"}

    def test_list_flows(self, populated_catalog: AgentCatalog) -> None:
        ids = {f.flow_id for f in populated_catalog.list_flows()}
        assert ids == {"code-gen"}

    def test_list_models_all(self, populated_catalog: AgentCatalog) -> None:
        ids = {m.model_id for m in populated_catalog.list_models()}
        assert ids == {"gpt-4o", "llama3"}

    def test_list_models_filtered_by_tier(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        local = populated_catalog.list_models(tier=ModelTier.LOCAL)
        assert {m.model_id for m in local} == {"llama3"}


# -- block / clear --------------------------------------------------------


class TestBlockAndClear:
    def test_block_agent_changes_status(
        self, populated_catalog: AgentCatalog,
    ) -> None:
        assert populated_catalog.block_agent("coder") is True
        agent = populated_catalog.get_agent("coder")
        assert agent is not None and agent.status == AgentStatus.BLOCKED

    def test_block_agent_missing_returns_false(
        self, catalog: AgentCatalog,
    ) -> None:
        assert catalog.block_agent("nope") is False

    def test_clear_removes_all(self, populated_catalog: AgentCatalog) -> None:
        populated_catalog.clear()
        assert populated_catalog.list_agents() == []
        assert populated_catalog.list_flows() == []
        assert populated_catalog.list_models() == []


# -- thread safety --------------------------------------------------------


class TestThreadSafety:
    def test_concurrent_register_agents(self) -> None:
        cat = AgentCatalog()
        n_threads = 20
        per_thread = 50

        def worker(tid: int) -> None:
            for i in range(per_thread):
                cat.register_agent(CatalogAgent(
                    agent_id=f"t{tid}-{i}", name=f"T{tid}",
                    status=AgentStatus.ALLOWED,
                ))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(cat.list_agents()) == n_threads * per_thread
