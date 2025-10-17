from django.db import models
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
    name = models.CharField(max_length=150)
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

    def __str__(self):
        return f"Mensaje de {self.sender.username} en Sala {self.room.id}"

    class Meta:
        ordering = ('timestamp',) # Ordena los mensajes por tiempo
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"