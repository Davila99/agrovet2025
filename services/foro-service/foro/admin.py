from django.contrib import admin
from foro.models import Post, Comment, Reaction, Notification, Community


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author_id', 'community_id', 'views_count', 'created_at')
    list_filter = ('created_at', 'community_id')
    search_fields = ('title', 'content', 'author_id')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'post_id', 'parent_id', 'reactions_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'user_id', 'post_id')


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'type', 'content_type', 'object_id', 'created_at')
    list_filter = ('type', 'created_at', 'content_type')
    search_fields = ('user_id',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient_id', 'actor_id', 'notif_type', 'read', 'created_at')
    list_filter = ('notif_type', 'read', 'created_at')
    search_fields = ('recipient_id', 'actor_id')


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug', 'members_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'slug')

