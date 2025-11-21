# Métricas de Rendimiento Reales - Agrovet2025

## ⚠️ Nota Importante

Este documento contiene **métricas reales obtenidas mediante pruebas ejecutadas** en el sistema. Las pruebas se ejecutaron el **20 de noviembre de 2025**.

**Estado de los Servicios al momento de las pruebas:**
- ❌ Servicios no estaban corriendo (requieren `docker-compose up`)
- ✅ Métricas del sistema obtenidas exitosamente

---

## 📊 Métricas del Sistema (Reales)

### Hardware del Sistema de Pruebas

**Fecha de Prueba:** 2025-11-20 18:13:28

| Métrica | Valor Real | Estado |
|---------|------------|--------|
| **CPU Cores** | 8 cores | ✅ |
| **CPU Uso Promedio** | 53.0% | ⚠️ Moderado |
| **CPU por Core** | 44.6% - 65.6% | ⚠️ Variable |
| **RAM Total** | 7.24 GB | ✅ |
| **RAM Usada** | 6.22 GB (85.8%) | ⚠️ Alta |
| **RAM Disponible** | 1.03 GB | ⚠️ Baja |
| **Disco Total** | 475.97 GB | ✅ |
| **Disco Usado** | 194.22 GB (40.8%) | ✅ |
| **Disco Libre** | 281.75 GB | ✅ |

### Análisis de Métricas del Sistema

**CPU:**
- Uso promedio: 53% - Sistema con carga moderada
- Variabilidad entre cores: 44.6% - 65.6%
- **Conclusión**: Sistema tiene capacidad disponible para ejecutar servicios

**RAM:**
- Uso: 85.8% - **ALTA UTILIZACIÓN**
- Disponible: 1.03 GB - **LIMITADO**
- **Conclusión**: ⚠️ **Se recomienda liberar RAM antes de ejecutar servicios**
- **Recomendación**: Cerrar aplicaciones innecesarias o aumentar RAM

**Disco:**
- Uso: 40.8% - **SALUDABLE**
- Espacio disponible: 281.75 GB - **SUFICIENTE**
- **Conclusión**: ✅ No hay problemas de espacio en disco

---

## 🧪 Pruebas de Rendimiento

### Estado Actual

**Servicios Verificados:**
- ❌ Auth Service (http://localhost:8002) - No disponible
- ❌ Media Service (http://localhost:8001) - No disponible
- ❌ Profiles Service (http://localhost:8003) - No disponible
- ❌ Marketplace Service (http://localhost:8004) - No disponible
- ❌ Foro Service (http://localhost:8005) - No disponible
- ❌ Chat Service (http://localhost:8006) - No disponible

**Razón:** Los servicios no están corriendo. Requieren iniciarse con Docker Compose.

---

## 📝 Cómo Ejecutar Pruebas de Rendimiento Reales

### Prerequisitos

1. **Iniciar los servicios:**
```bash
cd c:\Users\FSOCIETY\Desktop\Projects\Backend\agrovet2025
docker-compose -f docker-compose.dev.yml up -d
```

2. **Verificar que los servicios estén corriendo:**
```bash
docker-compose -f docker-compose.dev.yml ps
```

3. **Esperar 30-60 segundos** para que los servicios inicien completamente

### Ejecutar Pruebas Básicas

**Script de Pruebas Automáticas:**
```bash
python scripts/performance_test.py
```

Este script:
- ✅ Verifica disponibilidad de cada servicio
- ✅ Prueba endpoints de health check
- ✅ Ejecuta pruebas de carga concurrente (20 requests, 5 threads)
- ✅ Genera reporte JSON con métricas

**Salida esperada:**
```
============================================================
PRUEBAS DE RENDIMIENTO - AGROVET2025
============================================================
Timestamp: 2025-11-20T18:XX:XX
Base URL: http://localhost

Verificando servicios disponibles...
  auth            [OK] Disponible    (http://localhost:8002)
  media           [OK] Disponible    (http://localhost:8001)
  ...

Ejecutando pruebas básicas...
Probando auth            /health/... [OK] 45.23ms
Probando profiles        /health/... [OK] 38.12ms
...

Ejecutando pruebas de carga concurrente...
Prueba de carga: auth            (20 requests, 5 threads)... [OK] 12.5 RPS, P95: 125.34ms
...
```

### Ejecutar Pruebas con Locust (Carga Real)

**Instalar Locust:**
```bash
pip install locust
```

**Ejecutar prueba de carga:**
```bash
cd load_tests
locust -f locustfile.py --host=http://localhost --users 50 --spawn-rate 5 --run-time 5m
```

**Parámetros:**
- `--users 50`: 50 usuarios concurrentes
- `--spawn-rate 5`: Aumentar 5 usuarios por segundo
- `--run-time 5m`: Ejecutar por 5 minutos

**Acceder a dashboard:**
- Abrir navegador en: http://localhost:8089
- Ver métricas en tiempo real

### Ejecutar Pruebas con k6 (Alternativa)

**Instalar k6:**
```bash
# Windows: Descargar de https://k6.io/docs/getting-started/installation/
# O usar: choco install k6
```

**Crear script de prueba:**
```javascript
// load_tests/k6_test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp up a 20 usuarios
    { duration: '3m', target: 20 },   // Mantener 20 usuarios
    { duration: '1m', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const res = http.get('http://localhost:8002/health/');
  check(res, { 'status was 200': (r) => r.status == 200 });
  sleep(1);
}
```

**Ejecutar:**
```bash
k6 run load_tests/k6_test.js
```

### Obtener Métricas del Sistema

**Ejecutar script de métricas:**
```bash
python scripts/system_metrics.py
```

**Salida:**
- Métricas de CPU, RAM, Disco
- Guarda en archivo JSON: `system_metrics_YYYYMMDD_HHMMSS.json`

---

## 📈 Plantilla para Documentar Resultados Reales

Cuando ejecutes las pruebas, completa esta sección con los datos reales:

### Resultados de Pruebas Básicas

**Fecha:** _______________
**Servicios Corriendo:** _______________

| Servicio | Endpoint | Latencia (ms) | Status Code | Estado |
|----------|----------|---------------|-------------|--------|
| Auth | /health/ | _____ | _____ | ✅/❌ |
| Media | /health/ | _____ | _____ | ✅/❌ |
| Profiles | /health/ | _____ | _____ | ✅/❌ |
| Marketplace | /health/ | _____ | _____ | ✅/❌ |
| Foro | /health/ | _____ | _____ | ✅/❌ |
| Chat | /health/ | _____ | _____ | ✅/❌ |

### Resultados de Pruebas de Carga

**Configuración:**
- Usuarios concurrentes: _____
- Requests totales: _____
- Duración: _____
- Threads/Workers: _____

| Servicio | RPS | Latencia P50 | Latencia P95 | Latencia P99 | Error Rate | Estado |
|----------|-----|--------------|--------------|--------------|------------|--------|
| Auth | _____ | _____ | _____ | _____ | _____% | ✅/❌ |
| Profiles | _____ | _____ | _____ | _____ | _____% | ✅/❌ |
| Marketplace | _____ | _____ | _____ | _____ | _____% | ✅/❌ |

### Métricas del Sistema Durante Pruebas

**CPU:**
- Promedio: _____%
- Pico: _____%
- Por core: [_____, _____, _____, _____, _____, _____, _____, _____]

**RAM:**
- Total: _____ GB
- Usada: _____ GB (_____%)
- Disponible: _____ GB

**Disco I/O:**
- Lectura: _____ MB/s
- Escritura: _____ MB/s

---

## 🔄 Actualizar Documento con Datos Reales

### Pasos para Actualizar

1. **Ejecutar todas las pruebas** (básicas, carga, sistema)
2. **Recopilar archivos JSON generados:**
   - `performance_results_*.json`
   - `system_metrics_*.json`
3. **Analizar resultados** y completar las tablas arriba
4. **Actualizar este documento** con los datos reales
5. **Comparar con estimaciones** en `PERFORMANCE_AND_SCALABILITY.md`

### Ejemplo de Comando para Recopilar Todos los Resultados

```bash
# Ejecutar todas las pruebas en secuencia
python scripts/system_metrics.py
python scripts/performance_test.py
locust -f load_tests/locustfile.py --host=http://localhost --users 100 --spawn-rate 10 --run-time 10m --headless --html=load_test_report.html

# Los resultados estarán en:
# - system_metrics_*.json
# - performance_results_*.json
# - load_test_report.html
```

---

## 📋 Checklist de Pruebas

- [ ] Servicios iniciados con Docker Compose
- [ ] Verificar health checks de todos los servicios
- [ ] Ejecutar pruebas básicas (`performance_test.py`)
- [ ] Ejecutar pruebas de carga con Locust
- [ ] Obtener métricas del sistema durante pruebas
- [ ] Documentar resultados en este archivo
- [ ] Comparar con estimaciones teóricas
- [ ] Identificar cuellos de botella reales
- [ ] Proponer optimizaciones basadas en datos reales

---

## 🎯 Próximos Pasos

1. **Iniciar servicios** y ejecutar pruebas básicas
2. **Ejecutar pruebas de carga** con diferentes configuraciones:
   - 10 usuarios concurrentes
   - 50 usuarios concurrentes
   - 100 usuarios concurrentes
3. **Monitorear recursos** durante las pruebas
4. **Documentar todos los resultados** en este archivo
5. **Actualizar** `PERFORMANCE_AND_SCALABILITY.md` con datos reales

---

**Última actualización:** 2025-11-20 18:13:28
**Próxima ejecución de pruebas:** Pendiente (requiere servicios corriendo)

