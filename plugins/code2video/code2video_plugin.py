#!/usr/bin/env python3
"""AI Global OS plugin that drives Code2Video inside a sandboxed Docker container."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from runtime.plugin import AIOSPlugin

_IMAGE_TAG = "code2video:latest"
_CONTAINER_OUTPUT = "/manim/code2video/output"


class Code2VideoPlugin(AIOSPlugin):
    """Generate educational Manim videos via a sandboxed Code2Video container."""

    name = "code2video"
    version = "0.1.0"

    def on_load(self) -> None:
        """No runtime state needed at load time."""

    def _output_dir(self) -> Path:
        """Return the host directory where container output is collected."""
        return self.kernel.root / "state" / "code2video-output"

    def _plugin_dir(self) -> Path:
        return self.kernel.root / "plugins" / "code2video"

    def _docker_path(self) -> str:
        """Return the docker executable or an empty string if missing."""
        docker = shutil.which("docker")
        return docker or ""

    def _image_exists(self) -> bool:
        docker = self._docker_path()
        if not docker:
            return False
        result = subprocess.run(
            [docker, "images", "-q", _IMAGE_TAG],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())

    def build_image(self) -> str:
        """Build the Code2Video Docker image from the bundled Dockerfile."""
        docker = self._docker_path()
        if not docker:
            return json.dumps({"ok": False, "error": "Docker executable not found on PATH"})

        dockerfile = self._plugin_dir() / "Dockerfile"
        if not dockerfile.exists():
            return json.dumps({"ok": False, "error": f"Dockerfile not found at {dockerfile}"})

        try:
            result = subprocess.run(
                [docker, "build", "-t", _IMAGE_TAG, "-f", str(dockerfile), str(self._plugin_dir())],
                capture_output=True,
                text=True,
                check=False,
                timeout=1800,
            )
            if result.returncode != 0:
                return json.dumps({"ok": False, "error": result.stderr or "docker build failed"})
            return json.dumps({"ok": True, "image": _IMAGE_TAG, "message": "Image built successfully"})
        except subprocess.TimeoutExpired:
            return json.dumps({"ok": False, "error": "docker build timed out after 30 minutes"})
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"docker build error: {exc!s}"})

    def _ensure_image(self) -> tuple[bool, str]:
        if self._image_exists():
            return True, ""
        build = self.build_image()
        data = json.loads(build)
        if not data.get("ok"):
            return False, data.get("error", "unknown build error")
        return True, ""

    def _env_for_provider(self, provider: str) -> dict[str, str]:
        """Map provider to the environment variables the upstream code expects."""
        env: dict[str, str] = {}
        prefix = provider.upper().replace("-", "_")
        for key, value in os.environ.items():
            if key.startswith(f"CODE2VIDEO_{prefix}_") or key.startswith("CODE2VIDEO_"):
                # Strip CODE2VIDEO_ prefix and pass through
                stripped = key.removeprefix("CODE2VIDEO_")
                env[stripped] = value

        # Common keys expected by the container
        common_map = {
            "claude": ["CLAUDE_BASE_URL", "CLAUDE_API_KEY"],
            "gpt-41": ["GPT41_BASE_URL", "GPT41_API_VERSION", "GPT41_API_KEY", "GPT41_MODEL"],
            "gpt-5": ["GPT5_BASE_URL", "GPT5_API_VERSION", "GPT5_API_KEY", "GPT5_MODEL"],
            "gpt-4o": ["GPT4O_BASE_URL", "GPT4O_API_VERSION", "GPT4O_API_KEY", "GPT4O_MODEL"],
            "gpt-o4mini": ["GPTO4MINI_BASE_URL", "GPTO4MINI_API_VERSION", "GPTO4MINI_API_KEY", "GPTO4MINI_MODEL"],
            "Gemini": ["GEMINI_BASE_URL", "GEMINI_API_VERSION", "GEMINI_API_KEY", "GEMINI_MODEL"],
        }
        for key in common_map.get(provider, []):
            os_key = f"CODE2VIDEO_{key}"
            if os_key in os.environ and key not in env:
                env[key] = os.environ[os_key]

        if "ICONFINDER_API_KEY" in os.environ:
            env["ICONFINDER_API_KEY"] = os.environ["ICONFINDER_API_KEY"]

        return env

    def generate_video(
        self,
        topic: str,
        provider: str = "claude",
        use_feedback: bool = True,
        use_assets: bool = False,
        timeout: int = 1800,
    ) -> str:
        """Generate an educational video for the given topic inside the sandbox."""
        ok, error = self._ensure_image()
        if not ok:
            return json.dumps({"ok": False, "error": f"Image not available: {error}"})

        docker = self._docker_path()
        if not docker:
            return json.dumps({"ok": False, "error": "Docker executable not found on PATH"})

        output_dir = self._output_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Empty output dir for this run
        for item in output_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        env = self._env_for_provider(provider)
        env["C2V_TOPIC"] = topic
        env["C2V_PROVIDER"] = provider
        env["C2V_USE_FEEDBACK"] = "1" if use_feedback else "0"
        env["C2V_USE_ASSETS"] = "1" if use_assets else "0"

        cmd = [
            docker,
            "run",
            "--rm",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges:true",
            "-v",
            f"{output_dir}:{_CONTAINER_OUTPUT}",
            "-e",
            f"C2V_TOPIC={topic}",
            "-e",
            f"C2V_PROVIDER={provider}",
            "-e",
            f"C2V_USE_FEEDBACK={env['C2V_USE_FEEDBACK']}",
            "-e",
            f"C2V_USE_ASSETS={env['C2V_USE_ASSETS']}",
        ]

        for key, value in env.items():
            if key in {"C2V_TOPIC", "C2V_PROVIDER", "C2V_USE_FEEDBACK", "C2V_USE_ASSETS"}:
                continue
            if value:
                cmd.extend(["-e", f"{key}={value}"])

        cmd.append(_IMAGE_TAG)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
            result_file = output_dir / "result.json"
            if result_file.exists():
                data = json.loads(result_file.read_text(encoding="utf-8"))
                if data.get("ok"):
                    data["host_output_dir"] = str(output_dir)
                    # Windows host path for the user
                    data["host_video_path"] = str(output_dir / "final.mp4")
                return json.dumps(data)

            return json.dumps(
                {
                    "ok": False,
                    "error": "No result.json produced",
                    "stdout": result.stdout[-4000:],
                    "stderr": result.stderr[-4000:],
                }
            )
        except subprocess.TimeoutExpired:
            return json.dumps({"ok": False, "error": f"Container timed out after {timeout}s"})
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"Container execution failed: {exc!s}"})

    def list_videos(self) -> str:
        """Return a list of videos currently in the output directory."""
        output_dir = self._output_dir()
        if not output_dir.exists():
            return json.dumps({"ok": True, "videos": []})
        videos = [
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(output_dir.iterdir())
            if path.is_file()
        ]
        return json.dumps({"ok": True, "videos": videos})

    def register_mcp_tools(self) -> list[Any]:
        return [
            self.build_image,
            self.generate_video,
            self.list_videos,
        ]
