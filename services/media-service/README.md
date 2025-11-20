# Media Service

Microservicio para gestión de archivos multimedia (imágenes, videos) con integración a Supabase Storage.

## Características

- Subida y eliminación de archivos a Supabase
- API REST para gestión de media
- Eventos Kafka para notificar cambios
- Health checks
- Base de datos PostgreSQL independiente

## Endpoints

- `GET /api/media/` - Listar todos los archivos
- `POST /api/media/` - Subir nuevo archivo
- `GET /api/media/{id}/` - Obtener archivo por ID
- `PUT/PATCH /api/media/{id}/` - Actualizar archivo
- `DELETE /api/media/{id}/` - Eliminar archivo
- `GET /health/` - Health check
- `GET /health/detailed/` - Health check detallado

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-media:5432/media_db

# Supabase
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_BUCKET=agrovet-profile

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka (opcional)
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
```

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-media redis

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor
python manage.py runserver 0.0.0.0:8001
```

## Despliegue

Ver `docs/deploy.md` para instrucciones completas de despliegue en Kubernetes.

