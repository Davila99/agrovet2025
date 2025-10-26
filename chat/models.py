from django.db import models
from django.db.models import Count
from django.contrib.auth import get_user_model

# Obtiene el modelo de usuario activo (CustomUser, User, etc.)
User = get_user_model()

class ChatRoom(models.Model):
    """
    Representa una sala de chat entre dos usuarios o para un grupo.
    En este ejemplo, crearemos salas de chat de dos personas (consultas).
    """
    # UsamosManyToManyField para permitir que dos o más usuarios participen.
    # Usar related_name='chat_rooms' permite acceder a las salas desde el objeto User.
    name = models.CharField(max_length=150, blank=True)
    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        verbose_name="Participantes de la sala"
    )
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        # Muestra los nombres de usuario de los participantes.
        # Evita cargar todos los participantes en string en DB grandes
        participants_usernames = ', '.join(list(self.participants.values_list('username', flat=True))[:5])
        return f"Sala ID {self.id} ({participants_usernames})"

    class Meta:
        verbose_name = "Sala de Chat"
        verbose_name_plural = "Salas de Chat"

def get_or_create_private_chat(user1, user2):
    """
    Obtiene o crea una sala privada entre dos usuarios.
    """
    if user1 == user2:
        raise ValueError("Un usuario no puede chatear consigo mismo.")

    # Busca una sala privada existente CON EXACTAMENTE esos dos usuarios
    chats = (
        ChatRoom.objects
        .filter(is_private=True)
        .filter(participants=user1)
        .filter(participants=user2)
        .annotate(num_participants=Count('participants'))
        .filter(num_participants=2)
    )
    if chats.exists():
        return chats.first(), False

    # Si no existe, la crea
    chat = ChatRoom.objects.create(
        name=f"Chat: {user1.username} & {user2.username}",
        is_private=True
    )
    chat.participants.set([user1, user2])
    chat.save()
    return chat, True


class ChatMessage(models.Model):
    """
    Representa un mensaje enviado en una sala de chat específica.
    """
    room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name='messages', 
        verbose_name="Sala"
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages',
        verbose_name="Remitente"
    )
    content = models.TextField(verbose_name="Contenido del mensaje", blank=True)
    # Relación opcional a Media para imágenes/videos adjuntos
    media = models.ForeignKey('media.Media', on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_messages')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora")
    # Whether the message has been delivered to recipients. For 1:1 chats
    # this is sufficient. For group chats consider per-user delivery tracking.
    delivered = models.BooleanField(default=False, verbose_name="Entregado")
    # Timestamp when the message was first marked delivered (all recipients)
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha/Hora entrega")
    # Aggregate read state: True when all recipients have read the message
    read = models.BooleanField(default=False, verbose_name="Leído")
    # Timestamp when the message was first considered read by all recipients
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha/Hora lectura")
# Keep ChatMessage metadata and helpers below
    
    def __str__(self):
        return f"Mensaje de {self.sender.username} en Sala {self.room.id}"

    class Meta:
        ordering = ('timestamp',) # Ordena los mensajes por tiempo
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"

    def save(self, *args, **kwargs):
        # Save the message first
        super().save(*args, **kwargs)
        # Update room metadata: last_activity and optionally room name
        try:
            from django.utils import timezone
            self.room.last_activity = timezone.now()
            # If the room is private and has exactly two participants, set the room name
            # to the sender's display name so chat lists show the last sender.
            try:
                num = self.room.participants.count()
            except Exception:
                num = None
            if getattr(self.room, 'is_private', False) and num == 2:
                # Choose a readable display name for the sender
                display = getattr(self.sender, 'full_name', None) or getattr(self.sender, 'phone_number', None) or getattr(self.sender, 'username', None)
                if display:
                    self.room.name = display
            self.room.save(update_fields=['last_activity', 'name'])
        except Exception:
            # Avoid breaking message creation if room metadata update fails
            import logging; logging.getLogger(__name__).exception('Failed updating room metadata after saving ChatMessage')


class ChatMessageReceipt(models.Model):
    """
    Per-user receipt status for a ChatMessage.
    Tracks whether a specific recipient has had the message delivered and/or read.
    """
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='receipts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_receipts')
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('message', 'user')
        verbose_name = 'Receipt de mensaje'
        verbose_name_plural = 'Receipts de mensajes'
    def __str__(self):
        return f"Receipt message={getattr(self.message,'id',None)} user={getattr(self.user,'id',None)}"