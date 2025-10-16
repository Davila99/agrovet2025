from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from auth_app.models import User
from profiles.models import SpecialistProfile
from rest_framework.authtoken.models import Token
from django.contrib.auth.hashers import make_password


class ProfileRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_user_and_auth(self, phone='+59170000001'):
        # Crear usuario básico sin role
        user = User.objects.create(
            phone_number=phone,
            full_name='Test User',
            password=make_password('testpass123')
        )
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        return user

    def test_create_specialist_profile_updates_user_role(self):
        user = self.create_user_and_auth(phone='+59170000002')

        data = {
            "profession": "Veterinario",
            "experience_years": 3,
            "about_us": "Especialista en campo",
            "can_give_consultations": True
        }

        response = self.client.post('/api/profiles/specialists/', data, format='json')
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED))

        # Refrescar y comprobar role
        user.refresh_from_db()
        self.assertEqual(user.role, 'Specialist')

        # Comprobar que el perfil existe
        self.assertTrue(SpecialistProfile.objects.filter(user=user).exists())

    def test_delete_user_cascades_profile(self):
        # Crear usuario y perfil manualmente y comprobar la cascada
        user = User.objects.create(
            phone_number='+59170000003',
            full_name='User To Delete',
            password=make_password('testpass123')
        )
        profile = SpecialistProfile.objects.create(user=user, profession='Vet', experience_years=2)
        self.assertTrue(SpecialistProfile.objects.filter(user=user).exists())

        # Eliminar el usuario
        user.delete()

        # El perfil debe haber sido eliminado (cascada)
        self.assertFalse(SpecialistProfile.objects.filter(user=user).exists())
