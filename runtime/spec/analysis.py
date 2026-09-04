#!/usr/bin/env python3
"""Read-only spec analysis: cross-artifact consistency and code convergence."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

_VAGUE_TERMS = ["fast", "scalable", "secure", "intuitive", "robust", "efficient"]
_STOPWORDS = {"system", "must", "should", "user", "users", "shall", "able"}
_CODE_EXTENSIONS = {".py", ".php", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".kt", ".swift"}
_IGNORE_DIRS = {".git", "__pycache__", "node_modules", "vendor", ".venv", "venv", "dist", "build"}
_MAX_CONVERGE_FILES = 500  # hard cap on walked files (perf guard)
_MAX_CONVERGE_BYTES = 2_000_000  # hard cap on sampled code text (OOM guard)
_MAX_FILE_BYTES = 200_000  # per-file read cap


def _finding_id(prefix: str, seed: str) -> str:
    """Stable short id for a finding (SHA-256; md5 avoided project-wide)."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:6]
    return f"{prefix}-{digest}"


class AnalysisMixin:
    """Cross-artifact analysis methods for SpecEngine.

    Requires the host class (``SpecEngine``) to provide ``specs_dir``,
    ``load_spec``, and ``_spec_md_path``. The declarations below are
    overridden by SpecEngine via MRO; they exist so type checkers can
    verify attribute access from mixin methods.
    """

    specs_dir: Path

    def load_spec(self, spec_id: str) -> Any:  # pragma: no cover - host impl
        raise NotImplementedError

    def _spec_md_path(self, spec_id: str) -> Path:  # pragma: no cover - host impl
        raise NotImplementedError

    def _read_artifact(self, name: str) -> str:
        path = self.specs_dir / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def analyze_artifacts(self, spec_id: str) -> dict[str, Any]:
        """Cross-artifact consistency analysis (spec <-> plan <-> tasks).

        Non-destructive read-only analysis inspired by spec-kit's analyze
        command. Detects: coverage gaps, duplication, ambiguity,
        underspecification, constitution violations.

        Returns a structured report dict with findings + metrics.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        md_path = self._spec_md_path(spec_id)
        spec_md = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
        plan_md = self._read_artifact(f"{spec_id}.plan.md")
        tasks_md = self._read_artifact(f"{spec_id}.tasks.md")

        # Extract requirement IDs from spec state
        req_ids = {r.id for r in spec.requirements}
        # Task IDs from spec state (authoritative) + tasks.md scaffold (if present)
        task_ids = {t.id for t in spec.tasks}
        task_ids.update(re.findall(r"\bT\d{3}\b", tasks_md))
        # Extract FR-### and SC-### from spec
        fr_ids = set(re.findall(r"\bFR-\d{3}\b", spec_md))
        sc_ids = set(re.findall(r"\bSC-\d{3}\b", spec_md))

        # Coverage: requirements with no task reference. Match on the full
        # requirement id or on a word-boundary search of a stable 20-char
        # excerpt (plain substring on [:20] false-matches on truncation).
        uncovered_reqs = []
        for req in spec.requirements:
            excerpt = req.description.strip()[:20]
            excerpt_hit = bool(excerpt) and re.search(rf"\b{re.escape(excerpt)}", tasks_md) is not None
            if req.id not in tasks_md and not excerpt_hit:
                uncovered_reqs.append(req.id)

        # Ambiguity: vague adjectives without measurable criteria. Scan a
        # symmetric window (60 chars before + 100 after) so a unit stated
        # *before* the term ("100ms fast response") still counts as measured.
        ambiguity_findings: list[dict[str, Any]] = []
        unit_re = re.compile(
            r"\d+\s*(ms|s|sec|second|%|user|concurrent|minute|hour)",
            re.IGNORECASE,
        )
        for term in _VAGUE_TERMS:
            pattern = rf"\b{term}\b"
            if re.search(pattern, spec_md, re.IGNORECASE):
                for match in re.finditer(pattern, spec_md, re.IGNORECASE):
                    context_window = spec_md[max(0, match.start() - 60):match.start() + 100]
                    if not unit_re.search(context_window):
                        ambiguity_findings.append({"term": term, "position": match.start()})

        # Unresolved placeholders
        unresolved = re.findall(r"\[NEEDS CLARIFICATION[^\]]*\]", spec_md)
        todo_markers = re.findall(r"\b(TODO|TKTK|FIXME|\?\?\?)\b", spec_md + plan_md + tasks_md)

        # Constitution violations (if constitution set and not template-only)
        constitution_violations: list[str] = []
        if spec.constitution and "{{" not in spec.constitution:
            must_principles = re.findall(r"MUST\s+(.+?)(?:\.|$)", spec.constitution, re.IGNORECASE)
            for principle in must_principles[:10]:
                keyword = principle.split()[0].lower() if principle.split() else ""
                if keyword and len(keyword) > 3 and keyword not in spec_md.lower() and keyword not in plan_md.lower():
                    constitution_violations.append(principle.strip()[:80])

        findings: list[dict[str, str]] = []
        for req_id in uncovered_reqs:
            findings.append({
                "id": f"COV-{req_id}",
                "category": "coverage_gap",
                "severity": "HIGH",
                "location": "tasks.md",
                "summary": f"Requirement {req_id} has no associated task",
            })
        for amb in ambiguity_findings[:10]:
            findings.append({
                "id": _finding_id("AMB", f"{amb['term']}:{amb['position']}"),
                "category": "ambiguity",
                "severity": "MEDIUM",
                "location": f"spec.md:{amb['position']}",
                "summary": f"Vague term '{amb['term']}' lacks measurable criteria",
            })
        for marker in unresolved:
            findings.append({
                "id": _finding_id("UNC", marker),
                "category": "underspecification",
                "severity": "HIGH",
                "location": "spec.md",
                "summary": f"Unresolved: {marker[:60]}",
            })
        for marker in todo_markers[:5]:
            findings.append({
                "id": _finding_id("TODO", marker),
                "category": "underspecification",
                "severity": "MEDIUM",
                "location": "artifacts",
                "summary": f"Unresolved placeholder: {marker}",
            })
        for violation in constitution_violations:
            findings.append({
                "id": _finding_id("CON", violation),
                "category": "constitution_violation",
                "severity": "CRITICAL",
                "location": "constitution",
                "summary": f"MUST principle not reflected: {violation}",
            })

        coverage_pct = round((len(req_ids) - len(uncovered_reqs)) / max(len(req_ids), 1) * 100, 1)
        return {
            "spec_id": spec_id,
            "metrics": {
                "total_requirements": len(req_ids),
                "total_tasks": len(task_ids),
                "total_fr": len(fr_ids),
                "total_sc": len(sc_ids),
                "coverage_pct": coverage_pct,
                "ambiguity_count": len(ambiguity_findings),
                "unresolved_count": len(unresolved),
                "todo_count": len(todo_markers),
                "constitution_violations": len(constitution_violations),
            },
            "findings": findings,
            "critical_count": sum(1 for f in findings if f["severity"] == "CRITICAL"),
            "high_count": sum(1 for f in findings if f["severity"] == "HIGH"),
            "medium_count": sum(1 for f in findings if f["severity"] == "MEDIUM"),
        }

    def converge_to_code(self, spec_id: str, codebase_dir: Path) -> dict[str, Any]:
        """Assess codebase against spec/plan/tasks; identify remaining work.

        Inspired by spec-kit's converge command. Read-only — does NOT modify
        any files. Returns a structured report of gaps (missing/partial)
        with suggested remediation tasks.
        """
        spec = self.load_spec(spec_id)
        if spec is None:
            return {"error": f"Spec not found: {spec_id}"}
        try:
            resolved = codebase_dir.resolve()
        except OSError:
            return {"error": f"Codebase dir not resolvable: {codebase_dir}"}
        if not resolved.is_dir():
            return {"error": f"Codebase dir not found: {codebase_dir}"}

        # Single walk (not one rglob per extension), deterministic order,
        # hard-capped file count and byte budget.
        source_files: list[Path] = []
        for path in sorted(resolved.rglob("*")):
            if len(source_files) >= _MAX_CONVERGE_FILES:
                break
            if not path.is_file() or path.suffix not in _CODE_EXTENSIONS:
                continue
            if any(part in _IGNORE_DIRS for part in path.parts):
                continue
            source_files.append(path)

        # Build a keyword index from requirements (byte-capped sample).
        chunks: list[str] = []
        budget = _MAX_CONVERGE_BYTES
        for f in source_files[:100]:  # Sample first 100 files for text search
            try:
                if f.stat().st_size > _MAX_FILE_BYTES:
                    continue
                text = f.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            chunks.append(text[:budget])
            budget -= len(chunks[-1])
            if budget <= 0:
                break
        all_code_text = "\n".join(chunks)

        findings: list[dict[str, str]] = []
        for req in spec.requirements:
            words = re.findall(r"\b[a-z]{4,}\b", req.description.lower())
            keywords = [w for w in words if w not in _STOPWORDS]
            if not keywords:
                continue
            matched = sum(1 for kw in keywords[:5] if kw in all_code_text)
            if matched == 0:
                findings.append({
                    "id": f"MISS-{req.id}",
                    "gap_type": "missing",
                    "severity": "HIGH",
                    "source_ref": req.id,
                    "summary": f"Requirement {req.id} keywords not found in codebase: {', '.join(keywords[:3])}",
                })
            elif matched < len(keywords[:5]) / 2:
                findings.append({
                    "id": f"PART-{req.id}",
                    "gap_type": "partial",
                    "severity": "MEDIUM",
                    "source_ref": req.id,
                    "summary": f"Requirement {req.id} partially implemented ({matched}/{min(5, len(keywords))} keywords found)",
                })

        # Check task completion vs code
        incomplete_tasks = [t for t in spec.tasks if t.status != "done"]
        for task in incomplete_tasks:
            findings.append({
                "id": f"TASK-{task.id}",
                "gap_type": "missing" if task.status == "pending" else "partial",
                "severity": "HIGH" if task.status == "pending" else "MEDIUM",
                "source_ref": task.id,
                "summary": f"Task {task.id} not done (status: {task.status}): {task.description[:60]}",
            })

        # Suggest remediation tasks (append-only style, like spec-kit converge)
        suggested_tasks: list[dict[str, str]] = []
        existing_max = len(spec.tasks)
        for i, finding in enumerate(findings, start=1):
            suggested_tasks.append({
                "id": f"T{existing_max + i:03d}",
                "description": finding["summary"],
                "source_ref": finding["source_ref"],
                "gap_type": finding["gap_type"],
                "severity": finding["severity"],
            })

        return {
            "spec_id": spec_id,
            "codebase_dir": str(codebase_dir),
            "files_scanned": len(source_files),
            "metrics": {
                "requirements_checked": len(spec.requirements),
                "tasks_incomplete": len(incomplete_tasks),
                "findings_total": len(findings),
                "missing_count": sum(1 for f in findings if f["gap_type"] == "missing"),
                "partial_count": sum(1 for f in findings if f["gap_type"] == "partial"),
            },
            "findings": findings,
            "suggested_tasks": suggested_tasks,
            "converged": len(findings) == 0,
        }
