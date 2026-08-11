# Privacy Policy

**Last updated:** 2025-01-01

## Overview

AI Global OS ("we", "us", or "the software") is a sovereign AI engineering
control plane that runs locally on your machine. This privacy policy explains
how data is collected, stored, and used.

## Data Collection

### What We Collect

- **Memory Store:** Text content you ingest (rules, tech-stack docs, workflows,
  skills) is stored in a local SQLite database (`brain/memory.db`).
- **Budget State:** Token and cost usage data is stored in `state/budget.json`.
- **Audit Logs:** Policy decisions and action evaluations are logged to
  `state/audit.jsonl`.
- **Telemetry:** Usage metrics are stored locally in `state/telemetry.jsonl`.
- **Tracing:** Span data is stored in `state/spans.jsonl`.

### What We Do NOT Collect

- We do **not** send your data to any external server.
- We do **not** use cookies or tracking pixels.
- We do **not** collect personal information.
- We do **not** phone home or report usage analytics.

## Data Storage

All data is stored locally on your machine in the `state/` and `brain/`
directories. No data leaves your machine unless you explicitly configure
an external MCP server that transmits data.

## Data Encryption

When `AIOS_ENCRYPTION_KEY` is set, sensitive state files (e.g., `budget.json`)
are encrypted at rest using AES-128-CBC with HMAC-SHA256 (Fernet).

## Third-Party Services

AI Global OS can optionally connect to external MCP servers (e.g., Context7,
Upwork, Freelancer). These services have their own privacy policies. We are
not responsible for how third-party services handle your data.

## Data Retention

- Memory store data persists until you explicitly delete or invalidate it.
- Audit logs and telemetry data persist until you manually clear them.
- Budget state is overwritten on each save.

## Your Rights

- **Access:** You can view all stored data in the `state/` and `brain/` directories.
- **Deletion:** You can delete the `state/` and `brain/` directories at any time.
- **Portability:** All data is in standard formats (SQLite, JSON, JSONL).

## Contact

For privacy questions, open an issue at:
https://github.com/m3taz-ahmed/ai-globals/issues
