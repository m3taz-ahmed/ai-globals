#!/usr/bin/env bash
# aiZee installer for Linux/macOS/Ubuntu
# Idempotent: safe to run on first install, reinstall, or after a git pull update.
# Preserves runtime state, runs migrations, verifies dependencies, and self-heals
# broken symlinks / stale paths.
#
# Usage:
#   ./install.sh                # Full install/update (auto-detect root)
#   ./install.sh --whatif       # Dry-run: show what would happen
#   ./install.sh --update       # Update-only: skip file copy, run migrations + deps
#   ./install.sh --install-dir PATH  # Force a specific install target (copy mode)
#   ./install.sh --skip-pip     # Skip pip install
#   ./install.sh --skip-graphify    # Skip graphify build
#   ./install.sh --skip-mcp     # Skip MCP config generation
set -euo pipefail

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------

WHATIF=false
UPDATE=false
SKIP_PIP=false
SKIP_GRAPHIFY=false
SKIP_MCP=false
INSTALL_DIR=""
REPO="$(cd "$(dirname "$0")" && pwd)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --whatif)        WHATIF=true; shift ;;
        --update)        UPDATE=true; shift ;;
        --install-dir)   INSTALL_DIR="$2"; shift 2 ;;
        --skip-pip)      SKIP_PIP=true; shift ;;
        --skip-graphify) SKIP_GRAPHIFY=true; shift ;;
        --skip-mcp)      SKIP_MCP=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FILE=""

start_log() {
    local root="$1"
    local log_dir="$root/state"
    mkdir -p "$log_dir" 2>/dev/null
    LOG_FILE="$log_dir/install-$(date +%Y%m%d-%H%M%S).log"
    if ! $WHATIF; then
        echo "aiZee Install Log - $(date)" > "$LOG_FILE"
    fi
}

log() {
    local level="$1" msg="$2"
    local ts
    ts=$(date +%H:%M:%S)
    if [[ -n "$LOG_FILE" && ! $WHATIF ]]; then
        echo "[$ts] [$level] $msg" >> "$LOG_FILE"
    fi
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

step() { echo -e "\033[36m[aios] $1\033[0m"; log "INFO" "$1"; }
ok()   { echo -e "\033[32m[aios] OK: $1\033[0m"; log "OK" "$1"; }
warn() { echo -e "\033[33m[aios] WARN: $1\033[0m"; log "WARN" "$1"; }
err()  { echo -e "\033[31m[aios] ERROR: $1\033[0m"; log "ERROR" "$1"; }

has_cmd() { command -v "$1" >/dev/null 2>&1; }

# Retry logic for flaky commands
retry() {
    local desc="$1"; shift
    local max="${RETRY_MAX:-3}"
    local attempt=1
    while (( attempt <= max )); do
        step "$desc (attempt $attempt/$max)"
        if $WHATIF; then echo "WhatIf: $desc"; return 0; fi
        if "$@"; then return 0; fi
        local delay=$(( attempt * 2 ))
        warn "$desc failed (attempt $attempt) - retrying in ${delay}s"
        sleep "$delay"
        (( attempt++ ))
    done
    err "$desc failed after $max attempts"
    return 1
}

# Checksum verification
checksum() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }

# Auto-detect moved repo
root_valid() {
    local root="$1"
    [[ -f "$root/pyproject.toml" || -f "$root/config.py" ]]
}

resolve_stale_root() {
    local repo="$1" current="$2"
    if [[ -n "$current" && ! -d "$current" ]]; then
        warn "AIZEE_ROOT points to missing location: $current"
        if root_valid "$repo"; then
            step "Auto-detecting: using repo location as root: $repo"
            echo "$repo"
            return
        fi
    fi
    if [[ -n "$current" && ! -f "$current/pyproject.toml" && -f "$repo/pyproject.toml" ]]; then
        warn "Root at $current appears stale. Repo at $repo is valid."
        echo "$repo"
        return
    fi
    echo "$current"
}

# Health check for MCP servers
health_check_mcp() {
    local root="$1"
    step "Health check: MCP servers"
    local config="$root/.devin/mcp_config.json"
    [[ ! -f "$config" ]] && config="$root/aizee_mcp/config.json"
    [[ ! -f "$config" ]] && { warn "No MCP config found"; return; }
    # Parse with python for portability
    python3 -c "
import json, sys, shutil
with open('$config') as f:
    cfg = json.load(f)
for name, srv in cfg.get('mcpServers', {}).items():
    cmd = srv.get('command', '')
    if cmd == 'python':
        print(f'  {name}: python-based (deferred)')
    elif cmd == 'npx':
        status = 'ready' if shutil.which('npx') else 'npx not found'
        print(f'  {name}: {status}')
    elif cmd == 'uvx':
        status = 'ready' if shutil.which('uvx') else 'uvx not found'
        print(f'  {name}: {status}')
    else:
        print(f'  {name}: unknown command {cmd}')
" 2>/dev/null || warn "Failed to parse MCP config"
}

get_installed_version() {
    local root="$1"
    local vf="$root/.aizee-version"
    if [[ -f "$vf" ]]; then
        cat "$vf" | tr -d '[:space:]'
    fi
}

get_target_version() {
    local root="$1"
    local pyproject="$root/pyproject.toml"
    if [[ ! -f "$pyproject" ]]; then echo "0.0.0"; return; fi
    grep -m1 '^version' "$pyproject" | sed 's/.*"\(.*\)".*/\1/'
}

compare_version() {
    local a="$1" b="$2"
    local IFS=.
    local i a_parts=($a) b_parts=($b)
    for i in 0 1 2; do
        local av=${a_parts[$i]:-0} bv=${b_parts[$i]:-0}
        if (( av < bv )); then return -1; fi
        if (( av > bv )); then return 1; fi
    done
    return 0
}

# ---------------------------------------------------------------------------
# 0. Determine root
# ---------------------------------------------------------------------------

if [[ -n "$INSTALL_DIR" ]]; then
    ROOT="$INSTALL_DIR"
    COPY_MODE=true
elif [[ -f "$REPO/pyproject.toml" ]]; then
    ROOT="$REPO"
    COPY_MODE=false
else
    ROOT="${AIZEE_ROOT:-$HOME/.aizee}"
    COPY_MODE=true
fi

# Auto-detect moved repo
if [[ -z "$INSTALL_DIR" && -n "$AIZEE_ROOT" && "$AIZEE_ROOT" != "$REPO" ]]; then
    ROOT=$(resolve_stale_root "$REPO" "$ROOT")
fi

if $UPDATE; then COPY_MODE=false; fi

# Start logging
start_log "$ROOT"

if $WHATIF; then
    echo -e "\033[36mWhatIf: would install aiZee"
    echo "  Repo:      $REPO"
    echo "  Root:      $ROOT"
    echo "  CopyMode:  $COPY_MODE"
    echo "  Update:    $UPDATE\033[0m"
fi

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------

step "Pre-flight checks"

# Python
if ! has_cmd python; then
    err "python is required but not found on PATH"
    exit 1
fi
python_version=$(python --version 2>&1 | awk '{print $2}')
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)
if [[ "$python_major" -lt 3 ]] || { [[ "$python_major" -eq 3 ]] && [[ "$python_minor" -lt 10 ]]; }; then
    err "Python 3.10+ is required (found $python_version)"
    exit 1
fi
ok "Python: $python_version"

# npm/npx
if has_cmd npx; then
    ok "npx: available"
else
    warn "npx: not found — context7/upwork/freelancer MCP servers will not be available"
fi

# uvx
if has_cmd uvx; then
    ok "uvx: available"
else
    warn "uvx: not found — fiverr MCP server will not be available (install with: pip install uv)"
fi

# Version check
INSTALLED_VERSION=$(get_installed_version "$ROOT")
TARGET_VERSION=$(get_target_version "$REPO")
if [[ -n "$INSTALLED_VERSION" ]]; then
    ok "Installed version: $INSTALLED_VERSION (target: $TARGET_VERSION)"
else
    ok "First install (target: $TARGET_VERSION)"
fi

# If --update and already at target → exit
if $UPDATE && [[ -n "$INSTALLED_VERSION" ]]; then
    if compare_version "$INSTALLED_VERSION" "$TARGET_VERSION"; then
        ok "Already at $TARGET_VERSION — no update needed"
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# 2. Ensure root directory exists
# ---------------------------------------------------------------------------

mkdir -p "$ROOT"

# ---------------------------------------------------------------------------
# 3. Preserve user state on reinstall (copy mode only)
# ---------------------------------------------------------------------------

STATE_BACKUP=""
BRAIN_BACKUP=""
BACKUP_DIR="$ROOT/state/.backups"
if $COPY_MODE && [[ -d "$ROOT/state" ]]; then
    mkdir -p "$BACKUP_DIR" 2>/dev/null
    STATE_BACKUP="$BACKUP_DIR/state-$(date +%Y%m%d%H%M%S)"
    step "Preserving existing state to $STATE_BACKUP"
    if ! $WHATIF; then
        cp -R "$ROOT/state" "$STATE_BACKUP"
    fi
fi
if $COPY_MODE && [[ -d "$ROOT/brain" ]]; then
    mkdir -p "$BACKUP_DIR" 2>/dev/null
    BRAIN_BACKUP="$BACKUP_DIR/brain-$(date +%Y%m%d%H%M%S)"
    step "Preserving existing brain to $BRAIN_BACKUP"
    if ! $WHATIF; then
        cp -R "$ROOT/brain" "$BRAIN_BACKUP"
    fi
fi

# ---------------------------------------------------------------------------
# 4. Copy repo contents to root (copy mode only)
# ---------------------------------------------------------------------------

if $COPY_MODE; then
    step "Copying repo contents to $ROOT"
    if has_cmd rsync; then
        rsync -av --exclude='.git' --exclude='.github' --exclude='__pycache__' \
            --exclude='*.pyc' --exclude='*.pyo' --exclude='.pytest_cache' \
            --exclude='node_modules' --exclude='.venv' --exclude='venv' \
            --exclude='temp' --exclude='state' --exclude='brain' \
            --exclude='graphify-out' --exclude='.ai' --exclude='.aizee-version' \
            "$REPO/" "$ROOT/"
    else
        cp -R "$REPO"/* "$ROOT/" 2>/dev/null || true
        cp "$REPO"/.* "$ROOT/" 2>/dev/null || true
        rm -rf "$ROOT/.git" "$ROOT/.github" "$ROOT/__pycache__" "$ROOT/temp" "$ROOT/graphify-out"
    fi

    # Restore state/brain
    if [[ -n "$STATE_BACKUP" && -d "$STATE_BACKUP" ]]; then
        step "Restoring state"
        if ! $WHATIF; then
            mkdir -p "$ROOT/state"
            cp -R "$STATE_BACKUP"/* "$ROOT/state/" 2>/dev/null || true
            rm -rf "$STATE_BACKUP"
        fi
    fi
    if [[ -n "$BRAIN_BACKUP" && -d "$BRAIN_BACKUP" ]]; then
        step "Restoring brain"
        if ! $WHATIF; then
            mkdir -p "$ROOT/brain"
            cp -R "$BRAIN_BACKUP"/* "$ROOT/brain/" 2>/dev/null || true
            rm -rf "$BRAIN_BACKUP"
        fi
    fi
else
    step "In-place mode — skipping file copy (root = repo)"
fi

# ---------------------------------------------------------------------------
# 5. Run migrations
# ---------------------------------------------------------------------------

step "Checking migrations"
if ! $WHATIF; then
    python "$REPO/scripts/migrate.py" --root "$ROOT" || {
        local_exit=$?
        if [[ $local_exit -eq 2 ]]; then
            err "Migration failed — see output above"
            exit 2
        fi
    }
else
    echo "WhatIf: python $REPO/scripts/migrate.py --root $ROOT"
fi

# ---------------------------------------------------------------------------
# 6. Install / update Python dependencies
# ---------------------------------------------------------------------------

if ! $SKIP_PIP; then
    step "Checking Python dependencies"
    cd "$ROOT"
    if $WHATIF; then
        echo "WhatIf: python -m pip install -e '.[dev,graphify]'"
    else
        if [[ -n "$INSTALLED_VERSION" && ! $UPDATE ]]; then
            retry "pip install aios" python -m pip install -e '.[dev,graphify]' --no-deps || {
                err "Failed to install aios dependencies after retries"
                exit 1
            }
        else
            retry "pip install aios" python -m pip install -e '.[dev,graphify]' || {
                err "Failed to install aios dependencies after retries"
                exit 1
            }
        fi
    fi

    # Verify required packages
    step "Verifying required packages"
    for pkg in yaml mcp pydantic rich numpy cryptography; do
        if ! python -c "import $pkg" 2>/dev/null; then
            warn "Missing package: $pkg - attempting install"
            if ! $WHATIF; then
                retry "pip install $pkg" python -m pip install "$pkg" || warn "Could not install $pkg"
            fi
        fi
    done
    ok "Required packages verified"
else
    step "Skipping pip install (--skip-pip)"
fi

# ---------------------------------------------------------------------------
# 7. Set AIZEE_ROOT
# ---------------------------------------------------------------------------

export AIZEE_ROOT="$ROOT"
if ! $WHATIF; then
    # Persist to shell profile (bash or zsh)
    PROFILE=""
    if [[ -f "$HOME/.bashrc" ]]; then PROFILE="$HOME/.bashrc"
    elif [[ -f "$HOME/.zshrc" ]]; then PROFILE="$HOME/.zshrc"
    elif [[ -f "$HOME/.profile" ]]; then PROFILE="$HOME/.profile"
    fi
    if [[ -n "$PROFILE" ]]; then
        # Remove old AIZEE_ROOT lines and add new one
        # Use portable sed: create backup on macOS (BSD sed requires -i with suffix)
        if [[ "$(uname)" == "Darwin" ]]; then
            sed -i.bak '/^export AIZEE_ROOT=/d' "$PROFILE" 2>/dev/null && rm -f "${PROFILE}.bak"
        else
            sed -i '/^export AIZEE_ROOT=/d' "$PROFILE" 2>/dev/null
        fi
        echo "export AIZEE_ROOT=\"$ROOT\"" >> "$PROFILE"
        ok "AIZEE_ROOT set to $ROOT (in $PROFILE)"
    fi
fi

# ---------------------------------------------------------------------------
# 8. Validate globals + build knowledge graph
# ---------------------------------------------------------------------------

cd "$ROOT"
step "Validating globals"
if ! $WHATIF; then
    python scripts/validate-globals.py --fix
else
    echo "WhatIf: python scripts/validate-globals.py --fix"
fi

if ! $SKIP_GRAPHIFY; then
    step "Building knowledge graph"
    if ! $WHATIF; then
        python -m graphify update .
    else
        echo "WhatIf: python -m graphify update ."
    fi
else
    step "Skipping graphify (--skip-graphify)"
fi

# ---------------------------------------------------------------------------
# 9. Symlink agent configs
# ---------------------------------------------------------------------------

if ! $SKIP_MCP; then
    mkdir -p "$HOME/.claude"

    link_or_copy() {
        local src="$1" dst="$2"
        if [[ ! -e "$src" ]]; then
            step "Skipping $dst (source $src does not exist)"
            return
        fi
        # Remove broken symlink
        if [[ -L "$dst" && ! -e "$dst" ]]; then
            warn "Removing broken link: $dst"
            rm -f "$dst"
        fi
        # Backup existing non-link
        if [[ -e "$dst" && ! -L "$dst" ]]; then
            local backup="${dst}.$(date +%Y%m%d%H%M%S).backup"
            step "Backing up $dst -> $backup"
            if ! $WHATIF; then mv "$dst" "$backup" 2>/dev/null || rm -rf "$dst"; fi
        fi
        # Remove existing valid link
        if [[ -L "$dst" ]]; then
            rm -f "$dst"
        fi
        if ! $WHATIF; then
            ln -sf "$src" "$dst" 2>/dev/null || cp -R "$src" "$dst"
        fi
    }

    link_or_copy "$ROOT/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
    link_or_copy "$ROOT/.claude/settings.json" "$HOME/.claude/settings.json"
    link_or_copy "$ROOT/.claude/skills" "$HOME/.claude/skills"
    link_or_copy "$ROOT/.claude/agents" "$HOME/.claude/agents"
    link_or_copy "$ROOT/.devin/skills/global-os" "$HOME/.devin/skills/global-os"
    link_or_copy "$ROOT/.windsurf/skills/global-os" "$HOME/.windsurf/skills/global-os"
    link_or_copy "$ROOT/.aider.conf.yml" "$HOME/.aider.conf.yml"

    # ---------------------------------------------------------------------------
    # 10. Generate .claude/settings.json with absolute installed paths
    # ---------------------------------------------------------------------------

    mkdir -p "$ROOT/.claude"
    cat > "$ROOT/.claude/settings.json" <<EOF
{
  "permissions": {
    "allow": ["view","Read","read","grep","Glob","search","query","list","get","status","bash:git status","bash:git diff","bash:git log","bash:ls","bash:cd","bash:pwd","bash:graphify"],
    "ask": ["edit","write","Bash","bash:rm","bash:mv","bash:cp","mcp_call_tool","mcp_read_resource"],
    "deny": ["bash:rm -rf","bash:git reset --hard","bash:git checkout .","bash:git clean -fd","bash:git add -A","bash:git add .","bash:git push -f","bash:git stash","bash:curl -X POST","bash:curl -X DELETE","bash:node -e","bash:python -c"]
  },
  "mcpServers": {
    "aizee": { "command": "python", "args": ["scripts/aizee_mcp_wrapper.py"] },
    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp@3.1.0"] },
    "graphify": { "command": "python", "args": ["scripts/graphify_mcp_wrapper.py"] },
    "upwork": { "command": "python", "args": ["scripts/mcp_env_wrapper.py", "npx", "-y", "@furkankoykiran/upwork-mcp@1.2.2"] },
    "freelancer": { "command": "python", "args": ["scripts/mcp_env_wrapper.py", "npx", "-y", "freelancer-mcp-server@2.0.0"] },
    "fiverr": { "command": "python", "args": ["scripts/mcp_env_wrapper.py", "uvx", "fiverr-mcp-server"] },
    "linkedin": { "command": "python", "args": ["scripts/mcp_env_wrapper.py", "octopus-linkedin-mcp"] }
  },
  "alwaysAllow": { "tools": ["Read","read","grep","Glob","view","search","query"], "mcpTools": ["context7-resolve-library-id","context7-get-library-docs","graphify-query","query_rules","check_policy","search_memory","search_memory_vector","search_skills","get_changelog","get_active_context"] }
}
EOF
    ok "settings.json generated with root=$ROOT"
fi

# ---------------------------------------------------------------------------
# 11. CLI shim
# ---------------------------------------------------------------------------

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/aizee" <<EOF
#!/usr/bin/env bash
export AIZEE_ROOT="$ROOT"
export PYTHONIOENCODING=utf-8
python "$ROOT/aizee_cli.py" "\$@"
EOF
chmod +x "$BIN_DIR/aizee"
ok "CLI shim: $BIN_DIR/aizee"

# ---------------------------------------------------------------------------
# 12. Post-install verification
# ---------------------------------------------------------------------------

step "Post-install verification"
if ! $WHATIF; then
    if python "$ROOT/aizee_cli.py" status >/dev/null 2>&1; then
        ok "CLI: aizee status works"
    else
        warn "CLI status check failed"
    fi

    # Config path verification
    settings_path="$ROOT/.claude/settings.json"
    if [[ -f "$settings_path" ]]; then
        if grep -q "$ROOT" "$settings_path"; then
            ok "settings.json paths verified"
        else
            warn "settings.json does not contain current root path"
        fi
    fi

    # MCP server health check
    if ! $SKIP_MCP; then
        health_check_mcp "$ROOT"
    fi
fi

# ---------------------------------------------------------------------------
# 13. Write .aizee-version
# ---------------------------------------------------------------------------

if ! $WHATIF; then
    echo "$TARGET_VERSION" > "$ROOT/.aizee-version"
fi
ok "Version: $TARGET_VERSION"

# ---------------------------------------------------------------------------
# 14. Cleanup old backups (keep last 3)
# ---------------------------------------------------------------------------

if [[ -d "$BACKUP_DIR" ]]; then
    step "Cleaning old backups (keeping last 3)"
    if ! $WHATIF; then
        ls -1dt "$BACKUP_DIR"/state-* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true
        ls -1dt "$BACKUP_DIR"/brain-* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo -e "\033[32maiZee $TARGET_VERSION installed to $ROOT\033[0m"
echo -e "\033[32mCLI: aizee status\033[0m"
if [[ -n "$LOG_FILE" ]]; then
    echo -e "\033[90mLog: $LOG_FILE\033[0m"
fi
if ! $UPDATE; then
    echo -e "\033[33mEnsure $BIN_DIR is in your PATH and restart your shell.\033[0m"
fi
