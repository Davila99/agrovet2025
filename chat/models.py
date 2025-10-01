# chat_app/models.py
from django.db import models
# Asegúrate de que esta importación sea correcta
from auth_app.models import CustomUser 

# -----------------
# 1. Modelo de Sala/Conversación
# -----------------
class ChatRoom(models.Model):
    """
    Representa una conversación (sala de chat) entre dos o más usuarios.
    """
    # Participantes de la sala de chat. 
    # Usamos ManyToManyField para permitir 1:1 o chats grupales.
    participants = models.ManyToManyField(
        CustomUser, 
        related_name='chat_rooms'
    )
    # Nombre opcional para la sala (útil para chats grupales)
    name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True
    )
    # Marca de tiempo para ordenar las salas por la actividad más reciente
    last_activity = models.DateTimeField(
        auto_now_add=True 
    )

    def __str__(self):
        if self.name:
            return self.name
        # Muestra los nombres de usuario de los primeros dos participantes
        usernames = self.participants.values_list('username', flat=True)[:2]
        return f"Conversación: {', '.join(usernames)}"

    class Meta:
        # Ordena las salas por la actividad más reciente
        ordering = ('-last_activity',)



# -----------------
# 2. Modelo de Mensaje
# -----------------
class ChatMessage(models.Model):
    """
    Representa un mensaje individual dentro de una sala de chat específica.
    """
    # La sala a la que pertenece este mensaje
    room = models.ForeignKey(
        ChatRoom, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    # El usuario que envió el mensaje
    sender = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    # El contenido del mensaje
    content = models.TextField()
    # El momento en que se envió el mensaje
    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        # Muestra el remitente y un fragmento del mensaje
        return f"De {self.sender.username}: {self.content[:30]}..."

    class Meta:
        # Los mensajes se ordenan cronológicamente
        ordering = ('timestamp',)