# aiZee installer for Windows
# Idempotent: safe to run on first install, reinstall, or after a git pull update.
# Preserves runtime state, runs migrations, verifies dependencies, and self-heals
# broken symlinks / stale paths.
#
# Usage:
#   .\install.ps1                    # Full install/update (auto-detect root)
#   .\install.ps1 -WhatIf            # Dry-run: show what would happen
#   .\install.ps1 -Update            # Update-only: skip file copy, run migrations + deps
#   .\install.ps1 -InstallDir PATH   # Force a specific install target (copy mode)
#   .\install.ps1 -SkipPip           # Skip pip install
#   .\install.ps1 -SkipGraphify      # Skip graphify build
#   .\install.ps1 -SkipMCP           # Skip MCP config generation
#   .\install.ps1 -Gui              # Launch WPF GUI installer
param(
    [switch]$WhatIf,
    [switch]$SkipPip,
    [switch]$SkipGraphify,
    [switch]$SkipMCP,
    [switch]$Update,
    [switch]$Gui,
    [string]$InstallDir
)

# ---------------------------------------------------------------------------
# GUI mode: delegate to the WPF installer
# ---------------------------------------------------------------------------
if ($Gui) {
    $guiScript = Join-Path $PSScriptRoot "installer\gui_installer.ps1"
    if (Test-Path $guiScript) {
        & powershell -ExecutionPolicy Bypass -File $guiScript @PSBoundParameters
        exit $LASTEXITCODE
    } else {
        Write-Err "GUI installer not found at $guiScript"
        exit 1
    }
}

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

$LogFile = $null

function Start-Log {
    param([string]$Root)
    $logDir = Join-Path $Root "state"
    if (-not (Test-Path $logDir)) { New-Directory $logDir }
    $script:LogFile = Join-Path $logDir "install-$(Get-Date -Format yyyyMMdd-HHmmss).log"
    if (-not $WhatIf) {
        Set-Content -Path $script:LogFile -Value "aiZee Install Log - $(Get-Date)`n" -Force
    }
}

function Write-Log {
    param([string]$Level, [string]$Message)
    $timestamp = Get-Date -Format "HH:mm:ss"
    $line = "[$timestamp] [$Level] $Message"
    if ($script:LogFile -and -not $WhatIf) {
        Add-Content -Path $script:LogFile -Value $line -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step {
    param([string]$Message)
    Write-Host "[aizee] $Message" -ForegroundColor Cyan
    Write-Log "INFO" $Message
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[aizee] OK: $Message" -ForegroundColor Green
    Write-Log "OK" $Message
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[aizee] WARN: $Message" -ForegroundColor Yellow
    Write-Log "WARN" $Message
}

function Write-Err {
    param([string]$Message)
    Write-Host "[aizee] ERROR: $Message" -ForegroundColor Red
    Write-Log "ERROR" $Message
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

function Test-Command {
    param([string]$Name)
    $null = Get-Command $Name -ErrorAction SilentlyContinue
    return [bool]$?
}

# ---------------------------------------------------------------------------
# Retry logic for pip and other flaky commands
# ---------------------------------------------------------------------------

function Invoke-WithRetry {
    param(
        [scriptblock]$Script,
        [string]$Description = "command",
        [int]$MaxRetries = 3,
        [int]$BaseDelaySec = 2
    )
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Step "$Description (attempt $attempt/$MaxRetries)"
        if ($WhatIf) {
            Write-Host "WhatIf: $Description"
            return $true
        }
        try {
            & $Script
            if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq $null) {
                return $true
            }
            throw "Exit code: $LASTEXITCODE"
        } catch {
            $delay = $BaseDelaySec * $attempt
            Write-Warn "$Description failed (attempt $attempt): $_ -- retrying in ${delay}s"
            Start-Sleep -Seconds $delay
        }
    }
    Write-Err "$Description failed after $MaxRetries attempts"
    return $false
}

# ---------------------------------------------------------------------------
# Checksum verification
# ---------------------------------------------------------------------------

function Get-FileChecksum {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

function Test-FileChecksum {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path $Source) -or -not (Test-Path $Destination)) { return $false }
    $srcHash = Get-FileChecksum $Source
    $dstHash = Get-FileChecksum $Destination
    return $srcHash -eq $dstHash
}

# ---------------------------------------------------------------------------
# Auto-detect moved repo (if AIZEE_ROOT points to old location)
# ---------------------------------------------------------------------------

function Test-RootValid {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return $false }
    # A valid AIOS root must have pyproject.toml or config.py
    return (Test-Path (Join-Path $Root "pyproject.toml")) -or (Test-Path (Join-Path $Root "config.py"))
}

function Resolve-StaleRoot {
    param([string]$Repo, [string]$CurrentRoot)
    # If AIZEE_ROOT is set but invalid, or points to a different location
    # than the repo, prefer the repo if it's a valid AIOS root.
    if (-not $CurrentRoot -or -not (Test-RootValid $CurrentRoot)) {
        Write-Warn "AIZEE_ROOT points to invalid or missing location: $CurrentRoot"
        if (Test-RootValid $Repo) {
            Write-Step "Auto-detecting: using repo location as root: $Repo"
            return $Repo
        }
    }
    # Check if root has a .aizee-version but repo has a newer one (moved repo)
    $rootVersion = Get-InstalledVersion -Root $CurrentRoot
    $repoVersion = Get-TargetVersion -Root $Repo
    if ($rootVersion -and $repoVersion -and (Test-RootValid $Repo) -and -not (Test-RootValid $CurrentRoot)) {
        Write-Warn "Root at $CurrentRoot appears stale (no pyproject.toml). Repo at $Repo is valid."
        return $Repo
    }
    return $CurrentRoot
}

# ---------------------------------------------------------------------------
# Rollback support
# ---------------------------------------------------------------------------

$RollbackStack = [System.Collections.ArrayList]@()

function Push-Rollback {
    param([string]$Description, [scriptblock]$Undo)
    $script:RollbackStack.Add(@{ Description = $Description; Undo = $Undo }) | Out-Null
}

function Invoke-Rollback {
    param([string]$Reason)
    if ($script:RollbackStack.Count -eq 0) { return }
    Write-Err "Rolling back due to: $Reason"
    Write-Log "ROLLBACK" "Reason: $Reason"
    # Execute undo actions in reverse order
    for ($i = $script:RollbackStack.Count - 1; $i -ge 0; $i--) {
        $action = $script:RollbackStack[$i]
        Write-Warn "Rollback: $($action.Description)"
        Write-Log "ROLLBACK" "Undo: $($action.Description)"
        if (-not $WhatIf) {
            try {
                & $action.Undo
            } catch {
                Write-Warn "Rollback step failed: $_"
            }
        }
    }
    $script:RollbackStack.Clear()
}

# ---------------------------------------------------------------------------
# Health check for MCP servers
# ---------------------------------------------------------------------------

function Test-MCPServers {
    param([string]$Root)
    Write-Step "Health check: MCP servers"
    $results = @{}
    $configPath = Join-Path $Root ".devin\mcp_config.json"
    if (-not (Test-Path $configPath)) {
        $configPath = Join-Path $Root "aizee_mcp\config.json"
    }
    if (-not (Test-Path $configPath)) {
        Write-Warn "No MCP config found"
        return $results
    }
    try {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
        foreach ($serverName in $config.mcpServers.PSObject.Properties.Name) {
            $server = $config.mcpServers.$serverName
            $cmd = $server.command
            if ($cmd -eq "python") {
                # Test if the Python MCP server can start
                $results[$serverName] = "python-based (deferred)"
            } elseif ($cmd -eq "npx") {
                if (Test-Command "npx") {
                    $results[$serverName] = "ready"
                } else {
                    $results[$serverName] = "npx not found"
                }
            } elseif ($cmd -eq "uvx") {
                if (Test-Command "uvx") {
                    $results[$serverName] = "ready"
                } else {
                    $results[$serverName] = "uvx not found"
                }
            }
        }
    } catch {
        Write-Warn "Failed to parse MCP config: $_"
    }
    foreach ($name in $results.Keys) {
        $status = $results[$name]
        if ($status -eq "ready") {
            Write-Ok "MCP ${name}: ${status}"
        } else {
            Write-Warn "MCP ${name}: ${status}"
        }
    }
    return $results
}

function Get-InstalledVersion {
    param([string]$Root)
    $vf = Join-Path $Root ".aizee-version"
    if (Test-Path $vf) {
        return (Get-Content $vf -Raw).Trim()
    }
    return $null
}

function Get-TargetVersion {
    param([string]$Root)
    $pyproject = Join-Path $Root "pyproject.toml"
    if (-not (Test-Path $pyproject)) { return "0.0.0" }
    $content = Get-Content $pyproject -Raw
    if ($content -match 'version\s*=\s*"([^"]+)"') {
        return $matches[1]
    }
    return "0.0.0"
}

function Compare-Version {
    param([string]$A, [string]$B)
    $aParts = $A.Split(".") | ForEach-Object { [int]$_ }
    $bParts = $B.Split(".") | ForEach-Object { [int]$_ }
    while ($aParts.Count -lt 3) { $aParts += 0 }
    while ($bParts.Count -lt 3) { $bParts += 0 }
    for ($i = 0; $i -lt 3; $i++) {
        if ($aParts[$i] -lt $bParts[$i]) { return -1 }
        if ($aParts[$i] -gt $bParts[$i]) { return 1 }
    }
    return 0
}

# ---------------------------------------------------------------------------
# 0. Determine repo and root
# ---------------------------------------------------------------------------

$Repo = $PSScriptRoot
if ($Repo -eq "") { $Repo = (Get-Location).Path }

# Hybrid root detection:
#   - If -InstallDir is given -> copy mode (repo -> InstallDir)
#   - If the repo itself has pyproject.toml (in-place) -> root = repo
#   - Else -> fallback to LOCALAPPDATA\aiZee
if ($InstallDir) {
    $Root = $InstallDir
    $CopyMode = $true
} elseif (Test-Path (Join-Path $Repo "pyproject.toml")) {
    $Root = $Repo
    $CopyMode = $false
} else {
    $Root = if ($env:AIZEE_ROOT) { $env:AIZEE_ROOT } else { Join-Path $env:LOCALAPPDATA "aiZee" }
    $CopyMode = $true
}

# Auto-detect moved repo: if AIZEE_ROOT is stale, use repo location
if (-not $InstallDir -and $env:AIZEE_ROOT -and $env:AIZEE_ROOT -ne $Repo) {
    $Root = Resolve-StaleRoot -Repo $Repo -CurrentRoot $Root
}

if ($Update) { $CopyMode = $false }

# Start logging
Start-Log -Root $Root

if ($WhatIf) {
    Write-Host "WhatIf: would install aiZee" -ForegroundColor Cyan
    Write-Host "  Repo:      $Repo" -ForegroundColor Cyan
    Write-Host "  Root:      $Root" -ForegroundColor Cyan
    Write-Host "  CopyMode:  $CopyMode" -ForegroundColor Cyan
    Write-Host "  Update:    $Update" -ForegroundColor Cyan
}

# ---------------------------------------------------------------------------
# 1. Pre-flight checks
# ---------------------------------------------------------------------------

Write-Step "Pre-flight checks"

# Python
$prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
$pythonVersion = & python --version 2>&1
$pyExit = $LASTEXITCODE
$ErrorActionPreference = $prevEAP
if ($pyExit -ne 0) { throw "python is required but not found on PATH" }
if ($pythonVersion -notmatch "Python 3\.(1[0-9]|[2-9])") {
    throw "Python 3.10+ is required (found $pythonVersion)"
}
Write-Ok "Python: $pythonVersion"

# npm/npx (optional, needed for context7/upwork/freelancer MCPs)
$hasNpx = Test-Command "npx"
if ($hasNpx) {
    Write-Ok "npx: available"
} else {
    Write-Warn "npx: not found - context7/upwork/freelancer MCP servers will not be available"
}

# uvx (optional, needed for fiverr MCP)
$hasUvx = Test-Command "uvx"
if ($hasUvx) {
    Write-Ok "uvx: available"
} else {
    Write-Warn "uvx: not found - fiverr MCP server will not be available (install with: pip install uv)"
}

# Version check
$InstalledVersion = Get-InstalledVersion -Root $Root
$TargetVersion = Get-TargetVersion -Root $Repo
if ($InstalledVersion) {
    Write-Ok "Installed version: $InstalledVersion (target: $TargetVersion)"
} else {
    Write-Ok "First install (target: $TargetVersion)"
}

# If -Update and already at target version, exit early
if ($Update -and $InstalledVersion -and (Compare-Version $InstalledVersion $TargetVersion) -eq 0) {
    Write-Ok "Already at $TargetVersion - no update needed"
    exit 0
}

# ---------------------------------------------------------------------------
# 2. Ensure root directory exists
# ---------------------------------------------------------------------------

New-Directory $Root

# ---------------------------------------------------------------------------
# 3. Preserve user state on reinstall (copy mode only)
# ---------------------------------------------------------------------------

$StateBackup = $null
$BrainBackup = $null
$BackupDir = Join-Path $Root "state\.backups"
if ($CopyMode -and (Test-Path (Join-Path $Root "state"))) {
    if (-not (Test-Path $BackupDir)) { New-Directory $BackupDir }
    $StateBackup = Join-Path $BackupDir "state-$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Step "Preserving existing state to $StateBackup"
    if (-not $WhatIf) {
        Copy-Item -Path (Join-Path $Root "state") -Destination $StateBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}
if ($CopyMode -and (Test-Path (Join-Path $Root "brain"))) {
    if (-not (Test-Path $BackupDir)) { New-Directory $BackupDir }
    $BrainBackup = Join-Path $BackupDir "brain-$(Get-Date -Format yyyyMMddHHmmss)"
    Write-Step "Preserving existing brain to $BrainBackup"
    if (-not $WhatIf) {
        Copy-Item -Path (Join-Path $Root "brain") -Destination $BrainBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------------
# 4. Copy repo contents to root (copy mode only)
# ---------------------------------------------------------------------------

if ($CopyMode) {
    $Excludes = @(
        ".git", ".github", "__pycache__", "*.pyc", "*.pyo",
        ".pytest_cache", "node_modules", ".venv", "venv",
        "temp", "state", "brain", "graphify-out",
        ".ai", ".aizee-version", ".env",
        "backups", ".aizee-backups"
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

    # Restore state/brain
    if ($StateBackup -and (Test-Path $StateBackup)) {
        Write-Step "Restoring state"
        if (-not $WhatIf) {
            New-Directory (Join-Path $Root "state")
            Copy-Item -Path (Join-Path $StateBackup "*") -Destination (Join-Path $Root "state") -Recurse -Force -ErrorAction SilentlyContinue
            Remove-IfExists $StateBackup
        }
    }
    if ($BrainBackup -and (Test-Path $BrainBackup)) {
        Write-Step "Restoring brain"
        if (-not $WhatIf) {
            New-Directory (Join-Path $Root "brain")
            Copy-Item -Path (Join-Path $BrainBackup "*") -Destination (Join-Path $Root "brain") -Recurse -Force -ErrorAction SilentlyContinue
            Remove-IfExists $BrainBackup
        }
    }
} else {
    Write-Step "In-place mode - skipping file copy (root = repo)"
}

# ---------------------------------------------------------------------------
# 5. Run migrations
# ---------------------------------------------------------------------------

Write-Step "Checking migrations"
if (-not $WhatIf) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    & python (Join-Path $Repo "scripts\migrate.py") --root $Root 2>&1 | ForEach-Object { Write-Host $_ }
    $migExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($migExit -eq 2) {
        throw "Migration failed - see output above"
    }
    if ($migExit -eq 1) {
        Write-Ok "Migrations completed"
    } elseif ($migExit -eq 0) {
        Write-Ok "No migrations needed"
    }
} else {
    Write-Host "WhatIf: python scripts\migrate.py --root $Root"
}

# ---------------------------------------------------------------------------
# 6. Install / update Python dependencies (smart: only missing)
# ---------------------------------------------------------------------------

if (-not $SkipPip) {
    Write-Step "Checking Python dependencies"

    # Uninstall old 'aios' package if it exists (legacy rename cleanup)
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $null = & python -m pip show aios 2>&1
    $oldExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($oldExit -eq 0) {
        Write-Step "Removing legacy 'aios' package (renamed to 'aizee')"
        if (-not $WhatIf) {
            $prevEAP2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
            & python -m pip uninstall aios -y 2>&1 | ForEach-Object { Write-Host $_ }
            $ErrorActionPreference = $prevEAP2
        }
    }

    # --- Legacy cleanup: remove old ai-global-os / aios artifacts ---
    Write-Step "Legacy cleanup (ai-global-os -> aizee)"

    # 1. Remove old AGENT_OS_ROOT env var (renamed to AIZEE_ROOT)
    $oldOsRoot = [Environment]::GetEnvironmentVariable("AGENT_OS_ROOT", "User")
    if ($oldOsRoot) {
        Write-Step "Removing legacy AGENT_OS_ROOT env var (was: $oldOsRoot)"
        if (-not $WhatIf) {
            [Environment]::SetEnvironmentVariable("AGENT_OS_ROOT", $null, "User")
        }
    }
    $oldOsRootMachine = [Environment]::GetEnvironmentVariable("AGENT_OS_ROOT", "Machine")
    if ($oldOsRootMachine) {
        Write-Step "Removing legacy AGENT_OS_ROOT (Machine scope)"
        if (-not $WhatIf) {
            [Environment]::SetEnvironmentVariable("AGENT_OS_ROOT", $null, "Machine")
        }
    }

    # 2. Remove old AGENT_OS_DASHBOARD_TOKEN env var (renamed to AIZEE_DASHBOARD_TOKEN)
    $oldDashToken = [Environment]::GetEnvironmentVariable("AGENT_OS_DASHBOARD_TOKEN", "User")
    if ($oldDashToken) {
        Write-Step "Removing legacy AGENT_OS_DASHBOARD_TOKEN env var"
        if (-not $WhatIf) {
            [Environment]::SetEnvironmentVariable("AGENT_OS_DASHBOARD_TOKEN", $null, "User")
        }
    }

    # 3. Remove old CLI shim (ai-os.cmd) if it exists
    $oldShim = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\ai-os.cmd"
    if (Test-Path $oldShim) {
        Write-Step "Removing legacy CLI shim: $oldShim"
        if (-not $WhatIf) {
            Remove-Item $oldShim -Force -ErrorAction SilentlyContinue
        }
    }

    # 4. Remove old .aios-version file if it exists in root
    $oldVersionFile = Join-Path $Root ".aios-version"
    if (Test-Path $oldVersionFile) {
        Write-Step "Removing legacy .aios-version file"
        if (-not $WhatIf) {
            Remove-Item $oldVersionFile -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Ok "Legacy cleanup complete"

    $PipSpec = "$Root[dev,graphify]"
    if ($WhatIf) {
        Write-Host "WhatIf: python -m pip install -e `"$PipSpec`""
    } else {
        # Use --no-deps only on first install to avoid clobbering; on update,
        # install normally to pull in new transitive deps.
        $pipArgs = if ($InstalledVersion -and -not $Update) { @("-e", $PipSpec, "--no-deps") } else { @("-e", $PipSpec) }
        $pipOk = Invoke-WithRetry -Description "pip install aizee" -Script {
            $prevEAP = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            & python -m pip install @pipArgs 2>&1 | ForEach-Object { Write-Host $_ }
            $ec = $LASTEXITCODE
            $ErrorActionPreference = $prevEAP
            if ($ec -ne 0) { throw "pip exit $ec" }
        } -MaxRetries 3
        if (-not $pipOk) {
            Invoke-Rollback "pip install failed after retries"
            throw "Failed to install aizee dependencies after 3 attempts"
        }
        Push-Rollback "pip install" { Write-Log "ROLLBACK" "pip install cannot be undone" }
    }

    # Verify required packages
    Write-Step "Verifying required packages"
    $RequiredPackages = @("yaml", "mcp", "pydantic", "rich", "numpy", "cryptography")
    foreach ($pkg in $RequiredPackages) {
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        $check = & python -c "import $pkg; print('ok')" 2>&1
        $pkgExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        if ($pkgExit -ne 0) {
            Write-Warn "Missing package: $pkg - attempting install"
            if (-not $WhatIf) {
                $pkgOk = Invoke-WithRetry -Description "pip install $pkg" -Script {
                    $prevEAP2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
                    & python -m pip install $pkg 2>&1 | Out-Null
                    $ec = $LASTEXITCODE
                    $ErrorActionPreference = $prevEAP2
                    if ($ec -ne 0) { throw "pip exit $ec" }
                } -MaxRetries 2
                if (-not $pkgOk) { Write-Warn "Could not install $pkg" }
            }
        }
    }
    Write-Ok "Required packages verified"
} else {
    Write-Step "Skipping pip install (-SkipPip)"
}

# ---------------------------------------------------------------------------
# 7. Set the canonical root environment variable
# ---------------------------------------------------------------------------

$env:AIZEE_ROOT = $Root
if (-not $WhatIf) {
    [Environment]::SetEnvironmentVariable("AIZEE_ROOT", $Root, "User")
    Write-Ok "AIZEE_ROOT set to $Root (User scope)"
}

# ---------------------------------------------------------------------------
# 8. Validate globals + build knowledge graph
# ---------------------------------------------------------------------------

$OriginalLocation = Get-Location
Set-Location $Root
try {
    Write-Step "Validating globals"
    if (-not $WhatIf) {
        $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        & python scripts\validate-globals.py --fix 2>&1 | ForEach-Object { Write-Host $_ }
        $vgExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEAP
        if ($vgExit -ne 0) { throw "validate-globals failed" }
    } else {
        Write-Host "WhatIf: python scripts\validate-globals.py --fix"
    }

    if (-not $SkipGraphify) {
        Write-Step "Building knowledge graph"
        if (-not $WhatIf) {
            $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
            & python -m graphify update . 2>&1 | ForEach-Object { Write-Host $_ }
            $gfExit = $LASTEXITCODE
            $ErrorActionPreference = $prevEAP
            if ($gfExit -ne 0) { throw "graphify update failed" }
        } else {
            Write-Host "WhatIf: python -m graphify update ."
        }
    } else {
        Write-Step "Skipping graphify (-SkipGraphify)"
    }
} finally {
    Set-Location $OriginalLocation
}

# ---------------------------------------------------------------------------
# 9. Symlink / copy agent configs into common locations
# ---------------------------------------------------------------------------

if (-not $SkipMCP) {
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
            Write-Step "Skipping $Target (source $Source does not exist)"
            continue
        }

        # Check for broken symlink/junction and clean it
        if (Test-Path $Target) {
            $item = Get-Item $Target -Force -ErrorAction SilentlyContinue
            $isBroken = $false
            if ($item.LinkType -in @("SymbolicLink", "Junction", "HardLink")) {
                if (-not (Test-Path $item.Target)) { $isBroken = $true }
            }
            if ($isBroken) {
                Write-Warn "Removing broken link: $Target"
                if (-not $WhatIf) { Remove-IfExists $Target }
            }
        }

        # Backup existing if not a link we created
        if (Test-Path $Target) {
            $item = Get-Item $Target -Force -ErrorAction SilentlyContinue
            if ($item.LinkType -notin @("SymbolicLink", "Junction", "HardLink")) {
                $Backup = "$Target.$(Get-Date -Format yyyyMMddHHmmss).backup"
                Write-Step "Backing up $Target -> $Backup"
                if (-not $WhatIf) {
                    try {
                        Move-Item -Path $Target -Destination $Backup -Force -ErrorAction SilentlyContinue
                    } catch {
                        Remove-IfExists $Target
                    }
                }
            } else {
                # It is a valid link - remove it so we can recreate
                if (-not $WhatIf) { Remove-IfExists $Target }
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
                    Write-Host "WhatIf: Junction $Target -> $Source"
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
                    Write-Host "WhatIf: HardLink $Target -> $Source"
                }
            } catch {
                if (-not $WhatIf) {
                    Copy-Item -Path $Source -Destination $Target -Force
                }
            }
        }
    }

    # ---------------------------------------------------------------------------
    # 10. Generate .claude/settings.json with absolute installed paths
    # ---------------------------------------------------------------------------

    $ClaudeDir = Join-Path $Root ".claude"
    New-Directory $ClaudeDir
    $EscapedRoot = $Root -replace '\\', '\\\\'
    $ClaudeSettings = @"
{
  "permissions": {
    "allow": ["view","Read","read","grep","Glob","search","query","list","get","status","bash:git status","bash:git diff","bash:git log","bash:ls","bash:cd","bash:pwd","bash:graphify"],
    "ask": ["edit","write","Bash","bash:rm","bash:mv","bash:cp","mcp_call_tool","mcp_read_resource"],
    "deny": ["bash:rm -rf","bash:git reset --hard","bash:git checkout .","bash:git clean -fd","bash:git add -A","bash:git add .","bash:git push -f","bash:git stash","bash:curl -X POST","bash:curl -X DELETE","bash:Invoke-WebRequest -Method Post","bash:Invoke-WebRequest -Method Delete","bash:node -e","bash:python -c"]
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
"@
    if (-not $WhatIf) {
        Set-Content -Path (Join-Path $ClaudeDir "settings.json") -Value $ClaudeSettings -Force
    }
    Write-Ok "settings.json generated with root=$Root"
}

# ---------------------------------------------------------------------------
# 11. CLI shim
# ---------------------------------------------------------------------------

$ShimDir = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
$Shim = Join-Path $ShimDir "aizee.cmd"
$ShimContent = "@echo off`nset AIZEE_ROOT=$Root`nset PYTHONIOENCODING=utf-8`npython `"$Root\aizee_cli.py`" %*"
if (-not $WhatIf) {
    New-Directory $ShimDir
    Set-Content -Path $Shim -Value $ShimContent -Force
}
Write-Ok "CLI shim: $Shim"

# ---------------------------------------------------------------------------
# 11b. Global MCP config sync (IDE-agnostic)
# ---------------------------------------------------------------------------

Write-Step "Global MCP config sync"
if (-not $WhatIf) {
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $syncOutput = & python (Join-Path $Root "scripts\mcp_global_sync.py") 2>&1
    $syncExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($syncExit -eq 0) {
        Write-Ok "Global MCP config synced to %APPDATA%\devin\mcp_config.json"
    } else {
        Write-Warn "MCP global sync failed:`n$syncOutput"
    }

    # Verify the global config actually persisted (Devin CLI migrations can
    # reset it to {"mcpServers": {}} on startup). Re-sync once if empty.
    $globalCfg = Join-Path $env:APPDATA "devin\mcp_config.json"
    if (Test-Path $globalCfg) {
        try {
            $cfgData = Get-Content $globalCfg -Raw | ConvertFrom-Json
            $serverCount = @($cfgData.mcpServers.PSObject.Properties).Count
            if ($serverCount -eq 0) {
                Write-Warn "Global MCP config is empty after sync — re-writing (Devin may have reset it)"
                $prevEAP2 = $ErrorActionPreference; $ErrorActionPreference = "Continue"
                & python (Join-Path $Root "scripts\mcp_global_sync.py") 2>&1 | ForEach-Object { Write-Host $_ }
                $ErrorActionPreference = $prevEAP2
                $cfgData = Get-Content $globalCfg -Raw | ConvertFrom-Json
                $serverCount = @($cfgData.mcpServers.PSObject.Properties).Count
            }
            if ($serverCount -gt 0) {
                Write-Ok "Global MCP config verified: $serverCount servers (works from any workspace)"
            } else {
                Write-Warn "Global MCP config still empty after re-sync — run 'aizee mcp sync' manually"
            }
        } catch {
            Write-Warn "Could not verify global MCP config: $_"
        }
    }

    # Update global Devin AGENTS.md to point to the new root
    $devinDir = Join-Path $env:APPDATA "devin"
    $globalAgents = Join-Path $devinDir "AGENTS.md"
    $sourceAgents = Join-Path $Root "AGENTS.md"
    if (Test-Path $sourceAgents) {
        try {
            Copy-Item -Path $sourceAgents -Destination $globalAgents -Force
            Write-Ok "Global Devin AGENTS.md updated to root: $Root"
        } catch {
            Write-Warn "Could not update global Devin AGENTS.md: $_"
        }
    }
}

# ---------------------------------------------------------------------------
# 12. Post-install verification
# ---------------------------------------------------------------------------

Write-Step "Post-install verification"
if (-not $WhatIf) {
    # CLI test
    $prevEAP = $ErrorActionPreference; $ErrorActionPreference = "Continue"
    $testOutput = & python (Join-Path $Root "aizee_cli.py") status 2>&1
    $cliExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($cliExit -ne 0) {
        Write-Warn "CLI status check failed:`n$testOutput"
    } else {
        Write-Ok "CLI: aizee status works"
    }

    # AIZEE_ROOT verification
    $envRoot = [Environment]::GetEnvironmentVariable("AIZEE_ROOT", "User")
    if ($envRoot -ne $Root) {
        Write-Warn "AIZEE_ROOT mismatch: env=$envRoot, expected=$Root"
    } else {
        Write-Ok "AIZEE_ROOT verified: $Root"
    }

    # Config path verification
    $settingsPath = Join-Path $Root ".claude\settings.json"
    if (Test-Path $settingsPath) {
        $settingsContent = Get-Content $settingsPath -Raw
        if ($settingsContent -notmatch [regex]::Escape($Root)) {
            Write-Warn "settings.json does not contain current root path"
        } else {
            Write-Ok "settings.json paths verified"
        }
    }

    # MCP server health check
    if (-not $SkipMCP) {
        $null = Test-MCPServers -Root $Root
    }
}

# ---------------------------------------------------------------------------
# 13. Write .aizee-version
# ---------------------------------------------------------------------------

if (-not $WhatIf) {
    Set-Content -Path (Join-Path $Root ".aizee-version") -Value $TargetVersion -Force
}
Write-Ok "Version: $TargetVersion"

# ---------------------------------------------------------------------------
# 14. Cleanup old backups (keep last 3)
# ---------------------------------------------------------------------------

if (Test-Path $BackupDir) {
    Write-Step "Cleaning old backups (keeping last 3)"
    if (-not $WhatIf) {
        $stateBackups = Get-ChildItem -Path $BackupDir -Filter "state-*" -Directory | Sort-Object LastWriteTime -Descending
        if ($stateBackups.Count -gt 3) {
            $stateBackups | Select-Object -Skip 3 | ForEach-Object { Remove-IfExists $_.FullName }
        }
        $brainBackups = Get-ChildItem -Path $BackupDir -Filter "brain-*" -Directory | Sort-Object LastWriteTime -Descending
        if ($brainBackups.Count -gt 3) {
            $brainBackups | Select-Object -Skip 3 | ForEach-Object { Remove-IfExists $_.FullName }
        }
    }
}

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "aiZee $TargetVersion installed to $Root" -ForegroundColor Green
Write-Host "CLI: aizee status" -ForegroundColor Green
if ($LogFile) {
    Write-Host "Log: $LogFile" -ForegroundColor Gray
}
if (-not $Update) {
    Write-Host "Restart your terminal to ensure PATH and AIZEE_ROOT are updated." -ForegroundColor Yellow
}
