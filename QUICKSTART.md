# 🚀 Inicio Rápido - Agrovet2025

## Un solo comando para todo

```powershell
.\start-dev.ps1
```

O directamente con Docker Compose:

```powershell
docker-compose -f docker-compose.dev.yml up -d
```

## URLs

- **Frontend**: http://localhost:5173
- **Backend**: puertos 8001-8006
- **Traefik**: http://localhost:8080

## Detener todo

```powershell
.\stop-dev.ps1
```

O:

```powershell
docker-compose -f docker-compose.dev.yml down
```

## Ver logs

```powershell
# Todos los servicios
docker-compose -f docker-compose.dev.yml logs -f

# Solo frontend
docker-compose -f docker-compose.dev.yml logs -f frontend

# Solo un servicio backend
docker-compose -f docker-compose.dev.yml logs -f auth-service
```

---

Para más detalles, ver [README_STARTUP.md](./README_STARTUP.md)
