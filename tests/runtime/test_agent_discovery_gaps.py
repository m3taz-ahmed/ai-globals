"""Gap coverage for runtime/agent_discovery.py."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from runtime.agent_discovery import (
    AgentDiscovery,
    _first_prose_line,
    _parse_frontmatter,
    _split_list,
    discover_by_capability,
    skill_to_entity,
)
from runtime.service_catalog import (
    REL_OWNED_BY,
    REL_PROVIDES_CAPABILITY,
    CatalogEntity,
    EntityMeta,
    EntityRelation,
)


class TestParseConfig:
    def _discover(self, tmp_path):
        return AgentDiscovery(home=tmp_path, project_root=tmp_path).discover()

    def test_rules_dir_iterdir_oserror(self, tmp_path):
        rules = tmp_path / ".cursor" / "rules"
        rules.mkdir(parents=True)
        real_iterdir = Path.iterdir

        def guarded(self, *a, **k):
            if self == rules:
                raise OSError("locked")
            return real_iterdir(self, *a, **k)

        with patch.object(Path, "iterdir", guarded):
            agents = self._discover(tmp_path)
        cursor = [a for a in agents if a.name == "Cursor (rules)"]
        assert cursor and cursor[0].metadata["file_count"] == 0

    def test_json_decode_error_returns_agent(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{bad json")
        agents = self._discover(tmp_path)
        assert any(a.name == "Claude Code" for a in agents)

    def test_mcp_servers_non_dict_ignored(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            json.dumps({"mcpServers": [1, 2, 3], "model": 42})
        )
        agents = self._discover(tmp_path)
        agent = next(a for a in agents if a.name == "Claude Code")
        assert agent.mcp_servers == []
        assert agent.model is None

    def test_yaml_parse_error_returns_agent(self, tmp_path):
        (tmp_path / ".aider.conf.yml").write_text("a: [unclosed\n  - : :")
        agents = self._discover(tmp_path)
        assert any(a.name == "Aider" for a in agents)

    def test_yaml_non_str_model(self, tmp_path):
        (tmp_path / ".aider.conf.yml").write_text("model: 123\n")
        agents = self._discover(tmp_path)
        agent = next(a for a in agents if a.name == "Aider")
        assert agent.model is None

    def test_dedup_same_kind_and_path(self, tmp_path):
        (tmp_path / "AGENTS.md").write_text("# x")
        dup = ("generic", "AGENTS.md", "AGENTS.md")
        with patch.object(
            AgentDiscovery, "_TARGETS", [*AgentDiscovery._TARGETS, dup]
        ):
            agents = self._discover(tmp_path)
        names = [a.name for a in agents]
        assert names.count("AGENTS.md") == 1


class TestFrontmatter:
    def test_unclosed_frontmatter(self):
        fm, body = _parse_frontmatter("---\nkey: v\nno closer")
        assert fm == {}
        assert "no closer" in body

    def test_invalid_yaml_frontmatter(self):
        fm, body = _parse_frontmatter("---\n{[invalid:\n---\nbody")
        assert fm == {}
        assert body == "body"

    def test_non_dict_yaml_frontmatter(self):
        fm, body = _parse_frontmatter("---\n- just\n- a list\n---\nbody")
        assert fm == {}
        assert body == "body"


class TestSmallHelpers:
    def test_first_prose_line_only_headings(self):
        assert _first_prose_line("# H1\n## H2\n[link]\n\n") == ""

    def test_split_list_variants(self):
        assert _split_list(None) == []
        assert _split_list(["a", " ", "b"]) == ["a", "b"]
        assert _split_list("a, b ,,c") == ["a", "b", "c"]
        assert _split_list(42) == []


class TestCapabilityDiscovery:
    def test_non_matching_relation_falls_to_spec(self):
        ent = CatalogEntity(
            api_version="v1",
            kind="Skill",
            metadata=EntityMeta(name="s"),
            spec={"capabilities": ["cap-x"]},
            relations=[EntityRelation(REL_OWNED_BY, "agent:a")],
        )
        catalog = SimpleNamespace(all=lambda: [ent])
        out = discover_by_capability(catalog, "cap-x")
        assert out == [ent]

    def test_relation_match_breaks(self):
        ent = CatalogEntity(
            api_version="v1",
            kind="Skill",
            metadata=EntityMeta(name="s"),
            relations=[EntityRelation(REL_PROVIDES_CAPABILITY, "cap-y")],
        )
        catalog = SimpleNamespace(all=lambda: [ent])
        out = discover_by_capability(catalog, "cap-y")
        assert out == [ent]


class TestSkillToEntity:
    def test_tech_stack_spec(self, tmp_path):
        skill = tmp_path / "s.md"
        skill.write_text(
            "---\ndescription: d\ntech_stack: python, react\n---\n# Body\n"
        )
        ent = skill_to_entity(skill, "s")
        assert ent.spec["tech_stack"] == ["python", "react"]
