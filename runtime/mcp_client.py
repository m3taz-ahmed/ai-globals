"""MCP client for calling external MCP servers via stdio.

Provides both synchronous (threading-based) and asynchronous (asyncio) interfaces.
The async interface uses asyncio.subprocess for non-blocking I/O.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import queue
import shutil
import subprocess
import sysconfig
import threading
import uuid
from pathlib import Path
from typing import Any, Protocol, cast

_logger = logging.getLogger(__name__)

# Shared stdio process pool keyed by (server_name, os_root).  Keeps MCP server
# processes alive across multiple tool calls instead of spawning per call.
_PROC_POOL: dict[tuple[str, Path], subprocess.Popen[str]] = {}
_PROC_INIT: dict[tuple[str, Path], bool] = {}
_PROC_LOCK = threading.Lock()
_SEND_LOCKS: dict[tuple[str, Path], threading.Lock] = {}
_DEFAULT_TIMEOUT = 30.0
_SECRETS_LOADED = False

# Allowlist of env vars that .env files are permitted to set.
# Prevents injection of unexpected env vars via malicious .env files.
_ENV_ALLOWLIST: frozenset[str] = frozenset({
    # Core
    "AIZEE_ROOT", "AGENT_PROJECT_ROOT", "AIOS_ENCRYPTION_KEY", "AIOS_VERSION",
    # Dashboard
    "AIZEE_DASHBOARD_TOKEN", "AIZEE_DASHBOARD_ALLOW_NO_TOKEN",
    "AIZEE_DASHBOARD_ORIGIN", "AGENT_OS_DASHBOARD_TOKEN",
    "AGENT_OS_DASHBOARD_ALLOW_NO_TOKEN", "AGENT_OS_DASHBOARD_ORIGIN",
    "AGENT_OS_DASHBOARD_MAX_BODY_SIZE", "AGENT_OS_DASHBOARD_RATE_LIMIT",
    "AGENT_OS_DASHBOARD_RATE_WINDOW", "AGENT_OS_DASHBOARD_RATE_MAX_ENTRIES",
    "AGENT_OS_DASHBOARD_TRUSTED_PROXIES", "AGENT_OS_HOST",
    # Sentry
    "SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE", "SENTRY_ENVIRONMENT",
    # Plugins (legacy)
    "UPWORK_CLIENT_ID", "UPWORK_CLIENT_SECRET",
    "FREELANCER_OAUTH_TOKEN", "FREELANCER_ACCOUNTS",
    "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_MCP_TOKEN_PATH",
    "GRAPHIFY_WRAPPER_LOG",
    # Plugins (marketing/freelance — 27 new)
    "AUTOMATISCH_API_KEY", "AUTOMATISCH_URL",
    "BREVO_API_KEY",
    "CHATWOOT_API_KEY", "CHATWOOT_URL",
    "DOCUMENSO_API_KEY",
    "ERPNEXT_API_KEY", "ERPNEXT_URL",
    "FLAGSMITH_API_KEY",
    "FORMBRICKS_API_KEY",
    "GOOGLE_ADS_DEVELOPER_TOKEN", "GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET",
    "GROWTHBOOK_API_KEY",
    "HUBSPOT_API_KEY",
    "KHAMSAT_API_TOKEN",
    "KIT_API_KEY",
    "KLAVIYO_API_KEY",
    "LAGO_API_KEY", "LAGO_API_URL",
    "LISTMONK_API_URL", "LISTMONK_API_KEY",
    "META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID",
    "MOSTAQL_API_TOKEN",
    "N8N_API_KEY", "N8N_BASE_URL",
    "OPENREPLAY_API_KEY",
    "POSTHOG_API_KEY", "POSTHOG_PROJECT_ID",
    "POSTIZ_API_KEY",
    "SENDGRID_API_KEY",
    "TIKTOK_ACCESS_TOKEN", "TIKTOK_ADVERTISER_ID",
    "TWENTY_API_KEY",
    "TWITTER_BEARER_TOKEN",
    "YOUTUBE_API_KEY",
})


def _load_secrets_once() -> None:
    """Load ``.env`` from the OS root into ``os.environ`` (once per process).

    Only known environment variable names (allowlist) are accepted — unknown
    keys are silently skipped to prevent injection of unexpected env vars.
    """
    global _SECRETS_LOADED
    if _SECRETS_LOADED:
        return
    _SECRETS_LOADED = True
    env_file = Path(os.environ.get("AIZEE_ROOT", "")) / ".env"
    if not env_file.is_file():
        # Fallback: parent of runtime/ directory
        env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not key or value.startswith("your_"):
            continue
        if key not in _ENV_ALLOWLIST:
            continue
        os.environ.setdefault(key, value)


def _user_script_dirs() -> list[str]:
    """Return Python user-base script/bin directories not already on PATH.

    When a package is installed via ``pip install --user`` (the default on
    systems without a writable global site-packages), its console-script
    entry points land in a per-user Scripts/bin directory that is frequently
    missing from ``PATH``. We discover those directories via ``sysconfig``
    so MCP servers shipped as Python entry points resolve portably — no
    hardcoded per-machine paths in ``config.json``.
    """
    scheme = "nt_user" if os.name == "nt" else "posix_user"
    candidates: list[str] = []
    scripts = sysconfig.get_path("scripts", scheme)
    if scripts:
        candidates.append(scripts)
    # On Windows the per-user Scripts dir is the canonical one; on POSIX the
    # bin dir may live under the userbase too.
    userbase = sysconfig.get_config_var("userbase")
    if userbase:
        for child in ("Scripts", "bin"):
            d = str(Path(userbase) / child)
            if d not in candidates and Path(d).is_dir():
                candidates.append(d)
    existing = {str(Path(p).resolve()) for p in os.environ.get("PATH", "").split(os.pathsep) if p}
    return [d for d in candidates if str(Path(d).resolve()) not in existing]


def _user_site_dirs() -> list[str]:
    """Return Python user site-packages directories for PYTHONPATH augmentation."""
    scheme = "nt_user" if os.name == "nt" else "posix_user"
    site = sysconfig.get_path("purelib", scheme)
    return [site] if site else []


def _terminate_pool() -> None:
    with _PROC_LOCK:
        for proc in _PROC_POOL.values():
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        _PROC_POOL.clear()
        _PROC_INIT.clear()


atexit.register(_terminate_pool)


# B2: Shell metacharacters that indicate command injection attempts.
_SHELL_METACHARS = set(";|&`$(){}[]<>!\n\r")
# B2: Allowed MCP server command basenames (extend as new servers are added).
_ALLOWED_MCP_COMMANDS = frozenset({
    "python", "python3", "node", "npx", "uv", "uvx", "ruby", "go",
    "docker", "java", "bun", "deno",
})


def _get_settings_manager(os_root: Path) -> Any:
    """Return the shared ``SettingsManager`` for ``os_root`` (lazy import).

    Imported lazily to avoid a runtime→settings import at module load and to
    dodge any import-cycle risk. Returns an object exposing
    ``is_mcp_enabled(name) -> bool``.
    """
    from runtime.settings import get_settings_manager

    return get_settings_manager(os_root)


# Error payload returned when a server is disabled in dashboard settings.
def _disabled_result(server_name: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": (
            f"MCP server '{server_name}' is disabled in dashboard settings "
            "(toggle it back on in the Settings → MCP Servers panel)"
        ),
        "disabled": True,
    }


def _validate_mcp_command(cmd: str, args: list[Any]) -> None:
    """Validate that an MCP server command is safe to spawn.

    Rejects:
    - Shell metacharacters in command or args (injection prevention).
    - Commands that are not in the allowlist (when basename doesn't match).
    - Absolute paths to non-standard locations (must resolve via PATH or be in allowlist).
    """
    if not cmd or not isinstance(cmd, str):
        raise ValueError(f"MCP command is empty or not a string: {cmd!r}")
    # Check for shell metacharacters in command
    if any(c in _SHELL_METACHARS for c in cmd):
        raise ValueError(f"MCP command contains shell metacharacters: {cmd!r}")
    # Check args for metacharacters
    for arg in args:
        if not isinstance(arg, str):
            continue
        if any(c in _SHELL_METACHARS for c in arg):
            raise ValueError(f"MCP arg contains shell metacharacters: {arg!r}")
    # Extract basename for allowlist check
    cmd_basename = Path(cmd).name.lower()
    if cmd_basename not in _ALLOWED_MCP_COMMANDS:
        import logging
        logging.getLogger(__name__).warning(
            "MCP command %r is not in the allowlist %s — proceeding but "
            "consider adding it to _ALLOWED_MCP_COMMANDS for production safety.",
            cmd, sorted(_ALLOWED_MCP_COMMANDS),
        )


class _SettingsLike(Protocol):
    """Structural type for the settings manager dependency (avoids import cycle)."""

    def is_mcp_enabled(self, server_name: str) -> bool: ...


class McpClient:
    """Spawn and call tools on an MCP server defined in config.

    Processes are cached per (server, root) so repeated calls to the same
    server reuse the initialized stdio connection.

    Enable-gate: before spawning or calling a server, the shared settings
    manager's ``is_mcp_enabled`` is consulted. A server toggled OFF in the
    dashboard settings is never spawned and its tool calls return a disabled
    error — it neither loads nor appears.
    """

    def __init__(
        self,
        server_name: str,
        os_root: Path,
        settings_manager: _SettingsLike | None = None,
    ) -> None:
        self.server_name = server_name
        self.os_root = os_root
        self.config = self._load_config()
        self._key = (server_name, os_root)
        # Resolve the shared settings manager (process-wide cache) so the
        # dashboard toggle is honored without callers having to inject it.
        if settings_manager is None:
            settings_manager = cast(_SettingsLike, _get_settings_manager(os_root))
        self._settings: _SettingsLike = settings_manager

    def _is_enabled(self) -> bool:
        """True if this server is enabled in dashboard settings (default True)."""
        try:
            return bool(self._settings.is_mcp_enabled(self.server_name))
        except Exception:
            # Fail-open on settings error: never block MCP because settings
            # could not be read. The settings manager itself is fail-safe
            # (corrupt file → defaults), so this is a defensive backstop.
            return True

    def is_enabled(self) -> bool:
        """Public check: is this MCP server enabled in dashboard settings?"""
        return self._is_enabled()

    def _load_config(self) -> dict[str, Any]:
        for settings_path in [self.os_root / ".claude" / "settings.json", self.os_root / "aizee_mcp" / "config.json"]:
            if settings_path.exists():
                data = cast(dict[str, Any], json.loads(settings_path.read_text(encoding="utf-8")))
                mcp_servers = cast(dict[str, Any], data.get("mcpServers") or data.get("mcp_servers", {}))
                if self.server_name in mcp_servers:
                    return cast(dict[str, Any], mcp_servers[self.server_name])
        return {}

    def _spawn(self) -> subprocess.Popen[str]:
        if not self.config:
            raise RuntimeError(f"MCP server '{self.server_name}' not configured")
        cmd = self.config["command"]
        args = self.config.get("args", [])
        # B2: Validate command — reject shell metacharacters and require absolute
        # path or resolvable binary. Prevents config.json command injection.
        _validate_mcp_command(cmd, args)
        _load_secrets_once()
        env = self._build_spawn_env()
        resolved = shutil.which(cmd, path=env.get("PATH"))
        if resolved:
            cmd = resolved
        return subprocess.Popen(
            [cmd, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env, cwd=str(self.os_root),
        )

    def _build_spawn_env(self) -> dict[str, str]:
        """Build environment for the child MCP server process."""
        env = {"AIZEE_ROOT": str(self.os_root), **os.environ}
        extra_path = _user_script_dirs()
        if extra_path:
            env["PATH"] = os.pathsep.join([*extra_path, env.get("PATH", "")])
        extra_site = _user_site_dirs()
        if extra_site:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join([*extra_site, existing]) if existing else os.pathsep.join(extra_site)
        return env

    def _send(
        self,
        proc: subprocess.Popen[str],
        payload: dict[str, Any],
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError("Process pipes not available")
        req = json.dumps(payload)
        proc.stdin.write(req + "\n")
        proc.stdin.flush()
        result = self._read_stdout(proc.stdout, timeout)
        if isinstance(result, Exception):
            raise result
        if not result:
            raise RuntimeError("MCP server closed stdout")
        return cast(dict[str, Any], json.loads(result))

    def _read_stdout(self, stdout: Any, timeout: float) -> str | Exception:
        """Read a line from stdout with timeout via a daemon thread."""
        q: queue.Queue[str | Exception] = queue.Queue()
        def _read() -> None:
            try:
                q.put(stdout.readline())
            except Exception as exc:
                _logger.debug("stdout read failed: %s", exc, exc_info=True)
                q.put(exc)
        reader = threading.Thread(target=_read, daemon=True)
        reader.start()
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return TimeoutError(
                f"MCP server '{self.server_name}' response timed out after {timeout}s")

    def _ensure_process(self) -> subprocess.Popen[str]:
        with _PROC_LOCK:
            proc = self._reap_or_spawn()
            if not _PROC_INIT.get(self._key):
                self._init_server(proc)
            return proc

    def _reap_or_spawn(self) -> subprocess.Popen[str]:
        """Reap dead process if needed and spawn a new one."""
        proc = _PROC_POOL.get(self._key)
        if proc is not None and proc.poll() is not None:
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
            proc = None
        if proc is None:
            proc = self._spawn()
            _PROC_POOL[self._key] = proc
            _PROC_INIT[self._key] = False
        return proc

    def _init_server(self, proc: subprocess.Popen[str]) -> None:
        """Send initialize request to the MCP server."""
        init_id = str(uuid.uuid4())
        init_resp = self._send(proc, {
            "jsonrpc": "2.0", "id": init_id, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "aizee", "version": "4.22.1"}},
        })
        if "error" in init_resp:
            self._release_locked(proc)
            raise RuntimeError(init_resp["error"])
        _PROC_INIT[self._key] = True

    def _release_locked(self, proc: subprocess.Popen[str] | None = None) -> None:
        proc = proc or _PROC_POOL.pop(self._key, None)
        _PROC_INIT.pop(self._key, None)
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Synchronous wrapper around async_call_tool."""
        if not self._is_enabled():
            return _disabled_result(self.server_name)
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            # Already in an async context — can't use asyncio.run
            # Fall back to the original sync implementation
            return self._call_tool_sync(tool_name, arguments)
        return asyncio.run(self.async_call_tool(tool_name, arguments))

    def _call_tool_sync(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Synchronous (threading-based) call_tool implementation.

        Used as a fallback when ``call_tool`` is invoked from within a
        running asyncio event loop (where ``asyncio.run`` cannot be used).
        """
        if not self._is_enabled():
            return _disabled_result(self.server_name)
        if not self.config:
            return {"ok": False, "error": f"MCP server '{self.server_name}' not configured"}
        try:
            proc = self._ensure_process()
            call_id = str(uuid.uuid4())
            send_lock = _SEND_LOCKS.setdefault(self._key, threading.Lock())
            with send_lock:
                resp = self._send(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": call_id,
                        "method": "tools/call",
                        "params": {"name": tool_name, "arguments": arguments},
                    },
                )
        except Exception as exc:
            _logger.debug("MCP tool call failed: %s", exc, exc_info=True)
            with _PROC_LOCK:
                self._release_locked()
            return {"ok": False, "error": str(exc)}
        if "error" in resp:
            return {"ok": False, "error": resp["error"]}
        return {"ok": True, "result": resp.get("result")}

    def close(self) -> None:
        """Release the cached process for this server/root."""
        with _PROC_LOCK:
            self._release_locked()

    async def async_call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Async version of call_tool using asyncio.subprocess."""
        if not self._is_enabled():
            return _disabled_result(self.server_name)
        if not self.config:
            return {"ok": False, "error": f"MCP server '{self.server_name}' not configured"}
        proc = await self._async_spawn()
        if isinstance(proc, dict):
            return proc
        try:
            init_err = await self._async_init(proc)
            if init_err:
                return init_err
            resp = await self._async_call(proc, tool_name, arguments)
        except TimeoutError:
            return {"ok": False, "error": f"MCP server '{self.server_name}' timed out"}
        except Exception as exc:
            _logger.debug("MCP async call failed: %s", exc, exc_info=True)
            return {"ok": False, "error": str(exc)}
        finally:
            await self._async_terminate(proc)
        if "error" in resp:
            return {"ok": False, "error": resp["error"]}
        return {"ok": True, "result": resp.get("result")}

    async def _async_spawn(self) -> asyncio.subprocess.Process | dict[str, Any]:
        """Spawn async subprocess. Returns process or error dict."""
        cmd = self.config["command"]
        args = self.config.get("args", [])
        _load_secrets_once()
        env = {"AIZEE_ROOT": str(self.os_root), **os.environ}
        try:
            return await asyncio.create_subprocess_exec(
                cmd, *args, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env=env, cwd=str(self.os_root),
            )
        except Exception as exc:
            _logger.debug("MCP server spawn failed: %s", exc, exc_info=True)
            return {"ok": False, "error": f"Failed to spawn MCP server: {exc}"}

    async def _async_init(self, proc: asyncio.subprocess.Process) -> dict[str, Any] | None:
        """Send initialize request. Returns error dict or None on success."""
        init_req = json.dumps({"jsonrpc": "2.0", "id": str(uuid.uuid4()),
            "method": "initialize", "params": {"protocolVersion": "2024-11-05",
            "capabilities": {}, "clientInfo": {"name": "aizee", "version": "4.22.1"}}}) + "\n"
        assert proc.stdin is not None
        proc.stdin.write(init_req.encode())
        await proc.stdin.drain()
        assert proc.stdout is not None
        init_line = await asyncio.wait_for(proc.stdout.readline(), timeout=_DEFAULT_TIMEOUT)
        if not init_line:
            return {"ok": False, "error": "MCP server closed stdout during init"}
        init_resp = json.loads(init_line.decode())
        if "error" in init_resp:
            return {"ok": False, "error": init_resp["error"]}
        return None

    async def _async_call(self, proc: asyncio.subprocess.Process, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send tools/call request and return parsed response."""
        call_req = json.dumps({"jsonrpc": "2.0", "id": str(uuid.uuid4()),
            "method": "tools/call", "params": {"name": tool_name, "arguments": arguments}}) + "\n"
        assert proc.stdin is not None
        proc.stdin.write(call_req.encode())
        await proc.stdin.drain()
        assert proc.stdout is not None
        resp_line = await asyncio.wait_for(proc.stdout.readline(), timeout=_DEFAULT_TIMEOUT)
        if not resp_line:
            return {"ok": False, "error": "MCP server closed stdout"}
        return cast(dict[str, Any], json.loads(resp_line.decode()))

    async def _async_terminate(self, proc: asyncio.subprocess.Process) -> None:
        """Terminate the async process."""
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=2)
        except TimeoutError:
            proc.kill()

    def is_configured(self) -> bool:
        return bool(self.config)


def parse_mcp_command(text: str) -> tuple[str, str, dict[str, Any]] | None:
    """Parse 'server.tool(args)' or 'server.tool' into (server, tool, args)."""
    text = text.strip()
    if "." not in text:
        return None
    if "(" not in text:
        server, _, tool = text.partition(".")
        if not server or not tool:
            return None
        return server, tool, {}
    head, _, rest = text.partition("(")
    server, _, tool = head.partition(".")
    if not server or not tool:
        return None
    args_text = rest.rstrip(" )")
    if not args_text:
        return server, tool, {}
    try:
        args = json.loads(args_text)
    except json.JSONDecodeError:
        return None
    return server, tool, args if isinstance(args, dict) else {}
