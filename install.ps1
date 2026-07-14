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

# Add CLI to PATH via batch shim
$ShimDir = "$env:LOCALAPPDATA\Microsoft\WindowsApps"
$Shim = "$ShimDir\ai-os.cmd"
$ShimContent = "@echo off`nset AGENT_OS_ROOT=$Root`nset PYTHONIOENCODING=utf-8`npython `"$Root\cli.py`" %*"
Set-Content -Path $Shim -Value $ShimContent -Force

Write-Host "AI Global OS installed to $Root"
Write-Host "CLI: ai-os status"
Write-Host "Restart your terminal to ensure PATH is updated."
