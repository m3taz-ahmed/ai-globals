#!/usr/bin/env python3
"""aiZee update script — pull latest from GitHub and re-run post-install hooks.

Usage:
    python scripts/update.py              # interactive
    python scripts/update.py --yes        # non-interactive (auto-confirm)

What it does:
  1. Check if this is a git repo (has .git/).
  2. git fetch origin → compare local vs remote.
  3. If behind: git pull (preserves local learned data via .gitignore).
  4. Re-run post-install: pip install -e ., MCP config sync, CLI shim refresh.
  5. Print summary of updated files.

Learned data (memory/, state/, brain/, graphify-out/, .env) is gitignored
and never touched by git pull.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=False)
    if check and result.returncode != 0:
        return result.returncode, result.stdout, result.stderr
    return result.returncode, result.stdout, result.stderr


def _is_git_repo(root: Path) -> bool:
    """Check if the root is inside a git repository."""
    git_dir = root / ".git"
    if git_dir.exists():
        return True
    # Check parent directories
    rc, _, _ = _run(["git", "rev-parse", "--git-dir"], cwd=root, check=False)
    return rc == 0


def _get_current_branch(root: Path) -> str:
    """Get the current git branch name."""
    rc, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, check=False)
    if rc == 0:
        return out.strip()
    return "main"


def _check_remote(root: Path, branch: str) -> dict[str, Any]:
    """Fetch from remote and compare local vs remote.

    Returns dict with:
      - behind: bool (local is behind remote)
      - ahead: bool (local has unpushed commits)
      - commits_behind: int
      - remote_url: str
      - error: str | None
    """
    info: dict[str, Any] = {
        "behind": False, "ahead": False, "commits_behind": 0,
        "remote_url": "", "error": None,
    }

    # Get remote URL
    rc, out, _ = _run(["git", "remote", "get-url", "origin"], cwd=root, check=False)
    if rc == 0:
        info["remote_url"] = out.strip()

    # Fetch
    rc, _, err = _run(["git", "fetch", "origin"], cwd=root, check=False)
    if rc != 0:
        info["error"] = f"git fetch failed: {err.strip()}"
        return info

    # Compare local vs remote
    local_ref = "HEAD"
    remote_ref = f"origin/{branch}"

    # Commits behind (remote has, local doesn't)
    rc, out, _ = _run(
        ["git", "rev-list", "--count", f"{local_ref}..{remote_ref}"],
        cwd=root, check=False,
    )
    if rc == 0:
        info["commits_behind"] = int(out.strip() or "0")
        info["behind"] = info["commits_behind"] > 0

    # Commits ahead (local has, remote doesn't)
    rc, out, _ = _run(
        ["git", "rev-list", "--count", f"{remote_ref}..{local_ref}"],
        cwd=root, check=False,
    )
    if rc == 0:
        info["ahead"] = int(out.strip() or "0") > 0

    return info


def _git_pull(root: Path, branch: str) -> dict[str, Any]:
    """Pull latest from remote. Returns dict with result info."""
    result: dict[str, Any] = {"success": False, "output": "", "error": ""}

    # Try pull with rebase first (cleaner history)
    rc, out, err = _run(
        ["git", "pull", "--rebase", "origin", branch],
        cwd=root, check=False,
    )
    if rc == 0:
        result["success"] = True
        result["output"] = out
        return result

    # Fallback: regular pull (merge)
    rc2, out2, err2 = _run(
        ["git", "pull", "origin", branch],
        cwd=root, check=False,
    )
    if rc2 == 0:
        result["success"] = True
        result["output"] = out2
        return result

    result["error"] = err.strip() or err2.strip()
    result["output"] = out + out2
    return result


def _get_changed_files(root: Path, old_head: str, new_head: str) -> list[str]:
    """Get list of files changed between two commits."""
    if old_head == new_head:
        return []
    rc, out, _ = _run(
        ["git", "diff", "--name-only", old_head, new_head],
        cwd=root, check=False,
    )
    if rc == 0:
        return [f for f in out.strip().split("\n") if f]
    return []


def _post_install_hooks(root: Path) -> list[str]:
    """Re-run post-install steps. Returns list of actions taken."""
    actions: list[str] = []

    # 1. pip install -e . (refresh package)
    rc, _out, _ = _run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
        cwd=root, check=False,
    )
    actions.append(f"pip install -e .: {'OK' if rc == 0 else 'skipped'}")

    # 2. MCP config sync
    sync_script = root / "scripts" / "mcp_global_sync.py"
    if sync_script.exists():
        rc, _, _ = _run(
            [sys.executable, str(sync_script)],
            cwd=root, check=False,
        )
        actions.append(f"MCP config sync: {'OK' if rc == 0 else 'skipped'}")

    # 3. CLI shim refresh
    cli_script = root / "scripts" / "install_cli_shim.py"
    if cli_script.exists():
        rc, _, _ = _run(
            [sys.executable, str(cli_script)],
            cwd=root, check=False,
        )
        actions.append(f"CLI shim refresh: {'OK' if rc == 0 else 'skipped'}")

    # 4. Memory re-ingest (if memory store exists)
    memory_db = root / "memory" / "store.db"
    if memory_db.exists():
        rc, _, _ = _run(
            [sys.executable, "-m", "aizee_cli", "--root", str(root), "memory", "ingest"],
            cwd=root, check=False,
        )
        actions.append(f"memory ingest: {'OK' if rc == 0 else 'skipped'}")

    return actions


def run_update(root: Path, assume_yes: bool = False) -> int:
    """Main update flow. Returns exit code."""
    print("=" * 60)
    print("  aiZee Update — Pull latest from GitHub")
    print("=" * 60)
    print()

    # Step 1: Check if git repo
    if not _is_git_repo(root):
        print("[ERROR] This is not a git repository. Cannot update.")
        print("        Clone the repo first: git clone <url> aizee")
        return 1

    # Step 2: Get branch + check remote
    branch = _get_current_branch(root)
    print(f"  Branch:  {branch}")

    info = _check_remote(root, branch)
    if info["error"]:
        print(f"[ERROR] {info['error']}")
        return 1

    if info["remote_url"]:
        print(f"  Remote:  {info['remote_url']}")

    if not info["behind"]:
        if info["ahead"]:
            print("\n  [OK] Already up to date (local has unpushed commits).")
        else:
            print("\n  [OK] Already up to date. No updates available.")
        return 0

    print(f"\n  [UPDATE] {info['commits_behind']} commit(s) behind remote.")
    print()

    # Step 3: Confirm
    if not assume_yes:
        try:
            answer = input("  Pull updates? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            return 1
        if answer != "y":
            print("  Cancelled.")
            return 1

    # Step 4: Get current HEAD for diff
    _, old_head, _ = _run(["git", "rev-parse", "HEAD"], cwd=root, check=False)

    # Step 5: Git pull
    print("\n  Pulling updates...")
    pull_result = _git_pull(root, branch)
    if not pull_result["success"]:
        print(f"  [ERROR] Pull failed: {pull_result['error']}")
        print("  Resolve conflicts manually, then re-run update.")
        return 1

    # Step 6: Get new HEAD + changed files
    _, new_head, _ = _run(["git", "rev-parse", "HEAD"], cwd=root, check=False)
    changed = _get_changed_files(root, old_head.strip(), new_head.strip())

    if changed:
        print(f"  Updated {len(changed)} file(s):")
        for f in changed[:20]:
            print(f"    - {f}")
        if len(changed) > 20:
            print(f"    ... and {len(changed) - 20} more")
    else:
        print("  No files changed.")

    # Step 7: Post-install hooks
    print("\n  Running post-install hooks...")
    actions = _post_install_hooks(root)
    for a in actions:
        print(f"    {a}")

    # Step 8: Summary
    print("\n" + "=" * 60)
    print("  [DONE] aiZee updated successfully.")
    print("  Learned data (memory/state/brain/.env) preserved.")
    print("=" * 60)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aiZee update — pull latest from GitHub")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    parser.add_argument("--root", default=None, help="aiZee root directory (default: auto-detect)")
    args = parser.parse_args(argv)

    # Auto-detect: script is in <root>/scripts/
    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent

    if not root.exists():
        print(f"[ERROR] Root not found: {root}")
        return 1

    return run_update(root, assume_yes=args.yes)


if __name__ == "__main__":
    raise SystemExit(main())
