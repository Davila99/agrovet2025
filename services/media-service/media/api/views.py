"""
API views for Media service.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from media.models import Media
from media.api.serializers import MediaSerializer
from media.utils.supabase_utils import upload_image_to_supabase, delete_image_from_supabase
import sys, os, logging

# Add common to path for events
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.events.kafka_producer import publish_media_event

logger = logging.getLogger(__name__)

class MediaViewSet(viewsets.ModelViewSet):
    authentication_classes = []  # Allow unauthenticated access
    permission_classes = []      # Public endpoint
    queryset = Media.objects.all().order_by('-created_at')
    serializer_class = MediaSerializer
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        """Create a new Media object with optional file upload."""
        try:
            # Get uploaded file - support both 'image' and 'audio' fields
            image = request.FILES.get('image') or request.FILES.get('audio')
            if not image and getattr(request, 'FILES', None):
                try:
                    image = next(iter(request.FILES.values()))
                except Exception:
                    image = None

            # Prepare data
            data = {k: v for k, v in request.data.items()}

            logger.info("MediaViewSet.create", extra={
                'files': list(request.FILES.keys()),
                'data_keys': list(data.keys()),
                'user': str(request.user) if request.user.is_authenticated else None,
            })

            # Upload to Supabase if file provided
            if image:
                # Determine folder from request or default to 'media'
                folder = request.data.get('folder', 'media')
                url = upload_image_to_supabase(image, folder=folder)
                if url:
                    data['url'] = url
                    logger.info(f"File uploaded to Supabase: {url}")

            # Create Media object
            serializer = self.get_serializer(data=data, partial=True)
            if not serializer.is_valid():
                logger.warning(f"Serializer validation errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            # Publish event to Kafka
            try:
                publish_media_event('media.created', serializer.data['id'], {
                    'url': serializer.data.get('url'),
                    'name': serializer.data.get('name'),
                })
            except Exception as e:
                logger.error(f"Failed to publish media.created event: {e}")

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as exc:
            logger.exception('Unexpected exception in MediaViewSet.create')
            return Response(
                {'detail': 'internal server error', 'error': str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update a Media object, optionally replacing the file."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Get new file if provided
        image = request.FILES.get('image')
        if not image and getattr(request, 'FILES', None):
            try:
                image = next(iter(request.FILES.values()))
            except Exception:
                image = None

        data = {k: v for k, v in request.data.items()}

        # If new file provided, delete old one and upload new
        if image:
            if instance.url:
                delete_image_from_supabase(instance.url)
            url = upload_image_to_supabase(image, folder="media")
            if url:
                data['url'] = url

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Publish event
        try:
            publish_media_event('media.updated', instance.id, {
                'url': serializer.data.get('url'),
            })
        except Exception as e:
            logger.error(f"Failed to publish media.updated event: {e}")

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete a Media object and its file from Supabase."""
        instance = self.get_object()
        media_id = instance.id

        # Delete from Supabase
        if instance.url:
            delete_image_from_supabase(instance.url)

        self.perform_destroy(instance)

        # Publish event
        try:
            publish_media_event('media.deleted', media_id, {
                'url': instance.url,
            })
        except Exception as e:
            logger.error(f"Failed to publish media.deleted event: {e}")

        return Response(status=status.HTTP_204_NO_CONTENT)
