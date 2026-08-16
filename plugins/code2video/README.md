# Code2Video Plugin for AI Global OS

Sandboxed Code2Video integration. Generates educational Manim videos inside an isolated Docker container.

## Architecture

```text
AI Global OS (Windows)
  │
  │  generate_video(topic, ...)
  ▼
plugins/code2video/code2video_plugin.py
  │
  │  docker run --rm --read-only --cap-drop=ALL ...
  ▼
code2video:latest (Linux container on WSL2)
  │
  │  /app/entrypoint.py
  │  ──► api_config.json from env
  │  ──► python /app/src/agent.py --knowledge_point "..."
  ▼
output.mp4 on host volume
```

## Configuration

Enable in `plugins.yaml`:

```yaml
plugins:
  code2video:
    enabled: true
    permissions:
      - generate_video
      - build_image
```

Set API keys in the OS secret store or environment:

- `CODE2VIDEO_CLAUDE_API_KEY`
- `CODE2VIDEO_OPENAI_API_KEY`
- `CODE2VIDEO_GEMINI_API_KEY`
- `CODE2VIDEO_ICONFINDER_API_KEY`

## Build image

```powershell
docker build -t code2video:latest -f plugins/code2video/Dockerfile plugins/code2video
```

## Usage

```text
ai-os generate video --topic "Linear transformations and matrices"
```

## Files

- `__init__.py`: plugin gate (minimal import)
- `code2video_plugin.py`: OS plugin + MCP tool
- `Dockerfile`: container image with Manim + Code2Video
- `entrypoint.py`: container command wrapper
