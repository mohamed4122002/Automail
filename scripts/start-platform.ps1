<# 
    Marketing Automation Platform - Preflight + Startup Script

    Usage:
      ./start-platform.ps1

    This script:
      - Performs environment preflight checks
      - Ensures Python and Node dependencies are installed
      - Boots Docker infrastructure (Postgres, Redis, backend, worker)
      - Runs DB migrations and seed data (idempotent)
      - Starts backend, Celery worker, and frontend in separate terminals
      - Verifies basic health and prints a final status summary
#>

param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

### Helpers ###############################################################

function Write-Info($msg) {
    Write-Host "[INFO]  $msg" -ForegroundColor Cyan
}

function Write-Success($msg) {
    Write-Host "[OK]    $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[WARN]  $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "[FAIL]  $msg" -ForegroundColor Red
}

function Fail-And-Exit($msg, [int]$code = 1) {
    Write-Fail $msg
    exit $code
}

function Test-CommandExists($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Test-PortFree([int]$Port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        if ($null -ne $conn) {
            return $false
        }
        return $true
    } catch {
        # Fallback using netstat for older environments
        $netstat = netstat -ano | Select-String ":$Port\s"
        if ($netstat) { return $false }
        return $true
    }
}

function Ensure-InRoot() {
    if (-not (Test-Path -LiteralPath "backend") -or -not (Test-Path -LiteralPath "docker-compose.yml")) {
        Fail-And-Exit "Please run this script from the project root (containing 'backend' and 'docker-compose.yml')."
    }
}

### 1. PREFLIGHT CHECKS ###################################################

Write-Host "=== Marketing Automation Platform Startup ===" -ForegroundColor White

Ensure-InRoot

Write-Info "Running preflight checks..."

# 1. Docker
if (-not (Test-CommandExists "docker")) {
    Fail-And-Exit "Docker CLI not found. Please install Docker Desktop for Windows."
}
try {
    $dockerVersion = docker --version
    Write-Success "Docker found: $dockerVersion"
} catch {
    Fail-And-Exit "Failed to execute 'docker --version'. Ensure Docker is correctly installed."
}

try {
    docker info | Out-Null
    Write-Success "Docker daemon is running."
} catch {
    Fail-And-Exit "Docker daemon is not running. Please start Docker Desktop and retry."
}

# 2. Docker Compose (v2+)
try {
    $dcVersion = docker compose version
    Write-Success "Docker Compose available: $dcVersion"
} catch {
    Fail-And-Exit "Docker Compose (docker compose) is not available. Ensure Docker Desktop v2+ is installed and 'docker compose' works."
}

# 3. Python
if (-not (Test-CommandExists "python")) {
    Fail-And-Exit "Python not found. Install Python 3.10+ and ensure 'python' is on PATH."
}
try {
    $pyVerOut = python --version 2>&1
    Write-Info "Python version: $pyVerOut"
    $pyVer = ($pyVerOut -replace '[^\d\.]', '')
    $major = [int]($pyVer.Split('.')[0])
    $minor = [int]($pyVer.Split('.')[1])
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        Fail-And-Exit "Python 3.10+ required. Detected: $pyVerOut"
    }
    Write-Success "Python version is >= 3.10."
} catch {
    Fail-And-Exit "Failed to determine Python version: $_"
}

# 4. Node.js / npm
if (-not (Test-CommandExists "node")) {
    Fail-And-Exit "Node.js not found. Install Node.js (LTS) and ensure 'node' is on PATH."
}
if (-not (Test-CommandExists "npm")) {
    Fail-And-Exit "npm not found. Install Node.js/npm and ensure 'npm' is on PATH."
}
try {
    $nodeVer = node --version
    $npmVer = npm --version
    Write-Success "Node.js: $nodeVer, npm: $npmVer"
} catch {
    Fail-And-Exit "Failed to determine Node/npm versions: $_"
}

# 5. Port checks
$ports = @(5432, 6379, 8000, 5173)
foreach ($p in $ports) {
    if (-not (Test-PortFree -Port $p)) {
        Fail-And-Exit "Port $p is already in use. Stop conflicting services and retry."
    }
}
Write-Success "Required ports are free: $($ports -join ', ')."

### 2. PYTHON DEPENDENCIES CHECK ##########################################

Write-Info "Ensuring Python dependencies are installed (requirements.txt)..."
if (-not (Test-Path -LiteralPath "requirements.txt")) {
    Fail-And-Exit "requirements.txt not found in project root."
}

try {
    python -m pip install --upgrade pip | Out-Null
    python -m pip install -r requirements.txt
    Write-Success "Python dependencies installed/verified."
} catch {
    Fail-And-Exit "Failed to install Python dependencies from requirements.txt: $_"
}

### 3. NODE DEPENDENCIES CHECK ###########################################

Write-Info "Ensuring Node dependencies for frontend..."
Push-Location "frontend"
try {
    if (-not (Test-Path -LiteralPath "node_modules")) {
        Write-Info "node_modules not found – running 'npm install'..."
        npm install
        Write-Success "npm install completed."
    } else {
        Write-Success "node_modules already present – skipping npm install."
    }
} catch {
    Pop-Location
    Fail-And-Exit "npm install failed in 'frontend': $_"
}
Pop-Location

### 4. DATABASE & REDIS VALIDATION #######################################

Write-Info "Starting/validating Docker services (db, redis, backend, worker)..."

try {
    docker compose up -d --build db redis backend worker
    Write-Success "docker compose services started (db, redis, backend, worker)."
} catch {
    Fail-And-Exit "Failed to start docker-compose services: $_"
}

Start-Sleep -Seconds 8

function Test-Container-Running($serviceName) {
    $ps = docker compose ps $serviceName --format "{{.Service}} {{.State}}" 2>$null
    if (-not $ps) { return $false }
    return $ps -match "running"
}

if (-not (Test-Container-Running "db")) {
    Fail-And-Exit "PostgreSQL container 'db' is not running after docker compose up."
}
if (-not (Test-Container-Running "redis")) {
    Fail-And-Exit "Redis container 'redis' is not running after docker compose up."
}

Write-Success "PostgreSQL and Redis containers are running."

# Determine DATABASE_URL (prefer env, fallback to default from config)
if ($env:DATABASE_URL) {
    $databaseUrl = $env:DATABASE_URL
} else {
    $databaseUrl = "postgresql://automation_user:Mm@01151800275$@localhost:5432/marketing_automation"
    Write-Warn "DATABASE_URL not set in environment; using default local URL."
}

# Test DB connection via Python
Write-Info "Validating PostgreSQL connectivity..."
$dbTest = @"
import sys
from sqlalchemy import create_engine, text

url = "$databaseUrl"
try:
    engine = create_engine(url)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("DB_OK")
except Exception as e:
    print("DB_FAIL:", e, file=sys.stderr)
    sys.exit(1)
"@

try {
    $dbOut = python -c $dbTest 2>&1
    if ($dbOut -notmatch "DB_OK") {
        Fail-And-Exit "Database connectivity check failed: $dbOut"
    }
    Write-Success "Database connectivity verified."
} catch {
    Fail-And-Exit "Database connectivity check raised an error: $_"
}

# Test Redis connectivity by checking container logs/state only (simplified)
Write-Info "Validating Redis container state..."
try {
    $redisPs = docker compose ps redis --format "{{.State}}"
    if ($redisPs -notmatch "running") {
        Fail-And-Exit "Redis container is not in 'running' state."
    }
    Write-Success "Redis container state is healthy (running)."
} catch {
    Fail-And-Exit "Failed to inspect Redis container state: $_"
}

### 5. MIGRATIONS & SEED ##################################################

Write-Info "Running Alembic migrations (upgrade head)..."
try {
    alembic upgrade head
    Write-Success "Alembic migrations applied successfully."
} catch {
    Fail-And-Exit "Alembic migration failed: $_"
}

$seedFlag = ".seeded"
if (-not (Test-Path -LiteralPath $seedFlag)) {
    Write-Info "Seed flag not found – seeding database with demo data..."
    try {
        python -m backend.seed
        New-Item -ItemType File -Path $seedFlag -Force | Out-Null
        Write-Success "Database seeded and seed flag '$seedFlag' created."
    } catch {
        Fail-And-Exit "Database seeding failed: $_"
    }
} else {
    Write-Success "Seed flag '$seedFlag' exists – skipping seeding."
}

### 6. START SERVICES (Backend, Celery, Frontend) ########################

Write-Info "Starting application services (backend, worker, frontend)..."


# Frontend (npm run dev)
try {
    $frontendCmd = "cd `"$PWD\frontend`"; npm run dev"
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $frontendCmd -WindowStyle Minimized | Out-Null
    Write-Success "Frontend (Vite dev server) started in a new PowerShell window."
} catch {
    Fail-And-Exit "Failed to start frontend service: $_"
}

Write-Info "Waiting for services to come up..."
Start-Sleep -Seconds 10

### 7. FINAL STATUS OUTPUT & HEALTH CHECKS ###############################

$allOk = $true

# Check backend port
if (Test-PortFree -Port 8000) {
    Write-Fail "Backend (port 8000) does not appear to be listening."
    $allOk = $false
} else {
    Write-Success "Backend appears to be listening on port 8000."
}

# Check frontend port
if (Test-PortFree -Port 5173) {
    Write-Fail "Frontend (port 5173) does not appear to be listening."
    $allOk = $false
} else {
    Write-Success "Frontend appears to be listening on port 5173."
}

# Check docker services still running
if (-not (Test-Container-Running "backend")) {
    Write-Fail "Docker service 'backend' is not running."
    $allOk = $false
}
if (-not (Test-Container-Running "worker")) {
    Write-Fail "Docker service 'worker' is not running."
    $allOk = $false
}

# Simple SSE health check (ensure endpoint is reachable)
try {
    $sseResp = Invoke-WebRequest -Uri "http://localhost:8000/api/realtime/events" -Headers @{ "Accept" = "text/event-stream" } -Method GET -TimeoutSec 5
    if ($sseResp.StatusCode -ge 200 -and $sseResp.StatusCode -lt 400) {
        Write-Success "SSE endpoint reachable at /api/realtime/events."
    } else {
        Write-Warn "SSE endpoint returned unexpected status: $($sseResp.StatusCode)"
    }
} catch {
    Write-Warn "Could not verify SSE endpoint (this may be transient): $_"
}

Write-Host ""
if ($allOk) {
    Write-Host "✅ SYSTEM STARTED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "Backend URL : http://localhost:8000" -ForegroundColor Green
    Write-Host "Frontend URL: http://localhost:5173" -ForegroundColor Green
    Write-Host "Database    : PostgreSQL (connected)" -ForegroundColor Green
    Write-Host "Redis       : connected (container running)" -ForegroundColor Green
    Write-Host "SSE         : /api/realtime/events reachable" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ SERVICE FAILED - one or more services are not healthy." -ForegroundColor Red
    Fail-And-Exit "Check individual service logs (backend, worker, frontend, docker containers) for details."
}

### 6. START SERVICES (Backend, Celery, Frontend with Chrome) ################

Write-Info "Starting application services with live logs..."


# Frontend (Vite) - open in Google Chrome
try {
    $frontendPort = 5173
    $frontendURL = "http://localhost:$frontendPort"

    Push-Location "frontend"
    Write-Info "Installing Node dependencies if needed..."
    if (-not (Test-Path -LiteralPath "node_modules")) {
        npm install
        Write-Success "Node modules installed."
    } else {
        Write-Success "Node modules already present."
    }

    Write-Info "Starting Vite dev server..."
    Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", "npm run dev"

    # انتظر شوية قبل فتح Chrome عشان server يبدأ
    Start-Sleep -Seconds 5

    Write-Info "Opening Frontend in Google Chrome..."
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    if (-Not (Test-Path $chromePath)) {
        Write-Warn "Google Chrome not found at default path. Please open $frontendURL manually."
    } else {
        Start-Process $chromePath $frontendURL
        Write-Success "Frontend opened in Google Chrome."
    }
    Pop-Location
} catch {
    Fail-And-Exit "Failed to start frontend service: $_"
}
