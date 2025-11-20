# Marketplace Service

Microservicio para gestión de anuncios, catálogo de productos y seguimiento de usuarios.

## Características

- CRUD completo de anuncios (Add)
- CRUD de categorías
- Sistema de seguimiento (Follow)
- Búsqueda y filtros avanzados
- Anuncios cercanos por geolocalización
- Integración con Auth Service y Media Service
- Eventos Kafka

## Endpoints

- `GET /api/adds/` - Listar anuncios
- `POST /api/adds/` - Crear anuncio
- `GET /api/adds/{id}/` - Detalle de anuncio
- `PUT/PATCH /api/adds/{id}/` - Actualizar anuncio
- `DELETE /api/adds/{id}/` - Eliminar anuncio
- `GET /api/adds/my_adds/` - Mis anuncios
- `GET /api/adds/following_adds/` - Anuncios de usuarios seguidos
- `GET /api/adds/nearby/` - Anuncios cercanos
- `GET /api/adds/categories/` - Listar categorías
- `POST /api/adds/follows/` - Seguir usuario
- `DELETE /api/adds/follows/{id}/` - Dejar de seguir
- `GET /health/` - Health check

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-marketplace:5432/marketplace_db

# Auth Service
AUTH_SERVICE_URL=http://auth-service:8002

# Media Service
MEDIA_SERVICE_URL=http://media-service:8001

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
```

## Eventos Kafka Publicados

- `add.created` - Anuncio creado
- `add.updated` - Anuncio actualizado
- `add.sold` - Producto vendido

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-marketplace redis kafka

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor
python manage.py runserver 0.0.0.0:8004
```

