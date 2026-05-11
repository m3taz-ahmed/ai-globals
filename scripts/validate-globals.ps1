# AI Globals Validation Script (PowerShell) v4.9.0
# This script ensures the repository follows its own standards.

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$GenerateManifest,
    [switch]$Force,
    [switch]$Fix,
    [switch]$Interactive
)

$GlobalPath = $PSScriptRoot | Split-Path

if (-not $GlobalPath -or -not (Test-Path -LiteralPath $GlobalPath)) {
    Write-Error "Invalid or empty global path: '$GlobalPath'. Ensure this script runs from within the .ai directory."
    exit 1
}

# Fuzzy Match Helper
function Get-FuzzyMatch($Target, $List) {
    # 1. Exact match
    if ($List -contains $Target) { return $Target }
    
    # 2. Case-insensitive basename match
    $TargetBase = [System.IO.Path]::GetFileName($Target)
    $Match = $List | Where-Object { [System.IO.Path]::GetFileName($_) -eq $TargetBase } | Select-Object -First 1
    if ($Match) { return $Match }

    # 3. Fuzzy search (partial match)
    $Match = $List | Where-Object { $_ -like "*$TargetBase*" } | Select-Object -First 1
    if ($Match) { return $Match }

    return $null
}

$RuleFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
$RuleFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse

Write-Host "Starting AI Globals Validation v4.9.0 [Self-Healing Mode: $(if($Fix){"ON"}else{"OFF"})]..." -ForegroundColor Cyan

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
    $SecretRegex = '(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)\s*[:=]\s*[\x22\x27]?([a-zA-Z0-9\/\+]' + [char]123 + '20,' + [char]125 + ')'
    if ($Content -match $SecretRegex) {
        Write-Error "Potential SECRET detected in ${FileName}: $($Matches[0])"
        $ErrorFound = $true; $ErrorCount++
    }

    # 4. H1 Title (Support Markdown # and HTML <h1>)
    if ($Content -notmatch "(?m)^#\s+.+" -and $Content -notmatch "(?i)<h1>.+</h1>") {
        Write-Error "Missing H1 title in $FileName"
        $ErrorFound = $true; $ErrorCount++
    }

    # 5. Cross-Reference Self-Healing (Enhanced with Fuzzy Matching & Interaction)
    $Refs = [regex]::Matches($Content, "([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)")
    foreach ($Ref in $Refs) {
        $RawTargetFile = $Ref.Groups[1].Value
        $TargetFile = $RawTargetFile.Replace("/", "\")
        $SectionNum = $Ref.Groups[2].Value
        
        $ResolvedPath = Get-FuzzyMatch $TargetFile $GlobalHeaders.Keys

        if (-not $ResolvedPath) {
            Write-Error "Broken Reference in ${FileName}: Target '$TargetFile' not found."
            $ErrorFound = $true; $ErrorCount++
        } elseif ($GlobalHeaders[$ResolvedPath] -notcontains $SectionNum) {
            # Fuzzy match for section header (if SectionNum is slightly off, e.g. 1.1 instead of 1)
            $NearMatch = $GlobalHeaders[$ResolvedPath] | Where-Object { $_ -like "$SectionNum*" -or $SectionNum -like "$_*" } | Select-Object -First 1
            
            if ($Fix -and $NearMatch) {
                $ShouldApply = $true
                if ($Interactive) {
                    $choice = Read-Host "Found broken section §$SectionNum in $FileName (referencing $ResolvedPath). Suggesting fix to §$NearMatch. Apply? [Y/N]"
                    if ($choice -ne 'Y') { $ShouldApply = $false }
                }
                
                if ($ShouldApply) {
                    $Content = $Content.Replace("$RawTargetFile §$SectionNum", "$RawTargetFile §$NearMatch")
                    $FileModified = $true; $FixedCount++
                    Write-Host "Healed section: §$SectionNum -> §$NearMatch in $FileName" -ForegroundColor Gray
                }
            } else {
                Write-Error "Broken Reference in ${FileName}: Section '§$SectionNum' not found in '$ResolvedPath'."
                $ErrorFound = $true; $ErrorCount++
            }
        } elseif ($Fix -and $TargetFile -ne $ResolvedPath) {
            # Auto-Fix Path
            $ShouldApply = $true
            if ($Interactive) {
                $choice = Read-Host "Found broken path '$TargetFile' in $FileName. Suggesting fix to '$ResolvedPath'. Apply? [Y/N]"
                if ($choice -ne 'Y') { $ShouldApply = $false }
            }

            if ($ShouldApply) {
                $Content = $Content.Replace($RawTargetFile, $ResolvedPath.Replace("\", "/"))
                $FileModified = $true; $FixedCount++
                Write-Host "Healed path: $TargetFile -> $ResolvedPath in $FileName" -ForegroundColor Gray
            }
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
$ReadmeVersion = if ((Get-Content "$GlobalPath\README.md" -Raw -Encoding UTF8) -match "badge/.*?-$VersionPattern") { $Matches[1] } else { "NF" }
$ChangelogVersion = if ((Get-Content "$GlobalPath\CHANGELOG.md" -Raw -Encoding UTF8) -match "(?m)^##\s*\[v?$VersionPattern\]") { $Matches[1] } else { "NF" }
$ScriptVersion = if ((Get-Content "$GlobalPath\scripts\validate-globals.ps1" -Raw -Encoding UTF8) -match "Validation.*?v(\d+\.\d+\.\d+)") { $Matches[1] } else { "NF" }

$Versions = @($ReadmeVersion, $ChangelogVersion, $ScriptVersion) | Where-Object { $_ -ne "NF" } | Select-Object -Unique
if ($Versions.Count -ne 1) { Write-Error "Version Mismatch! README=$ReadmeVersion, CL=$ChangelogVersion, Script=$ScriptVersion"; $ErrorCount++ }
else { Write-Host "Version: $($Versions -join '')" -ForegroundColor Green }

# 8. Manifest Update (Automatic regeneration after fixes)
if (-not $DryRun -and ($ErrorCount -eq 0 -or $Fix)) {
    Write-Host "Updating integrity.manifest..." -ForegroundColor Cyan
    $ManifestOutput = $NewManifest.Keys | Sort-Object | ForEach-Object { "$($NewManifest[$_])  $_" }
    [System.IO.File]::WriteAllLines($ManifestPath, $ManifestOutput, [System.Text.UTF8Encoding]::new($false))
}

Write-Host "`nSummary: Scanned=$ScannedCount, Skipped=$SkippedCount, Errors=$ErrorCount, Warnings=$WarningCount, Healed=$FixedCount"
exit [int]($ErrorCount -gt 0)

