"""
API views for Auth service.
"""
from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import sys
import os
import logging

from .serializers import (
    UserProfileImageUploadSerializer,
    UserRegisterSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    PhoneResetRequestSerializer,
    PhoneResetVerifySerializer,
)
from auth_app.models import User, PhoneResetCode
from auth_app.utils.supabase_utils import delete_image_from_supabase, upload_image_to_supabase
from auth_app.utils.sms_utils import send_sms_code

# Add common to path for events
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.events.kafka_producer import publish_user_event

logger = logging.getLogger(__name__)


@api_view(['POST'])
def request_password_reset_by_phone(request):
    """Solicitar reset de contraseña por SMS."""
    serializer = PhoneResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']

    try:
        user = User.objects.get(phone_number=phone)
    except User.DoesNotExist:
        return Response({'detail': 'No user with that phone.'}, status=404)

    import random
    code = f"{random.randint(100000, 999999):06d}"
    PhoneResetCode.objects.create(user=user, code=code)
    try:
        send_sms_code(phone, code)
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return Response({'detail': 'Failed to send SMS', 'error': str(e)}, status=500)

    return Response({'detail': 'Código enviado al número registrado.'})


@api_view(['POST'])
def verify_code_and_reset_password(request):
    """Verificar código y resetear contraseña."""
    serializer = PhoneResetVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    phone = serializer.validated_data['phone']
    code = serializer.validated_data['code']
    new_password = serializer.validated_data['new_password']

    reset = PhoneResetCode.objects.filter(
        user__phone_number=phone, code=code
    ).order_by('-created_at').first()
    
    if not reset or not reset.is_valid():
        return Response({'detail': 'Código inválido o expirado.'}, status=400)

    user = reset.user
    user.set_password(new_password)
    user.save()
    # Eliminar códigos usados
    PhoneResetCode.objects.filter(user=user).delete()
    
    # Publicar evento
    try:
        publish_user_event('user.password_reset', user.id, {
            'phone_number': phone,
        })
    except Exception as e:
        logger.error(f"Failed to publish user.password_reset event: {e}")
    
    return Response({'detail': 'Contraseña actualizada correctamente.'})


class RegisterViewSet(viewsets.ModelViewSet):
    """ViewSet para registro de usuarios."""
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        
        # Publicar evento de usuario creado
        try:
            publish_user_event('user.created', user.id, {
                'phone_number': user.phone_number,
                'full_name': user.full_name,
                'role': user.role,
            })
        except Exception as e:
            logger.error(f"Failed to publish user.created event: {e}")
        
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginViewSet(viewsets.ViewSet):
    """ViewSet para login de usuarios."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    
    def create(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        user = authenticate(request, phone_number=phone_number, password=password)

        if not user:
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)


class UploadProfilePictureView(APIView):
    """View para subir imagen de perfil."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserProfileImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            serializer.update(user, serializer.validated_data)
            
            # Publicar evento
            try:
                publish_user_event('user.updated', user.id, {
                    'profile_picture': user.profile_picture,
                })
            except Exception as e:
                logger.error(f"Failed to publish user.updated event: {e}")
            
            return Response({
                "message": "Imagen de perfil actualizada correctamente",
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(viewsets.ModelViewSet):
    """
    CRUD completo para el modelo User.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['full_name', 'last_name', 'phone_number', 'role']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegisterSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        """Actualiza datos de usuario y reemplaza imagen de perfil en Supabase si se envía una nueva."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
            validated_data = serializer.validated_data
        except Exception as exc:
            # Manejo tolerante de errores de profile_picture
            files = getattr(request, 'FILES', None)
            no_file = not files or 'profile_picture' not in files
            errors = getattr(exc, 'detail', None)
            has_picture_error = False
            if isinstance(errors, dict):
                has_picture_error = 'profile_picture' in errors
            if no_file and has_picture_error:
                try:
                    data = {k: v for k, v in request.data.items()}
                except Exception:
                    data = {}
                if 'profile_picture' in data:
                    data.pop('profile_picture')
                serializer = self.get_serializer(instance, data=data, partial=partial)
                serializer.is_valid(raise_exception=True)
                validated_data = serializer.validated_data
            else:
                raise

        # Validar cambio de role (nota: validación de perfiles se hace en profiles-service)
        new_role = validated_data.get('role')
        if new_role is not None:
            # Nota: La validación completa de perfiles se hace en profiles-service
            # Aquí solo validamos que el role sea válido
            valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
            if new_role not in valid_roles:
                return Response(
                    {'role': f'Role inválido. Debe ser uno de: {valid_roles}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Manejo de imagen de perfil
        image = validated_data.pop('profile_picture', None)
        if image:
            # Si el usuario ya tiene imagen, eliminar la anterior
            if instance.profile_picture:
                try:
                    old_image_path = instance.profile_picture.split("/")[-1]
                    delete_image_from_supabase(f"profiles/{old_image_path}")
                except Exception as e:
                    logger.warning(f"Error eliminando imagen anterior: {e}")

            # Subir la nueva imagen
            url = upload_image_to_supabase(image, folder="profiles")
            if url:
                instance.profile_picture = url

        # Actualizar otros campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        
        # Publicar evento
        try:
            publish_user_event('user.updated', instance.id, {
                'role': instance.role,
                'full_name': instance.full_name,
            })
        except Exception as e:
            logger.error(f"Failed to publish user.updated event: {e}")
        
        return Response(UserSerializer(instance).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Elimina un usuario y también su imagen de Supabase si existe."""
        instance = self.get_object()
        user_id = instance.id

        if instance.profile_picture:
            try:
                old_image_path = instance.profile_picture.split("/")[-1]
                delete_image_from_supabase(f"profiles/{old_image_path}")
            except Exception as e:
                logger.warning(f"Error eliminando imagen al borrar usuario: {e}")

        self.perform_destroy(instance)
        
        # Publicar evento
        try:
            publish_user_event('user.deleted', user_id, {
                'phone_number': instance.phone_number,
            })
        except Exception as e:
            logger.error(f"Failed to publish user.deleted event: {e}")
        
        return Response(
            {"message": "Usuario eliminado correctamente"},
            status=status.HTTP_204_NO_CONTENT
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def test_token_view(request):
    """
    Dev helper: POST {"phone_number": "..."} returns/creates a token for that user.
    
    WARNING: development helper only. Do not expose in production.
    """
    phone = request.data.get('phone_number')
    if not phone:
        return Response(
            {'error': 'phone_number required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        user = User.objects.get(phone_number=phone)
    except User.DoesNotExist:
        return Response(
            {'error': 'user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})

