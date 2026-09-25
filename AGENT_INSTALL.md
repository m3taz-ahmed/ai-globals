# aiZee — Install Guide for AI Agents

You are an AI agent installing aiZee for the user. **Done =** `aizee doctor`
reports healthy, `aizee status` returns counts, and `aizee task classify
--prompt "test"` prints a heuristic classification. A green doctor alone does
not confirm your harness loads the rules — verify your skills/rules path picks
up the config files. Never use `sudo`; the user owns the machine.

## 1. Install

**Windows (PowerShell):**

```powershell
git clone <repo> <path>; cd <path>
./install.ps1
```

**macOS / Linux:**

```bash
git clone <repo> <path>; cd <path>
./install.sh
```

If `aizee` is not on PATH afterward, restart your shell/agent session to pick
up the new PATH, or invoke `python <path>/aizee_cli.py` directly.

## 2. Verify

```bash
aizee doctor          # environment health
aizee status          # OS counts + services
aizee task classify --prompt "fix this typo"   # deterministic check, no model needed
```

## 3. Wire your harness

aiZee's source of truth is its `rules/` + `AGENTS.md`. Point your agent host at
them:

- **Cursor** — rules materialize under `.cursor/rules/`; lifecycle hooks live
  in `.cursor/hooks.json` (`aizee hook inject|observe|summary`).
- **Claude Code / Codex / others** — read `AGENTS.md` at repo root; it is the
  canonical bootloader. For skill discovery use `aizee skill list` /
  `aizee skill invoke <name>`.

## 4. First governed task

```text
Classify this request, decompose if non-trivial, and work the plan:
<your task here>
```

Expected: the agent runs `aizee task classify`, then `aizee task decompose`
for standard/complex work, then per-task `start → verify → complete`, then
`aizee task finish` before declaring done.

## 5. Recovery

- `aizee doctor` fails → follow its reported checks first; do not reinstall.
- Hooks silent → confirm `.cursor/hooks.json` exists and `aizee hook inject`
  prints without error on stdin JSON `{}`.
- Wrong root → set `AIZEE_ROOT` to the aiZee directory; never hardcode paths.
