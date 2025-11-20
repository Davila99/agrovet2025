from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Post, Comment, Reaction, Notification, Community
import sys
import os

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client


class UserBriefSerializer(serializers.Serializer):
    """Serializer breve para información de usuario desde Auth Service."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField(allow_null=True)


class MediaSerializer(serializers.Serializer):
    """Serializer para media desde Media Service."""
    id = serializers.IntegerField()
    name = serializers.CharField(allow_null=True)
    url = serializers.URLField(allow_null=True)
    description = serializers.CharField(allow_null=True)


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    popularity = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'post_id', 'parent_id', 'content', 'media',
            'created_at', 'updated_at', 'reactions_count', 'replies_count',
            'popularity', 'replies'
        ]
        read_only_fields = ['reactions_count', 'replies_count', 'created_at', 'updated_at', 'popularity', 'replies']

    def get_user(self, obj):
        """Obtener información del usuario desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.user_id)
            if user:
                return {
                    'id': user.get('id'),
                    'name': user.get('full_name') or f"User {obj.user_id}",
                    'avatar': user.get('profile_picture'),
                }
        except Exception:
            pass
        return {'id': obj.user_id, 'name': f"User {obj.user_id}", 'avatar': None}

    def get_media(self, obj):
        """Obtener media desde Media Service."""
        if not obj.media_id:
            return None
        try:
            media_client = get_media_client()
            return media_client.get_media(obj.media_id)
        except Exception:
            return None

    def get_replies(self, obj):
        """Obtener respuestas ordenadas por popularidad."""
        from .models import Comment
        replies = Comment.objects.filter(parent_id=obj.id)
        replies = sorted(replies, key=lambda c: (c.reactions_count + c.replies_count), reverse=True)
        return CommentSerializer(replies, many=True, context=self.context).data

    def get_popularity(self, obj):
        """Calcular popularidad."""
        return obj.reactions_count + obj.replies_count


class PostSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    reactions_count = serializers.SerializerMethodField()
    media = serializers.SerializerMethodField()
    community = serializers.SerializerMethodField()
    community_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'title', 'content', 'media', 'community', 'community_id',
            'created_at', 'updated_at', 'views_count', 'relevance_score',
            'comments_count', 'reactions_count', 'comments'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'views_count', 'relevance_score',
            'comments', 'comments_count', 'reactions_count'
        ]

    def get_author(self, obj):
        """Obtener información del autor desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.author_id)
            if user:
                return {
                    'id': user.get('id'),
                    'name': user.get('full_name') or f"User {obj.author_id}",
                    'avatar': user.get('profile_picture'),
                }
        except Exception:
            pass
        return {'id': obj.author_id, 'name': f"User {obj.author_id}", 'avatar': None}

    def get_media(self, obj):
        """Obtener media desde Media Service."""
        if not obj.media_id:
            return None
        try:
            media_client = get_media_client()
            return media_client.get_media(obj.media_id)
        except Exception:
            return None

    def get_community(self, obj):
        """Obtener información de comunidad."""
        if not obj.community_id:
            return None
        try:
            community = Community.objects.get(id=obj.community_id)
            return CommunitySerializer(community, context=self.context).data
        except Community.DoesNotExist:
            return None

    def get_comments(self, obj):
        """Obtener comentarios principales ordenados por popularidad."""
        from .models import Comment
        comments = Comment.objects.filter(post_id=obj.id, parent_id__isnull=True)
        comments = sorted(comments, key=lambda c: (c.reactions_count + c.replies_count), reverse=True)
        return CommentSerializer(comments, many=True, context=self.context).data

    def get_comments_count(self, obj):
        """Contar comentarios."""
        from .models import Comment
        return Comment.objects.filter(post_id=obj.id).count()

    def get_reactions_count(self, obj):
        """Contar reacciones al post."""
        from .models import Reaction
        from django.contrib.contenttypes.models import ContentType
        ct = ContentType.objects.get_for_model(Post)
        return Reaction.objects.filter(content_type=ct, object_id=obj.id).count()


class ReactionSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Reaction
        fields = ['id', 'user', 'type', 'content_type', 'object_id', 'created_at']
        read_only_fields = ['created_at', 'user']

    def get_user(self, obj):
        """Obtener información del usuario desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.user_id)
            if user:
                return {
                    'id': user.get('id'),
                    'name': user.get('full_name') or f"User {obj.user_id}",
                    'avatar': user.get('profile_picture'),
                }
        except Exception:
            pass
        return {'id': obj.user_id, 'name': f"User {obj.user_id}", 'avatar': None}


class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'recipient_id', 'actor', 'notif_type', 'summary', 'read', 'created_at']
        read_only_fields = ['created_at']

    def get_actor(self, obj):
        """Obtener información del actor desde Auth Service."""
        try:
            auth_client = get_auth_client()
            user = auth_client.get_user(obj.actor_id)
            if user:
                return {
                    'id': user.get('id'),
                    'name': user.get('full_name') or f"User {obj.actor_id}",
                    'avatar': user.get('profile_picture'),
                }
        except Exception:
            pass
        return {'id': obj.actor_id, 'name': f"User {obj.actor_id}", 'avatar': None}


class CommunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Community
        fields = [
            'id', 'name', 'slug', 'short_description', 'description',
            'cover_image', 'avatar', 'members_count', 'created_by_id', 'created_at'
        ]
        read_only_fields = ['members_count', 'created_at', 'created_by_id']

