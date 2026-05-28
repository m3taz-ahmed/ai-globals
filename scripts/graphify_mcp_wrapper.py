"""
Graphify MCP Wrapper — Dynamic Workspace Detection
====================================================
This wrapper intercepts the MCP 'initialize' JSON-RPC message on stdin,
extracts the workspace path, changes the working directory to it,
then replays the buffered messages and proxies the rest of stdin to
the real graphify MCP server.

Because graphify's serve() uses a default relative graph_path of
"graphify-out/graph.json", chdir() to the workspace root is sufficient
to make it pick up the right graph for any project.

The interception works at the OS file-descriptor level so it is compatible
with graphify's own _filter_blank_stdin() which also rewires fd 0.

Protocol: MCP stdio uses plain JSON lines (one JSON-RPC message per line).
"""

import sys
import os
import json
import urllib.parse
import threading
import logging
from pathlib import Path

# Set up debug logging to a file (always useful for diagnosing MCP issues)
_LOG_PATH = Path(os.environ.get("GRAPHIFY_WRAPPER_LOG", 
    Path.home() / ".graphify" / "wrapper_debug.log"))
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("graphify_wrapper")


def _uri_to_path(uri: str) -> str | None:
    """Convert a file:// URI to a local filesystem path."""
    if not uri.startswith("file:///"):
        return None
    path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    # Windows: /C:/foo → C:/foo
    if len(path) > 2 and path[0] == "/" and path[2] == ":":
        path = path[1:]
    return path


def _extract_workspace_from_initialize(line: bytes) -> str | None:
    """Parse a JSON-RPC line and return the workspace path if it's 'initialize'."""
    text = line.strip()
    if not text:
        return None
    try:
        msg = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None

    if msg.get("method") != "initialize":
        return None

    log.info("Got initialize message: %s", json.dumps(msg, indent=2, default=str)[:2000])

    params = msg.get("params", {})

    # === Strategy 1: MCP 'roots' (MCP spec standard) ===
    # MCP clients can send roots in capabilities
    roots = params.get("roots") or []
    if not roots:
        # Some clients put it in capabilities.roots
        roots = (params.get("capabilities", {}).get("roots", {}).get("roots", []))
    for root in roots:
        uri = root.get("uri", "") if isinstance(root, dict) else str(root)
        path = _uri_to_path(uri)
        if path and os.path.isdir(path):
            log.info("Found workspace from MCP roots: %s", path)
            return path

    # === Strategy 2: LSP-style rootUri (some clients still send this) ===
    root_uri = params.get("rootUri") or ""
    path = _uri_to_path(root_uri)
    if path and os.path.isdir(path):
        log.info("Found workspace from rootUri: %s", path)
        return path

    # === Strategy 3: Legacy rootPath ===
    root_path = params.get("rootPath") or ""
    if root_path and os.path.isabs(root_path) and os.path.isdir(root_path):
        log.info("Found workspace from rootPath: %s", root_path)
        return root_path

    # === Strategy 4: workspaceFolders array ===
    folders = params.get("workspaceFolders") or []
    for folder in folders:
        uri = folder.get("uri", "")
        path = _uri_to_path(uri)
        if path and os.path.isdir(path):
            log.info("Found workspace from workspaceFolders: %s", path)
            return path

    # === Strategy 5: clientInfo or processId-based detection ===
    # Some IDE clients include workspaceFolder info in clientInfo
    client_info = params.get("clientInfo", {})
    log.info("clientInfo: %s", client_info)

    log.info("os.environ: %s", json.dumps(dict(os.environ), indent=2))

    log.warning("Could not extract workspace from initialize message")
    return None


def _install_intercept_pipe():
    """
    Install an OS-level pipe on fd 0 (stdin).
    
    We read from the *original* stdin in a background thread, intercept
    the first 'initialize' message to extract the workspace path, then
    relay all messages (including the initialize) through the pipe to
    the new fd 0 that graphify will read from.
    
    This works at the fd level so it is fully compatible with graphify's
    own _filter_blank_stdin() which also manipulates fd 0.
    """
    log.info("Starting graphify MCP wrapper, cwd=%s, pid=%d", os.getcwd(), os.getpid())

    # Save the original stdin fd
    original_fd = os.dup(sys.stdin.buffer.fileno())

    # Create a new pipe: graphify will read from r_fd (which we'll dup2 onto fd 0)
    r_fd, w_fd = os.pipe()

    workspace_found = threading.Event()
    workspace_path = [None]  # mutable container for thread result

    def _relay():
        """Read from original stdin, intercept initialize, relay everything."""
        try:
            with open(original_fd, "rb", closefd=True) as src, \
                 open(w_fd, "wb", closefd=True) as dst:
                found = False
                for line in src:
                    log.debug("stdin line: %s", line[:300])

                    # Try to extract workspace from initialize (only before we find it)
                    if not found:
                        ws = _extract_workspace_from_initialize(line)
                        if ws is not None:
                            workspace_path[0] = ws
                            found = True
                            workspace_found.set()
                        elif b'"initialize"' in line:
                            # Saw initialize but couldn't extract workspace
                            found = True
                            workspace_found.set()

                    # Always relay the line (including initialize itself)
                    dst.write(line)
                    dst.flush()
        except Exception as exc:
            log.error("Relay thread error: %s", exc, exc_info=True)
        finally:
            workspace_found.set()  # unblock main thread even on error

    relay_thread = threading.Thread(target=_relay, daemon=True)
    relay_thread.start()

    # Wait for the initialize message (with timeout to avoid hanging forever)
    workspace_found.wait(timeout=30)

    ws = workspace_path[0]
    if ws and os.path.isdir(ws):
        log.info("Changing working directory to: %s", ws)
        os.chdir(ws)
        os.environ["GRAPHIFY_WORKSPACE"] = ws
    else:
        # Fallback to the script's grandparent directory (assuming script is in workspace/scripts/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fallback_ws = os.path.dirname(script_dir)
        log.warning("No workspace detected from MCP protocol, using script's parent directory as fallback: %s", fallback_ws)
        os.chdir(fallback_ws)
        os.environ["GRAPHIFY_WORKSPACE"] = fallback_ws

    # Now replace fd 0 with our pipe's read end
    os.dup2(r_fd, 0)
    os.close(r_fd)

    # Rewrap sys.stdin so Python sees the new fd 0
    sys.stdin = open(0, "r", encoding="utf-8", errors="replace", closefd=False)

    log.info("Wrapper setup complete, final cwd=%s", os.getcwd())


if __name__ == "__main__":
    _install_intercept_pipe()

    # Now start graphify — it will read from the intercepted fd 0
    # which already has the initialize message queued up
    from graphify.serve import serve
    serve()
