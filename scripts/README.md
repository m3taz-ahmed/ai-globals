# `scripts/` — Automation & Validation Tools

This directory contains the **self-healing validation engine** for AI Global OS.

---

## `validate-globals.ps1` — Integrity Validator (v4.5.0)

The primary automation tool. Performs a full integrity scan of the repository, detects issues, and can auto-correct them.

### Usage

```powershell
# Standard validation scan (read-only)
.\scripts\validate-globals.ps1

# Full scan — bypasses SHA-256 incremental cache
.\scripts\validate-globals.ps1 -Force

# Auto-fix mode — corrects encoding, line endings, and broken references
.\scripts\validate-globals.ps1 -Fix

# Dry-run — shows what -Fix would change without writing anything
.\scripts\validate-globals.ps1 -Fix -DryRun

# Generate a fresh SHA-256 integrity manifest
.\scripts\validate-globals.ps1 -GenerateManifest
```

### What It Checks

| Check | Description |
|---|---|
| **Encoding** | Detects mojibake artifacts (`â€"`, `â€™`, `U+FFFD`) |
| **Line Endings** | Ensures all files use LF (not CRLF) |
| **Cross-References** | Validates all `ref: filename.md §N` links exist |
| **Secret Scanning** | Entropy-based detection of potential credential leaks |
| **Version Consistency** | Confirms version number matches across README, state/CHANGELOG.md, and script |
| **Integrity Manifest** | SHA-256 hashes to detect unauthorized file changes |
| **Rule Propagation** | If core rules changed, forces a full system re-scan |

### Exit Codes

| Code | Meaning |
|---|---|
| `0` | All checks passed |
| `1` | Issues found (details in output) |
| `2` | Script error (misconfiguration or missing files) |

### Running in CI

```yaml
# Example GitHub Actions step
- name: Validate AI Global OS integrity
  shell: pwsh
  run: .\scripts\validate-globals.ps1 -Force
```

---

## Requirements

- **PowerShell 7+** (cross-platform: Windows, Linux, macOS)
- Run from the repository root (same directory as `global-roles.md`)
