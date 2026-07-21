#!/usr/bin/env bash
set -e

ROOT="${AGENT_OS_ROOT:-$HOME/.ai-os}"
REPO="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ROOT"

# Copy repo contents (rsync optional)
if command -v rsync >/dev/null 2>&1; then
    rsync -av --exclude='.git' --exclude='.github' "$REPO/" "$ROOT/"
else
    cp -R "$REPO"/* "$ROOT/"
    rm -rf "$ROOT/.git" "$ROOT/.github"
fi

# Symlink agent configs
mkdir -p "$HOME/.claude"
ln -sf "$ROOT/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null || cp "$ROOT/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
ln -sf "$ROOT/.claude/settings.json" "$HOME/.claude/settings.json" 2>/dev/null || cp "$ROOT/.claude/settings.json" "$HOME/.claude/settings.json"
ln -sf "$ROOT/.claude/skills" "$HOME/.claude/skills" 2>/dev/null || cp -R "$ROOT/.claude/skills" "$HOME/.claude/skills"
ln -sf "$ROOT/.claude/agents" "$HOME/.claude/agents" 2>/dev/null || cp -R "$ROOT/.claude/agents" "$HOME/.claude/agents"
ln -sf "$ROOT/.aider.conf.yml" "$HOME/.aider.conf.yml" 2>/dev/null || cp "$ROOT/.aider.conf.yml" "$HOME/.aider.conf.yml"

# Generate .claude/settings.json with absolute installed paths
mkdir -p "$HOME/.claude"
cat > "$ROOT/.claude/settings.json" <<EOF
{
  "permissions": {
    "allow": ["view","Read","grep","Glob","bash:git status","bash:git diff","bash:git log","bash:ls","bash:cd","bash:pwd","bash:graphify"],
    "ask": ["edit","write","Bash","bash:rm","bash:mv","bash:cp","mcp_call_tool","mcp_read_resource"],
    "deny": ["bash:rm -rf","bash:git reset --hard","bash:git checkout .","bash:git clean -fd","bash:git add -A","bash:git add .","bash:git push -f","bash:git stash","bash:curl -X POST","bash:curl -X DELETE","bash:node -e","bash:python -c"]
  },
  "mcpServers": {
    "ai-global-os": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$ROOT'; subprocess.run([sys.executable,'-m','aios_mcp.aios_server'], cwd=root)"] },
    "context7": { "command": "npx", "args": ["-y", "@context7/mcp"] },
    "graphify": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$ROOT'; subprocess.run([sys.executable, str(pathlib.Path(root)/'scripts'/'graphify_mcp_wrapper.py'))])"] }
  },
  "alwaysAllow": { "tools": ["Read","grep","Glob","view"], "mcpTools": ["context7-get-library-docs","graphify-query","query_rules","check_policy","search_memory","search_memory_vector"] }
}
EOF
ln -sf "$ROOT/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null || cp "$ROOT/.claude/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
ln -sf "$ROOT/.claude/settings.json" "$HOME/.claude/settings.json" 2>/dev/null || cp "$ROOT/.claude/settings.json" "$HOME/.claude/settings.json"
ln -sf "$ROOT/.claude/skills" "$HOME/.claude/skills" 2>/dev/null || cp -R "$ROOT/.claude/skills" "$HOME/.claude/skills"
ln -sf "$ROOT/.claude/agents" "$HOME/.claude/agents" 2>/dev/null || cp -R "$ROOT/.claude/agents" "$HOME/.claude/agents"
ln -sf "$ROOT/.aider.conf.yml" "$HOME/.aider.conf.yml" 2>/dev/null || cp "$ROOT/.aider.conf.yml" "$HOME/.aider.conf.yml"

# CLI shim
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/ai-os" <<EOF
#!/usr/bin/env bash
export AGENT_OS_ROOT="$ROOT"
export PYTHONIOENCODING=utf-8
python "$ROOT/cli.py" "$@"
EOF
chmod +x "$BIN_DIR/ai-os"

echo "AI Global OS installed to $ROOT"
echo "CLI: ai-os status"
echo "Ensure $BIN_DIR is in your PATH."
