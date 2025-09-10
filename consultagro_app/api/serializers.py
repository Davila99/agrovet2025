from rest_framework import serializers

from consultagro_app.models import Ad, AdImage, AgronomoProfile, Block, Call, Chat, Message, Notification, PropietarioProfile, Specialty, User, UserSpecialty, VetProfile, WorkImage


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class VetProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VetProfile
        fields = '__all__'


class AgronomoProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgronomoProfile
        fields = '__all__'


class PropietarioProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropietarioProfile
        fields = '__all__'


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = '__all__'


class UserSpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSpecialty
        fields = '__all__'


class WorkImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkImage
        fields = '__all__'


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class BlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = '__all__'


class CallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Call
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = '__all__'


class AdImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdImage
        fields = '__all__'
