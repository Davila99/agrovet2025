# Arquitectura Detallada - Microservicios Agrovet

## 📋 Tecnologías Utilizadas

### Backend
- **Django 4.2+**: Framework web para cada microservicio
- **Django REST Framework**: API REST
- **Django Channels**: WebSockets para chat en tiempo real
- **Daphne**: Servidor ASGI para WebSockets
- **Gunicorn**: Servidor WSGI para servicios HTTP

### Base de Datos
- **PostgreSQL 15**: Base de datos relacional (una instancia por servicio)
- **Django ORM**: Mapeo objeto-relacional

### Cache y Mensajería
- **Redis 7**: Cache, sesiones, Channel Layers y presencia online
- **Apache Kafka**: Eventos asíncronos entre servicios
- **Zookeeper**: Coordinación para Kafka

### API Gateway y Load Balancer
- **Traefik v2.12**: API Gateway y reverse proxy

### Contenedores y Orquestación
- **Docker**: Contenedores para cada servicio
- **Docker Compose**: Orquestación local

### Almacenamiento
- **Supabase Storage**: Almacenamiento de archivos multimedia
- **MinIO** (opcional): S3-compatible para desarrollo local

### Comunicación
- **HTTP/REST**: Comunicación síncrona entre servicios
- **WebSockets**: Chat en tiempo real
- **Kafka Events**: Comunicación asíncrona

### Herramientas de Desarrollo
- **drf-yasg**: Documentación OpenAPI/Swagger
- **python-dotenv**: Variables de entorno
- **confluent-kafka**: Cliente Python para Kafka

---

## 🏗️ Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         🌐 INTERNET / CLIENTES                              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                                │
                                │ HTTPS/HTTP
                                │
                ┌───────────────▼───────────────┐
                │   🚦 TRAEFIK API GATEWAY       │
                │   (Load Balancer + Router)     │
                │   Port: 80                     │
                │   Dashboard: 8080              │
                └───────────────┬────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        │                       │                       │
┌───────▼────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│  🔐 AUTH       │    │  📁 MEDIA        │    │  👤 PROFILES     │
│  SERVICE       │    │  SERVICE         │    │  SERVICE         │
│  Port: 8002    │    │  Port: 8001      │    │  Port: 8003      │
│                │    │                  │    │                  │
│  • Login       │    │  • Upload        │    │  • Specialist    │
│  • Register    │    │  • Delete        │    │  • Businessman   │
│  • Reset PWD   │    │  • Get Media     │    │  • Consumer     │
│  • Users CRUD  │    │                  │    │                  │
└───────┬────────┘    └─────────┬────────┘    └────────┬─────────┘
        │                       │                       │
        │                       │                       │
┌───────▼────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│  🛒 MARKETPLACE│    │  💬 CHAT         │    │  📝 FORO         │
│  SERVICE       │    │  SERVICE         │    │  SERVICE         │
│  Port: 8004    │    │  Port: 8006      │    │  Port: 8005      │
│                │    │  (ASGI/Daphne)   │    │                  │
│  • Adds CRUD   │    │  • WebSockets    │    │  • Posts         │
│  • Categories  │    │  • Messages      │    │  • Comments      │
│  • Follow      │    │  • Rooms        │    │  • Reactions     │
│  • Search      │    │  • Presence      │    │  • Communities   │
└───────┬────────┘    └─────────┬────────┘    └────────┬─────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        │                       │                       │
┌───────▼────────┐    ┌─────────▼────────┐    ┌────────▼─────────┐
│  🗄️ POSTGRESQL │    │  ⚡ REDIS        │    │  📨 KAFKA        │
│  DATABASES     │    │  Port: 6379      │    │  Port: 9092      │
│                │    │                  │    │                  │
│  • auth_db     │    │  • Cache         │    │  • Events        │
│  • media_db    │    │  • Sessions      │    │  • Topics        │
│  • profiles_db │    │  • Channel       │    │  • Producers     │
│  • marketplace │    │    Layers        │    │  • Consumers     │
│  • chat_db     │    │  • Presence      │    │                  │
│  • foro_db     │    │                  │    │                  │
└────────────────┘    └──────────────────┘    └────────┬─────────┘
                                                       │
                                              ┌────────▼─────────┐
                                              │  🦘 ZOOKEEPER     │
                                              │  Port: 2181       │
                                              │  (Kafka Coord)    │
                                              └───────────────────┘
```

---

## 🔄 Flujo de Peticiones Detallado

### 1. Flujo de Autenticación

```
👤 Cliente
  │
  │ POST /api/auth/login/
  │ { phone_number, password }
  │
  ▼
🚦 Traefik (auth.localhost)
  │
  │ Route: Host(`auth.localhost`)
  │
  ▼
🔐 Auth Service (8002)
  │
  │ 1. Validar credenciales
  │ 2. Generar Token
  │ 3. Consultar PostgreSQL (auth_db)
  │
  ├─► 🗄️ PostgreSQL (auth_db)
  │
  │ 4. Publicar evento Kafka
  │
  ├─► 📨 Kafka Topic: user.events
  │    Event: user.logged_in
  │
  │ 5. Retornar Token
  │
  ▼
👤 Cliente recibe Token
```

### 2. Flujo de Creación de Perfil

```
👤 Cliente
  │
  │ POST /api/profiles/specialists/
  │ Authorization: Token <token>
  │ { profession, experience_years, ... }
  │
  ▼
🚦 Traefik (profiles.localhost)
  │
  ▼
👤 Profiles Service (8003)
  │
  │ 1. Validar Token
  │
  ├─► 🔐 Auth Service
  │    GET /api/auth/users/me/
  │    Authorization: Token <token>
  │    └─► Retorna: { id, full_name, role, ... }
  │
  │ 2. Crear SpecialistProfile
  │
  ├─► 🗄️ PostgreSQL (profiles_db)
  │    INSERT INTO specialist_profile ...
  │
  │ 3. Publicar evento
  │
  ├─► 📨 Kafka Topic: profiles.events
  │    Event: profile.created
  │    { profile_id, user_id, profile_type: 'specialist' }
  │
  │ 4. Retornar perfil creado
  │
  ▼
👤 Cliente recibe perfil
```

### 3. Flujo de Chat en Tiempo Real

```
👤 Cliente A                    👤 Cliente B
  │                                │
  │ WebSocket                      │ WebSocket
  │ ws://chat.localhost/ws/chat/1/ │ ws://chat.localhost/ws/chat/1/
  │ ?token=<token>                 │ ?token=<token>
  │                                │
  ▼                                ▼
🚦 Traefik                        🚦 Traefik
  │                                │
  ▼                                ▼
💬 Chat Service (8006)            💬 Chat Service (8006)
  │                                │
  │ 1. Validar Token              │ 1. Validar Token
  ├─► 🔐 Auth Service              ├─► 🔐 Auth Service
  │                                │
  │ 2. Conectar WebSocket          │ 2. Conectar WebSocket
  │    - Agregar a grupo: chat_1   │    - Agregar a grupo: chat_1
  │    - Marcar online             │    - Marcar online
  │                                │
  ├─► ⚡ Redis                     ├─► ⚡ Redis
  │    SET chat:online_users       │    SET chat:online_users
  │    ADD user_A                  │    ADD user_B
  │                                │
  │ 3. Enviar mensaje              │
  │    { type: 'chat_message',     │
  │      text: 'Hola!' }           │
  │                                │
  │ 4. Guardar mensaje             │
  ├─► 🗄️ PostgreSQL (chat_db)     │
  │    INSERT INTO chat_message    │
  │                                │
  │ 5. Broadcast vía Channel Layer │
  ├─► ⚡ Redis Channel Layer       │
  │    group_send('chat_1', msg)   │
  │                                │
  │                                │ 6. Recibir mensaje
  │                                │    chat_message handler
  │                                │
  │                                │ 7. Marcar como entregado
  ├─► 🗄️ PostgreSQL (chat_db)      │
  │    UPDATE receipt              │
  │    SET delivered = true        │
  │                                │
  │                                │ 8. Enviar a Cliente B
  │                                ▼
  │                            👤 Cliente B recibe mensaje
  │
  │ 9. Publicar evento
  ├─► 📨 Kafka Topic: chat.events
  │    Event: chat.message.sent
  │
  ▼
👤 Cliente A ve confirmación
```

### 4. Flujo de Eventos Asíncronos (Kafka)

```
🔐 Auth Service
  │
  │ Usuario registrado
  │
  │ publish_event('user.events', 'user.created', {
  │   user_id: 123,
  │   role: 'specialist',
  │   phone_number: '+1234567890'
  │ })
  │
  ▼
📨 Kafka Topic: user.events
  │
  │ Partition 0 ──┐
  │ Partition 1 ──┼──► Consumer Groups
  │ Partition 2 ──┘
  │
  ├─► 👤 Profiles Service Consumer
  │    Group: profiles-service-user-consumer
  │    │
  │    │ Escucha: user.created
  │    │
  │    ├─► Crear SpecialistProfile automáticamente
  │    │
  │    └─► 🗄️ PostgreSQL (profiles_db)
  │         INSERT INTO specialist_profile ...
  │
  ├─► 📝 Foro Service Consumer (futuro)
  │    Group: foro-service-user-consumer
  │    │
  │    └─► Agregar usuario a comunidades por defecto
  │
  └─► Otros servicios...
```

---

## 🚦 Traefik - API Gateway y Load Balancer

### ¿Qué es Traefik?

Traefik es un **reverse proxy** y **load balancer** moderno que funciona como API Gateway. Enrutamiento automático basado en etiquetas Docker.

### Implementación

```yaml
# docker-compose.dev.yml
traefik:
  image: traefik:v2.12
  command:
    - "--api.insecure=true"           # Dashboard en :8080
    - "--providers.docker=true"       # Auto-discovery de servicios
    - "--entrypoints.web.address=:80" # Puerto de entrada
  ports:
    - "80:80"      # HTTP
    - "8080:8080"  # Dashboard
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro
```

### Diagrama de Funcionamiento

```
                    🌐 Cliente
                       │
                       │ HTTP Request
                       │ Host: auth.localhost
                       │
                       ▼
            ┌──────────────────────┐
            │   🚦 TRAEFIK         │
            │   Port: 80            │
            │                       │
            │  ┌────────────────┐  │
            │  │  Entrypoint    │  │
            │  │  :80 (web)     │  │
            │  └────────┬───────┘  │
            │           │           │
            │  ┌────────▼───────┐  │
            │  │  Router Rules   │  │
            │  │                 │  │
            │  │  IF Host =      │  │
            │  │  auth.localhost │  │
            │  │  THEN route to  │  │
            │  │  auth-service   │  │
            │  └────────┬───────┘  │
            │           │           │
            │  ┌────────▼───────┐  │
            │  │  Load Balancer │  │
            │  │  (Round Robin) │  │
            │  └────────┬───────┘  │
            └───────────┼───────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
  ┌─────────┐    ┌─────────┐    ┌─────────┐
  │ Auth    │    │ Auth    │    │ Auth    │
  │ Service │    │ Service │    │ Service │
  │ :8002   │    │ :8002   │    │ :8002   │
  │ (Pod 1) │    │ (Pod 2) │    │ (Pod 3) │
  └─────────┘    └─────────┘    └─────────┘
```

### Routing Rules (Labels Docker)

```yaml
# Cada servicio tiene labels:
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.auth.rule=Host(`auth.localhost`)"
  - "traefik.http.services.auth.loadbalancer.server.port=8002"
```

### Tabla de Rutas

| Host | Servicio | Puerto Interno | Descripción |
|------|----------|----------------|-------------|
| `auth.localhost` | Auth Service | 8002 | Autenticación |
| `media.localhost` | Media Service | 8001 | Archivos multimedia |
| `profiles.localhost` | Profiles Service | 8003 | Perfiles de usuarios |
| `marketplace.localhost` | Marketplace Service | 8004 | Anuncios y catálogo |
| `chat.localhost` | Chat Service | 8006 | Chat en tiempo real |
| `foro.localhost` | Foro Service | 8005 | Foro y comunidades |

---

## ⚡ Redis - Cache y Mensajería

### ¿Qué es Redis?

Redis es una base de datos **en memoria** (in-memory) usada para:
- **Cache**: Almacenar datos frecuentemente accedidos
- **Sesiones**: Almacenar sesiones de usuario
- **Channel Layers**: Para WebSockets (Django Channels)
- **Presencia**: Usuarios online/offline

### Implementación

```yaml
# docker-compose.dev.yml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy volatile-lru
  ports:
    - "6379:6379"
```

### Diagrama de Funcionamiento

```
┌─────────────────────────────────────────────────────────┐
│                    ⚡ REDIS SERVER                      │
│                    Port: 6379                           │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DATABASE 0: Sessions                            │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │ Key: session:abc123                        │ │  │
│  │  │ Value: { user_id: 123, ... }               │ │  │
│  │  │ TTL: 3600s                                 │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  DATABASE 1: Cache                              │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │ Key: cache:user:123                        │ │  │
│  │  │ Value: { full_name: "Juan", ... }         │ │  │
│  │  │ TTL: 300s                                  │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Channel Layers (WebSockets)                     │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │ Key: chat_1                                 │ │  │
│  │  │ Type: SET                                  │ │  │
│  │  │ Members: [channel_A, channel_B, ...]       │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Presence (Online Users)                        │  │
│  │  ┌────────────────────────────────────────────┐ │  │
│  │  │ Key: chat:online_users                     │ │  │
│  │  │ Type: SET                                  │ │  │
│  │  │ Members: [123, 456, 789]                  │ │  │
│  │  └────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
    ┌────┴────┐         ┌────┴────┐         ┌────┴────┐
    │ Auth    │         │ Chat    │         │ Profiles│
    │ Service │         │ Service │         │ Service │
    └─────────┘         └─────────┘         └─────────┘
```

### Uso en Código

```python
# Cache
from django.core.cache import cache

# Guardar
cache.set('user:123', user_data, timeout=300)

# Obtener
user_data = cache.get('user:123')

# Channel Layers (WebSockets)
from channels.layers import get_channel_layer
channel_layer = get_channel_layer()
await channel_layer.group_send('chat_1', {
    'type': 'chat_message',
    'message': 'Hola!'
})

# Presencia
import redis
r = redis.from_url('redis://localhost:6379/0')
r.sadd('chat:online_users', user_id)  # Marcar online
r.srem('chat:online_users', user_id)  # Marcar offline
```

### Persistencia (AOF)

```
Redis Server
  │
  │ --appendonly yes
  │
  ▼
┌─────────────────┐
│  AOF File       │
│  (appendonly.aof)│
│                 │
│  *3              │
│  $3              │
│  SET             │
│  $10             │
│  session:abc123  │
│  $20             │
│  {user_id: 123}  │
└─────────────────┘
```

---

## 📨 Kafka - Eventos Asíncronos

### ¿Qué es Kafka?

Apache Kafka es una plataforma de **streaming de eventos** distribuida. Permite comunicación asíncrona entre servicios mediante **topics** y **partitions**.

### Implementación

```yaml
# docker-compose.dev.yml
zookeeper:
  image: bitnami/zookeeper:latest
  ports:
    - "2181:2181"

kafka:
  image: bitnami/kafka:latest
  environment:
    - KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181
    - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092
    - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
  ports:
    - "9092:9092"
```

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    📨 KAFKA CLUSTER                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  🦘 ZOOKEEPER (Coordinador)                         │   │
│  │  Port: 2181                                         │   │
│  │  • Gestión de brokers                               │   │
│  │  • Liderazgo de particiones                         │   │
│  │  • Configuración                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ▲                                  │
│                          │                                  │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │  📨 KAFKA BROKER                                     │   │
│  │  Port: 9092                                          │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  TOPIC: user.events                          │    │   │
│  │  │  Partitions: 3                               │    │   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐   │    │   │
│  │  │  │Partition │  │Partition │  │Partition │   │    │   │
│  │  │  │    0     │  │    1     │  │    2     │   │    │   │
│  │  │  │          │  │          │  │          │   │    │   │
│  │  │  │[msg 1]   │  │[msg 4]   │  │[msg 7]   │   │    │   │
│  │  │  │[msg 2]   │  │[msg 5]   │  │[msg 8]   │   │    │   │
│  │  │  │[msg 3]   │  │[msg 6]   │  │[msg 9]   │   │    │   │
│  │  │  └──────────┘  └──────────┘  └──────────┘   │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  TOPIC: marketplace.events                    │    │   │
│  │  │  Partitions: 3                                │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                       │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │  TOPIC: chat.events                           │    │   │
│  │  │  Partitions: 3                                │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │                              │
    ┌────┴────┐                    ┌────┴────┐
    │Producer │                    │Consumer │
    │(Auth)   │                    │(Profiles)│
    └─────────┘                    └─────────┘
```

### Flujo de Producción de Eventos

```
🔐 Auth Service
  │
  │ Usuario creado
  │
  │ producer = get_producer()
  │ producer.publish(
  │   topic='user.events',
  │   event_type='user.created',
  │   data={ user_id: 123, role: 'specialist' },
  │   key='123'  # Partition key
  │ )
  │
  ▼
📨 Kafka Producer
  │
  │ 1. Serializar evento a JSON
  │ 2. Seleccionar partition (hash(key) % partitions)
  │ 3. Enviar a Kafka Broker
  │
  ▼
📨 Kafka Broker
  │
  │ 1. Recibir mensaje
  │ 2. Escribir en partition correspondiente
  │ 3. Replicar (si hay replicas)
  │ 4. Confirmar a producer
  │
  ▼
✅ Evento almacenado en topic
```

### Flujo de Consumo de Eventos

```
👤 Profiles Service Consumer
  │
  │ consumer = KafkaEventConsumer(
  │   group_id='profiles-service-user-consumer',
  │   topics=['user.events']
  │ )
  │
  │ consumer.register_handler('user.created', handle_user_created)
  │ consumer.start()  # Loop infinito
  │
  ▼
📨 Kafka Consumer
  │
  │ 1. Conectar a Kafka Broker
  │ 2. Suscribirse a topics
  │ 3. Poll mensajes
  │
  ▼
📨 Kafka Broker
  │
  │ 1. Enviar mensajes del topic
  │ 2. Trackear offset por consumer group
  │
  ▼
👤 Profiles Service
  │
  │ handle_user_created(data):
  │   user_id = data['user_id']
  │   role = data['role']
  │
  │   if role == 'specialist':
  │     SpecialistProfile.objects.create(user_id=user_id)
  │
  ▼
🗄️ PostgreSQL (profiles_db)
  │
  │ INSERT INTO specialist_profile ...
```

### Topics y Eventos

| Topic | Eventos | Producer | Consumers |
|-------|---------|----------|-----------|
| `user.events` | `user.created`, `user.updated`, `user.deleted`, `user.role_changed` | Auth Service | Profiles Service |
| `profile.events` | `profile.created`, `profile.updated` | Profiles Service | - |
| `marketplace.events` | `add.created`, `add.updated`, `add.sold` | Marketplace Service | - |
| `chat.events` | `chat.message.sent`, `chat.room.created` | Chat Service | - |
| `foro.events` | `foro.post.created`, `foro.comment.added`, `foro.reaction.added` | Foro Service | - |
| `media.events` | `media.created`, `media.updated`, `media.deleted` | Media Service | - |

---

## 🗄️ PostgreSQL - Base de Datos

### ¿Qué es PostgreSQL?

PostgreSQL es una base de datos relacional **open-source** y robusta. Usamos **una instancia por servicio** (database per service pattern).

### Implementación

```yaml
# docker-compose.dev.yml
postgres-auth:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=auth_db
    - POSTGRES_USER=agrovet
    - POSTGRES_PASSWORD=agrovet_dev
  ports:
    - "5432:5432"
```

### Diagrama de Bases de Datos

```
┌─────────────────────────────────────────────────────────────┐
│              🗄️ POSTGRESQL INSTANCES                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 auth_db (Port: 5432)                            │   │
│  │  ┌──────────────┐  ┌──────────────┐                 │   │
│  │  │ auth_user    │  │phone_reset_  │                 │   │
│  │  │              │  │code          │                 │   │
│  │  │ • id         │  │              │                 │   │
│  │  │ • phone_num  │  │ • id         │                 │   │
│  │  │ • password   │  │ • user_id    │                 │   │
│  │  │ • role       │  │ • code       │                 │   │
│  │  │ • full_name  │  │ • expires_at │                 │   │
│  │  └──────────────┘  └──────────────┘                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 profiles_db (Port: 5433)                         │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │specialist_   │  │businessman_  │  │consumer_    │ │   │
│  │  │profile       │  │profile      │  │profile      │ │   │
│  │  │              │  │              │  │             │ │   │
│  │  │ • id         │  │ • id         │  │ • id        │ │   │
│  │  │ • user_id    │  │ • user_id    │  │ • user_id   │ │   │
│  │  │ • profession │  │ • business_  │  │             │ │   │
│  │  │ • experience │  │   name       │  │             │ │   │
│  │  │ • work_      │  │ • products_  │  │             │ │   │
│  │  │   images_ids │  │   ids        │  │             │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 marketplace_db (Port: 5434)                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │ add          │  │ category    │  │ follow      │ │   │
│  │  │              │  │             │  │             │ │   │
│  │  │ • id         │  │ • id         │  │ • id        │ │   │
│  │  │ • publisher_ │  │ • name       │  │ • follower_ │ │   │
│  │  │   id         │  │ • description│  │   id       │ │   │
│  │  │ • title      │  │             │  │ • following_ │ │   │
│  │  │ • price      │  │             │  │   id        │ │   │
│  │  │ • main_      │  │             │  │             │ │   │
│  │  │   image_id   │  │             │  │             │ │   │
│  │  │ • secondary_ │  │             │  │             │ │   │
│  │  │   image_ids  │  │             │  │             │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 chat_db (Port: 5435)                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │ chat_room    │  │chat_message  │  │chat_message │ │   │
│  │  │              │  │              │  │_receipt     │ │   │
│  │  │ • id         │  │ • id         │  │             │ │   │
│  │  │ • name       │  │ • room_id    │  │ • id        │ │   │
│  │  │ • participants│ │ • sender_id  │  │ • message_id│ │   │
│  │  │   _ids       │  │ • content    │  │ • user_id   │ │   │
│  │  │ • is_private │  │ • media_id  │  │ • delivered │ │   │
│  │  └──────────────┘  └──────────────┘  │ • read      │ │   │
│  │                                       └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 foro_db (Port: 5437)                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │   │
│  │  │ post         │  │ comment      │  │ reaction    │ │   │
│  │  │              │  │              │  │             │ │   │
│  │  │ • id         │  │ • id         │  │ • id        │ │   │
│  │  │ • author_id  │  │ • user_id    │  │ • user_id   │ │   │
│  │  │ • title      │  │ • post_id    │  │ • type      │ │   │
│  │  │ • content    │  │ • parent_id  │  │ • content_  │ │   │
│  │  │ • media_id   │  │ • content    │  │   type      │ │   │
│  │  │ • community_ │  │ • media_id   │  │ • object_id │ │   │
│  │  │   id         │  │              │  │             │ │   │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  📊 media_db (Port: 5436)                            │   │
│  │  ┌──────────────┐                                    │   │
│  │  │ media        │                                    │   │
│  │  │              │                                    │   │
│  │  │ • id         │                                    │   │
│  │  │ • name       │                                    │   │
│  │  │ • url        │                                    │   │
│  │  │ • description│                                    │   │
│  │  │ • price      │                                    │   │
│  │  │ • content_   │                                    │   │
│  │  │   type_id    │                                    │   │
│  │  │ • object_id  │                                    │   │
│  │  └──────────────┘                                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Conexión desde Servicios

```python
# settings.py de cada servicio
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'auth_db'),
        'USER': os.getenv('DB_USER', 'agrovet'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'agrovet_dev'),
        'HOST': os.getenv('DB_HOST', 'postgres-auth'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

---

## 🐳 Docker Compose - Orquestación Local

### ¿Qué es Docker Compose?

Docker Compose permite definir y ejecutar **múltiples contenedores Docker** como una aplicación única.

### Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              🐳 DOCKER COMPOSE                              │
│              docker-compose.dev.yml                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  🌐 NETWORK: agrovet-network                        │   │
│  │  Driver: bridge                                      │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ 🚦 Traefik   │  │ ⚡ Redis     │  │ 📨 Kafka   │ │   │
│  │  │ Container    │  │ Container    │  │ Container  │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Port: 80     │  │ Port: 6379   │  │ Port: 9092 │ │   │
│  │  │ :8080        │  │              │  │            │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ 🔐 Auth      │  │ 📁 Media     │  │ 👤 Profiles│ │   │
│  │  │ Service      │  │ Service      │  │ Service    │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Port: 8002   │  │ Port: 8001   │  │ Port: 8003 │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Volumes:     │  │ Volumes:     │  │ Volumes:   │ │   │
│  │  │ - ./services │  │ - ./services │  │ - ./services│ │   │
│  │  │ - ./common   │  │ - ./common   │  │ - ./common │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ 🛒 Marketplace│  │ 💬 Chat      │  │ 📝 Foro    │ │   │
│  │  │ Service      │  │ Service      │  │ Service    │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Port: 8004   │  │ Port: 8006   │  │ Port: 8005 │ │   │
│  │  └──────────────┘  └──────────────┘  └────────────┘ │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │   │
│  │  │ 🗄️ PostgreSQL│  │ 🗄️ PostgreSQL│  │ 🗄️ PostgreSQL│ │   │
│  │  │ auth_db      │  │ media_db     │  │ profiles_db │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Port: 5432   │  │ Port: 5436   │  │ Port: 5433 │ │   │
│  │  │              │  │              │  │            │ │   │
│  │  │ Volume:      │  │ Volume:      │  │ Volume:    │ │   │
│  │  │ postgres_    │  │ postgres_    │  │ postgres_  │ │   │
│  │  │ auth_data    │  │ media_data   │  │ profiles_  │ │   │
│  │  └──────────────┘  └──────────────┘  │ data       │ │   │
│  │                                       └────────────┘ │   │
│  │  ... (más PostgreSQL containers)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  💾 VOLUMES (Persistent Storage)                     │   │
│  │  • redis-data                                         │   │
│  │  • postgres-auth-data                                 │   │
│  │  • postgres-media-data                                │   │
│  │  • postgres-profiles-data                             │   │
│  │  • postgres-marketplace-data                          │   │
│  │  • postgres-chat-data                                 │   │
│  │  • postgres-foro-data                                 │   │
│  │  • kafka-data                                         │   │
│  │  • zookeeper-data                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Comandos

```bash
# Levantar todos los servicios
docker-compose -f docker-compose.dev.yml up

# Levantar en background
docker-compose -f docker-compose.dev.yml up -d

# Ver logs
docker-compose -f docker-compose.dev.yml logs -f auth-service

# Detener servicios
docker-compose -f docker-compose.dev.yml down

# Reconstruir un servicio
docker-compose -f docker-compose.dev.yml build auth-service
docker-compose -f docker-compose.dev.yml up auth-service
```

---

## 🔗 Comunicación Entre Servicios

### HTTP/REST (Síncrono)

```
👤 Profiles Service
  │
  │ Necesita información del usuario
  │
  │ auth_client = get_auth_client()
  │ user = auth_client.get_user(user_id=123)
  │
  │ HTTP GET http://auth-service:8002/api/auth/users/123/
  │ Headers: { Authorization: 'Token <token>' }
  │
  ▼
🔐 Auth Service
  │
  │ 1. Validar token
  │ 2. Consultar PostgreSQL (auth_db)
  │ 3. Retornar datos del usuario
  │
  │ HTTP 200 OK
  │ { id: 123, full_name: "Juan", role: "specialist", ... }
  │
  ▼
👤 Profiles Service
  │
  │ Usa datos del usuario para crear perfil
```

### Kafka Events (Asíncrono)

```
🔐 Auth Service
  │
  │ Usuario registrado
  │
  │ producer = get_producer()
  │ producer.publish(
  │   topic='user.events',
  │   event_type='user.created',
  │   data={ user_id: 123, role: 'specialist' }
  │ )
  │
  │ ✅ No espera respuesta
  │ ✅ Continúa ejecución
  │
  ▼
📨 Kafka Broker
  │
  │ Almacena evento en topic
  │
  ▼
👤 Profiles Service Consumer
  │
  │ Escucha topic: user.events
  │
  │ Cuando recibe 'user.created':
  │   - Crea SpecialistProfile automáticamente
  │   - No necesita llamar a Auth Service
```

### WebSockets (Tiempo Real)

```
👤 Cliente A                    👤 Cliente B
  │                                │
  │ WebSocket                      │ WebSocket
  │ ws://chat.localhost/ws/chat/1/ │ ws://chat.localhost/ws/chat/1/
  │                                │
  ▼                                ▼
💬 Chat Service                    💬 Chat Service
  │                                │
  │ Conectado a grupo: chat_1      │ Conectado a grupo: chat_1
  │                                │
  │ Envía mensaje                  │
  │                                │
  ├─► ⚡ Redis Channel Layer       │
  │    group_send('chat_1', msg)   │
  │                                │
  │                                │ Recibe mensaje
  │                                │
  │                                ▼
  │                            👤 Cliente B recibe mensaje
```

---

## 📊 Resumen de Puertos

| Servicio | Puerto | Protocolo | Descripción |
|----------|--------|-----------|-------------|
| Traefik | 80 | HTTP | API Gateway |
| Traefik Dashboard | 8080 | HTTP | Panel de administración |
| Auth Service | 8002 | HTTP | Autenticación |
| Media Service | 8001 | HTTP | Archivos multimedia |
| Profiles Service | 8003 | HTTP | Perfiles de usuarios |
| Marketplace Service | 8004 | HTTP | Anuncios |
| Foro Service | 8005 | HTTP | Foro |
| Chat Service | 8006 | WebSocket/HTTP | Chat en tiempo real |
| PostgreSQL (auth) | 5432 | TCP | Base de datos auth |
| PostgreSQL (media) | 5436 | TCP | Base de datos media |
| PostgreSQL (profiles) | 5433 | TCP | Base de datos profiles |
| PostgreSQL (marketplace) | 5434 | TCP | Base de datos marketplace |
| PostgreSQL (chat) | 5435 | TCP | Base de datos chat |
| PostgreSQL (foro) | 5437 | TCP | Base de datos foro |
| Redis | 6379 | TCP | Cache y sesiones |
| Kafka | 9092 | TCP | Eventos |
| Zookeeper | 2181 | TCP | Coordinación Kafka |
| MinIO | 9000 | HTTP | S3 API |
| MinIO Console | 9001 | HTTP | Panel MinIO |

---

## 🎯 Patrones de Arquitectura Implementados

### 1. Database per Service
Cada microservicio tiene su propia base de datos PostgreSQL independiente.

### 2. API Gateway
Traefik actúa como punto de entrada único para todos los servicios.

### 3. Event-Driven Architecture
Kafka permite comunicación asíncrona entre servicios mediante eventos.

### 4. Strangler Pattern
Los servicios pueden ejecutarse en paralelo con el monolito durante la migración.

### 5. CQRS (Command Query Responsibility Segregation)
Separación entre comandos (escritura) y queries (lectura) en diferentes endpoints.

### 6. Circuit Breaker (implícito)
Los servicios manejan errores cuando otros servicios no están disponibles.

---

## 📝 Notas Finales

- **Escalabilidad**: Cada servicio puede escalarse independientemente
- **Resiliencia**: Si un servicio falla, los demás continúan funcionando
- **Desarrollo**: Cada servicio puede desarrollarse y desplegarse independientemente
- **Testing**: Cada servicio puede probarse de forma aislada
- **Tecnología**: Cada servicio puede usar diferentes tecnologías si es necesario

---

**Última actualización**: 2025-01-XX
**Versión**: 1.0.0

