# Funcionalidades Completas - Migración a Microservicios

Este documento lista TODAS las funcionalidades del monolito original y su estado de migración.

## ✅ Funcionalidades Migradas

### Auth Service ✅
- ✅ Registro de usuarios con validación de phone_number
- ✅ Login con autenticación por token
- ✅ Reset de contraseña por SMS (Twilio)
- ✅ CRUD completo de usuarios
- ✅ Subida de imágenes de perfil a Supabase
- ✅ Eliminación automática de imágenes al borrar usuario
- ✅ Validación de roles (Specialist, businessman, consumer)
- ✅ Búsqueda de usuarios
- ✅ Bearer token authentication
- ✅ Eventos Kafka: user.created, user.updated, user.deleted, user.password_reset

### Media Service ✅
- ✅ CRUD completo de Media
- ✅ Subida de archivos a Supabase Storage
- ✅ Eliminación de archivos de Supabase
- ✅ Generic relations (content_type/object_id)
- ✅ Validación de content_type
- ✅ Eventos Kafka: media.created, media.updated, media.deleted

## ⏳ Funcionalidades Pendientes de Migrar

### Profiles Service ✅
**Funcionalidades del monolito**:
- [x] SpecialistProfile CRUD completo
- [x] BusinessmanProfile CRUD completo
- [x] ConsumerProfile CRUD completo
- [x] Upload de work_images para SpecialistProfile
- [x] Upload de products_and_services para BusinessmanProfile
- [x] Endpoint `by-user/{user_id}` para obtener perfil por usuario
- [x] Validación: un usuario solo puede tener un tipo de perfil
- [x] Sincronización automática: crear perfil al crear usuario según role (vía Kafka Consumer)
- [x] Sincronización de role: actualizar role del usuario al crear perfil

**Integraciones implementadas**:
- [x] HTTP Client para Auth Service (obtener usuarios)
- [x] HTTP Client para Media Service (obtener media)
- [x] Kafka Consumer para escuchar `user.created` y crear perfiles automáticamente
- [x] Kafka Producer para publicar `profile.created`, `profile.updated`

### Marketplace Service (Add) ✅
**Funcionalidades del monolito**:
- [x] Add CRUD completo
- [x] Category CRUD completo
- [x] Follow CRUD (seguir/dejar de seguir usuarios)
- [x] Endpoint `my_adds` - anuncios del usuario autenticado
- [x] Endpoint `following_adds` - anuncios de usuarios seguidos
- [x] Endpoint `nearby` - anuncios cercanos por geolocalización
- [x] Filtros: por categoría, condición, estado
- [x] Búsqueda: por título y descripción
- [x] Ordenamiento: por fecha, precio
- [x] Validación: máximo 4 imágenes secundarias
- [x] Relación con Media (main_image_id, secondary_image_ids)

**Integraciones implementadas**:
- [x] HTTP Client para Auth Service (validar usuarios)
- [x] HTTP Client para Media Service (obtener/crear media)
- [x] Kafka Producer para publicar `add.created`, `add.updated`

### Chat Service ✅
**Funcionalidades del monolito**:
- [x] ChatRoom CRUD completo
- [x] ChatMessage CRUD completo
- [x] ChatMessageReceipt CRUD (tracking de entregas/lecturas)
- [x] WebSockets para chat en tiempo real (Django Channels)
- [x] Función `get_or_create_private_chat` - crear sala privada entre 2 usuarios
- [x] Endpoint `get_or_create_private` - API helper para crear sala privada
- [x] Endpoint `last_messages` - últimos N mensajes de una sala
- [x] Endpoint `mark_read` - marcar mensajes como leídos
- [x] Broadcast de mensajes vía Channel Layer
- [x] Presencia online/offline
- [x] Soporte para media en mensajes
- [x] Actualización automática de last_activity en ChatRoom

**Integraciones implementadas**:
- [x] HTTP Client para Auth Service (validar usuarios)
- [x] HTTP Client para Media Service (obtener/crear media)
- [x] Redis Channel Layer para WebSockets
- [x] Kafka Producer para publicar `chat.message.sent`, `chat.room.created`

### Foro Service ✅
**Funcionalidades del monolito**:
- [x] Post CRUD completo
- [x] Comment CRUD completo (con respuestas anidadas)
- [x] Reaction CRUD completo (heart, like, dislike)
- [x] Notification CRUD completo
- [x] Community CRUD completo
- [x] Endpoint `relevant` - posts relevantes personalizados (algoritmo de relevancia)
- [x] Endpoint `join/leave` - unirse/salir de comunidades
- [x] Endpoint `upload_cover` - subir imagen de portada de comunidad
- [x] Endpoint `upload_avatar` - subir avatar de comunidad
- [x] Algoritmo de relevancia: boost por interacciones, decay temporal
- [x] Contadores: views_count, reactions_count, replies_count, members_count
- [x] Notificaciones automáticas: post_reply, comment_reply, post_reaction, comment_reaction
- [x] Sincronización automática de members_count

**Integraciones implementadas**:
- [x] HTTP Client para Auth Service (validar usuarios)
- [x] HTTP Client para Media Service (obtener/crear media)
- [x] Kafka Producer para publicar `foro.post.created`, `foro.comment.added`, `foro.reaction.added`

## 🔧 Funcionalidades de Infraestructura

### Completadas ✅
- [x] Docker Compose para desarrollo local
- [x] Health checks en todos los servicios
- [x] Kafka producer/consumer base
- [x] Redis con namespaces
- [x] HTTP clients para comunicación entre servicios
- [x] Scripts para crear topics Kafka

### Pendientes
- [ ] Scripts de migración ETL para cada servicio
- [ ] Kubernetes manifests completos
- [ ] Helm charts
- [ ] GitHub Actions workflows para todos los servicios
- [ ] Prometheus metrics
- [ ] Jaeger tracing
- [ ] Logs estructurados JSON

## 📊 Resumen de Cobertura

| Servicio | Funcionalidades | Estado |
|----------|----------------|--------|
| Auth Service | 10/10 | ✅ 100% |
| Media Service | 6/6 | ✅ 100% |
| Profiles Service | 9/9 | ✅ 100% |
| Marketplace Service | 12/12 | ✅ 100% |
| Chat Service | 15/15 | ✅ 100% |
| Foro Service | 15/15 | ✅ 100% |
| **Total** | **67/67** | **✅ 100%** |

## 🎯 Prioridades

1. **Alta**: Profiles Service (depende de Auth, otros servicios lo necesitan)
2. **Alta**: Marketplace Service (funcionalidad core del negocio)
3. **Media**: Chat Service (requiere WebSockets, más complejo)
4. **Media**: Foro Service (similar a Marketplace en complejidad)
5. **Baja**: Infraestructura adicional (observability, etc.)

## 📝 Notas de Implementación

### Profiles Service
- Necesita escuchar eventos `user.created` de Auth Service
- Debe crear perfiles automáticamente según el role del usuario
- Debe sincronizar el role del usuario cuando se crea un perfil

### Marketplace Service
- Necesita validar que el publisher existe en Auth Service
- Debe obtener información de media desde Media Service
- Puede usar eventos para sincronización eventual

### Chat Service
- Requiere Django Channels y Redis Channel Layers
- WebSockets deben autenticarse con tokens de Auth Service
- Necesita mantener estado de presencia en Redis

### Foro Service
- Algoritmo de relevancia requiere datos de interacciones
- Notificaciones pueden enviarse vía eventos Kafka
- Comunidades pueden sincronizarse con Auth Service para miembros

