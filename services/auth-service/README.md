# Auth Service

Microservicio de autenticación y gestión de usuarios. Servicio crítico del que dependen otros servicios.

## Características

- Registro y login de usuarios
- Tokens de autenticación (Django Token Auth)
- Reset de contraseña por SMS (Twilio)
- Gestión de perfiles de usuario
- Subida de imágenes de perfil a Supabase
- Eventos Kafka para sincronización con otros servicios

## Endpoints

- `POST /api/auth/register/` - Registro de usuario
- `POST /api/auth/login/` - Login y obtención de token
- `GET /api/auth/users/` - Listar usuarios (autenticado)
- `GET /api/auth/users/{id}/` - Detalle de usuario
- `PUT/PATCH /api/auth/users/{id}/` - Actualizar usuario
- `DELETE /api/auth/users/{id}/` - Eliminar usuario
- `POST /api/auth/upload-profile-picture/` - Subir imagen de perfil
- `POST /api/auth/password-reset/request/` - Solicitar reset por SMS
- `POST /api/auth/password-reset/verify/` - Verificar código y resetear
- `GET /health/` - Health check

## Variables de Entorno

```bash
# Database
DATABASE_URL=postgresql://agrovet:password@postgres-auth:5432/auth_db

# Supabase
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-key
SUPABASE_BUCKET=agrovet-profile

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# Twilio (opcional, para SMS)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-phone-number

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=*
```

## Eventos Kafka Publicados

- `user.created` - Usuario creado
- `user.updated` - Usuario actualizado
- `user.deleted` - Usuario eliminado

## Desarrollo Local

```bash
# Con docker-compose
docker-compose -f docker-compose.dev.yml up postgres-auth redis kafka

# Ejecutar migraciones
python manage.py migrate

# Crear superuser
python manage.py createsuperuser

# Ejecutar servidor
python manage.py runserver 0.0.0.0:8002
```

