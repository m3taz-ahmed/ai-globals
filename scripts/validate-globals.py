#!/usr/bin/env python3
# AI Globals Validation Script (Python) v4.13.0
# This script ensures the repository follows its own standards.

import os
import sys
import re
import hashlib
import argparse

# Console Color Utilities
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    RESET = '\033[0m'

def print_color(text, color=Colors.RESET):
    # Check if stdout is a TTY and supports color (simplified for cross-platform compatibility)
    if sys.stdout.isatty():
        print(f"{color}{text}{Colors.RESET}")
    else:
        print(text)

# Shannon Entropy Calculator for Secret Detection
def calculate_entropy(data):
    if not data:
        return 0
    entropy = 0
    for x in range(256):
        p_x = float(data.count(chr(x))) / len(data)
        if p_x > 0:
            import math
            entropy += - p_x * math.log(p_x, 2)
    return entropy

def get_fuzzy_match(target, file_list):
    # 1. Exact match
    normalized_target = os.path.normpath(target).lower()
    for f in file_list:
        if os.path.normpath(f).lower() == normalized_target:
            return f

    # 2. Case-insensitive basename match
    target_base = os.path.basename(normalized_target)
    for f in file_list:
        if os.path.basename(f).lower() == target_base:
            return f

    # 3. Fuzzy search (partial match)
    for f in file_list:
        if target_base in os.path.basename(f).lower():
            return f

    return None

def main():
    parser = argparse.ArgumentParser(description="AI Globals Validation v4.13.0")
    parser.add_argument("--dry-run", action="store_true", help="Scan files without writing modifications")
    parser.add_argument("--generate-manifest", action="store_true", help="Force regenerate manifest")
    parser.add_argument("--force", action="store_true", help="Bypass manifest checks and scan all files")
    parser.add_argument("--fix", action="store_true", help="Enable self-healing auto-corrections")
    parser.add_argument("--interactive", action="store_true", help="Prompt user before applying changes")
    args = parser.parse_args()

    # The .ai root path is parent to the scripts folder containing this script
    global_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(global_path)

    print_color(f"Starting AI Globals Validation v4.13.0 [Self-Healing Mode: {'ON' if args.fix else 'OFF'}]...", Colors.CYAN)

    # Collect all md files mirroring PowerShell logic
    rule_files = []
    
    # 1. Non-recursive .md files in the root folder
    for f in os.listdir(global_path):
        if f.endswith('.md') and os.path.isfile(os.path.join(global_path, f)):
            rule_files.append(f)
            
    # 2. Recursive .md files in rules/, tech-stack/, workflows/ folders
    target_dirs = ['rules', 'tech-stack', 'workflows']
    for d in target_dirs:
        dir_path = os.path.join(global_path, d)
        if os.path.exists(dir_path):
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    if f.endswith('.md'):
                        full_f = os.path.join(root, f)
                        rel_path = os.path.relpath(full_f, global_path)
                        rule_files.append(rel_path)

    scanned_count = 0
    skipped_count = 0
    error_count = 0
    warning_count = 0
    healed_count = 0

    # Load Integrity Manifest
    manifest = {}
    manifest_path = os.path.join(global_path, "integrity.manifest")
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.match(r"^\s*([A-Fa-f0-9]{64})\s+(.+)$", line)
                if match:
                    manifest[match.group(2).strip()] = match.group(1).lower()

    # Core Rule Check to force full scan
    core_files = ["global-workflow.md", "global-roles.md"]
    rules_dir = os.path.join(global_path, "rules")
    if os.path.exists(rules_dir):
        for f in os.listdir(rules_dir):
            if f.endswith(".md"):
                core_files.append(os.path.join("rules", f))

    force_scan = args.force or args.generate_manifest
    for cf in core_files:
        cf_path = os.path.join(global_path, cf)
        if os.path.exists(cf_path):
            with open(cf_path, 'rb') as f:
                cf_hash = hashlib.sha256(f.read()).hexdigest()
            if manifest.get(cf) != cf_hash:
                force_scan = True
                print_color(f"Core rule change detected in {cf}. Forcing full system scan...", Colors.YELLOW)
                break

    file_data = {}
    global_headers = {}

    # Pass 1: Collect Headers & Hashes
    for rel_name in rule_files:
        file_path = os.path.join(global_path, rel_name)
        with open(file_path, 'rb') as f:
            bytes_content = f.read()
        current_hash = hashlib.sha256(bytes_content).hexdigest()

        # Check if we can skip validation
        if not force_scan and rel_name in manifest and manifest[rel_name] == current_hash:
            skipped_count += 1
            # Still extract headers for references validation
            try:
                content = bytes_content.decode('utf-8')
            except UnicodeDecodeError:
                content = bytes_content.decode('latin-1') # fallback
            headers = [m.group(1).strip() for m in re.finditer(r"(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$", content)]
            global_headers[rel_name] = headers
            continue

        try:
            content = bytes_content.decode('utf-8')
        except UnicodeDecodeError:
            content = bytes_content.decode('latin-1')
        
        headers = [m.group(1).strip() for m in re.finditer(r"(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$", content)]
        global_headers[rel_name] = headers

        file_data[rel_name] = {
            'content': content,
            'full_path': file_path,
            'hash': current_hash
        }

    new_manifest = manifest.copy()

    # Pass 2: Validation & Healing
    for rel_name, data in file_data.items():
        content = data['content']
        file_path = data['full_path']
        error_found = False
        file_modified = False
        scanned_count += 1

        # 1. Line Endings (LF)
        if "\r\n" in content:
            if args.fix:
                content = content.replace("\r\n", "\n")
                file_modified = True
                healed_count += 1
                print_color(f"Fixed CRLF in {rel_name}", Colors.GRAY)
            else:
                print_color(f"WARNING: CRLF detected in {rel_name}.", Colors.YELLOW)
                warning_count += 1

        # 2. UTF-8 BOM
        with open(file_path, 'rb') as f:
            header_bytes = f.read(3)
        if header_bytes == b'\xef\xbb\xbf':
            if args.fix:
                # Strip BOM from content
                if content.startswith('\ufeff'):
                    content = content[1:]
                file_modified = True
                healed_count += 1
                print_color(f"Stripped BOM in {rel_name}", Colors.GRAY)
            else:
                print_color(f"WARNING: UTF-8 BOM detected in {rel_name}.", Colors.YELLOW)
                warning_count += 1

        # 3. Secret Scanner (Regex + Entropy Threshold)
        secret_regex = re.compile(
            r'(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)\s*[:=]\s*[\'"]?([a-zA-Z0-9\/\+\-_=]{20,})[\'"]?'
        )
        for match in secret_regex.finditer(content):
            matched_value = match.group(2)
            # Filter out mock strings / standard placeholder variables
            is_mock = any(mock in matched_value.lower() for mock in [
                'placeholder', 'your_', 'secret_here', 'token_here', 'example', 'mysecret', 'dummy', 'xxxx'
            ])
            # Check entropy to filter low-entropy variable names or placeholders
            entropy = calculate_entropy(matched_value)
            if not is_mock and entropy > 3.0:
                print_color(f"ERROR: Potential SECRET detected in {rel_name}: {match.group(0)} (Entropy: {entropy:.2f})", Colors.RED)
                error_found = True
                error_count += 1

        # 4. H1 Title
        if not re.search(r"(?m)^#\s+.+", content) and not re.search(r"(?i)<h1>.+</h1>", content):
            print_color(f"ERROR: Missing H1 title in {rel_name}", Colors.RED)
            error_found = True
            error_count += 1

        # 5. Cross-Reference Self-Healing
        refs = re.finditer(r"([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)", content)
        for ref in refs:
            raw_target_file = ref.group(1)
            target_file = raw_target_file.replace("/", os.sep)
            section_num = ref.group(2)

            resolved_path = get_fuzzy_match(target_file, list(global_headers.keys()))

            if not resolved_path:
                print_color(f"ERROR: Broken Reference in {rel_name}: Target '{target_file}' not found.", Colors.RED)
                error_found = True
                error_count += 1
            elif section_num not in global_headers[resolved_path]:
                # Try finding a near match
                near_match = None
                for h in global_headers[resolved_path]:
                    if h.startswith(section_num) or section_num.startswith(h):
                        near_match = h
                        break
                
                if args.fix and near_match:
                    should_apply = True
                    if args.interactive:
                        choice = input(f"Found broken section §{section_num} in {rel_name} (referencing {resolved_path}). Suggesting fix to §{near_match}. Apply? [Y/N]: ").strip().upper()
                        if choice != 'Y':
                            should_apply = False
                    
                    if should_apply:
                        content = content.replace(f"{raw_target_file} §{section_num}", f"{raw_target_file} §{near_match}")
                        file_modified = True
                        healed_count += 1
                        print_color(f"Healed section: §{section_num} -> §{near_match} in {rel_name}", Colors.GRAY)
                else:
                    print_color(f"ERROR: Broken Reference in {rel_name}: Section '§{section_num}' not found in '{resolved_path}'.", Colors.RED)
                    error_found = True
                    error_count += 1
            elif args.fix and target_file != resolved_path:
                # Auto-fix path naming
                should_apply = True
                if args.interactive:
                    choice = input(f"Found broken path '{target_file}' in {rel_name}. Suggesting fix to '{resolved_path}'. Apply? [Y/N]: ").strip().upper()
                    if choice != 'Y':
                        should_apply = False

                if should_apply:
                    content = content.replace(raw_target_file, resolved_path.replace(os.sep, "/"))
                    file_modified = True
                    healed_count += 1
                    print_color(f"Healed path: {target_file} -> {resolved_path} in {rel_name}", Colors.GRAY)

        # 5b. General File Reference Validation
        ignored_file_refs = {
            'monthely-maintenance-prompt.md', 'nuxt-4.md', 'bun-1.md', 'drizzle-orm.md', 
            '09-ai-review.md', 'mobile-standards.md', 'gemini.md', 'workflows\\nn-name.md', 
            'tech-stack\\xxx.md', 'verification-patterns.md', 'filename.md', 'bug_report.md', 
            'feature_request.md', 'tech_stack_request.md', 'pull_request_template.md'
        }
        file_refs = re.finditer(r"\b([\w\-\./]+\.md)\b", content)
        for ref in file_refs:
            raw_target_file = ref.group(1)
            
            # Check if this match is followed by a section mark
            index_after = ref.end()
            remaining_content = content[index_after:]
            if re.match(r"^\s+[§S]\s*\d+", remaining_content):
                continue

            target_file = raw_target_file.replace("/", os.sep)
            base_target_file = os.path.basename(target_file).lower()
            if target_file.lower() in ignored_file_refs or base_target_file in ignored_file_refs:
                continue

            resolved_path = get_fuzzy_match(target_file, list(global_headers.keys()))
            if not resolved_path:
                print_color(f"ERROR: Broken File Reference in {rel_name}: Target '{target_file}' not found.", Colors.RED)
                error_found = True
                error_count += 1

        # 6. Mojibake
        if re.search(r"(\xC3\xA2\x80\x9C|\xC3\xA2\x80\x9D|\xE2\x80\x9C|\xE2\x80\x9D|\uFFFD)", content):
            print_color(f"ERROR: Encoding artifact (mojibake) found in {rel_name}.", Colors.RED)
            error_found = True
            error_count += 1

        # 7. Newline at end of file
        if not content.endswith("\n"):
            if args.fix:
                content += "\n"
                file_modified = True
                healed_count += 1
                print_color(f"Added trailing newline to {rel_name}", Colors.GRAY)
            else:
                print_color(f"WARNING: Missing trailing newline in {rel_name}.", Colors.YELLOW)
                warning_count += 1
        elif content.endswith("\n\n"):
            if args.fix:
                content = content.rstrip("\n") + "\n"
                file_modified = True
                healed_count += 1
                print_color(f"Normalized trailing newlines in {rel_name}", Colors.GRAY)
            else:
                print_color(f"WARNING: Multiple trailing newlines in {rel_name}.", Colors.YELLOW)
                warning_count += 1

        if file_modified and not args.dry_run:
            with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(content)
            # Recalculate hash after healing
            with open(file_path, 'rb') as f:
                new_hash = hashlib.sha256(f.read()).hexdigest()
            data['hash'] = new_hash

        if not error_found:
            new_manifest[rel_name] = data['hash']

    # 7. Version Consistency Check
    version_pattern = r'(\d+\.\d+\.\d+)'
    
    def extract_version(path, regex):
        if not os.path.exists(path):
            return "NF"
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
        match = re.search(regex, file_content)
        return match.group(1) if match else "NF"

    readme_ver = extract_version("README.md", r"badge/.*?-" + version_pattern)
    readme_ar_ver = extract_version("README-AR.md", r"badge/.*?-" + version_pattern)
    changelog_ver = extract_version("CHANGELOG.md", r"(?m)^##\s*\[v?" + version_pattern + r"\]")
    ps1_ver = extract_version("scripts/validate-globals.ps1", r"Validation.*?v" + version_pattern)
    py_ver = extract_version("scripts/validate-globals.py", r"Validation.*?v" + version_pattern)

    versions = {
        "README.md": readme_ver,
        "README-AR.md": readme_ar_ver,
        "CHANGELOG.md": changelog_ver,
        "validate-globals.ps1": ps1_ver,
        "validate-globals.py": py_ver
    }

    unique_versions = {v for v in versions.values() if v != "NF"}
    if len(unique_versions) != 1:
        details = ", ".join(f"{k}={v}" for k, v in versions.items())
        print_color(f"ERROR: Version Mismatch! {details}", Colors.RED)
        error_count += 1
    else:
        print_color(f"Version: {list(unique_versions)[0]}", Colors.GREEN)

    # 8. Manifest Update (Automatic regeneration after checks/fixes pass)
    if not args.dry_run and (error_count == 0 or args.fix):
        print_color("Updating integrity.manifest...", Colors.CYAN)
        sorted_manifest = sorted(new_manifest.items())
        with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
            for rel, h in sorted_manifest:
                f.write(f"{h}  {rel}\n")

    print(f"\nSummary: Scanned={scanned_count}, Skipped={skipped_count}, Errors={error_count}, Warnings={warning_count}, Healed={healed_count}")
    sys.exit(1 if error_count > 0 else 0)

if __name__ == "__main__":
    main()
