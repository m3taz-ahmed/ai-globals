$basePath = "D:\server\.ai"
$folders = @("rules", "tech-stack", "workflows", "skills")
$uncompiled = @()

foreach ($folder in $folders) {
    $srcPath = Join-Path $basePath $folder
    $destPath = Join-Path $basePath "min\$folder"
    
    if (-Not (Test-Path $srcPath)) { continue }
    
    $files = Get-ChildItem -Path $srcPath -Filter "*.md"
    foreach ($file in $files) {
        $minFileName = $file.BaseName + ".min"
        $destFile = Join-Path $destPath $minFileName
        
        if (-Not (Test-Path $destFile)) {
            $uncompiled += "$folder\$($file.Name)"
        } else {
            $minItem = Get-Item $destFile
            if ($file.LastWriteTime -gt $minItem.LastWriteTime) {
                $uncompiled += "$folder\$($file.Name)"
            }
        }
    }
}

if ($uncompiled.Count -gt 0) {
    Write-Output $uncompiled
}
