from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Import existing Media model without modifying it
try:
    from media.models import Media
except Exception:
    Media = None


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    content = models.TextField()
    media = models.ForeignKey('media.Media', null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    community = models.ForeignKey('Community', null=True, blank=True, on_delete=models.SET_NULL, related_name='posts')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0)
    relevance_score = models.FloatField(default=0.0, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.author}"

    def increment_views(self):
        self.views_count = models.F('views_count') + 1
        self.save(update_fields=['views_count'])


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    media = models.ForeignKey('media.Media', null=True, blank=True, on_delete=models.SET_NULL, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reactions_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user} on {self.post}"

    def increment_replies(self):
        self.replies_count = models.F('replies_count') + 1
        self.save(update_fields=['replies_count'])


class Reaction(models.Model):
    REACTION_CHOICES = (
        ('heart', 'Heart'),
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reactions')
    type = models.CharField(max_length=16, choices=REACTION_CHOICES)

    # Generic target so a reaction can point to Post or Comment
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('user', 'content_type', 'object_id', 'type'),)

    def __str__(self):
        return f"{self.type} by {self.user} on {self.content_object}"


class Notification(models.Model):
    NOTIF_TYPES = (
        ('post_reply', 'Reply to post'),
        ('comment_reply', 'Reply to comment'),
        ('post_reaction', 'Reaction to post'),
        ('comment_reaction', 'Reaction to comment'),
    )
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='actor_notifications')
    # optional links to post/comment via GenericForeignKey
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    notif_type = models.CharField(max_length=32, choices=NOTIF_TYPES)
    summary = models.CharField(max_length=512, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification {self.notif_type} -> {self.recipient}"


class Community(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_communities')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='communities', blank=True)
    members_count = models.PositiveIntegerField(default=0)
    cover_image = models.CharField(max_length=500, blank=True, null=True, help_text='Optional URL to a cover image for the community')
    avatar = models.CharField(max_length=500, blank=True, null=True, help_text='Optional URL for community avatar (round)')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-members_count', '-created_at']

    def __str__(self):
        return self.name


# Signals: keep members_count in sync and auto-assign default communities on user creation
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver


@receiver(m2m_changed, sender=Community.members.through)
def update_members_count(sender, instance, action, pk_set, **kwargs):
    """
    Update `members_count` whenever members are added/removed.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        instance.members_count = instance.members.count()
        instance.save(update_fields=["members_count"])


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def add_user_to_default_communities(sender, instance, created, **kwargs):
    """
    When a new user is created, add them to default communities based on their role.
    This will create the community if it doesn't exist.
    """
    if not created:
        return

    role = getattr(instance, 'role', None)
    if not role:
        return

    # Mapping from role value to list of community slugs to join
    role_map = {
        'consumer': ['consumidores'],
        'businessman': ['agroveterinarias'],
        'veterinario': ['veterinarios'],
        'agronomo': ['agronomos'],
        'Specialist': ['especialistas'],
    }

    slugs = role_map.get(role, [])
    for slug in slugs:
        community, created_c = Community.objects.get_or_create(
            slug=slug,
            defaults={
                'name': slug.replace('-', ' ').title(),
                'short_description': '',
                'created_by': None,
            }
        )
        # add member
        community.members.add(instance)
