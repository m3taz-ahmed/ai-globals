#!/usr/bin/env python3
"""Ingest project documents into memory store."""

from __future__ import annotations

from pathlib import Path

import config

from .store import MemoryStore


class Ingestor:
    """Ingest rules, tech-stack, workflows, and session artifacts into memory."""

    def __init__(self, store: MemoryStore, root: Path | None = None) -> None:
        self.store = store
        self.root = root or config.discover_root()

    def ingest_tech_stack(self) -> list[str]:
        ids: list[str] = []
        for p in (self.root / "tech-stack").glob("*.md"):
            content = p.read_text(encoding="utf-8").strip()
            if content:
                source = f"tech-stack/{p.name}"
                self.store.delete_by_source(source)
                m = self.store.add(
                    "factual", content, source=source, meta={"file": str(p)}
                )
                ids.append(m.id)
        return ids

    def ingest_workflows(self) -> list[str]:
        ids: list[str] = []
        for p in (self.root / "workflows").glob("*.md"):
            content = p.read_text(encoding="utf-8").strip()
            if content:
                source = f"workflows/{p.name}"
                self.store.delete_by_source(source)
                m = self.store.add(
                    "procedural", content, source=source, meta={"file": str(p)}
                )
                ids.append(m.id)
        return ids

    def ingest_rules(self) -> list[str]:
        ids: list[str] = []
        for p in (self.root / "rules").glob("*.md"):
            content = p.read_text(encoding="utf-8").strip()
            if content:
                source = f"rules/{p.name}"
                self.store.delete_by_source(source)
                m = self.store.add(
                    "semantic", content, source=source, meta={"file": str(p)}
                )
                ids.append(m.id)
        return ids

    def ingest_sessions(self, project_root: Path) -> list[str]:
        """Ingest per-project active-context and Memory.md."""
        ids: list[str] = []
        for f in [project_root / ".ai" / "active-context.md", project_root / "Memory.md", self.root / "state" / "MEMORY.md"]:
            if f.exists():
                content = f.read_text(encoding="utf-8")
                source = str(f)
                self.store.delete_by_source(source)
                m = self.store.add("episodic", content, source=source, meta={"project": str(project_root)})
                ids.append(m.id)
        return ids

    def ingest_all(self) -> list[str]:
        return self.ingest_rules() + self.ingest_workflows() + self.ingest_tech_stack()
