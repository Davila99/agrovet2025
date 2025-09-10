from rest_framework import viewsets
from .serializers import *

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class VetProfileViewSet(viewsets.ModelViewSet):
    queryset = VetProfile.objects.all()
    serializer_class = VetProfileSerializer

class AgronomoProfileViewSet(viewsets.ModelViewSet):
    queryset = AgronomoProfile.objects.all()
    serializer_class = AgronomoProfileSerializer

class PropietarioProfileViewSet(viewsets.ModelViewSet):
    queryset = PropietarioProfile.objects.all()
    serializer_class = PropietarioProfileSerializer

class SpecialtyViewSet(viewsets.ModelViewSet):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtySerializer

class UserSpecialtyViewSet(viewsets.ModelViewSet):
    queryset = UserSpecialty.objects.all()
    serializer_class = UserSpecialtySerializer

class WorkImageViewSet(viewsets.ModelViewSet):
    queryset = WorkImage.objects.all()
    serializer_class = WorkImageSerializer

class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class BlockViewSet(viewsets.ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer

class CallViewSet(viewsets.ModelViewSet):
    queryset = Call.objects.all()
    serializer_class = CallSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer

class AdImageViewSet(viewsets.ModelViewSet):
    queryset = AdImage.objects.all()
    serializer_class = AdImageSerializer
