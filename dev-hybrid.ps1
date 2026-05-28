# dev-hybrid.ps1
# =============================================================================
# HYBRID DEV MODE - Qdrant + Postgres trong Docker, Python + Java chay native
# =============================================================================
# Dung: .\dev-hybrid.ps1 [start|stop|ingest|status|help]
# =============================================================================

param(
    [ValidateSet("start","stop","ingest","status","help")]
    [string]$Action = "status"
)

$ROOT    = $PSScriptRoot
$BACKEND = Join-Path $ROOT "backend-python"
$SPRING  = Join-Path $ROOT "spring-boot\orchestration-service"
$VENV    = Join-Path $BACKEND ".venv\Scripts\python.exe"

function Write-Step { param($msg) Write-Host "`n>> $msg" -ForegroundColor Cyan }
function Write-OK   { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-Err  { param($msg) Write-Host "  [XX] $msg" -ForegroundColor Red }

# =============================================================================
function Show-Status {
    Write-Step "Docker Infrastructure:"
    docker compose -f "$ROOT\docker-compose.infra.yml" ps 2>$null

    Write-Step "Native Services:"

    $fastapi = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    $spring  = Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue
    $vue     = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue

    if ($fastapi) { Write-OK  "FastAPI  -> http://localhost:8000  RUNNING" }
    else          { Write-Warn "FastAPI  -> http://localhost:8000  NOT RUNNING" }

    if ($spring)  { Write-OK  "Spring   -> http://localhost:8081  RUNNING" }
    else          { Write-Warn "Spring   -> http://localhost:8081  NOT RUNNING" }

    if ($vue)     { Write-OK  "Vue      -> http://localhost:5173  RUNNING" }
    else          { Write-Warn "Vue      -> http://localhost:5173  NOT RUNNING" }
}

# =============================================================================
function Start-Infra {
    Write-Step "Khoi dong Qdrant + Postgres trong Docker..."
    docker compose -f "$ROOT\docker-compose.infra.yml" up -d
    Write-OK "Qdrant: http://localhost:6333"
    Write-OK "Postgres: localhost:5432"

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host "  Mo 3 terminal rieng de chay native:" -ForegroundColor White
    Write-Host ""
    Write-Host "  [TERMINAL 1] FastAPI:" -ForegroundColor Yellow
    Write-Host "    cd backend-python" -ForegroundColor Gray
    Write-Host "    `$env:PYTHONUTF8='1'; .venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [TERMINAL 2] Spring Boot:" -ForegroundColor Yellow
    Write-Host "    cd spring-boot\orchestration-service" -ForegroundColor Gray
    Write-Host "    `$envFile='..\..\.env'; if(Test-Path `$envFile){ Get-Content `$envFile | Where-Object { `$_ -match '^APP_JWT_SECRET=(.+)$' } | ForEach-Object { `$env:APP_JWT_SECRET=`$matches[1].Trim() } }; mvn spring-boot:run" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [TERMINAL 3] Vue:" -ForegroundColor Yellow
    Write-Host "    cd frontend-vue" -ForegroundColor Gray
    Write-Host "    npm run dev" -ForegroundColor Gray
    Write-Host "============================================================" -ForegroundColor DarkGray
}

# =============================================================================
function Stop-Infra {
    Write-Step "Dung Docker infrastructure..."
    docker compose -f "$ROOT\docker-compose.infra.yml" down
    Write-OK "Qdrant va Postgres da dung"
    Write-Warn "Tat cac terminal FastAPI / Spring Boot / Vue bang Ctrl+C"
}

# =============================================================================
function Run-Ingest {
    Write-Step "Kiem tra Qdrant..."
    try {
        $null = Invoke-WebRequest "http://localhost:6333/healthz" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-OK "Qdrant san sang"
    } catch {
        Write-Err "Qdrant chua chay! Chay: .\dev-hybrid.ps1 start truoc"
        exit 1
    }

    if (!(Test-Path $VENV)) {
        Write-Err "Khong tim thay .venv tai $VENV"
        exit 1
    }

    Write-Step "Wipe du lieu cu..."
    & $VENV "$BACKEND\wipe_rag.py"

    Write-Step "Ingest du lieu moi (BAAI/bge-m3, dim=1024)..."
    & $VENV "$BACKEND\ingestion\batch_ingest.py"

    Write-OK "Ingest hoan tat!"
}

# =============================================================================
function Show-Help {
    Write-Host @"

HYBRID DEV MODE
--------------------------------------------------------------
  .\dev-hybrid.ps1 start    Khoi dong Qdrant+Postgres (Docker)
  .\dev-hybrid.ps1 stop     Dung Docker infrastructure
  .\dev-hybrid.ps1 ingest   Wipe + ingest lai toan bo data
  .\dev-hybrid.ps1 status   Kiem tra trang thai tat ca services
  .\dev-hybrid.ps1 help     Hien thi help nay

Loi ich: Python va Java dung RAM may that, khong bi Docker gioi han
"@
}

# =============================================================================
switch ($Action) {
    "start"  { Start-Infra }
    "stop"   { Stop-Infra }
    "ingest" { Run-Ingest }
    "status" { Show-Status }
    "help"   { Show-Help }
    default  { Show-Status }
}
