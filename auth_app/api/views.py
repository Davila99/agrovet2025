# auth_app/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.views import APIView

from .serializers import (
    UserProfileImageUploadSerializer,
    UserRegisterSerializer,
    UserLoginSerializer,
    UserSerializer,
    BusinessmanProfileSerializer
)
from auth_app.models import User,BusinessmanProfile
from auth_app.utils.supabase_utils import delete_image_from_supabase, upload_image_to_supabase



class RegisterViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_201_CREATED)


class LoginViewSet(viewsets.ViewSet):
    def create(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']
        password = serializer.validated_data['password']

        user = authenticate(request, phone_number=phone_number, password=password)

        if not user:
            return Response({"error": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "user": UserSerializer(user).data,
            "token": token.key
        }, status=status.HTTP_200_OK)
class UploadProfilePictureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UserProfileImageUploadSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            serializer.update(user, serializer.validated_data)
            return Response({
                "message": "Imagen de perfil actualizada correctamente",
                "user": UserSerializer(user).data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserView(viewsets.ModelViewSet):
    """
    CRUD completo para el modelo User.
    Permite listar, crear, editar, eliminar y ver detalles de usuarios.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['full_name', 'last_name', 'phone_number', 'role']

    def get_serializer_class(self):
        # Si se está creando o actualizando un usuario, usa el serializer con password
        if self.action in ['create', 'update', 'partial_update']:
            return UserRegisterSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        """
        Actualiza datos de usuario y reemplaza imagen de perfil en Supabase si se envía una nueva.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Manejo de imagen de perfil
        image = validated_data.pop('profile_picture', None)
        if image:
            from auth_app.utils.supabase_utils import upload_image_to_supabase, delete_image_from_supabase

            # Si el usuario ya tiene imagen, eliminar la anterior
            if instance.profile_picture:
                try:
                    old_image_path = instance.profile_picture.split("/")[-1]
                    delete_image_from_supabase(f"profiles/{old_image_path}")
                except Exception as e:
                    print("⚠️ Error eliminando imagen anterior:", e)

            # Subir la nueva imagen
            url = upload_image_to_supabase(image, folder="profiles")
            if url:
                instance.profile_picture = url

        # Actualizar otros campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return Response(UserSerializer(instance).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """
        Elimina un usuario y también su imagen de Supabase si existe.
        """
        instance = self.get_object()

        if instance.profile_picture:
            try:
                old_image_path = instance.profile_picture.split("/")[-1]
                from auth_app.utils.supabase_utils import delete_image_from_supabase
                delete_image_from_supabase(f"profiles/{old_image_path}")
            except Exception as e:
                print("⚠️ Error eliminando imagen al borrar usuario:", e)

        self.perform_destroy(instance)
        return Response({"message": "Usuario eliminado correctamente"}, status=status.HTTP_204_NO_CONTENT)


class BusinessmanProfileViewSet(viewsets.ModelViewSet):
    queryset = BusinessmanProfile.objects.select_related('user').all()  # ⚡ optimiza la consulta
    serializer_class = BusinessmanProfileSerializer
    permission_classes = [permissions.AllowAny]