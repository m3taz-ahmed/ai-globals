import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.code2video.code2video_plugin import Code2VideoPlugin
from plugins.code2video.entrypoint import _build_api_config


@pytest.fixture
def plugin(tmp_path: Path):
    kernel = MagicMock()
    kernel.root = tmp_path
    return Code2VideoPlugin(kernel, None)


def test_build_api_config_from_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_BASE_URL", "https://example.com/claude")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-claude")
    monkeypatch.setenv("ICONFINDER_API_KEY", "icon-key")

    config = _build_api_config()

    assert config["claude"]["base_url"] == "https://example.com/claude"
    assert config["claude"]["api_key"] == "sk-claude"
    assert config["iconfinder"]["api_key"] == "icon-key"


def test_register_mcp_tools(plugin):
    tools = plugin.register_mcp_tools()
    assert len(tools) == 3
    assert plugin.build_image in tools
    assert plugin.generate_video in tools
    assert plugin.list_videos in tools


def test_generate_video_missing_docker(plugin):
    with patch.object(shutil, "which", return_value=None):
        result = json.loads(plugin.generate_video("test topic"))

    assert result["ok"] is False
    assert "Docker executable not found" in result["error"]


def test_generate_video_builds_image_and_runs_container(plugin, tmp_path):
    output_dir = tmp_path / "state" / "code2video-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(cmd, **kwargs):
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        # Simulate container writing result.json after the run step
        if len(cmd) > 1 and cmd[1] == "run":
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "result.json").write_text(
                json.dumps({"ok": True, "video_path": "/manim/code2video/output/final.mp4"}),
                encoding="utf-8",
            )
            (output_dir / "final.mp4").write_bytes(b"fake video")

        return FakeResult()

    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=fake_run) as mock_run,
    ):
        result = json.loads(plugin.generate_video("Pythagorean theorem"))

    assert result.get("ok") is True, result
    assert result["host_video_path"] == str(output_dir / "final.mp4")
    assert mock_run.call_count == 1
    docker_call = mock_run.call_args_list[0][0][0]
    assert docker_call[0] == "/usr/bin/docker"
    assert docker_call[1] == "run"
    assert "code2video:latest" in docker_call


def test_list_videos(plugin, tmp_path):
    output_dir = tmp_path / "state" / "code2video-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "final.mp4").write_bytes(b"fake video")

    result = json.loads(plugin.list_videos())

    assert result["ok"] is True
    assert len(result["videos"]) == 1
    assert result["videos"][0]["name"] == "final.mp4"
