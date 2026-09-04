#!/usr/bin/env python3
"""Consolidation primitives for memory upkeep (from agent-memory).

Dry-runnable hygiene jobs for memory maintenance:
- dedupe_entities: Vector similarity-based entity merging
- summarize_long_traces: Identify traces needing summarization
- detect_superseded_facts: Find outdated information

All operations are idempotent and dry-runnable by default.

Usage::

    from memory.consolidation import ConsolidationEngine

    engine = ConsolidationEngine()
    report = engine.dedupe_entities(entries, dry_run=True)
    print(report.merged_count)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from memory.simhash import SimHashIndex, compute_simhash, hamming_distance


@dataclass
class ConsolidationReport:
    """Report from a consolidation operation."""

    operation: str
    dry_run: bool
    examined: int = 0
    merged_count: int = 0
    summarized_count: int = 0
    superseded_count: int = 0
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ConsolidationEngine:
    """Memory consolidation primitives (from agent-memory).

    All operations are idempotent and dry-runnable by default.
    """

    simhash_index: SimHashIndex = field(default_factory=SimHashIndex)
    similarity_threshold: int = 3  # Hamming distance threshold

    def dedupe_entities(
        self,
        entries: list[dict[str, Any]],
        *,
        dry_run: bool = True,
    ) -> ConsolidationReport:
        """Find and optionally merge duplicate entities.

        Uses SimHash for near-duplicate detection. A dry run never touches
        the shared ``simhash_index`` (previously it polluted the index, so
        a second call found the first call's dry-run entries).
        """
        report = ConsolidationReport(operation="dedupe", dry_run=dry_run)
        seen: dict[str, str] = {}  # simhash → first entry_id
        for entry in entries:
            entry_id = str(entry.get("id", ""))
            content = entry.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            sh = compute_simhash(content)
            if sh:
                if not dry_run:
                    self.simhash_index.add_hash(entry_id, sh)
                for existing_id, existing_hash in seen.items():
                    if hamming_distance(sh, existing_hash) <= self.similarity_threshold:
                        report.merged_count += 1
                        report.details.append({
                            "duplicate": entry_id,
                            "original": existing_id,
                            "action": "would_merge" if dry_run else "merged",
                        })
                        break
                else:
                    seen[entry_id] = sh
            report.examined += 1
        return report

    def summarize_long_traces(
        self,
        entries: list[dict[str, Any]],
        *,
        max_length: int = 5000,
        dry_run: bool = True,
    ) -> ConsolidationReport:
        """Identify traces that need summarization."""
        report = ConsolidationReport(operation="summarize", dry_run=dry_run)
        for entry in entries:
            content = entry.get("content", "")
            if not isinstance(content, str):
                content = str(content)
            if len(content) > max_length:
                report.summarized_count += 1
                report.details.append({
                    "entry_id": entry.get("id", ""),
                    "length": len(content),
                    "action": "would_summarize" if dry_run else "summarized",
                })
            report.examined += 1
        return report

    def detect_superseded_facts(
        self,
        entries: list[dict[str, Any]],
        *,
        dry_run: bool = True,
    ) -> ConsolidationReport:
        """Find outdated facts (entries with valid_to set or superseded_by)."""
        report = ConsolidationReport(operation="supersede", dry_run=dry_run)
        for entry in entries:
            if entry.get("valid_to") or entry.get("superseded_by"):
                report.superseded_count += 1
                report.details.append({
                    "entry_id": entry.get("id", ""),
                    "valid_to": entry.get("valid_to"),
                    "superseded_by": entry.get("superseded_by"),
                    "action": "would_invalidate" if dry_run else "invalidated",
                })
            report.examined += 1
        return report


if __name__ == "__main__":
    engine = ConsolidationEngine()
    entries = [
        {"id": "1", "content": "The quick brown fox jumps over the lazy dog"},
        {"id": "2", "content": "The quick brown fox jumps over the lazy dog today"},
        {"id": "3", "content": "A completely different fact about quantum physics"},
    ]
    report = engine.dedupe_entities(entries, dry_run=True)
    print(f"Examined: {report.examined}, Merged: {report.merged_count}")
