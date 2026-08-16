#!/usr/bin/env python3
"""Container entrypoint: generate api_config.json and run Code2Video."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

OUTPUT_DIR = Path("/manim/code2video/output")
SRC_DIR = Path("/manim/code2video/src")
API_CONFIG = SRC_DIR / "api_config.json"


def _env_or_default(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _build_api_config() -> dict[str, dict[str, str]]:
    """Build api_config.json from container environment variables."""
    return {
        "gemini": {
            "base_url": _env_or_default("GEMINI_BASE_URL"),
            "api_version": _env_or_default("GEMINI_API_VERSION", "2024-03-01-preview"),
            "api_key": _env_or_default("GEMINI_API_KEY"),
            "model": _env_or_default("GEMINI_MODEL", "gemini-2.5-pro-preview-05-06"),
        },
        "gpt41": {
            "base_url": _env_or_default("GPT41_BASE_URL"),
            "api_version": _env_or_default("GPT41_API_VERSION"),
            "api_key": _env_or_default("GPT41_API_KEY"),
            "model": _env_or_default("GPT41_MODEL", "gpt-4.1-2025-04-14"),
        },
        "gpt5": {
            "base_url": _env_or_default("GPT5_BASE_URL"),
            "api_version": _env_or_default("GPT5_API_VERSION"),
            "api_key": _env_or_default("GPT5_API_KEY"),
            "model": _env_or_default("GPT5_MODEL"),
        },
        "gpto4mini": {
            "base_url": _env_or_default("GPTO4MINI_BASE_URL"),
            "api_version": _env_or_default("GPTO4MINI_API_VERSION"),
            "api_key": _env_or_default("GPTO4MINI_API_KEY"),
            "model": _env_or_default("GPTO4MINI_MODEL", "o4-mini-2025-04-16"),
        },
        "gpt4o": {
            "base_url": _env_or_default("GPT4O_BASE_URL"),
            "api_version": _env_or_default("GPT4O_API_VERSION"),
            "api_key": _env_or_default("GPT4O_API_KEY"),
            "model": _env_or_default("GPT4O_MODEL", "gpt-4o-2024-11-20"),
        },
        "claude": {
            "base_url": _env_or_default("CLAUDE_BASE_URL"),
            "api_key": _env_or_default("CLAUDE_API_KEY"),
        },
        "iconfinder": {
            "api_key": _env_or_default("ICONFINDER_API_KEY"),
        },
    }


def _write_api_config() -> None:
    API_CONFIG.write_text(json.dumps(_build_api_config(), indent=2), encoding="utf-8")


def _find_video(folder: Path) -> Path | None:
    """Locate the final merged video under the generated CASES folder."""
    for path in sorted(folder.rglob("*.mp4")):
        return path
    return None


def _run_agent(topic: str, provider: str, use_feedback: bool, use_assets: bool) -> Path | None:
    """Invoke Code2Video agent.py for a single topic."""
    _write_api_config()

    cmd = [
        sys.executable,
        "agent.py",
        "--API",
        provider,
        "--folder_prefix",
        "AIOS",
        "--knowledge_point",
        topic,
        "--max_code_token_length",
        "10000",
        "--max_fix_bug_tries",
        "10",
        "--max_regenerate_tries",
        "10",
        "--max_feedback_gen_code_tries",
        "3",
        "--max_mllm_fix_bugs_tries",
        "3",
        "--feedback_rounds",
        "2",
    ]
    if use_feedback:
        cmd.append("--use_feedback")
    if use_assets:
        cmd.append("--use_assets")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    print(f"[Code2Video] Starting generation for topic: {topic}", flush=True)
    start = time.time()
    result = subprocess.run(
        cmd,
        cwd=SRC_DIR,
        env=env,
        text=True,
        capture_output=False,
    )
    elapsed = time.time() - start
    print(f"[Code2Video] agent.py finished in {elapsed:.1f}s with exit {result.returncode}", flush=True)

    if result.returncode != 0:
        return None

    cases_dir = SRC_DIR / "CASES"
    video_path = _find_video(cases_dir)
    return video_path


def _copy_output(video_path: Path | None) -> dict[str, object]:
    """Copy the generated video to the host-mounted output directory."""
    if video_path is None or not video_path.exists():
        return {"ok": False, "error": "No video was produced. Check container logs."}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT_DIR / "final.mp4"
    shutil.copy2(video_path, destination)
    return {
        "ok": True,
        "video_path": "/manim/code2video/output/final.mp4",
        "host_video_path": "final.mp4",
        "size_bytes": destination.stat().st_size,
    }


def main() -> int:
    topic = _env_or_default("C2V_TOPIC")
    provider = _env_or_default("C2V_PROVIDER", "claude")
    use_feedback = _env_or_default("C2V_USE_FEEDBACK", "1") in ("1", "true", "True", "yes")
    use_assets = _env_or_default("C2V_USE_ASSETS", "1") in ("1", "true", "True", "yes")

    if not topic:
        result = {"ok": False, "error": "C2V_TOPIC environment variable is required"}
    else:
        video_path = _run_agent(topic, provider, use_feedback, use_assets)
        result = _copy_output(video_path)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "result.json").write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
