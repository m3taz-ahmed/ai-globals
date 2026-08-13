"""Synchronous MCP client for calling external MCP servers via stdio."""

from __future__ import annotations

import atexit
import json
import os
import queue
import shutil
import subprocess
import sysconfig
import threading
import uuid
from pathlib import Path
from typing import Any, cast

# Shared stdio process pool keyed by (server_name, os_root).  Keeps MCP server
# processes alive across multiple tool calls instead of spawning per call.
_PROC_POOL: dict[tuple[str, Path], subprocess.Popen[str]] = {}
_PROC_INIT: dict[tuple[str, Path], bool] = {}
_PROC_LOCK = threading.Lock()
_SEND_LOCKS: dict[tuple[str, Path], threading.Lock] = {}
_DEFAULT_TIMEOUT = 30.0


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


class McpClient:
    """Spawn and call tools on an MCP server defined in config.

    Processes are cached per (server, root) so repeated calls to the same
    server reuse the initialized stdio connection.
    """

    def __init__(self, server_name: str, os_root: Path) -> None:
        self.server_name = server_name
        self.os_root = os_root
        self.config = self._load_config()
        self._key = (server_name, os_root)

    def _load_config(self) -> dict[str, Any]:
        for settings_path in [self.os_root / ".claude" / "settings.json", self.os_root / "aios_mcp" / "config.json"]:
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
        env = {"AGENT_OS_ROOT": str(self.os_root), **os.environ}
        # Augment PATH with per-user Python script dirs so entry-point MCP
        # servers (e.g. installed via ``pip install --user``) resolve without
        # hardcoding machine-specific paths in config.json.
        extra_path = _user_script_dirs()
        if extra_path:
            env["PATH"] = os.pathsep.join([*extra_path, env.get("PATH", "")])
        # Some Python MCP servers expose their entry point as a top-level
        # module (e.g. ``server.py``) that is only importable from the user
        # site-packages. Add it to PYTHONPATH so ``python -c`` wrappers work.
        extra_site = _user_site_dirs()
        if extra_site:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join([*extra_site, existing]) if existing else os.pathsep.join(extra_site)
        # On Windows, CreateProcess uses the *parent* process PATH for
        # executable lookup, not the env we pass to the child. Resolve the
        # command to an absolute path via shutil.which against the augmented
        # PATH so user-installed entry points are found portably.
        resolved = shutil.which(cmd, path=env.get("PATH"))
        if resolved:
            cmd = resolved
        return subprocess.Popen(
            [cmd, *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(self.os_root),
        )

    def _send(
        self,
        proc: subprocess.Popen[str],
        payload: dict[str, Any],
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError("Process pipes not available")
        stdout = proc.stdout
        req = json.dumps(payload)
        proc.stdin.write(req + "\n")
        proc.stdin.flush()

        q: queue.Queue[str | Exception] = queue.Queue()

        def _read() -> None:
            try:
                line = stdout.readline()
                q.put(line)
            except Exception as exc:
                q.put(exc)

        reader = threading.Thread(target=_read, daemon=True)
        reader.start()
        try:
            result = q.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(
                f"MCP server '{self.server_name}' response timed out after {timeout}s"
            ) from exc
        if isinstance(result, Exception):
            raise result
        if not result:
            raise RuntimeError("MCP server closed stdout")
        return cast(dict[str, Any], json.loads(result))

    def _ensure_process(self) -> subprocess.Popen[str]:
        with _PROC_LOCK:
            proc = _PROC_POOL.get(self._key)
            if proc is None or proc.poll() is not None:
                proc = self._spawn()
                _PROC_POOL[self._key] = proc
                _PROC_INIT[self._key] = False
            if not _PROC_INIT.get(self._key):
                init_id = str(uuid.uuid4())
                init_resp = self._send(
                    proc,
                    {
                        "jsonrpc": "2.0",
                        "id": init_id,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "ai-global-os", "version": "4.22.0"},
                        },
                    },
                )
                if "error" in init_resp:
                    self._release_locked(proc)
                    raise RuntimeError(init_resp["error"])
                _PROC_INIT[self._key] = True
            return proc

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
        """Call a tool on the configured MCP server."""
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
