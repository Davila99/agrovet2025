from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from ..models import SpecialistProfile, BusinessmanProfile, ConsumerProfile # CORRECCIÓN: Se usa '..' para apuntar al directorio padre (profiles)
from .serializers import (
    SpecialistProfileSerializer,
    BusinessmanProfileSerializer,
    ConsumerProfileSerializer
)

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

class BusinessmanProfileViewSet(UserProfileViewSet):
    queryset = BusinessmanProfile.objects.all()
    serializer_class = BusinessmanProfileSerializer

class ConsumerProfileViewSet(UserProfileViewSet):
    queryset = ConsumerProfile.objects.all()
    serializer_class = ConsumerProfileSerializer