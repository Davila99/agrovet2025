from rest_framework import viewsets
from profiles.models import Specialitys, BusinessOwner, ProfesionalPerfil
from .serializers import SpecialitysSerializer, BusinessOwnerSerializer, ProfesionalPerfilSerializer

class SpecialitysViewSet(viewsets.ModelViewSet):
    queryset = Specialitys.objects.all()
    serializer_class = SpecialitysSerializer

class BusinessOwnerViewSet(viewsets.ModelViewSet):
    queryset = BusinessOwner.objects.all()
    serializer_class = BusinessOwnerSerializer

class ProfesionalPerfilViewSet(viewsets.ModelViewSet):
    queryset = ProfesionalPerfil.objects.all()
    serializer_class = ProfesionalPerfilSerializer
