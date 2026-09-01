#!/usr/bin/env python3
"""aiZee dashboard server."""

from __future__ import annotations

import contextlib
import hmac
import ipaddress
import json
import logging
import mimetypes
import os
import signal
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar, cast

# Allow direct execution (`python dashboard/server.py`) from any CWD:
# Python puts the script's directory on sys.path, not the project root,
# so bootstrap it before importing project modules.
if __package__ in (None, ""):
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

import config
from memory.store import MemoryStore
from runtime.astryx import AstryxLinter
from runtime.kernel import Kernel
from runtime.metrics import format_metrics
from runtime.settings import SECTIONS as SETTINGS_SECTIONS
from runtime.settings import SettingsManager, get_settings_manager, reload_settings_manager
from runtime.telemetry import system_metrics

logger = logging.getLogger(__name__)

# The dashboard UI MUST be the one shipped next to this server code. Serving
# assets from a discovered root (which may point to another install/version)
# pairs NEW security policy with OLD markup (or vice versa) and silently
# breaks the UI. Tests may override _ASSET_DIR_OVERRIDE.
_CODE_DIR = Path(__file__).resolve().parent
_ASSET_DIR_OVERRIDE: Path | None = None


def _asset_dir() -> Path:
    return _ASSET_DIR_OVERRIDE or _CODE_DIR

def _env_first(*names: str, default: str = "") -> str:
    """Return first set env var among names, or default."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v
    return default

_MAX_BODY_SIZE = int(_env_first("AIZEE_DASHBOARD_MAX_BODY_SIZE", "AGENT_OS_DASHBOARD_MAX_BODY_SIZE", default="1048576"))
_ALLOWED_ORIGINS = {o.strip() for o in _env_first("AIZEE_DASHBOARD_ORIGINS", "AGENT_OS_DASHBOARD_ORIGINS", default="http://127.0.0.1:8080,http://localhost:8080").split(",") if o.strip()}
_TRUSTED_PROXIES = {ip.strip() for ip in _env_first("AIZEE_DASHBOARD_TRUSTED_PROXIES", "AGENT_OS_DASHBOARD_TRUSTED_PROXIES", default="").split(",") if ip.strip()}

# Shared instances so state (budget, audit, chat) is consistent across requests.
_kernel_cache: tuple[Path, Kernel] | None = None
_memory_cache: tuple[Path, MemoryStore] | None = None
_cache_lock = threading.Lock()

# Simple per-IP fixed-window rate limiter.
# Clamp to >=1 so a misconfigured env var (0 or negative) cannot disable rate limiting.
_rate_limit = max(1, int(_env_first("AIZEE_DASHBOARD_RATE_LIMIT", "AGENT_OS_DASHBOARD_RATE_LIMIT", default="120")))
_rate_window = max(1.0, float(_env_first("AIZEE_DASHBOARD_RATE_WINDOW", "AGENT_OS_DASHBOARD_RATE_WINDOW", default="60")))
_rate_state: dict[str, tuple[int, float]] = {}
_rate_lock = threading.Lock()
# Max number of tracked IPs; oldest entries evicted when exceeded. Clamp to >=1.
_rate_max_entries = max(1, int(_env_first("AIZEE_DASHBOARD_RATE_MAX_ENTRIES", "AGENT_OS_DASHBOARD_RATE_MAX_ENTRIES", default="10000")))


def _kernel_instance() -> Kernel:
    global _kernel_cache
    root = config.discover_root()
    project_root = config.discover_project_root()
    with _cache_lock:
        if _kernel_cache is None or _kernel_cache[0] != root:
            _kernel_cache = (root, Kernel(root, project_root))
        return _kernel_cache[1]


def _memory_instance() -> MemoryStore:
    global _memory_cache
    project_root = config.discover_project_root()
    with _cache_lock:
        if _memory_cache is None or _memory_cache[0] != project_root:
            _memory_cache = (project_root, MemoryStore(project_root))
        return _memory_cache[1]


def _settings_instance() -> SettingsManager:
    """Return the shared, process-wide SettingsManager for the OS root.

    Uses ``get_settings_manager`` so the dashboard, kernel, McpClient, and
    PluginManager all share one instance — a toggle + restart is immediately
    visible to every MCP gate.
    """
    root = config.discover_root()
    return get_settings_manager(root)


def _sync_ide_mcp_configs(root: Path, mcp_settings: dict[str, Any]) -> None:
    """Sync MCP server toggles to ALL IDE MCP config files.

    When a user disables an MCP server in the dashboard, we update every IDE
    config source so the server is not loaded on next restart — regardless of
    which IDE (Devin, Claude Code, Windsurf, Cursor) is used.

    Supported config files:
    - ``.devin/mcp_config.local.json`` — Devin overlay (uses ``"disabled": true``)
    - ``.claude/settings.json`` — Claude Code (remove disabled server entries)

    Re-enabling a server restores it in Claude Code (from the canonical
    ``aizee_mcp/config.json``) and removes the disabled flag in Devin.
    """
    # --- 1. Devin: .devin/mcp_config.local.json (disabled flag overlay) ---
    _sync_devin_mcp_local(root, mcp_settings)

    # --- 2. Claude Code: .claude/settings.json (remove/add server entries) ---
    _sync_claude_mcp_settings(root, mcp_settings)


def _sync_devin_mcp_local(root: Path, mcp_settings: dict[str, Any]) -> None:
    """Update .devin/mcp_config.local.json with disabled flags."""
    local_path = root / ".devin" / "mcp_config.local.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    local: dict[str, Any] = {"mcpServers": {}}
    if local_path.exists():
        try:
            local = json.loads(local_path.read_text(encoding="utf-8"))
            if "mcpServers" not in local or not isinstance(local["mcpServers"], dict):
                local["mcpServers"] = {}
        except (ValueError, OSError):
            local = {"mcpServers": {}}

    servers = local["mcpServers"]
    for server_name, cfg in mcp_settings.items():
        if not isinstance(cfg, dict):
            continue
        enabled = cfg.get("enabled", True)
        existing = servers.get(server_name, {})
        if not isinstance(existing, dict):
            existing = {}
        if enabled:
            existing.pop("disabled", None)
        else:
            existing["disabled"] = True
        if existing:
            servers[server_name] = existing
        elif server_name in servers and not servers[server_name]:
            servers.pop(server_name, None)

    local_path.write_text(json.dumps(local, indent=2), encoding="utf-8")


def _sync_claude_mcp_settings(root: Path, mcp_settings: dict[str, Any]) -> None:
    """Update .claude/settings.json — remove disabled servers, restore enabled.

    Claude Code has no ``disabled`` flag; the only way to prevent loading is
    to remove the server entry entirely. To restore a re-enabled server, we
    read the canonical config from ``aizee_mcp/config.json`` AND
    ``.devin/mcp_config.json`` so servers defined in either source can be
    restored.
    """
    claude_path = root / ".claude" / "settings.json"
    if not claude_path.exists():
        return  # No Claude Code config to update

    # Read current Claude settings
    try:
        claude_cfg = json.loads(claude_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return
    if "mcpServers" not in claude_cfg or not isinstance(claude_cfg["mcpServers"], dict):
        return

    # Read canonical MCP config (source of truth for server definitions).
    # Check both aizee_mcp/config.json AND .devin/mcp_config.json so servers
    # that only exist in the Devin config (e.g. upwork, freelancer) can be
    # restored when re-enabled.
    canonical: dict[str, Any] = {}
    for cfg_path in [root / "aizee_mcp" / "config.json", root / ".devin" / "mcp_config.json"]:
        if not cfg_path.exists():
            continue
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            for name, defn in raw.get("mcpServers", {}).items():
                if name not in canonical:
                    canonical[name] = defn
        except (ValueError, OSError):
            pass

    changed = False
    for server_name, cfg in mcp_settings.items():
        if not isinstance(cfg, dict):
            continue
        enabled = cfg.get("enabled", True)
        if enabled:
            # Restore: if server is missing from Claude config but exists in
            # canonical, add it back.
            if server_name not in claude_cfg["mcpServers"] and server_name in canonical:
                claude_cfg["mcpServers"][server_name] = canonical[server_name]
                changed = True
        else:
            # Disable: remove from Claude config entirely
            if server_name in claude_cfg["mcpServers"]:
                del claude_cfg["mcpServers"][server_name]
                changed = True

    if changed:
        claude_path.write_text(json.dumps(claude_cfg, indent=2), encoding="utf-8")


def _check_rate_limit(client_ip: str) -> bool:
    if _rate_limit <= 0:
        return True  # Explicit 0 disables rate limiting (for tests); env var is clamped to >=1.
    now = time.time()
    needs_cleanup = False
    with _rate_lock:
        count, window_start = _rate_state.get(client_ip, (0, now))
        if now - window_start > _rate_window:
            count, window_start = 0, now
        count += 1
        _rate_state[client_ip] = (count, window_start)
        # Defer expensive cleanup outside lock to avoid blocking hot path.
        needs_cleanup = len(_rate_state) > _rate_max_entries * 0.9
        result = count <= _rate_limit
    if needs_cleanup:
        _evict_stale_entries(now)
    return result


def _evict_stale_entries(now: float) -> None:
    """Evict stale/LRU entries without holding lock during sort."""
    # Snapshot keys to avoid holding lock during O(n log n) sort.
    with _rate_lock:
        if len(_rate_state) <= _rate_max_entries * 0.9:
            return
        snapshot = list(_rate_state.items())
    # Stale eviction outside lock
    stale_ips = [ip for ip, (_, ws) in snapshot if now - ws > _rate_window]
    if stale_ips:
        with _rate_lock:
            for ip in stale_ips:
                _rate_state.pop(ip, None)
            if len(_rate_state) <= _rate_max_entries * 0.9:
                return
    # LRU eviction: sort snapshot outside lock, then delete under lock
    with _rate_lock:
        if len(_rate_state) <= _rate_max_entries * 0.9:
            return
        # Re-snapshot after stale cleanup for accurate ordering
        current = list(_rate_state.items())
    current.sort(key=lambda item: item[1][1])
    excess = len(current) - int(_rate_max_entries * 0.9)
    to_evict = [ip for ip, _ in current[:max(excess, 1)]]
    with _rate_lock:
        for ip in to_evict:
            _rate_state.pop(ip, None)


def _client_ip(handler: DashboardHandler) -> str:
    """Resolve client IP when the direct peer is a trusted proxy.

    Per RFC 7239, X-Forwarded-For is "client, proxy1, proxy2". The left-most
    element is the most easily spoofed (client-controlled), so for a chain of
    trusted proxies we iterate from the RIGHT and return the first address
    that is NOT a trusted proxy — that is the real client as reported by the
    closest trusted proxy. If all entries are trusted proxies, fall back to
    the left-most entry (single-proxy case).
    """
    direct = handler.client_address[0]
    if direct in _TRUSTED_PROXIES:
        raw = handler.headers.get("X-Forwarded-For", "")
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        if parts:
            # L4: scan from the right (closest trusted proxy) and return the
            # first non-trusted address — this is the real client. The
            # left-most entry is client-controlled and easily spoofed.
            for candidate in reversed(parts):
                try:
                    ipaddress.ip_address(candidate)
                except ValueError:
                    continue
                if candidate not in _TRUSTED_PROXIES:
                    return candidate
            # All entries were trusted proxies (unusual) — use left-most.
            try:
                ipaddress.ip_address(parts[0])
                return parts[0]
            except ValueError:
                pass
    return direct


def _dashboard_token(root: Path) -> str | None:
    """Return the configured dashboard token, or None for open access.

    Authentication is OPT-IN: set ``AIZEE_DASHBOARD_TOKEN`` (or legacy
    ``AGENT_OS_DASHBOARD_TOKEN``) to require Bearer auth on every API call.
    By default the dashboard runs unauthenticated — a deliberate choice for
    local use, which stays safe because the server binds to 127.0.0.1,
    GETs are read-only/dry-run, and state-changing POSTs still enforce the
    CSRF custom header that cross-origin pages cannot set.

    B9: If no env var is set, reads a previously auto-generated token from
    ``state/dashboard.token`` (created on first network-exposed start).
    """
    env_token = (
        os.environ.get("AIZEE_DASHBOARD_TOKEN")
        or os.environ.get("AGENT_OS_DASHBOARD_TOKEN")
    )
    if env_token:
        return env_token
    # B9: Read auto-generated token from state file if it exists.
    token_file = root / "state" / "dashboard.token"
    if token_file.exists():
        stored = token_file.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    return None


def _write_dashboard_token_file(root: Path, token: str) -> Path:
    """Persist an auto-generated dashboard token to ``state/dashboard.token`` (B9).

    The file is created with 0o600 permissions. The token is never printed
    to stdout — only the file path is logged.
    """
    token_file = root / "state" / "dashboard.token"
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token, encoding="utf-8")
    try:
        import platform

        if platform.system() == "Windows":
            import getpass
            import subprocess

            try:
                user = os.getlogin()
            except OSError:
                user = getpass.getuser()
            subprocess.run(
                ["icacls", str(token_file), "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        else:
            token_file.chmod(0o600)
    except Exception:
        with contextlib.suppress(OSError):
            token_file.chmod(0o600)
    return token_file


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler with shared kernel/memory and per-IP rate limiting."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.root = config.discover_root()
        self.project_root = config.discover_project_root()
        self.kernel = _kernel_instance()
        self.memory = _memory_instance()
        super().__init__(*args, **kwargs)

    def _origin(self) -> str:
        """Return a validated CORS origin to reflect, or "" to disallow.

        Security: never reflect ``*`` or an unvalidated configured origin with
        credentials. The reflected value must exactly match the request Origin
        against an explicit allowlist (configured env value or the built-in
        ``_ALLOWED_ORIGINS``). A wildcard ``*`` configured value is rejected
        because ``Access-Control-Allow-Credentials: true`` is always set.
        """
        configured = _env_first("AIZEE_DASHBOARD_ORIGIN", "AGENT_OS_DASHBOARD_ORIGIN")
        request_origin = self.headers.get("Origin", "")
        # Build an allowlist: configured origin (if any, and not "*") + defaults.
        allow: set[str] = set(_ALLOWED_ORIGINS)
        if configured and configured != "*":
            allow.add(configured)
        # Only reflect the request Origin if it is on the allowlist.
        if request_origin and request_origin in allow:
            return request_origin
        return ""

    _CSP: str = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none';"
    )

    def _cors_headers(self) -> None:
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        # NOTE: X-Requested-With is intentionally NOT exposed here. It is the
        # CSRF guard header (_csrf); listing it in Allow-Headers would let a
        # cross-origin page (that passed the origin check) set it and bypass
        # the CSRF protection. Only Authorization/Content-Type are safe to
        # expose; the dashboard's same-origin JS already sets X-Requested-With.
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _security_headers(self) -> None:
        self.send_header("Content-Security-Policy", self._CSP)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        # The UI ships without asset hashing; heuristic browser caching would
        # serve a STALE index.html after upgrades (breaking it against newer
        # CSP/routes). Local files are cheap — always revalidate.
        self.send_header("Cache-Control", "no-cache")

    def _send(
        self, code: int, body: bytes, content_type: str = "text/plain", cors: bool = True
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        if cors:
            self._cors_headers()
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _auth(self) -> bool:
        token = _dashboard_token(self.root)
        if not token:
            return True  # Open-access mode (opt-in auth via AIZEE_DASHBOARD_TOKEN).
        header = self.headers.get("Authorization", "")
        return hmac.compare_digest(header, f"Bearer {token}")

    def _csrf(self) -> bool:
        """State-changing requests must carry a non-forgeable custom header.

        Cross-origin web pages cannot set custom headers unless CORS explicitly
        allows them, and the strict CORS origin policy above blocks untrusted
        origins. Same-origin dashboard JS sets this header on every POST.
        """
        return self.headers.get("X-Requested-With") == "AIOS-Dashboard"

    def do_OPTIONS(self) -> None:
        self._send(204, b"", cors=True)

    # Static UI assets are served without authentication: they contain no
    # secrets, and the token prompt lives inside app.js — requiring auth to
    # fetch the page that asks for the token is a chicken-and-egg deadlock.
    # Everything under /api/* (and any other path) stays token-protected.
    # /api/health is public so K8s probes pass even when AIZEE_DASHBOARD_TOKEN is set
    # (see deploy/k8s/deployment.yaml readinessProbe/livenessProbe).
    _PUBLIC_ASSETS: frozenset[str] = frozenset({
        "/", "/index.html", "/index.css", "/app.js",
        "/favicon.ico", "/favicon-32.png", "/favicon-16.png",
        "/apple-touch-icon.png", "/logo.png",
    })
    _PUBLIC_API_PATHS: frozenset[str] = frozenset({
        "/api/health",
    })

    def _handle(self) -> None:
        if not _check_rate_limit(_client_ip(self)):
            self._send(429, b"Rate limit exceeded", cors=True)
            return
        parsed = urllib.parse.urlparse(self.path)
        is_public_asset = (
            (self.command == "GET" and parsed.path in self._PUBLIC_ASSETS)
            or parsed.path in self._PUBLIC_API_PATHS
        )
        if not is_public_asset and not self._auth():
            self._send(401, b"Unauthorized", cors=True)
            return
        if self.command == "POST" and not self._csrf():
            self._send(403, b"CSRF protection failed", cors=True)
            return
        if parsed.path == "/api/status":
            self._send_status()
        elif parsed.path == "/api/health":
            self._send_health()
        elif parsed.path == "/api/check":
            self._send_check(parsed.query)
        elif parsed.path == "/api/metrics":
            self._send_metrics()
        elif parsed.path == "/api/telemetry":
            self._send_telemetry()
        elif parsed.path == "/api/system":
            self._send_system()
        elif parsed.path == "/api/audit":
            self._send_audit()
        elif parsed.path == "/api/guardian":
            self._send_guardian()
        elif parsed.path == "/api/capabilities":
            self._send_capabilities()
        elif parsed.path == "/api/tracing":
            self._send_tracing()
        elif parsed.path == "/api/lint":
            self._send_lint()
        elif parsed.path == "/api/memory/search":
            self._send_memory_search(parsed.query)
        elif parsed.path == "/api/policy/test":
            self._send_policy_test()
        elif parsed.path == "/api/workflows":
            self._send_workflows()
        elif parsed.path == "/api/workflow/run":
            self._send_workflow_run()
        elif parsed.path == "/api/saga/run":
            self._send_saga_run()
        elif parsed.path.startswith("/api/saga/"):
            self._send_saga_get(parsed.path[10:])
        elif parsed.path == "/api/chat":
            self._send_chat()
        elif parsed.path == "/api/graph":
            self._send_graph()
        elif parsed.path == "/api/graph/stats":
            self._send_graph_stats()
        elif parsed.path == "/api/events":
            self._send_sse_events()
        elif parsed.path == "/api/settings" and self.command == "GET":
            self._send_settings_get()
        elif parsed.path == "/api/settings" and self.command == "POST":
            self._send_settings_update()
        elif parsed.path == "/api/settings/defaults" and self.command == "GET":
            self._send_settings_defaults()
        elif parsed.path == "/api/settings/reset" and self.command == "POST":
            self._send_settings_reset()
        elif parsed.path == "/api/settings/mcp-status" and self.command == "GET":
            self._send_settings_mcp_status()
        elif parsed.path == "/api/settings/restart" and self.command == "POST":
            self._send_settings_restart()
        elif parsed.path == "/" or parsed.path == "/index.html":
            self._serve_file(_asset_dir() / "index.html")
        elif parsed.path == "/app.js":
            self._serve_file(_asset_dir() / "app.js", "application/javascript; charset=utf-8")
        elif parsed.path == "/vendor/chart.umd.min.js":
            self._serve_file(
                _asset_dir() / "static" / "vendor" / "chart.umd.min.js",
                "application/javascript; charset=utf-8",
            )
        elif parsed.path == "/index.css":
            self._serve_file(_asset_dir() / "index.css")
        elif parsed.path == "/favicon.ico":
            self._serve_file(_asset_dir() / "static" / "favicon.ico")
        elif parsed.path == "/favicon-32.png":
            self._serve_file(_asset_dir() / "static" / "favicon-32.png")
        elif parsed.path == "/favicon-16.png":
            self._serve_file(_asset_dir() / "static" / "favicon-16.png")
        elif parsed.path == "/apple-touch-icon.png":
            self._serve_file(_asset_dir() / "static" / "apple-touch-icon.png")
        elif parsed.path == "/logo.png":
            self._serve_file(_asset_dir().parent / "logo.png")
        else:
            self._send(404, b"Not found")

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _read_json_body(self) -> dict[str, Any] | None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (ValueError, TypeError):
            # SEC-05: garbage Content-Length header → 400, not traceback
            self._send(400, b"Invalid Content-Length header")
            return None
        if content_length <= 0:
            return {}
        if content_length > _MAX_BODY_SIZE:
            self._send(413, b"Payload too large")
            return None
        try:
            data = self.rfile.read(content_length)
            return cast(dict[str, Any], json.loads(data.decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send(400, b"Invalid JSON body")
            return None

    def _send_status(self) -> None:
        self._send(200, json.dumps(self.kernel.status(), default=str).encode("utf-8"), "application/json")

    def _send_health(self) -> None:
        health = {"ok": True, "root": str(self.root), "version": config.VERSION}
        self._send(200, json.dumps(health).encode("utf-8"), "application/json")

    def _send_check(self, query: str) -> None:
        """Dry-run policy evaluation only.

        GET is CSRF-exempt and must never trigger privileged state changes,
        so ``approve`` is rejected outright and evaluation always runs with
        ``dry_run=True`` (no audit writes, no budget deduction). Real
        approved actions belong to the CLI/MCP gates.
        """
        qs = urllib.parse.parse_qs(query)
        action = qs.get("action", [""])[0]
        if not action or not action.isalnum():
            self._send(400, b"Invalid action format")
            return
        if qs.get("approve", [""])[0]:
            self._send(400, b"Approving actions via GET is not allowed; use the aizee CLI gate instead")
            return
        result = self.kernel.act(action, dry_run=True)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_memory_search(self, query: str) -> None:
        qs = urllib.parse.parse_qs(query)
        q = qs.get("q", [""])[0]
        kind = qs.get("kind", [""])[0] or None
        results = self.memory.search(q, kind)
        items = [{"id": r.id, "kind": r.kind, "source": r.source, "content": r.content} for r in results]
        self._send(200, json.dumps(items).encode("utf-8"), "application/json")

    def _send_policy_test(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        action = body.get("action", "")
        if not action or not action.isalnum():
            self._send(400, b"Invalid action format")
            return
        args = body.get("args", {}) if isinstance(body.get("args"), dict) else {}
        result = self.kernel.act(action, dry_run=True, **args)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_workflows(self) -> None:
        workflows = self.kernel.list_workflows()
        self._send(200, json.dumps(workflows, default=str).encode("utf-8"), "application/json")

    def _send_workflow_run(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        workflow_id = body.get("workflow_id", "")
        if not workflow_id or not isinstance(workflow_id, str):
            self._send(400, b"Missing or invalid workflow_id")
            return
        context = body.get("context", {}) if isinstance(body.get("context"), dict) else {}
        result = self.kernel.run_workflow(workflow_id, context)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_saga_run(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        saga_id = body.get("saga_id", "")
        if not saga_id or not isinstance(saga_id, str):
            self._send(400, b"Missing or invalid saga_id")
            return
        steps = body.get("steps", [])
        if not isinstance(steps, list):
            self._send(400, b"steps must be a list")
            return
        context = body.get("context", {}) if isinstance(body.get("context"), dict) else {}
        result = self.kernel.run_saga(saga_id, steps, context)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_saga_get(self, saga_id: str) -> None:
        result = self.kernel.saga.get_saga(saga_id)
        if result is None:
            self._send(404, b"Saga not found")
            return
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_chat(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        message = body.get("message", "")
        if not message or not isinstance(message, str):
            self._send(400, b"Missing or invalid message")
            return
        session_id = body.get("session_id")
        if session_id is not None and not isinstance(session_id, str):
            self._send(400, b"Invalid session_id")
            return
        result = self.kernel.chat_message(message, session_id=session_id)
        self._send(200, json.dumps(result, default=str).encode("utf-8"), "application/json")

    def _send_metrics(self) -> None:
        body = format_metrics(self.kernel).encode("utf-8")
        self._send(200, body, "text/plain; version=0.0.4; charset=utf-8", cors=False)

    def _send_telemetry(self) -> None:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            limit = min(int(qs.get("limit", ["100"])[0]), 1000)
        except (ValueError, TypeError):
            self._send(400, b"Invalid limit")
            return
        event_type = qs.get("type", [""])[0] or None
        events = self.kernel.telemetry.query(limit=limit, event_type=event_type)
        self._send(200, json.dumps(events, default=str).encode("utf-8"), "application/json")

    def _send_system(self) -> None:
        data = system_metrics()
        data["root"] = str(self.root)
        data["project_root"] = str(self.project_root)
        data["version"] = config.VERSION
        self._send(200, json.dumps(data, default=str).encode("utf-8"), "application/json")

    def _send_audit(self) -> None:
        # SEC-06: support ?limit= (default 200, max 1000) + tail-read
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            limit = min(int(qs.get("limit", ["200"])[0]), 1000)
        except (ValueError, TypeError):
            limit = 200
        audit_file = self.root / "state" / "audit.log"
        lines: list[Any] = []
        if audit_file.exists():
            # Tail-read: only keep the last `limit` lines in memory
            from collections import deque
            with audit_file.open("r", encoding="utf-8") as f:
                tail = list(deque(f, maxlen=limit))
            for line in tail:
                if line.strip():
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        self._send(200, json.dumps(lines, default=str).encode("utf-8"), "application/json")

    def _send_guardian(self) -> None:
        rules = [r.get("name", "unnamed") for r in self.kernel.guardian.rules]
        self._send(200, json.dumps({"rules": rules, "count": len(rules)}).encode("utf-8"), "application/json")

    def _send_capabilities(self) -> None:
        self._send(200, json.dumps({"capabilities": self.kernel.capabilities.list()}).encode("utf-8"), "application/json")

    def _send_tracing(self) -> None:
        # SEC-06: support ?limit= (default 200, max 1000) + tail-read
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        try:
            limit = min(int(qs.get("limit", ["200"])[0]), 1000)
        except (ValueError, TypeError):
            limit = 200
        trace_file = self.kernel.project_root / "state" / "spans.jsonl"
        lines: list[Any] = []
        if trace_file.exists():
            # Tail-read: only keep the last `limit` lines in memory
            from collections import deque
            with trace_file.open("r", encoding="utf-8") as f:
                tail = list(deque(f, maxlen=limit))
            for line in tail:
                if line.strip():
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        self._send(200, json.dumps(lines, default=str).encode("utf-8"), "application/json")

    def _send_lint(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        code = body.get("code", "")
        if not isinstance(code, str):
            self._send(400, b"Missing or invalid code")
            return
        linter = AstryxLinter(max_lines=body.get("max_lines", 50), max_params=body.get("max_params", 7))
        findings = linter.lint_text(code)
        self._send(
            200,
            json.dumps({"ok": True, "findings": [finding.__dict__ for finding in findings]}).encode("utf-8"),
            "application/json",
        )

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists():
            self._send(404, b"Not found")
            return
        ctype = content_type or mimetypes.guess_type(str(path))[0] or "text/plain"
        self._send(200, path.read_bytes(), ctype, cors=False)

    # --- Settings API ---

    def _send_settings_get(self) -> None:
        sm = _settings_instance()
        section = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("section", [""])[0]
        if section:
            if section not in SETTINGS_SECTIONS:
                self._send(400, b"Invalid section")
                return
            data = sm.get_section(section)
        else:
            data = sm.get_all()
        self._send(200, json.dumps(data, default=str).encode("utf-8"), "application/json")

    def _send_settings_update(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        section = body.get("section", "")
        data = body.get("data", {})
        if not section or section not in SETTINGS_SECTIONS:
            self._send(400, b"Missing or invalid section")
            return
        if not isinstance(data, dict):
            self._send(400, b"data must be an object")
            return
        sm = _settings_instance()
        try:
            updated = sm.update_section(section, data)
        except Exception as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode("utf-8"), "application/json")
            return
        # When MCP server toggles change, sync ALL IDE MCP config files
        # (Devin + Claude Code) so disabled servers are not loaded on next
        # IDE restart.
        if section == "mcp_servers":
            with contextlib.suppress(Exception):
                _sync_ide_mcp_configs(self.root, data)
        self._send(200, json.dumps({"ok": True, "section": section, "data": updated}, default=str).encode("utf-8"), "application/json")

    def _send_settings_defaults(self) -> None:
        sm = _settings_instance()
        section = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("section", [""])[0]
        if section:
            if section not in SETTINGS_SECTIONS:
                self._send(400, b"Invalid section")
                return
            try:
                defaults = sm.reset_section(section)
            except Exception as exc:
                self._send(400, json.dumps({"error": str(exc)}).encode("utf-8"), "application/json")
                return
        else:
            defaults = sm.reset_all()
        self._send(200, json.dumps({"ok": True, "data": defaults}, default=str).encode("utf-8"), "application/json")

    def _send_settings_reset(self) -> None:
        body = self._read_json_body()
        if body is None:
            return
        section = body.get("section", "")
        sm = _settings_instance()
        if section:
            if section not in SETTINGS_SECTIONS:
                self._send(400, b"Invalid section")
                return
            try:
                data = sm.reset_section(section)
            except Exception as exc:
                self._send(400, json.dumps({"error": str(exc)}).encode("utf-8"), "application/json")
                return
        else:
            data = sm.reset_all()
        # When MCP server toggles are reset, sync ALL IDE MCP config files
        # so all servers are restored to enabled in Devin + Claude Code.
        if section == "mcp_servers" or not section:
            with contextlib.suppress(Exception):
                _sync_ide_mcp_configs(self.root, data.get("mcp_servers", data) if isinstance(data, dict) else {})
        self._send(200, json.dumps({"ok": True, "data": data}, default=str).encode("utf-8"), "application/json")

    def _send_settings_mcp_status(self) -> None:
        sm = _settings_instance()
        status = sm.mcp_status()
        categories = sm.mcp_categories()
        self._send(
            200,
            json.dumps({"servers": status, "categories": categories}, default=str).encode("utf-8"),
            "application/json",
        )

    def _send_settings_restart(self) -> None:
        """Soft-reload the kernel: reset caches so next request rebuilds them.

        This clears the kernel and memory caches so the next request
        re-initializes them from disk (policies, budget). The shared
        SettingsManager is reloaded in place so the MCP enable-gate picks up
        toggles immediately. The MCP process pool is terminated so disabled
        servers do not keep running and re-enabled servers reconnect fresh.
        """
        global _kernel_cache, _memory_cache
        root = config.discover_root()
        with _cache_lock:
            # Flush budget state before dropping the kernel reference
            if _kernel_cache is not None:
                with contextlib.suppress(Exception):
                    _kernel_cache[1].save()
            _kernel_cache = None
            if _memory_cache is not None:
                with contextlib.suppress(Exception):
                    _memory_cache[1].close()
            _memory_cache = None
        # Reload the shared settings manager so every MCP gate (McpClient,
        # PluginManager, kernel) sees the new toggle state at once.
        with contextlib.suppress(Exception):
            reload_settings_manager(root)
        # Terminate MCP process pool so servers reconnect with fresh config
        # (and disabled servers stop running immediately).
        with contextlib.suppress(Exception):
            from runtime.mcp_client import _terminate_pool
            _terminate_pool()
        self._send(200, json.dumps({"ok": True, "message": "aiZee kernel reloaded"}).encode("utf-8"), "application/json")

    # Simple in-memory cache for graph.json to avoid reading 2MB on every request
    _graph_cache: ClassVar[dict[str, tuple[float, bytes]]] = {}
    _graph_cache_lock: ClassVar[threading.Lock] = threading.Lock()

    def _send_graph(self) -> None:
        """Serve the graphify graph.json (capped to 2MB for dashboard) with ETag/mtime cache."""
        graph_path = self.root / "graphify-out" / "graph.json"
        if not graph_path.exists():
            self._send(200, json.dumps({"ok": False, "error": "graph.json not found"}).encode("utf-8"), "application/json")
            return
        # Check If-None-Match / mtime cache
        try:
            mtime = graph_path.stat().st_mtime
        except OSError:
            mtime = 0
        cache_key = str(graph_path)
        # Handle ETag/If-None-Match
        etag = f'W/"{int(mtime)}-{graph_path.stat().st_size if graph_path.exists() else 0}"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        with self._graph_cache_lock:
            cached = self._graph_cache.get(cache_key)
            if cached and cached[0] == mtime:
                data = cached[1]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", "public, max-age=30")
                self._cors_headers()
                self._security_headers()
                self.end_headers()
                self.wfile.write(data)
                return
        # DASH-7 fix: check size before loading the whole file into memory to
        # avoid a memory-exhaustion DoS on very large graph.json files.
        if graph_path.stat().st_size > 2 * 1024 * 1024:
            self._send(200, json.dumps({"ok": False, "error": "graph too large for dashboard; use graphify MCP"}).encode("utf-8"), "application/json")
            return
        data = graph_path.read_bytes()
        with self._graph_cache_lock:
            self._graph_cache[cache_key] = (mtime, data)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "public, max-age=30")
        self._cors_headers()
        self._security_headers()
        self.end_headers()
        self.wfile.write(data)

    def _send_graph_stats(self) -> None:
        """Return summary stats from the graphify graph."""
        graph_path = self.root / "graphify-out" / "graph.json"
        if not graph_path.exists():
            self._send(200, json.dumps({"ok": False, "error": "graph.json not found"}).encode("utf-8"), "application/json")
            return
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            nodes = data.get("nodes", [])
            links = data.get("links", [])
            communities = set()
            for n in nodes:
                c = n.get("community") if isinstance(n, dict) else None
                if isinstance(c, int):
                    communities.add(c)
            stats = {"ok": True, "nodes": len(nodes), "edges": len(links), "communities": len(communities)}
            self._send(200, json.dumps(stats).encode("utf-8"), "application/json", cors=True)
        except (json.JSONDecodeError, OSError) as exc:
            self._send(200, json.dumps({"ok": False, "error": str(exc)}).encode("utf-8"), "application/json", cors=True)

    _sse_clients: ClassVar[int] = 0
    _sse_lock: ClassVar[threading.Lock] = threading.Lock()
    _MAX_SSE_CLIENTS: ClassVar[int] = 20

    def _send_sse_events(self) -> None:
        """Server-Sent Events stream for real-time telemetry.

        SEC-04: routes through shared security headers, polls every 5s (not 1s),
        hard 10-min connection lifetime (EventSource auto-reconnects).
        Limits concurrent SSE clients to prevent thread-pool exhaustion.
        """
        with self._sse_lock:
            if DashboardHandler._sse_clients >= DashboardHandler._MAX_SSE_CLIENTS:
                self._send(503, b"Too many SSE clients", cors=True)
                return
            DashboardHandler._sse_clients += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        # Security headers (same as _send)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        if _ALLOWED_ORIGINS:
            origin = self.headers.get("Origin", "")
            if origin in _ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()
        try:
            # 10 min max (120 iterations x 5s), down from 60s x 1s polling
            for _ in range(120):
                status = self.kernel.status()
                payload = json.dumps({
                    "version": status.get("version"),
                    "budgets": status.get("budgets"),
                    "metrics": status.get("metrics"),
                    "agents": status.get("agents"),
                    "guardian_rules": status.get("guardian_rules"),
                    "capabilities": status.get("capabilities"),
                    "tech_stack": status.get("tech_stack"),
                    "timestamp": time.time(),
                }, default=str)
                self.wfile.write(f"data: {payload}\n\n".encode())
                self.wfile.flush()
                time.sleep(5)  # 5s poll interval (was 1s)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            with self._sse_lock:
                DashboardHandler._sse_clients = max(0, DashboardHandler._sse_clients - 1)

    def log_message(self, format: str, *args: object) -> None:
        """Log only errors and warnings, silence routine access logs."""
        msg = format % args
        if " 4" in msg or " 5" in msg:
            print(f"[dashboard] {msg}", file=sys.stderr)


def _shutdown(_signum: int, _frame: Any) -> None:  # pragma: no cover
    """Graceful shutdown — flush storage and close DB connections."""
    try:
        from runtime.storage_backend import StorageFactory
        StorageFactory().shutdown_all()
    except Exception:
        logger.debug("Storage shutdown failed during dashboard shutdown", exc_info=True)
    # Close cached memory store connections
    global _memory_cache
    if _memory_cache is not None:
        with contextlib.suppress(Exception):
            _memory_cache[1].close()
        _memory_cache = None
    sys.exit(0)


def _is_loopback_host(host: str) -> bool:
    """Return True only for loopback addresses (SEC-W1).

    Accepts: 127.x.x.x, localhost, ::1.
    Rejects: 0.0.0.0, external IPs, hostnames.
    """
    h = host.strip().lower()
    if h in ("localhost", "::1"):
        return True
    # 127.0.0.0/8 — any 127.x.x.x is loopback
    parts = h.split(".")
    if len(parts) == 4 and parts[0] == "127":
        return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts[1:])
    return False


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = _env_first("AIZEE_DASHBOARD_HOST", "AGENT_OS_HOST", default="127.0.0.1")
    token = _dashboard_token(Path(os.environ.get("AIZEE_ROOT", ".")))
    # SEC-W1: refuse to bind non-loopback host without authentication. When no
    # token is configured we generate a cryptographically random one so the
    # service still boots (e.g. `docker compose up`) instead of crash-looping,
    # while remaining authenticated rather than open (P0 fix).
    if not _is_loopback_host(host) and token is None:
        import secrets

        token = secrets.token_urlsafe(32)
        os.environ["AIZEE_DASHBOARD_TOKEN"] = token
        # B9: Write the token to a file (0o600) instead of printing to stdout.
        token_path = _write_dashboard_token_file(
            Path(os.environ.get("AIZEE_ROOT", ".")), token
        )
        logger.info(
            "NETWORK-EXPOSED MODE: no AIZEE_DASHBOARD_TOKEN set — generated a "
            "random token and stored it at %s. Pass it as "
            "`Authorization: Bearer <token>`. Set the env var for a stable "
            "token across restarts.",
            token_path,
        )
    # Fail-closed: never boot network-exposed with a known placeholder/empty
    # token (e.g. the K8s secret shipped with REPLACE_WITH_REAL_TOKEN...).
    # Empty token is only acceptable on loopback (local open-access dev).
    if token in ("REPLACE_WITH_REAL_TOKEN_DO_NOT_DEPLOY_THIS",) or (
        not token and not _is_loopback_host(host)
    ):
        raise SystemExit(
            "aiZee dashboard refuses to start: AIZEE_DASHBOARD_TOKEN is a "
            "placeholder or empty while binding a non-loopback host. Generate "
            "a real token: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"aiZee dashboard: http://{host}:{port}")
    if not token:
        print("Open-access mode: APIs are unauthenticated (localhost only). "
              "Set AIZEE_DASHBOARD_TOKEN to require a Bearer token.")
    elif not _is_loopback_host(host):
        print("WARNING: NETWORK-EXPOSED MODE — dashboard is accessible on the "
              f"network at {host}:{port}. Ensure TLS is terminated at ingress.")
    server.serve_forever()
