$services = @(
    @{ Name = "Auth Service";       Url = "http://localhost:8002/health/" },
    @{ Name = "Media Service";      Url = "http://localhost:8001/health/" },
    @{ Name = "Profiles Service";   Url = "http://localhost:8003/health/" },
    @{ Name = "Marketplace Service"; Url = "http://localhost:8004/health/" },
    @{ Name = "Foro Service";       Url = "http://localhost:8005/health/" },
    @{ Name = "Chat Service";       Url = "http://localhost:8006/health/" },
    @{ Name = "MinIO";              Url = "http://localhost:9000/minio/health/live" }
)

Write-Host "Verificando estado de los microservicios..." -ForegroundColor Cyan
Write-Host "----------------------------------------"

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.Url -Method Get -ErrorAction Stop -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ $($service.Name): OK" -ForegroundColor Green
        } else {
            Write-Host "⚠️ $($service.Name): Status $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ $($service.Name): Error de conexión ($($_.Exception.Message))" -ForegroundColor Red
    }
}

Write-Host "----------------------------------------"
Write-Host "Verificación completada."
