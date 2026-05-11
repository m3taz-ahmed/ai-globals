# AI Globals Validation Script (PowerShell) v4.8.0
# This script ensures the repository follows its own standards.

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$GenerateManifest,
    [switch]$Force,
    [switch]$Fix
)

$GlobalPath = $PSScriptRoot | Split-Path

if (-not $GlobalPath -or -not (Test-Path -LiteralPath $GlobalPath)) {
    Write-Error "Invalid or empty global path: '$GlobalPath'. Ensure this script runs from within the .ai directory."
    exit 1
}

$RuleFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
$RuleFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation v4.8.0 [Self-Healing Mode: $(if($Fix){"ON"}else{"OFF"})]..." -ForegroundColor Cyan

$ScannedCount = 0; $SkippedCount = 0; $ErrorCount = 0; $WarningCount = 0; $FixedCount = 0

# 0. Load Integrity Manifest
$Manifest = @{}
$ManifestPath = Join-Path $GlobalPath "integrity.manifest"
if (Test-Path $ManifestPath) {
    Get-Content $ManifestPath | ForEach-Object {
        if ($_ -match "^\s*([A-F0-9]{64})\s+(.+)$") {
            $Manifest[$Matches[2].Trim()] = $Matches[1]
        }
    }
}

# 1. Rule Propagation Check
$CoreFiles = @("global-workflow.md", "global-roles.md") + (Get-ChildItem -Path "$GlobalPath\rules" -Filter "*.md" -File).FullName
$ForceScan = $Force
foreach ($CoreFile in $CoreFiles) {
    $Rel = $CoreFile.Replace("$GlobalPath\", "")
    $Hash = [BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([System.IO.File]::ReadAllBytes($CoreFile))) -replace '-', ''
    if ($Manifest[$Rel] -ne $Hash) {
        $ForceScan = $true
        Write-Host "Core rule change detected in $Rel. Forcing full system scan..." -ForegroundColor Yellow
        break
    }
}

$FileData = @{}
$GlobalHeaders = @{}

# Pass 1: Collect Data
foreach ($File in $RuleFiles) {
    $ContentBytes = [System.IO.File]::ReadAllBytes($File.FullName)
    $CurrentHash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($ContentBytes)
    $CurrentHashHex = [BitConverter]::ToString($CurrentHash) -replace '-', ''
    $RelativeName = $File.FullName.Replace("$GlobalPath\", "")
    
    if (-not $ForceScan -and $Manifest.ContainsKey($RelativeName) -and $Manifest[$RelativeName] -eq $CurrentHashHex) {
        $SkippedCount++
        $Content = [System.Text.Encoding]::UTF8.GetString($ContentBytes)
        $Matches_Headers = [regex]::Matches($Content, "(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$")
        $Headers = @()
        foreach ($m in $Matches_Headers) { $Headers += $m.Groups[1].Value.Trim() }
        $GlobalHeaders[$RelativeName] = $Headers
        continue
    }

    $Content = [System.Text.Encoding]::UTF8.GetString($ContentBytes)
    $Matches_Headers = [regex]::Matches($Content, "(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$")
    $Headers = @()
    foreach ($m in $Matches_Headers) { $Headers += $m.Groups[1].Value.Trim() }
    $GlobalHeaders[$RelativeName] = $Headers

    $FileData[$RelativeName] = @{
        Content  = $Content
        FullName = $File.FullName
        Hash     = $CurrentHashHex
    }
}

$NewManifest = $Manifest.Clone()

# Pass 2: Validation & Healing
foreach ($Entry in $FileData.GetEnumerator()) {
    $Content = $Entry.Value.Content
    $FileName = $Entry.Key
    $FilePath = $Entry.Value.FullName
    $ErrorFound = $false; $FileModified = $false
    $ScannedCount++

    # 1. Line Endings (LF)
    if ($Content -match "`r`n") {
        if ($Fix) {
            $Content = $Content -replace "`r`n", "`n"
            $FileModified = $true; $FixedCount++
            Write-Host "Fixed CRLF in $FileName" -ForegroundColor Gray
        } else {
            Write-Warning "CRLF detected in $FileName."
            $WarningCount++
        }
    }

    # 2. UTF-8 BOM
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        if ($Fix) {
            $Content = $Content.TrimStart([char]0xFEFF)
            $FileModified = $true; $FixedCount++
            Write-Host "Stripped BOM in $FileName" -ForegroundColor Gray
        } else {
            Write-Warning "UTF-8 BOM detected in $FileName."
            $WarningCount++
        }
    }

    # 3. Secret Scanner
    # Constructed dynamically to avoid literal curly braces confusing IDE syntax highlighters
    $SecretRegex = '(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)\s*[:=]\s*[\x22\x27]?([a-zA-Z0-9\/\+]' + [char]123 + '20,' + [char]125 + ')'
    if ($Content -match $SecretRegex) {
        Write-Error "Potential SECRET detected in ${FileName}: $($Matches[0])"
        $ErrorFound = $true; $ErrorCount++
    }


    # 4. H1 Title
    if ($Content -notmatch "^# ") {
        Write-Error "Missing H1 title in $FileName"
        $ErrorFound = $true; $ErrorCount++
    }

    # 5. Cross-Reference Self-Healing
    $Refs = [regex]::Matches($Content, "([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)")
    foreach ($Ref in $Refs) {
        $TargetFile = $Ref.Groups[1].Value.Replace("/", "\")
        $SectionNum = $Ref.Groups[2].Value
        
        $ResolvedPath = if ($GlobalHeaders.ContainsKey($TargetFile)) { $TargetFile }
                        else { ($GlobalHeaders.Keys | Where-Object { $_ -like "*\$TargetFile" -or $_ -eq $TargetFile }) | Select-Object -First 1 }

        if (-not $ResolvedPath) {
            Write-Error "Broken Reference in ${FileName}: Target '$TargetFile' not found."
            $ErrorFound = $true; $ErrorCount++
        } elseif ($GlobalHeaders[$ResolvedPath] -notcontains $SectionNum) {
            Write-Error "Broken Reference in ${FileName}: Section '§$SectionNum' not found in '$ResolvedPath'."
            $ErrorFound = $true; $ErrorCount++
        } elseif ($Fix -and $TargetFile -ne $ResolvedPath) {
            # Auto-Fix Path (e.g. anti-patterns.md -> rules\anti-patterns.md)
            $Content = $Content.Replace("$TargetFile §$SectionNum", "$ResolvedPath §$SectionNum")
            $FileModified = $true; $FixedCount++
            Write-Host "Healed link: $TargetFile -> $ResolvedPath in $FileName" -ForegroundColor Gray
        }
    }

    # 6. Mojibake
    if ($Content -match '(\xC3\xA2\x80\x9C|\xC3\xA2\x80\x9D|\xE2\x80\x9C|\xE2\x80\x9D|\uFFFD)') {
        Write-Error "Encoding artifact (mojibake) found in $FileName."
        $ErrorFound = $true; $ErrorCount++
    }

    # 7. Newline at end of file
    if ($Content -notmatch "\n$") {
        if ($Fix) {
            $Content += "`n"
            $FileModified = $true; $FixedCount++
            Write-Host "Added trailing newline to $FileName" -ForegroundColor Gray
        } else {
            Write-Warning "Missing trailing newline in $FileName."
            $WarningCount++
        }
    } elseif ($Content -match "\n\n$") {
        if ($Fix) {
            $Content = $Content.TrimEnd("`n") + "`n"
            $FileModified = $true; $FixedCount++
            Write-Host "Normalized trailing newlines in $FileName" -ForegroundColor Gray
        } else {
            Write-Warning "Multiple trailing newlines in $FileName."
            $WarningCount++
        }
    }

    if ($FileModified -and -not $DryRun) {
        [System.IO.File]::WriteAllText($FilePath, $Content, [System.Text.UTF8Encoding]::new($false))
        # Recalculate hash after fix
        $NewHash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Content))
        $Entry.Value.Hash = [BitConverter]::ToString($NewHash) -replace '-', ''
    }

    if (-not $ErrorFound) {
        Write-Host "$FileName passed." -ForegroundColor Green
        $NewManifest[$FileName] = $Entry.Value.Hash
    }
}

# 7. Version Consistency
$VersionPattern = '(\d+\.\d+\.\d+)'
$ReadmeVersion = if ((Get-Content "$GlobalPath\README.md" -Raw -Encoding UTF8) -match "Sovereignty\s*\(v?$VersionPattern\)") { $Matches[1] } else { "NF" }
$ChangelogVersion = if ((Get-Content "$GlobalPath\CHANGELOG.md" -Raw -Encoding UTF8) -match "(?m)^##\s*\[v?$VersionPattern\]") { $Matches[1] } else { "NF" }
$ScriptVersion = if ((Get-Content "$GlobalPath\scripts\validate-globals.ps1" -Raw -Encoding UTF8) -match "Validation.*?v(\d+\.\d+\.\d+)") { $Matches[1] } else { "NF" }

$Versions = @($ReadmeVersion, $ChangelogVersion, $ScriptVersion) | Where-Object { $_ -ne "NF" } | Select-Object -Unique
if ($Versions.Count -ne 1) { Write-Error "Version Mismatch! README=$ReadmeVersion, CL=$ChangelogVersion, Script=$ScriptVersion"; $ErrorCount++ }
else { Write-Host "Version: $($Versions -join '')" -ForegroundColor Green }

# 8. Manifest Update
if (-not $DryRun -and $ErrorCount -eq 0) {
    $ManifestOutput = $NewManifest.Keys | Sort-Object | ForEach-Object { "$($NewManifest[$_])  $_" }
    [System.IO.File]::WriteAllLines($ManifestPath, $ManifestOutput, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "`nSummary: Scanned=$ScannedCount, Skipped=$SkippedCount, Errors=$ErrorCount, Warnings=$WarningCount, Healed=$FixedCount"
exit [int]($ErrorCount -gt 0)

