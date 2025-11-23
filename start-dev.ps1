# Agrovet2025 Development Environment Startup Script
# This script starts ALL services (backend + frontend) using Docker Compose

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Agrovet2025 Development Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/2] Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Start all services (backend + frontend)
Write-Host "[2/2] Starting all services..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run..." -ForegroundColor Gray
Write-Host ""

docker-compose -f docker-compose.dev.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ✓ All Services Started" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend:          http://localhost:5173" -ForegroundColor White
Write-Host "Traefik Dashboard: http://localhost:8080" -ForegroundColor White
Write-Host ""
Write-Host "Backend Services:" -ForegroundColor White
Write-Host "  Auth Service:        http://localhost:8002" -ForegroundColor Gray
Write-Host "  Media Service:       http://localhost:8001" -ForegroundColor Gray
Write-Host "  Profiles Service:    http://localhost:8003" -ForegroundColor Gray
Write-Host "  Marketplace Service: http://localhost:8004" -ForegroundColor Gray
Write-Host "  Foro Service:        http://localhost:8005" -ForegroundColor Gray
Write-Host "  Chat Service:        http://localhost:8006" -ForegroundColor Gray
Write-Host ""
Write-Host "To view logs:      docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor Yellow
Write-Host "To stop services:  .\stop-dev.ps1" -ForegroundColor Yellow
Write-Host ""

