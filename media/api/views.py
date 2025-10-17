from rest_framework import viewsets, status
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
        # Esperamos que la imagen venga en el campo 'image' si se sube
        image = request.FILES.get('image')
        data = request.data.copy()

        if image:
            url = upload_image_to_supabase(image, folder="media")
            if url:
                data['url'] = url

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        image = request.FILES.get('image')
        data = request.data.copy()

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
