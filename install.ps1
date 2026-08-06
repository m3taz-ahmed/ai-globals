# AI Global OS installer for Windows
# Idempotent: safe to run on first install or over an existing install.
# Preserves runtime state and cleans stale artifacts.
param(
    [switch]$WhatIf,
    [switch]$SkipPip,
    [switch]$SkipGraphify
)

$ErrorActionPreference = "Stop"

$Repo = $PSScriptRoot
if ($Repo -eq "" ) { $Repo = Get-Location }

$pythonVersion = & python --version 2>&1
if ($LASTEXITCODE -ne 0) { throw "python is required" }
if ($pythonVersion -notmatch "Python 3\.(1[0-9]|[2-9])") {
    throw "Python 3.10+ is required (found $pythonVersion)"
}

$Root = if ($env:AGENT_OS_ROOT) { $env:AGENT_OS_ROOT } else { "$env:LOCALAPPDATA\AI-Global-OS" }

if ($WhatIf) {
    Write-Host "WhatIf: would install AI Global OS from $Repo to $Root" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "[aios] $Message" -ForegroundColor Cyan
}

function Remove-IfExists {
    param([string]$Path)
    if (Test-Path $Path) {
        if ($WhatIf) {
            Write-Host "WhatIf: Remove-Item $Path -Recurse -Force"
        } else {
            Remove-Item -Path $Path -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function New-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        if ($WhatIf) {
            Write-Host "WhatIf: New-Item -Directory $Path"
        } else {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
        }
    }
}

function Invoke-Checked {
    param([scriptblock]$Script, [string]$FailureMessage)
    & $Script
    if ($LASTEXITCODE -ne 0) { throw $FailureMessage }
}

# Ensure target root exists
New-Directory $Root

# Preserve user state on reinstall
$StateBackup = $null
$BrainBackup = $null
if (Test-Path "$Root\state") {
    $StateBackup = "$env:TEMP\aios-state-$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Step "Preserving existing state to $StateBackup"
    if (-not $WhatIf) {
        Copy-Item -Path "$Root\state" -Destination $StateBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}
if (Test-Path "$Root\brain") {
    $BrainBackup = "$env:TEMP\aios-brain-$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Step "Preserving existing brain to $BrainBackup"
    if (-not $WhatIf) {
        Copy-Item -Path "$Root\brain" -Destination $BrainBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Directories/files that should never be copied from repo to install target
$Excludes = @(
    ".git",
    ".github",
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".pytest_cache",
    "node_modules",
    ".venv",
    "venv",
    "temp",
    "state",
    "brain",
    "graphify-out"
)

Write-Step "Copying repo contents to $Root"
Get-ChildItem -Path $Repo | Where-Object {
    $name = $_.Name
    $excluded = $false
    foreach ($pattern in $Excludes) {
        if ($name -like $pattern) { $excluded = $true; break }
        if ($_.Extension -and ($name -like "*.pyc" -or $name -like "*.pyo")) { $excluded = $true; break }
    }
    -not $excluded
} | ForEach-Object {
    $Dest = Join-Path $Root $_.Name
    if ($_.PSIsContainer) {
        Remove-IfExists $Dest
        if (-not $WhatIf) {
            Copy-Item -Path $_.FullName -Destination $Dest -Recurse -Force
        }
    } else {
        if (-not $WhatIf) {
            Copy-Item -Path $_.FullName -Destination $Dest -Force
        }
    }
}

# Restore state/brain if present
if ($StateBackup -and (Test-Path $StateBackup)) {
    Write-Step "Restoring state"
    if (-not $WhatIf) {
        New-Directory "$Root\state"
        Copy-Item -Path "$StateBackup\*" -Destination "$Root\state" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-IfExists $StateBackup
    }
}
if ($BrainBackup -and (Test-Path $BrainBackup)) {
    Write-Step "Restoring brain"
    if (-not $WhatIf) {
        New-Directory "$Root\brain"
        Copy-Item -Path "$BrainBackup\*" -Destination "$Root\brain" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-IfExists $BrainBackup
    }
}

# Install / update Python dependencies
if (-not $SkipPip) {
    Write-Step "Installing Python dependencies in $Root"
    $PipSpec = "$Root[dev,graphify]"
    if ($WhatIf) {
        Write-Host "WhatIf: python -m pip install -e `"$PipSpec`" --force-reinstall --no-deps"
    } else {
        & python -m pip install -e "$PipSpec" --force-reinstall
        if ($LASTEXITCODE -ne 0) { throw "Failed to install aios dependencies" }
    }
} else {
    Write-Step "Skipping pip install because -SkipPip was specified"
}

# Set the canonical root for the current process
$env:AGENT_OS_ROOT = $Root
[Environment]::SetEnvironmentVariable("AGENT_OS_ROOT", $Root, "User")

# Build the integrity manifest and knowledge graph from the installed source
$OriginalLocation = Get-Location
Set-Location $Root
try {
    Write-Step "Validating globals"
    if (-not $WhatIf) {
        & python scripts\validate-globals.py --fix
        if ($LASTEXITCODE -ne 0) { throw "validate-globals failed" }
    }
    if (-not $SkipGraphify) {
        Write-Step "Building knowledge graph"
        if (-not $WhatIf) {
            & python -m graphify update .
            if ($LASTEXITCODE -ne 0) { throw "graphify update failed" }
        }
    } else {
        Write-Step "Skipping graphify because -SkipGraphify was specified"
    }
} finally {
    Set-Location $OriginalLocation
}

# Symlink or copy agent configs into common locations
$Config = @{
    "$env:USERPROFILE\.claude\CLAUDE.md" = "$Root\.claude\CLAUDE.md"
    "$env:USERPROFILE\.claude\settings.json" = "$Root\.claude\settings.json"
    "$env:USERPROFILE\.claude\skills" = "$Root\.claude\skills"
    "$env:USERPROFILE\.claude\agents" = "$Root\.claude\agents"
    "$env:USERPROFILE\.devin\skills\global-os" = "$Root\.devin\skills\global-os"
    "$env:USERPROFILE\.windsurf\skills\global-os" = "$Root\.windsurf\skills\global-os"
    "$env:USERPROFILE\.aider.conf.yml" = "$Root\.aider.conf.yml"
}

foreach ($Target in $Config.Keys) {
    $Source = $Config[$Target]
    if (-not (Test-Path $Source)) {
        Write-Step "Skipping $Target because source $Source does not exist"
        continue
    }
    if (Test-Path $Target) {
        $Backup = "$Target.$(Get-Date -Format yyyyMMddHHmmss).backup"
        if (-not $WhatIf) {
            try {
                Move-Item -Path $Target -Destination $Backup -Force -ErrorAction SilentlyContinue
            } catch {
                Remove-IfExists $Target
            }
        } else {
            Write-Host "WhatIf: backup $Target -> $Backup"
        }
    }
    $Parent = Split-Path -Path $Target -Parent
    if ($Parent -and -not (Test-Path $Parent)) {
        New-Directory $Parent
    }
    if (Test-Path $Source -PathType Container) {
        try {
            if (-not $WhatIf) {
                New-Item -ItemType Junction -Path $Target -Target $Source -Force | Out-Null
            } else {
                Write-Host "WhatIf: New-Item Junction $Target -> $Source"
            }
        } catch {
            if (-not $WhatIf) {
                Remove-IfExists $Target
                Copy-Item -Path $Source -Destination $Target -Recurse -Force
            }
        }
    } else {
        try {
            if (-not $WhatIf) {
                New-Item -ItemType HardLink -Path $Target -Target $Source -Force | Out-Null
            } else {
                Write-Host "WhatIf: New-Item HardLink $Target -> $Source"
            }
        } catch {
            if (-not $WhatIf) {
                Copy-Item -Path $Source -Destination $Target -Force
            }
        }
    }
}

# Generate .claude/settings.json with absolute installed paths
$ClaudeDir = "$Root\.claude"
New-Directory $ClaudeDir
$EscapedRoot = $Root -replace '\\', '\\\\'
$ClaudeSettings = @"
{
  "permissions": {
    "allow": ["view","Read","grep","Glob","bash:git status","bash:git diff","bash:git log","bash:ls","bash:cd","bash:pwd","bash:graphify"],
    "ask": ["edit","write","Bash","bash:rm","bash:mv","bash:cp","mcp_call_tool","mcp_read_resource"],
    "deny": ["bash:rm -rf","bash:git reset --hard","bash:git checkout .","bash:git clean -fd","bash:git add -A","bash:git add .","bash:git push -f","bash:git stash","bash:curl -X POST","bash:curl -X DELETE","bash:Invoke-WebRequest -Method Post","bash:Invoke-WebRequest -Method Delete","bash:node -e","bash:python -c"]
  },
  "mcpServers": {
    "ai-global-os": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$($EscapedRoot)'; subprocess.run([sys.executable,'-m','aios_mcp.aios_server'], cwd=root)"] },
    "context7": { "command": "npx", "args": ["-y", "@context7/mcp"] },
    "graphify": { "command": "python", "args": ["-c", "import os,sys,subprocess,pathlib; root=os.environ.get('AGENT_OS_ROOT') or '$($EscapedRoot)'; subprocess.run([sys.executable, str(pathlib.Path(root)/'scripts'/'graphify_mcp_wrapper.py')])"] }
  },
  "alwaysAllow": { "tools": ["Read","grep","Glob","view"], "mcpTools": ["context7-get-library-docs","graphify-query","query_rules","check_policy","search_memory","search_memory_vector"] }
}
"@
if (-not $WhatIf) {
    Set-Content -Path "$ClaudeDir\settings.json" -Value $ClaudeSettings -Force
}

# Add CLI to PATH via batch shim
$ShimDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$Shim = "$ShimDir\ai-os.cmd"
$ShimContent = "@echo off`nset AGENT_OS_ROOT=$Root`nset PYTHONIOENCODING=utf-8`npython `"$Root\cli.py`" %*"
if (-not $WhatIf) {
    New-Directory $ShimDir
    Set-Content -Path $Shim -Value $ShimContent -Force
}

# Test the CLI works in the current process
Write-Step "Testing CLI"
if (-not $WhatIf) {
    $testOutput = & python "$Root\cli.py" status 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "CLI status check failed:`n$testOutput"
    } else {
        Write-Step "CLI OK"
    }
}

Write-Host "AI Global OS installed to $Root" -ForegroundColor Green
Write-Host "CLI: ai-os status" -ForegroundColor Green
Write-Host "Restart your terminal to ensure PATH and AGENT_OS_ROOT are updated." -ForegroundColor Yellow
