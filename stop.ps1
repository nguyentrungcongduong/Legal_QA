# =============================================================
#   Legal QA - Stop All Services
#   Chay: .\stop.ps1
# =============================================================
param(
    [switch]$KeepDocker   # Giu lai Postgres + Qdrant Docker containers
)

function Ok  ($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn ($msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "  [Legal QA] Dang dung tat ca services..." -ForegroundColor Cyan

# Kill FastAPI / uvicorn
$py = Get-Process python, uvicorn -ErrorAction SilentlyContinue
if ($py) {
    $py | Stop-Process -Force -ErrorAction SilentlyContinue
    Ok "FastAPI / Python da dung ($($py.Count) processes)"
} else { Warn "Khong tim thay FastAPI process" }

# Kill Spring Boot (java process chay tu thu muc orchestration)
$java = Get-Process java -ErrorAction SilentlyContinue | Where-Object {
    (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine -like "*orchestration*"
}
if ($java) {
    $java | Stop-Process -Force -ErrorAction SilentlyContinue
    Ok "Spring Boot da dung"
} else {
    # Fallback: kill theo port 8081
    $p = Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
    if ($p) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Ok "Spring Boot :8081 da dung (port kill)" }
    else { Warn "Khong tim thay Spring Boot process" }
}

# Kill Vue (node/vite)
$node = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess
if ($node) {
    Stop-Process -Id $node -Force -ErrorAction SilentlyContinue
    Ok "Vue :5173 da dung"
} else { Warn "Khong tim thay Vue process" }

# Docker infra
if (-not $KeepDocker) {
    Write-Host ""
    Write-Host "  Dung Docker infra (Postgres + Qdrant)..." -ForegroundColor Gray
    docker stop rag-postgres rag-qdrant 2>$null | Out-Null
    Ok "Docker containers da dung (data van duoc giu)"
    Write-Host "  (De giu Docker chay: .\stop.ps1 -KeepDocker)" -ForegroundColor DarkGray
} else {
    Warn "Giu Docker infra chay (flag -KeepDocker)"
}

Write-Host ""
Write-Host "  Tat ca services da dung. Chay .\start.ps1 de bat lai." -ForegroundColor Cyan
Write-Host ""
