# Opportunity Agent — morning website-outreach autopilot.
# Registered with Windows Task Scheduler to run every day at 9:00 AM.
# It only reads public websites and writes drafts to the local DB — it sends nothing.
$ErrorActionPreference = "Stop"
$root    = $PSScriptRoot
$backend = Join-Path $root "backend"
$logdir  = Join-Path $backend "logs"
if (-not (Test-Path $logdir)) { New-Item -ItemType Directory -Path $logdir | Out-Null }

$stamp = Get-Date -Format "yyyy-MM-dd"
$log   = Join-Path $logdir "morning_$stamp.log"

# Force UTF-8 end-to-end so the log stays clean and greppable.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location $backend
Add-Content -Path $log -Encoding utf8 -Value "=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') morning batch START ==="
& python morning_batch.py 2>&1 | Out-File -FilePath $log -Append -Encoding utf8
Add-Content -Path $log -Encoding utf8 -Value "=== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') morning batch END (exit $LASTEXITCODE) ==="
