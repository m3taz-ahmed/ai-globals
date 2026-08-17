#!/usr/bin/env python3
"""LinkedIn plugin for aiZee — proxies to octopus-linkedin MCP server.

Requires an authenticated LinkedIn session. Run ``octopus-linkedin authorize``
once to cache an access token (valid ~60 days). The token is stored locally in
``site-packages/token.json`` and is **never** committed to the repository.

Governed workflow: draft → review → approve → publish → analyze.
Direct publish tools are available but the draft workflow is preferred.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from runtime.mcp_client import McpClient
from runtime.plugin import AIOSPlugin


class LinkedInPlugin(AIOSPlugin):
    """Bridge AIOS kernel to the external octopus-linkedin MCP server.

    Implements the governed content workflow:
        draft → review → approve → publish → comment → analyze

    All drafting/approval is local-only. ``publish_draft`` is the single gate
    that sends content to LinkedIn, and it refuses to publish unapproved drafts.
    """

    name = "linkedin"
    version = "0.1.0"

    def on_load(self) -> None:
        """Validate that the LinkedIn token is available; warn if missing."""
        import warnings

        token_path = os.environ.get("LINKEDIN_MCP_TOKEN_PATH", "")
        has_env_token = bool(os.environ.get("LINKEDIN_ACCESS_TOKEN"))
        if not token_path and not has_env_token:
            warnings.warn(
                "LinkedIn plugin enabled but no access token found. "
                "Run `octopus-linkedin authorize` to authenticate. "
                "Tool calls will fail until the token is set.",
                stacklevel=2,
            )

    def _client(self) -> McpClient:
        return McpClient("linkedin", self.kernel.root)

    # ------------------------------------------------------------------
    # Profile (read-only)
    # ------------------------------------------------------------------

    def linkedin_get_profile(self) -> str:
        """Get the authenticated user's LinkedIn profile (name, headline, email)."""
        return self._proxy("get_profile", {})

    # ------------------------------------------------------------------
    # Direct posting (use draft workflow instead for governance)
    # ------------------------------------------------------------------

    def linkedin_create_post(self, text: str, visibility: str = "PUBLIC") -> str:
        """Publish a text post directly to LinkedIn. Use draft workflow for governance."""
        return self._proxy("create_post", {"text": text, "visibility": visibility})

    def linkedin_share_link(self, text: str, url: str) -> str:
        """Publish a post with a URL preview card."""
        return self._proxy("share_link", {"text": text, "url": url})

    def linkedin_share_image(self, text: str, image_path: str) -> str:
        """Publish a post with one local image."""
        return self._proxy("share_image", {"text": text, "image_path": image_path})

    def linkedin_delete_post(self, post_urn: str) -> str:
        """Delete a post by its URN."""
        return self._proxy("delete_post", {"post_urn": post_urn})

    # ------------------------------------------------------------------
    # Draft workflow (governed: draft → approve → publish)
    # ------------------------------------------------------------------

    def linkedin_create_draft(self, text: str, kind: str = "text") -> str:
        """Save a draft locally (never touches LinkedIn). Kind: text|link|image."""
        return self._proxy("create_draft", {"text": text, "kind": kind})

    def linkedin_list_drafts(self, status: str = "") -> str:
        """List drafts, optionally filtered by status: draft|approved|scheduled|published."""
        args: dict[str, Any] = {}
        if status:
            args["status"] = status
        return self._proxy("list_drafts", args)

    def linkedin_get_draft(self, draft_id: str) -> str:
        """Read a single draft by ID."""
        return self._proxy("get_draft", {"draft_id": draft_id})

    def linkedin_update_draft(self, draft_id: str, text: str) -> str:
        """Edit a draft. Resets approval status."""
        return self._proxy("update_draft", {"draft_id": draft_id, "text": text})

    def linkedin_approve_draft(self, draft_id: str, note: str = "") -> str:
        """Approve a draft — the review gate before publishing."""
        args: dict[str, Any] = {"draft_id": draft_id}
        if note:
            args["note"] = note
        return self._proxy("approve_draft", args)

    def linkedin_delete_draft(self, draft_id: str) -> str:
        """Delete a draft locally."""
        return self._proxy("delete_draft", {"draft_id": draft_id})

    def linkedin_schedule_draft(self, draft_id: str, publish_at: str) -> str:
        """Schedule an approved draft for later publishing. ISO 8601 datetime."""
        return self._proxy("schedule_draft", {"draft_id": draft_id, "publish_at": publish_at})

    def linkedin_unschedule_draft(self, draft_id: str) -> str:
        """Clear a draft's scheduled time."""
        return self._proxy("unschedule_draft", {"draft_id": draft_id})

    def linkedin_publish_draft(self, draft_id: str) -> str:
        """Publish an approved draft to LinkedIn now. Refuses unapproved drafts."""
        return self._proxy("publish_draft", {"draft_id": draft_id})

    def linkedin_publish_due(self) -> str:
        """Publish all approved drafts whose scheduled time has arrived."""
        return self._proxy("publish_due", {})

    # ------------------------------------------------------------------
    # Comments & engagement
    # ------------------------------------------------------------------

    def linkedin_list_comments(self, post_urn: str) -> str:
        """List comments on a post you control."""
        return self._proxy("list_comments", {"post_urn": post_urn})

    def linkedin_reply_comment(self, post_urn: str, comment: str) -> str:
        """Reply to a comment on a post you control."""
        return self._proxy("reply_comment", {"post_urn": post_urn, "comment": comment})

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def linkedin_get_post_stats(self, post_urn: str) -> str:
        """Get likes and comments count for a post."""
        return self._proxy("get_post_stats", {"post_urn": post_urn})

    # ------------------------------------------------------------------
    # Internal proxy
    # ------------------------------------------------------------------

    def _proxy(self, tool: str, arguments: dict[str, Any]) -> str:
        """Call a tool on the external LinkedIn MCP server via stdio."""
        try:
            result = self._client().call_tool(tool, arguments)
            return result if isinstance(result, str) else json.dumps(result, default=str)
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"LinkedIn MCP call failed: {exc!s}"})

    def register_mcp_tools(self) -> list[Callable[..., str]]:
        return [
            # Profile
            self.linkedin_get_profile,
            # Direct posting
            self.linkedin_create_post,
            self.linkedin_share_link,
            self.linkedin_share_image,
            self.linkedin_delete_post,
            # Draft workflow (governed)
            self.linkedin_create_draft,
            self.linkedin_list_drafts,
            self.linkedin_get_draft,
            self.linkedin_update_draft,
            self.linkedin_approve_draft,
            self.linkedin_delete_draft,
            self.linkedin_schedule_draft,
            self.linkedin_unschedule_draft,
            self.linkedin_publish_draft,
            self.linkedin_publish_due,
            # Comments & engagement
            self.linkedin_list_comments,
            self.linkedin_reply_comment,
            # Analytics
            self.linkedin_get_post_stats,
        ]
