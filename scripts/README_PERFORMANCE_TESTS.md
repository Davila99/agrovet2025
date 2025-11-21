# Scripts de Pruebas de Rendimiento

## 📋 Descripción

Scripts para ejecutar pruebas de rendimiento reales y obtener métricas del sistema y servicios.

## 🛠️ Scripts Disponibles

### 1. `performance_test.py`

Prueba endpoints de los servicios y ejecuta pruebas de carga concurrente.

**Uso:**
```bash
python scripts/performance_test.py
```

**Qué hace:**
- Verifica disponibilidad de servicios
- Prueba endpoints de health check
- Ejecuta pruebas de carga (20 requests, 5 threads)
- Genera reporte JSON: `performance_results_YYYYMMDD_HHMMSS.json`

**Requisitos:**
- Servicios corriendo (docker-compose up)
- Python 3.11+
- requests library

### 2. `system_metrics.py`

Obtiene métricas del sistema (CPU, RAM, Disco).

**Uso:**
```bash
python scripts/system_metrics.py
```

**Qué hace:**
- Mide CPU usage (total y por core)
- Mide RAM usage (total, usado, disponible)
- Mide Disk usage
- Genera reporte JSON: `system_metrics_YYYYMMDD_HHMMSS.json`

**Requisitos:**
- Python 3.11+
- psutil library (`pip install psutil`)

## 📊 Interpretar Resultados

### performance_results_*.json

```json
{
  "timestamp": "2025-11-20T18:12:49",
  "services": {
    "auth": {
      "health": {
        "endpoint": "/health/",
        "latency_ms": 45.23,
        "status_code": 200
      },
      "load_test": {
        "total_requests": 20,
        "success_count": 20,
        "error_count": 0,
        "rps": 12.5,
        "latency_p95_ms": 125.34
      }
    }
  }
}
```

### system_metrics_*.json

```json
{
  "timestamp": "2025-11-20T18:13:28",
  "cpu": {
    "percent": 53.0,
    "count": 8
  },
  "memory": {
    "total_gb": 7.24,
    "used_gb": 6.22,
    "percent": 85.8
  }
}
```

## 🚀 Ejecutar Suite Completa de Pruebas

```bash
# 1. Iniciar servicios
docker-compose -f docker-compose.dev.yml up -d

# 2. Esperar 30-60 segundos

# 3. Obtener métricas del sistema
python scripts/system_metrics.py

# 4. Ejecutar pruebas de rendimiento
python scripts/performance_test.py

# 5. (Opcional) Pruebas de carga con Locust
locust -f load_tests/locustfile.py --host=http://localhost --users 100 --spawn-rate 10 --run-time 10m
```

## 📝 Notas

- Los scripts verifican automáticamente si los servicios están disponibles
- Si un servicio no está disponible, se omite de las pruebas
- Los resultados se guardan en archivos JSON con timestamp
- Los scripts son compatibles con Windows, Linux y macOS

