from django.db import models
from django.db.models import Count
from django.utils import timezone


class ChatRoom(models.Model):
    """
    Representa una sala de chat entre dos usuarios o para un grupo.
    """
    name = models.CharField(max_length=150, blank=True)
    # Store participant IDs as JSON array (from Auth Service)
    participants_ids = models.JSONField(default=list, help_text="Lista de IDs de participantes en Auth Service")
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sala de Chat"
        verbose_name_plural = "Salas de Chat"

    def __str__(self):
        return f"Sala ID {self.id} ({len(self.participants_ids)} participantes)"


def get_or_create_private_chat(user1_id, user2_id):
    """
    Obtiene o crea una sala privada entre dos usuarios.
    
    Args:
        user1_id: ID del primer usuario en Auth Service
        user2_id: ID del segundo usuario en Auth Service
    
    Returns:
        Tuple (ChatRoom, created)
    """
    if user1_id == user2_id:
        raise ValueError("Un usuario no puede chatear consigo mismo.")

    # Buscar sala privada existente con exactamente esos dos usuarios
    chats = ChatRoom.objects.filter(
        is_private=True,
        participants_ids__contains=[user1_id]
    ).filter(
        participants_ids__contains=[user2_id]
    )
    
    # Filtrar por longitud exacta de 2 participantes
    for chat in chats:
        if len(chat.participants_ids) == 2:
            return chat, False

    # Si no existe, crear
    chat = ChatRoom.objects.create(
        name=f"Chat: User {user1_id} & User {user2_id}",
        is_private=True,
        participants_ids=[user1_id, user2_id]
    )
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
    sender_id = models.IntegerField(db_index=True, help_text="ID del remitente en Auth Service")
    content = models.TextField(verbose_name="Contenido del mensaje", blank=True)
    
    # Store media_id from Media Service instead of ForeignKey
    media_id = models.IntegerField(null=True, blank=True, help_text="ID de media en Media Service")
    
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha/Hora")
    sent = models.BooleanField(default=True, verbose_name="Enviado")
    delivered = models.BooleanField(default=False, verbose_name="Entregado")
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha/Hora entrega")
    read = models.BooleanField(default=False, verbose_name="Leído")
    seen = models.BooleanField(default=False, verbose_name="Visto")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha/Hora lectura")

    class Meta:
        ordering = ('timestamp',)
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"

    def __str__(self):
        return f"Mensaje de user_id={self.sender_id} en Sala {self.room.id}"

    def save(self, *args, **kwargs):
        """Actualizar last_activity de la sala al guardar mensaje."""
        super().save(*args, **kwargs)
        try:
            self.room.last_activity = timezone.now()
            self.room.save(update_fields=['last_activity'])
        except Exception:
            pass


class ChatMessageReceipt(models.Model):
    """
    Per-user receipt status for a ChatMessage.
    Tracks whether a specific recipient has had the message delivered and/or read.
    """
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='receipts')
    user_id = models.IntegerField(db_index=True, help_text="ID del usuario en Auth Service")
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('message', 'user_id')
        verbose_name = 'Receipt de mensaje'
        verbose_name_plural = 'Receipts de mensajes'

    def __str__(self):
        return f"Receipt message={self.message.id} user_id={self.user_id}"

