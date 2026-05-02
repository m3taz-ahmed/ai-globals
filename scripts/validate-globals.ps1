# AI Globals Validation Script (PowerShell)
# This script ensures the repository follows its own standards.

$GlobalPath = "D:\server\.ai"
$RuleFiles = Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation..." -ForegroundColor Cyan

foreach ($File in $RuleFiles) {
    $Content = Get-Content $File.FullName -Raw
    $ErrorFound = $false

    # 1. Check for CRLF (Windows) line endings
    if ($Content -match "`r`n") {
        Write-Warning "CRLF detected in $($File.Name). Normalizing to LF..."
        $Content = $Content -replace "`r`n", "`n"
        Set-Content -Path $File.FullName -Value $Content -NoNewline -Encoding utf8
    }

    # 2. Check for H1 Title
    if ($Content -notmatch "^# ") {
        Write-Error "Missing H1 title in $($File.Name)"
        $ErrorFound = $true
    }

    # 3. Check for Backticks on tech terms (basic check for .md or .env)
    if ($Content -match "(?<!`)(README\.md|\.env|package\.json|composer\.json)(?!`)") {
        Write-Warning "Technical term without backticks found in $($File.Name)"
    }

    if (-not $ErrorFound) {
        Write-Host "✅ $($File.Name) passed." -ForegroundColor Green
    }
}

Write-Host "Validation Complete." -ForegroundColor Cyan
