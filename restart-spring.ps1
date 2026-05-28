# restart-spring.ps1
# ============================================================
# Rebuild và restart Spring Boot :8081
# Chay: .\restart-spring.ps1
# ============================================================

$ROOT   = $PSScriptRoot
$SPRING = Join-Path $ROOT "spring-boot\orchestration-service"
$LOG    = Join-Path $ROOT "spring_stdout.log"
$ERRLOG = Join-Path $ROOT "spring_stderr.log"

function Write-OK   { param($m) Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn { param($m) Write-Host "  [!!] $m" -ForegroundColor Yellow }
function Write-Err  { param($m) Write-Host "  [XX] $m" -ForegroundColor Red }
function Write-Info { param($m) Write-Host "  --> $m" -ForegroundColor Cyan }

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "   Legal QA - Spring Boot Quick Restart           " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan

# Kill Spring Boot cu
$killed = @()
Get-Process java -ErrorAction SilentlyContinue | Where-Object {
    (Get-Process -Id $_.Id -ErrorAction SilentlyContinue).Modules | Select-Object -ExpandProperty FileName -ErrorAction SilentlyContinue | Select-String "orchestration" -Quiet
} | ForEach-Object {
    $killed += $_.Id
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

# Fallback: kill tat ca java process dang listen :8081
$port8081Pid = (netstat -ano | Select-String ":8081.*LISTENING") -replace ".*\s(\d+)$", '$1'
if ($port8081Pid) {
    $port8081Pid | ForEach-Object {
        Stop-Process -Id ([int]$_) -Force -ErrorAction SilentlyContinue
    }
    Write-Warn "Da kill Spring Boot (PID: $($port8081Pid -join ', '))"
    Start-Sleep 2
}

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LOG    -Value "`n`n========== SPRING RESTART at $ts =========="
Add-Content -Path $ERRLOG -Value "`n`n========== SPRING RESTART at $ts =========="

Write-Info "Building Spring Boot (Maven)..."
Write-Info "Log xem tai: $LOG"

# --- Load JWT secret tu .env ---
$envFile = Join-Path $ROOT ".env"
$jwtSecret = "legal-rag-super-secret-key-2024-must-be-32-chars"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^APP_JWT_SECRET=(.+)$") { $jwtSecret = $matches[1].Trim() }
        elseif ($_ -match "^JWT_SECRET=(.+)$" -and $jwtSecret -eq "legal-rag-super-secret-key-2024-must-be-32-chars") {
            $jwtSecret = $matches[1].Trim()
        }
    }
}
Write-Info "JWT secret loaded (first 8 chars): $($jwtSecret.Substring(0, [Math]::Min(8,$jwtSecret.Length)))..."

# Open terminal moi chay Spring Boot
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
    `$host.UI.RawUI.WindowTitle = 'Legal QA - Spring Boot :8081'
    `$host.UI.RawUI.ForegroundColor = 'Yellow'
    Write-Host '============================================' -ForegroundColor Yellow
    Write-Host '   Spring Boot :8081  -  RESTART            ' -ForegroundColor Yellow
    Write-Host '============================================' -ForegroundColor Yellow
    Set-Location '$SPRING'
    Write-Host 'Building...' -ForegroundColor Cyan
    `$env:APP_JWT_SECRET = '$jwtSecret'
    mvn spring-boot:run 2>&1 | Tee-Object -FilePath '$LOG' -Append
    Write-Host ''
    Write-Host '!!! Spring Boot da dung !!!' -ForegroundColor Red
    Write-Host 'Nhan Enter de dong terminal' -ForegroundColor Yellow
    Read-Host
"@ -WindowStyle Normal

# Wait for Spring Boot ready
Write-Info "Dang cho Spring Boot san sang..."
$ready = $false
$start = Get-Date
for ($i = 1; $i -le 24; $i++) {
    Start-Sleep 5
    $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds)
    try {
        $null = Invoke-RestMethod "http://localhost:8081/api/auth/login" -Method POST `
            -ContentType "application/json" -Body '{"email":"_","password":"_"}' `
            -TimeoutSec 3 -ErrorAction Stop
        Write-OK "Spring Boot :8081 READY sau ${elapsed}s"
        $ready = $true; break
    } catch {
        $status = 0
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
        # 401 hoac 500 → server da up (chi chua login thanh cong)
        if ($status -ge 400) {
            Write-OK "Spring Boot :8081 READY sau ${elapsed}s (HTTP $status)"
            $ready = $true; break
        }
        if ($i % 3 -eq 0) { Write-Info "${elapsed}s: Dang khoi dong..." }
    }
}

if ($ready) {
    Write-Host ""
    Write-Host "  Spring Boot:  http://localhost:8081" -ForegroundColor Green
    Write-Host "  Auth:         http://localhost:8081/api/auth/login" -ForegroundColor Green
} else {
    Write-Err "Spring Boot chua ready sau timeout. Kiem tra terminal Yellow."
}
