"""MCP client for calling external MCP servers via stdio.

Provides both synchronous (threading-based) and asynchronous (asyncio) interfaces.
The async interface uses asyncio.subprocess for non-blocking I/O.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import queue
import subprocess
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
            if proc is not None and proc.poll() is not None:
                # Reap the dead process to prevent zombie accumulation.
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                proc = None
            if proc is None:
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
                            "clientInfo": {"name": "ai-global-os", "version": "4.22.1"},
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

    async def async_call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Async version of call_tool using asyncio.subprocess.

        Spawns a fresh process per call (no pooling) for isolation.
        Suitable for async contexts where blocking I/O is undesirable.
        """
        if not self.config:
            return {"ok": False, "error": f"MCP server '{self.server_name}' not configured"}
        cmd = self.config["command"]
        args = self.config.get("args", [])
        env = {"AGENT_OS_ROOT": str(self.os_root), **os.environ}
        try:
            proc = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(self.os_root),
            )
        except Exception as exc:
            return {"ok": False, "error": f"Failed to spawn MCP server: {exc}"}

        try:
            # Initialize
            init_id = str(uuid.uuid4())
            init_req = json.dumps({
                "jsonrpc": "2.0",
                "id": init_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "ai-global-os", "version": "4.22.1"},
                },
            }) + "\n"
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

            # Call tool
            call_id = str(uuid.uuid4())
            call_req = json.dumps({
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }) + "\n"
            proc.stdin.write(call_req.encode())
            await proc.stdin.drain()
            resp_line = await asyncio.wait_for(proc.stdout.readline(), timeout=_DEFAULT_TIMEOUT)
            if not resp_line:
                return {"ok": False, "error": "MCP server closed stdout"}
            resp = json.loads(resp_line.decode())
        except asyncio.TimeoutError:
            return {"ok": False, "error": f"MCP server '{self.server_name}' timed out"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                proc.kill()
        if "error" in resp:
            return {"ok": False, "error": resp["error"]}
        return {"ok": True, "result": resp.get("result")}

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
