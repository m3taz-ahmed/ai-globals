# Quickstart: {{TITLE}}

**Spec ID**: `{{SPEC_ID}}` | **Phase**: 1 (design)
**Date**: {{DATE}}

## Prerequisites

- [Runtime version, e.g., Python 3.11+]
- [Dependencies, e.g., pip install -r requirements.txt]
- [External services, e.g., PostgreSQL running on localhost:5432]

## Setup

```bash
# Clone and install
git clone [repo-url]
cd [project]
[install command]

# Configure
cp .env.example .env
# Edit .env with your settings

# Run migrations
[migration command]
```

## Verify It Works

```bash
# Run the quickstart test
[test command, e.g., pytest tests/test_quickstart.py -v]

# Start the service
[start command, e.g., python -m src.main]

# Check health
curl http://localhost:[port]/health
```

## Expected Output

```
[Expected output from the quickstart test or health check]
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| [Common issue] | [Fix] |

<!--
  aiZee GATES:
  - Quickstart must pass before declaring done
  - Include exact commands (no "figure it out" steps)
  - Verify with eval/harness.py
-->
