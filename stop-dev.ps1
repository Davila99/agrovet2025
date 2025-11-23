# Agrovet2025 Development Environment Stop Script
# This script stops both backend microservices and frontend development server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agrovet2025 Development Shutdown" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Stop backend services
Write-Host "[1/2] Stopping backend microservices..." -ForegroundColor Yellow

docker-compose -f docker-compose.dev.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Backend services stopped" -ForegroundColor Green
} else {
    Write-Host "⚠ Some issues occurred while stopping backend services" -ForegroundColor Yellow
}

# Note about frontend
Write-Host "[2/2] Frontend server..." -ForegroundColor Yellow
Write-Host "  If the frontend dev server is running, press Ctrl+C in its terminal" -ForegroundColor Gray
Write-Host ""
Write-Host "✓ Shutdown complete" -ForegroundColor Green
Write-Host ""
