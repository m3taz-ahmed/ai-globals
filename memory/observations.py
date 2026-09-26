"""Observation memory - continuous capture of agent activity.

Implements the capture -> compress -> inject loop (architectural pattern
adapted from the claude-mem project): IDE lifecycle hooks feed tool events
into a crash-safe pending queue; events are deduplicated and stored as
compact observations; at prompt time a small markdown block of recent
observations is produced for context injection.

Storage is a standalone SQLite database (``state/observations.db`` under
the project root) so its schema stays independent of ``memory.store``.
Hooks must never block the editor: :func:`handle_hook` swallows every
failure and the CLI always exits 0.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.schemas import StorageError, ValidationError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    tool TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    paths TEXT NOT NULL DEFAULT '[]',
    content_hash TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);
CREATE INDEX IF NOT EXISTS idx_obs_time ON observations(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_obs_hash ON observations(content_hash);
CREATE TABLE IF NOT EXISTS pending_events (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""

KIND_PROMPT = "prompt"
KIND_FILE_EDIT = "file_edit"
KIND_SHELL = "shell"
KIND_MCP = "mcp"
KIND_SESSION_START = "session_start"
KIND_SESSION_END = "session_end"
KINDS = frozenset(
    {KIND_PROMPT, KIND_FILE_EDIT, KIND_SHELL, KIND_MCP, KIND_SESSION_START, KIND_SESSION_END}
)

_EVENT_KINDS: dict[str, str] = {
    "beforeSubmitPrompt": KIND_PROMPT,
    "afterFileEdit": KIND_FILE_EDIT,
    "afterShellExecution": KIND_SHELL,
    "afterMCPExecution": KIND_MCP,
    "sessionInit": KIND_SESSION_START,
    "session-init": KIND_SESSION_START,
    "stop": KIND_SESSION_END,
}

_PATH_KEYS = frozenset(
    {"file_path", "filePath", "filepath", "path", "file", "filename", "target_file", "targetFile"}
)
_SESSION_KEYS = ("session_id", "sessionId", "conversation_id", "conversationId", "generationId")

MAX_TITLE = 160
MAX_DETAIL = 2000
MAX_PATHS = 10
MAX_PAYLOAD_CHARS = 4000
DEFAULT_DB = "state/observations.db"


@dataclass(frozen=True)
class Observation:
    """A single compressed record of agent activity."""

    id: str
    session_id: str
    kind: str
    tool: str
    title: str
    detail: str
    paths: tuple[str, ...]
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "kind": self.kind,
            "tool": self.tool,
            "title": self.title,
            "detail": self.detail,
            "paths": list(self.paths),
            "created_at": self.created_at,
        }

    @staticmethod
    def from_row(row: tuple[Any, ...]) -> Observation:
        return Observation(
            id=str(row[0]),
            session_id=str(row[1]),
            kind=str(row[2]),
            tool=str(row[3]),
            title=str(row[4]),
            detail=str(row[5]),
            paths=tuple(json.loads(str(row[6]))),
            created_at=float(row[7]),
        )


def _clip(text: Any, limit: int) -> str:
    s = str(text).strip()
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


def session_id_of(payload: dict[str, Any]) -> str:
    """Best-effort session id from a hook payload (field names vary by IDE)."""
    for key in _SESSION_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return "default"


def _extract_paths(value: Any, out: list[str], depth: int = 0) -> None:
    if depth > 4 or len(out) >= MAX_PATHS:
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if len(out) >= MAX_PATHS:
                return
            if key in _PATH_KEYS and isinstance(item, str) and item:
                if item not in out:
                    out.append(item)
            else:
                _extract_paths(item, out, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _extract_paths(item, out, depth + 1)


def _tool_of(payload: dict[str, Any]) -> str:
    for key in ("tool_name", "toolName", "tool", "command"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def summarize_event(event: str, payload: dict[str, Any]) -> tuple[str, str, str, tuple[str, ...], str]:
    """Compress a raw hook payload into (title, detail, tool, paths, kind)."""
    kind = _EVENT_KINDS.get(event, event if event in KINDS else KIND_PROMPT)
    tool = _tool_of(payload)
    paths: list[str] = []
    _extract_paths(payload, paths)
    if kind == KIND_FILE_EDIT:
        title = f"Edited {paths[0] if paths else 'file'}"
    elif kind == KIND_SHELL:
        title = f"Ran {_clip(payload.get('command') or payload.get('cmd') or tool or 'command', 80)}"
    elif kind == KIND_MCP:
        title = f"MCP {_clip(tool or payload.get('method') or 'call', 80)}"
    elif kind == KIND_PROMPT:
        title = f"Prompt: {_clip(payload.get('prompt') or payload.get('text') or '', 100)}"
    else:
        title = _clip(event.replace("_", " ").replace("-", " "), MAX_TITLE)
    raw = json.dumps(payload, default=str, ensure_ascii=False) if payload else ""
    detail = _clip(raw, MAX_DETAIL)
    return _clip(title, MAX_TITLE), detail, tool, tuple(paths[:MAX_PATHS]), kind


def _content_hash(session_id: str, kind: str, tool: str, title: str, detail: str) -> str:
    raw = "\x00".join((session_id, kind, tool, title, detail))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ObservationStore:
    """Crash-safe pending queue + deduplicated observation store (SQLite)."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise StorageError(f"cannot init observations db: {exc}") from exc

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # -- pending queue -----------------------------------------------------

    def enqueue(self, session_id: str, event: str, payload: dict[str, Any]) -> str:
        """Stage a raw event before processing so a failure never loses it."""
        if not session_id or not event:
            raise ValidationError("session_id and event are required")
        row_id = uuid.uuid4().hex
        body = _clip(json.dumps(payload, default=str, ensure_ascii=False), MAX_PAYLOAD_CHARS)
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO pending_events VALUES (?,?,?,?,?)",
                    (row_id, session_id, event, body, time.time()),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"enqueue failed: {exc}") from exc
        return row_id

    def pending(self, session_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT id, session_id, event, payload FROM pending_events"
        params: tuple[Any, ...] = ()
        if session_id is not None:
            sql += " WHERE session_id = ?"
            params = (session_id,)
        sql += " ORDER BY created_at"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            try:
                payload = json.loads(row[3])
            except (json.JSONDecodeError, TypeError):
                payload = {}
            out.append({"id": row[0], "session_id": row[1], "event": row[2], "payload": payload})
        return out

    def _drop_pending(self, conn: sqlite3.Connection, row_id: str) -> None:
        conn.execute("DELETE FROM pending_events WHERE id = ?", (row_id,))

    # -- recording ----------------------------------------------------------

    def record(
        self,
        session_id: str,
        kind: str,
        tool: str,
        title: str,
        detail: str,
        paths: tuple[str, ...] = (),
    ) -> Observation | None:
        """Insert an observation. Returns ``None`` when it is a duplicate."""
        if kind not in KINDS:
            raise ValidationError(f"unknown observation kind: {kind}", {"kind": kind})
        digest = _content_hash(session_id, kind, tool, title, detail)
        obs = Observation(
            id=uuid.uuid4().hex,
            session_id=session_id,
            kind=kind,
            tool=tool,
            title=title,
            detail=detail,
            paths=paths,
            created_at=time.time(),
        )
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        obs.id,
                        obs.session_id,
                        obs.kind,
                        obs.tool,
                        obs.title,
                        obs.detail,
                        json.dumps(list(obs.paths)),
                        digest,
                        obs.created_at,
                    ),
                )
        except sqlite3.Error as exc:
            raise StorageError(f"record failed: {exc}") from exc
        return obs if cur.rowcount else None

    def record_event(self, session_id: str, event: str, payload: dict[str, Any]) -> Observation | None:
        """Stage then compress+store one hook event; retries queued leftovers."""
        self.enqueue(session_id, event, payload)
        processed = self.process_pending(session_id)
        return processed[-1] if processed else None

    def process_pending(self, session_id: str | None = None) -> list[Observation]:
        """Compress queued events into observations; drops each row it stores."""
        out: list[Observation] = []
        for row in self.pending(session_id):
            title, detail, tool, paths, kind = summarize_event(row["event"], row["payload"])
            obs = self.record(row["session_id"], kind, tool, title, detail, paths)
            with self._connect() as conn:
                self._drop_pending(conn, row["id"])
            if obs is not None:
                out.append(obs)
        return out

    # -- retrieval -----------------------------------------------------------

    _COLS = "id, session_id, kind, tool, title, detail, paths, created_at"

    def recent(self, limit: int = 20, session_id: str | None = None) -> list[Observation]:
        sql = f"SELECT {self._COLS} FROM observations"
        params: tuple[Any, ...] = ()
        if session_id is not None:
            sql += " WHERE session_id = ?"
            params = (session_id,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        with self._connect() as conn:
            rows = conn.execute(sql, (*params, limit)).fetchall()
        return [Observation.from_row(r) for r in rows]

    def search(self, query: str, limit: int = 20) -> list[Observation]:
        like = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {self._COLS} FROM observations"
                " WHERE title LIKE ? OR detail LIKE ? OR paths LIKE ?"
                " ORDER BY created_at DESC LIMIT ?",
                (like, like, like, limit),
            ).fetchall()
        return [Observation.from_row(r) for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0])

    # -- context injection ----------------------------------------------------

    def context_block(
        self, session_id: str | None = None, limit: int = 10, query: str | None = None
    ) -> str:
        """Markdown block of recent observations for prompt-time injection."""
        obs = self.search(query, limit) if query else self.recent(limit, session_id)
        if not obs:
            return ""
        lines = ["### Recent observations"]
        for o in obs:
            stamp = time.strftime("%H:%M", time.localtime(o.created_at))
            suffix = f" ({', '.join(o.paths[:3])})" if o.paths else ""
            lines.append(f"- [{stamp}] {o.title}{suffix}")
        return "\n".join(lines)

    def session_summary(self, session_id: str) -> dict[str, Any]:
        """Aggregate stats for one session (used by the ``stop`` hook)."""
        with self._connect() as conn:
            total = int(
                conn.execute(
                    "SELECT COUNT(*) FROM observations WHERE session_id = ?", (session_id,)
                ).fetchone()[0]
            )
            kinds = dict(
                conn.execute(
                    "SELECT kind, COUNT(*) FROM observations WHERE session_id = ? GROUP BY kind",
                    (session_id,),
                ).fetchall()
            )
            bounds = conn.execute(
                "SELECT MIN(created_at), MAX(created_at) FROM observations WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        duration = (bounds[1] - bounds[0]) if total and bounds[0] is not None else 0.0
        return {"session_id": session_id, "observations": total, "kinds": kinds, "duration_s": round(duration, 1)}


def default_db_path(project_root: Path) -> Path:
    return Path(project_root) / DEFAULT_DB


def handle_hook(
    action: str, project_root: Path, payload: dict[str, Any], kind: str = "", event: str = ""
) -> str:
    """Entry point for ``aizee hook <action>``. Returns text to print; never raises."""
    try:
        store = ObservationStore(default_db_path(project_root))
        session_id = session_id_of(payload)
        if action == "inject":
            query = payload.get("prompt") or payload.get("text")
            block = store.context_block(
                session_id=session_id, query=query if isinstance(query, str) else None
            )
            contract = _task_contract_block(project_root)
            return "\n\n".join(part for part in (contract, block) if part)
        if action == "observe":
            store.enqueue(session_id, event or kind or "event", payload)
            store.process_pending(session_id)
            warning = _task_contract_scope_warning(project_root, payload, event or kind)
            if warning:
                store.enqueue(session_id, "scope_violation", {"warning": warning})
                store.process_pending(session_id)
                return warning
        elif action == "summary":
            summary = store.session_summary(session_id)
            if summary["observations"]:
                kinds = ", ".join(f"{k}:{v}" for k, v in sorted(summary["kinds"].items()))
                return f"Session summary: {summary['observations']} observations ({kinds}) in {summary['duration_s']}s"
        return ""
    except Exception:
        return ""


def _task_contract_block(project_root: Path) -> str:
    """Active task-plan status for prompt injection. Never raises."""
    try:
        from runtime.task_contract import TaskContractManager

        return TaskContractManager(project_root).hook_inject_block()
    except Exception:
        return ""


def _task_contract_scope_warning(
    project_root: Path, payload: dict[str, Any], event: str
) -> str:
    """After-file-edit scope check against the active contract task."""
    kind = _EVENT_KINDS.get(event, event if event in KINDS else "")
    if kind != KIND_FILE_EDIT:
        return ""
    paths: list[str] = []
    _extract_paths(payload, paths)
    if not paths:
        return ""
    try:
        from runtime.task_contract import TaskContractManager

        mgr = TaskContractManager(project_root)
        warnings = [w for w in (mgr.hook_observe_edit(p) for p in paths) if w]
        return "\n".join(warnings)
    except Exception:
        return ""
