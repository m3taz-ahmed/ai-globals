#!/usr/bin/env python3
# AI Globals Validation Script (Python) v4.17.0
# This script ensures the repository follows its own standards.

import os
import sys
import re
import hashlib
import argparse
import math
from typing import List, Dict, Tuple, Optional

# Console Color Utilities
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    RESET = '\033[0m'

class ValidationContext:
    def __init__(self, fix: bool, interactive: bool, dry_run: bool, force: bool) -> None:
        self.fix: bool = fix
        self.interactive: bool = interactive
        self.dry_run: bool = dry_run
        self.force: bool = force
        self.scanned_count: int = 0
        self.skipped_count: int = 0
        self.error_count: int = 0
        self.warning_count: int = 0
        self.healed_count: int = 0
        self.global_headers: Dict[str, List[str]] = {}
        self.defined_codes: set = set()

def print_color(text: str, color: str = Colors.RESET) -> None:
    if sys.stdout.isatty():
        print(f"{color}{text}{Colors.RESET}")
    else:
        print(text)

def calculate_entropy(data: str) -> float:
    if not data:
        return 0.0
    frequencies: Dict[str, int] = {}
    for char in data:
        frequencies[char] = frequencies.get(char, 0) + 1
    entropy: float = 0.0
    total_len = len(data)
    for count in frequencies.values():
        p_x = float(count) / total_len
        entropy -= p_x * math.log(p_x, 2)
    return entropy

def get_fuzzy_match(target: str, file_list: List[str]) -> Optional[str]:
    normalized_target = os.path.normpath(target).lower()
    for f in file_list:
        if os.path.normpath(f).lower() == normalized_target:
            return f
    target_base = os.path.basename(normalized_target)
    for f in file_list:
        if os.path.basename(f).lower() == target_base:
            return f
    for f in file_list:
        if target_base in os.path.basename(f).lower():
            return f
    return None

def collect_rule_files(global_path: str) -> List[str]:
    ignore_lines = []
    ignore_file = os.path.join(global_path, ".aiignore")
    if os.path.exists(ignore_file):
        with open(ignore_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith('#'):
                    ignore_lines.append(line_str.replace('/', os.sep))

    rule_files: List[str] = []
    for f in os.listdir(global_path):
        if f.endswith('.md') and os.path.isfile(os.path.join(global_path, f)):
            rule_files.append(f)
    target_dirs = ['rules', 'tech-stack', 'workflows']
    for d in target_dirs:
        dir_path = os.path.join(global_path, d)
        if os.path.exists(dir_path):
            for root, _, files in os.walk(dir_path):
                for f in files:
                    if f.endswith('.md'):
                        full_f = os.path.join(root, f)
                        rule_files.append(os.path.relpath(full_f, global_path))
                        
    filtered_files = []
    for rf in rule_files:
        skip = False
        for pattern in ignore_lines:
            if pattern in rf:
                skip = True
                break
        if not skip:
            filtered_files.append(rf)
    return filtered_files

def load_integrity_manifest(manifest_path: str) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r"^\s*([A-Fa-f0-9]{64})\s+(.+)$", line)
                if match:
                    manifest[match.group(2).strip()] = match.group(1).lower()
    return manifest

def check_core_rules(global_path: str, manifest: Dict[str, str]) -> bool:
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
                cf_hash = hashlib.sha256(f.read()).hexdigest()
            if manifest.get(cf) != cf_hash:
                print_color(f"Core rule change detected in {cf}. Forcing full scan...", Colors.YELLOW)
                return True
    return False

def extract_headers(content: str) -> List[str]:
    return [m.group(1).strip() for m in re.finditer(r"(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$", content)]

def decode_content(bytes_content: bytes) -> str:
    try:
        return bytes_content.decode('utf-8')
    except UnicodeDecodeError:
        return bytes_content.decode('latin-1')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Globals Validation v4.17.0")
    parser.add_argument("--dry-run", action="store_true", help="Scan files without writing modifications")
    parser.add_argument("--generate-manifest", action="store_true", help="Force regenerate manifest")
    parser.add_argument("--force", action="store_true", help="Bypass manifest checks and scan all files")
    parser.add_argument("--fix", action="store_true", help="Enable self-healing auto-corrections")
    parser.add_argument("--interactive", action="store_true", help="Prompt user before applying changes")
    return parser.parse_args()

def check_line_endings(content: str, rel_name: str, ctx: ValidationContext) -> Tuple[str, bool]:
    if "\r\n" not in content:
        return content, False
    if ctx.fix:
        ctx.healed_count += 1
        print_color(f"Fixed CRLF in {rel_name}", Colors.GRAY)
        return content.replace("\r\n", "\n"), True
    print_color(f"WARNING: CRLF detected in {rel_name}.", Colors.YELLOW)
    ctx.warning_count += 1
    return content, False

def check_utf8_bom(content: str, file_path: str, rel_name: str, ctx: ValidationContext) -> Tuple[str, bool]:
    with open(file_path, 'rb') as f:
        header_bytes = f.read(3)
    if header_bytes != b'\xef\xbb\xbf':
        return content, False
    if ctx.fix:
        if content.startswith('\ufeff'):
            content = content[1:]
        ctx.healed_count += 1
        print_color(f"Stripped BOM in {rel_name}", Colors.GRAY)
        return content, True
    print_color(f"WARNING: UTF-8 BOM detected in {rel_name}.", Colors.YELLOW)
    ctx.warning_count += 1
    return content, False

def check_secrets(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    secret_regex = re.compile(
        r'(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)\s*[:=]\s*[\'"]?([a-zA-Z0-9\/\+\-_=]{20,})[\'"]?'
    )
    error_found = False
    for match in secret_regex.finditer(content):
        matched_value = match.group(2)
        is_mock = any(mock in matched_value.lower() for mock in [
            'placeholder', 'your_', 'secret_here', 'token_here', 'example', 'mysecret', 'dummy', 'xxxx'
        ])
        entropy = calculate_entropy(matched_value)
        if not is_mock and entropy > 3.0:
            print_color(f"ERROR: Potential SECRET detected in {rel_name}: {match.group(0)} (Entropy: {entropy:.2f})", Colors.RED)
            error_found = True
            ctx.error_count += 1
    return error_found

def check_h1_title(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    if not re.search(r"(?m)^#\s+.+", content) and not re.search(r"(?i)<h1>.+</h1>", content):
        print_color(f"ERROR: Missing H1 title in {rel_name}", Colors.RED)
        ctx.error_count += 1
        return True
    return False

def handle_broken_section(content: str, raw_target_file: str, resolved_path: str, section_num: str, rel_name: str, ctx: ValidationContext) -> Tuple[str, bool, bool]:
    near_match = next((h for h in ctx.global_headers[resolved_path] if h.startswith(section_num) or section_num.startswith(h)), None)
    if ctx.fix and near_match:
        if not ctx.interactive or input(f"Found broken section §{section_num} in {rel_name}. Fix to §{near_match}? [Y/N]: ").strip().upper() == 'Y':
            content = content.replace(f"{raw_target_file} §{section_num}", f"{raw_target_file} §{near_match}")
            ctx.healed_count += 1
            print_color(f"Healed section: §{section_num} -> §{near_match} in {rel_name}", Colors.GRAY)
            return content, False, True
    print_color(f"ERROR: Broken Reference in {rel_name}: Section '§{section_num}' not found in '{resolved_path}'.", Colors.RED)
    ctx.error_count += 1
    return content, True, False

def check_cross_references(content: str, rel_name: str, ctx: ValidationContext) -> Tuple[str, bool, bool]:
    refs = re.finditer(r"([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)", content)
    error_found, file_modified = False, False
    for ref in refs:
        raw_t, section_num = ref.group(1), ref.group(2)
        target_file = raw_t.replace("/", os.sep)
        resolved_path = get_fuzzy_match(target_file, list(ctx.global_headers.keys()))
        if not resolved_path:
            print_color(f"ERROR: Broken Reference in {rel_name}: Target '{target_file}' not found.", Colors.RED)
            error_found = True
            ctx.error_count += 1
        elif section_num not in ctx.global_headers[resolved_path]:
            content, err, mod = handle_broken_section(content, raw_t, resolved_path, section_num, rel_name, ctx)
            error_found = error_found or err
            file_modified = file_modified or mod
        elif ctx.fix and target_file != resolved_path:
            if not ctx.interactive or input(f"Found broken path '{target_file}' in {rel_name}. Fix to '{resolved_path}'? [Y/N]: ").strip().upper() == 'Y':
                content = content.replace(raw_t, resolved_path.replace(os.sep, "/"))
                file_modified = True
                ctx.healed_count += 1
                print_color(f"Healed path: {target_file} -> {resolved_path} in {rel_name}", Colors.GRAY)
    return content, error_found, file_modified

def check_file_references(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    ignored_file_refs = {
        'monthely-maintenance-prompt.md', 'nuxt-4.md', 'bun-1.md', 'drizzle-orm.md', 
        '09-ai-review.md', 'mobile-standards.md', 'gemini.md', 'workflows\\nn-name.md', 
        'tech-stack\\xxx.md', 'verification-patterns.md', 'filename.md', 'bug_report.md', 
        'feature_request.md', 'tech_stack_request.md', 'pull_request_template.md',
        'active-context.md', 'skill.md', 'memory-archive.md'
    }
    file_refs = re.finditer(r"\b([\w\-\./]+\.md)\b", content)
    error_found = False
    for ref in file_refs:
        raw_target_file = ref.group(1)
        index_after = ref.end()
        if re.match(r"^\s+[§S]\s*\d+", content[index_after:]):
            continue
        target_file = raw_target_file.replace("/", os.sep)
        if "server" + os.sep + ".ai" in target_file:
            target_file = target_file.split("server" + os.sep + ".ai" + os.sep)[-1]
        base_target_file = os.path.basename(target_file).lower()
        if target_file.lower() in ignored_file_refs or base_target_file in ignored_file_refs:
            continue
        resolved_path = get_fuzzy_match(target_file, list(ctx.global_headers.keys()))
        if not resolved_path:
            global_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if os.path.exists(os.path.join(global_path, target_file)):
                continue
            print_color(f"ERROR: Broken File Reference in {rel_name}: Target '{target_file}' not found.", Colors.RED)
            error_found = True
            ctx.error_count += 1
    return error_found

def check_mojibake(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    if re.search(r"(\xC3\xA2\x80\x9C|\xC3\xA2\x80\x9D|\xE2\x80\x9C|\xE2\x80\x9D|\uFFFD)", content):
        print_color(f"ERROR: Encoding artifact (mojibake) found in {rel_name}.", Colors.RED)
        ctx.error_count += 1
        return True
    return False

def check_symbolic_codes(content: str, rel_name: str, ctx: ValidationContext) -> bool:
    error_found = False
    if "vocabulary.md" in rel_name:
        return False
    codes = re.finditer(r"\[([A-Z]{3,4}-\d{2})\]", content)
    for match in codes:
        code = match.group(1)
        if code not in ctx.defined_codes:
            print_color(f"ERROR: Undefined Symbolic Code in {rel_name}: '{code}' is not defined in vocabulary.md.", Colors.RED)
            error_found = True
            ctx.error_count += 1
    return error_found

def check_trailing_newlines(content: str, rel_name: str, ctx: ValidationContext) -> Tuple[str, bool]:
    if not content.endswith("\n"):
        if ctx.fix:
            ctx.healed_count += 1
            print_color(f"Added trailing newline to {rel_name}", Colors.GRAY)
            return content + "\n", True
        print_color(f"WARNING: Missing trailing newline in {rel_name}.", Colors.YELLOW)
        ctx.warning_count += 1
    elif content.endswith("\n\n"):
        if ctx.fix:
            ctx.healed_count += 1
            print_color(f"Normalized trailing newlines in {rel_name}", Colors.GRAY)
            return content.rstrip("\n") + "\n", True
        print_color(f"WARNING: Multiple trailing newlines in {rel_name}.", Colors.YELLOW)
        ctx.warning_count += 1
    return content, False

def extract_version(path: str, regex: str) -> str:
    if not os.path.exists(path):
        return "NF"
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        match = re.search(regex, f.read())
    return match.group(1) if match else "NF"

def check_version_consistency(global_path: str, ctx: ValidationContext) -> bool:
    v_pattern = r'(\d+\.\d+\.\d+)'
    versions = {
        "README.md": extract_version(os.path.join(global_path, "README.md"), r"badge/.*?-" + v_pattern),
        "README-AR.md": extract_version(os.path.join(global_path, "README-AR.md"), r"badge/.*?-" + v_pattern),
        "CHANGELOG.md": extract_version(os.path.join(global_path, "CHANGELOG.md"), r"(?m)^##\s*\[v?" + v_pattern + r"\]"),
        "validate-globals.ps1": extract_version(os.path.join(global_path, "scripts", "validate-globals.ps1"), r"Validation.*?v" + v_pattern),
        "validate-globals.py": extract_version(os.path.join(global_path, "scripts", "validate-globals.py"), r"Validation.*?v" + v_pattern)
    }
    unique_versions = {v for v in versions.values() if v != "NF"}
    if len(unique_versions) != 1:
        details = ", ".join(f"{k}={v}" for k, v in versions.items())
        print_color(f"ERROR: Version Mismatch! {details}", Colors.RED)
        ctx.error_count += 1
        return False
    print_color(f"Version: {list(unique_versions)[0]}", Colors.GREEN)
    return True

def validate_single_file(rel_name: str, file_data: Dict[str, Dict], ctx: ValidationContext) -> Tuple[Optional[str], bool]:
    data = file_data[rel_name]
    content = data['content']
    file_path = data['full_path']
    ctx.scanned_count += 1
    
    content, ending_mod = check_line_endings(content, rel_name, ctx)
    content, bom_mod = check_utf8_bom(content, file_path, rel_name, ctx)
    
    sec_err = check_secrets(content, rel_name, ctx)
    h1_err = check_h1_title(content, rel_name, ctx)
    content, ref_err, ref_mod = check_cross_references(content, rel_name, ctx)
    file_ref_err = check_file_references(content, rel_name, ctx)
    moji_err = check_mojibake(content, rel_name, ctx)
    code_err = check_symbolic_codes(content, rel_name, ctx)
    content, nl_mod = check_trailing_newlines(content, rel_name, ctx)
    
    error_found = sec_err or h1_err or ref_err or file_ref_err or moji_err or code_err
    file_modified = ending_mod or bom_mod or ref_mod or nl_mod
    
    if file_modified and not ctx.dry_run:
        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        with open(file_path, 'rb') as f:
            data['hash'] = hashlib.sha256(f.read()).hexdigest()
            
    return (data['hash'] if not error_found else None), error_found

def run_pass1(rule_files: List[str], global_path: str, manifest: Dict[str, str], force_scan: bool, ctx: ValidationContext) -> Dict[str, Dict]:
    file_data: Dict[str, Dict] = {}
    for rel_name in rule_files:
        file_path = os.path.join(global_path, rel_name)
        with open(file_path, 'rb') as f:
            bytes_content = f.read()
        current_hash = hashlib.sha256(bytes_content).hexdigest()
        
        if not force_scan and rel_name in manifest and manifest[rel_name] == current_hash:
            ctx.skipped_count += 1
            content = decode_content(bytes_content)
            ctx.global_headers[rel_name] = extract_headers(content)
            continue
            
        content = decode_content(bytes_content)
        ctx.global_headers[rel_name] = extract_headers(content)
        file_data[rel_name] = {
            'content': content,
            'full_path': file_path,
            'hash': current_hash
        }
    return file_data

def main() -> None:
    args = parse_args()
    global_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(global_path)
    
    fix_status = 'ON' if args.fix else 'OFF'
    print_color(f"Starting AI Globals Validation v4.17.0 [Self-Healing Mode: {fix_status}]...", Colors.CYAN)
    
    rule_files = collect_rule_files(global_path)
    manifest = load_integrity_manifest(os.path.join(global_path, "integrity.manifest"))
    force_scan = args.force or args.generate_manifest or check_core_rules(global_path, manifest)
    
    ctx = ValidationContext(args.fix, args.interactive, args.dry_run, args.force)
    
    vocab_path = os.path.join(global_path, "rules", "vocabulary.md")
    if os.path.exists(vocab_path):
        with open(vocab_path, 'r', encoding='utf-8', errors='ignore') as f:
            vocab_content = f.read()
            for match in re.finditer(r"\[([A-Z]{3,4}-\d{2})\]", vocab_content):
                ctx.defined_codes.add(match.group(1))
                
    file_data = run_pass1(rule_files, global_path, manifest, force_scan, ctx)
    
    new_manifest = manifest.copy()
    for rel_name in file_data:
        h, err = validate_single_file(rel_name, file_data, ctx)
        if not err and h is not None:
            new_manifest[rel_name] = h
        elif rel_name in new_manifest:
            del new_manifest[rel_name]
            
    check_version_consistency(global_path, ctx)
    
    if not args.dry_run and (ctx.error_count == 0 or args.fix):
        print_color("Updating integrity.manifest...", Colors.CYAN)
        sorted_manifest = sorted(new_manifest.items())
        with open(os.path.join(global_path, "integrity.manifest"), 'w', encoding='utf-8', newline='\n') as f:
            for rel, h in sorted_manifest:
                f.write(f"{h}  {rel}\n")
                
    print(f"\nSummary: Scanned={ctx.scanned_count}, Skipped={ctx.skipped_count}, Errors={ctx.error_count}, Warnings={ctx.warning_count}, Healed={ctx.healed_count}")
    sys.exit(1 if ctx.error_count > 0 else 0)

if __name__ == "__main__":
    main()
