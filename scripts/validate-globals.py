#!/usr/bin/env python3
# AI Globals Validation Script (Python) v4.21.0
# Source of truth validator — PowerShell wrapper delegates to this script.

import argparse
import hashlib
import math
import os
import re
import sys

AI_TITLE_TAGS = ("FILE", "TECH", "WORKFLOW", "SKILL")

class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    RESET = '\033[0m'

class ValidationContext:
    def __init__(self, fix: bool, interactive: bool, dry_run: bool, force: bool) -> None:
        self.fix = fix
        self.interactive = interactive
        self.dry_run = dry_run
        self.force = force
        self.scanned_count = 0
        self.skipped_count = 0
        self.error_count = 0
        self.warning_count = 0
        self.healed_count = 0
        self.global_headers: dict[str, list[str]] = {}
        self.defined_codes: set = set()

def cprint(text: str, color: str = Colors.RESET) -> None:
    if sys.stdout.isatty():
        print(f"{color}{text}{Colors.RESET}")
    else:
        print(text)

def calculate_entropy(data: str) -> float:
    if not data:
        return 0.0
    freq: dict[str, int] = {}
    for ch in data:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(data)
    return -sum((c / total) * math.log(c / total, 2) for c in freq.values())

def get_fuzzy_match(target: str, file_list: list[str]) -> str | None:
    norm = os.path.normpath(target).lower()
    for f in file_list:
        if os.path.normpath(f).lower() == norm:
            return f
    base = os.path.basename(norm)
    for f in file_list:
        if os.path.basename(f).lower() == base:
            return f
    for f in file_list:
        if base in os.path.basename(f).lower():
            return f
    return None

def collect_rule_files(global_path: str) -> list[str]:
    ignore_lines: list[str] = []
    ignore_file = os.path.join(global_path, ".aiignore")
    if os.path.exists(ignore_file):
        with open(ignore_file, encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith('#'):
                    ignore_lines.append(s.replace('/', os.sep))

    rule_files: list[str] = []
    for fname in os.listdir(global_path):
        if fname.endswith('.md') and os.path.isfile(os.path.join(global_path, fname)):
            rule_files.append(fname)

    for d in ('rules', 'tech-stack', 'workflows', 'skills'):
        dir_path = os.path.join(global_path, d)
        if os.path.exists(dir_path):
            for root, _, files in os.walk(dir_path):
                for fname in files:
                    if fname.endswith('.md'):
                        rule_files.append(os.path.relpath(os.path.join(root, fname), global_path))

    filtered: list[str] = []
    for rf in rule_files:
        if not any(pat in rf for pat in ignore_lines):
            filtered.append(rf)
    return filtered

def load_manifest(manifest_path: str) -> dict[str, str]:
    manifest: dict[str, str] = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, encoding='utf-8') as f:
            for line in f:
                m = re.match(r"^\s*([A-Fa-f0-9]{64})\s+(.+)$", line)
                if m:
                    manifest[m.group(2).strip()] = m.group(1).lower()
    return manifest

def check_core_rules(global_path: str, manifest: dict[str, str]) -> bool:
    core_files = ["global-workflow.md", "global-roles.md"]
    rules_dir = os.path.join(global_path, "rules")
    if os.path.exists(rules_dir):
        for f in os.listdir(rules_dir):
            if f.endswith(".md"):
                core_files.append(os.path.join("rules", f))
    for cf in core_files:
        cf_path = os.path.join(global_path, cf)
        if os.path.exists(cf_path):
            with open(cf_path, 'rb') as f:
                h = hashlib.sha256(f.read()).hexdigest()
            if manifest.get(cf) != h:
                cprint(f"Core rule change in {cf} — forcing full scan.", Colors.YELLOW)
                return True
    return False

def extract_headers(content: str) -> list[str]:
    return [m.group(1).strip() for m in re.finditer(r"(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+", content)]

def decode_content(raw: bytes) -> str:
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')

def _body_after_frontmatter(content: str) -> str:
    """Return file body, stripping YAML frontmatter (--- ... ---) if present."""
    stripped = content.lstrip()
    if not stripped.startswith('---'):
        return stripped
    end = stripped.find('\n---', 3)
    return stripped[end + 4:].lstrip() if end != -1 else stripped

def is_ai_file(content: str) -> bool:
    """True if the file (or its body after YAML frontmatter) starts with an AI tag."""
    body = _body_after_frontmatter(content)
    first_line = body.split('\n')[0].strip()
    return any(first_line.startswith(f"[{tag}]") for tag in AI_TITLE_TAGS)

def _has_yaml_frontmatter_name(content: str) -> bool:
    stripped = content.lstrip()
    if not stripped.startswith('---'):
        return False
    end = stripped.find('\n---', 3)
    if end == -1:
        return False
    front = stripped[:end]
    return bool(re.search(r"(?m)^name\s*:", front))

def check_title(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    """Accept [FILE]/[TECH]/[WORKFLOW]/[SKILL] (AI files), YAML frontmatter with name:
    (package skills), or # H1 / <h1> (human docs)."""
    if is_ai_file(content):
        return False
    if _has_yaml_frontmatter_name(content):
        return False
    if re.search(r"(?m)^#\s+.+", content) or re.search(r"(?i)<h1>.+</h1>", content):
        return False
    cprint(f"ERROR: Missing title in {rel_name} (no AI tag, YAML name:, or # H1)", Colors.RED)
    ctx.error_count += 1
    return True

def check_struct(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    """AI files with [SKILL]/[FILE]/[TECH]/[WORKFLOW] in body MUST have [OBJ] and [RULES]."""
    if not is_ai_file(content):
        return False
    error = False
    if "[OBJ]" not in content:
        cprint(f"ERROR: Missing [OBJ] in AI file {rel_name}", Colors.RED)
        ctx.error_count += 1
        error = True
    if "[RULES]" not in content:
        cprint(f"ERROR: Missing [RULES] in AI file {rel_name}", Colors.RED)
        ctx.error_count += 1
        error = True
    return error

def check_line_endings(content: str, rel_name: str, ctx: ValidationContext) -> tuple[str, bool]:
    if "\r\n" not in content:
        return content, False
    if ctx.fix:
        ctx.healed_count += 1
        cprint(f"Fixed CRLF in {rel_name}", Colors.GRAY)
        return content.replace("\r\n", "\n"), True
    cprint(f"WARNING: CRLF in {rel_name}.", Colors.YELLOW)
    ctx.warning_count += 1
    return content, False

def check_utf8_bom(content: str, file_path: str, rel_name: str, ctx: ValidationContext) -> tuple[str, bool]:
    with open(file_path, 'rb') as f:
        hdr = f.read(3)
    if hdr != b'\xef\xbb\xbf':
        return content, False
    if ctx.fix:
        if content.startswith('\ufeff'):
            content = content[1:]
        ctx.healed_count += 1
        cprint(f"Stripped BOM in {rel_name}", Colors.GRAY)
        return content, True
    cprint(f"WARNING: UTF-8 BOM in {rel_name}.", Colors.YELLOW)
    ctx.warning_count += 1
    return content, False

def check_secrets(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    pat = re.compile(
        r'(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)'
        r'\s*[:=]\s*[\'"]?([a-zA-Z0-9\/\+\-_=]{20,})[\'"]?'
    )
    mocks = ('placeholder', 'your_', 'secret_here', 'token_here', 'example', 'mysecret', 'dummy', 'xxxx')
    error = False
    for m in pat.finditer(content):
        val = m.group(2)
        if any(mk in val.lower() for mk in mocks):
            continue
        if calculate_entropy(val) > 3.0:
            cprint(f"ERROR: Potential SECRET in {rel_name}: {m.group(0)}", Colors.RED)
            error = True
            ctx.error_count += 1
    return error

def check_mojibake(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    if re.search(r"(\xC3\xA2\x80\x9C|\xC3\xA2\x80\x9D|\xE2\x80\x9C|\xE2\x80\x9D|\uFFFD)", content):
        cprint(f"ERROR: Mojibake in {rel_name}.", Colors.RED)
        ctx.error_count += 1
        return True
    return False

def check_symbolic_codes(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    if "vocabulary.md" in rel_name:
        return False
    error = False
    for m in re.finditer(r"\[([A-Z]{3,4}-\d{2})\]", content):
        code = m.group(1)
        if code not in ctx.defined_codes:
            cprint(f"ERROR: Undefined code [{code}] in {rel_name} (not in rules/vocabulary.md)", Colors.RED)
            error = True
            ctx.error_count += 1
    return error

def handle_broken_section(content: str, raw_t: str, resolved: str, sec: str,
                           rel_name: str, ctx: ValidationContext) -> tuple[str, bool, bool]:
    near = next((h for h in ctx.global_headers[resolved] if h.startswith(sec) or sec.startswith(h)), None)
    if ctx.fix and near and (not ctx.interactive or input(f"Fix §{sec}->§{near} in {rel_name}? [Y/N]: ").strip().upper() == 'Y'):
        content = content.replace(f"{raw_t} §{sec}", f"{raw_t} §{near}")
        ctx.healed_count += 1
        cprint(f"Healed §{sec}->§{near} in {rel_name}", Colors.GRAY)
        return content, False, True
    cprint(f"ERROR: Broken ref §{sec} in {rel_name} (target: {resolved})", Colors.RED)
    ctx.error_count += 1
    return content, True, False

def check_cross_references(content: str, rel_name: str, ctx: ValidationContext) -> tuple[str, bool, bool]:
    error, modified = False, False
    for ref in re.finditer(r"([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)", content):
        raw_t, sec = ref.group(1), ref.group(2)
        target = raw_t.replace("/", os.sep)
        resolved = get_fuzzy_match(target, list(ctx.global_headers.keys()))
        if not resolved:
            cprint(f"ERROR: Broken ref in {rel_name}: '{target}' not found", Colors.RED)
            error = True
            ctx.error_count += 1
        elif sec not in ctx.global_headers[resolved]:
            content, err, mod = handle_broken_section(content, raw_t, resolved, sec, rel_name, ctx)
            error = error or err
            modified = modified or mod
        elif ctx.fix and target != resolved:
            if not ctx.interactive or input(f"Fix path '{target}'->'{resolved}' in {rel_name}? [Y/N]: ").strip().upper() == 'Y':
                content = content.replace(raw_t, resolved.replace(os.sep, "/"))
                modified = True
                ctx.healed_count += 1
    return content, error, modified

IGNORED_FILE_REFS = {
    'monthely-maintenance-prompt.md', 'nuxt-4.md', 'bun-1.md', 'drizzle-orm.md',
    '09-ai-review.md', 'mobile-standards.md', 'gemini.md', 'workflows\\nn-name.md',
    'tech-stack\\xxx.md', 'verification-patterns.md', 'filename.md', 'bug_report.md',
    'feature_request.md', 'tech_stack_request.md', 'pull_request_template.md',
    'active-context.md', 'skill.md', 'memory-archive.md',
    # project-specific placeholder files (referenced conceptually, not tracked)
    'spec.md', 'plan.md', 'tasks.md', 'pxx-name.md',
    # external/generated files (agent config, graphify output, ponytail ledger)
    'claude.md', 'agents.md', 'graph_report.md', 'ponytail-debt.md',
}

def check_file_references(content: str, rel_name: str, ctx: ValidationContext, global_path: str) -> bool:
    error = False
    for ref in re.finditer(r"(?<![\w/])(\.?[\w\-./]+\.md)\b", content):
        raw_t = ref.group(1)
        if re.match(r"^\s+[§S]\s*\d+", content[ref.end():]):
            continue
        # Skip wildcard/template references like .gsap/pages/*.animation.md or .gsap/pages/<page>.animation.md
        prefix = content[max(0, ref.start()-40):ref.start()]
        if '*' in prefix or '<' in prefix or '>' in prefix:
            continue
        target = raw_t.replace("/", os.sep)
        if "server" + os.sep + ".ai" in target:
            target = target.split("server" + os.sep + ".ai" + os.sep)[-1]
        base = os.path.basename(target).lower()
        if target.lower() in IGNORED_FILE_REFS or base in IGNORED_FILE_REFS:
            continue
        if get_fuzzy_match(target, list(ctx.global_headers.keys())):
            continue
        if os.path.exists(os.path.join(global_path, target)):
            continue
        cprint(f"ERROR: Broken file ref in {rel_name}: '{raw_t}' not found", Colors.RED)
        error = True
        ctx.error_count += 1
    return error

def check_trailing_newlines(content: str, rel_name: str, ctx: ValidationContext) -> tuple[str, bool]:
    if not content.endswith("\n"):
        if ctx.fix:
            ctx.healed_count += 1
            cprint(f"Added trailing newline to {rel_name}", Colors.GRAY)
            return content + "\n", True
        cprint(f"WARNING: Missing trailing newline in {rel_name}.", Colors.YELLOW)
        ctx.warning_count += 1
    elif content.endswith("\n\n"):
        if ctx.fix:
            ctx.healed_count += 1
            cprint(f"Normalized trailing newlines in {rel_name}", Colors.GRAY)
            return content.rstrip("\n") + "\n", True
        cprint(f"WARNING: Multiple trailing newlines in {rel_name}.", Colors.YELLOW)
        ctx.warning_count += 1
    return content, False

def extract_version(path: str, regex: str) -> str:
    if not os.path.exists(path):
        return "NF"
    with open(path, encoding='utf-8', errors='ignore') as f:
        m = re.search(regex, f.read())
    return m.group(1) if m else "NF"

def check_version_consistency(global_path: str, ctx: ValidationContext) -> bool:
    vp = r'(\d+\.\d+\.\d+)'
    versions = {
        "README.md":           extract_version(os.path.join(global_path, "README.md"),                 r"badge/.*?-" + vp),
        "README-AR.md":        extract_version(os.path.join(global_path, "README-AR.md"),              r"badge/.*?-" + vp),
        "state/CHANGELOG.md":  extract_version(os.path.join(global_path, "state", "CHANGELOG.md"),    r"(?m)^##\s*\[v?" + vp + r"\]"),
        "validate-globals.ps1":extract_version(os.path.join(global_path, "scripts", "validate-globals.ps1"), r"Validation.*?v" + vp),
        "validate-globals.py": extract_version(os.path.join(global_path, "scripts", "validate-globals.py"),  r"Validation.*?v" + vp),
    }
    unique = {v for v in versions.values() if v != "NF"}
    if len(unique) != 1:
        details = ", ".join(f"{k}={v}" for k, v in versions.items())
        cprint(f"ERROR: Version mismatch: {details}", Colors.RED)
        ctx.error_count += 1
        return False
    cprint(f"Version: {next(iter(unique))} (all consistent)", Colors.GREEN)
    return True

def validate_single_file(rel_name: str, data: dict, ctx: ValidationContext, global_path: str) -> tuple[str | None, bool]:
    content = data['content']
    ctx.scanned_count += 1

    content, le_mod   = check_line_endings(content, rel_name, ctx)
    content, bom_mod  = check_utf8_bom(content, data['full_path'], rel_name, ctx)
    sec_err            = check_secrets(content, rel_name, ctx)
    title_err          = check_title(content, rel_name, ctx)
    struct_err         = check_struct(content, rel_name, ctx)
    content, ref_err, ref_mod = check_cross_references(content, rel_name, ctx)
    fref_err           = check_file_references(content, rel_name, ctx, global_path)
    moji_err           = check_mojibake(content, rel_name, ctx)
    code_err           = check_symbolic_codes(content, rel_name, ctx)
    content, nl_mod    = check_trailing_newlines(content, rel_name, ctx)

    error_found   = sec_err or title_err or struct_err or ref_err or fref_err or moji_err or code_err
    file_modified = le_mod or bom_mod or ref_mod or nl_mod

    if file_modified and not ctx.dry_run:
        with open(data['full_path'], 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        with open(data['full_path'], 'rb') as f:
            data['hash'] = hashlib.sha256(f.read()).hexdigest()

    return (data['hash'] if not error_found else None), error_found

def run_pass1(rule_files: list[str], global_path: str, manifest: dict[str, str],
              force: bool, ctx: ValidationContext) -> dict[str, dict]:
    file_data: dict[str, dict] = {}
    for rel in rule_files:
        fpath = os.path.join(global_path, rel)
        with open(fpath, 'rb') as f:
            raw = f.read()
        current_hash = hashlib.sha256(raw).hexdigest()
        content = decode_content(raw)
        ctx.global_headers[rel] = extract_headers(content)
        if not force and rel in manifest and manifest[rel] == current_hash:
            ctx.skipped_count += 1
            continue
        file_data[rel] = {'content': content, 'full_path': fpath, 'hash': current_hash}
    return file_data

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI Globals Validation v4.21.0")
    p.add_argument("--dry-run",            action="store_true", help="Scan without writing")
    p.add_argument("--generate-manifest",  action="store_true", help="Force regenerate manifest")
    p.add_argument("--force",              action="store_true", help="Bypass manifest cache")
    p.add_argument("--fix",                action="store_true", help="Self-healing auto-correct")
    p.add_argument("--interactive",        action="store_true", help="Prompt before each fix")
    return p.parse_args()

def main() -> None:
    args = parse_args()
    global_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(global_path)

    vocab_path = os.path.join(global_path, "rules", "vocabulary.md")
    if not os.path.exists(vocab_path):
        cprint(f"MISCONFIG: rules/vocabulary.md not found at {vocab_path}", Colors.RED)
        sys.exit(2)

    cprint(f"AI Globals Validation v4.21.0 [Fix: {'ON' if args.fix else 'OFF'}]", Colors.CYAN)

    rule_files = collect_rule_files(global_path)
    manifest_path = os.path.join(global_path, "integrity.manifest")
    manifest = load_manifest(manifest_path)
    force = args.force or args.generate_manifest or check_core_rules(global_path, manifest)

    ctx = ValidationContext(args.fix, args.interactive, args.dry_run, args.force)

    with open(vocab_path, encoding='utf-8', errors='ignore') as f:
        for m in re.finditer(r"\[([A-Z]{3,4}-\d{2})\]", f.read()):
            ctx.defined_codes.add(m.group(1))

    file_data = run_pass1(rule_files, global_path, manifest, force, ctx)

    new_manifest = manifest.copy()
    # Remove stale manifest entries for files that no longer exist
    existing_files = set(rule_files)
    for stale in list(new_manifest.keys()):
        if stale not in existing_files:
            del new_manifest[stale]

    for rel in file_data:
        h, err = validate_single_file(rel, file_data[rel], ctx, global_path)
        if not err and h:
            new_manifest[rel] = h
        elif rel in new_manifest:
            del new_manifest[rel]
        if not err:
            cprint(f"  PASS: {rel}", Colors.GREEN)

    check_version_consistency(global_path, ctx)

    if not args.dry_run and (ctx.error_count == 0 or args.fix):
        cprint("Updating integrity.manifest...", Colors.CYAN)
        with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
            for rel, h in sorted(new_manifest.items()):
                f.write(f"{h}  {rel}\n")

    print(f"\nSummary: Scanned={ctx.scanned_count}, Skipped={ctx.skipped_count}, "
          f"Errors={ctx.error_count}, Warnings={ctx.warning_count}, Healed={ctx.healed_count}")
    if ctx.error_count > 0:
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
