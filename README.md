# ConsultVets 🐾
# ConsultVets / Agrovet2025 🐾

Sistema de gestión con chat en tiempo real y subida de media. Este README describe cómo preparar el backend y un pequeño ejemplo de frontend (React) para probar el chat y la subida de imágenes.

## Requisitos previos
- Python 3.10+
- Redis (local o remoto) para Channel Layer
- Node.js + npm (para el frontend si quieres probar la demo)

## Instalación y configuración (backend)
1. Clona el repositorio y entra en la carpeta:

```powershell
git clone https://github.com/Davila99/agrovet2025.git
cd agrovet2025
```

2. Crea y activa un virtualenv:

```powershell
python -m venv .venv; .\.venv\\Scripts\\Activate.ps1
```

3. Instala dependencias:

```powershell
pip install -r requirements.txt
```

4. Crea un `.env` en la raíz con al menos estas variables (ejemplo):

```
DJANGO_SECRET_KEY=tu_secret_key
DEBUG=True
DATABASE_URL=mysql://user:pass@localhost:3306/agrovet
SUPABASE_URL=https://your-supabase-url
SUPABASE_KEY=your-service-role-or-anon-key
SUPABASE_BUCKET=your-bucket-name
REDIS_URL=redis://localhost:6379/0
```

5. Ejecuta migraciones y crea superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

## Ejecutar el backend (ASGI) para WebSocket
Para que los WebSocket funcionen correctamente es recomendable ejecutar ASGI con `uvicorn` o `daphne` (y tener Redis corriendo):

```powershell
# Instalar uvicorn si no lo tienes
pip install uvicorn
uvicorn consultveterinarias.asgi:application --reload
```

Si usas Docker o WSL, inicia Redis en tu entorno. En Windows puedes usar WSL o una instancia remota de Redis.

## Endpoints importantes
- REST API base: `http://127.0.0.1:8000/api/`
- Login (obtener token): `POST /api/auth/login/` (guarda `token`)
- Upload specialist images: `POST /api/profiles/specialists/{pk}/upload_work_images/` (multipart, campo `images`)
- Chat REST:
	- `POST /api/chat/rooms/` — crear sala
	- `POST /api/chat/messages/` — enviar mensaje por REST
	- `GET /api/chat/messages/last_messages/?room=<id>&limit=N` — últimos mensajes

## WebSocket (real-time chat)
- WS URL: `ws://127.0.0.1:8000/ws/chat/<room_id>/?token=<DRF-token>`
	- La autenticación se realiza por query string `?token=` con el token DRF.
- Enviar mensajes desde frontend por WS:
	- Texto simple: `{ "message": "Hola" }`
	- Con media: `{ "message": { "content": "Mira esto", "media_id": 123 } }`
- Mensajes recibidos contienen keys: `message`, `username`, `timestamp` y opcionalmente `media_id` y `media_url`.

## Ejemplo mínimo de componente React para conectar al WS

```javascript
import React, { useEffect, useState } from 'react';

export default function Chat({ roomId, token }) {
	const [messages, setMessages] = useState([]);

	useEffect(() => {
		const ws = new WebSocket(`ws://127.0.0.1:8000/ws/chat/${roomId}/?token=${token}`);

		ws.onopen = () => console.log('WS open');
		ws.onmessage = (evt) => {
			const data = JSON.parse(evt.data);
			setMessages(prev => [...prev, data]);
		};
		ws.onclose = () => console.log('WS closed');

		return () => ws.close();
	}, [roomId, token]);

	return (
		<div>
			{messages.map((m, i) => (
				<div key={i}>
					<b>{m.username}</b>: {m.message}
					{m.media_url && <div><img src={m.media_url} alt="media" style={{maxWidth:200}}/></div>}
				</div>
			))}
		</div>
	);
}
```

## Postman
- Importa `tools/postman/agrovet_chat.postman_collection.json`.
- Flujo sugerido: Login → Create Room → Upload images → Post message → Get last messages

## Seguridad y recomendaciones
- Evita pasar tokens en query strings en producción sin TLS. Prefiere cookies o headers.
- Configura `channels_redis` y Redis gestionado para producción.
- Valida que el usuario pertenezca a la sala antes de aceptar y almacenar mensajes.

---

Si quieres que además genere un pequeño `frontend/` con `create-react-app` ya configurado dentro del repo, dímelo y lo creo (incluyo `package.json` y comandos de inicio).
