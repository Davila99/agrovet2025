from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from ..models import SpecialistProfile, BusinessmanProfile, ConsumerProfile # CORRECCIÓN: Se usa '..' para apuntar al directorio padre (profiles)
from .serializers import (
    SpecialistProfileSerializer,
    BusinessmanProfileSerializer,
    ConsumerProfileSerializer
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from media.api.serializers import MediaSerializer
from auth_app.utils.supabase_utils import upload_image_to_supabase
from media.models import Media

# Clase base que implementa la lógica de seguridad para perfiles 1-a-1.
class UserProfileViewSet(viewsets.ModelViewSet):
    """ 
    Clase base para ViewSets de perfiles. 
    Asegura que un usuario solo pueda ver/modificar su propio perfil.
    """
    # Permiso requerido: solo usuarios autentados pueden acceder.
    permission_classes = [IsAuthenticated]

    # 1. Filtrar el QuerySet: solo devuelve el perfil vinculado al usuario de la solicitud.
    def get_queryset(self):
        # Devolvemos solo el perfil que pertenece al usuario que realiza la solicitud.
        if self.request.user.is_authenticated:
            # self.queryset se define en las clases hijas (e.g., SpecialistProfile.objects.all())
            return self.queryset.filter(user=self.request.user)
        return self.queryset.none() 

    # 2. Asignar Usuario en Creación: Asigna el usuario actual al perfil.
    def perform_create(self, serializer):
        # Antes de crear, verificamos si el perfil ya existe para este usuario
        if self.queryset.filter(user=self.request.user).exists():
            raise serializers.ValidationError("Este usuario ya tiene un perfil de este tipo. Utilice PUT o PATCH para actualizarlo.")
        
        # Guardamos la instancia asignando automáticamente el usuario logueado
        serializer.save(user=self.request.user)

# Vistas específicas para cada tipo de perfil

class SpecialistProfileViewSet(UserProfileViewSet):
    queryset = SpecialistProfile.objects.all()
    serializer_class = SpecialistProfileSerializer

    @action(detail=True, methods=['post'])
    def upload_work_images(self, request, pk=None):
        """Upload one or multiple images for this specialist profile.
        multipart/form-data with key 'images' as multiple files.
        """
        profile = self.get_object()
        files = request.FILES.getlist('images') or [request.FILES.get('image')] if request.FILES.get('image') else []
        if not files:
            return Response({'detail': 'No files provided.'}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        ct = ContentType.objects.get_for_model(SpecialistProfile)

        for f in files:
            url = upload_image_to_supabase(f, folder='media')
            m = Media.objects.create(name=f.name, description=request.data.get('description',''), url=url, content_type=ct, object_id=profile.pk)
            created.append(m)

        serializer = MediaSerializer(created, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class BusinessmanProfileViewSet(UserProfileViewSet):
    queryset = BusinessmanProfile.objects.all()
    serializer_class = BusinessmanProfileSerializer

class ConsumerProfileViewSet(UserProfileViewSet):
    queryset = ConsumerProfile.objects.all()
    serializer_class = ConsumerProfileSerializer