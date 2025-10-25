from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate

from .serializers import UserProfileImageUploadSerializer, UserRegisterSerializer, UserLoginSerializer, UserSerializer
from auth_app.models import User
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


class RegisterViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegisterSerializer
    # Allow anonymous registration without CSRF/session auth for API clients
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

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
    # Disable default session authentication to avoid CSRF requirement on login
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
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
    queryset = User.objects.all()
    serializer_class = UserSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def test_token_view(request):
    """Dev helper: POST {"phone_number": "..."} returns/creates a token for that user.

    WARNING: development helper only. Do not expose in production.
    """
    phone = request.data.get('phone_number')
    if not phone:
        return Response({'error': 'phone_number required'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(phone_number=phone)
    except User.DoesNotExist:
        return Response({'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': UserSerializer(user).data})
