#!/usr/bin/env python3
"""AI Global OS CLI."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config
from memory.ingest import Ingestor
from memory.store import MemoryStore
from runtime.kernel import Kernel

console = Console()


def _root(args: argparse.Namespace) -> Path:
    return args.root if args.root else config.discover_root()


def cmd_status(args: argparse.Namespace) -> int:
    k = Kernel(_root(args))
    status = k.status()
    table = Table(title=f"AI Global OS Status (v{status['version']})")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Root", status["root"])
    table.add_row("Workflows", str(len(status["workflows"])))
    table.add_row("Budgets", str(len(status["budgets"])))
    table.add_row("Rules", str(len(status["rules"])))

    console.print(table)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    k = Kernel(_root(args))
    action_args = json.loads(args.args) if args.args else {}
    if args.approve:
        action_args["approved"] = True
    result = k.act(args.action, **action_args)
    if result["ok"]:
        console.print(Panel(f"[green]Action '{args.action}' Allowed[/green]\n" + json.dumps(result, indent=2)))
    else:
        console.print(Panel(f"[red]Action '{args.action}' Blocked/Denied[/red]\n" + json.dumps(result, indent=2)))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    k = Kernel(_root(args))
    context = json.loads(args.context) if args.context else {}
    result = k.run_workflow(args.workflow, context)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    root = _root(args)
    store = MemoryStore(root)
    if args.subcommand == "search":
        table = Table(title="Memory Search")
        table.add_column("Kind", style="cyan")
        table.add_column("Content")
        for mem in store.search(args.query, args.kind, limit=args.limit):
            table.add_row(mem.kind, mem.content[:120])
        console.print(table)
    elif args.subcommand == "vector":
        table = Table(title="Vector Search")
        table.add_column("ID", style="cyan")
        table.add_column("Score", style="magenta")
        for vr in store.search_vector(args.query, k=args.limit):
            table.add_row(str(vr['id']), f"{vr['score']:.4f}")
        console.print(table)
    elif args.subcommand == "add":
        m = store.add(args.kind, args.content, source=args.source or "cli")
        console.print(f"[green]Added memory:[/green] {m.id}")
    elif args.subcommand == "ingest":
        with console.status("Ingesting memories..."):
            ingestor = Ingestor(store, root)
            ids = ingestor.ingest_all()
        console.print(f"[green]Ingested {len(ids)} memories[/green]")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = _root(args)
    subprocess.run([sys.executable, str(root / "scripts" / "sync-agent-configs.py")], check=True)
    return 0


def cmd_graphify(args: argparse.Namespace) -> int:
    subprocess.run(["graphify", "update", "."], check=False)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    console.print(f"AI Global OS v{config.VERSION}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    root = _root(args)
    checks = {
        "root": root.exists(),
        "pyproject.toml": (root / "pyproject.toml").exists(),
        "runtime/policies/default.yaml": (root / "runtime" / "policies" / "default.yaml").exists(),
        "rules directory": (root / "rules").exists(),
        "workflows directory": (root / "workflows").exists(),
        "tech-stack directory": (root / "tech-stack").exists(),
        "state directory": (root / "state").exists(),
        "brain directory": (root / "brain").exists(),
    }
    try:
        from memory.vector import VectorMemory

        vector = VectorMemory(root)
        checks["vector index"] = vector.is_available()
    except Exception:
        checks["vector index"] = False

    table = Table(title="AI Global OS Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    for name, ok in checks.items():
        table.add_row(name, "ok" if ok else "missing")
    console.print(table)
    return 0 if all(checks.values()) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-os", description="AI Global OS CLI")
    parser.add_argument("--root", type=Path, default=None, help="AI Global OS root (default: AGENT_OS_ROOT or install dir)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show system status")
    sub.add_parser("sync", help="Sync agent configs")
    sub.add_parser("graphify", help="Update graphify graph")
    sub.add_parser("version", help="Show version")
    sub.add_parser("doctor", help="Check environment health")

    p_check = sub.add_parser("check", help="Check policy for action")
    p_check.add_argument("action")
    p_check.add_argument("--args", default="", help="JSON action args")
    p_check.add_argument("--approve", action="store_true", help="Approve ask decisions")

    p_run = sub.add_parser("run", help="Run workflow")
    p_run.add_argument("workflow")
    p_run.add_argument("--context", default="", help="JSON workflow context")

    p_mem = sub.add_parser("memory", help="Memory commands")
    p_mem.add_argument("subcommand", choices=["search", "vector", "add", "ingest"])
    p_mem.add_argument("--query", default="")
    p_mem.add_argument("--kind", default=None)
    p_mem.add_argument("--content", default="")
    p_mem.add_argument("--source", default="")
    p_mem.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "status": cmd_status,
        "check": cmd_check,
        "run": cmd_run,
        "memory": cmd_memory,
        "sync": cmd_sync,
        "graphify": cmd_graphify,
        "version": cmd_version,
        "doctor": cmd_doctor,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
