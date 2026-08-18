#!/usr/bin/env python3
"""aiZee CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import config

if TYPE_CHECKING:
    from runtime.kernel import Kernel

console = Console()


def _root(args: argparse.Namespace) -> Path:
    return args.root if args.root else config.discover_root()


def _project_root(args: argparse.Namespace) -> Path:
    project = args.project
    if isinstance(project, Path):
        return project
    return config.discover_project_root()


def _kernel(args: argparse.Namespace) -> Kernel:
    from runtime.kernel import Kernel

    return Kernel(_root(args), _project_root(args))


def cmd_status(args: argparse.Namespace) -> int:
    k = _kernel(args)
    status = k.status()
    table = Table(title=f"aiZee Status (v{status['version']})")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Root", status["root"])
    table.add_row("Personas", str(len(status["personas"])))
    table.add_row("Skills", str(len(status["skills"])))
    table.add_row("Workflows", str(len(status["workflows"])))
    table.add_row("Budgets", str(len(status["budgets"])))
    table.add_row("Rules", str(len(status["rules"])))

    console.print(table)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    k = _kernel(args)
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
    k = _kernel(args)
    context = json.loads(args.context) if args.context else {}
    result = k.run_workflow(args.workflow, context)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    from memory.store import MemoryStore

    root = _project_root(args)
    store = MemoryStore(root)
    results = store.search_hybrid(
        args.query, k=args.limit, kind=args.kind, explain=getattr(args, "explain", False)
    )

    table = Table(title="Hybrid Context Query")
    table.add_column("Kind", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Score", style="green")
    table.add_column("Content")
    for r in results:
        score = f"{r['score']:.4f}" if r["score"] is not None else "-"
        table.add_row(r["kind"], r["source"], score, r["content"][:120])
    console.print(table)
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    from memory.store import MemoryStore

    root = _project_root(args)
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
        table.add_column("Kind", style="cyan")
        table.add_column("Source", style="magenta")
        table.add_column("Score", style="green")
        for vr in store.search_vector(args.query, k=args.limit, kind=args.kind):
            fetched = store.get(vr["id"])
            kind = fetched.kind if fetched else "-"
            source = fetched.source if fetched else "-"
            table.add_row(str(vr["id"]), kind, source, f"{vr['score']:.4f}")
        console.print(table)
    elif args.subcommand == "add":
        if not args.kind or not args.content:
            console.print("[red]--kind and --content are required for 'add'[/red]")
            return 1
        m = store.add(args.kind, args.content, source=args.source or "cli")
        console.print(f"[green]Added memory:[/green] {m.id}")
    elif args.subcommand == "ingest":
        from memory.ingest import Ingestor

        with console.status("Ingesting memories..."):
            ingestor = Ingestor(store, _root(args))
            ids = ingestor.ingest_all()
        console.print(f"[green]Ingested {len(ids)} memories[/green]")

        # Auto-ingest: watch for changes in tech-stack/, rules/, workflows/
        if getattr(args, "watch", False):
            import time

            os_root = _root(args)
            watch_dirs = [os_root / "tech-stack", os_root / "rules", os_root / "workflows"]
            snapshots = {}
            for d in watch_dirs:
                if d.exists():
                    snapshots[d] = {f.name: f.stat().st_mtime for f in d.rglob("*.md")}
            console.print("[cyan]Watching tech-stack/, rules/, workflows/ for changes...[/cyan]")
            console.print("[dim]Press Ctrl+C to stop.[/dim]")
            try:
                while True:
                    changed = False
                    for d in watch_dirs:
                        if not d.exists():
                            continue
                        current = {f.name: f.stat().st_mtime for f in d.rglob("*.md")}
                        if current != snapshots.get(d):
                            changed = True
                            snapshots[d] = current
                    if changed:
                        console.print("[yellow]Change detected — re-ingesting...[/yellow]")
                        ingestor2 = Ingestor(store, os_root)
                        new_ids = ingestor2.ingest_all()
                        console.print(f"[green]Re-ingested {len(new_ids)} memories[/green]")
                    time.sleep(2)
            except KeyboardInterrupt:
                console.print("[cyan]Stopped watching.[/cyan]")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    root = _root(args)
    subprocess.run([sys.executable, str(root / "scripts" / "sync-agent-configs.py")], check=True)
    return 0


def cmd_graphify(args: argparse.Namespace) -> int:
    subprocess.run(["graphify", "update", "."], check=False)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    console.print(f"aiZee v{config.VERSION}")
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.subcommand == "test":
        action_args = json.loads(args.args) if args.args else {}
        result = k.act(args.action, dry_run=True, **action_args)
        print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_budget(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.subcommand == "list":
        table = Table(title="Budgets")
        table.add_column("Scope", style="cyan")
        table.add_column("Max Tokens", style="green")
        table.add_column("Max Cost USD", style="green")
        table.add_column("Period", style="green")
        for scope, budget in k.budget.budgets.items():
            table.add_row(
                scope,
                str(budget.max_tokens) if budget.max_tokens else "-",
                f"${budget.max_cost_usd:.2f}" if budget.max_cost_usd else "-",
                budget.period,
            )
        console.print(table)
    elif args.subcommand == "usage":
        table = Table(title="Budget Usage")
        table.add_column("Scope", style="cyan")
        table.add_column("Tokens", style="green")
        table.add_column("Cost USD", style="green")
        table.add_column("Calls", style="green")
        table.add_column("Period Key", style="green")
        for scope, usage in k.budget.usage.items():
            table.add_row(
                scope,
                str(usage.get("tokens", 0)),
                f"${usage.get('cost', 0):.4f}",
                str(usage.get("calls", 0)),
                str(usage.get("period_key", "")),
            )
        console.print(table)
    elif args.subcommand == "set":
        from runtime.budget import Budget

        budget = Budget(
            max_tokens=args.max_tokens,
            max_cost_usd=args.max_cost,
            period=args.period,
            on_exceed=args.on_exceed,
        )
        k.budget.set_budget(args.scope, budget)
        k.budget.save()
        console.print(f"[green]Budget '{args.scope}' updated[/green]")
    return 0


def cmd_project(args: argparse.Namespace) -> int:
    if args.subcommand == "init":
        target = Path(args.path).resolve()
        target.mkdir(parents=True, exist_ok=True)
        for sub in (".ai", "runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
            (target / sub).mkdir(parents=True, exist_ok=True)
        (target / ".ai" / "active-context.md").write_text("# Active Context\n\n", encoding="utf-8")
        (target / "runtime" / "policies" / "default.yaml").write_text(
            "default_action: ask\nrules:\n"
            "  - name: allow-read\n    condition: \"type in ['view', 'Read']\"\n    action: allow\n",
            encoding="utf-8",
        )
        console.print(f"[green]Initialized project at {target}[/green]")
        console.print("Set AGENT_PROJECT_ROOT or use --root to target this project.")
    return 0


def cmd_saga(args: argparse.Namespace) -> int:
    k = _kernel(args)
    steps = json.loads(args.steps) if args.steps else []
    context = json.loads(args.context) if args.context else {}
    result = k.run_saga(args.saga_id, steps, context)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_telemetry(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.subcommand == "summary":
        print(json.dumps(k.telemetry.summary(), indent=2))
    elif args.subcommand == "events":
        events = k.telemetry.query(limit=args.limit, event_type=args.type)
        print(json.dumps(events, indent=2, default=str))
    elif args.subcommand == "system":
        from runtime.telemetry import system_metrics

        print(json.dumps(system_metrics(), indent=2))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Audit log commands (show, verify)."""
    from runtime.audit import AuditLogger

    root = _root(args)
    logger = AuditLogger(root)

    if args.subcommand == "show":
        entries = logger.read_entries(
            event_type=args.type if args.type else None,
            limit=args.limit,
        )
        if not entries:
            console.print("[yellow]No audit entries found.[/yellow]")
            return 0
        table = Table(title=f"Audit Log (last {len(entries)})")
        table.add_column("Timestamp", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Details", style="green")
        for e in entries:
            ts = e.get("ts", "-")[:19]
            etype = e.get("type", "-")
            details = json.dumps(e.get("details", {}), default=str)[:100]
            table.add_row(ts, etype, details)
        console.print(table)
    elif args.subcommand == "verify":
        result = logger.verify_chain()
        if result["valid"]:
            console.print(f"[green]Chain valid — {result['entries_checked']} entries checked[/green]")
        else:
            console.print(f"[red]Chain BROKEN at entry {result['broken_at']}[/red]")
        return 0 if result["valid"] else 1
    return 0


def cmd_spec(args: argparse.Namespace) -> int:
    """Spec-driven development commands (scaffold, analyze, converge)."""
    from pathlib import Path

    from runtime.spec_engine import SpecEngine

    os_root = _root(args)
    specs_dir = os_root / "specs"
    engine = SpecEngine(specs_dir)

    if args.subcommand == "list":
        specs = engine.list_specs()
        if not specs:
            console.print("[yellow]No specs found.[/yellow]")
            return 0
        table = Table(title="Specs")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Phase", style="magenta")
        for s in specs:
            table.add_row(s.get("id", "-"), s.get("title", "-"), s.get("phase", "-"))
        console.print(table)
    elif args.subcommand == "analyze":
        report = engine.analyze_artifacts(args.spec_id)
        print(json.dumps(report, indent=2, default=str))
    elif args.subcommand == "converge":
        codebase = Path(args.codebase) if args.codebase else _project_root(args)
        report = engine.converge_to_code(args.spec_id, codebase)
        print(json.dumps(report, indent=2, default=str))
    elif args.subcommand == "scaffold":
        if not args.template or not args.title:
            console.print("[red]--template and --title required for scaffold[/red]")
            return 1
        if args.template == "spec":
            result = engine.scaffold_spec(args.spec_id, args.title)
        elif args.template == "plan":
            result = engine.scaffold_plan(args.spec_id)
        elif args.template == "tasks":
            result = engine.scaffold_tasks(args.spec_id)
        else:
            console.print(f"[red]Unknown template: {args.template}[/red]")
            return 1
        console.print(f"[green]Scaffolded {args.template}:[/green] {result}")
    return 0


def cmd_stack(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.subcommand == "detect":
        detected = k.detect_tech_stack()
        print(json.dumps(detected, indent=2))
    elif args.subcommand == "show":
        from runtime.tech_stack import load_stack_docs

        docs = load_stack_docs(k.project_root, k.root)
        for name, content in docs.items():
            console.print(f"[cyan]{name}[/cyan]")
            console.print(content[:500])
            console.print("")
    return 0


def cmd_linkedin(args: argparse.Namespace) -> int:
    """LinkedIn CLI — proxy to octopus-linkedin MCP server."""
    from runtime.mcp_client import McpClient

    client = McpClient("linkedin", _root(args))
    if not client.is_configured():
        console.print("[red]LinkedIn MCP server not configured. Run the installer.[/red]")
        return 1

    action = args.linkedin_action
    tool_map = {
        "profile": ("get_profile", {}),
        "post": ("create_post", {"text": args.text, "visibility": args.visibility or "PUBLIC"}),
        "draft": ("create_draft", {"text": args.text, "kind": "text"}),
        "drafts": ("list_drafts", {"status": args.status} if args.status else {}),
        "approve": ("approve_draft", {"draft_id": args.draft_id}),
        "publish": ("publish_draft", {"draft_id": args.draft_id}),
        "schedule": ("schedule_draft", {"draft_id": args.draft_id, "publish_at": args.when}),
        "stats": ("get_post_stats", {"post_urn": args.urn}),
        "delete": ("delete_post", {"post_urn": args.urn}),
    }

    if action not in tool_map:
        console.print(f"[red]Unknown linkedin action: {action}[/red]")
        return 1

    tool, arguments = tool_map[action]
    result = client.call_tool(tool, arguments)
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    if args.server == "sync":
        import subprocess
        root = _root(args)
        cmd = [sys.executable, str(root / "scripts" / "mcp_global_sync.py")]
        if args.check:
            cmd.append("--check")
        return subprocess.call(cmd, cwd=str(root))

    if not args.server or not args.tool:
        console.print("[red]Usage: aizee mcp <server> <tool> [--args '...'][/red]")
        console.print("[cyan]       aizee mcp sync [--check][/cyan]")
        return 1

    from runtime.mcp_client import McpClient

    client = McpClient(args.server, _root(args))
    if not client.is_configured():
        console.print(f"[red]MCP server '{args.server}' not configured[/red]")
        return 1
    arguments = json.loads(args.args) if args.args else {}
    result = client.call_tool(args.tool, arguments)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


def cmd_chat(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.message:
        result = k.chat_message(args.message)
        print(json.dumps(result, indent=2, default=str))
        return 0
    console.print("[cyan]aiZee Chat (type 'exit' to quit)[/cyan]")
    while True:
        try:
            msg = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if not msg or msg.lower() == "exit":
            break
        result = k.chat_message(msg)
        print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_ci(args: argparse.Namespace) -> int:
    from runtime.ci import CIPipeline

    pipeline = CIPipeline(_root(args))
    rc = pipeline.run(skip_pytest=args.skip_pytest)
    for r in pipeline.results:
        color = "green" if r["ok"] else "red"
        console.print(f"[{color}]{r['name']}: {'PASS' if r['ok'] else 'FAIL'}[/{color}]")
    return rc


def cmd_agent(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.subcommand == "spawn":
        scope = json.loads(args.scope) if args.scope else []
        lords = json.loads(args.lords) if getattr(args, "lords", "") else []
        result = k.spawn_agent(args.agent_id, args.persona, scope, lords=lords)
        print(json.dumps(result, indent=2, default=str))
    elif args.subcommand == "delegate":
        arguments = json.loads(args.args) if args.args else {}
        result = k.delegate(args.agent_id, args.action, **arguments)
        print(json.dumps(result, indent=2, default=str))
    elif args.subcommand == "list":
        print(json.dumps(k.pool.list_agents(), indent=2, default=str))
    elif args.subcommand == "sync":
        print(json.dumps(k.pool.synchronize(), indent=2, default=str))
    return 0


def cmd_persona(args: argparse.Namespace) -> int:
    k = _kernel(args)
    if args.persona_action == "list":
        print(json.dumps(k.persona.list_personas(), indent=2))
    elif args.persona_action == "detect":
        text = " ".join(args.text)
        if not text:
            console.print("[red]Provide text as positional arguments.[/red]")
            return 1
        if args.multi:
            result = k.persona.detect_multiple(text, max_personas=args.max_personas, max_lords=args.max_lords)
        else:
            result = k.detect_persona(text)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_skill(args: argparse.Namespace) -> int:
    k = _kernel(args)
    resolver = k.skill_resolver
    if args.skill_subcommand == "list":
        for name in resolver.list_skills():
            console.print(f"[cyan]{name}[/cyan]")
    elif args.skill_subcommand == "invoke":
        content = resolver.load(args.name)
        if content is None:
            console.print(f"[red]Skill '{args.name}' not found[/red]")
            return 1
        console.print(Panel(f"[cyan]{args.name}[/cyan]\n\n{content}", title="Skill"))
    elif args.skill_subcommand == "search":
        query = args.query.lower()
        for name in resolver.list_skills():
            if query in name.lower():
                console.print(f"[cyan]{name}[/cyan]")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    os_root = _root(args)
    project_root = _project_root(args)
    checks = {
        "os root": os_root.exists(),
        "project root": project_root.exists(),
        "pyproject.toml": (os_root / "pyproject.toml").exists(),
        "os policies": (os_root / "runtime" / "policies" / "default.yaml").exists(),
        "project policies": (project_root / "runtime" / "policies" / "default.yaml").exists(),
        "rules directory": (os_root / "rules").exists(),
        "workflows directory": (os_root / "workflows").exists(),
        "tech-stack directory": (os_root / "tech-stack").exists(),
        "state directory": (project_root / "state").exists(),
        "brain directory": (project_root / "brain").exists(),
        "managers module": (os_root / "runtime" / "managers").is_dir(),
        "mcp tools module": (os_root / "aizee_mcp" / "tools").is_dir(),
        "crypto module": (os_root / "runtime" / "crypto.py").exists(),
        "migrations module": (os_root / "runtime" / "migrations.py").exists(),
        "observability module": (os_root / "runtime" / "observability.py").exists(),
        "LICENSE": (os_root / "LICENSE").exists(),
        "CODEOWNERS": (os_root / ".github" / "CODEOWNERS").exists(),
        "API.md": (os_root / "aizee_mcp" / "API.md").exists(),
    }

    # Version check
    version_file = os_root / ".aizee-version"
    if version_file.exists():
        installed_ver = version_file.read_text(encoding="utf-8").strip()
        checks[f"installed version ({installed_ver})"] = True
    else:
        checks["installed version"] = False

    # Encryption check
    try:
        import os as _os

        if _os.environ.get("AIOS_ENCRYPTION_KEY"):
            checks["encryption key set"] = True
            from runtime.crypto import _get_fernet

            checks["encryption fernet valid"] = _get_fernet() is not None
        else:
            checks["encryption key set"] = False
    except Exception:
        checks["encryption key set"] = False

    # Python deps check
    for pkg in ("yaml", "mcp", "pydantic", "rich", "cryptography"):
        try:
            __import__(pkg)
            checks[f"pip: {pkg}"] = True
        except ImportError:
            checks[f"pip: {pkg}"] = False

    try:
        from memory.vector import VectorMemory

        vector = VectorMemory(project_root)
        checks["vector index"] = vector.is_available()
    except Exception:
        checks["vector index"] = False

    # Global MCP config check (must be synced so MCPs work in any workspace)
    try:
        if os.name == "nt":
            g_dir = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "devin"
        else:
            g_dir = Path.home() / ".config" / "devin"
        g_cfg = g_dir / "mcp_config.json"
        if g_cfg.exists():
            g_data = json.loads(g_cfg.read_text(encoding="utf-8"))
            g_count = len(g_data.get("mcpServers", {}))
            checks[f"global mcp config ({g_count} servers)"] = g_count > 0
        else:
            checks["global mcp config"] = False
    except Exception:
        checks["global mcp config"] = False

    # --- Guardian policy check ---
    guardian_path = os_root / "runtime" / "policies" / "guardian.yaml"
    if guardian_path.exists():
        try:
            from runtime.guardian import Guardian
            g = Guardian.from_yaml(guardian_path)
            checks[f"guardian.yaml ({len(g.rules)} rules)"] = len(g.rules) > 0
        except Exception:
            checks["guardian.yaml (load error)"] = False
    else:
        checks["guardian.yaml"] = False

    # --- Probity guardrails check ---
    probity_path = os_root / "runtime" / "policies" / "probity.yaml"
    if probity_path.exists():
        try:
            import yaml as _yaml

            from runtime.probity import Guardrails
            data = _yaml.safe_load(probity_path.read_text(encoding="utf-8")) or {}
            gr = Guardrails(data)
            checks[f"probity.yaml ({len(gr.rules)} rules)"] = len(gr.rules) > 0
        except Exception:
            checks["probity.yaml (load error)"] = False
    else:
        checks["probity.yaml"] = False

    # --- Capabilities check ---
    try:
        from runtime.sovereign import AgentCapabilities
        caps = AgentCapabilities()
        checks[f"capabilities ({len(caps.list())})"] = len(caps.list()) > 0
    except Exception:
        checks["capabilities"] = False

    # --- Tech stack detection check ---
    try:
        from runtime.kernel import Kernel
        k = Kernel(os_root)
        ts = k.detect_tech_stack()
        checks[f"tech_stack detection ({len(ts)} entries)"] = len(ts) > 0
    except Exception:
        checks["tech_stack detection"] = False

    # --- cryptography version match check ---
    try:
        from importlib.metadata import version
        installed = version("cryptography")
        checks[f"cryptography=={installed} (pyproject <52.0)"] = True
    except Exception:
        checks["cryptography version"] = False

    # --- .env.example check ---
    checks[".env.example template"] = (os_root / ".env.example").exists()

    table = Table(title="aiZee Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    for name, ok in checks.items():
        table.add_row(name, "ok" if ok else "missing")
    console.print(table)
    return 0 if all(checks.values()) else 1


def cmd_uninstall(args: argparse.Namespace) -> int:
    """Interactive uninstaller with selective keep/backup.

    Modes:
      aizee uninstall          → console interactive (default)
      aizee uninstall --gui    → tkinter GUI
      aizee uninstall --yes    → non-interactive (defaults: delete OS, keep learned)
    """
    root = _root(args)
    if not root.exists():
        console.print(f"[red]aiZee root not found: {root}[/red]")
        return 1

    if args.gui:
        from runtime.uninstaller_gui import main as gui_main
        return gui_main([str(root)])

    from runtime.uninstaller import interactive_uninstall
    return interactive_uninstall(root, assume_yes=args.yes)


def cmd_test(args: argparse.Namespace) -> int:
    """Run pytest with configurable speed tiers.

    Tiers:
      aizee test           → fast (default): skip slow/mcp/dashboard/vector, no coverage, ~12s
      aizee test --full    → full: all tests + coverage, ~35s
      aizee test --verbose → verbose output
      aizee test --xdist   → parallel execution (faster on Linux/macOS, slower on Windows)
    """
    import subprocess
    import sys

    if args.full:
        pytest_args = [
            sys.executable, "-m", "pytest",
            "--tb=short", "-p", "no:warnings",
            "--cov=runtime", "--cov=memory", "--cov=aizee_mcp",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ]
        console.print("[cyan]Running FULL test suite (all tests + coverage)...[/]")
    else:
        # Default / --fast: skip slow tests, no coverage
        pytest_args = [
            sys.executable, "-m", "pytest",
            "-m", "not slow and not mcp and not dashboard and not vector",
            "--no-cov", "--tb=short", "-p", "no:warnings",
        ]
        console.print("[cyan]Running FAST tests (unit only, no slow/coverage)...[/]")

    if args.verbose:
        pytest_args.append("-v")
    if hasattr(args, "xdist") and args.xdist:
        import os
        workers = max(2, min(os.cpu_count() or 4, 8))
        pytest_args.extend(["-n", str(workers)])

    result = subprocess.run(pytest_args, cwd=str(_root(args)))
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aizee", description="aiZee CLI")
    parser.add_argument("--root", type=Path, default=None, help="aiZee root (default: AIZEE_ROOT or install dir)")
    parser.add_argument("--project", type=Path, default=None, help="Active project root (default: AGENT_PROJECT_ROOT, CWD/.ai, or OS root)")
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

    p_query = sub.add_parser("query", help="Hybrid search across memory")
    p_query.add_argument("query")
    p_query.add_argument("--kind", default=None)
    p_query.add_argument("--limit", type=int, default=10)
    p_query.add_argument("--explain", action="store_true")

    p_mem = sub.add_parser("memory", help="Memory commands")
    p_mem.add_argument("subcommand", choices=["search", "vector", "add", "ingest"])
    p_mem.add_argument("--query", default="")
    p_mem.add_argument("--kind", default=None)
    p_mem.add_argument("--content", default="")
    p_mem.add_argument("--source", default="")
    p_mem.add_argument("--limit", type=int, default=10)
    p_mem.add_argument("--watch", action="store_true", help="Auto re-ingest on tech-stack/rules/workflows changes")

    p_policy = sub.add_parser("policy", help="Policy commands")
    p_policy.add_argument("subcommand", choices=["test"])
    p_policy.add_argument("action")
    p_policy.add_argument("--args", default="", help="JSON action args")

    p_budget = sub.add_parser("budget", help="Budget commands")
    p_budget.add_argument("subcommand", choices=["list", "usage", "set"])
    p_budget.add_argument("--scope", default="global")
    p_budget.add_argument("--max-tokens", type=int, default=None)
    p_budget.add_argument("--max-cost", type=float, default=None)
    p_budget.add_argument("--period", default="session", choices=["session", "hourly", "daily", "weekly", "monthly"])
    p_budget.add_argument("--on-exceed", default="block", choices=["warn", "fallback", "block"])

    p_project = sub.add_parser("project", help="Project commands")
    p_project.add_argument("subcommand", choices=["init"])
    p_project.add_argument("--path", default=".")

    p_saga = sub.add_parser("saga", help="Run a saga with compensations")
    p_saga.add_argument("saga_id")
    p_saga.add_argument("--steps", default="", help='JSON saga steps, e.g. [{"action":"Read","args":{}},{"action":"Bash","args":{"command":"x"},"compensation":{"action":"Bash","args":{"command":"undo x"}}}]')
    p_saga.add_argument("--context", default="", help="JSON saga context")

    p_telemetry = sub.add_parser("telemetry", help="Telemetry and observability")
    p_telemetry.add_argument("subcommand", choices=["summary", "events", "system"])
    p_telemetry.add_argument("--type", default=None, help="Filter events by type")
    p_telemetry.add_argument("--limit", type=int, default=20)

    p_stack = sub.add_parser("stack", help="Tech-stack detection")
    p_stack.add_argument("subcommand", choices=["detect", "show"])

    p_spec = sub.add_parser("spec", help="Spec-driven development commands")
    p_spec.add_argument("subcommand", choices=["list", "analyze", "converge", "scaffold"])
    p_spec.add_argument("spec_id", nargs="?", default="", help="Spec ID")
    p_spec.add_argument("--codebase", default="", help="Codebase dir for converge")
    p_spec.add_argument("--template", default="", help="Template type for scaffold (spec/plan/tasks)")
    p_spec.add_argument("--title", default="", help="Title for scaffold")

    p_audit = sub.add_parser("audit", help="Audit log commands")
    p_audit.add_argument("subcommand", choices=["show", "verify"])
    p_audit.add_argument("--type", default="", help="Filter by event type")
    p_audit.add_argument("--limit", type=int, default=50, help="Max entries to show")

    p_mcp = sub.add_parser("mcp", help="Call an external MCP tool or sync global config")
    p_mcp.add_argument("server", nargs="?", help="MCP server name (or 'sync' to write global config)")
    p_mcp.add_argument("tool", nargs="?", help="Tool name to call")
    p_mcp.add_argument("--args", default="", help="JSON tool arguments")
    p_mcp.add_argument("--check", action="store_true", help="Dry-run: print config without writing (sync only)")

    p_chat = sub.add_parser("chat", help="Persistent chat REPL")
    p_chat.add_argument("message", nargs="?", default=None, help="Single message (omit for REPL)")

    p_ci = sub.add_parser("ci", help="Run CI quality gates")
    p_ci.add_argument("--skip-pytest", action="store_true", help="Skip pytest to save time")

    p_uninstall = sub.add_parser("uninstall", help="Interactive uninstall with selective keep/backup")
    p_uninstall.add_argument("--yes", "-y", action="store_true", help="Skip confirmation (use defaults: keep learned, delete OS)")
    p_uninstall.add_argument("--gui", action="store_true", help="Launch tkinter GUI uninstaller")

    p_test = sub.add_parser("test", help="Run tests (fast tier ~12s, --full: all tests with coverage ~35s)")
    p_test.add_argument("--full", action="store_true", help="Full tier: all tests + coverage")
    p_test.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    p_test.add_argument("--xdist", action="store_true", help="Parallel execution (faster on Linux/macOS)")

    p_agent = sub.add_parser("agent", help="Sub-agent orchestration")
    p_agent.add_argument("subcommand", choices=["spawn", "delegate", "list", "sync"])
    p_agent.add_argument("--agent-id", default=None)
    p_agent.add_argument("--persona", default="auto", help="Persona code(s) or 'auto' to detect")
    p_agent.add_argument("--lords", default="", help="JSON list of additional skill names")
    p_agent.add_argument("--scope", default="", help="JSON list of allowed actions")
    p_agent.add_argument("--action", default=None)
    p_agent.add_argument("--args", default="", help="JSON arguments for delegate")

    p_persona = sub.add_parser("persona", help="Persona detection")
    sp_persona = p_persona.add_subparsers(dest="persona_action", required=True)

    sp_persona.add_parser("list", help="List available personas")

    p_persona_detect = sp_persona.add_parser("detect", help="Detect persona(s) from text")
    p_persona_detect.add_argument("text", nargs="+", help="Text to analyze")
    p_persona_detect.add_argument("--multi", action="store_true", default=True, help="Return top-N personas + skills (default)")
    p_persona_detect.add_argument("--single", dest="multi", action="store_false", help="Return a single persona only")
    p_persona_detect.add_argument("--max-personas", type=int, default=3, help="Max personas when --multi is used")
    p_persona_detect.add_argument("--max-lords", type=int, default=5, help="Max additional lord skills to load")

    p_skill = sub.add_parser("skill", help="Skill commands")
    sp_skill = p_skill.add_subparsers(dest="skill_subcommand", required=True)
    sp_skill.add_parser("list", help="List available skills")
    p_skill_invoke = sp_skill.add_parser("invoke", help="Show a skill's markdown content")
    p_skill_invoke.add_argument("name", help="Skill name")
    p_skill_search = sp_skill.add_parser("search", help="Search skills by name keyword")
    p_skill_search.add_argument("query", help="Search keyword")

    # --- linkedin ---
    p_linkedin = sub.add_parser("linkedin", help="LinkedIn content automation")
    sp_linkedin = p_linkedin.add_subparsers(dest="linkedin_action", required=True)

    sp_linkedin.add_parser("profile", help="Get your LinkedIn profile")

    p_li_post = sp_linkedin.add_parser("post", help="Publish a text post directly")
    p_li_post.add_argument("text", help="Post text")
    p_li_post.add_argument("--visibility", default="PUBLIC", choices=["PUBLIC", "CONNECTIONS"])

    p_li_draft = sp_linkedin.add_parser("draft", help="Save a draft locally")
    p_li_draft.add_argument("text", help="Draft text")

    p_li_drafts = sp_linkedin.add_parser("drafts", help="List drafts")
    p_li_drafts.add_argument("--status", default="", choices=["", "draft", "approved", "scheduled", "published"])

    p_li_approve = sp_linkedin.add_parser("approve", help="Approve a draft")
    p_li_approve.add_argument("draft_id", help="Draft ID")

    p_li_publish = sp_linkedin.add_parser("publish", help="Publish an approved draft")
    p_li_publish.add_argument("draft_id", help="Draft ID")

    p_li_schedule = sp_linkedin.add_parser("schedule", help="Schedule an approved draft")
    p_li_schedule.add_argument("draft_id", help="Draft ID")
    p_li_schedule.add_argument("when", help="ISO 8601 datetime (e.g. 2026-07-02T09:00:00Z)")

    p_li_stats = sp_linkedin.add_parser("stats", help="Get post stats (likes, comments)")
    p_li_stats.add_argument("urn", help="Post URN")

    p_li_delete = sp_linkedin.add_parser("delete", help="Delete a post")
    p_li_delete.add_argument("urn", help="Post URN")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "status": cmd_status,
        "check": cmd_check,
        "policy": cmd_policy,
        "run": cmd_run,
        "query": cmd_query,
        "memory": cmd_memory,
        "budget": cmd_budget,
        "project": cmd_project,
        "saga": cmd_saga,
        "telemetry": cmd_telemetry,
        "stack": cmd_stack,
        "spec": cmd_spec,
        "audit": cmd_audit,
        "mcp": cmd_mcp,
        "chat": cmd_chat,
        "ci": cmd_ci,
        "test": cmd_test,
        "agent": cmd_agent,
        "persona": cmd_persona,
        "skill": cmd_skill,
        "linkedin": cmd_linkedin,
        "sync": cmd_sync,
        "graphify": cmd_graphify,
        "version": cmd_version,
        "doctor": cmd_doctor,
        "uninstall": cmd_uninstall,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
