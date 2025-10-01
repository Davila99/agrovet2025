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
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat.message', # Método que manejará el envío (ver abajo)
                    'message': message,
                    'username': user.username,
                    'timestamp': self.get_current_time() # Solo para ejemplo, el cliente puede formatearlo mejor
                }
            )

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

        # 2. Crea el mensaje
        ChatMessage.objects.create(
            room=room,
            sender=user,
            content=message
        )
        
        # 3. Actualiza la marca de tiempo de la última actividad de la sala
        room.last_activity = F('timestamp') # Usar F-expression para evitar race conditions
        room.save(update_fields=['last_activity'])