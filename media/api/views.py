from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from media.models import Media
from media.api.serializers import MediaSerializer
from auth_app.utils.supabase_utils import upload_image_to_supabase, delete_image_from_supabase
import logging

logger = logging.getLogger(__name__)


class MediaViewSet(viewsets.ModelViewSet):
    """ViewSet para listar, crear, editar y borrar Media. Soporta subida a Supabase."""
    queryset = Media.objects.all().order_by('-created_at')
    serializer_class = MediaSerializer
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        try:
            # Esperamos que la imagen venga en el campo 'image' si se sube
            image = request.FILES.get('image')
            # If frontend used a different field name (e.g. 'file' or 'media'),
            # fall back to the first uploaded file present.
            if not image and getattr(request, 'FILES', None):
                try:
                    image = next(iter(request.FILES.values()))
                except Exception:
                    image = None
            # Build a shallow dict from request.data to avoid deep-copying
            # uploaded file objects (which can raise 'cannot pickle BufferedRandom').
            try:
                data = {k: v for k, v in request.data.items()}
            except Exception:
                # Fallback to empty dict if something unexpected is present
                data = {}
            # Log incoming request for diagnosis (kept concise)
            try:
                logger.info("MediaViewSet.create incoming", extra={
                    'files': list(request.FILES.keys()),
                    'data_keys': list(request.data.keys()),
                    'user': getattr(request, 'user', None),
                    'auth_header': bool(request.META.get('HTTP_AUTHORIZATION'))
                })
            except Exception:
                logger.exception('Failed logging incoming request for MediaViewSet.create')

            # If an image is present, log some attributes for diagnosis
            if image:
                try:
                    logger.info('MediaViewSet.create incoming file', extra={
                        'name': getattr(image, 'name', None),
                        'size': getattr(image, 'size', None),
                        'content_type': getattr(image, 'content_type', None)
                    })
                except Exception:
                    logger.exception('Failed logging incoming file attributes')

            if image:
                url = upload_image_to_supabase(image, folder="media")
                try:
                    logger.info('upload_image_to_supabase returned', extra={'url': url})
                except Exception:
                    logger.exception('Failed logging supabase upload result')
                if url:
                    data['url'] = url

            # Use partial=True so clients can perform an "upload-first" flow
            # sending only the file (image) and url without being forced to provide
            # content_type/object_id at creation time.
            serializer = self.get_serializer(data=data, partial=True)
            # Log serializer initial data (concise)
            try:
                logger.info('serializer.initial_data', extra={'initial_data_keys': list(getattr(serializer, 'initial_data', {}).keys() if getattr(serializer,'initial_data',None) else [])})
            except Exception:
                logger.exception('Failed logging serializer initial data')

            # Validate explicitly to capture and log serializer errors for 400 responses
            if not serializer.is_valid():
                try:
                    logger.info('serializer validation errors', extra={'errors': serializer.errors})
                    logger.debug('incoming data for failed serializer', extra={'data_keys': list(data.keys())})
                except Exception:
                    logger.exception('Failed logging serializer errors')
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            # After saving, attempt to read back the created Media and log its description for debugging
            try:
                created_id = serializer.data.get('id')
                if created_id:
                    from media.models import Media as _Media
                    m = _Media.objects.filter(id=created_id).first()
                    if m is not None:
                        desc = getattr(m, 'description', None)
                        try:
                            logger.info('saved Media', extra={'id': m.id, 'description_len': len(str(desc))})
                        except Exception:
                            logger.exception('Failed logging saved Media details')
            except Exception:
                logger.exception('Error while attempting to log created media details')
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as exc:
            # Catch unexpected exceptions and return JSON instead of HTML
            logger.exception('unexpected exception in MediaViewSet.create')
            return Response({'detail': 'internal server error', 'error': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        image = request.FILES.get('image')
        if not image and getattr(request, 'FILES', None):
            try:
                image = next(iter(request.FILES.values()))
            except Exception:
                image = None
        try:
            data = {k: v for k, v in request.data.items()}
        except Exception:
            data = {}

        if image:
            # Intentamos borrar la anterior si existe
            if instance.url:
                delete_image_from_supabase(instance.url)
            url = upload_image_to_supabase(image, folder="media")
            if url:
                data['url'] = url

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Borrar de supabase si existe
        if instance.url:
            delete_image_from_supabase(instance.url)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='debug_description')
    def debug_description(self, request, pk=None):
        """Debug endpoint: returns raw description stored on Media (for troubleshooting spectrum)."""
        try:
            m = self.get_object()
            return Response({'id': m.id, 'description': getattr(m, 'description', None)})
        except Exception as e:
            return Response({'detail': 'error', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
