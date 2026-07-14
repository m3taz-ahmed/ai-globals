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
