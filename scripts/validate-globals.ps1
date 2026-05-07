# AI Globals Validation Script (PowerShell)
# This script ensures the repository follows its own standards.

$GlobalPath = $PSScriptRoot | Split-Path
$RuleFiles = Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation..." -ForegroundColor Cyan

foreach ($File in $RuleFiles) {
    $Content = Get-Content $File.FullName -Raw
    $ErrorFound = $false

    # 1. Check for CRLF (Windows) line endings
    if ($Content -match "`r`n") {
        Write-Warning "CRLF detected in $($File.Name). Normalizing to LF..."
        $Content = $Content -replace "`r`n", "`n"
        [System.IO.File]::WriteAllText($File.FullName, $Content, [System.Text.UTF8Encoding]::new($false))
    }

    # 2. Check for UTF-8 BOM
    $bytes = [System.IO.File]::ReadAllBytes($File.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Warning "UTF-8 BOM detected in $($File.Name). Stripping BOM..."
        $Content = $Content.TrimStart([char]0xFEFF)
        [System.IO.File]::WriteAllText($File.FullName, $Content, [System.Text.UTF8Encoding]::new($false))
    }

    # 3. Check for H1 Title
    if ($Content -notmatch "^# ") {
        Write-Error "Missing H1 title in $($File.Name)"
        $ErrorFound = $true
    }

    # 4. Check for Backticks on tech terms (basic check for .md or .env)
    if ($Content -match "(?<!`)(README\.md|\.env|package\.json|composer\.json)(?!`)") {
        Write-Warning "Technical term without backticks found in $($File.Name)"
    }

    # 5. Check for mojibake encoding artifacts
    $mojibakeEmDash = [char]0x00E2 + [string][char]0x20AC + [string][char]0x009C
    $mojibakeArrow = [char]0x00E2 + [string][char]0x0086 + [string][char]0x0092
    if ($Content -match [regex]::Escape($mojibakeEmDash) -or $Content -match [regex]::Escape($mojibakeArrow)) {
        Write-Error ("Mojibake encoding artifact found in $($File.Name). " +
            "Replace with proper Unicode characters (em-dash: U+2014, right arrow: U+2192).")
        $ErrorFound = $true
    }

    if (-not $ErrorFound) {
        Write-Host "$($File.Name) passed." -ForegroundColor Green
    }
}

Write-Host "Validation Complete." -ForegroundColor Cyan
