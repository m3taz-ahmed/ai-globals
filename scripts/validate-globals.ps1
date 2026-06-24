# AI Globals Validation Script (PowerShell) v4.20.0
# Thin wrapper — delegates all logic to validate-globals.py (source of truth).

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$GenerateManifest,
    [switch]$Force,
    [switch]$Fix,
    [switch]$Interactive
)

$PyScript = Join-Path $PSScriptRoot "validate-globals.py"
if (-not (Test-Path $PyScript)) {
    Write-Error "validate-globals.py not found at: $PyScript"
    exit 2
}

$PyArgs = @()
if ($DryRun)           { $PyArgs += "--dry-run" }
if ($GenerateManifest) { $PyArgs += "--generate-manifest" }
if ($Force)            { $PyArgs += "--force" }
if ($Fix)              { $PyArgs += "--fix" }
if ($Interactive)      { $PyArgs += "--interactive" }

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) { $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $PythonCmd) {
    Write-Error "Python not found. Install Python 3.10+ and ensure it is on PATH."
    exit 2
}

& $PythonCmd.Source $PyScript @PyArgs
exit $LASTEXITCODE
