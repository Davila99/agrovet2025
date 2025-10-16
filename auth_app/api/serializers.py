from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from auth_app.models import User
from auth_app.utils.supabase_utils import upload_image_to_supabase
from profiles.models import BusinessmanProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'last_name', 'phone_number', 'role', 'bio', 'profile_picture', 'latitude', 'longitude']
class BusinessmanProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)   # 🔹 igual que hiciste con AsignaturaSerializer en el otro ejemplo

    class Meta:
        model = BusinessmanProfile
        fields = '__all__'
class UserProfileImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

    def update(self, instance, validated_data):
        image = validated_data['image']
        url = upload_image_to_supabase(image, folder="profiles")
        if url:
            instance.profile_picture = url
            instance.save()
        return instance

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False)  # Acepta imagen opcional

    class Meta:
        model = User
        fields = ['id', 'full_name', 'last_name', 'phone_number', 'password', 'role', 'bio', 'profile_picture', 'latitude', 'longitude']

    def create(self, validated_data):
        image = validated_data.pop('profile_picture', None)  # Extraemos la imagen si viene
        validated_data['password'] = make_password(validated_data['password'])

        user = User.objects.create(**validated_data)

        if image:
            # Subimos a Supabase y guardamos la URL
            url = upload_image_to_supabase(image, folder="profiles")
            user.profile_picture = url
            user.save()

        return user

class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)
