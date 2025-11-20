"""
API views for Foro service.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import sys
import os
import logging

from .models import Post, Comment, Reaction, Notification, Community
from .serializers import (
    PostSerializer, CommentSerializer, ReactionSerializer,
    NotificationSerializer, CommunitySerializer
)

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client
from common.http_clients.media_client import get_media_client
from common.events.kafka_producer import get_producer
from foro.utils.supabase_utils import upload_image_to_supabase

logger = logging.getLogger(__name__)


def get_user_from_token(request):
    """Obtener usuario desde token."""
    token = request.META.get('HTTP_AUTHORIZATION', '').replace('Token ', '').replace('Bearer ', '')
    if not token:
        return None
    auth_client = get_auth_client()
    return auth_client.verify_token(token)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Crear post con autor y media."""
        user = get_user_from_token(self.request)
        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Token inválido')
        
        media_id = self.request.data.get('media_id')
        community_id = self.request.data.get('community_id') or self.request.data.get('community')
        
        serializer.save(
            author_id=user.get('id'),
            media_id=media_id,
            community_id=community_id
        )
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('foro.events', 'foro.post.created', {
                'post_id': serializer.instance.id,
                'author_id': user.get('id'),
                'title': serializer.instance.title,
            })
        except Exception as e:
            logger.error(f"Failed to publish foro.post.created event: {e}")

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def relevant(self, request):
        """Posts relevantes personalizados."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.get('id')
        
        # Construir interacciones del usuario
        interacted_authors = {}
        
        # Comentarios del usuario -> autores de posts
        user_comments = Comment.objects.filter(user_id=user_id)
        for c in user_comments:
            try:
                post = Post.objects.get(id=c.post_id)
                a = post.author_id
                interacted_authors[a] = interacted_authors.get(a, 0) + 3
            except Post.DoesNotExist:
                pass
        
        # Reacciones del usuario
        user_reacts = Reaction.objects.filter(user_id=user_id)
        for r in user_reacts:
            if r.content_type.model == 'post':
                try:
                    post = Post.objects.get(id=r.object_id)
                    a = post.author_id
                    interacted_authors[a] = interacted_authors.get(a, 0) + 2
                except Post.DoesNotExist:
                    pass
        
        # Calcular scores
        posts = list(Post.objects.all())
        def score(p):
            base = p.relevance_score or 0
            boost = interacted_authors.get(p.author_id, 0)
            # Time decay
            age_hours = (timezone.now() - p.created_at).total_seconds() / 3600.0
            decay = max(0.1, 1.0 - age_hours / 168.0)
            return base * 0.6 + boost * 1.2 * decay

        posts.sort(key=lambda p: score(p), reverse=True)
        page = self.paginate_queryset(posts)
        serializer = PostSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Crear comentario."""
        user = get_user_from_token(self.request)
        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Token inválido')
        
        user_id = user.get('id')
        parent_id = self.request.data.get('parent')
        post_id = self.request.data.get('post')
        media_id = self.request.data.get('media_id')
        
        if not post_id:
            raise serializers.ValidationError({'post': 'post_id requerido'})
        
        comment = serializer.save(
            user_id=user_id,
            post_id=post_id,
            parent_id=parent_id,
            media_id=media_id
        )
        
        # Actualizar contadores y notificaciones
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
                parent.increment_replies()
                # Crear notificación
                Notification.objects.create(
                    recipient_id=parent.user_id,
                    actor_id=user_id,
                    content_type=ContentType.objects.get_for_model(Comment),
                    object_id=comment.id,
                    notif_type='comment_reply',
                    summary=f'Usuario {user_id} respondió a tu comentario'
                )
            except Comment.DoesNotExist:
                pass
        else:
            # Notificar al autor del post
            try:
                post = Post.objects.get(id=post_id)
                Notification.objects.create(
                    recipient_id=post.author_id,
                    actor_id=user_id,
                    content_type=ContentType.objects.get_for_model(Comment),
                    object_id=comment.id,
                    notif_type='post_reply',
                    summary=f'Usuario {user_id} comentó en tu post'
                )
            except Post.DoesNotExist:
                pass
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('foro.events', 'foro.comment.added', {
                'comment_id': comment.id,
                'post_id': post_id,
                'user_id': user_id,
            })
        except Exception as e:
            logger.error(f"Failed to publish foro.comment.added event: {e}")


class ReactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        """Crear reacción."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_id = user.get('id')
        rtype = request.data.get('type')
        ctype = request.data.get('content_type')
        obj_id = request.data.get('object_id')
        
        if ctype not in ['post', 'comment']:
            return Response({'detail': 'invalid content_type'}, status=status.HTTP_400_BAD_REQUEST)
        
        model = Post if ctype == 'post' else Comment
        content_type = ContentType.objects.get_for_model(model)
        
        # Verificar que el objeto existe
        try:
            if ctype == 'post':
                target = Post.objects.get(id=obj_id)
            else:
                target = Comment.objects.get(id=obj_id)
        except (Post.DoesNotExist, Comment.DoesNotExist):
            return Response({'detail': 'Objeto no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        
        # Crear o obtener reacción
        obj, created = Reaction.objects.get_or_create(
            user_id=user_id,
            content_type=content_type,
            object_id=target.id,
            type=rtype
        )
        
        if created:
            # Incrementar contadores
            if isinstance(target, Comment):
                Comment.objects.filter(pk=target.id).update(reactions_count=F('reactions_count') + 1)
            
            # Crear notificación
            owner_id = target.author_id if hasattr(target, 'author_id') else target.user_id
            Notification.objects.create(
                recipient_id=owner_id,
                actor_id=user_id,
                content_type=content_type,
                object_id=target.id,
                notif_type='post_reaction' if ctype == 'post' else 'comment_reaction',
                summary=f'Usuario {user_id} reaccionó {rtype}'
            )
        
        # Publicar evento
        try:
            producer = get_producer()
            producer.publish('foro.events', 'foro.reaction.added', {
                'reaction_id': obj.id,
                'user_id': user_id,
                'type': rtype,
                'content_type': ctype,
                'object_id': obj_id,
            })
        except Exception as e:
            logger.error(f"Failed to publish foro.reaction.added event: {e}")
        
        serializer = ReactionSerializer(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        """Eliminar reacción."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        reaction = get_object_or_404(Reaction, pk=pk, user_id=user.get('id'))
        target = reaction.content_object
        
        if hasattr(target, 'reactions_count'):
            target.reactions_count = F('reactions_count') - 1
            target.save(update_fields=['reactions_count'])
        
        reaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Obtener notificaciones del usuario autenticado."""
        user = get_user_from_token(self.request)
        if not user:
            return Notification.objects.none()
        return Notification.objects.filter(recipient_id=user.get('id'))

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Marcar notificaciones como leídas."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        ids = request.data.get('ids', [])
        qs = Notification.objects.filter(recipient_id=user.get('id'), id__in=ids)
        qs.update(read=True)
        return Response({'updated': qs.count()})


class CommunityViewSet(viewsets.ModelViewSet):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        """Crear comunidad."""
        user = get_user_from_token(self.request)
        if not user:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Token inválido')
        
        comm = serializer.save(created_by_id=user.get('id'))
        # Agregar creador como miembro
        if comm.members_ids is None:
            comm.members_ids = []
        if user.get('id') not in comm.members_ids:
            comm.members_ids.append(user.get('id'))
        comm.update_members_count()

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        """Unirse a comunidad."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        comm = get_object_or_404(Community, pk=pk)
        user_id = user.get('id')
        
        if comm.members_ids is None:
            comm.members_ids = []
        if user_id not in comm.members_ids:
            comm.members_ids.append(user_id)
            comm.update_members_count()
        
        return Response({'joined': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def leave(self, request, pk=None):
        """Salir de comunidad."""
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'No autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
        
        comm = get_object_or_404(Community, pk=pk)
        user_id = user.get('id')
        
        if comm.members_ids and user_id in comm.members_ids:
            comm.members_ids.remove(user_id)
            comm.update_members_count()
        
        return Response({'left': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_cover(self, request, pk=None):
        """Subir imagen de portada."""
        comm = get_object_or_404(Community, pk=pk)
        f = request.FILES.get('file')
        if not f:
            return Response({'detail': 'file required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            url = upload_image_to_supabase(f, folder='communities')
        except Exception as e:
            logger.exception('Exception uploading community cover to supabase')
            return Response({'detail': 'upload failed', 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
        if not url:
            return Response({'detail': 'upload failed'}, status=status.HTTP_502_BAD_GATEWAY)
        
        comm.cover_image = url
        comm.save(update_fields=['cover_image'])
        return Response({'cover_image': url})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_avatar(self, request, pk=None):
        """Subir avatar."""
        comm = get_object_or_404(Community, pk=pk)
        f = request.FILES.get('file')
        if not f:
            return Response({'detail': 'file required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            url = upload_image_to_supabase(f, folder='communities/avatars')
        except Exception as e:
            logger.exception('Exception uploading community avatar to supabase')
            return Response({'detail': 'upload failed', 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        
        if not url:
            return Response({'detail': 'upload failed'}, status=status.HTTP_502_BAD_GATEWAY)
        
        comm.avatar = url
        comm.save(update_fields=['avatar'])
        return Response({'avatar': url})

