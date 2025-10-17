# chat_app/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import F

from .models import ChatRoom, ChatMessage

# Obtenemos el modelo de usuario que estás utilizando (CustomUser)
User = get_user_model() 

class ChatConsumer(AsyncWebsocketConsumer):
    # ----------------------------------------------------
    # 1. Métodos de Conexión y Desconexión
    # ----------------------------------------------------
    async def connect(self):
        """Se llama cuando el WebSocket se conecta (handshake)."""
        # Obtenemos el ID de la sala desde la URL (routing)
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        # Creamos un nombre de grupo de canal para esta sala
        self.room_group_name = f'chat_{self.room_id}'

        # Unimos al usuario al grupo de la sala
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Aceptamos la conexión
        await self.accept()

    async def disconnect(self, close_code):
        """Se llama cuando el WebSocket se desconecta."""
        # Abandonamos el grupo de la sala
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
    # ----------------------------------------------------
    # 2. Recepción de Mensajes (Desde el Cliente)
    # ----------------------------------------------------
    async def receive(self, text_data):
        """Se llama cuando recibimos un mensaje del WebSocket."""
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # El usuario actual está en self.scope['user']
        user = self.scope['user']

        # Si el usuario está autenticado, procesamos el mensaje
        if user.is_authenticated:
            # Llama a una función asíncrona para guardar el mensaje en la base de datos
            await self.save_message(user, message)

            # Envía el mensaje al grupo de la sala (a todos los clientes conectados)
            # Recuperamos el último mensaje creado para obtener id/media
            # Guardar mensaje ya fue realizado en save_message
            from chat.models import ChatMessage
            last_msg = ChatMessage.objects.filter(room_id=self.room_id, sender=user).order_by('-timestamp').first()
            payload = {
                'type': 'chat.message',
                'message': last_msg.content if last_msg else message,
                'username': user.username,
                'timestamp': self.get_current_time()
            }
            if last_msg and last_msg.media:
                payload['media_id'] = last_msg.media.id
                payload['media_url'] = last_msg.media.url

            await self.channel_layer.group_send(self.room_group_name, payload)

    # ----------------------------------------------------
    # 3. Envío de Mensajes (Al Cliente)
    # ----------------------------------------------------
    async def chat_message(self, event):
        """Se llama cuando el grupo recibe un mensaje (del channel_layer)."""
        message = event['message']
        username = event['username']
        timestamp = event['timestamp']

        # Envía el mensaje al WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'timestamp': timestamp
        }))

    # ----------------------------------------------------
    # 4. Funciones de Base de Datos y Utilidades
    # ----------------------------------------------------
    @classmethod
    def get_current_time(cls):
        """Devuelve una marca de tiempo simple (mejor usar JS para formato)."""
        # Nota: En un entorno de producción, es mejor obtener esto del servidor
        # o usar un paquete como `timezone.now()` en la función de base de datos.
        import datetime
        return datetime.datetime.now().strftime("%H:%M")


    # NOTA: Los consumidores son asíncronos (async/await), pero las operaciones 
    # de Django ORM son síncronas. Debemos envolverlas en `sync_to_async`.
    # Esto requiere el decorador `database_sync_to_async` de Channels.
    from channels.db import database_sync_to_async

    @database_sync_to_async
    def save_message(self, user, message):
        """Guarda el mensaje en la base de datos de forma síncrona."""
        # 1. Busca la sala y el usuario
        try:
            room = ChatRoom.objects.get(id=self.room_id)
        except ChatRoom.DoesNotExist:
            # Si la sala no existe, no hacemos nada (o manejamos el error)
            return

        # 2. Si message es JSON/dict, extraemos content y media_id
        content = None
        media_obj = None
        try:
            # message puede venir como string JSON
            if isinstance(message, str):
                import json as _json
                parsed = _json.loads(message)
            else:
                parsed = message

            content = parsed.get('content') if isinstance(parsed, dict) else str(parsed)
            media_id = parsed.get('media_id') if isinstance(parsed, dict) else None
            if media_id:
                from media.models import Media
                try:
                    media_obj = Media.objects.get(id=media_id)
                except Media.DoesNotExist:
                    media_obj = None
        except Exception:
            # Si no es JSON, tratamos message como texto
            content = str(message)

        # 3. Crea el mensaje con posible media
        ChatMessage.objects.create(
            room=room,
            sender=user,
            content=content or '',
            media=media_obj
        )

        # 4. Actualiza la marca de tiempo de la última actividad de la sala
        from django.utils import timezone
        room.last_activity = timezone.now()
        room.save(update_fields=['last_activity'])