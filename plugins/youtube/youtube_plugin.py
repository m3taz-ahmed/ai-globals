#!/usr/bin/env python3
"""YoutubePlugin for aiZee — proxies to external MCP server.

External MCP server: npx -y @youtube/mcp
Required env vars: YOUTUBE_API_KEY
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class YoutubePlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external youtube MCP server."""

    name = "youtube"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate required env vars on plugin load."""
        import os
        missing = [v for v in ("YOUTUBE_API_KEY",) if not os.environ.get(v)]
        if missing:
            import logging
            logging.getLogger(__name__).warning(
                "%s plugin loaded without %s — tool calls will fail until set",
                self.__class__.__name__, ", ".join(missing),
            )

    def _client(self) -> McpClient:
        return McpClient("youtube", self.kernel.root)

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": "YoutubePlugin MCP call failed: " + str(exc)})

    def youtube_list_videos(self, channel_id: str) -> str:
        """List channel videos."""
        return self._proxy("list_videos", {"channel_id": channel_id})

    def youtube_get_video(self, video_id: str) -> str:
        """Get video details."""
        return self._proxy("get_video", {"video_id": video_id})

    def youtube_upload_video(self, title: str, file_path: str, description: str = "") -> str:
        """Upload a video."""
        return self._proxy("upload_video", {"title": title, "file_path": file_path, "description": description})

    def youtube_get_analytics(self, video_id: str) -> str:
        """Get video analytics."""
        return self._proxy("get_analytics", {"video_id": video_id})

    def youtube_list_comments(self, video_id: str) -> str:
        """List video comments."""
        return self._proxy("list_comments", {"video_id": video_id})

    def youtube_get_channel(self, channel_id: str) -> str:
        """Get channel details."""
        return self._proxy("get_channel", {"channel_id": channel_id})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            self.youtube_list_videos,
            self.youtube_get_video,
            self.youtube_upload_video,
            self.youtube_get_analytics,
            self.youtube_list_comments,
            self.youtube_get_channel
        ]
