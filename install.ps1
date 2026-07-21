# AI Global OS installer for Windows
$Repo = $PSScriptRoot
if ($Repo -eq "") { $Repo = Get-Location }

$Root = if ($env:AGENT_OS_ROOT) { $env:AGENT_OS_ROOT } else { "$env:LOCALAPPDATA\AI-Global-OS" }

if (-not (Test-Path $Root)) { New-Item -ItemType Directory -Path $Root -Force | Out-Null }

# Copy repo contents into AI Global OS root
Get-ChildItem -Path $Repo -Exclude @(".git", ".github") | ForEach-Object {
    $Dest = Join-Path $Root $_.Name
    if ($_.PSIsContainer) {
        if (Test-Path $Dest) { Remove-Item -Path $Dest -Recurse -Force }
        Copy-Item -Path $_.FullName -Destination $Dest -Recurse -Force
    } else {
        Copy-Item -Path $_.FullName -Destination $Dest -Force
    }
}

# Symlink or copy agent configs into common locations
$Config = @{
    "$env:USERPROFILE\.claude\CLAUDE.md" = "$Root\.claude\CLAUDE.md"
    "$env:USERPROFILE\.claude\settings.json" = "$Root\.claude\settings.json"
    "$env:USERPROFILE\.claude\skills" = "$Root\.claude\skills"
    "$env:USERPROFILE\.claude\agents" = "$Root\.claude\agents"
    "$env:USERPROFILE\.aider.conf.yml" = "$Root\.aider.conf.yml"
}

foreach ($Target in $Config.Keys) {
    $Source = $Config[$Target]
    if (Test-Path $Target) { Remove-Item -Path $Target -Force -Recurse }
    if (Test-Path $Source -PathType Container) {
        try {
            New-Item -ItemType SymbolicLink -Path $Target -Target $Source -Force | Out-Null
        } catch {
            Copy-Item -Path $Source -Destination $Target -Recurse -Force
        }
    } else {
        try {
            New-Item -ItemType HardLink -Path $Target -Target $Source -Force | Out-Null
        } catch {
            Copy-Item -Path $Source -Destination $Target -Force
        }
    }
}

# Generate .claude/settings.json with absolute installed paths
$ClaudeDir = "$Root\.claude"
if (-not (Test-Path $ClaudeDir)) { New-Item -ItemType Directory -Path $ClaudeDir -Force | Out-Null }
$ClaudeSettings = @"
{
  "permissions": {
    "allow": ["view","Read","grep","Glob","bash:git status","bash:git diff","bash:git log","bash:ls","bash:cd","bash:pwd","bash:graphify"],
    "ask": ["edit","write","Bash","bash:rm","bash:mv","bash:cp","mcp_call_tool","mcp_read_resource"],
    "deny": ["bash:rm -rf","bash:git reset --hard","bash:git checkout .","bash:git clean -fd","bash:git add -A","bash:git add .","bash:git push -f","bash:git stash","bash:curl -X POST","bash:curl -X DELETE","bash:Invoke-WebRequest -Method Post","bash:Invoke-WebRequest -Method Delete","bash:node -e","bash:python -c"]
  },
  "mcpServers": {
    "ai-global-os": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$($Root -replace '\\','\\\\')'; subprocess.run([sys.executable,'-m','aios_mcp.aios_server'], cwd=root)"] },
    "context7": { "command": "npx", "args": ["-y", "@context7/mcp"] },
    "graphify": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$($Root -replace '\\','\\\\')'; subprocess.run([sys.executable, str(pathlib.Path(root)/'scripts'/'graphify_mcp_wrapper.py')])"] }
  },
  "alwaysAllow": { "tools": ["Read","grep","Glob","view"], "mcpTools": ["context7-get-library-docs","graphify-query","query_rules","check_policy","search_memory","search_memory_vector"] }
}
"@
Set-Content -Path "$ClaudeDir\settings.json" -Value $ClaudeSettings -Force

# Add CLI to PATH via batch shim
$ShimDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$Shim = "$ShimDir\ai-os.cmd"
$ShimContent = "@echo off`nset AGENT_OS_ROOT=$Root`nset PYTHONIOENCODING=utf-8`npython `"$Root\cli.py`" %*"
Set-Content -Path $Shim -Value $ShimContent -Force

Write-Host "AI Global OS installed to $Root"
Write-Host "CLI: ai-os status"
Write-Host "Restart your terminal to ensure PATH is updated."
