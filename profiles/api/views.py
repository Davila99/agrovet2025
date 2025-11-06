from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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

        # Evitar que un usuario tenga más de un tipo de perfil
        user = self.request.user
        has_spec = False
        has_bus = False
        has_cons = False
        try:
            _ = user.specialist_profile
            has_spec = True
        except Exception:
            pass
        try:
            _ = user.businessman_profile
            has_bus = True
        except Exception:
            pass
        try:
            _ = user.consumer_profile
            has_cons = True
        except Exception:
            pass

        # Si ya tiene otro tipo de perfil distinto al que se intenta crear, bloquear
        if self.serializer_class == SpecialistProfileSerializer and (has_bus or has_cons):
            raise serializers.ValidationError("El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario.")
        if self.serializer_class == BusinessmanProfileSerializer and (has_spec or has_cons):
            raise serializers.ValidationError("El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario.")
        if self.serializer_class == ConsumerProfileSerializer and (has_spec or has_bus):
            raise serializers.ValidationError("El usuario ya tiene otro tipo de perfil. Sólo se permite un rol por usuario.")

        # Guardamos la instancia asignando automaticamente el usuario logueado
        instance = serializer.save(user=self.request.user)

        # Sincronizar el role del usuario según el tipo de perfil creado
        try:
            user = self.request.user
            if isinstance(instance, SpecialistProfile):
                user.role = 'Specialist'
            elif isinstance(instance, BusinessmanProfile):
                # conservar la convención en minúsculas usada en User.ROLE_CHOICES
                user.role = 'businessman'
            elif isinstance(instance, ConsumerProfile):
                user.role = 'consumer'
            # Guardar solo el campo role para eficiencia
            user.save(update_fields=['role'])
        except Exception:
            # No fallar la creación del perfil si la sincronización del role falla; registrar/log si es necesario
            pass

# Vistas específicas para cada tipo de perfil

class SpecialistProfileViewSet(UserProfileViewSet):
    queryset = SpecialistProfile.objects.all()
    serializer_class = SpecialistProfileSerializer


    def create(self, request, *args, **kwargs):
        """Crear SpecialistProfile asignado al usuario autenticado.
        Reutiliza la validación del serializer y usa perform_create para coherencia.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Usar perform_create para aprovechar las validaciones adicionales
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

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