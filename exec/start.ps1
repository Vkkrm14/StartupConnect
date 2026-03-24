# TrustGraph Quick Start Script for Windows PowerShell
# Run this script to start the entire system

Write-Host "TrustGraph - Quick Start" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Prefer Docker Compose v2 (docker compose) but keep fallback to docker-compose
$useComposeV2 = $false
try {
    docker compose version *> $null
    $useComposeV2 = $true
} catch {
    $useComposeV2 = $false
}

function Invoke-Compose {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        $Args
    )

    if ($useComposeV2) {
        docker compose @Args
    } else {
        docker-compose @Args
    }
}

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        if (Get-Command $Command -ErrorAction Stop) {
            return $true
        }
    } catch {
        return $false
    }
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

$allGood = $true

if (-not (Test-Command "docker")) {
    Write-Host "[X] Docker not found. Please install Docker Desktop." -ForegroundColor Red
    Write-Host "   Download: https://www.docker.com/products/docker-desktop/`n" -ForegroundColor Gray
    $allGood = $false
} else {
    Write-Host "[OK] Docker found" -ForegroundColor Green
}

if (-not (Test-Command "python")) {
    Write-Host "[X] Python not found. Please install Python 3.11+." -ForegroundColor Red
    Write-Host "   Download: https://www.python.org/downloads/`n" -ForegroundColor Gray
    $allGood = $false
} else {
    $pythonVersion = python --version
    Write-Host "[OK] Python found: $pythonVersion" -ForegroundColor Green
}

if (-not (Test-Command "flutter")) {
    Write-Host "[!] Flutter not found. Install to run mobile app." -ForegroundColor Yellow
    Write-Host "   Download: https://docs.flutter.dev/get-started/install`n" -ForegroundColor Gray
} else {
    $flutterVersion = flutter --version | Select-Object -First 1
    Write-Host "[OK] Flutter found: $flutterVersion" -ForegroundColor Green
}

if (-not $allGood) {
    Write-Host "`n[X] Please install missing prerequisites and try again.`n" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "`n================================`n" -ForegroundColor Cyan

# Start backend services
Write-Host "Starting Docker services..." -ForegroundColor Yellow

# Elasticsearch requires vm.max_map_count >= 262144.
# On Docker Desktop for Windows, this must be set on the Docker Desktop (WSL2) VM,
# not via container sysctls (which triggers an OCI runtime error).
if (Test-Command "wsl") {
    try {
        Write-Host "Ensuring vm.max_map_count for Elasticsearch (Docker Desktop WSL2)..." -ForegroundColor Yellow
        wsl -d docker-desktop -u root sysctl -w vm.max_map_count=262144 *> $null
        Write-Host "[OK] vm.max_map_count configured" -ForegroundColor Green
    } catch {
        Write-Host "[!] Could not set vm.max_map_count via WSL. If Elasticsearch fails to start, run:" -ForegroundColor Yellow
        Write-Host "    wsl -d docker-desktop -u root sysctl -w vm.max_map_count=262144" -ForegroundColor Gray
    }
}

Invoke-Compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[X] Failed to start Docker services. Check Docker Desktop is running.`n" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

Write-Host "[OK] Docker services starting...`n" -ForegroundColor Green

# Wait for services to be healthy
Write-Host "Waiting for services to be ready (60 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Check service status
Write-Host "`nService Status:" -ForegroundColor Yellow
Invoke-Compose ps

Write-Host "`n================================`n" -ForegroundColor Cyan

# Seed data
Write-Host "Seeding sample data..." -ForegroundColor Yellow
Write-Host "   (10 users, 4 startups, trust network)`n" -ForegroundColor Gray

python backend\scripts\seed_data.py --clear --force

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  Data seeding failed. Services may not be fully ready yet." -ForegroundColor Yellow
    Write-Host "   You can try again later with: python backend\scripts\seed_data.py --clear`n" -ForegroundColor Gray
} else {
    Write-Host "[OK] Sample data seeded successfully`n" -ForegroundColor Green
}

Write-Host "================================`n" -ForegroundColor Cyan

# Provide next steps
Write-Host "[OK] Backend is ready!`n" -ForegroundColor Green

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1] Test Backend APIs:" -ForegroundColor Yellow
Write-Host "   • API Gateway: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "   • Graph Service: http://localhost:8001/docs" -ForegroundColor Gray
Write-Host "   • Search Service: http://localhost:8003/docs`n" -ForegroundColor Gray

Write-Host "[2] Start Kafka Consumers (Optional - for real-time features):" -ForegroundColor Yellow
Write-Host "   Open 3 new PowerShell windows and run:`n" -ForegroundColor Gray
Write-Host "   Window 1 (Search Indexer):" -ForegroundColor White
Write-Host "   cd backend\search-service" -ForegroundColor Gray
Write-Host "   python -m app.consumers.user_indexer_consumer`n" -ForegroundColor Gray
Write-Host "   Window 2 (Trust Updater):" -ForegroundColor White
Write-Host "   cd backend\graph-service" -ForegroundColor Gray
Write-Host "   python -m app.consumers.trust_update_consumer`n" -ForegroundColor Gray
Write-Host "   Window 3 (Intro Workflow):" -ForegroundColor White
Write-Host "   cd backend\workflow-service" -ForegroundColor Gray
Write-Host "   python -m app.consumers.intro_event_consumer`n" -ForegroundColor Gray

Write-Host "[3] Run Flutter App:" -ForegroundColor Yellow
Write-Host "   cd frontend\trustgraph_app" -ForegroundColor Gray
Write-Host "   flutter pub get" -ForegroundColor Gray
Write-Host "   flutter run -d chrome`n" -ForegroundColor Gray

Write-Host "================================`n" -ForegroundColor Cyan

Write-Host "Sample Users (for testing):" -ForegroundColor Cyan
Write-Host "   • Alice Johnson (Founder - FinFlow)" -ForegroundColor Gray
Write-Host "   • Bob Smith (Founder - no startup)" -ForegroundColor Gray
Write-Host "   • Frank Miller (Investor - fintech)" -ForegroundColor Gray
Write-Host "   • Ivy Martinez (Connector)`n" -ForegroundColor Gray

Write-Host "To stop all services:" -ForegroundColor Red
Write-Host "   docker compose down`n" -ForegroundColor Gray

Write-Host "Happy coding!`n" -ForegroundColor Green

Read-Host "Press Enter to continue"
