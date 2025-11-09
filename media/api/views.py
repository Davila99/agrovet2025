from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from media.models import Media
from media.api.serializers import MediaSerializer
from auth_app.utils.supabase_utils import upload_image_to_supabase, delete_image_from_supabase


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
            # Log incoming request for debugging
            try:
                print(f"[MediaViewSet.create] files={list(request.FILES.keys())} data_keys={list(request.data.keys())} user={getattr(request,'user',None)} auth={request.META.get('HTTP_AUTHORIZATION')}")
            except Exception:
                pass

            # If an image is present, log some attributes for diagnosis
            if image:
                try:
                    print(f"[MediaViewSet.create] incoming file: name={getattr(image,'name',None)} size={getattr(image,'size',None)} content_type={getattr(image,'content_type',None)}")
                except Exception:
                    pass

            if image:
                url = upload_image_to_supabase(image, folder="media")
                try:
                    print(f"[MediaViewSet.create] upload_image_to_supabase returned: {url}")
                except Exception:
                    pass
                if url:
                    data['url'] = url

            # Use partial=True so clients can perform an "upload-first" flow
            # sending only the file (image) and url without being forced to provide
            # content_type/object_id at creation time.
            serializer = self.get_serializer(data=data, partial=True)
            # Log serializer initial data for debugging
            try:
                print(f"[MediaViewSet.create] serializer.initial_data: {getattr(serializer,'initial_data',None)}")
            except Exception:
                pass

            # Validate explicitly to capture and log serializer errors for 400 responses
            if not serializer.is_valid():
                try:
                    print(f"[MediaViewSet.create] serializer errors: {serializer.errors}")
                    print(f"[MediaViewSet.create] incoming data: {data}")
                except Exception:
                    pass
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
                            print(f"[MediaViewSet.create] saved Media id={m.id} description_preview={repr(desc)[:200]} desc_len={len(str(desc))}")
                        except Exception:
                            pass
            except Exception:
                pass
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as exc:
            # Catch unexpected exceptions and return JSON instead of HTML
            import traceback as _tb
            print('[MediaViewSet.create] unexpected exception:', exc)
            try:
                _tb.print_exc()
            except Exception:
                pass
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
