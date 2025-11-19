from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import F
from .models import Post, Comment, Reaction, Notification, Community
from .serializers import PostSerializer, CommentSerializer, ReactionSerializer, NotificationSerializer, CommunitySerializer
from media.models import Media
from django.conf import settings
from django.utils import timezone
from auth_app.utils.supabase_utils import upload_image_to_supabase
import logging

logger = logging.getLogger(__name__)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related('author', 'media', 'community')
    serializer_class = PostSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        # Expect optional media id in request.data['media_id']
        media_id = self.request.data.get('media_id')
        media = None
        if media_id:
            media = get_object_or_404(Media, pk=media_id)
        # optional community id
        community = None
        community_id = self.request.data.get('community_id') or self.request.data.get('community')
        if community_id:
            community = get_object_or_404(Community, pk=community_id)
        serializer.save(author=self.request.user, media=media, community=community)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def relevant(self, request):
        # Simple personalized relevance: boost posts from authors the user interacted with
        user = request.user
        # build interaction counts: reactions and comments by the user to other authors
        interacted_authors = {}
        # comments by user -> posts' authors
        user_comments = Comment.objects.filter(user=user).select_related('post__author')
        for c in user_comments:
            a = c.post.author_id
            interacted_authors[a] = interacted_authors.get(a, 0) + 3
        # reactions by user -> content_object might be post or comment
        user_reacts = Reaction.objects.filter(user=user)
        for r in user_reacts:
            obj = r.content_object
            if hasattr(obj, 'author_id'):
                a = obj.author_id
                interacted_authors[a] = interacted_authors.get(a, 0) + 2
            elif hasattr(obj, 'user_id'):
                a = getattr(obj, 'user_id')
                interacted_authors[a] = interacted_authors.get(a, 0) + 1

        posts = list(Post.objects.all().select_related('author'))
        def score(p):
            base = p.relevance_score or 0
            boost = interacted_authors.get(p.author_id, 0)
            # time decay: more recent posts get slight boost
            age_hours = (timezone.now() - p.created_at).total_seconds() / 3600.0
            decay = max(0.1, 1.0 - age_hours / 168.0)
            return base * 0.6 + boost * 1.2 * decay

        posts.sort(key=lambda p: score(p), reverse=True)
        page = self.paginate_queryset(posts)
        serializer = PostSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().select_related('user', 'post', 'parent')
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        user = self.request.user
        parent = None
        parent_id = self.request.data.get('parent')
        post_id = self.request.data.get('post')
        post = get_object_or_404(Post, pk=post_id)
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
        comment = serializer.save(user=user, post=post, parent=parent)
        # update counts and notifications
        if parent:
            parent.increment_replies()
            Notification.objects.create(recipient=parent.user, actor=user, content_object=comment, notif_type='comment_reply', summary=f'{user} replied to your comment')
        else:
            Notification.objects.create(recipient=post.author, actor=user, content_object=comment, notif_type='post_reply', summary=f'{user} commented on your post')


class ReactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        # body: { type: 'like', content_type: 'post'|'comment', object_id: id }
        rtype = request.data.get('type')
        ctype = request.data.get('content_type')
        obj_id = request.data.get('object_id')
        if ctype not in ['post', 'comment']:
            return Response({'detail':'invalid content_type'}, status=status.HTTP_400_BAD_REQUEST)
        model = Post if ctype == 'post' else Comment
        target = get_object_or_404(model, pk=obj_id)
        content_type = ContentType.objects.get_for_model(model)
        # ensure single reaction per type per user
        obj, created = Reaction.objects.get_or_create(user=request.user, content_type=content_type, object_id=target.pk, type=rtype)
        if created:
            # increment counters
            if isinstance(target, Post):
                # optional: no counter field on post for reactions; keep in Reaction table
                pass
            else:
                Comment.objects.filter(pk=target.pk).update(reactions_count=F('reactions_count') + 1)
            # notify
            owner = target.author if hasattr(target, 'author') else target.user
            Notification.objects.create(recipient=owner, actor=request.user, content_object=target, notif_type=( 'post_reaction' if ctype=='post' else 'comment_reaction' ), summary=f'{request.user} reacted {rtype}')
        serializer = ReactionSerializer(obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def remove(self, request, pk=None):
        # remove a reaction by id if owned
        reaction = get_object_or_404(Reaction, pk=pk, user=request.user)
        # decrement counters if needed
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
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        ids = request.data.get('ids', [])
        qs = Notification.objects.filter(recipient=request.user, id__in=ids)
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
        # set creator automatically
        comm = serializer.save(created_by=self.request.user)
        # add creator as member by default
        try:
            comm.members.add(self.request.user)
            comm.members_count = comm.members.count()
            comm.save(update_fields=['members_count'])
        except Exception:
            pass

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def join(self, request, pk=None):
        comm = get_object_or_404(Community, pk=pk)
        comm.members.add(request.user)
        comm.members_count = comm.members.count()
        comm.save(update_fields=['members_count'])
        return Response({'joined': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def leave(self, request, pk=None):
        comm = get_object_or_404(Community, pk=pk)
        comm.members.remove(request.user)
        comm.members_count = comm.members.count()
        comm.save(update_fields=['members_count'])
        return Response({'left': True})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_cover(self, request, pk=None):
        """Upload a cover image for the community. Accepts multipart/form-data with file field 'file'."""
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
        """Upload an avatar image for the community. Accepts multipart/form-data with file field 'file'."""
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
