param (
    [Parameter(Mandatory=$true)]
    [string]$SkillName,
    
    [string]$TargetName
)

$basePath = "D:\server\.ai"
$tmpPath = Join-Path $basePath "tmp\skill-ingest"
$techStackPath = Join-Path $basePath "tech-stack"

if (Test-Path $tmpPath) { Remove-Item -Recurse -Force $tmpPath }
New-Item -ItemType Directory -Path $tmpPath | Out-Null

Write-Host "Fetching skill: $SkillName from skills.sh..."
Push-Location $tmpPath

try {
    # Using npx --yes to avoid interactive prompts.
    # It fetches the skill from skills.sh
    npx --yes skills add $SkillName
} catch {
    Write-Warning "Failed to fetch skill $SkillName. Error: $_"
    Pop-Location
    Remove-Item -Recurse -Force $tmpPath
    exit 1
}

Pop-Location

# The skills CLI puts downloaded skills in .agents\skills\
$skillsDir = Join-Path $tmpPath ".agents\skills"

$ingestedCount = 0

if (Test-Path $skillsDir) {
    # If TargetName is provided, only ingest that specific folder
    $foldersToProcess = if ($TargetName) {
        $targetFolder = Join-Path $skillsDir $TargetName
        if (Test-Path $targetFolder) { Get-Item $targetFolder } else { @() }
    } else {
        Get-ChildItem -Path $skillsDir -Directory
    }

    foreach ($folder in $foldersToProcess) {
        $skillMdPath = Join-Path $folder.FullName "SKILL.md"
        if (Test-Path $skillMdPath) {
            $destName = "$($folder.Name).md"
            $destPath = Join-Path $techStackPath $destName
            Copy-Item $skillMdPath -Destination $destPath -Force
            Write-Host "Ingested community skill into: $destPath"
            $ingestedCount++
        }
    }
} else {
    # Fallback to look for .md or .mdc
    $files = Get-ChildItem -Path $tmpPath -Recurse -Include *.md, *.mdc
    foreach ($file in $files) {
        if ($file.FullName -match "\\\.agents\\") { continue }
        $destName = $file.Name -replace '\.mdc$', '.md'
        $destPath = Join-Path $techStackPath $destName
        Copy-Item $file.FullName -Destination $destPath -Force
        Write-Host "Ingested community skill into: $destPath"
        $ingestedCount++
    }
}

if ($ingestedCount -eq 0) {
    Write-Warning "No markdown rules (.md, .mdc) found in the skill payload."
}

Remove-Item -Recurse -Force $tmpPath
Write-Host "Ingestion complete. Run get-uncompiled.ps1 to minify."
