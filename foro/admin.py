from django.contrib import admin
from .models import Post, Comment, Reaction, Notification


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'created_at', 'views_count', 'relevance_score')
    search_fields = ('title', 'content', 'author__full_name')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'parent', 'created_at', 'reactions_count', 'replies_count')
    search_fields = ('content', 'user__full_name')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'content_type', 'object_id', 'created_at')
    search_fields = ('user__full_name',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'actor', 'notif_type', 'read', 'created_at')
    list_filter = ('notif_type', 'read')
