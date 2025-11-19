# Documentación del Sprint — CI/CD, Rendimiento y Optimización Backend

Fecha: 2025-11-19

## 1. CI/CD

**Diagrama del pipeline (simplificado ASCII)**

```
push/pr -> Github Actions (build-and-test) -> deploy-example (simulated)
                   |                                |
                 tests,                            simulate upload
                 coverage                          migrate, restart
```

**Explicación paso a paso**
- El workflow `backend-ci.yml` se ejecuta en cada `push` a `main` y en cada PR.
- Pasos de CI:
  - Checkout del repositorio
  - Setup Python 3.11
  - `pip install -r requirements.txt`
  - `python manage.py makemigrations --check --dry-run` para detectar migraciones pendientes
  - `python manage.py check` para validar configuración
  - `coverage run --source='.' manage.py test` y `coverage report -m`
- Pasos de CD (ejemplo simulado):
  - Empaqueta el release (`tar.gz`) y lo copia a una carpeta simulada `/tmp/fake-remote`
  - Guarda un backup del release actual en `/tmp/releases`
  - Simula `python manage.py migrate` y reinicio de servicios (Gunicorn/Daphne)
  - Si ocurre una falla, intenta un rollback restaurando el backup más reciente

**Evidencias simuladas**
- Attachments: el workflow sube `coverage-report` como artefacto.
- En una ejecución real el step `Run tests` genera `coverage.xml` y se puede publicar en servicios de cobertura.

**Cómo se hace el deploy (real)**
1. Crear un servidor con acceso SSH y configurar `systemd` para Gunicorn/Daphne.
2. Configurar el flujo real en GitHub Actions para usar `appleboy/scp-action` o `rsync` y ejecutar comandos remotos via SSH (con llave privada en Secrets).
3. Pasos típicos: transferir release, activar virtualenv, instalar dependencias, aplicar migraciones, reiniciar servicios.

## 2. Rendimiento y Escalabilidad

**Metodología de pruebas**
- Utilizamos `k6` para scripts reproducibles (headless) y `locust` para pruebas interactivas.
- Mediremos: latencia p95/p99, throughput (req/s), error rate y tiempo promedio.
- Ejecutar en entorno lo más parecido a producción (red, DB y Redis reales).

**Resumen de resultados (simulados)**

```
| Test         | Users | p95 (ms) | p99 (ms) | throughput (req/s) | error rate |
|--------------|------:|---------:|---------:|-------------------:|-----------:|
| k6_10_users  |    10 |      120 |      240 |                 30 |       0.0% |
| k6_50_users  |    50 |      300 |      700 |                120 |       0.5% |
| k6_100_users |   100 |      700 |     1200 |                220 |       2.0% |
```

ASCII gráfico (p95 latency):

```
1000ms |                     *
 800ms |              *      *
 600ms |       *      *
 400ms | *     *
 200ms | *
        -------------------------
         10   50   100 users
```

**Instrucciones**
- k6: `k6 run load_tests/k6_100_users.js`
- locust: `locust -f load_tests/locustfile.py` (abrir UI en http://127.0.0.1:8089)

## 3. Optimización del Backend

### 3.1 Endpoints pesados (candidatos)
- `GET /api/foro/posts/` — puede devolver objetos con relaciones `author`, `media`, `comments` (coste N+1).
- `GET /api/foro/posts/<id>/` — detalle con comentarios anidados, cada comentario puede traer `replies`.

### 3.2 Mejora por ejemplo (select_related / prefetch_related / anotaciones)
Ejemplo aplicado en `foro/views.py` (sugerencia):

```py
# Antes: Post.objects.all().select_related('author')
# Optimizado: traer media y comunidad junto a author, y prefetchear comentarios top-level
posts = Post.objects.all().select_related('author', 'media', 'community').prefetch_related(
    Prefetch('comments', queryset=Comment.objects.filter(parent__isnull=True).select_related('user'))
)
```

### 3.3 Paginación
- Usar paginación en list endpoints (DRF PageNumberPagination o LimitOffsetPagination) para evitar respuestas enormes.

### 3.4 Caché con Redis
- Instalado `redis` y `django-redis` (añadir en requirements si no existe).
- Configuración en `consultveterinarias/settings.py` (se añadió `CACHES` y `REDIS_URL`).
- Utilidades en `tools/cache_utils.py`:

```py
from tools.cache_utils import get_or_set_cache, invalidate_cache

def get_popular_posts():
    return get_or_set_cache('popular_posts_v1', lambda: list(Post.objects.order_by('-relevance_score')[:20].values()), timeout=60)
```

### 3.5 Middleware de medición
- `tools/middleware/performance.py` implementa `PerformanceMiddleware` que añade header `X-Perf-Time-ms` y logea requests lentas (>500ms).

### 3.6 Tabla comparativa (simulada)

| Métrica | Antes | Después (select_related + cache) |
|---|---:|---:|
| Latencia p95 (GET posts) | 700 ms | 220 ms |
| Número de queries (GET posts) | 45 | 5 |
| Peso respuesta (KB) | 860 KB | 280 KB |
| CPU (avg) | 65% | 30% |

## 4. Conclusiones del Sprint

- Limitaciones: los resultados son simulados; deben validarse en entorno real con datos representativos.
- Próximo plan: aplicar cache granular, indexar campos usados en filtros/orden, usar paginación por cursor y mejorar async tasks para procesamiento de media.

---

Anexos: archivos añadidos al repo:
- `.github/workflows/backend-ci.yml`
- `load_tests/*` (k6 scripts, locustfile, README)
- `tools/cache_utils.py`
- `tools/middleware/performance.py`
- cambios en `consultveterinarias/settings.py` (caché Redis)
- `requirements.txt` actualizado (redis, coverage)
