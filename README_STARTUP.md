# 🚀 Agrovet2025 - Guía de Inicio Rápido

Esta guía te ayudará a levantar todo el entorno de desarrollo (backend + frontend) con un solo comando.

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

- **Docker Desktop** (versión 20.10 o superior)
- **Node.js** (versión 18 o superior)
- **npm** (incluido con Node.js)

### Verificar instalaciones

```powershell
# Verificar Docker
docker --version

# Verificar Node.js
node --version

# Verificar npm
npm --version
```

## 🎯 Inicio Rápido

### Iniciar todo el entorno

Ejecuta el siguiente comando en la raíz del proyecto:

```powershell
.\start-dev.ps1
```

Este script hará lo siguiente:
1. ✅ Verificar que Docker esté corriendo
2. ✅ Verificar que Node.js esté instalado
3. ✅ Iniciar todos los microservicios del backend (vía Docker Compose)
4. ✅ Esperar a que los servicios estén saludables
5. ✅ Instalar dependencias del frontend (si es necesario)
6. ✅ Iniciar el servidor de desarrollo del frontend

### Detener todo el entorno

```powershell
.\stop-dev.ps1
```

Para detener el frontend, presiona `Ctrl+C` en la terminal donde está corriendo.

## 🌐 URLs de los Servicios

Una vez que todo esté corriendo, podrás acceder a:

### Frontend
- **Aplicación**: http://localhost:5173

### Backend - Microservicios
- **Auth Service**: http://localhost:8002
  - Swagger: http://localhost:8002/swagger/
  - Health: http://localhost:8002/health/
- **Media Service**: http://localhost:8001
  - Swagger: http://localhost:8001/swagger/
  - Health: http://localhost:8001/health/
- **Profiles Service**: http://localhost:8003
  - Swagger: http://localhost:8003/swagger/
  - Health: http://localhost:8003/health/
- **Marketplace Service**: http://localhost:8004
  - Swagger: http://localhost:8004/swagger/
  - Health: http://localhost:8004/health/
- **Foro Service**: http://localhost:8005
  - Swagger: http://localhost:8005/swagger/
  - Health: http://localhost:8005/health/
- **Chat Service**: http://localhost:8006
  - Swagger: http://localhost:8006/swagger/
  - Health: http://localhost:8006/health/

### Infraestructura
- **Traefik Dashboard**: http://localhost:8080
- **Redis**: localhost:6379
- **Kafka**: localhost:9092, localhost:9094
- **MinIO Console**: http://localhost:9001

## 🔧 Solución de Problemas

### Docker no está corriendo
```
✗ Docker is not running. Please start Docker Desktop and try again.
```
**Solución**: Abre Docker Desktop y espera a que esté completamente iniciado.

### Puertos ocupados
Si algún puerto ya está en uso, verás errores al iniciar los servicios.

**Solución**: Detén cualquier servicio que esté usando los puertos 5173, 8001-8006, 6379, 9092, etc.

```powershell
# Ver qué proceso está usando un puerto (ejemplo: 8002)
netstat -ano | findstr :8002
```

### Servicios no saludables
Si los servicios tardan mucho en estar listos:

```powershell
# Ver el estado de los contenedores
docker-compose -f docker-compose.dev.yml ps

# Ver logs de un servicio específico
docker-compose -f docker-compose.dev.yml logs auth-service
docker-compose -f docker-compose.dev.yml logs media-service
```

### Frontend no se conecta al backend
Verifica que las variables de entorno en `frontend/agrovet/.env.development` apunten a los puertos correctos:

```env
VITE_AUTH_SERVICE_URL=http://127.0.0.1:8002/api
VITE_CHAT_SERVICE_URL=http://127.0.0.1:8006
VITE_FORUM_SERVICE_URL=http://127.0.0.1:8005/api
VITE_ADDS_SERVICE_URL=http://127.0.0.1:8004/api
VITE_MEDIA_SERVICE_URL=http://127.0.0.1:8001/api
VITE_WS_URL=ws://127.0.0.1:8006/ws
```

### Reinstalar dependencias del frontend

```powershell
cd frontend/agrovet
Remove-Item -Recurse -Force node_modules
npm install
```

## 📚 Comandos Útiles

### Ver logs en tiempo real
```powershell
# Todos los servicios
docker-compose -f docker-compose.dev.yml logs -f

# Un servicio específico
docker-compose -f docker-compose.dev.yml logs -f auth-service
```

### Reiniciar un servicio específico
```powershell
docker-compose -f docker-compose.dev.yml restart auth-service
```

### Limpiar todo (incluyendo volúmenes)
```powershell
docker-compose -f docker-compose.dev.yml down -v
```

### Reconstruir imágenes
```powershell
docker-compose -f docker-compose.dev.yml up -d --build
```

## 🏗️ Arquitectura

El proyecto usa una arquitectura de microservicios:

- **6 microservicios Django** (Auth, Media, Profiles, Marketplace, Foro, Chat)
- **Traefik** como API Gateway
- **PostgreSQL** (una base de datos por servicio)
- **Redis** para caché y sesiones
- **Kafka + Zookeeper** para mensajería asíncrona
- **MinIO** para almacenamiento S3-compatible
- **Frontend Vite + React** que consume los microservicios

## 📝 Notas Adicionales

- El primer inicio puede tardar varios minutos mientras se descargan las imágenes de Docker
- Las migraciones de base de datos se ejecutan automáticamente al iniciar cada servicio
- El frontend se recarga automáticamente cuando detecta cambios en el código
- Los cambios en el código del backend requieren reiniciar el contenedor correspondiente

## 🔗 Más Información

- [README_MICROSERVICES.md](./README_MICROSERVICES.md) - Documentación detallada de la arquitectura de microservicios
- [DELIVERABLES.md](./DELIVERABLES.md) - Entregables del proyecto
- [docker-compose.dev.yml](./docker-compose.dev.yml) - Configuración de Docker Compose
