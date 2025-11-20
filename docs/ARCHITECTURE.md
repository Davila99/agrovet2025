# Arquitectura de Microservicios - Agrovet2025

## Resumen Ejecutivo

Este documento describe la arquitectura de microservicios propuesta para migrar el monolito Django actual a una arquitectura distribuida escalable.

## Arquitectura de Alto Nivel

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Traefik)                     │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│  Auth Service  │  │ Media Service  │  │Profile Service │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│ Marketplace    │  │  Chat Service  │  │ Foro Service   │
│   Service      │  │                │  │                │
└────────────────┘  └────────────────┘  └────────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌───────▼────────┐
│   PostgreSQL   │  │     Redis       │  │     Kafka      │
│  (per service) │  │  (Cache/Session)│  │   (Events)     │
└────────────────┘  └────────────────┘  └────────────────┘
```

## Microservicios

### 1. Auth Service (`auth-service`)
**Responsabilidad**: Autenticación, autorización, gestión de usuarios, tokens JWT/OAuth2.

**Tecnología**: Django REST Framework
**Base de Datos**: PostgreSQL (`auth_db`)
**Endpoints principales**:
- `POST /api/auth/register/` - Registro de usuarios
- `POST /api/auth/login/` - Login y obtención de token
- `POST /api/auth/logout/` - Logout
- `GET /api/auth/me/` - Información del usuario actual

**Eventos Kafka**:
- `user.created` - Usuario creado
- `user.updated` - Usuario actualizado
- `user.deleted` - Usuario eliminado

### 2. Media Service (`media-service`)
**Responsabilidad**: Subida, almacenamiento y gestión de archivos multimedia (imágenes, videos).

**Tecnología**: Django REST Framework + Supabase Storage
**Base de Datos**: PostgreSQL (`media_db`)
**Endpoints principales**:
- `GET /api/media/` - Listar archivos
- `POST /api/media/` - Subir archivo
- `GET /api/media/{id}/` - Obtener archivo
- `DELETE /api/media/{id}/` - Eliminar archivo

**Eventos Kafka**:
- `media.created` - Archivo subido
- `media.deleted` - Archivo eliminado

### 3. Profiles Service (`profiles-service`)
**Responsabilidad**: Gestión de perfiles de usuarios (Specialist, Businessman, Consumer).

**Tecnología**: Django REST Framework
**Base de Datos**: PostgreSQL (`profiles_db`)
**Dependencias**: Auth Service (via HTTP/gRPC), Media Service (via eventos)
**Endpoints principales**:
- `GET /api/profiles/specialists/` - Listar especialistas
- `POST /api/profiles/specialists/` - Crear perfil especialista
- `GET /api/profiles/businessmen/` - Listar empresarios
- `POST /api/profiles/businessmen/` - Crear perfil empresario

**Eventos Kafka**:
- `profile.created` - Perfil creado
- `profile.updated` - Perfil actualizado

### 4. Marketplace Service (`marketplace-service`)
**Responsabilidad**: Gestión de anuncios, catálogo de productos, órdenes.

**Tecnología**: Django REST Framework
**Base de Datos**: PostgreSQL (`marketplace_db`)
**Dependencias**: Auth Service, Media Service
**Endpoints principales**:
- `GET /api/adds/` - Listar anuncios
- `POST /api/adds/` - Crear anuncio
- `GET /api/adds/{id}/` - Detalle de anuncio
- `POST /api/adds/{id}/purchase/` - Comprar producto

**Eventos Kafka**:
- `add.created` - Anuncio creado
- `add.updated` - Anuncio actualizado
- `add.sold` - Producto vendido

### 5. Chat Service (`chat-service`)
**Responsabilidad**: Chat en tiempo real, mensajería, WebSockets.

**Tecnología**: Django Channels + WebSockets
**Base de Datos**: PostgreSQL (`chat_db`)
**Dependencias**: Auth Service, Media Service
**Endpoints principales**:
- `GET /api/chat/rooms/` - Listar salas
- `POST /api/chat/rooms/` - Crear sala
- `GET /api/chat/rooms/{id}/messages/` - Mensajes de sala
- WebSocket: `ws://chat-service/ws/chat/{room_id}/`

**Eventos Kafka**:
- `chat.message.sent` - Mensaje enviado
- `chat.room.created` - Sala creada

### 6. Foro Service (`foro-service`)
**Responsabilidad**: Foro tipo Reddit, posts, comentarios, reacciones, comunidades.

**Tecnología**: Django REST Framework
**Base de Datos**: PostgreSQL (`foro_db`)
**Dependencias**: Auth Service, Media Service
**Endpoints principales**:
- `GET /api/foro/posts/` - Listar posts
- `POST /api/foro/posts/` - Crear post
- `GET /api/foro/posts/{id}/comments/` - Comentarios de post
- `POST /api/foro/posts/{id}/react/` - Reaccionar a post

**Eventos Kafka**:
- `foro.post.created` - Post creado
- `foro.comment.added` - Comentario agregado
- `foro.reaction.added` - Reacción agregada

## Infraestructura

### API Gateway
- **Traefik**: Enrutamiento, load balancing, SSL termination
- Configuración mediante labels Docker o IngressRoute (Kubernetes)

### Message Broker
- **Kafka**: Eventos asíncronos entre servicios
- Topics por dominio: `user.events`, `marketplace.events`, `media.events`, `chat.events`, `foro.events`
- Replicación: 2-3 réplicas según entorno

### Cache y Sesiones
- **Redis**: Cache distribuido y almacenamiento de sesiones
- Configuración:
  - Persistencia AOF habilitada
  - Max memory policy: `volatile-lru`
  - Namespaces por servicio para evitar conflictos

### Bases de Datos
- **PostgreSQL**: Una instancia por servicio (DB per service)
- Configuración:
  - Connection pooling (PgBouncer recomendado)
  - Backups automáticos
  - Replicación en producción

### Storage
- **Supabase Storage**: Almacenamiento de archivos multimedia
- Alternativa local: MinIO (S3-compatible)

## Comunicación entre Servicios

### Síncrona (HTTP/gRPC)
- Autenticación: Auth Service valida tokens
- Consultas directas: Profiles Service consulta usuarios a Auth Service

### Asíncrona (Eventos Kafka)
- Eventos de dominio: User created, Media uploaded, Order placed
- Desacoplamiento: Servicios se comunican vía eventos sin conocer implementación

## Seguridad

- **Autenticación**: JWT tokens emitidos por Auth Service
- **Autorización**: Cada servicio valida tokens independientemente
- **TLS**: HTTPS obligatorio en producción
- **Secrets**: Kubernetes Secrets o HashiCorp Vault
- **mTLS**: Opcional entre servicios en producción

## Observabilidad

- **Métricas**: Prometheus + Grafana
- **Logs**: Loki + Fluentd
- **Tracing**: Jaeger para requests distribuidos
- **Health Checks**: Endpoint `/health/` en cada servicio

## Escalabilidad

- **Horizontal**: Cada servicio puede escalarse independientemente
- **Auto-scaling**: Kubernetes HPA basado en CPU/memoria
- **Load Balancing**: Traefik distribuye carga entre réplicas

## Estrategia de Migración

1. **Fase 1**: Extraer servicios read-only (Media, Foro)
2. **Fase 2**: Extraer servicios con dependencias simples (Profiles)
3. **Fase 3**: Extraer servicios complejos (Marketplace, Chat)
4. **Fase 4**: Migrar Auth Service (crítico)
5. **Fase 5**: Desactivar monolito gradualmente

Ver `docs/MIGRATION.md` para detalles.

