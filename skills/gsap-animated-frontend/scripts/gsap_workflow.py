#!/usr/bin/env python3
"""Internal workflow helper for the GSAP skill."""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import click
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    import yaml
except ImportError:
    print("Install dependencies first: pip install -r requirements.txt")
    sys.exit(1)

SCRIPT_PATH = Path(__file__).resolve().parent
if str(SCRIPT_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPT_PATH))

from brand_extractor import extract_brand_signals
from interview_generator import build_interview_questions, build_recommendations
from interview_strategy import build_interview_brief
from phase_planner import build_phases
from project_intelligence import build_project_intelligence
from structure_search import detect_routes, discover_page_structure

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

console = Console(force_terminal=True)
PACKAGE_DIR = SCRIPT_PATH.parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
SOURCE_EXTENSIONS = (".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte")
STYLE_EXTENSIONS = (".css", ".scss", ".sass", ".less")
SKIP_DIRS = {
    "node_modules",
    ".next",
    "dist",
    ".git",
    ".pnpm",
    "__pycache__",
    ".turbo",
    "build",
    "coverage",
}
ANIMATION_CONFIG_FILE = "gsap-animations.yaml"
MOTION_LIB_PATTERNS = {
    "GSAP": r"gsap|ScrollTrigger|useGSAP",
    "Framer Motion": r"framer-motion|motion\.",
    "Lenis": r"\bLenis\b",
    "AOS": r"\baos\b",
    "Anime.js": r"animejs|anime\(",
    "Motion One": r"motion-one|@motionone|animate\(",
    "Lottie": r"lottie|bodymovin",
    "React Spring": r"react-spring|useSpring|useTrail",
    "Three.js": r"\bthree\b|@react-three|fiber",
    "Locomotive Scroll": r"locomotive-scroll",
    "Barba.js": r"barba",
}


def find_project_root(start_path=".") -> Path:
    path = Path(start_path).resolve()
    while path != path.parent:
        if (path / "package.json").exists() or (path / ".git").exists():
            return path
        path = path.parent
    return Path(start_path).resolve()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_package_json(directory: Path):
    package_file = directory / "package.json"
    if not package_file.exists():
        return None
    try:
        return json.loads(package_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_candidate_apps(root: Path):
    candidates = [root]
    for rel in (
        "apps/web",
        "apps/site",
        "apps/frontend",
        "frontend",
        "client",
        "web",
        "site",
        "app",
        "src",
        "packages/ui",
        "packages/web",
    ):
        candidate = root / rel
        if candidate.exists():
            candidates.append(candidate)
    unique = []
    for item in candidates:
        if item not in unique:
            unique.append(item)
    return unique


def detect_framework(root: Path) -> str:
    for candidate in find_candidate_apps(root):
        package_data = load_package_json(candidate)
        if not package_data:
            continue
        deps = {
            **package_data.get("dependencies", {}),
            **package_data.get("devDependencies", {}),
        }
        if "next" in deps:
            return "next"
        if "react" in deps or "react-dom" in deps:
            return "react"
        if "vue" in deps:
            return "vue"
        if "svelte" in deps:
            return "svelte"
    return "vanilla"


def detect_package_manager(root: Path) -> str:
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists():
        return "bun"
    return "npm"


def collect_packages(root: Path):
    package_data = load_package_json(root) or {}
    deps = {
        **package_data.get("dependencies", {}),
        **package_data.get("devDependencies", {}),
    }
    if deps:
        return deps

    for candidate in find_candidate_apps(root):
        package_data = load_package_json(candidate)
        if package_data:
            deps = {
                **package_data.get("dependencies", {}),
                **package_data.get("devDependencies", {}),
            }
            if deps:
                return deps
    return {}


def get_scan_roots(root: Path):
    preferred = [
        root / "apps" / "web" / "src",
        root / "apps" / "web" / "app",
        root / "apps" / "web" / "pages",
        root / "apps" / "site" / "src",
        root / "apps" / "site" / "app",
        root / "apps" / "frontend" / "src",
        root / "frontend" / "src",
        root / "frontend" / "app",
        root / "client" / "src",
        root / "web" / "src",
        root / "site" / "src",
        root / "src",
        root / "app",
        root / "pages",
        root / "components",
        root / "sections",
        root / "layouts",
        root / "widgets",
        root / "features",
        root / "modules",
        root / "lib",
        root / "content",
        root / "packages" / "ui" / "src",
        root / "packages" / "web" / "src",
    ]
    roots = [path for path in preferred if path.exists()]
    return roots or [root]


def scan_files(root: Path, include_styles=False):
    files = []
    extensions = set(SOURCE_EXTENSIONS)
    if include_styles:
        extensions.update(STYLE_EXTENSIONS)

    def walk(directory: Path):
        try:
            for entry in directory.iterdir():
                if entry.is_dir():
                    if entry.name not in SKIP_DIRS:
                        walk(entry)
                elif entry.suffix in extensions:
                    files.append(entry)
        except (PermissionError, OSError):
            return

    for scan_root in get_scan_roots(root):
        walk(scan_root)
    return sorted(set(files))


def load_template(name: str, replacements: dict[str, str] | None = None) -> str:
    content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
    for key, value in (replacements or {}).items():
        content = content.replace(f"{{{{{key}}}}}", value)
    return content


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "page"


def ensure_workspace(root: Path, page: str, project_name: str | None = None):
    project_name = project_name or root.name
    page_slug = slugify(page)
    gsap_dir = root / ".gsap"
    pages_dir = gsap_dir / "pages"
    tasks_dir = gsap_dir / "tasks"
    phases_dir = gsap_dir / "phases" / page_slug
    for directory in (gsap_dir, pages_dir, tasks_dir, phases_dir):
        directory.mkdir(parents=True, exist_ok=True)

    created = []
    artifacts = {
        gsap_dir / "animation-spec.md": load_template("animation-spec.md", {"PROJECT_NAME": project_name}),
        gsap_dir / "animation-plan.md": load_template("animation-plan.md", {"PROJECT_NAME": project_name}),
        gsap_dir / "audit-report.md": load_template("audit-report.md", {"PROJECT_NAME": project_name}),
        tasks_dir / f"{page_slug}.tasks.md": load_template("animation-tasks.md", {"PROJECT_NAME": project_name}),
        pages_dir / f"{page_slug}.animation.md": load_template("page-animation.md", {"PAGE_NAME": page_slug}),
    }
    for path, content in artifacts.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)

    return created


def replace_or_append_section(content: str, heading: str, lines: list[str]) -> str:
    block = f"## {heading}\n\n" + "\n".join(lines).rstrip() + "\n"
    pattern = rf"\n## {re.escape(heading)}\n.*?(?=\n## |\Z)"
    if re.search(pattern, content, flags=re.S):
        return re.sub(pattern, "\n" + block, content, flags=re.S)
    content = content.rstrip() + "\n\n" + block
    return content


def set_field(content: str, label: str, value: str) -> str:
    lines = content.splitlines()
    updated = False
    target_prefix = f"- {label}:"
    for index, line in enumerate(lines):
        if line.startswith(target_prefix):
            lines[index] = f"{target_prefix} {value}"
            updated = True
            break
    if not updated:
        lines.append(f"{target_prefix} {value}")
    return "\n".join(lines) + "\n"


def markdown_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in rows:
        safe = [str(cell).replace("\n", " ").replace("|", "/") for cell in row]
        lines.append("| " + " | ".join(safe) + " |")
    return lines


def package_summary(packages: dict):
    interesting = []
    for name in [
        "gsap",
        "@gsap/react",
        "next",
        "react",
        "tailwindcss",
        "framer-motion",
        "lenis",
        "three",
        "@react-three/fiber",
        "lottie-web",
        "animejs",
        "locomotive-scroll",
        "react-spring",
        "typescript",
    ]:
        if name in packages:
            interesting.append(f"{name}@{packages[name]}")
    return interesting


def infrastructure_lines(discovery: dict) -> list[str]:
    infrastructure = discovery["project_intelligence"]["infrastructure"]
    if not infrastructure:
        return ["  - None strongly inferred"]
    lines = []
    for label, values in infrastructure.items():
        lines.append(f"  - {label}: {', '.join(values)}")
    return lines


def infer_page_route(page: str, discovery: dict) -> str:
    token = slugify(page)
    routes = discovery["routes"]
    aliases = {f"/{token}", f"/{token.replace('-', '')}"}
    if token in {"home", "homepage", "landing", "index"} and "/" in routes:
        return "/"
    for route in routes:
        if route in aliases:
            return route
    return page if page.startswith("/") else f"/{token}"


def discover_motion_stack(root: Path):
    files = scan_files(root)
    counts = Counter()
    for source_file in files:
        content = read_text(source_file)
        for name, pattern in MOTION_LIB_PATTERNS.items():
            if re.search(pattern, content, flags=re.I):
                counts[name] += 1
    return counts


def discover_project(root: Path, page: str):
    packages = collect_packages(root)
    page_structure = discover_page_structure(root, page, scan_files, read_text, slugify)
    motion_stack = discover_motion_stack(root)
    design_tokens = extract_brand_signals(root, scan_files, read_text)
    routes = detect_routes(root, get_scan_roots)
    project_intelligence = build_project_intelligence(
        {
            "packages": packages,
            "page_structure": page_structure,
            "motion_stack": motion_stack,
            "design_tokens": design_tokens,
            "routes": routes,
        }
    )

    return {
        "root": root,
        "framework": detect_framework(root),
        "package_manager": detect_package_manager(root),
        "packages": packages,
        "routes": routes,
        "page_structure": page_structure,
        "motion_stack": motion_stack,
        "design_tokens": design_tokens,
        "project_intelligence": project_intelligence,
    }


def write_phase_files(root: Path, page: str, phases: list[dict]):
    page_slug = slugify(page)
    phases_dir = root / ".gsap" / "phases" / page_slug
    created = []
    for phase in phases:
        task_lines = "\n".join(f"- [ ] {task}" for task in phase["tasks"])
        content = load_template(
            "phase.md",
            {
                "PHASE_ID": phase["id"],
                "PAGE_NAME": page_slug,
                "SECTION_NAME": phase["section"],
                "RECIPE": phase["recipe"],
                "OBJECTIVE": phase["objective"],
                "TASKS": task_lines,
            },
        )
        phase_path = phases_dir / f"{phase['id'].lower()}-{slugify(phase['section'])}.md"
        if not phase_path.exists():
            created.append(phase_path)
        write_text(phase_path, content)
    return created


def update_animation_spec(root: Path, page: str, discovery: dict, questions: list[str], phases: list[dict], mode: str, interview_brief: dict):
    spec_path = root / ".gsap" / "animation-spec.md"
    content = read_text(spec_path)

    package_lines = package_summary(discovery["packages"]) or ["No notable frontend packages detected."]
    color_lines = discovery["design_tokens"]["colors"] or ["No color tokens detected yet."]
    font_lines = discovery["design_tokens"]["fonts"] or ["No font tokens detected yet."]
    tone_lines = discovery["design_tokens"]["tone_hints"] or ["No strong tone keywords detected yet."]

    content = set_field(content, "Owner Workflow", mode)
    content = replace_or_append_section(
        content,
        "Discovery Snapshot",
        [
            f"- Framework: {discovery['framework']}",
            f"- Package Manager: {discovery['package_manager']}",
            "- Packages:",
            *[f"  - {item}" for item in package_lines],
            f"- Routes Detected: {', '.join(discovery['routes'][:12]) if discovery['routes'] else 'None detected'}",
        ],
    )
    content = replace_or_append_section(
        content,
        "Brand And Design Signals",
        [
            "- Colors:",
            *[f"  - {item}" for item in color_lines],
            "- Fonts:",
            *[f"  - {item}" for item in font_lines],
            "- Tone Hints:",
            *[f"  - {item}" for item in tone_lines],
            "- CSS Variables:",
            *[f"  - {item}" for item in (discovery['design_tokens']['css_vars'] or ['None detected'])],
            "- Visual Direction:",
            *[f"  - {item}" for item in (discovery['design_tokens']['visual_direction'] or ['Not inferred yet'])],
            f"- Blur Usage Signals: {discovery['design_tokens']['blur_usage']}",
            f"- Backdrop Filter Signals: {discovery['design_tokens']['backdrop_usage']}",
        ],
    )
    content = replace_or_append_section(
        content,
        "Questions To Resolve",
        [f"- {question}" for question in interview_brief["priority_questions"]] or ["- No blocking discovery questions right now."],
    )
    content = replace_or_append_section(
        content,
        "Project Intelligence",
        [
            f"- Inferred Archetypes: {', '.join(discovery['project_intelligence']['archetypes'])}",
            "- Supporting Infrastructure:",
            *infrastructure_lines(discovery),
            "- Project Constraints:",
            *[f"  - {item}" for item in discovery["project_intelligence"]["constraints"]],
        ],
    )
    content = replace_or_append_section(
        content,
        "Interview Strategy",
        [
            f"- Interview Mode: {interview_brief['interview_mode']}",
            f"- Priority Categories: {', '.join(interview_brief['categories']) if interview_brief['categories'] else 'None'}",
            "- Priority Questions:",
            *[f"  - {item}" for item in interview_brief["priority_questions"]],
        ],
    )
    content = replace_or_append_section(
        content,
        "Phase Strategy",
        [
            f"- Active Page: {page}",
            "- Rule: implement one major section per phase.",
            f"- Planned Phase Count: {len(phases)}",
            f"- First Phase: {phases[0]['id']} - {phases[0]['section']}" if phases else "- First Phase: Not generated",
        ],
    )
    write_text(spec_path, content)


def update_page_artifact(root: Path, page: str, discovery: dict, mode: str, questions: list[str], recommendations: list[str], phases: list[dict], interview_brief: dict):
    page_slug = slugify(page)
    page_path = root / ".gsap" / "pages" / f"{page_slug}.animation.md"
    content = read_text(page_path)
    page_structure = discovery["page_structure"]
    active_phase = phases[0]["id"] if phases else "None"

    content = set_field(content, "Page Route", infer_page_route(page, discovery))
    content = set_field(content, "Source File", page_structure["source_file"] or "Manual mapping needed")
    content = set_field(content, "Page Status", "Needs phased implementation plan" if mode == "gsap-new" else "Needs phased refactor")
    content = set_field(content, "Active Phase", active_phase)
    content = replace_or_append_section(
        content,
        "Discovery Snapshot",
        [
            f"- Matched Files: {', '.join(file.name for file in page_structure['page_files'][:8]) if page_structure['page_files'] else 'No direct matches found'}",
            f"- Sections Detected: {', '.join(page_structure['sections']) if page_structure['sections'] else 'No obvious section types detected'}",
            f"- Repeated Components: {', '.join(page_structure['repeated_components']) if page_structure['repeated_components'] else 'None detected'}",
            f"- Structure Patterns: {', '.join(page_structure['patterns']) if page_structure['patterns'] else 'No strong patterns inferred'}",
            f"- Selector Samples: {', '.join(page_structure['selector_keywords'][:8]) if page_structure['selector_keywords'] else 'None detected'}",
        ],
    )
    content = replace_or_append_section(
        content,
        "Resume State",
        [
            f"- Next Agent Action: open phase {active_phase} and implement only that section.",
            f"- Blocking Questions: {' | '.join(interview_brief['priority_questions']) if interview_brief['priority_questions'] else 'None from auto-discovery'}",
            "- Discovery Confidence: Medium unless the agent verifies source files manually.",
            f"- Active Phase: {active_phase}",
        ],
    )
    content = replace_or_append_section(
        content,
        "Recommended Motion Directions",
        [f"- {item}" for item in recommendations] or ["- Manual motion direction needed."],
    )
    content = replace_or_append_section(
        content,
        "Scenario Notes",
        [
            f"- Inferred Product Type: {', '.join(discovery['project_intelligence']['archetypes'])}",
            "- Motion Constraints:",
            *[f"  - {item}" for item in discovery["project_intelligence"]["constraints"]],
        ],
    )
    phase_rows = [
        [phase["id"], phase["section"], phase["recipe"], phase["status"], phase["objective"]]
        for phase in phases
    ]
    content = replace_or_append_section(
        content,
        "Phase Status",
        markdown_table(["Phase", "Section", "Recipe", "Status", "Notes"], phase_rows),
    )
    write_text(page_path, content)


def update_plan_artifact(root: Path, page: str, discovery: dict, mode: str, questions: list[str], recommendations: list[str], phases: list[dict], interview_brief: dict):
    plan_path = root / ".gsap" / "animation-plan.md"
    content = read_text(plan_path)
    page_slug = slugify(page)
    page_structure = discovery["page_structure"]
    active_phase = phases[0]["id"] if phases else "None"

    content = set_field(content, "Current Mode", mode)
    content = set_field(content, "Resume State", "Discovery complete, phased execution pending")
    content = set_field(content, "Active Phase", active_phase)
    content = set_field(content, "Suggested Next Command", f"Implement {active_phase} only, then update all .gsap artifacts.")
    content = replace_or_append_section(
        content,
        f"Workflow Snapshot - {page_slug}",
        [
            f"- Mode: {mode}",
            f"- Framework: {discovery['framework']}",
            f"- Package Manager: {discovery['package_manager']}",
            f"- Existing Motion Stack: {', '.join(discovery['motion_stack'].keys()) if discovery['motion_stack'] else 'No motion libraries detected'}",
            f"- Matched Files: {', '.join(file.name for file in page_structure['page_files'][:8]) if page_structure['page_files'] else 'No direct matches'}",
            f"- Inferred Product Type: {', '.join(discovery['project_intelligence']['archetypes'])}",
        ],
    )
    content = replace_or_append_section(
        content,
        f"Implementation Plan - {page_slug}",
        [
            "- Read .gsap artifacts before editing code.",
            "- Work in one major section phase at a time.",
            "- Finish hero or top-priority story beat before supporting sections.",
            "- Add spectacle only where the story earns it.",
            "- Update phase, tasks, and page artifacts after each section.",
        ],
    )
    recipe_rows = [[page_slug, phase["section"], phase["recipe"], phase["status"], phase["objective"]] for phase in phases]
    content = replace_or_append_section(
        content,
        "Recipes By Section",
        markdown_table(["Page", "Section", "Recipe", "Status", "Notes"], recipe_rows),
    )
    phase_rows = [[phase["id"], page_slug, phase["section"], phase["objective"], phase["recipe"], phase["status"]] for phase in phases]
    content = replace_or_append_section(
        content,
        "Phases",
        markdown_table(["Phase", "Page", "Section", "Objective", "Recipe", "Status"], phase_rows),
    )
    content = replace_or_append_section(
        content,
        f"Detected Project Signals - {page_slug}",
        [
            f"- Sections: {', '.join(page_structure['sections']) if page_structure['sections'] else 'Not inferred'}",
            f"- Structure Patterns: {', '.join(page_structure['patterns']) if page_structure['patterns'] else 'Not inferred'}",
            f"- Selector Samples: {', '.join(page_structure['selector_keywords'][:10]) if page_structure['selector_keywords'] else 'None detected'}",
            f"- Infrastructure: {', '.join(discovery['project_intelligence']['infrastructure'].keys()) if discovery['project_intelligence']['infrastructure'] else 'None strongly inferred'}",
            "- Recommendations:",
            *[f"  - {item}" for item in recommendations],
            "- Open Questions:",
            *[f"  - {item}" for item in (interview_brief["priority_questions"] or ['None from auto-discovery'])],
            "- Constraints:",
            *[f"  - {item}" for item in discovery["project_intelligence"]["constraints"]],
        ],
    )
    write_text(plan_path, content)


def update_tasks_artifact(root: Path, page: str, phases: list[dict]):
    page_slug = slugify(page)
    tasks_path = root / ".gsap" / "tasks" / f"{page_slug}.tasks.md"
    content = read_text(tasks_path)
    active_phase = phases[0]["id"] if phases else "None"

    queue_rows = [[phase["id"], page_slug, phase["section"], phase["objective"], phase["status"]] for phase in phases]
    content = replace_or_append_section(
        content,
        "Current Queue",
        markdown_table(["Phase", "Page", "Section", "Goal", "Status"], queue_rows),
    )
    active_checklist = ["- [ ] No phases generated yet."]
    if phases:
        active_checklist = [
            f"- [ ] Open `.gsap/phases/{page_slug}/{phases[0]['id'].lower()}-{slugify(phases[0]['section'])}.md`.",
            f"- [ ] Implement only the {phases[0]['section']} section in this pass.",
            "- [ ] Verify reduced motion and mobile behavior.",
            "- [ ] Update plan, page, and phase artifacts.",
            "- [ ] Only then move to the next phase.",
        ]
    content = replace_or_append_section(content, "Active Phase Checklist", active_checklist)
    content = set_field(content, "Execution Style", "one phase at a time")
    content = set_field(content, "Active Phase", active_phase)
    write_text(tasks_path, content)


def update_audit_artifact(root: Path, page: str, discovery: dict, questions: list[str], recommendations: list[str], phases: list[dict], interview_brief: dict):
    audit_path = root / ".gsap" / "audit-report.md"
    content = read_text(audit_path)
    page_slug = slugify(page)
    motion_stack = discovery["motion_stack"]
    page_structure = discovery["page_structure"]
    findings = []

    if "GSAP" not in motion_stack:
        findings.append("GSAP does not appear to be implemented yet on the matched files.")
    if "Hero" in page_structure["sections"] and "Feature Grid" in page_structure["sections"]:
        findings.append("Hero and repeated-card motion should not carry equal visual weight.")
    if not discovery["design_tokens"]["colors"]:
        findings.append("No obvious brand color tokens were detected automatically; visual direction may need manual confirmation.")
    if "3D or canvas surface" in page_structure["patterns"]:
        findings.append("3D or canvas sections need deliberate fallbacks and should be isolated to specific phases.")
    if not findings:
        findings.append("Existing page signals were detected; proceed with a careful phased refactor rather than a full reset.")

    content = set_field(content, "Last Audit Mode", "gsap-refactor")
    content = replace_or_append_section(
        content,
        f"Refactor Snapshot - {page_slug}",
        [
            f"- Existing Motion Stack: {', '.join(motion_stack.keys()) if motion_stack else 'None detected'}",
            f"- Matched Files: {', '.join(file.name for file in page_structure['page_files'][:8]) if page_structure['page_files'] else 'No direct matches'}",
            f"- Planned Phases: {', '.join(phase['id'] + ' ' + phase['section'] for phase in phases) if phases else 'None'}",
            "- Findings:",
            *[f"  - {item}" for item in findings],
            "- Recommended Improvements:",
            *[f"  - {item}" for item in recommendations],
            "- Open Questions:",
            *[f"  - {item}" for item in (interview_brief["priority_questions"] or ['None from auto-discovery'])],
            "- Constraints:",
            *[f"  - {item}" for item in discovery["project_intelligence"]["constraints"]],
        ],
    )
    write_text(audit_path, content)


def render_summary_table(discovery: dict, page: str, questions: list[str], phases: list[dict]):
    table = Table(title=f"GSAP Discovery - {page}")
    table.add_column("Signal", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Framework", discovery["framework"])
    table.add_row("Package manager", discovery["package_manager"])
    table.add_row("Routes detected", str(len(discovery["routes"])))
    table.add_row("Matched files", ", ".join(file.name for file in discovery["page_structure"]["page_files"][:5]) or "None")
    table.add_row("Sections", ", ".join(discovery["page_structure"]["sections"]) or "Not inferred")
    table.add_row("Motion stack", ", ".join(discovery["motion_stack"].keys()) if discovery["motion_stack"] else "None detected")
    table.add_row("Questions", str(len(questions)))
    table.add_row("Phases", ", ".join(phase["id"] for phase in phases) if phases else "None")
    return table


def orchestrate(mode: str, path: str, page: str, project_name: str | None):
    root = find_project_root(path)
    created = ensure_workspace(root, page, project_name)
    discovery = discover_project(root, page)
    questions = build_interview_questions(discovery, mode)
    interview_brief = build_interview_brief(questions, discovery, mode)
    recommendations = build_recommendations(discovery, mode)
    phases = build_phases(page, discovery, mode)
    created.extend(write_phase_files(root, page, phases))

    update_animation_spec(root, page, discovery, questions, phases, mode, interview_brief)
    update_page_artifact(root, page, discovery, mode, questions, recommendations, phases, interview_brief)
    update_plan_artifact(root, page, discovery, mode, questions, recommendations, phases, interview_brief)
    update_tasks_artifact(root, page, phases)
    if mode == "gsap-refactor":
        update_audit_artifact(root, page, discovery, questions, recommendations, phases, interview_brief)

    console.print(
        Panel(
            f"[bold cyan]{mode}[/] prepared workflow state for [bold white]{page}[/]\n"
            f"[dim]framework: {discovery['framework']} | package manager: {discovery['package_manager']} | phases: {len(phases)}[/]",
            border_style="cyan",
        )
    )
    if created:
        for created_path in created:
            console.print(f"[green]Created[/] {created_path}")
    console.print(render_summary_table(discovery, page, questions, phases))


@click.group()
def cli():
    """Internal GSAP workflow helper."""


@cli.command(name="gsap-new")
@click.option("--path", default=".", help="Project root path")
@click.option("--page", required=True, help="Page or section name")
@click.option("--project-name", default=None, help="Display name written into templates")
def gsap_new(path, page, project_name):
    """Bootstrap and orchestrate new-page workflow state."""
    orchestrate("gsap-new", path, page, project_name)


@cli.command(name="gsap-refactor")
@click.option("--path", default=".", help="Project root path")
@click.option("--page", required=True, help="Page or component name")
@click.option("--project-name", default=None, help="Display name written into templates")
def gsap_refactor(path, page, project_name):
    """Bootstrap and orchestrate refactor workflow state."""
    orchestrate("gsap-refactor", path, page, project_name)


@cli.command(name="_status", hidden=True)
@click.option("--path", default=".", help="Project root path")
def internal_status(path):
    root = find_project_root(path)
    gsap_dir = root / ".gsap"
    table = Table(title=".gsap Status")
    table.add_column("Artifact")
    table.add_column("Present")
    for artifact in [
        "animation-spec.md",
        "animation-plan.md",
        "audit-report.md",
        "pages",
        "tasks",
        "phases",
    ]:
        target = gsap_dir / artifact
        table.add_row(artifact, "yes" if target.exists() else "no")
    console.print(table)


@cli.command(name="_config", hidden=True)
@click.option("--path", default=".", help="Project root path")
def internal_config(path):
    root = find_project_root(path)
    config_path = root / ANIMATION_CONFIG_FILE
    if not config_path.exists():
        console.print("No gsap config found.")
        return
    console.print(config_path.read_text(encoding="utf-8"))


@cli.command(name="_init", hidden=True)
@click.option("--path", default=".", help="Project root path")
def internal_init(path):
    root = find_project_root(path)
    config_path = root / ANIMATION_CONFIG_FILE
    if not config_path.exists():
        config = {
            "version": "3.1",
            "project": {
                "name": root.name,
                "framework": detect_framework(root),
                "package_manager": detect_package_manager(root),
            },
            "performance": {"reduced_motion": True, "device_priority": "mobile-first"},
        }
        config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")
    console.print(f"Initialized {config_path}")


def main():
    cli()


if __name__ == "__main__":
    main()
