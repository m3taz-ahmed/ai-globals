$readmeUrl = "https://raw.githubusercontent.com/alistaitsacle/free-llm-api-keys/main/README.md"
Write-Host "Fetching active free keys from GitHub..." -ForegroundColor Cyan

$userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

try {
    $readme = Invoke-RestMethod -Uri $readmeUrl -UseBasicParsing -UserAgent $userAgent
} catch {
    Write-Error "Failed to fetch keys from repository. Check your internet connection."
    exit 1
}

# Find all sk- keys
$keys = [regex]::Matches($readme, 'sk-[A-Za-z0-9]+') | Select-Object -ExpandProperty Value -Unique

if ($keys.Count -eq 0) {
    Write-Error "No keys found in README."
    exit 1
}

Write-Host "Found $($keys.Count) unique keys. Validating active status via completion tests..." -ForegroundColor Cyan

$geminiProKey = $null
$geminiFlashKey = $null
$kimiKey = $null
$deepseekKey = $null
$codestralKey = $null

foreach ($key in $keys) {
    if ($geminiProKey -and $geminiFlashKey -and $kimiKey -and $deepseekKey -and $codestralKey) {
        break
    }
    
    $headers = @{
        "Authorization" = "Bearer $key"
        "Content-Type" = "application/json"
    }
    
    try {
        # Step 1: Query models to see what model ID this key is restricted to
        $response = Invoke-RestMethod -Uri "https://aiapiv2.pekpik.com/v1/models" -Headers $headers -Method Get -TimeoutSec 3 -UserAgent $userAgent
        
        if ($response.data) {
            $allowedModels = @($response.data | Select-Object -ExpandProperty id)
            $targetModel = $allowedModels[0]

            
            $isTargetNeeded = $false
            if (($allowedModels -contains "gemini-2.5-pro") -and -not $geminiProKey) { $isTargetNeeded = $true }
            elseif (($allowedModels -contains "gemini-2.5-flash") -and -not $geminiFlashKey) { $isTargetNeeded = $true }
            elseif (($allowedModels -contains "kimi-k2.5") -and -not $kimiKey) { $isTargetNeeded = $true }
            elseif (($allowedModels -contains "deepseek-chat" -or $allowedModels -contains "deepseek-reasoner") -and -not $deepseekKey) { $isTargetNeeded = $true }
            elseif (($allowedModels -contains "codestral") -and -not $codestralKey) { $isTargetNeeded = $true }
            
            if ($isTargetNeeded) {
                # Step 2: Validate that the key actually has quota and is not rate-limited (429)
                Write-Host "Testing key: $key ($targetModel)... " -NoNewline
                
                $body = @{
                    model = $targetModel
                    messages = @(
                        @{ role = "user"; content = "a" }
                    )
                    max_tokens = 1
                } | ConvertTo-Json
                
                $chatResponse = Invoke-RestMethod -Uri "https://aiapiv2.pekpik.com/v1/chat/completions" -Headers $headers -Method Post -Body $body -ContentType "application/json" -TimeoutSec 5 -UserAgent $userAgent
                
                if ($chatResponse.choices -or $chatResponse.id) {
                    if ($allowedModels -contains "gemini-2.5-pro") { $geminiProKey = $key }
                    elseif ($allowedModels -contains "gemini-2.5-flash") { $geminiFlashKey = $key }
                    elseif ($allowedModels -contains "kimi-k2.5") { $kimiKey = $key }
                    elseif ($allowedModels -contains "deepseek-chat" -or $allowedModels -contains "deepseek-reasoner") { $deepseekKey = $key }
                    elseif ($allowedModels -contains "codestral") { $codestralKey = $key }
                    Write-Host " [SUCCESS - MAPPED]" -ForegroundColor Green
                } else {
                    Write-Host " [FAILED]" -ForegroundColor Red
                }
            }
        }
    } catch {
        # Catch 429/401/500 errors and print the message
        Write-Host " [FAILED: $($_.Exception.Message)]" -ForegroundColor Red
    }
}

if ($geminiProKey) { $env:FREE_GEMINI_PRO_KEY = $geminiProKey }
if ($geminiFlashKey) { $env:FREE_GEMINI_FLASH_KEY = $geminiFlashKey }
if ($kimiKey) { $env:FREE_KIMI_KEY = $kimiKey }
if ($deepseekKey) { $env:FREE_DEEPSEEK_KEY = $deepseekKey }
if ($codestralKey) { $env:FREE_CODESTRAL_KEY = $codestralKey }

Write-Host "`nEnvironment variables status:" -ForegroundColor Cyan
Write-Host "  FREE_GEMINI_PRO_KEY   : $(if ($geminiProKey) { 'MAPPED' } else { 'MISSING' })" -ForegroundColor $(if ($geminiProKey) { 'Green' } else { 'Yellow' })
Write-Host "  FREE_GEMINI_FLASH_KEY : $(if ($geminiFlashKey) { 'MAPPED' } else { 'MISSING' })" -ForegroundColor $(if ($geminiFlashKey) { 'Green' } else { 'Yellow' })
Write-Host "  FREE_KIMI_KEY         : $(if ($kimiKey) { 'MAPPED' } else { 'MISSING' })" -ForegroundColor $(if ($kimiKey) { 'Green' } else { 'Yellow' })
Write-Host "  FREE_DEEPSEEK_KEY     : $(if ($deepseekKey) { 'MAPPED' } else { 'MISSING' })" -ForegroundColor $(if ($deepseekKey) { 'Green' } else { 'Yellow' })
Write-Host "  FREE_CODESTRAL_KEY    : $(if ($codestralKey) { 'MAPPED' } else { 'MISSING' })" -ForegroundColor $(if ($codestralKey) { 'Green' } else { 'Yellow' })

# Detect and Launch OpenCode Desktop App
$desktopPaths = @(
    "C:\Users\Moataz\AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe",
    "C:\Users\Moataz\scoop\shims\opencode-desktop.exe",
    "$env:LOCALAPPDATA\Programs\@opencode-aidesktop\OpenCode.exe"
)

$desktopExe = $null
foreach ($path in $desktopPaths) {
    if (Test-Path $path) {
        $desktopExe = $path
        break
    }
}

if ($desktopExe) {
    Write-Host "`nLaunching OpenCode Desktop..." -ForegroundColor Green
    Start-Process -FilePath $desktopExe
} else {
    $opencodeCommand = Get-Command opencode -ErrorAction SilentlyContinue
    if ($opencodeCommand) {
        Write-Host "`nOpenCode Desktop not found. Launching OpenCode CLI..." -ForegroundColor Green
        opencode
    } else {
        Write-Host "`nEnvironment variables set successfully!" -ForegroundColor Green
        Write-Host "Warning: OpenCode Desktop or CLI command was not found." -ForegroundColor Yellow
    }
}
