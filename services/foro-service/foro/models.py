from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


class Post(models.Model):
    """Post en el foro."""
    author_id = models.IntegerField(db_index=True, help_text="ID del usuario en Auth Service")
    title = models.CharField(max_length=255)
    content = models.TextField()
    media_id = models.IntegerField(null=True, blank=True, help_text="ID de media en Media Service")
    community_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="ID de comunidad")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    relevance_score = models.FloatField(default=0.0, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Post'
        verbose_name_plural = 'Posts'

    def __str__(self):
        return f"{self.title} by user_id={self.author_id}"

    def increment_views(self):
        """Incrementar contador de vistas."""
        self.views_count = models.F('views_count') + 1
        self.save(update_fields=['views_count'])


class Comment(models.Model):
    """Comentario en un post, puede tener respuestas anidadas."""
    user_id = models.IntegerField(db_index=True, help_text="ID del usuario en Auth Service")
    post_id = models.IntegerField(db_index=True, help_text="ID del post")
    parent_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="ID del comentario padre (para respuestas)")
    content = models.TextField()
    media_id = models.IntegerField(null=True, blank=True, help_text="ID de media en Media Service")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reactions_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'

    def __str__(self):
        return f"Comment by user_id={self.user_id} on post_id={self.post_id}"

    def increment_replies(self):
        """Incrementar contador de respuestas."""
        self.replies_count = models.F('replies_count') + 1
        self.save(update_fields=['replies_count'])


class Reaction(models.Model):
    """Reacción a un post o comentario."""
    REACTION_CHOICES = (
        ('heart', 'Heart'),
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )
    user_id = models.IntegerField(db_index=True, help_text="ID del usuario en Auth Service")
    type = models.CharField(max_length=16, choices=REACTION_CHOICES)
    
    # Generic target: puede ser Post o Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user_id', 'content_type', 'object_id', 'type'),)
        verbose_name = 'Reacción'
        verbose_name_plural = 'Reacciones'

    def __str__(self):
        return f"{self.type} by user_id={self.user_id}"


class Notification(models.Model):
    """Notificación para usuarios."""
    NOTIF_TYPES = (
        ('post_reply', 'Reply to post'),
        ('comment_reply', 'Reply to comment'),
        ('post_reaction', 'Reaction to post'),
        ('comment_reaction', 'Reaction to comment'),
    )
    recipient_id = models.IntegerField(db_index=True, help_text="ID del usuario destinatario en Auth Service")
    actor_id = models.IntegerField(db_index=True, help_text="ID del usuario que realiza la acción en Auth Service")
    
    # Generic target: puede ser Post o Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    notif_type = models.CharField(max_length=32, choices=NOTIF_TYPES)
    summary = models.CharField(max_length=512, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def __str__(self):
        return f"Notification {self.notif_type} -> user_id={self.recipient_id}"


class Community(models.Model):
    """Comunidad temática."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_by_id = models.IntegerField(null=True, blank=True, help_text="ID del usuario creador en Auth Service")
    
    # Members stored as JSON array of user_ids
    members_ids = models.JSONField(default=list, blank=True, help_text="Lista de IDs de miembros en Auth Service")
    members_count = models.PositiveIntegerField(default=0)
    
    cover_image = models.CharField(max_length=500, blank=True, null=True, help_text='URL de imagen de portada')
    avatar = models.CharField(max_length=500, blank=True, null=True, help_text='URL de avatar')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-members_count', '-created_at']
        verbose_name = 'Comunidad'
        verbose_name_plural = 'Comunidades'

    def __str__(self):
        return self.name

    def update_members_count(self):
        """Actualizar contador de miembros."""
        # Ensure members_ids is a list
        if self.members_ids is None:
            self.members_ids = []
        # Normalize possible string IDs to ints when possible
        try:
            self.members_ids = [int(x) for x in self.members_ids]
        except Exception:
            # If conversion fails, keep original list
            pass
        self.members_count = len(self.members_ids) if self.members_ids else 0
        # Persist both members_ids and members_count to keep DB consistent
        self.save(update_fields=['members_ids', 'members_count'])

