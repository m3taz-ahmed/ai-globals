# Contributing to aiZee

Thank you for contributing! aiZee follows its own governance rules — this
document is the fast path for humans and AI agents alike.

## Ground Rules

1. **Read before writing.** Load `spec.md`, `AGENTS.md`, and
   `global-roles.md` first. Every action passes the kernel gates
   (`Probity → Guardian → Policy → Budget → Audit`).
2. **Conventional commits**: `feat:`, `fix:`, `perf:`, `docs:`, `chore:`,
   `refactor:`. Stage only files you modified (`git add <file>`, never
   `git add .`).
3. **No secrets in git.** `.env` is a template (`env.example`); real tokens
   live outside the repo.
4. **Windows-safe shell.** The primary dev environment is PowerShell — use
   `;` instead of `&&`, `Test-Path` instead of `test -f`.

## Development Workflow

```powershell
pip install -e '.[dev]'          # one-time setup

python -m pytest -q              # FAST tier while iterating (~12s)
ruff check .                     # lint gate
python -m mypy runtime memory aizee_mcp config.py aizee_cli.py dashboard/server.py

python -m pytest --cov-fail-under=80   # FULL tier before declaring done
python scripts/sync_docs.py --check    # docs must match reality
```

### Two-Tier Testing [TEST-07]

- **FAST tier (iteration):** run ONLY tests for code you touched,
  ~5s max. Example:
  `python -m pytest runtime/tests/test_kernel.py -q`
- **FULL tier (before done):** complete suite + coverage ≥ 80%. Green or
  it doesn't ship. Never run the full suite on every save; never skip it
  at the end.

## Code Standards

| Rule | Requirement |
|------|-------------|
| `[CODE-03]` | Class < 300 lines, method < 30 lines |
| `[CODE-04]` | Enums/constants over magic strings |
| `[CODE-05]` | SOLID & DRY; constructor injection |
| Types | Strict typing; no bare `Any` without justification |
| Errors | Raise `AizeeError` subclasses from `runtime/schemas.py`; never bare `Exception` |
| Storage | Use `StorageFactory` from `runtime/storage_backend.py` |
| Security | Fail closed; parameterized SQL; no `eval()`; hash-chain audit events |

## Adding Things

- **Runtime module:** create `runtime/<name>.py`, wire through a manager,
  add `runtime/tests/test_<name>.py`, export in `runtime/__init__.py`.
- **Skill:** `skills/<name>/SKILL.md` with frontmatter (`triggers`,
  `personas`, `tech_stack`). Verify with
  `aizee persona detect --multi "<task>"`.
- **Workflow:** `workflows/<NN>-<name>.md` continuing the numbering
  sequence. `scripts/sync_docs.py` regenerates the README routing table —
  just run it after adding files.

## Docs Are Verified by CI

Counts in `AGENTS.md`/`spec.md` and the workflow routing table are checked
by `scripts/sync_docs.py --check` on every PR. Run
`python scripts/sync_docs.py` locally to repair drift before pushing.

## Reporting Issues

Include: aiZee version (`aizee version`), `aizee doctor` output, minimal
reproduction steps, and expected vs actual behavior. Security issues:
do NOT open a public issue — see `SECURITY` contact in `docs/`.
