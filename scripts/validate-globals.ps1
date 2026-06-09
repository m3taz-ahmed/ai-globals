# AI Globals Validation Script (PowerShell) v4.17.0
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
function Get-FuzzyMatch {
    param([string]$Target, [string[]]$List)
    if ($List -contains $Target) { return $Target }
    $TargetBase = [System.IO.Path]::GetFileName($Target)
    $Match = $List | Where-Object { [System.IO.Path]::GetFileName($_) -eq $TargetBase } | Select-Object -First 1
    if ($Match) { return $Match }
    $Match = $List | Where-Object { $_ -like "*$TargetBase*" } | Select-Object -First 1
    if ($Match) { return $Match }
    return $null
}

function Get-RuleFiles {
    param([string]$GlobalPath)
    $IgnoreLines = @()
    $IgnoreFile = Join-Path $GlobalPath ".aiignore"
    if (Test-Path $IgnoreFile) {
        $IgnoreLines = Get-Content $IgnoreFile | Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') } | ForEach-Object { $_.Trim().Replace('/', '\') }
    }
    
    $AllFiles = Get-ChildItem -Path "$GlobalPath" -Filter "*.md" -File
    $AllFiles += Get-ChildItem -Path "$GlobalPath\rules", "$GlobalPath\tech-stack", "$GlobalPath\workflows" -Filter "*.md" -Recurse
    
    $Filtered = @()
    foreach ($f in $AllFiles) {
        $rel = $f.FullName.Replace("$GlobalPath\", "")
        $ignored = $false
        foreach ($ignore in $IgnoreLines) {
            if ($rel -like "*$ignore*") {
                $ignored = $true
                break
            }
        }
        if (-not $ignored) {
            $Filtered += $f
        }
    }
    return $Filtered
}

function Get-IntegrityManifest {
    param([string]$ManifestPath)
    $Manifest = @{}
    if (Test-Path $ManifestPath) {
        Get-Content $ManifestPath | ForEach-Object {
            if ($_ -match "^\s*([A-F0-9]{64})\s+(.+)$") {
                $Manifest[$Matches[2].Trim()] = $Matches[1]
            }
        }
    }
    return $Manifest
}

function Get-FileHashHex {
    param([string]$FilePath)
    $Bytes = [System.IO.File]::ReadAllBytes($FilePath)
    $Hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($Bytes)
    return [BitConverter]::ToString($Hash) -replace '-', ''
}

function Test-CoreRules {
    param([string]$GlobalPath, [hashtable]$Manifest)
    $CoreFiles = @("global-workflow.md", "global-roles.md") + (Get-ChildItem -Path "$GlobalPath\rules" -Filter "*.md" -File).FullName
    foreach ($CoreFile in $CoreFiles) {
        $Rel = $CoreFile.Replace("$GlobalPath\", "")
        $Hash = Get-FileHashHex $CoreFile
        if ($Manifest[$Rel] -ne $Hash) {
            Write-Host "Core rule change detected in $Rel. Forcing full system scan..." -ForegroundColor Yellow
            return $true
        }
    }
    return $false
}

function Test-LineEndings {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    if ($Content -match "`r`n") {
        if ($ctx.Fix) {
            $ctx.FixedCount++
            Write-Host "Fixed CRLF in $FileName" -ForegroundColor Gray
            return $true, ($Content -replace "`r`n", "`n")
        } else {
            Write-Warning "CRLF detected in $FileName."
            $ctx.WarningCount++
        }
    }
    return $false, $Content
}

function Test-Utf8Bom {
    param([string]$FilePath, [string]$Content, [string]$FileName, [hashtable]$ctx)
    if (Test-Path $FilePath) {
        $fs = [System.IO.File]::OpenRead($FilePath)
        $headerBytes = New-Object byte[] 3
        $read = $fs.Read($headerBytes, 0, 3)
        $fs.Close()
        if ($read -eq 3 -and $headerBytes[0] -eq 0xEF -and $headerBytes[1] -eq 0xBB -and $headerBytes[2] -eq 0xBF) {
            if ($ctx.Fix) {
                $ctx.FixedCount++
                Write-Host "Stripped BOM in $FileName" -ForegroundColor Gray
                return $true, $Content.TrimStart([char]0xFEFF)
            } else {
                Write-Warning "UTF-8 BOM detected in $FileName."
                $ctx.WarningCount++
            }
        }
    }
    return $false, $Content
}

function Test-Secrets {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    $SecretRegex = '(?i)(password|api_key|secret|token|private_key|ssh-rsa|BEGIN\s+RSA\s+PRIVATE)\s*[:=]\s*[\x22\x27]?([a-zA-Z0-9\/\+\-_=]' + [char]123 + '20,' + [char]125 + ')'
    $Matches_Sec = [regex]::Matches($Content, $SecretRegex)
    $ErrorFound = $false
    foreach ($Match in $Matches_Sec) {
        $Val = $Match.Groups[2].Value
        $IsMock = $false
        foreach ($Mock in @('placeholder', 'your_', 'secret_here', 'token_here', 'example', 'mysecret', 'dummy', 'xxxx')) {
            if ($Val.ToLower().Contains($Mock)) { $IsMock = $true }
        }
        if (-not $IsMock) {
            Write-Error "Potential SECRET detected in ${FileName}: $($Match.Value)"
            $ctx.ErrorCount++
            $ErrorFound = $true
        }
    }
    return $ErrorFound
}

function Test-H1Title {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    if ($Content -notmatch "(?m)^#\s+.+" -and $Content -notmatch "(?i)<h1>.+</h1>") {
        Write-Error "Missing H1 title in $FileName"
        $ctx.ErrorCount++
        return $true
    }
    return $false
}

function Handle-BrokenSection {
    param([string]$Content, [string]$RawTargetFile, [string]$ResolvedPath, [string]$SectionNum, [string]$FileName, [hashtable]$ctx)
    $NearMatch = $ctx.GlobalHeaders[$ResolvedPath] | Where-Object { $_ -like "$SectionNum*" -or $SectionNum -like "$_*" } | Select-Object -First 1
    if ($ctx.Fix -and $NearMatch) {
        $ShouldApply = $true
        if ($ctx.Interactive) {
            $choice = Read-Host "Found broken section §$SectionNum in $FileName (referencing $ResolvedPath). Suggesting fix to §$NearMatch. Apply? [Y/N]"
            if ($choice -ne 'Y') { $ShouldApply = $false }
        }
        if ($ShouldApply) {
            $newContent = $Content.Replace("$RawTargetFile §$SectionNum", "$RawTargetFile §$NearMatch")
            $ctx.FixedCount++
            Write-Host "Healed section: §$SectionNum -> §$NearMatch in $FileName" -ForegroundColor Gray
            return $true, $newContent, $false
        }
    }
    Write-Error "Broken Reference in ${FileName}: Section '§$SectionNum' not found in '$ResolvedPath'."
    $ctx.ErrorCount++
    return $false, $Content, $true
}

function Test-CrossReferences {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    $Refs = [regex]::Matches($Content, "([\w\-\./]+\.md)\s+[§S]\s*(\d+(?:\.\d+)?)")
    $ErrorFound = $false; $FileModified = $false
    foreach ($Ref in $Refs) {
        $RawTargetFile = $Ref.Groups[1].Value
        $TargetFile = $RawTargetFile.Replace("/", "\")
        $SectionNum = $Ref.Groups[2].Value
        $ResolvedPath = Get-FuzzyMatch $TargetFile $ctx.GlobalHeaders.Keys
        if (-not $ResolvedPath) {
            Write-Error "Broken Reference in ${FileName}: Target '$TargetFile' not found."
            $ctx.ErrorCount++; $ErrorFound = $true
        } elseif ($ctx.GlobalHeaders[$ResolvedPath] -notcontains $SectionNum) {
            $applied, $Content, $err = Handle-BrokenSection $Content $RawTargetFile $ResolvedPath $SectionNum $FileName $ctx
            if ($applied) { $FileModified = $true }
            if ($err) { $ErrorFound = $true }
        } elseif ($ctx.Fix -and $TargetFile -ne $ResolvedPath) {
            if (-not $ctx.Interactive -or (Read-Host "Found broken path '$TargetFile' in $FileName. Fix to '$ResolvedPath'? [Y/N]") -eq 'Y') {
                $Content = $Content.Replace($RawTargetFile, $ResolvedPath.Replace("\", "/"))
                $FileModified = $true; $ctx.FixedCount++
                Write-Host "Healed path: $TargetFile -> $ResolvedPath in $FileName" -ForegroundColor Gray
            }
        }
    }
    return $FileModified, $Content, $ErrorFound
}

function Test-FileReferences {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    $IgnoredFileRefs = @('monthely-maintenance-prompt.md','nuxt-4.md','bun-1.md','drizzle-orm.md','09-ai-review.md','mobile-standards.md','GEMINI.md','workflows\NN-name.md','tech-stack\xxx.md','verification-patterns.md','filename.md','bug_report.md','feature_request.md','tech_stack_request.md','PULL_REQUEST_TEMPLATE.md','active-context.md','SKILL.md','memory-archive.md')
    $FileRefs = [regex]::Matches($Content, "(?i)\b([\w\-\./]+\.md)\b")
    $ErrorFound = $false
    foreach ($FileRef in $FileRefs) {
        $RawTargetFile = $FileRef.Groups[1].Value
        $IndexAfter = $FileRef.Index + $FileRef.Length
        if ($IndexAfter -lt $Content.Length -and $Content.Substring($IndexAfter) -match "^\s+[§S]\s*\d+") { continue }

        $TargetFile = $RawTargetFile.Replace("/", "\")
        if ($TargetFile -like "*server\.ai\*") {
            $TargetFile = $TargetFile -replace '^.*server\\\.ai\\', ''
        }
        $BaseTargetFile = [System.IO.Path]::GetFileName($TargetFile)
        if ($IgnoredFileRefs -contains $TargetFile -or $IgnoredFileRefs -contains $BaseTargetFile) { continue }
        $ResolvedPath = Get-FuzzyMatch $TargetFile $ctx.GlobalHeaders.Keys
        if (-not $ResolvedPath) {
            if (Test-Path (Join-Path $GlobalPath $TargetFile)) { continue }
            Write-Error "Broken File Reference in ${FileName}: Target '$TargetFile' not found."
            $ctx.ErrorCount++; $ErrorFound = $true
        }
    }
    return $ErrorFound
}

function Test-Mojibake {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    if ($Content -match '(\xC3\xA2\x80\x9C|\xC3\xA2\x80\x9D|\xE2\x80\x9C|\xE2\x80\x9D|\uFFFD)') {
        Write-Error "Encoding artifact (mojibake) found in $FileName."
        $ctx.ErrorCount++
        return $true
    }
    return $false
}

function Test-SymbolicCodes {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    $ErrorFound = $false
    $Refs = [regex]::Matches($Content, "\[([A-Z]{3,4}-\d{2})\]")
    foreach ($ref in $Refs) {
        $code = $ref.Groups[1].Value
        if ($FileName -like "*vocabulary.md") { continue }
        if (-not $ctx.DefinedCodes.ContainsKey($code)) {
            Write-Error "Undefined Symbolic Code in ${FileName}: '$code' is not defined in vocabulary.md."
            $ctx.ErrorCount++; $ErrorFound = $true
        }
    }
    return $ErrorFound
}

function Test-TrailingNewlines {
    param([string]$Content, [string]$FileName, [hashtable]$ctx)
    if ($Content -notmatch "\n$") {
        if ($ctx.Fix) {
            $ctx.FixedCount++
            Write-Host "Added trailing newline to $FileName" -ForegroundColor Gray
            return $true, ($Content + "`n")
        } else {
            Write-Warning "Missing trailing newline in $FileName."
            $ctx.WarningCount++
        }
    } elseif ($Content -match "\n\n$") {
        if ($ctx.Fix) {
            $ctx.FixedCount++
            Write-Host "Normalized trailing newlines in $FileName" -ForegroundColor Gray
            return $true, ($Content.TrimEnd("`n") + "`n")
        } else {
            Write-Warning "Multiple trailing newlines in $FileName."
            $ctx.WarningCount++
        }
    }
    return $false, $Content
}

function Test-SingleFile {
    param([string]$FileName, [hashtable]$EntryVal, [hashtable]$ctx)
    $Content = $EntryVal.Content
    $FilePath = $EntryVal.FullName
    $ctx.ScannedCount++
    
    $modLE, $Content = Test-LineEndings $Content $FileName $ctx
    $modBom, $Content = Test-Utf8Bom $FilePath $Content $FileName $ctx
    $errSec = Test-Secrets $Content $FileName $ctx
    $errH1 = Test-H1Title $Content $FileName $ctx
    $modRefs, $Content, $errRefs = Test-CrossReferences $Content $FileName $ctx
    $errFileRefs = Test-FileReferences $Content $FileName $ctx
    $errMoji = Test-Mojibake $Content $FileName $ctx
    $errCodes = Test-SymbolicCodes $Content $FileName $ctx
    $modNL, $Content = Test-TrailingNewlines $Content $FileName $ctx
    
    $FileModified = $modLE -or $modBom -or $modRefs -or $modNL
    $ErrorFound = $errSec -or $errH1 -or $errRefs -or $errFileRefs -or $errMoji -or $errCodes
    
    if ($FileModified -and -not $ctx.DryRun) {
        [System.IO.File]::WriteAllText($FilePath, $Content, [System.Text.UTF8Encoding]::new($false))
        $NewHash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($Content))
        $EntryVal.Hash = [BitConverter]::ToString($NewHash) -replace '-', ''
    }
    return $ErrorFound
}

function Extract-Version {
    param([string]$Path, [string]$Regex)
    if (-not (Test-Path $Path)) { return "NF" }
    $RawContent = Get-Content $Path -Raw -Encoding UTF8
    if ($RawContent -match $Regex) { return $Matches[1] }
    return "NF"
}

function Test-VersionConsistency {
    param([string]$GlobalPath, [hashtable]$ctx)
    $VersionPattern = '(\d+\.\d+\.\d+)'
    $ReadmeVersion = Extract-Version "$GlobalPath\README.md" "badge/.*?-$VersionPattern"
    $ReadmeArVersion = Extract-Version "$GlobalPath\README-AR.md" "badge/.*?-$VersionPattern"
    $ChangelogVersion = Extract-Version "$GlobalPath\CHANGELOG.md" "(?m)^##\s*\[v?$VersionPattern\]"
    $ScriptVersion = Extract-Version "$GlobalPath\scripts\validate-globals.ps1" "Validation.*?v$VersionPattern"
    $PyScriptVersion = Extract-Version "$GlobalPath\scripts\validate-globals.py" "Validation.*?v$VersionPattern"
    
    $Versions = @($ReadmeVersion, $ReadmeArVersion, $ChangelogVersion, $ScriptVersion, $PyScriptVersion) | Where-Object { $_ -ne "NF" } | Select-Object -Unique
    if ($Versions.Count -ne 1) {
        Write-Error "Version Mismatch! README=$ReadmeVersion, README-AR=$ReadmeArVersion, CL=$ChangelogVersion, Script=$ScriptVersion, PyScript=$PyScriptVersion"
        $ctx.ErrorCount++
        return $false
    }
    Write-Host "Version: $($Versions -join '')" -ForegroundColor Green
    return $true
}

function Update-IntegrityManifest {
    param([string]$ManifestPath, [hashtable]$NewManifest)
    Write-Host "Updating integrity.manifest..." -ForegroundColor Cyan
    $ManifestOutput = $NewManifest.Keys | Sort-Object | ForEach-Object { "$($NewManifest[$_])  $_" }
    [System.IO.File]::WriteAllLines($ManifestPath, $ManifestOutput, [System.Text.UTF8Encoding]::new($false))
}

function Get-Headers {
    param([string]$Content)
    $Matches_Headers = [regex]::Matches($Content, "(?m)^##\s+(\d+(?:\.\d+)?)\.?\s+(.+)$")
    $Headers = @()
    foreach ($m in $Matches_Headers) { $Headers += $m.Groups[1].Value.Trim() }
    return $Headers
}

function Run-Pass1 {
    param([object[]]$RuleFiles, [string]$GlobalPath, [hashtable]$Manifest, [bool]$ForceScan, [hashtable]$ctx)
    $FileData = @{}
    foreach ($File in $RuleFiles) {
        $RelativeName = $File.FullName.Replace("$GlobalPath\", "")
        $ContentBytes = [System.IO.File]::ReadAllBytes($File.FullName)
        $CurrentHashHex = [BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash($ContentBytes)) -replace '-', ''
        
        $Content = [System.Text.Encoding]::UTF8.GetString($ContentBytes)
        $ctx.GlobalHeaders[$RelativeName] = Get-Headers $Content
        
        if (-not $ForceScan -and $Manifest.ContainsKey($RelativeName) -and $Manifest[$RelativeName] -eq $CurrentHashHex) {
            $ctx.SkippedCount++
            continue
        }
        $FileData[$RelativeName] = @{ Content = $Content; FullName = $File.FullName; Hash = $CurrentHashHex }
    }
    return $FileData
}

function Run-Pass2 {
    param([hashtable]$FileData, [hashtable]$NewManifest, [hashtable]$ctx)
    foreach ($Entry in $FileData.GetEnumerator()) {
        $ErrorFound = Test-SingleFile $Entry.Key $Entry.Value $ctx
        if (-not $ErrorFound) {
            Write-Host "$($Entry.Key) passed." -ForegroundColor Green
            $NewManifest[$Entry.Key] = $Entry.Value.Hash
        } elseif ($NewManifest.ContainsKey($Entry.Key)) {
            $NewManifest.Remove($Entry.Key)
        }
    }
}

# Execution Start
$RuleFiles = Get-RuleFiles $GlobalPath
Write-Host "Starting AI Globals Validation v4.17.0 [Self-Healing Mode: $(if($Fix){"ON"}else{"OFF"})]..." -ForegroundColor Cyan

$ManifestPath = Join-Path $GlobalPath "integrity.manifest"
$Manifest = Get-IntegrityManifest $ManifestPath
$ForceScan = $Force -or $GenerateManifest -or (Test-CoreRules $GlobalPath $Manifest)

$VocabularyPath = Join-Path $GlobalPath "rules\vocabulary.md"
$DefinedCodes = @{}
if (Test-Path $VocabularyPath) {
    $VocabContent = Get-Content $VocabularyPath -Raw -Encoding UTF8
    $Matches_Codes = [regex]::Matches($VocabContent, "\[([A-Z]{3,4}-\d{2})\]")
    foreach ($m in $Matches_Codes) {
        $DefinedCodes[$m.Groups[1].Value] = $true
    }
}

$ctx = @{
    Fix = $Fix; Interactive = $Interactive; DryRun = $DryRun
    ScannedCount = 0; SkippedCount = 0; ErrorCount = 0; WarningCount = 0; FixedCount = 0
    GlobalHeaders = @{}
    DefinedCodes = $DefinedCodes
}

$FileData = Run-Pass1 $RuleFiles $GlobalPath $Manifest $ForceScan $ctx
$NewManifest = $Manifest.Clone()
Run-Pass2 $FileData $NewManifest $ctx

$null = Test-VersionConsistency $GlobalPath $ctx

if (-not $DryRun -and ($ctx.ErrorCount -eq 0 -or $Fix)) {
    Update-IntegrityManifest $ManifestPath $NewManifest
}

Write-Host "`nSummary: Scanned=$($ctx.ScannedCount), Skipped=$($ctx.SkippedCount), Errors=$($ctx.ErrorCount), Warnings=$($ctx.WarningCount), Healed=$($ctx.FixedCount)"
exit [int]($ctx.ErrorCount -gt 0)
