$basePath = "D:\server\.ai"
$folders = @("rules", "tech-stack", "workflows", "skills")

Write-Host "Starting AI Context Minification..."

foreach ($folder in $folders) {
    $srcPath = Join-Path $basePath $folder
    $destPath = Join-Path $basePath "min\$folder"
    
    if (-Not (Test-Path $srcPath)) { continue }
    
    if (-Not (Test-Path $destPath)) {
        New-Item -ItemType Directory -Force -Path $destPath | Out-Null
    }

    $files = Get-ChildItem -Path $srcPath -Filter "*.md"
    foreach ($file in $files) {
        $content = Get-Content $file.FullName -Raw
        
        # Extreme Minification for LLM Context
        # 1. Remove Markdown syntax
        $content = $content -replace '(?m)^#+\s*', ''
        $content = $content -replace '\*\*(.*?)\*\*', '$1'
        $content = $content -replace '_(.*?)_', '$1'
        $content = $content -replace '(?m)^>\s*', ''
        $content = $content -replace '(?m)^\-\s*', ''
        
        # 2. Convert tables to comma separation
        $content = $content -replace '\|', ','
        $content = $content -replace '(?m)^[\s-]*$', ''
        
        # 3. Strip URLs
        $content = $content -replace '\[(.*?)\]\(.*?\)', '$1'
        
        # 4. Remove empty lines, convert newlines to semicolons
        $content = $content -replace '(?m)^\s*$\n?', ''
        $content = $content -replace '\r?\n', ';'
        
        # 5. Remove stop words to save tokens without losing meaning
        $stopWords = @(" the ", " a ", " an ", " is ", " are ", " was ", " were ", " to ", " of ", " for ", " and ", " in ", " on ", " at ", " by ", " with ", " as ", " this ", " that ", " these ", " those ", " please ", " ensure ")
        foreach ($word in $stopWords) {
            $content = $content -replace "(?i)$word", " "
        }
        
        # 6. Final trim and whitespace squash
        $content = $content -replace '\s{2,}', ' '
        $content = $content.Trim()
        
        $minFileName = $file.BaseName + ".min"
        $destFile = Join-Path $destPath $minFileName
        
        [System.IO.File]::WriteAllText($destFile, $content, [System.Text.UTF8Encoding]::new($false))
        Write-Host "Compiled: $folder\$($file.Name) -> min\$folder\$minFileName"
    }
}

Write-Host "Minification Complete! All AI context generated in D:\server\.ai\min\"
