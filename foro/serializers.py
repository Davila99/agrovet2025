from rest_framework import serializers
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from .models import Post, Comment, Reaction, Notification
from media.models import Media


class UserBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='pk')
    full_name = serializers.CharField()
    profile_picture = serializers.CharField(allow_null=True)


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ['id', 'name', 'url', 'description']


class CommentSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(source='user', read_only=True)
    replies = serializers.SerializerMethodField()
    popularity = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'user', 'post', 'parent', 'content', 'media', 'created_at', 'updated_at', 'reactions_count', 'replies_count', 'popularity', 'replies']
        read_only_fields = ['reactions_count', 'replies_count', 'created_at', 'updated_at', 'popularity', 'replies']

    def get_replies(self, obj):
        # order replies by popularity (reactions + replies)
        qs = obj.replies.all()
        qs = sorted(qs, key=lambda c: (c.reactions_count + c.replies_count), reverse=True)
        return CommentSerializer(qs, many=True, context=self.context).data

    def get_popularity(self, obj):
        return obj.reactions_count + obj.replies_count


class PostSerializer(serializers.ModelSerializer):
    author = UserBriefSerializer(source='author', read_only=True)
    comments = serializers.SerializerMethodField()
    media = MediaSerializer(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author', 'title', 'content', 'media', 'created_at', 'updated_at', 'views_count', 'relevance_score', 'comments']
        read_only_fields = ['created_at', 'updated_at', 'views_count', 'relevance_score', 'comments']

    def get_comments(self, obj):
        # top-level comments ordered by popularity
        qs = obj.comments.filter(parent__isnull=True)
        qs = sorted(qs, key=lambda c: (c.reactions_count + c.replies_count), reverse=True)
        return CommentSerializer(qs, many=True, context=self.context).data


class ReactionSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = Reaction
        fields = ['id', 'user', 'type', 'content_type', 'object_id', 'created_at']
        read_only_fields = ['created_at', 'user']


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'actor', 'notif_type', 'summary', 'read', 'created_at']
        read_only_fields = ['created_at']
