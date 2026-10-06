import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from plugins.code2video import entrypoint
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


# ---------------------------------------------------------------------------
# Coverage restoration — paths lost when the file was never fully exercised
# ---------------------------------------------------------------------------


def test_plugin_dir(plugin, tmp_path):
    assert plugin._plugin_dir() == tmp_path / "plugins" / "code2video"


def test_image_exists_true_and_false(plugin):
    ok_result = MagicMock(stdout="abc123\n")
    empty_result = MagicMock(stdout="")
    with (
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=[ok_result, empty_result]) as mock_run,
    ):
        assert plugin._image_exists() is True
        assert plugin._image_exists() is False
    assert mock_run.call_args_list[0][0][0][:2] == ["/usr/bin/docker", "images"]


def test_build_image_no_dockerfile(plugin):
    with patch.object(shutil, "which", return_value="/usr/bin/docker"):
        result = json.loads(plugin.build_image())
    assert result["ok"] is False
    assert "Dockerfile not found" in result["error"]


def test_build_image_success_and_failure(plugin, tmp_path):
    plug_dir = tmp_path / "plugins" / "code2video"
    plug_dir.mkdir(parents=True)
    (plug_dir / "Dockerfile").write_text("FROM scratch", encoding="utf-8")

    good = MagicMock(returncode=0, stderr="")
    bad = MagicMock(returncode=1, stderr="build broke")
    with (
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=[good, bad]),
    ):
        assert json.loads(plugin.build_image())["ok"] is True
        fail = json.loads(plugin.build_image())
        assert fail["ok"] is False and "build broke" in fail["error"]


def test_build_image_timeout_and_exception(plugin, tmp_path):
    plug_dir = tmp_path / "plugins" / "code2video"
    plug_dir.mkdir(parents=True)
    (plug_dir / "Dockerfile").write_text("FROM scratch", encoding="utf-8")
    with (
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("docker", 1)),
    ):
        assert "timed out" in json.loads(plugin.build_image())["error"]
    with (
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=OSError("spawn fail")),
    ):
        assert "docker build error" in json.loads(plugin.build_image())["error"]


def test_ensure_image_builds_when_missing(plugin):
    with (
        patch.object(plugin, "_image_exists", return_value=False),
        patch.object(plugin, "build_image", return_value=json.dumps({"ok": True})) as mock_build,
    ):
        ok, err = plugin._ensure_image()
    assert ok and err == ""
    mock_build.assert_called_once()


def test_env_for_provider_passthrough(plugin, monkeypatch):
    monkeypatch.setenv("CODE2VIDEO_CLAUDE_API_KEY", "sk-x")
    monkeypatch.setenv("CODE2VIDEO_GEMINI_MODEL", "gem-1")
    monkeypatch.setenv("ICONFINDER_API_KEY", "icon")
    env = plugin._env_for_provider("claude")
    assert env["CLAUDE_API_KEY"] == "sk-x"
    assert env["GEMINI_MODEL"] == "gem-1"
    assert env["ICONFINDER_API_KEY"] == "icon"


def test_generate_video_no_result_json(plugin, tmp_path):
    def fake_run(cmd, **kwargs):
        return MagicMock(returncode=0, stdout="logs", stderr="errs")

    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=fake_run),
    ):
        result = json.loads(plugin.generate_video("topic"))
    assert result["ok"] is False
    assert "No result.json produced" in result["error"]
    assert result["stdout"] == "logs" and result["stderr"] == "errs"


def test_generate_video_result_not_ok(plugin, tmp_path):
    output_dir = tmp_path / "state" / "code2video-output"

    def fake_run(cmd, **kwargs):
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "result.json").write_text(
            json.dumps({"ok": False, "error": "agent failed"}), encoding="utf-8"
        )
        return MagicMock(returncode=1, stdout="", stderr="")

    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=fake_run),
    ):
        result = json.loads(plugin.generate_video("topic"))
    assert result["ok"] is False
    assert result["error"] == "agent failed"
    assert "host_video_path" not in result


def test_generate_video_cleans_output_dir(plugin, tmp_path):
    output_dir = tmp_path / "state" / "code2video-output"
    stale_sub = output_dir / "stale_dir"
    stale_sub.mkdir(parents=True)
    (stale_sub / "inner.txt").write_text("x", encoding="utf-8")
    (output_dir / "stale.mp4").write_bytes(b"old")

    def fake_run(cmd, **kwargs):
        (output_dir / "result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        return MagicMock(returncode=0, stdout="", stderr="")

    env = {"CODE2VIDEO_CLAUDE_API_KEY": "sk-extra"}
    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=fake_run) as mock_run,
        patch.dict("os.environ", env, clear=False),
    ):
        result = json.loads(plugin.generate_video("topic"))

    assert result["ok"] is True
    assert not stale_sub.exists() and not (output_dir / "stale.mp4").exists()
    docker_call = mock_run.call_args_list[0][0][0]
    joined = " ".join(docker_call)
    assert "CLAUDE_API_KEY=sk-extra" in joined


def test_generate_video_timeout_and_exception(plugin):
    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("docker", 5)),
    ):
        assert "timed out" in json.loads(plugin.generate_video("t"))["error"]
    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=OSError("spawn")),
    ):
        assert "Container execution failed" in json.loads(plugin.generate_video("t"))["error"]


def test_generate_video_docker_missing_after_image_ok(plugin):
    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value=None),
    ):
        result = json.loads(plugin.generate_video("topic"))
    assert result["ok"] is False
    assert "Docker executable not found" in result["error"]


def test_list_videos_empty_dir(plugin):
    result = json.loads(plugin.list_videos())
    assert result == {"ok": True, "videos": []}


# ---------------------------------------------------------------------------
# entrypoint.py — container-side logic, exercised via monkeypatched paths
# ---------------------------------------------------------------------------


def test_write_api_config(tmp_path, monkeypatch):
    cfg = tmp_path / "api_config.json"
    monkeypatch.setattr(entrypoint, "API_CONFIG", cfg)
    entrypoint._write_api_config()
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert "claude" in data and "gemini" in data


def test_find_video(tmp_path):
    assert entrypoint._find_video(tmp_path) is None
    nested = tmp_path / "CASES" / "x" / "out.mp4"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"v")
    assert entrypoint._find_video(tmp_path) == nested


def test_run_agent_success_and_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(entrypoint, "SRC_DIR", tmp_path)
    monkeypatch.setattr(entrypoint, "API_CONFIG", tmp_path / "api_config.json")
    cases = tmp_path / "CASES" / "job"
    cases.mkdir(parents=True)
    video = cases / "final.mp4"
    video.write_bytes(b"v")

    good = MagicMock(returncode=0)
    bad = MagicMock(returncode=1)
    with patch.object(entrypoint.subprocess, "run", side_effect=[good, bad]) as mock_run:
        assert entrypoint._run_agent("topic", "claude", True, True) == video
        assert entrypoint._run_agent("topic", "claude", False, False) is None
    cmd_ok = mock_run.call_args_list[0][0][0]
    assert "--use_feedback" in cmd_ok and "--use_assets" in cmd_ok
    cmd_no_flags = mock_run.call_args_list[1][0][0]
    assert "--use_feedback" not in cmd_no_flags


def test_copy_output(tmp_path, monkeypatch):
    monkeypatch.setattr(entrypoint, "OUTPUT_DIR", tmp_path / "out")
    assert entrypoint._copy_output(None)["ok"] is False
    missing = tmp_path / "gone.mp4"
    assert entrypoint._copy_output(missing)["ok"] is False
    src = tmp_path / "src.mp4"
    src.write_bytes(b"video-bytes")
    result = entrypoint._copy_output(src)
    assert result["ok"] is True
    assert result["size_bytes"] == len(b"video-bytes")
    assert (tmp_path / "out" / "final.mp4").exists()


def test_entrypoint_main_no_topic(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(entrypoint, "OUTPUT_DIR", tmp_path / "out")
    monkeypatch.delenv("C2V_TOPIC", raising=False)
    rc = entrypoint.main()
    assert rc == 1
    assert json.loads((tmp_path / "out" / "result.json").read_text())["ok"] is False


def test_entrypoint_main_success(tmp_path, monkeypatch):
    monkeypatch.setattr(entrypoint, "OUTPUT_DIR", tmp_path / "out")
    monkeypatch.setenv("C2V_TOPIC", "gravity")
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    with patch.object(entrypoint, "_run_agent", return_value=video):
        assert entrypoint.main() == 0
    result = json.loads((tmp_path / "out" / "result.json").read_text())
    assert result["ok"] is True


def test_generate_video_env_skip_and_empty_value(plugin, tmp_path, monkeypatch):
    """Cover: item neither file nor dir during cleanup, and empty env value
    skipped in the -e passthrough loop."""
    output_dir = tmp_path / "state" / "code2video-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    ghost = MagicMock()
    ghost.is_file.return_value = False
    ghost.is_dir.return_value = False
    stale = output_dir / "stale.txt"
    stale.write_text("x", encoding="utf-8")

    real_iterdir = type(output_dir).iterdir

    def fake_iterdir(self):
        if self == output_dir:
            return iter([stale, ghost])
        return real_iterdir(self)

    def fake_run(cmd, **kwargs):
        (output_dir / "result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setenv("CODE2VIDEO_EMPTY_KEY", "")
    monkeypatch.setattr(type(output_dir), "iterdir", fake_iterdir)
    with (
        patch.object(plugin, "_image_exists", return_value=True),
        patch.object(shutil, "which", return_value="/usr/bin/docker"),
        patch.object(subprocess, "run", side_effect=fake_run) as mock_run,
    ):
        result = json.loads(plugin.generate_video("topic"))

    assert result["ok"] is True
    joined = " ".join(mock_run.call_args_list[0][0][0])
    assert "EMPTY_KEY" not in joined
