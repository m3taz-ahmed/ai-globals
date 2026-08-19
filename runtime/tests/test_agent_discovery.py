"""Tests for runtime/agent_discovery.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.agent_discovery import AgentDiscovery, DiscoveredAgent


class TestAgentDiscovery:
    def test_no_configs(self, tmp_path: Path):
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        assert d.discover() == []

    def test_detects_agents_md(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("# agents", encoding="utf-8")
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        agents = d.discover()
        assert any(a.kind == "generic" for a in agents)

    def test_detects_claude_settings(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            json.dumps({"mcpServers": {"aizee": {}}}), encoding="utf-8"
        )
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        agents = d.discover()
        claude = [a for a in agents if a.kind == "claude_code"]
        assert claude
        assert "aizee" in claude[0].mcp_servers

    def test_detects_cursor_rules_dir(self, tmp_path: Path):
        (tmp_path / ".cursor").mkdir()
        rules = tmp_path / ".cursor" / "rules"
        rules.mkdir()
        (rules / "a.mdc").write_text("rule", encoding="utf-8")
        (rules / "b.mdc").write_text("rule", encoding="utf-8")
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        agents = d.discover()
        cursor = [a for a in agents if a.kind == "cursor"]
        assert cursor
        assert cursor[0].metadata.get("file_count") == 2

    def test_dedup(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        agents = d.discover()
        # Same file found from both home and project_root — deduped.
        assert len([a for a in agents if a.kind == "generic"]) == 1

    def test_report_empty(self, tmp_path: Path):
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        assert "No AI agent" in d.report()

    def test_report_lists_agents(self, tmp_path: Path):
        (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        report = d.report()
        assert "AGENTS.md" in report
        assert "Discovered" in report

    def test_aider_yaml_model(self, tmp_path: Path):
        (tmp_path / ".aider.conf.yml").write_text("model: gpt-4\n", encoding="utf-8")
        d = AgentDiscovery(home=tmp_path, project_root=tmp_path)
        agents = d.discover()
        aider = [a for a in agents if a.kind == "aider"]
        assert aider
        assert aider[0].model == "gpt-4"
