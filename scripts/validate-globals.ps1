# AI Globals Validation Script (PowerShell) v4.1.0
# This script ensures the repository follows its own standards.

$GlobalPath = $PSScriptRoot | Split-Path
# Expand scope to include root-level markdown files
$RuleFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
$RuleFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation v4.1.0..." -ForegroundColor Cyan

$ScannedCount = 0
$ErrorCount = 0
$WarningCount = 0

# Cache headers for cross-reference validation
$FileHeaders = @{}
foreach ($File in $RuleFiles) {
    $Content = Get-Content $File.FullName -Raw
    $Headers = [regex]::Matches($Content, "^(#+)\s+(.+)$", "Multiline") | ForEach-Object { $_.Groups[2].Value.Trim() }
    $FileHeaders[$File.Name] = $Headers
}

foreach ($File in $RuleFiles) {
    $Content = Get-Content $File.FullName -Raw
    $ErrorFound = $false
    $ScannedCount++

    # 1. Check for CRLF (Windows) line endings
    if ($Content -match "`r`n") {
        Write-Warning "CRLF detected in $($File.Name). Normalizing to LF..."
        $Content = $Content -replace "`r`n", "`n"
        [System.IO.File]::WriteAllText($File.FullName, $Content, [System.Text.UTF8Encoding]::new($false))
        $WarningCount++
    }

    # 2. Check for UTF-8 BOM
    $bytes = [System.IO.File]::ReadAllBytes($File.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Warning "UTF-8 BOM detected in $($File.Name). Stripping BOM..."
        $Content = $Content.TrimStart([char]0xFEFF)
        [System.IO.File]::WriteAllText($File.FullName, $Content, [System.Text.UTF8Encoding]::new($false))
        $WarningCount++
    }

    # 3. Check for H1 Title
    if ($Content -notmatch "^# ") {
        Write-Error "Missing H1 title in $($File.Name)"
        $ErrorFound = $true
        $ErrorCount++
    }

    # 4. Check for Backticks on tech terms (basic check for .md or .env)
    if ($Content -match "(?<!`)(README\.md|\.env|package\.json|composer\.json)(?!`)") {
        Write-Warning "Technical term without backticks found in $($File.Name)"
        $WarningCount++
    }

    # 5. Check for mojibake encoding artifacts
    $mojibakeEmDash = [char]0x00E2 + [string][char]0x20AC + [string][char]0x009C
    $mojibakeArrow = [char]0x00E2 + [string][char]0x0086 + [string][char]0x0092
    $mojibakeAlternativeEmDash = [char]0x00E2 + [string][char]0x0080 + [string][char]0x0094
    if ($Content -match [regex]::Escape($mojibakeEmDash) -or $Content -match [regex]::Escape($mojibakeArrow) -or $Content -match [regex]::Escape($mojibakeAlternativeEmDash)) {
        Write-Error ("Mojibake encoding artifact found in $($File.Name). " +
            "Replace with proper Unicode characters (em-dash: U+2014, right arrow: U+2192).")
        $ErrorFound = $true
        $ErrorCount++
    }

    # 6. Cross-Reference Validation (§ Section Links)
    $Refs = [regex]::Matches($Content, "see\s+([\w-]+\.md)\s+§\s*(\d+)")
    foreach ($Ref in $Refs) {
        $TargetFile = $Ref.Groups[1].Value
        $SectionNum = $Ref.Groups[2].Value
        
        if ($FileHeaders.ContainsKey($TargetFile)) {
            $TargetHeaders = $FileHeaders[$TargetFile]
            $SectionFound = $false
            foreach ($Header in $TargetHeaders) {
                if ($Header -match "^$SectionNum\.") {
                    $SectionFound = $true
                    break
                }
            }
            if (-not $SectionFound) {
                Write-Error "Broken cross-reference in $($File.Name): Section § $SectionNum not found in $TargetFile"
                $ErrorFound = $true
                $ErrorCount++
            }
        } else {
            Write-Error "Broken cross-reference in $($File.Name): Target file $TargetFile not found."
            $ErrorFound = $true
            $ErrorCount++
        }
    }

    if (-not $ErrorFound) {
        Write-Host "$($File.Name) passed." -ForegroundColor Green
    }
}

Write-Host "`nValidation Summary:" -ForegroundColor Cyan
Write-Host "Files Scanned: $ScannedCount"
Write-Host "Errors: $ErrorCount" -ForegroundColor $(if ($ErrorCount -gt 0) { "Red" } else { "Gray" })
Write-Host "Warnings: $WarningCount" -ForegroundColor $(if ($WarningCount -gt 0) { "Yellow" } else { "Gray" })

if ($ErrorCount -gt 0) {
    Write-Host "`nValidation FAILED." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nValidation SUCCESSFUL." -ForegroundColor Green
    exit 0
}
