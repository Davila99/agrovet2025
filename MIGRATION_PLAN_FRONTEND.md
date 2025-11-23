# Frontend Migration Plan (Microservices)

Última actualización: 2025-11-21

Objetivo: Migrar el frontend para consumir el backend dividido en microservicios sin romper la UX. El plan es migrar módulo a módulo, normalizando respuestas con adaptadores y manteniendo compatibilidad a través de `httpClient` y `authClient`.

Checklist:

- [x] Crear plantillas de entorno (`.env.development`, `.env.production`, `.env.docker`) y documentar variables VITE_*.
- [x] Añadir `src/services/env.js` con `getServiceUrl`/`buildUrl` para resolver servicios por ambiente.
- [x] Actualizar `src/services/httpClient.js` para soportar URLs absolutas, usar `env.buildUrl`, y manejar timeouts/service-down.
- [x] Crear carpeta de adaptadores `src/services/adapters/` y añadir `authAdapter`, `postAdapter`, `mediaAdapter` (scaffold).
- [x] Actualizar endpoints `src/services/endpoints/auth.js` para llamar al AUTH microservice y normalizar la respuesta.
- [x] Crear `migration_inventory.json` con mapeo inicial de llamadas frontend -> microservicio.
- [x] Implementar manejo de tokens y flujo de refresh en `src/services/authClient.js`.
- [x] Añadir interceptor en `httpClient` para intentar refresh+retry en 401 (no-auth endpoints).

-- [ ] Migrar módulo `media` (uploads) (in-progress):
  - [x] Actualizar endpoint `media` a `env.buildUrl('MEDIA', ...)`.
  - [ ] Asegurar que `ImageUploader` use FormData campo `image` y que backend devuelva `{ id, url }`.
  - [x] Integrar `mediaAdapter` para normalizar media objects (mediaAPI returns normalized objects).
   - [x] Actualizar endpoint `media` a `env.buildUrl('MEDIA', ...)`.
   - [ ] Asegurar que `ImageUploader` use FormData campo `image` y que backend devuelva `{ id, url }`.
   - [x] Integrar `mediaAdapter` para normalizar media objects (mediaAPI returns normalized objects).

  Nota: Se corrigió `authAPI.login` para persistir tokens mediante `authClient.saveTokens()` cuando el servicio AUTH devuelve `token|access` y `refresh`. Esto evita que peticiones posteriores (por ejemplo `addService.createAdd`) no envíen Authorization y reciban "credentials not provided".

- [ ] Migrar módulo `foro` (posts/comments):
  - [ ] Actualizar `src/services/endpoints/foro.js` para usar `env.buildUrl('FORUM', ...)`.
  - [ ] Reemplazar llamadas antiguas por adaptadores (`postAdapter`).
  - [ ] Verificar creación de posts devuelve objeto completo; si no, usar fallback `getPostDetail` en `PostComposer`.

- [ ] Migrar `adds`, `profiles`, `marketplace`, `chat` módulos por orden de prioridad.

- [ ] WebSocket / Sockets:
  - [ ] Asegurar que los tokens renovados se utilicen al abrir/conectar sockets.
  - [ ] Implementar reconexión y reauth en canales cuando refresh ocurra.

- [ ] Tests:
  - [ ] Unit tests para `authClient`, `httpClient` interceptor y adapters.
  - [ ] Integration test para login -> refresh -> protected endpoint.

- [ ] Dockerize frontend (add Dockerfile, docker-compose.frontend.yml) y documentar run steps.

Notas de progreso y decisiones:
- Se mantuvo compatibilidad temporal escribiendo `localStorage['token']` cuando se guardan tokens en `authClient`, para evitar romper componentes legacy que leen esa clave.
- El flujo de refresh prueba varios endpoints comunes (`/auth/refresh/`, `/auth/token/refresh/`, `/auth/refresh-token/`) para soportar distintos backends.

Proxima acción planificada: Migrar módulo `media` y asegurar que el upload-first flow devuelva consistentemente `{id, url}`; luego migrar `foro`.

Si quieres que marque otros pasos ya realizados que no estén reflejados aquí, dime cuáles y actualizo el archivo.
