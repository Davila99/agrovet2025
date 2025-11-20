# Guía de Despliegue - Microservicios Agrovet2025

## Desarrollo Local

### Prerrequisitos
- Docker y Docker Compose
- Python 3.11+
- PostgreSQL client (opcional)

### 1. Levantar Infraestructura

```bash
# Levantar servicios de infraestructura
docker-compose -f docker-compose.dev.yml up -d

# Verificar que todos los servicios estén corriendo
docker-compose -f docker-compose.dev.yml ps
```

### 2. Crear Topics de Kafka

```bash
# Opción 1: Desde el host (requiere Kafka CLI instalado)
python scripts/create_kafka_topics.py

# Opción 2: Desde el contenedor
docker exec -it kafka-agrovet kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic user.events \
  --partitions 3 \
  --replication-factor 1
```

### 3. Configurar Variables de Entorno

Crear archivo `.env` en la raíz del proyecto:

```bash
# Database URLs
DATABASE_URL_AUTH=postgresql://agrovet:agrovet_dev@localhost:5432/auth_db
DATABASE_URL_MEDIA=postgresql://agrovet:agrovet_dev@localhost:5436/media_db
DATABASE_URL_PROFILES=postgresql://agrovet:agrovet_dev@localhost:5433/profiles_db
DATABASE_URL_MARKETPLACE=postgresql://agrovet:agrovet_dev@localhost:5434/marketplace_db
DATABASE_URL_CHAT=postgresql://agrovet:agrovet_dev@localhost:5435/chat_db
DATABASE_URL_FORO=postgresql://agrovet:agrovet_dev@localhost:5437/foro_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Supabase
SUPABASE_URL=https://kprsxavfuqotrgfxyqbj.supabase.co
SUPABASE_KEY=your-key-here
SUPABASE_BUCKET=agrovet-profile

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=*
```

### 4. Ejecutar Migraciones

Para cada servicio:

```bash
# Media Service
cd services/media-service
python manage.py migrate
python manage.py createsuperuser  # opcional

# Repetir para otros servicios...
```

### 5. Ejecutar Servicios

```bash
# Media Service (puerto 8001)
cd services/media-service
python manage.py runserver 0.0.0.0:8001

# En otra terminal, Auth Service (puerto 8002)
cd services/auth-service
python manage.py runserver 0.0.0.0:8002

# etc...
```

### 6. Configurar Traefik (Opcional)

Traefik detectará automáticamente los servicios con labels Docker. Para desarrollo local, puedes acceder directamente a los puertos.

## Producción (Kubernetes)

### Prerrequisitos
- Cluster Kubernetes (v1.24+)
- kubectl configurado
- Helm 3.x
- Traefik Ingress Controller instalado

### 1. Crear Namespace

```bash
kubectl create namespace agrovet
```

### 2. Crear Secrets

```bash
# Crear secret para base de datos
kubectl create secret generic db-credentials \
  --from-literal=username=agrovet \
  --from-literal=password=your-secure-password \
  -n agrovet

# Crear secret para Supabase
kubectl create secret generic supabase-credentials \
  --from-literal=url=https://your-supabase-url.supabase.co \
  --from-literal=key=your-key \
  --from-literal=bucket=agrovet-profile \
  -n agrovet

# Crear secret para Django
kubectl create secret generic django-secret \
  --from-literal=secret-key=your-secret-key \
  -n agrovet
```

### 3. Desplegar con Helm

```bash
# Instalar chart de media-service
helm install media-service deploy/helm/media-service \
  --namespace agrovet \
  --set image.tag=latest \
  --set database.host=postgres-media \
  --set redis.url=redis://redis:6379/0

# Repetir para otros servicios...
```

### 4. Configurar Ingress

Los servicios expondrán IngressRoutes de Traefik automáticamente. Verificar:

```bash
kubectl get ingressroute -n agrovet
```

### 5. Verificar Despliegue

```bash
# Ver pods
kubectl get pods -n agrovet

# Ver logs
kubectl logs -f deployment/media-service -n agrovet

# Health check
curl https://api.agrovet.com/health/
```

## CI/CD con GitHub Actions

Los workflows están configurados en `.github/workflows/`. Cada servicio tiene su propio workflow que:

1. Ejecuta lint y tests
2. Construye imagen Docker
3. Escanea con Trivy
4. Publica a registry (GHCR)
5. Despliega a Kubernetes (opcional)

### Despliegue Manual

```bash
# Build y push imagen
docker build -t ghcr.io/your-org/media-service:latest services/media-service/
docker push ghcr.io/your-org/media-service:latest

# Actualizar deployment
kubectl set image deployment/media-service \
  media-service=ghcr.io/your-org/media-service:latest \
  -n agrovet
```

## Rollback

### Rollback de Deployment

```bash
# Ver historial
kubectl rollout history deployment/media-service -n agrovet

# Rollback a versión anterior
kubectl rollout undo deployment/media-service -n agrovet

# Rollback a versión específica
kubectl rollout undo deployment/media-service --to-revision=2 -n agrovet
```

### Rollback de Helm

```bash
# Ver releases
helm list -n agrovet

# Rollback
helm rollback media-service 1 -n agrovet
```

## Monitoreo

### Health Checks

Cada servicio expone:
- `GET /health/` - Health check simple
- `GET /health/detailed/` - Health check con DB y Redis

### Métricas

- Prometheus scrape endpoints: `/metrics/` (si implementado)
- Grafana dashboards: Ver `deploy/grafana/`

### Logs

```bash
# Logs de un servicio
kubectl logs -f deployment/media-service -n agrovet

# Logs de todos los pods
kubectl logs -f -l app=media-service -n agrovet
```

## Troubleshooting

### Servicio no inicia

1. Verificar logs: `kubectl logs deployment/service-name -n agrovet`
2. Verificar configuración: `kubectl describe deployment/service-name -n agrovet`
3. Verificar secrets: `kubectl get secrets -n agrovet`

### Base de datos no conecta

1. Verificar que PostgreSQL esté corriendo
2. Verificar credenciales en secrets
3. Verificar network policies

### Kafka no funciona

1. Verificar que Kafka y Zookeeper estén corriendo
2. Verificar topics: `kafka-topics --list --bootstrap-server localhost:9092`
3. Verificar configuración de bootstrap servers

## Próximos Pasos

- [ ] Configurar auto-scaling (HPA)
- [ ] Configurar backups automáticos de DB
- [ ] Implementar canary deployments
- [ ] Configurar alertas (Prometheus Alertmanager)
- [ ] Implementar rate limiting en Traefik

