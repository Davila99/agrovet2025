# Migración a Microservicios - Agrovet2025

## 🎯 Objetivo

Migrar el monolito Django actual a una arquitectura de microservicios escalable y mantenible.

## 📋 Estado Actual

### ✅ Completado

1. **Estructura Base**
   - Módulos comunes (`common/`)
   - Health checks reutilizables
   - Configuración Kafka (producer/consumer)
   - Configuración Redis con namespaces

2. **Infraestructura**
   - `docker-compose.dev.yml` completo con:
     - Traefik (API Gateway)
     - Redis (Cache/Sessions)
     - Kafka + Zookeeper (Eventos)
     - PostgreSQL (una instancia por servicio)
     - MinIO (S3-compatible)

3. **Media Service**
   - Estructura completa del microservicio
   - Integración con Supabase
   - Eventos Kafka
   - Health endpoints
   - Dockerfile y requirements

4. **CI/CD**
   - GitHub Actions workflow para Media Service
   - Tests, lint, build, scan, deploy

5. **Documentación**
   - `docs/ARCHITECTURE.md` - Arquitectura de alto nivel
   - `docs/DEPLOY.md` - Guía de despliegue
   - `DELIVERABLES.md` - Lista de entregables

### ⏳ En Progreso / Pendiente

1. **Microservicios Restantes**
   - Auth Service
   - Profiles Service
   - Marketplace Service
   - Chat Service
   - Foro Service

2. **Kubernetes**
   - Manifests YAML completos
   - Helm charts
   - ConfigMaps y Secrets

3. **Scripts de Migración**
   - ETL para migrar datos
   - Scripts de validación

4. **Observability**
   - Métricas Prometheus
   - Tracing Jaeger
   - Logs estructurados

## 🚀 Inicio Rápido

### Desarrollo Local

```bash
# 1. Levantar infraestructura
docker-compose -f docker-compose.dev.yml up -d

# 2. Crear topics de Kafka
python scripts/create_kafka_topics.py

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Ejecutar Media Service
cd services/media-service
python manage.py migrate
python manage.py runserver 0.0.0.0:8001
```

### Testing

```bash
cd services/media-service
pytest --cov=. --cov-report=html
```

## 📚 Documentación

- [Arquitectura](docs/ARCHITECTURE.md) - Diseño de alto nivel
- [Despliegue](docs/DEPLOY.md) - Guías de despliegue
- [Entregables](DELIVERABLES.md) - Lista completa de entregables

## 🔄 Estrategia de Migración

1. **Fase 1**: Servicios read-only (Media ✅, Foro)
2. **Fase 2**: Servicios con dependencias simples (Profiles)
3. **Fase 3**: Servicios complejos (Marketplace, Chat)
4. **Fase 4**: Auth Service (crítico)
5. **Fase 5**: Desactivar monolito gradualmente

## 🛠️ Tecnologías

- **Backend**: Django 4.2+ / Django REST Framework
- **Message Broker**: Apache Kafka
- **Cache**: Redis
- **Database**: PostgreSQL (una por servicio)
- **Storage**: Supabase Storage
- **API Gateway**: Traefik
- **Orquestación**: Kubernetes
- **CI/CD**: GitHub Actions

## 📝 Notas Importantes

- El código mantiene compatibilidad con el monolito durante la migración
- Los servicios pueden ejecutarse en paralelo
- Se recomienda usar feature flags para activar/desactivar funcionalidades
- Todos los cambios están documentados en commits atómicos

## 🤝 Contribución

Para agregar un nuevo servicio:

1. Crear estructura en `services/<service-name>/`
2. Copiar y adaptar de `services/media-service/` como template
3. Agregar workflow en `.github/workflows/`
4. Crear manifests en `deploy/k8s/<service-name>/`
5. Actualizar documentación

## 📞 Soporte

Para preguntas o problemas, ver:
- `docs/ARCHITECTURE.md` para diseño
- `docs/DEPLOY.md` para despliegue
- Issues en el repositorio

