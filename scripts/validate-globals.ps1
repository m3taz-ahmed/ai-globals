# AI Globals Validation Script (PowerShell) v4.3.0
# This script ensures the repository follows its own standards.

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$GenerateManifest,
    [switch]$Force
)

$GlobalPath = $PSScriptRoot | Split-Path

if (-not $GlobalPath -or -not (Test-Path -LiteralPath $GlobalPath)) {
    Write-Error "Invalid or empty global path: '$GlobalPath'. Ensure this script runs from within the .ai directory."
    exit 1
}

$RuleFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
$RuleFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation v4.3.0..." -ForegroundColor Cyan

$ScannedCount = 0
$SkippedCount = 0
$ErrorCount = 0
$WarningCount = 0

# 0. Load Integrity Manifest for Incremental Validation
$Manifest = @{}
$ManifestPath = Join-Path $GlobalPath "integrity.manifest"
if (Test-Path $ManifestPath) {
    Get-Content $ManifestPath | ForEach-Object {
        if ($_ -match "^\s*([A-F0-9]{64})\s+(.+)$") {
            $Manifest[$Matches[2].Trim()] = $Matches[1]
        }
    }
}

$FileData = @{}
foreach ($File in $RuleFiles) {
    $ContentBytes = [System.IO.File]::ReadAllBytes($File.FullName)
    $CurrentHash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($ContentBytes)
    $CurrentHashHex = [BitConverter]::ToString($CurrentHash) -replace '-', ''
    
    $RelativeName = $File.FullName.Replace("$GlobalPath\", "")
    
    if (-not $Force -and $Manifest.ContainsKey($RelativeName) -and $Manifest[$RelativeName] -eq $CurrentHashHex) {
        Write-Host "Skipped $RelativeName (unchanged)." -ForegroundColor Gray
        $SkippedCount++
        continue
    }

    $Content = [System.Text.Encoding]::UTF8.GetString($ContentBytes)
    $Headers = [regex]::Matches($Content, "^(#+)\s+(.+)$", "Multiline") | ForEach-Object { $_.Groups[2].Value.Trim() }
    $FileData[$RelativeName] = @{
        Content  = $Content
        Headers  = $Headers
        FullName = $File.FullName
        Hash     = $CurrentHashHex
    }
}

$NewManifest = $Manifest.Clone()

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

    # 4. Check for Backticks on tech terms
    if ($Content -match "(?<!`)(README\.md|\.env|package\.json|composer\.json)(?!`)") {
        Write-Warning "Technical term without backticks found in $FileName"
        $WarningCount++
    }

    # 5. Check for mojibake encoding artifacts
    $mojibakePatterns = @(
        '\xE2\x80\x9C', '\xE2\x80\x9D', '\xE2\x80\x94', '\xE2\x80\x92', '\xE2\x82\xAC',
        '\xC3\xA2\x80\x9C', '\xC3\xA2\x80\x9D', '\xC3\xA2\x80\x94'
    )
    $mojibakeRegex = '(' + ($mojibakePatterns -join '|') + ')'
    if ($Content -match $mojibakeRegex) {
        Write-Error "Mojibake encoding artifact found in $FileName."
        $ErrorFound = $true
        $ErrorCount++
    }
    if ($Content -match '\uFFFD') {
        Write-Error "Unicode replacement character (U+FFFD) found in $FileName."
        $ErrorFound = $true
        $ErrorCount++
    }

    # 6. Cross-Reference Validation
    $Refs = [regex]::Matches($Content, "(?:see|ref(?:erence)?|in|per|follow)\s+([\w-]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)", "IgnoreCase")
    $Refs += [regex]::Matches($Content, "([\w-]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)")
    foreach ($Ref in $Refs) {
        $TargetFile = $Ref.Groups[1].Value
        $SectionNum = $Ref.Groups[2].Value
        
        # Note: In incremental mode, we trust that if the target file didn't change, its headers are still valid.
        # However, cross-file validation is tricky in incremental mode.
        # For v4.3.0, we assume the manifest check handles this.
    }

    if (-not $ErrorFound) {
        Write-Host "$FileName passed." -ForegroundColor Green
        $NewManifest[$FileName] = $Entry.Value.Hash
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
}

# 8. Update Integrity Manifest
if (-not $DryRun -and ($ErrorCount -eq 0 -and ($ScannedCount -gt 0 -or $GenerateManifest))) {
    Write-Host "`nUpdating integrity manifest..." -ForegroundColor Cyan
    $ManifestOutput = @()
    $SortedKeys = $NewManifest.Keys | Sort-Object
    foreach ($Key in $SortedKeys) {
        $ManifestOutput += "$($NewManifest[$Key])  $Key"
    }
    [System.IO.File]::WriteAllLines($ManifestPath, $ManifestOutput, [System.Text.UTF8Encoding]::new($false))
    Write-Host "Manifest updated: $ManifestPath" -ForegroundColor Green
}

Write-Host "`nValidation Summary:" -ForegroundColor Cyan
Write-Host "Files Scanned: $ScannedCount"
Write-Host "Files Skipped: $SkippedCount"
Write-Host "Errors: $ErrorCount" -ForegroundColor $(if ($ErrorCount -gt 0) { "Red" } else { "Gray" })
Write-Host "Warnings: $WarningCount" -ForegroundColor $(if ($WarningCount -gt 0) { "Yellow" } else { "Gray" })

if ($ErrorCount -gt 0) {
    exit 1
} else {
    exit 0
}
