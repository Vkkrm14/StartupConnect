# TrustGraph - Stop All Services
# Stops Docker containers and optionally removes data

Write-Host " TrustGraph - Stop Services" -ForegroundColor Red
Write-Host "================================`n" -ForegroundColor Red

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

# Ask if user wants to keep data
$keepData = Read-Host "Keep database data? (Y/n)"

if ($keepData -eq "n" -or $keepData -eq "N") {
    Write-Host "`n  WARNING: This will delete all data!" -ForegroundColor Yellow
    $confirm = Read-Host "Are you sure? (yes/no)"
    
    if ($confirm -eq "yes") {
        Write-Host "`n  Stopping services and removing data..." -ForegroundColor Red
        Invoke-Compose down -v
        Write-Host "All services stopped and data cleared`n" -ForegroundColor Green
    } else {
        Write-Host "`n  Cancelled. Use 'docker-compose down -v' to remove data manually.`n" -ForegroundColor Cyan
        Invoke-Compose down
        Write-Host " Services stopped (data preserved)`n" -ForegroundColor Green
    }
} else {
    Write-Host "`n Stopping services (keeping data)..." -ForegroundColor Yellow
    Invoke-Compose down
    Write-Host " All services stopped (data preserved)`n" -ForegroundColor Green
}

Read-Host "Press Enter to exit"
