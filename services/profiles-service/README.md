# Profiles Service

Microservicio para gestión de perfiles de usuarios (Specialist, Businessman, Consumer).

## Características

- CRUD completo de perfiles especializados
- Integración con Auth Service (HTTP) para obtener usuarios
- Integración con Media Service (HTTP) para obtener media
- Escucha eventos `user.created` de Auth Service para crear perfiles automáticamente
- Eventos Kafka para sincronización

## Endpoints

- `GET /api/profiles/specialists/` - Listar especialistas
- `POST /api/profiles/specialists/` - Crear perfil especialista
- `GET /api/profiles/specialists/{id}/` - Detalle de especialista
- `GET /api/profiles/specialists/by-user/{user_id}/` - Perfil por usuario
- `POST /api/profiles/specialists/{id}/upload_work_images/` - Subir imágenes de trabajo
- `GET /api/profiles/businessmen/` - Listar empresarios
- `POST /api/profiles/businessmen/` - Crear perfil empresario
- `GET /api/profiles/consumers/` - Listar consumidores
- `GET /health/` - Health check

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-profiles:5432/profiles_db

# Auth Service
AUTH_SERVICE_URL=http://auth-service:8002

# Media Service
MEDIA_SERVICE_URL=http://media-service:8001

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Supabase
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_BUCKET=agrovet-profile

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
```

## Eventos Kafka

**Escucha**:
- `user.created` - Crea perfil automáticamente según role

**Publica**:
- `profile.created` - Perfil creado
- `profile.updated` - Perfil actualizado

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-profiles redis kafka

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor
python manage.py runserver 0.0.0.0:8003
```

