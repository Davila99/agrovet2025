# List of images to pull sequentially
$images = @(
    "redis:7-alpine",
    "bitnamilegacy/zookeeper:3.9",
    "bitnamilegacy/kafka:3.6",
    "postgres:15-alpine",
    "minio/minio:latest"
)

foreach ($image in $images) {
    Write-Host "Pulling $image..."
    docker pull $image
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to pull $image"
        exit 1
    }
}

Write-Host "All images pulled successfully."
