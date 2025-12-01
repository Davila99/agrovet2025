"""
WebSocket consumers for chat service.
"""
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from chat.models import ChatMessage, ChatMessageReceipt, ChatRoom, get_or_create_private_chat
from chat.presence import mark_online, mark_offline, is_online, get_all_online_users
from common.events.kafka_producer import get_producer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Consumer para chat en tiempo real."""
    
    async def connect(self):
        """Conectar al WebSocket."""
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            await self.close()
            return

        self.user = user
        self.user_id = getattr(user, 'id', None)
        self.room_id = self.scope.get('url_route', {}).get('kwargs', {}).get('room_id')
        self.room_group_name = f'chat_{self.room_id}'
        self.user_group_name = f'user_{self.user_id}'

        # Agregar a grupos
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)

        # Nota: online/offline lo maneja PresenceConsumer
        await self.accept()
        logger.info(f'[CONNECT] user_id={self.user_id} joined room={self.room_id}')

    async def disconnect(self, close_code):
        """Desconectar del WebSocket."""
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        except Exception:
            logger.exception('group_discard failed')
        
        # Nota: online/offline lo maneja PresenceConsumer
        logger.info(f'[DISCONNECT] user_id={self.user_id} left room={self.room_id}')

    async def receive_json(self, content, **kwargs):
        """Recibir mensaje JSON del cliente."""
        try:
            event_type = content.get('type')
            logger.debug(f'[RECEIVE_JSON] user_id={self.user_id} type={event_type}')
            
            if event_type == 'chat_message':
                await self.create_message(content)
            elif event_type == 'mark_read':
                await self.mark_messages_read(content)
            else:
                logger.warning(f'[UNKNOWN_EVENT] {event_type}')
        except Exception:
            logger.exception('receive_json handling failed')

    async def create_message(self, content):
        """Crear mensaje y broadcast."""
        room_id = content.get('room_id') or self.room_id
        text = content.get('text', '') or content.get('content', '')
        media_id = content.get('media_id')
        
        try:
            room = await database_sync_to_async(ChatRoom.objects.get)(id=room_id)
        except ChatRoom.DoesNotExist:
            logger.error(f'Room {room_id} not found')
            return

        # Crear mensaje
        try:
            msg = await database_sync_to_async(ChatMessage.objects.create)(
                room=room,
                sender_id=self.user_id,
                content=text,
                media_id=media_id
            )
        except Exception:
            logger.exception('Failed creating message')
            return

        # Crear receipts para participantes excepto sender
        try:
            participant_ids = room.participants_ids or []
            recipients = [pid for pid in participant_ids if pid != self.user_id]
            
            for recipient_id in recipients:
                await database_sync_to_async(ChatMessageReceipt.objects.get_or_create)(
                    message=msg,
                    user_id=recipient_id,
                    defaults={'delivered': False, 'read': False}
                )
        except Exception:
            logger.exception('Failed creating receipts')

        # Broadcast mensaje
        try:
            out_payload = {
                'type': 'chat_message',
                'message_id': msg.id,
                'sender_id': self.user_id,
                'text': text,
                'content': text,
                'room_id': str(room_id),
                'room': str(room_id),
                'media_id': media_id,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None,
                'client_msg_id': content.get('client_msg_id'),
            }
            
            await self.channel_layer.group_send(self.room_group_name, out_payload)
            
            # Publicar evento Kafka
            try:
                producer = get_producer()
                producer.publish('chat.events', 'chat.message.sent', {
                    'message_id': msg.id,
                    'room_id': room_id,
                    'sender_id': self.user_id,
                })
            except Exception as e:
                logger.error(f"Failed to publish chat.message.sent event: {e}")
                
        except Exception:
            logger.exception('Failed broadcasting message')

    async def chat_message(self, event):
        """Handler cuando se recibe un mensaje del grupo."""
        # Enviar mensaje al cliente
        await self.send_json({
            'type': 'chat_message',
            'message_id': event.get('message_id'),
            'sender_id': event.get('sender_id'),
            'text': event.get('text') or event.get('content'),
            'room_id': event.get('room_id'),
            'media_id': event.get('media_id'),
            'timestamp': event.get('timestamp'),
            'client_msg_id': event.get('client_msg_id'),
        })
        
        # Marcar receipt como entregado si el usuario está online
        if self.user_id and event.get('sender_id') != self.user_id:
            try:
                message_id = event.get('message_id')
                if message_id:
                    receipt = await database_sync_to_async(
                        ChatMessageReceipt.objects.filter(
                            message_id=message_id,
                            user_id=self.user_id,
                            delivered=False
                        ).first
                    )()
                    if receipt:
                        receipt.delivered = True
                        receipt.delivered_at = timezone.now()
                        await database_sync_to_async(receipt.save)()
                        
                        # Notificar al sender
                        sender_id = event.get('sender_id')
                        if sender_id:
                            await self.channel_layer.group_send(
                                f'user_{sender_id}',
                                {
                                    'type': 'message_delivered',
                                    'message_id': message_id,
                                    'user_id': self.user_id,
                                }
                            )
            except Exception:
                logger.exception('Failed marking message delivered')

    async def message_delivered(self, event):
        """Handler para notificación de entrega."""
        await self.send_json({
            'type': 'message_delivered',
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id'),
        })

    async def mark_messages_read(self, content):
        """Marcar mensajes como leídos."""
        room_id = content.get('room_id') or self.room_id
        message_ids = content.get('message_ids', [])
        
        try:
            now = timezone.now()
            receipts = await database_sync_to_async(list)(
                ChatMessageReceipt.objects.filter(
                    message__room_id=room_id,
                    user_id=self.user_id,
                    read=False
                )
            )
            
            if message_ids:
                receipts = [r for r in receipts if r.message_id in message_ids]
            
            updated_ids = []
            for receipt in receipts:
                receipt.read = True
                receipt.read_at = now
                await database_sync_to_async(receipt.save)()
                updated_ids.append(receipt.message_id)
            
            # Actualizar flags agregados en ChatMessage
            for msg_id in set(updated_ids):
                try:
                    msg = await database_sync_to_async(ChatMessage.objects.get)(id=msg_id)
                    # Verificar si todos los receipts están leídos
                    all_read = await database_sync_to_async(
                        lambda: not ChatMessageReceipt.objects.filter(
                            message_id=msg_id,
                            read=False
                        ).exists()
                    )()
                    if all_read:
                        msg.read = True
                        msg.seen = True
                        msg.read_at = now
                        await database_sync_to_async(msg.save)()
                except Exception:
                    logger.exception(f'Failed updating message {msg_id}')
            
            # Notificar a otros participantes
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'message_ids': updated_ids,
                    'user_id': self.user_id,
                }
            )
            
        except Exception:
            logger.exception('Failed marking messages read')

    async def messages_read(self, event):
        """Handler para notificación de lectura."""
        await self.send_json({
            'type': 'messages_read',
            'message_ids': event.get('message_ids'),
            'user_id': event.get('user_id'),
        })


class PresenceConsumer(AsyncJsonWebsocketConsumer):
    """Consumer para presencia online/offline."""
    
    # Grupo global para notificar presencia a todos los usuarios conectados
    PRESENCE_GROUP = 'presence_global'
    
    async def connect(self):
        """Conectar al WebSocket de presencia."""
        user = self.scope.get('user')
        if not user or not getattr(user, 'is_authenticated', False):
            await self.close()
            return

        self.user = user
        self.user_id = getattr(user, 'id', None)
        self.user_group_name = f'user_{self.user_id}'

        # Primero aceptar la conexión
        await self.accept()
        
        # Luego unirse a los grupos
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.channel_layer.group_add(self.PRESENCE_GROUP, self.channel_name)
        
        if self.user_id:
            await mark_online(self.user_id)
            
            # Notificar a todos (incluyéndome) que este usuario está online
            await self.channel_layer.group_send(
                self.PRESENCE_GROUP,
                {
                    'type': 'presence_update',
                    'event': 'online',
                    'user_id': self.user_id,
                }
            )
        
        logger.info(f'[PRESENCE_CONNECT] user_id={self.user_id}')

    async def disconnect(self, close_code):
        """Desconectar."""
        # Notificar a todos que este usuario está offline ANTES de salir del grupo
        if self.user_id:
            await mark_offline(self.user_id)
            
            try:
                await self.channel_layer.group_send(
                    self.PRESENCE_GROUP,
                    {
                        'type': 'presence_update',
                        'event': 'offline',
                        'user_id': self.user_id,
                    }
                )
            except Exception as e:
                logger.warning(f'Failed to broadcast offline: {e}')
        
        try:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
            await self.channel_layer.group_discard(self.PRESENCE_GROUP, self.channel_name)
        except Exception:
            pass
        
        logger.info(f'[PRESENCE_DISCONNECT] user_id={self.user_id}')

    async def receive_json(self, content, **kwargs):
        """Recibir eventos de presencia."""
        event_type = content.get('type')
        if event_type == 'ping':
            await self.send_json({'type': 'pong'})
        elif event_type == 'get_online_users':
            # Cliente solicita lista de usuarios online
            await self.send_online_users_list()

    async def presence_update(self, event):
        """Handler para enviar actualizaciones de presencia a los clientes."""
        user_id = event.get('user_id')
        presence_event = event.get('event')
        
        # No enviar al mismo usuario su propia actualización
        if user_id == self.user_id:
            return
            
        await self.send_json({
            'type': f'presence.{presence_event}',
            'user_id': user_id,
        })

    async def send_online_users_list(self):
        """Enviar lista de usuarios actualmente online."""
        try:
            online_users = await get_all_online_users()
            logger.info(f'[PRESENCE] Sending online users list: {online_users}')
            await self.send_json({
                'type': 'online_users_list',
                'users': online_users,
            })
        except Exception as e:
            logger.error(f'Error getting online users list: {e}')
            await self.send_json({
                'type': 'online_users_list',
                'users': [],
            })

