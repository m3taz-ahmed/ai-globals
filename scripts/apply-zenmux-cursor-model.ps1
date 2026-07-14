#Requires -Version 5.1
<#
.SYNOPSIS
  Configure ZenMux Claude Fable 5 in Cursor and hide the built-in Fable picker entry to avoid alias merge.
.NOTES
  Close Cursor completely before running. Restart Cursor after success.
#>
$ErrorActionPreference = 'Stop'

$DbPath = Join-Path $env:APPDATA 'Cursor\User\globalStorage\state.vscdb'
$CustomModel = 'anthropic/claude-fable-5'
$BaseUrl = 'https://zenmux.ai/api/v1'
$StorageKey = 'src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser'

$running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match '^(Cursor|cursor|Glass)$'
}
if ($running) {
    Write-Host 'Cursor is still running. Close it completely, then rerun this script.' -ForegroundColor Red
    $running | Select-Object ProcessName, Id | Format-Table
    exit 1
}

if (-not (Test-Path $DbPath)) {
    Write-Error "Cursor state DB not found: $DbPath"
}

$backup = "$DbPath.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Copy-Item $DbPath $backup
Write-Host "Backup: $backup" -ForegroundColor Cyan

$py = @"
import json, sqlite3, sys
from pathlib import Path

db = Path(r'$DbPath')
custom = '$CustomModel'
key = '$StorageKey'
fable_slugs = [
    'claude-fable-5',
    'claude-fable-5-low', 'claude-fable-5-medium', 'claude-fable-5-high',
    'claude-fable-5-xhigh', 'claude-fable-5-max',
    'claude-fable-5-thinking-low', 'claude-fable-5-thinking-medium',
    'claude-fable-5-thinking-high', 'claude-fable-5-thinking-xhigh',
    'claude-fable-5-thinking-max',
]

conn = sqlite3.connect(db)
cur = conn.cursor()
cur.execute('SELECT value FROM ItemTable WHERE key = ?', (key,))
row = cur.fetchone()
if not row:
    raise SystemExit('applicationUser row missing')

data = json.loads(row[0])
data['openAIBaseUrl'] = '$BaseUrl'
data['useOpenAIKey'] = True

ai = data.setdefault('aiSettings', {})
ai['userAddedModels'] = [custom]

enabled = list(ai.get('modelOverrideEnabled') or [])
if custom not in enabled:
    enabled.append(custom)
ai['modelOverrideEnabled'] = enabled

disabled = list(ai.get('modelOverrideDisabled') or [])
for slug in fable_slugs:
    if slug not in disabled:
        disabled.append(slug)
if custom in disabled:
    disabled.remove(custom)
ai['modelOverrideDisabled'] = disabled

data['availableAPIKeyModels'] = [{'name': custom, 'defaultOn': True}]

cur.execute('UPDATE ItemTable SET value = ? WHERE key = ?', (json.dumps(data, separators=(',', ':')), key))
conn.commit()
conn.close()
print('OK')
"@

python -c $py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ''
Write-Host 'Done.' -ForegroundColor Green
Write-Host '1. Open Cursor'
Write-Host '2. Settings -> Models -> verify Override Base URL = https://zenmux.ai/api/v1'
Write-Host '3. Pick model: anthropic/claude-fable-5'
Write-Host ''
Write-Host 'Built-in Fable 5 High is hidden to prevent merge with ZenMux.' -ForegroundColor Yellow
Write-Host 'Re-enable it from Settings -> Models if you need Cursor native Fable.' -ForegroundColor Yellow
Write-Host ''
Write-Host 'ZenMux account must have positive balance (402 = no credit).' -ForegroundColor Yellow
Write-Host 'Wrong URL ap/v1 causes Cloudflare 403 shown as missing csrf token.' -ForegroundColor Yellow
Write-Host 'Claude models in Agent mode may fail with unsupported tool definition; try Ask mode.' -ForegroundColor Yellow
