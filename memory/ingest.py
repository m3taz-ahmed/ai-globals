#!/usr/bin/env python3
"""Ingest rules, tech-stack, workflows, skills, and AGENTS.md into memory."""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import config

from .store import Memory, MemoryStore, _deterministic_id

_AI_TITLE_TAGS = ("[FILE]", "[TECH]", "[WORKFLOW]", "[SKILL]")
_MAX_INGEST_BYTES = 500_000  # skip files larger than this (OOM guard)

# (source_prefix, kind, recursive)
_TRACKED: tuple[tuple[str, str, bool], ...] = (
    ("rules", "semantic", False),
    ("tech-stack", "factual", False),
    ("workflows", "procedural", False),
    ("skills", "procedural", True),
)


class Ingestor:
    """Incrementally loads canonical Markdown files into the memory store."""

    def __init__(self, store: MemoryStore, root: Path | None = None) -> None:
        self.store = store
        self.root = root or config.discover_root()
        self.manifest_path = self.root / "brain" / "ingest_manifest.json"

    def _load_manifest(self) -> dict[str, str]:
        if self.manifest_path.exists():
            try:
                data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except (ValueError, OSError, UnicodeDecodeError):
                return {}
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        return {}

    def _save_manifest(self, manifest: dict[str, str]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        tmp.replace(self.manifest_path)

    @staticmethod
    def _sig(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _body_after_frontmatter(content: str) -> str:
        if content.startswith("---") and "---" in content[3:]:
            parts = content.split("---", 2)
            if len(parts) >= 3 and "\nname:" in parts[1]:
                return parts[2]
        return content

    def _is_ai_file(self, content: str) -> bool:
        body = self._body_after_frontmatter(content)
        stripped = body.lstrip() if body else ""
        first = stripped.splitlines()[0].strip() if stripped else ""
        return any(first.startswith(tag) for tag in _AI_TITLE_TAGS)

    def _validate(self, content: str, source: str) -> bool:
        if not self._is_ai_file(content):
            return True
        if "[OBJ]" not in content or "[RULES]" not in content:
            warnings.warn(f"Skipping malformed AI file {source}: missing [OBJ] or [RULES]", stacklevel=2)
            return False
        return True

    def _memory(self, source: str, kind: str, content: str) -> Memory:
        now = datetime.now(timezone.utc).isoformat()
        # Deterministic id (not uuid4): if the manifest is lost, re-ingest
        # maps to the same rows and INSERT OR IGNORE dedups instead of
        # duplicating every file.
        return Memory(
            id=_deterministic_id(content, kind, source),
            kind=kind,
            content=content,
            source=source,
            meta=json.dumps({}),
            created_at=now,
            valid_from=now,
            valid_to=None,
        )

    def _read_tracked(self, p: Path) -> str | None:
        """Read a tracked file with size cap + symlink containment. None = skip."""
        try:
            if p.stat().st_size > _MAX_INGEST_BYTES:
                warnings.warn(f"Skipping oversize ingest file {p} (>500KB)", stacklevel=2)
                return None
            resolved = p.resolve()
            resolved.relative_to(self.root.resolve())
        except (OSError, ValueError):
            return None
        try:
            return resolved.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _collect_dir(
        self,
        source_prefix: str,
        kind: str,
        recursive: bool,
        manifest: dict[str, str],
    ) -> tuple[list[Memory], dict[str, str], set[str]]:
        dir_path = self.root / source_prefix
        if not dir_path.is_dir():
            return [], {}, set()

        globber = dir_path.rglob("*.md") if recursive else dir_path.glob("*.md")
        to_add: list[Memory] = []
        new_sigs: dict[str, str] = {}
        current_sources: set[str] = set()

        for p in sorted(globber):
            if not p.is_file():
                continue
            rel = p.relative_to(dir_path)
            source = f"{source_prefix}/{rel.as_posix()}"
            content = self._read_tracked(p)
            if content is None:
                continue
            if not self._validate(content, source):
                continue
            sig = self._sig(content)
            current_sources.add(source)
            new_sigs[source] = sig
            if manifest.get(source) == sig:
                continue
            to_add.append(self._memory(source, kind, content))

        return to_add, new_sigs, current_sources

    def _collect_agents(self, manifest: dict[str, str]) -> tuple[list[Memory], dict[str, str], set[str]]:
        p = self.root / "AGENTS.md"
        if not p.is_file():
            return [], {}, set()
        source = "AGENTS.md"
        content = self._read_tracked(p)
        if content is None:
            return [], {}, set()
        if not self._validate(content, source):
            return [], {}, set()
        sig = self._sig(content)
        current_sources = {source}
        new_sigs = {source: sig}
        if manifest.get(source) == sig:
            return [], new_sigs, current_sources
        return [self._memory(source, "episodic", content)], new_sigs, current_sources

    def ingest_all(self) -> list[str]:
        """Ingest all tracked directories and AGENTS.md, remove stale sources, and update manifest."""
        manifest = self._load_manifest()
        to_add: list[Memory] = []
        new_sigs: dict[str, str] = {}
        current_sources: set[str] = set()

        for source_prefix, kind, recursive in _TRACKED:
            new_to_add, new_sigs_dir, new_sources = self._collect_dir(source_prefix, kind, recursive, manifest)
            to_add.extend(new_to_add)
            new_sigs.update(new_sigs_dir)
            current_sources |= new_sources

        agents_to_add, agents_sigs, agents_sources = self._collect_agents(manifest)
        to_add.extend(agents_to_add)
        new_sigs.update(agents_sigs)
        current_sources |= agents_sources

        to_delete = [
            source
            for source, sig in manifest.items()
            if source not in current_sources or manifest[source] != new_sigs.get(source)
        ]
        self.store.delete_by_source_batch(to_delete)
        if to_add:
            self.store.add_batch(to_add)
        self._save_manifest(new_sigs)
        return [m.id for m in to_add]
