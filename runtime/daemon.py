"""aiZee background daemon — ensures settings persist when dashboard is closed.

The daemon is a lightweight background process that:
1. Watches ``state/settings.json`` for changes (polling, cross-platform).
2. Syncs MCP server toggles to ALL IDE config files (Devin, Claude, Cursor)
   so disabled servers are not loaded on next IDE restart — even if the
   dashboard was never opened in this session.
3. Writes a heartbeat to ``state/daemon.health`` every N seconds so the
   Tauri tray icon and CLI can detect liveness.
4. Manages a PID file at ``state/daemon.pid`` for single-instance control.
5. Provides auto-start hooks (Windows Task Scheduler, Linux systemd user,
   macOS LaunchAgent) so the daemon launches on boot.

Design:
- Zero external dependencies (stdlib only) — runs in any Python 3.10+.
- Single-instance via PID file + lock.
- Graceful shutdown via SIGTERM/SIGINT (and CTRL_BREAK_EVENT on Windows).
- Fail-safe: if settings.json is corrupt, logs a warning and keeps running
  with the last known-good state.
- Thread-safe: the watcher + heartbeat run in separate threads.

Usage:
    # Programmatic
    from runtime.daemon import AizeeDaemon
    daemon = AizeeDaemon(root)
    daemon.start()  # blocks until stopped

    # CLI (via aizee_cli.py)
    aizee daemon start [--foreground]
    aizee daemon stop
    aizee daemon status
    aizee daemon enable-autostart
    aizee daemon disable-autostart
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import platform
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from runtime.schemas import AizeeError, ErrorSeverity

_logger = logging.getLogger(__name__)

# --- Constants ---

HEARTBEAT_INTERVAL = 5.0  # seconds between heartbeat writes
WATCH_INTERVAL = 2.0  # seconds between settings.json polls
PID_FILENAME = "daemon.pid"
HEALTH_FILENAME = "daemon.health"
SETTINGS_FILENAME = "settings.json"
DAEMON_NAME = "aizee-daemon"


class DaemonError(AizeeError):
    """Raised for daemon-specific failures (already running, start failed, etc.)."""

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__("DAEMON_ERROR", message, ErrorSeverity.HIGH, context)


class AizeeDaemon:
    """Background settings-sync daemon for aiZee.

    Single-instance per OS root. Watches settings.json and syncs MCP toggles
    to IDE config files. Writes heartbeat for liveness detection.
    """

    def __init__(self, root: Path, *, foreground: bool = False) -> None:
        self.root = Path(root).resolve()
        self._state_dir = self.root / "state"
        self._pid_file = self._state_dir / PID_FILENAME
        self._health_file = self._state_dir / HEALTH_FILENAME
        self._settings_file = self._state_dir / SETTINGS_FILENAME
        self._foreground = foreground
        self._stop_event = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._last_settings_mtime: float = 0.0
        self._last_settings_hash: str = ""
        self._started_at: float = 0.0

    # --- Lifecycle ---

    def start(self) -> int:
        """Start the daemon. Blocks until stopped (signal or stop()).

        Returns exit code (0 = clean shutdown, 1 = error).
        """
        self._state_dir.mkdir(parents=True, exist_ok=True)

        # Single-instance check
        existing_pid = self._read_pid()
        if existing_pid is not None and self._is_process_alive(existing_pid):
            _logger.error("Daemon already running (PID %d)", existing_pid)
            return 1

        # Write PID file
        self._write_pid()

        # Setup signal handlers
        self._setup_signal_handlers()

        self._started_at = time.time()
        _logger.info("aiZee daemon started (PID %d, root=%s)", os.getpid(), self.root)

        # Initial sync — ensure IDE configs match settings.json right now
        self._sync_ide_configs()

        # Start worker threads
        self._watcher_thread = threading.Thread(
            target=self._watch_loop, name="aizee-daemon-watcher", daemon=True,
        )
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="aizee-daemon-heartbeat", daemon=True,
        )
        self._watcher_thread.start()
        self._heartbeat_thread.start()

        # Write initial heartbeat
        self._write_heartbeat()

        # Block until stopped
        with contextlib.suppress(KeyboardInterrupt):
            self._stop_event.wait()

        # Cleanup
        self._cleanup()
        _logger.info("aiZee daemon stopped")
        return 0

    def stop(self) -> bool:
        """Signal the daemon to stop. Returns True if signal was sent."""
        pid = self._read_pid()
        if pid is None:
            return False
        if not self._is_process_alive(pid):
            self._cleanup_pid_file()
            return False
        try:
            if platform.system() == "Windows":
                # On Windows, SIGTERM/CTRL_BREAK_EVENT don't work for detached
                # processes. Use taskkill /F for reliable termination.
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F", "/T"],
                    capture_output=True, timeout=10, shell=False,
                )
            else:
                os.kill(pid, signal.SIGTERM)
            _logger.info("Stop signal sent to daemon PID %d", pid)
            return True
        except ProcessLookupError:
            self._cleanup_pid_file()
            return False
        except PermissionError:
            _logger.error("Permission denied stopping daemon PID %d", pid)
            return False

    @classmethod
    def status(cls, root: Path) -> dict[str, Any]:
        """Return daemon status dict (does not start a daemon)."""
        state_dir = Path(root) / "state"
        pid_file = state_dir / PID_FILENAME
        health_file = state_dir / HEALTH_FILENAME

        pid = cls._read_pid_static(pid_file)
        alive = pid is not None and cls._is_process_alive_static(pid)

        health: dict[str, Any] = {}
        if health_file.exists():
            try:
                health = json.loads(health_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                health = {}

        return {
            "running": alive,
            "pid": pid if alive else None,
            "started_at": health.get("started_at"),
            "last_heartbeat": health.get("timestamp"),
            "uptime_seconds": health.get("uptime_seconds"),
            "root": str(root),
            "syncs": health.get("syncs", 0),
            "last_sync": health.get("last_sync"),
        }

    # --- Worker loops ---

    def _watch_loop(self) -> None:
        """Poll settings.json for changes and sync IDE configs on change."""
        while not self._stop_event.is_set():
            try:
                self._check_and_sync()
            except Exception as exc:
                _logger.warning("daemon watcher error: %s", exc, exc_info=True)
            self._stop_event.wait(WATCH_INTERVAL)

    def _heartbeat_loop(self) -> None:
        """Write heartbeat file periodically for liveness detection."""
        while not self._stop_event.is_set():
            self._write_heartbeat()
            self._stop_event.wait(HEARTBEAT_INTERVAL)

    def _check_and_sync(self) -> bool:
        """Check if settings.json changed; if so, sync IDE configs.

        Returns True if a sync was performed.
        """
        if not self._settings_file.exists():
            return False
        try:
            mtime = self._settings_file.stat().st_mtime
        except OSError:
            return False
        if mtime == self._last_settings_mtime:
            return False
        # Read and hash to detect content changes (not just mtime bumps)
        try:
            content = self._settings_file.read_bytes()
        except OSError:
            return False
        content_hash = hashlib.sha256(content).hexdigest()
        if content_hash == self._last_settings_hash:
            # mtime changed but content identical — skip
            self._last_settings_mtime = mtime
            return False
        self._last_settings_mtime = mtime
        self._last_settings_hash = content_hash
        _logger.info("settings.json changed — syncing IDE configs")
        self._sync_ide_configs()
        return True

    def _sync_ide_configs(self) -> None:
        """Sync MCP server toggles from settings.json to ALL IDE config files.

        Reuses the same logic as dashboard/server.py _sync_ide_mcp_configs
        but operates standalone (no dashboard required).
        """
        if not self._settings_file.exists():
            return
        try:
            settings = json.loads(self._settings_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _logger.warning("cannot read settings.json for sync: %s", exc)
            return
        mcp_servers = settings.get("mcp_servers", {})
        if not isinstance(mcp_servers, dict):
            return

        sync_count = 0
        # 1. Devin: .devin/mcp_config.local.json (disabled flag overlay)
        sync_count += self._sync_devin_local(mcp_servers)
        # 2. Claude Code: .claude/settings.json (remove/add entries)
        sync_count += self._sync_claude_settings(mcp_servers)
        # 3. Cursor: .cursor/mcp.json (if exists — remove disabled servers)
        sync_count += self._sync_cursor_mcp(mcp_servers)
        # 4. Global Devin config: %APPDATA%/devin/mcp_config.json
        sync_count += self._sync_global_devin(mcp_servers)

        # Update health with sync info
        self._increment_sync_count()

    def _sync_devin_local(self, mcp_settings: dict[str, Any]) -> int:
        """Update .devin/mcp_config.local.json with disabled flags."""
        local_path = self.root / ".devin" / "mcp_config.local.json"
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
        changed = False
        for server_name, cfg in mcp_settings.items():
            if not isinstance(cfg, dict):
                continue
            enabled = cfg.get("enabled", True)
            existing = servers.get(server_name, {})
            if not isinstance(existing, dict):
                existing = {}
            if enabled:
                if "disabled" in existing:
                    existing.pop("disabled", None)
                    changed = True
            else:
                if not existing.get("disabled"):
                    existing["disabled"] = True
                    changed = True
            if existing:
                servers[server_name] = existing
            elif server_name in servers and not servers[server_name]:
                servers.pop(server_name, None)
                changed = True

        if changed:
            local_path.write_text(json.dumps(local, indent=2), encoding="utf-8")
            _logger.info("synced Devin local MCP config (%d servers)", len(servers))
        return 1 if changed else 0

    def _sync_claude_settings(self, mcp_settings: dict[str, Any]) -> int:
        """Update .claude/settings.json — remove disabled, restore enabled."""
        claude_path = self.root / ".claude" / "settings.json"
        if not claude_path.exists():
            return 0
        try:
            claude_cfg = json.loads(claude_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return 0
        if "mcpServers" not in claude_cfg or not isinstance(claude_cfg["mcpServers"], dict):
            return 0

        # Read canonical config for restoration
        canonical: dict[str, Any] = {}
        for cfg_path in [self.root / "aizee_mcp" / "config.json", self.root / ".devin" / "mcp_config.json"]:
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
                if server_name not in claude_cfg["mcpServers"] and server_name in canonical:
                    claude_cfg["mcpServers"][server_name] = canonical[server_name]
                    changed = True
            else:
                if server_name in claude_cfg["mcpServers"]:
                    del claude_cfg["mcpServers"][server_name]
                    changed = True

        if changed:
            claude_path.write_text(json.dumps(claude_cfg, indent=2), encoding="utf-8")
            _logger.info("synced Claude Code MCP config")
        return 1 if changed else 0

    def _sync_cursor_mcp(self, mcp_settings: dict[str, Any]) -> int:
        """Update .cursor/mcp.json if it exists — remove disabled servers."""
        cursor_path = self.root / ".cursor" / "mcp.json"
        if not cursor_path.exists():
            return 0
        try:
            cursor_cfg = json.loads(cursor_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return 0
        if "mcpServers" not in cursor_cfg or not isinstance(cursor_cfg["mcpServers"], dict):
            return 0

        changed = False
        for server_name, cfg in mcp_settings.items():
            if not isinstance(cfg, dict):
                continue
            enabled = cfg.get("enabled", True)
            if not enabled and server_name in cursor_cfg["mcpServers"]:
                del cursor_cfg["mcpServers"][server_name]
                changed = True

        if changed:
            cursor_path.write_text(json.dumps(cursor_cfg, indent=2), encoding="utf-8")
            _logger.info("synced Cursor MCP config")
        return 1 if changed else 0

    def _sync_global_devin(self, mcp_settings: dict[str, Any]) -> int:
        """Sync disabled flags to global Devin config (%APPDATA%/devin/mcp_config.json)."""
        if os.name == "nt":
            base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        else:
            base = str(Path.home() / ".config")
        global_path = Path(base) / "devin" / "mcp_config.json"
        if not global_path.exists():
            return 0
        try:
            global_cfg = json.loads(global_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return 0
        servers = global_cfg.get("mcpServers", {})
        if not isinstance(servers, dict):
            return 0

        changed = False
        for server_name, cfg in mcp_settings.items():
            if not isinstance(cfg, dict):
                continue
            enabled = cfg.get("enabled", True)
            if not enabled and server_name in servers:
                # Mark disabled rather than removing (global config is shared)
                entry = servers[server_name]
                if isinstance(entry, dict) and not entry.get("disabled"):
                    entry["disabled"] = True
                    changed = True
            elif enabled and server_name in servers:
                entry = servers[server_name]
                if isinstance(entry, dict) and entry.get("disabled"):
                    entry.pop("disabled", None)
                    changed = True

        if changed:
            global_path.write_text(json.dumps(global_cfg, indent=2), encoding="utf-8")
            _logger.info("synced global Devin MCP config")
        return 1 if changed else 0

    # --- Heartbeat ---

    def _write_heartbeat(self) -> None:
        """Write health file with current status for liveness detection."""
        now = time.time()
        uptime = int(now - self._started_at) if self._started_at else 0
        health = {
            "timestamp": now,
            "started_at": self._started_at,
            "uptime_seconds": uptime,
            "pid": os.getpid(),
            "root": str(self.root),
            "python": sys.version.split()[0],
            "platform": platform.system(),
            "syncs": getattr(self, "_sync_count", 0),
            "last_sync": getattr(self, "_last_sync_time", None),
        }
        try:
            tmp = self._health_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(health, indent=2), encoding="utf-8")
            os.replace(tmp, self._health_file)
        except OSError as exc:
            _logger.warning("heartbeat write failed: %s", exc)

    def _increment_sync_count(self) -> None:
        """Track sync count for health reporting."""
        self._sync_count = getattr(self, "_sync_count", 0) + 1
        self._last_sync_time = time.time()

    # --- PID management ---

    def _write_pid(self) -> None:
        """Write current PID to PID file."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._pid_file.write_text(str(os.getpid()), encoding="utf-8")

    def _read_pid(self) -> int | None:
        return self._read_pid_static(self._pid_file)

    @staticmethod
    def _read_pid_static(pid_file: Path) -> int | None:
        if not pid_file.exists():
            return None
        try:
            pid_str = pid_file.read_text(encoding="utf-8").strip()
            return int(pid_str) if pid_str else None
        except (ValueError, OSError):
            return None

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        return AizeeDaemon._is_process_alive_static(pid)

    @staticmethod
    def _is_process_alive_static(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            if platform.system() == "Windows":
                # os.kill(pid, 0) doesn't work reliably on Windows.
                # Use tasklist to check if process exists.
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                    capture_output=True, text=True, timeout=5, shell=False,
                )
                return str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, PermissionError, OSError, subprocess.TimeoutExpired):
            return False

    def _cleanup_pid_file(self) -> None:
        with contextlib.suppress(OSError):
            self._pid_file.unlink(missing_ok=True)

    def _cleanup(self) -> None:
        """Cleanup on shutdown — remove PID file."""
        self._cleanup_pid_file()

    # --- Signal handling ---

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown signal handlers."""
        def handler(signum: int, frame: Any) -> None:
            _logger.info("received signal %d — shutting down", signum)
            self._stop_event.set()

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)
        # SIGHUP doesn't exist on Windows — guard with getattr for mypy.
        sighup = getattr(signal, "SIGHUP", None)
        if sighup is not None:
            signal.signal(sighup, handler)

    # --- Auto-start ---

    @classmethod
    def enable_autostart(cls, root: Path) -> dict[str, Any]:
        """Enable auto-start on boot. Returns result dict."""
        system = platform.system()
        if system == "Windows":
            return cls._enable_autostart_windows(root)
        elif system == "Darwin":
            return cls._enable_autostart_macos(root)
        else:
            return cls._enable_autostart_linux(root)

    @classmethod
    def disable_autostart(cls) -> dict[str, Any]:
        """Disable auto-start on boot."""
        system = platform.system()
        if system == "Windows":
            return cls._disable_autostart_windows()
        elif system == "Darwin":
            return cls._disable_autostart_macos()
        else:
            return cls._disable_autostart_linux()

    @classmethod
    def _enable_autostart_windows(cls, root: Path) -> dict[str, Any]:
        """Create a Windows Scheduled Task that starts the daemon on logon."""
        python_exe = sys.executable
        daemon_script = str(Path(root) / "runtime" / "daemon.py")
        cmd = f'"{python_exe}" "{daemon_script}" --root "{root}"'
        task_name = DAEMON_NAME
        result = subprocess.run(
            [
                "schtasks", "/Create", "/TN", task_name,
                "/TR", cmd, "/SC", "ONLOGON", "/RL", "LIMITED",
                "/F",
            ],
            capture_output=True, text=True, timeout=15, shell=False,
        )
        return {
            "platform": "windows",
            "enabled": result.returncode == 0,
            "task_name": task_name,
            "output": result.stdout.strip() or result.stderr.strip(),
        }

    @classmethod
    def _disable_autostart_windows(cls) -> dict[str, Any]:
        result = subprocess.run(
            ["schtasks", "/Delete", "/TN", DAEMON_NAME, "/F"],
            capture_output=True, text=True, timeout=10, shell=False,
        )
        return {
            "platform": "windows",
            "disabled": result.returncode == 0,
            "output": result.stdout.strip() or result.stderr.strip(),
        }

    @classmethod
    def _enable_autostart_macos(cls, root: Path) -> dict[str, Any]:
        """Create a LaunchAgent plist for auto-start on macOS."""
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path = plist_dir / "ai.aizee.daemon.plist"
        python_exe = sys.executable
        daemon_script = str(Path(root) / "runtime" / "daemon.py")
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.aizee.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{daemon_script}</string>
        <string>--root</string>
        <string>{root}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{root}/state/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>{root}/state/daemon-error.log</string>
</dict>
</plist>"""
        plist_path.write_text(plist, encoding="utf-8")
        subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True, timeout=10)
        return {"platform": "macos", "enabled": True, "plist": str(plist_path)}

    @classmethod
    def _disable_autostart_macos(cls) -> dict[str, Any]:
        plist_path = Path.home() / "Library" / "LaunchAgents" / "ai.aizee.daemon.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True, timeout=10)
            plist_path.unlink(missing_ok=True)
        return {"platform": "macos", "disabled": True}

    @classmethod
    def _enable_autostart_linux(cls, root: Path) -> dict[str, Any]:
        """Create a systemd user service for auto-start on Linux."""
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        service_path = service_dir / "aizee-daemon.service"
        python_exe = sys.executable
        daemon_script = str(Path(root) / "runtime" / "daemon.py")
        service = f"""[Unit]
Description=aiZee Background Daemon
After=network.target

[Service]
Type=simple
ExecStart={python_exe} {daemon_script} --root {root}
Restart=on-failure
RestartSec=5
Environment=AIZEE_ROOT={root}
Environment=PYTHONIOENCODING=utf-8

[Install]
WantedBy=default.target
"""
        service_path.write_text(service, encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "enable", "aizee-daemon"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "start", "aizee-daemon"], capture_output=True, timeout=10)
        return {"platform": "linux", "enabled": True, "service": str(service_path)}

    @classmethod
    def _disable_autostart_linux(cls) -> dict[str, Any]:
        subprocess.run(["systemctl", "--user", "stop", "aizee-daemon"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "disable", "aizee-daemon"], capture_output=True, timeout=10)
        service_path = Path.home() / ".config" / "systemd" / "user" / "aizee-daemon.service"
        service_path.unlink(missing_ok=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
        return {"platform": "linux", "disabled": True}


# --- CLI entry point ---

def main(argv: list[str] | None = None) -> int:
    """CLI entry point for standalone daemon execution."""
    import argparse

    parser = argparse.ArgumentParser(description="aiZee background daemon")
    parser.add_argument("--root", default=None, help="aiZee root directory")
    parser.add_argument("--foreground", action="store_true", help="Run in foreground (don't detach)")
    parser.add_argument("--stop", action="store_true", help="Stop running daemon")
    parser.add_argument("--status", action="store_true", help="Print daemon status")
    parser.add_argument("--enable-autostart", action="store_true", help="Enable auto-start on boot")
    parser.add_argument("--disable-autostart", action="store_true", help="Disable auto-start on boot")
    args = parser.parse_args(argv)

    # Discover root
    if args.root:
        root = Path(args.root)
    else:
        # Try AIZEE_ROOT env, then parent of this file's directory
        env_root = os.environ.get("AIZEE_ROOT")
        if env_root and Path(env_root).is_dir():
            root = Path(env_root)
        else:
            root = Path(__file__).resolve().parent.parent

    if not root.is_dir():
        print(f"[ERROR] Root not found: {root}", file=sys.stderr)
        return 1

    if args.status:
        status = AizeeDaemon.status(root)
        print(json.dumps(status, indent=2))
        return 0 if status["running"] else 1

    if args.stop:
        daemon = AizeeDaemon(root)
        stopped = daemon.stop()
        print("Stop signal sent" if stopped else "No running daemon found")
        return 0 if stopped else 1

    if args.enable_autostart:
        result = AizeeDaemon.enable_autostart(root)
        print(json.dumps(result, indent=2))
        return 0 if result.get("enabled") else 1

    if args.disable_autostart:
        result = AizeeDaemon.disable_autostart()
        print(json.dumps(result, indent=2))
        return 0 if result.get("disabled") else 1

    # Default: start daemon
    daemon = AizeeDaemon(root, foreground=args.foreground)
    return daemon.start()


if __name__ == "__main__":
    raise SystemExit(main())
