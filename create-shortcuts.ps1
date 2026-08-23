#Requires -Version 5.1
<#
.SYNOPSIS
    Create desktop shortcuts for aiZee with custom icons.
.DESCRIPTION
    Generates .lnk shortcuts for the dashboard launcher and installer,
    using favicon.ico so they show a proper icon instead of the default
    .bat icon. Run once after install, or re-run after updates.
.PARAMETER Desktop
    Create shortcuts on the public desktop (all users). Default: current user desktop.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File create-shortcuts.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File create-shortcuts.ps1 -Desktop AllUsers
#>
[CmdletBinding()]
param(
    [ValidateSet('CurrentUser', 'AllUsers')]
    [string]$Desktop = 'CurrentUser'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Icon = Join-Path $Root 'dashboard\static\favicon.ico'

if (-not (Test-Path $Icon)) {
    Write-Warning "favicon.ico not found at $Icon - shortcuts will use default .bat icon."
    $Icon = $null
}

# Resolve desktop path
if ($Desktop -eq 'AllUsers') {
    $DesktopPath = [Environment]::GetFolderPath('CommonDesktopDirectory')
} else {
    $DesktopPath = [Environment]::GetFolderPath('DesktopDirectory')
}

if (-not $DesktopPath -or -not (Test-Path $DesktopPath)) {
    Write-Error "Desktop directory not found: $DesktopPath"
    exit 1
}

$Shell = New-Object -ComObject WScript.Shell

$iconLoc = if ($Icon) { "$Icon,0" } else { $null }

$shortcuts = @(
    @{
        Name = 'aiZee Dashboard.lnk'
        Target = Join-Path $Root 'start-dashboard.bat'
        Description = 'Launch aiZee Dashboard (web UI)'
        IconLocation = $iconLoc
    },
    @{
        Name = 'aiZee Installer.lnk'
        Target = Join-Path $Root 'install.bat'
        Description = 'Run aiZee GUI Installer'
        IconLocation = $iconLoc
    }
)

$created = 0
foreach ($sc in $shortcuts) {
    $lnkPath = Join-Path $DesktopPath $sc.Name
    if (-not (Test-Path $sc.Target)) {
        Write-Warning "Target not found, skipping: $($sc.Target)"
        continue
    }
    $shortcut = $Shell.CreateShortcut($lnkPath)
    $shortcut.TargetPath = $sc.Target
    $shortcut.WorkingDirectory = $Root
    $shortcut.Description = $sc.Description
    $shortcut.WindowStyle = 1  # Normal
    if ($sc.IconLocation) {
        $shortcut.IconLocation = $sc.IconLocation
    }
    $shortcut.Save()
    Write-Host "Created: $lnkPath" -ForegroundColor Green
    $created++
}

Write-Host ""
Write-Host "Done. $created shortcut(s) created on desktop ($Desktop)." -ForegroundColor Cyan
if ($created -gt 0 -and $Icon) {
    Write-Host "Icons sourced from: $Icon" -ForegroundColor Gray
}
