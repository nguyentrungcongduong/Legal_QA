# restart-fastapi.ps1
# ============================================================
# Restart nhanh FastAPI :8000 khi bị crash
# Chay: .\restart-fastapi.ps1
# ============================================================

$ROOT    = $PSScriptRoot
$BACKEND = Join-Path $ROOT "backend-python"
$LOG     = Join-Path $ROOT "fastapi_stdout.log"
$ERRLOG  = Join-Path $ROOT "fastapi_stderr.log"

# Script tam thoi de tranh loi escape khi dung -Command
$RUNNER  = Join-Path $env:TEMP "legalqa_fastapi_runner.ps1"

function Write-OK   { param($m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [!!] $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "  [XX] $m" -ForegroundColor Red }
function Write-Info { param($m) Write-Host "  --> $m" -ForegroundColor Cyan }

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Legal QA - FastAPI Quick Restart              " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# Kill Python/uvicorn cu neu con
$killed = @()
Get-Process python, uvicorn -ErrorAction SilentlyContinue | ForEach-Object {
    $killed += $_.Id
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
if ($killed.Count -gt 0) {
    Write-Warn "Da kill $($killed.Count) Python/uvicorn process cu"
    Start-Sleep 2
}

# Ghi timestamp vao log truoc khi start
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LOG    -Value "`n`n========== RESTART at $ts =========="
Add-Content -Path $ERRLOG -Value "`n`n========== RESTART at $ts =========="

# Tao script tam thoi (tranh loi escape phuc tap khi dung -Command)
@"
`$host.UI.RawUI.WindowTitle = 'Legal QA - FastAPI :8000'
Write-Host '============================================' -ForegroundColor Cyan
Write-Host '   FastAPI :8000  -  RESTART               ' -ForegroundColor Cyan
Write-Host '============================================' -ForegroundColor Cyan
Set-Location '$BACKEND'
`$env:PYTHONUTF8        = '1'
`$env:HF_HUB_OFFLINE    = '1'
`$env:TRANSFORMERS_OFFLINE = '1'
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 2>&1 | Tee-Object -FilePath '$ERRLOG' -Append
Write-Host ''
Write-Host '!!! FastAPI da dung (crash hoac bi tat) !!!' -ForegroundColor Red
Read-Host 'Nhan Enter de dong terminal'
"@ | Set-Content -Path $RUNNER -Encoding UTF8

Write-Info "Dang khoi dong FastAPI (model BAAI/bge-m3 can ~3-5 phut)..."
Write-Info "Log xem tai: $ERRLOG"

# Mo terminal: uu tien Windows Terminal (wt), fallback sang powershell window
$wtPath = (Get-Command wt -ErrorAction SilentlyContinue)?.Source
if ($wtPath) {
    Start-Process wt -ArgumentList "--title", "FastAPI :8000", "powershell", "-NoExit", "-File", $RUNNER
    Write-Info "Da mo tab Windows Terminal 'FastAPI :8000'"
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-File", $RUNNER -WindowStyle Normal
    Write-Info "Da mo cua so PowerShell 'FastAPI :8000'"
}

# Health check loop
Write-Info "Dang cho FastAPI san sang..."
$ready = $false
$start = Get-Date
for ($i = 1; $i -le 40; $i++) {
    Start-Sleep 10
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds)
    try {
        $h = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($h.status -eq "ok") {
            Write-OK "FastAPI :8000 READY sau ${elapsed}s"
            $ready = $true; break
        }
    } catch {
        $proc = Get-Process python -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-Err "FastAPI process da chet! Xem terminal 'FastAPI :8000' de xem loi."
            break
        }
        $ramMB = [math]::Round(($proc | Measure-Object WorkingSet -Maximum).Maximum / 1MB, 0)
        if ($i % 2 -eq 0) { Write-Info "${elapsed}s: Dang load... RAM=${ramMB}MB" }
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "  FastAPI:  http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "  Health:   http://localhost:8000/health" -ForegroundColor Green
} else {
    Write-Err "FastAPI chua ready sau timeout. Kiem tra terminal 'FastAPI :8000'"
}
