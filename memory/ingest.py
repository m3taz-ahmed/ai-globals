#!/usr/bin/env python3
"""Ingest project documents into memory store."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import config

from .store import Memory, MemoryStore


class Ingestor:
    """Ingest rules, tech-stack, workflows, and session artifacts into memory.

    Uses an incremental manifest stored in `brain/ingest_manifest.json` to skip
    unchanged files and batches SQLite/vector writes to avoid expensive re-embedding.
    """

    _DIRS: tuple[tuple[str, str], ...] = (
        ("rules", "semantic"),
        ("workflows", "procedural"),
        ("tech-stack", "factual"),
    )

    def __init__(self, store: MemoryStore, root: Path | None = None) -> None:
        self.store = store
        self.root = root or config.discover_root()
        self.manifest_file = self.root / "brain" / "ingest_manifest.json"

    def _load_manifest(self) -> dict[str, Any]:
        if self.manifest_file.exists():
            return cast(dict[str, Any], json.loads(self.manifest_file.read_text(encoding="utf-8")))
        return {}

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    @staticmethod
    def _signature(path: Path, content: str) -> dict[str, Any]:
        return {
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "mtime": path.stat().st_mtime_ns,
        }

    def _make_memory(self, kind: str, content: str, source: str, path: Path) -> Memory:
        now = datetime.now(timezone.utc).isoformat()
        return Memory(
            id=str(uuid.uuid4()),
            kind=kind,
            content=content,
            source=source,
            meta=json.dumps({"file": str(path)}),
            created_at=now,
            valid_from=now,
            valid_to=None,
        )

    def ingest_all(self) -> list[str]:
        """Ingest all tracked directories, skip unchanged files, and batch writes."""
        manifest = self._load_manifest()
        current_sources: set[str] = set()
        to_add: list[Memory] = []
        changed_sources: list[str] = []

        for name, kind in self._DIRS:
            dir_path = self.root / name
            if not dir_path.exists():
                continue
            for p in dir_path.glob("*.md"):
                source = f"{name}/{p.name}"
                current_sources.add(source)
                content = p.read_text(encoding="utf-8").strip()
                sig = self._signature(p, content)
                if manifest.get(source) == sig:
                    continue
                if content:
                    to_add.append(self._make_memory(kind, content, source, p))
                changed_sources.append(source)
                manifest[source] = sig

        removed_sources = [source for source in manifest if source not in current_sources]
        sources_to_delete = changed_sources + removed_sources
        if sources_to_delete:
            self.store.delete_by_source_batch(sources_to_delete)
        if to_add:
            self.store.add_batch(to_add)

        for source in removed_sources:
            manifest.pop(source, None)
        self._save_manifest(manifest)
        return [m.id for m in to_add]

    def ingest_tech_stack(self) -> list[str]:
        return self._ingest_dir("tech-stack", "factual")

    def ingest_workflows(self) -> list[str]:
        return self._ingest_dir("workflows", "procedural")

    def ingest_rules(self) -> list[str]:
        return self._ingest_dir("rules", "semantic")

    def _ingest_dir(self, name: str, kind: str) -> list[str]:
        """Ingest a single directory; returns IDs of newly added memories."""
        manifest = self._load_manifest()
        dir_path = self.root / name
        if not dir_path.exists():
            return []

        current_sources: set[str] = set()
        to_add: list[Memory] = []
        changed_sources: list[str] = []

        for p in dir_path.glob("*.md"):
            source = f"{name}/{p.name}"
            current_sources.add(source)
            content = p.read_text(encoding="utf-8").strip()
            sig = self._signature(p, content)
            if manifest.get(source) == sig:
                continue
            if content:
                to_add.append(self._make_memory(kind, content, source, p))
            changed_sources.append(source)
            manifest[source] = sig

        removed_sources = [source for source in manifest if source not in current_sources]
        sources_to_delete = changed_sources + removed_sources
        if sources_to_delete:
            self.store.delete_by_source_batch(sources_to_delete)
        if to_add:
            self.store.add_batch(to_add)

        for source in removed_sources:
            manifest.pop(source, None)
        self._save_manifest(manifest)
        return [m.id for m in to_add]

    def ingest_sessions(self, project_root: Path) -> list[str]:
        """Ingest per-project active-context and Memory.md."""
        ids: list[str] = []
        for f in [
            project_root / ".ai" / "active-context.md",
            project_root / "Memory.md",
            self.root / "state" / "MEMORY.md",
        ]:
            if f.exists():
                content = f.read_text(encoding="utf-8")
                source = str(f)
                self.store.delete_by_source(source)
                m = self.store.add("episodic", content, source=source, meta={"project": str(project_root)})
                ids.append(m.id)
        return ids
