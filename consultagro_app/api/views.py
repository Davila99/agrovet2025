from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from .models import User
from .serializers import RegisterSerializer, UserSerializer, ProfessionalSerializer


# -------------------------
# Registro
# -------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# -------------------------
# Login
# -------------------------
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_number = request.data.get("phone_number")
        password = request.data.get("password")
        user = authenticate(request, phone_number=phone_number, password=password)

        if not user:
            return Response({"error": "Credenciales inválidas"}, status=400)

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user": UserSerializer(user).data
        })


# -------------------------
# Lista de Veterinarios
# -------------------------
class VeterinaryList(generics.ListAPIView):
    serializer_class = ProfessionalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role="veterinario")


# -------------------------
# Lista de Agrónomos
# -------------------------
class AgronomoList(generics.ListAPIView):
    serializer_class = ProfessionalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(role="agronomo")
