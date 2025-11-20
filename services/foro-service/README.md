# Foro Service

Microservicio para gestión de foro tipo Reddit: posts, comentarios, reacciones, comunidades y notificaciones.

## Características

- CRUD completo de posts
- Comentarios anidados (respuestas)
- Sistema de reacciones (heart, like, dislike)
- Comunidades (grupos temáticos)
- Notificaciones automáticas
- Algoritmo de relevancia personalizado
- Integración con Auth Service y Media Service
- Eventos Kafka

## Endpoints

- `GET /api/foro/posts/` - Listar posts
- `POST /api/foro/posts/` - Crear post
- `GET /api/foro/posts/{id}/` - Detalle de post
- `GET /api/foro/posts/relevant/` - Posts relevantes personalizados
- `GET /api/foro/comments/` - Listar comentarios
- `POST /api/foro/comments/` - Crear comentario
- `POST /api/foro/reactions/` - Agregar reacción
- `GET /api/foro/communities/` - Listar comunidades
- `POST /api/foro/communities/{id}/join/` - Unirse a comunidad
- `POST /api/foro/communities/{id}/leave/` - Salir de comunidad
- `GET /health/` - Health check

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-foro:5432/foro_db

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

## Eventos Kafka Publicados

- `foro.post.created` - Post creado
- `foro.comment.added` - Comentario agregado
- `foro.reaction.added` - Reacción agregada

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-foro redis kafka

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor
python manage.py runserver 0.0.0.0:8005
```

