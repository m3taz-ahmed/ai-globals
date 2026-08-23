"""SARIF 2.1.0 output for aiZee findings.

Ported from strix (usestrix/strix) ``strix/report/sarif.py``.
Builds a GitHub code-scanning-compatible SARIF document from aiZee
findings so CI pipelines can upload via
``github/codeql-action/upload-sarif``, ingest into ASPM platforms,
or normalize across scanners.

Schema: SARIF 2.1.0 (OASIS). Validated against
https://json.schemastore.org/sarif-2.1.0.json.

Design notes:
- Rules are keyed on issue type ID (e.g. ``missing-title``).
- SARIF has three levels (error/warning/note); aiZee's three severities
  map directly: critical→error, warning→warning, info→note.
- File locations use repo-relative POSIX paths.
- Findings without safe locations are anchored to a synthetic
  ``SECURITY.md`` with ``properties.synthetic_location: true``.
- When repository context is supplied (URL/commit/branch), the run
  carries ``versionControlProvenance`` + ``automationDetails``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import PurePosixPath
from typing import Any

_logger = logging.getLogger(__name__)

SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
TOOL_NAME = "aiZee"
TOOL_INFORMATION_URI = "https://github.com/aizee"

# Synthetic anchor for findings without a safe code location.
_SYNTHETIC_LOCATION_URI = "SECURITY.md"

# SARIF only has three result levels; aiZee's three severities map here.
_SEVERITY_TO_LEVEL: dict[str, str] = {
    "critical": "error",
    "warning": "warning",
    "info": "note",
}

# Conservative label → CVSS-like score for security-severity ranking.
_SEVERITY_TO_SCORE: dict[str, float] = {
    "critical": 9.0,
    "warning": 6.0,
    "info": 3.0,
}


def _is_safe_path(path: str) -> bool:
    """Return True if *path* is a safe repo-relative POSIX path."""
    if not path:
        return False
    # Reject absolute paths, URIs, and traversal patterns
    if path.startswith("/") or "://" in path or path.startswith("\\"):
        return False
    return ".." not in PurePosixPath(path).parts


def _make_rule_id(issue_type: str) -> str:
    """Normalize a rule ID for SARIF."""
    return issue_type or "aizee-finding"


def _make_fingerprint(issue: dict[str, Any]) -> str:
    """Create a stable fingerprint for dedup across runs."""
    parts = [
        str(issue.get("issue_type", "")),
        str(issue.get("page_url", "")),
        str(issue.get("file", "")),
        str(issue.get("line", "")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def build_sarif(
    findings: list[dict[str, Any]],
    repo_url: str | None = None,
    commit_sha: str | None = None,
    branch: str | None = None,
) -> dict[str, Any]:
    """Build a SARIF 2.1.0 document from aiZee findings.

    Each finding dict should have:
    - ``issue_type``: the issue ID (e.g. ``"missing-title"``)
    - ``severity``: ``"critical"`` / ``"warning"`` / ``"info"``
    - ``title``: short label
    - ``explanation``: why it matters
    - ``how_to_fix``: remediation guidance
    - ``page_url``: the URL where the issue was found (optional)
    - ``file``: repo-relative file path (optional)
    - ``line``: line number (optional)
    - ``details``: additional structured details (optional)
    """
    # Build rules from unique issue types
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []

    for finding in findings:
        issue_type = str(finding.get("issue_type", "aizee-finding"))
        severity = str(finding.get("severity", "info"))
        rule_id = _make_rule_id(issue_type)

        # Register rule if not already present
        if rule_id not in rules:
            rules[rule_id] = {
                "id": rule_id,
                "name": str(finding.get("title", issue_type))[:100],
                "shortDescription": {
                    "text": str(finding.get("title", issue_type))[:200],
                },
                "fullDescription": {
                    "text": str(finding.get("explanation", "")),
                },
                "help": {
                    "text": str(finding.get("how_to_fix", "")),
                },
                "properties": {
                    "security-severity": str(
                        _SEVERITY_TO_SCORE.get(severity, 3.0)
                    ),
                    "aizee-severity": severity,
                },
            }

        # Build result
        level = _SEVERITY_TO_LEVEL.get(severity, "note")
        file_path = str(finding.get("file", ""))
        line = finding.get("line")
        page_url = str(finding.get("page_url", ""))

        result: dict[str, Any] = {
            "ruleId": rule_id,
            "level": level,
            "message": {
                "text": str(finding.get("title", issue_type)),
            },
            "fingerprints": {
                "primary": _make_fingerprint(finding),
            },
            "properties": {
                "aizee": {
                    "severity": severity,
                    "issue_type": issue_type,
                    "page_url": page_url,
                    "how_to_fix": str(finding.get("how_to_fix", "")),
                },
            },
        }

        # Location
        if _is_safe_path(file_path):
            location: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": file_path,
                    },
                },
            }
            if line and isinstance(line, int) and line > 0:
                location["physicalLocation"]["region"] = {
                    "startLine": line,
                }
            result["locations"] = [location]
        elif page_url:
            # Endpoint/target finding — use logical location
            result["locations"] = [
                {
                    "logicalLocation": {
                        "fullyQualifiedName": page_url,
                    },
                }
            ]
        else:
            # Synthetic anchor
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": _SYNTHETIC_LOCATION_URI},
                    },
                }
            ]
            result["properties"]["synthetic_location"] = True

        # Add fix suggestion if present
        fix = finding.get("fix")
        if fix and isinstance(fix, str):
            result["fixes"] = [
                {
                    "description": {"text": fix},
                }
            ]

        results.append(result)

    # Build the run
    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": TOOL_NAME,
                "informationUri": TOOL_INFORMATION_URI,
                "rules": list(rules.values()),
            },
        },
        "results": results,
    }

    # Version control provenance
    if repo_url or commit_sha or branch:
        provenance: dict[str, Any] = {}
        if repo_url:
            provenance["repositoryUri"] = repo_url
        if commit_sha:
            provenance["revisionId"] = commit_sha
        if branch:
            provenance["branch"] = branch
        run["versionControlProvenance"] = [provenance]
        run["automationDetails"] = {
            "id": f"aizee/{commit_sha or 'scan'}",
            "guid": _make_fingerprint({"issue_type": "run", "page_url": repo_url or ""}),
        }

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [run],
    }


def write_sarif(
    findings: list[dict[str, Any]],
    output_path: str,
    repo_url: str | None = None,
    commit_sha: str | None = None,
    branch: str | None = None,
) -> None:
    """Write a SARIF document to *output_path*.

    The call is wrapped in try/except by callers so a SARIF failure
    never blocks the primary report path.
    """
    try:
        sarif = build_sarif(findings, repo_url, commit_sha, branch)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sarif, f, indent=2, ensure_ascii=False)
    except Exception:
        _logger.exception("Failed to write SARIF to %s", output_path)
        raise


def sarif_to_json(
    findings: list[dict[str, Any]],
    repo_url: str | None = None,
    commit_sha: str | None = None,
    branch: str | None = None,
) -> str:
    """Build a SARIF document and return it as a JSON string."""
    sarif = build_sarif(findings, repo_url, commit_sha, branch)
    return json.dumps(sarif, indent=2, ensure_ascii=False)
