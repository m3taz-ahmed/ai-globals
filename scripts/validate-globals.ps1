# AI Globals Validation Script (PowerShell) v4.2.0
# This script ensures the repository follows its own standards.
# NOTE: For PowerShell 7+ environments, consider replacing the main loop with
# $FileData.GetEnumerator() | ForEach-Object -Parallel { ... } for faster validation.
# PowerShell 5.1 does not support -Parallel; Runspaces could be used but add complexity
# that isn't justified for ~50 files.

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$GenerateManifest
)

$GlobalPath = $PSScriptRoot | Split-Path

if (-not $GlobalPath -or -not (Test-Path -LiteralPath $GlobalPath)) {
    Write-Error "Invalid or empty global path: '$GlobalPath'. Ensure this script runs from within the .ai directory."
    exit 1
}

$RuleFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
$RuleFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation v4.2.0..." -ForegroundColor Cyan

$ScannedCount = 0
$ErrorCount = 0
$WarningCount = 0

$FileData = @{}
foreach ($File in $RuleFiles) {
    $Content = Get-Content $File.FullName -Raw -Encoding UTF8
    $Headers = [regex]::Matches($Content, "^(#+)\s+(.+)$", "Multiline") | ForEach-Object { $_.Groups[2].Value.Trim() }
    $FileData[$File.Name] = @{
        Content  = $Content
        Headers  = $Headers
        FullName = $File.FullName
    }
}

foreach ($Entry in $FileData.GetEnumerator()) {
    $Content = $Entry.Value.Content
    $FileName = $Entry.Key
    $FilePath = $Entry.Value.FullName
    $ErrorFound = $false
    $ScannedCount++

    # 1. Check for CRLF (Windows) line endings
    if ($Content -match "`r`n") {
        Write-Warning "CRLF detected in $FileName. Normalizing to LF..."
        $Content = $Content -replace "`r`n", "`n"
        if (-not $DryRun) {
            [System.IO.File]::WriteAllText($FilePath, $Content, [System.Text.UTF8Encoding]::new($false))
        } else {
            Write-Host "DRY RUN: Would normalize CRLF in $FileName" -ForegroundColor Yellow
        }
        $WarningCount++
    }

    # 2. Check for UTF-8 BOM
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Warning "UTF-8 BOM detected in $FileName. Stripping BOM..."
        $Content = $Content.TrimStart([char]0xFEFF)
        if (-not $DryRun) {
            [System.IO.File]::WriteAllText($FilePath, $Content, [System.Text.UTF8Encoding]::new($false))
        } else {
            Write-Host "DRY RUN: Would strip BOM from $FileName" -ForegroundColor Yellow
        }
        $WarningCount++
    }

    # 3. Check for H1 Title
    if ($Content -notmatch "^# ") {
        Write-Error "Missing H1 title in $FileName"
        $ErrorFound = $true
        $ErrorCount++
    }

    # 4. Check for Backticks on tech terms (basic check for .md or .env)
    if ($Content -match "(?<!`)(README\.md|\.env|package\.json|composer\.json)(?!`)") {
        Write-Warning "Technical term without backticks found in $FileName"
        $WarningCount++
    }

    # 5. Check for mojibake encoding artifacts (broader detection)
    $rawBytes = [System.IO.File]::ReadAllBytes($FilePath)
    $rawText = [System.Text.Encoding]::UTF8.GetString($rawBytes)
    $mojibakePatterns = @(
        '\xE2\x80\x9C'
        '\xE2\x80\x9D'
        '\xE2\x80\x94'
        '\xE2\x80\x92'
        '\xE2\x82\xAC'
        '\xC3\xA2\x80\x9C'
        '\xC3\xA2\x80\x9D'
        '\xC3\xA2\x80\x94'
    )
    $mojibakeRegex = '(' + ($mojibakePatterns -join '|') + ')'
    if ($rawText -match $mojibakeRegex) {
        Write-Error ("Mojibake encoding artifact found in $FileName. " +
            "Replace with proper Unicode characters (em-dash: U+2014, right arrow: U+2192, smart quotes: U+201C/U+201D).")
        $ErrorFound = $true
        $ErrorCount++
    }
    if ($Content -match '\uFFFD') {
        Write-Error "Unicode replacement character (U+FFFD) found in $FileName. File may have encoding corruption."
        $ErrorFound = $true
        $ErrorCount++
    }

    # 6. Cross-Reference Validation (expanded patterns)
    $Refs = [regex]::Matches($Content, "(?:see|ref(?:erence)?|in|per|follow)\s+([\w-]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)", "IgnoreCase")
    $Refs += [regex]::Matches($Content, "([\w-]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)")
    $ProcessedRefs = @{}
    foreach ($Ref in $Refs) {
        $TargetFile = $Ref.Groups[1].Value
        $SectionNum = $Ref.Groups[2].Value
        $RefKey = "$TargetFile§$SectionNum"
        if ($ProcessedRefs.ContainsKey($RefKey)) { continue }
        $ProcessedRefs[$RefKey] = $true

        if ($FileData.ContainsKey($TargetFile)) {
            $TargetHeaders = $FileData[$TargetFile].Headers
            $SectionFound = $false
            foreach ($Header in $TargetHeaders) {
                if ($Header -match "^$SectionNum\.") {
                    $SectionFound = $true
                    break
                }
            }
            if (-not $SectionFound) {
                    Write-Error "Broken cross-reference in ${FileName}: Section ${SectionNum} not found in ${TargetFile}"
                $ErrorFound = $true
                $ErrorCount++
            }
        } else {
                Write-Error "Broken cross-reference in ${FileName}: Target file ${TargetFile} not found."
            $ErrorFound = $true
            $ErrorCount++
        }
    }

    if (-not $ErrorFound) {
        Write-Host "$FileName passed." -ForegroundColor Green
    }
}

# 7. Version Consistency Check
Write-Host "`nChecking version consistency..." -ForegroundColor Cyan
$VersionPattern = 'v?(\d+\.\d+\.\d+)'

$ReadmeContent = Get-Content "$GlobalPath\README.md" -Raw -Encoding UTF8
$ReadmeVersion = if ($ReadmeContent -match "Sovereignty\s*\(v?$VersionPattern\)") { $Matches[1] } else { "NOT_FOUND" }

$ChangelogContent = Get-Content "$GlobalPath\CHANGELOG.md" -Raw -Encoding UTF8
$ChangelogVersion = if ($ChangelogContent -match "^\[v?$VersionPattern\]") { $Matches[1] } else { "NOT_FOUND" }

$ScriptContent = Get-Content "$GlobalPath\scripts\validate-globals.ps1" -Raw -Encoding UTF8
$ScriptVersion = if ($ScriptContent -match 'Validation.*?v(\d+\.\d+\.\d+)') { $Matches[1] } else { "NOT_FOUND" }

$Versions = @($ReadmeVersion, $ChangelogVersion, $ScriptVersion) | Where-Object { $_ -ne "NOT_FOUND" } | Select-Object -Unique
if ($Versions.Count -gt 1) {
    Write-Error "Version mismatch detected! README=v$ReadmeVersion, CHANGELOG=v$ChangelogVersion, Script=v$ScriptVersion"
    $ErrorCount++
} elseif ($Versions.Count -eq 1) {
    Write-Host "Version consistency OK: v$($Versions[0])" -ForegroundColor Green
} else {
    Write-Warning "Could not detect version numbers for consistency check."
    $WarningCount++
}

# 8. Integrity Manifest (optional)
if ($GenerateManifest) {
    Write-Host "`nGenerating SHA-256 integrity manifest..." -ForegroundColor Cyan
    $Manifest = @()
    foreach ($Entry in $FileData.GetEnumerator()) {
        $Bytes = [System.IO.File]::ReadAllBytes($Entry.Value.FullName)
        $Hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($Bytes)
        $HashHex = [BitConverter]::ToString($Hash) -replace '-', ''
        $Manifest += "$HashHex  $($Entry.Key)"
    }
    $ManifestPath = Join-Path $GlobalPath "integrity.manifest"
    [System.IO.File]::WriteAllLines($ManifestPath, $Manifest, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Manifest written to: $ManifestPath" -ForegroundColor Green
}

Write-Host "`nValidation Summary:" -ForegroundColor Cyan
Write-Host "Files Scanned: $ScannedCount"
Write-Host "Errors: $ErrorCount" -ForegroundColor $(if ($ErrorCount -gt 0) { "Red" } else { "Gray" })
Write-Host "Warnings: $WarningCount" -ForegroundColor $(if ($WarningCount -gt 0) { "Yellow" } else { "Gray" })
if ($DryRun) {
    Write-Host "Mode: DRY RUN (no files modified)" -ForegroundColor Yellow
}

if ($ErrorCount -gt 0) {
    Write-Host "`nValidation FAILED." -ForegroundColor Red
    exit 1
} else {
    Write-Host "`nValidation SUCCESSFUL." -ForegroundColor Green
    exit 0
}
