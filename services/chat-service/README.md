# Chat Service

Microservicio para chat en tiempo real con WebSockets (Django Channels).

## Características

- Chat en tiempo real con WebSockets
- CRUD de salas de chat (ChatRoom)
- CRUD de mensajes (ChatMessage)
- Sistema de receipts (entregado/leído)
- Presencia online/offline
- Integración con Auth Service y Media Service
- Eventos Kafka

## Endpoints REST

- `GET /api/chat/rooms/` - Listar salas
- `POST /api/chat/rooms/` - Crear sala
- `GET /api/chat/rooms/{id}/` - Detalle de sala
- `POST /api/chat/rooms/get_or_create_private/` - Crear sala privada
- `GET /api/chat/messages/` - Listar mensajes
- `POST /api/chat/messages/` - Crear mensaje
- `GET /api/chat/messages/last_messages/` - Últimos mensajes de una sala
- `POST /api/chat/messages/mark_read/` - Marcar mensajes como leídos
- `GET /health/` - Health check

## WebSockets

- `ws://chat-service/ws/chat/{room_id}/?token=<token>` - Chat en tiempo real
- `ws://chat-service/ws/presence/?token=<token>` - Presencia online/offline

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-chat:5432/chat_db

# Auth Service
AUTH_SERVICE_URL=http://auth-service:8002

# Media Service
MEDIA_SERVICE_URL=http://media-service:8001

# Redis (para Channel Layers y presencia)
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
```

## Eventos Kafka Publicados

- `chat.message.sent` - Mensaje enviado
- `chat.room.created` - Sala creada

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-chat redis kafka

# Ejecutar migraciones
python manage.py migrate

# Ejecutar servidor ASGI (requerido para WebSockets)
daphne -b 0.0.0.0 -p 8006 chat_service.asgi:application
```

## Notas

- Este servicio requiere ASGI (no WSGI) para WebSockets
- Usa Django Channels con Redis Channel Layers
- Los tokens de autenticación se validan con Auth Service

