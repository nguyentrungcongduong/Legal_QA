# =============================================================
#   Legal QA - Smart One-Click Startup
#   Chay: .\start.ps1
#   Stop: .\stop.ps1
# =============================================================
param(
    [switch]$SkipDocker,   # Bo qua kiem tra Docker infra
    [switch]$NoOpen        # Khong tu mo browser
)

$ROOT = $PSScriptRoot
$env:PYTHONUTF8 = '1'

# â”€â”€â”€ Colors helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function Info  ($msg) { Write-Host "  $msg" -ForegroundColor Cyan }
function Ok    ($msg) { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Warn  ($msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Err   ($msg) { Write-Host "  [XX] $msg" -ForegroundColor Red }
function Step  ($n, $msg) { Write-Host "`n  [$n] $msg" -ForegroundColor Magenta }

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "         Legal QA  -  Smart Startup v2.0           " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# â”€â”€â”€ STEP 0: Kill processes cu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "0/5" "Don sach process cu..."

# Kill Python (FastAPI)
$killed = @()
Get-Process python, uvicorn -ErrorAction SilentlyContinue | ForEach-Object {
    $killed += $_.Id; Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
if ($killed.Count -gt 0) { Warn "Da kill $($killed.Count) Python/uvicorn process" }

# Kill port 8000, 8081 neu bi chiem (bo qua port 5173 - Vue co the dang dev)
foreach ($port in @(8000, 8081)) {
    $pids = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $pids) {
        if ($p -and $p -ne $PID) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            Warn "Kill PID $p dang chiem port $port"
        }
    }
}

# Stop Docker containers cu (neu co)
docker stop legal-backend legal-orchestration legal-frontend-dev 2>$null | Out-Null

# Dung cac container khong phai rag-* (tranh ngon RAM/CPU)
$nonRagContainers = docker ps --format '{{.Names}}' 2>$null | Where-Object { $_ -and $_ -notmatch '^rag-' }
foreach ($cname in $nonRagContainers) {
    Warn "Dang dung container khong phai Legal QA: $cname"
    docker stop $cname 2>$null | Out-Null
}

Start-Sleep -Seconds 3  # cho OS release ports
Ok "Ports da duoc giai phong"

# â”€â”€â”€ STEP 1: Docker Infra (Postgres + Qdrant) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "1/5" "Kiem tra Docker infra (Postgres :5432, Qdrant :6333)..."

if (-not $SkipDocker) {
    # Kiem tra Docker daemon
    $dockerOk = (docker ps 2>$null) -ne $null
    if (-not $dockerOk) {
        Err "Docker Desktop chua chay! Hay mo Docker Desktop truoc."
        Err "Hoac chay: .\start.ps1 -SkipDocker (neu Postgres/Qdrant da chay)"
        exit 1
    }

    # Start infra containers
    docker compose -f "$ROOT\docker-compose.infra.yml" up -d 2>$null
    if ($LASTEXITCODE -ne 0) {
        # Thu voi docker-compose.yml nhung chi start postgres va qdrant
        docker compose -f "$ROOT\docker-compose.yml" up -d postgres qdrant 2>$null
    }

    # Doi Postgres san sang
    $pgReady = $false
    for ($i = 1; $i -le 20; $i++) {
        Start-Sleep 2
        $pg = docker exec rag-postgres pg_isready -U raguser -d ragdb 2>$null
        if ($pg -match "accepting connections") {
            Ok "Postgres :5432 san sang"
            $pgReady = $true; break
        }
        if ($i % 3 -eq 0) { Info "Doi Postgres... (${i}*2=${i*2}s)" }
    }
    if (-not $pgReady) { Warn "Postgres chua san sang sau 40s - tiep tuc anyway" }

    # Qdrant check
    try {
        $qr = Invoke-RestMethod "http://localhost:6333/healthz" -TimeoutSec 3 -ErrorAction SilentlyContinue
        Ok "Qdrant :6333 san sang"
    } catch {
        Warn "Qdrant chua san sang - tiep tuc anyway"
    }
} else {
    Warn "Bo qua Docker (flag -SkipDocker)"
}

# â”€â”€â”€ STEP 2: FastAPI :8000 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "2/5" "Khoi dong FastAPI :8000 (model BAAI/bge-m3 can ~3-4 phut)..."

# Mo terminal FastAPI
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'Legal QA - FastAPI :8000'
    `$host.UI.RawUI.ForegroundColor = 'Cyan'
    Write-Host '============================================' -ForegroundColor Cyan
    Write-Host '   FastAPI :8000  -  Dang load BAAI model  ' -ForegroundColor Cyan
    Write-Host '============================================' -ForegroundColor Cyan
    Set-Location '$ROOT\backend-python'
    `$env:PYTHONUTF8 = '1'
    `$env:HF_HUB_OFFLINE = '1'
    `$env:TRANSFORMERS_OFFLINE = '1'
    `$env:POSTGRES_URL = 'postgresql://raguser:ragpass@localhost:5432/ragdb?sslmode=disable'
    .\.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8000
    Write-Host 'FastAPI da dung. Nhan Enter de dong.' -ForegroundColor Red
    Read-Host
"@ -WindowStyle Normal

Info "FastAPI terminal da mo - dang doi san sang..."

# Health check that su (HTTP, khong phai chi TCP)
$faReady = $false
$faStart = Get-Date
for ($i = 1; $i -le 60; $i++) {   # max 10 phut
    Start-Sleep 10
    $elapsed = [math]::Round(((Get-Date) - $faStart).TotalSeconds)
    try {
        $h = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
        if ($h.status -eq "ok") {
            Ok "FastAPI :8000 READY sau ${elapsed}s  (RAM: ~1.4GB loaded)"
            $faReady = $true; break
        }
    } catch {
        # Chua san sang - check process con song khong
        $proc = Get-Process python, uvicorn -ErrorAction SilentlyContinue
        if (-not $proc) {
            Err "FastAPI process da chet! Kiem tra terminal FastAPI de xem loi."
            break
        }
        $maxRam = ($proc | Measure-Object WorkingSet -Maximum).Maximum
        $ramMB  = [math]::Round($maxRam / 1MB, 0)
        if ($i % 2 -eq 0) { Info "${elapsed}s: Dang load model... (RAM: ${ramMB}MB / ~1400MB)" }
    }
}

if (-not $faReady) {
    Err "FastAPI chua san sang sau 10 phut!"
    Err "Kiem tra terminal FastAPI de xem loi."
    Warn "Tiep tuc khoi dong Spring Boot va Vue nhung chat se bi loi."
}

# â”€â”€â”€ STEP 3: Spring Boot :8081 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "3/5" "Khoi dong Spring Boot :8081..."

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'Legal QA - Spring Boot :8081'
    Write-Host '============================================' -ForegroundColor Green
    Write-Host '   Spring Boot :8081                        ' -ForegroundColor Green
    Write-Host '============================================' -ForegroundColor Green
    Set-Location '$ROOT\spring-boot\orchestration-service'
    `$env:MAVEN_OPTS = '-Xmx512m -Xms128m'
    
    # Docs `.env` ?ể tiêm APP_JWT_SECRET cho Spring Boot (giống Python)
    `$envFile = '$ROOT\.env'
    if (Test-Path `$envFile) {
        Get-Content `$envFile | Where-Object { `$_ -match '^APP_JWT_SECRET=(.+)$' } | ForEach-Object {
            `$jwtSecret = `$matches[1].Trim()
            `$env:APP_JWT_SECRET = `$jwtSecret
        }
    }

    mvn spring-boot:run -q
    Write-Host 'Spring Boot da dung. Nhan Enter de dong.' -ForegroundColor Red
    Read-Host
"@ -WindowStyle Normal

# Spring Boot health check - dung login endpoint (reliable hon actuator)
$sbReady = $false
for ($i = 1; $i -le 18; $i++) {   # max 3 phut
    Start-Sleep 10
    $elapsed = [math]::Round($i * 10)
    try {
        $r = Invoke-WebRequest "http://localhost:8081/api/auth/login" -Method POST `
            -Body '{"email":"x","password":"x"}' -ContentType "application/json" `
            -TimeoutSec 5 -ErrorAction Stop -UseBasicParsing
        Ok "Spring Boot :8081 READY sau ${elapsed}s"
        $sbReady = $true; break
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        if ($status -ge 400 -and $status -lt 600) {
            Ok "Spring Boot :8081 READY sau ${elapsed}s (HTTP $status)"
            $sbReady = $true; break
        }
        if ($i % 2 -eq 0) { Info "${elapsed}s: Doi Spring Boot..." }
    }
}

if (-not $sbReady) {
    Err "Spring Boot chua san sang sau 3 phut!"
    Err "Kiem tra terminal Spring Boot."
}

# â”€â”€â”€ STEP 4: Vue :5173 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "4/5" "Khoi dong Vue :5173..."

# Check neu Vue da chay roi (dev session con do)
$vueAlready = $false
try {
    $vr = Invoke-RestMethod "http://localhost:5173" -TimeoutSec 3 -ErrorAction Stop
    Ok "Vue :5173 da chay san (session cu)"
    $vueAlready = $true
} catch {}

if (-not $vueAlready) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        `$host.UI.RawUI.WindowTitle = 'Legal QA - Vue :5173'
        Write-Host '============================================' -ForegroundColor Yellow
        Write-Host '   Vue Dev Server :5173                     ' -ForegroundColor Yellow
        Write-Host '============================================' -ForegroundColor Yellow
        Set-Location '$ROOT\frontend-vue'
        `$esbuild = Join-Path (Get-Location) 'node_modules\@esbuild\win32-x64\esbuild.exe'
        if (Test-Path `$esbuild) { Unblock-File -LiteralPath `$esbuild -ErrorAction SilentlyContinue }
        node scripts/prepare-esbuild.cjs 2>`$null
        npm run dev
        Write-Host 'Vue da dung. Nhan Enter de dong.' -ForegroundColor Red
        Read-Host
"@ -WindowStyle Normal

    $vueReady = $false
    for ($i = 1; $i -le 12; $i++) {
        Start-Sleep 5
        try {
            Invoke-WebRequest "http://localhost:5173" -TimeoutSec 3 -ErrorAction Stop | Out-Null
            Ok "Vue :5173 READY sau $($i*5)s"
            $vueReady = $true; break
        } catch {}
        if ($i % 2 -eq 0) { Info "$($i*5)s: Doi Vue..." }
    }
    if (-not $vueReady) { Warn "Vue chua respond nhung terminal da mo - kiem tra terminal Vue" }
}

# â”€â”€â”€ STEP 5: Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Step "5/5" "Ket qua khoi dong..."
Write-Host ""

$allOk = $faReady -and $sbReady

if ($allOk) {
    Write-Host "  ================================================" -ForegroundColor Green
    Write-Host "          ALL SERVICES READY!                      " -ForegroundColor Green
    Write-Host "  ================================================" -ForegroundColor Green
    Write-Host "    Browser:   http://localhost:5173" -ForegroundColor Green
    Write-Host "    FastAPI:   http://localhost:8000/docs" -ForegroundColor Green
    Write-Host "    Spring:    http://localhost:8081" -ForegroundColor Green
    Write-Host "    Postgres:  localhost:5432 (ragdb)" -ForegroundColor Green
    Write-Host "    Qdrant:    http://localhost:6333/dashboard" -ForegroundColor Green
    Write-Host "  ================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  De dung: .\stop.ps1" -ForegroundColor Gray
    Write-Host ""
    if (-not $NoOpen) { Start-Process "http://localhost:5173" }
} else {
    Write-Host "  ================================================" -ForegroundColor Red
    Write-Host "  MOT SO SERVICE CHUA SAN SANG!" -ForegroundColor Red
    Write-Host "  ================================================" -ForegroundColor Red
    if (-not $faReady) { Err "FastAPI :8000 - kiem tra terminal Cyan" }
    if (-not $sbReady) { Err "Spring Boot :8081 - kiem tra terminal Green" }
    Write-Host ""
    Write-Host "  Thu chay lai: .\start.ps1" -ForegroundColor Yellow
}
