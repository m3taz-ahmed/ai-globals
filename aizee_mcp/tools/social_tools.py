#!/usr/bin/env python3
"""Social media MCP tools: schedule, publish, draft, analytics, accounts, approve.

Implements a pluggable ``SocialProvider`` ABC (X / LinkedIn / Instagram /
YouTube / TikTok) inspired by Postiz's provider-interface pattern. A char-limit
normalizer trims/counts content per platform. Write tools (publish/schedule/
approve) are gated: they return JSON proxy instructions requiring human
approval; no external network call happens inline.
"""

from __future__ import annotations

import abc
import json
from enum import Enum
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore
from runtime import post_queue
from runtime.schemas import ValidationError

from .common import truncate, validate_query


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(error: str, **extra: Any) -> str:
    return _json({"ok": False, "error": error, **extra})


def _ok(**data: Any) -> str:
    return _json({"ok": True, **data})


class SocialNetwork(str, Enum):
    X = "x"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


# Per-network content limits (characters / caption length heuristics).
_CHAR_LIMITS: dict[str, int] = {
    SocialNetwork.X.value: 280,
    SocialNetwork.LINKEDIN.value: 3000,
    SocialNetwork.INSTAGRAM.value: 2200,
    SocialNetwork.YOUTUBE.value: 5000,
    SocialNetwork.TIKTOK.value: 2200,
}


def normalize_content(network: str, content: str) -> dict[str, Any]:
    """Normalize content for a network: enforce char limits, count length.

    Returns a dict with the (possibly trimmed) content, the original and final
    lengths, and whether truncation occurred.
    """
    key = (network or "").lower()
    if key not in _CHAR_LIMITS:
        raise ValidationError(
            f"Unknown social network '{network}'",
            context={"allowed": list(_CHAR_LIMITS)},
        )
    limit = _CHAR_LIMITS[key]
    trimmed = content[:limit]
    return {
        "network": key,
        "limit": limit,
        "original_length": len(content),
        "final_length": len(trimmed),
        "truncated": len(content) > limit,
        "content": trimmed,
    }


class SocialProvider(abc.ABC):
    """Pluggable social provider (concept). Builds a publish instruction."""

    network: SocialNetwork

    @abc.abstractmethod
    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class XProvider(SocialProvider):
    network = SocialNetwork.X

    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        norm = normalize_content(self.network.value, payload.get("content", ""))
        return {
            "network": self.network.value,
            "action": "tweet",
            "content": norm["content"],
            "truncated": norm["truncated"],
            "requires_oauth_env": "AIZEE_X_OAUTH",
        }


class LinkedInProvider(SocialProvider):
    network = SocialNetwork.LINKEDIN

    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        norm = normalize_content(self.network.value, payload.get("content", ""))
        return {
            "network": self.network.value,
            "action": "share",
            "content": norm["content"],
            "requires_oauth_env": "AIZEE_LINKEDIN_OAUTH",
        }


class InstagramProvider(SocialProvider):
    network = SocialNetwork.INSTAGRAM

    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        norm = normalize_content(self.network.value, payload.get("content", ""))
        return {
            "network": self.network.value,
            "action": "create_media",
            "caption": norm["content"],
            "requires_oauth_env": "AIZEE_INSTAGRAM_OAUTH",
        }


class YouTubeProvider(SocialProvider):
    network = SocialNetwork.YOUTUBE

    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "network": self.network.value,
            "action": "insert_video",
            "title": truncate(payload.get("title", ""), 100),
            "description": payload.get("content", ""),
            "requires_oauth_env": "AIZEE_YOUTUBE_OAUTH",
        }


class TikTokProvider(SocialProvider):
    network = SocialNetwork.TIKTOK

    def build_instruction(self, payload: dict[str, Any]) -> dict[str, Any]:
        norm = normalize_content(self.network.value, payload.get("content", ""))
        return {
            "network": self.network.value,
            "action": "post_video",
            "caption": norm["content"],
            "requires_oauth_env": "AIZEE_TIKTOK_OAUTH",
        }


_PROVIDERS: dict[str, type[SocialProvider]] = {
    SocialNetwork.X.value: XProvider,
    SocialNetwork.LINKEDIN.value: LinkedInProvider,
    SocialNetwork.INSTAGRAM.value: InstagramProvider,
    SocialNetwork.YOUTUBE.value: YouTubeProvider,
    SocialNetwork.TIKTOK.value: TikTokProvider,
}


def _resolve_provider(network: str) -> SocialProvider:
    key = (network or "").lower()
    if key not in _PROVIDERS:
        raise ValidationError(
            f"Unknown social network '{network}'",
            context={"allowed": list(_PROVIDERS)},
        )
    return _PROVIDERS[key]()


def register_social_tools(mcp: FastMCP) -> None:
    """Register social-media-related MCP tools."""

    @mcp.tool()
    def social_schedule(
        network: str,
        content: str,
        scheduled_at: str = "",
    ) -> str:
        """Schedule a post for later. WRITE/EXTERNAL — gated; returns proxy instruction (normalized content + schedule)."""
        if err := validate_query(content):
            return err
        try:
            provider = _resolve_provider(network)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        instruction = provider.build_instruction({"content": content})
        instruction["scheduled_at"] = scheduled_at
        instruction["action"] = "schedule"
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "instruction": instruction,
            "note": "Scheduled post requires guardian approval before execution.",
        })

    @mcp.tool()
    def social_publish(
        network: str,
        content: str,
    ) -> str:
        """Publish a post immediately. WRITE/EXTERNAL — gated; returns proxy instruction only (no inline network call)."""
        if err := validate_query(content):
            return err
        try:
            provider = _resolve_provider(network)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        instruction = provider.build_instruction({"content": content})
        return _json({
            "ok": True,
            "gated": True,
            "approval_required": True,
            "instruction": instruction,
            "note": "Publish requires human approval via guardian before the API call.",
        })

    @mcp.tool()
    def social_draft(
        network: str,
        topic: str,
        tone: str = "professional",
        length_hint: str = "short",
    ) -> str:
        """Draft platform-appropriate copy from a topic (pure generation guidance). Returns normalized draft text."""
        if err := validate_query(topic):
            return err
        try:
            provider = _resolve_provider(network)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        limit = _CHAR_LIMITS[provider.network.value]
        draft = f"[{tone}] {topic}: " + ("Add your key insight, CTA, and 2-3 hashtags here. " * max(1, limit // 80))[:limit]
        norm = normalize_content(provider.network.value, draft)
        return _ok(
            network=provider.network.value,
            tone=tone,
            length_hint=length_hint,
            draft=norm["content"],
            final_length=norm["final_length"],
            truncated=norm["truncated"],
        )

    @mcp.tool()
    def social_analytics(
        network: str,
        metric: str = "engagement",
        days: int = 30,
    ) -> str:
        """Fetch analytics (engagement/followers/impressions). READ/EXTERNAL — proxy instruction only."""
        try:
            provider = _resolve_provider(network)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        days = max(1, min(days, 365))
        return _json({
            "ok": True,
            "network": provider.network.value,
            "metric": metric,
            "days": days,
            "instruction": {
                "action": "analytics",
                "requires_oauth_env": f"AIZEE_{provider.network.value.upper()}_OAUTH",
                "query": {"metric": metric, "window": f"{days}d"},
            },
            "note": "Proxy instruction; fetch via approved executor.",
        })

    @mcp.tool()
    def social_accounts() -> str:
        """List connected social accounts (from configured providers). READ — returns configured networks."""
        return _ok(
            accounts=[
                {"network": n.value, "configured": False, "oauth_env": f"AIZEE_{n.value.upper()}_OAUTH"}
                for n in SocialNetwork
            ],
            note="Account linking requires OAuth credentials in env; none configured by default.",
        )

    @mcp.tool()
    def social_approve(
        instruction_id: str,
        approved: bool = False,
    ) -> str:
        """Explicit approval gate for a pending social instruction. WRITE — returns approval decision object (guardian-enforced)."""
        if not instruction_id:
            return _err("'instruction_id' is required")
        return _json({
            "ok": True,
            "gated": True,
            "instruction_id": instruction_id,
            "approved": approved,
            "decision": "approved" if approved else "rejected",
            "note": "Approval is recorded; execution proceeds only if approved AND guardian allows.",
        })

    @mcp.tool()
    def social_enqueue(
        network: str,
        content: str,
    ) -> str:
        """Enqueue a normalized post via runtime.post_queue. Pure computation (no network call).

        Enforces channel char limits and X free-post allowance. Returns the
        queued post metadata. Use social_publish to actually send.
        """
        if err := validate_query(content):
            return err
        try:
            provider = _resolve_provider(network)
        except ValidationError as exc:
            return _err(exc.message, context=exc.context)
        try:
            pq = post_queue.PostQueue(
                char_limits=dict(_CHAR_LIMITS),
            )
            queued = pq.enqueue(provider.network.value, content)
        except (ValidationError, TypeError, ValueError, AttributeError) as exc:
            return _err(exc.message if hasattr(exc, "message") else str(exc))
        return _ok(
            channel=queued.channel,
            text=queued.text,
            original_length=queued.original_length,
            note="Queued via runtime.post_queue. Use social_publish to send.",
        )
