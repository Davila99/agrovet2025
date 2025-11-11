from django.core.management.base import BaseCommand
from auth_app.models import User
from profiles.models import SpecialistProfile, BusinessmanProfile, ConsumerProfile

class Command(BaseCommand):
    help = "Crea perfiles para usuarios que aún no los tienen según su rol"

    def handle(self, *args, **kwargs):
        created = 0
        for user in User.objects.all():
            role = (user.role or '').lower()
            try:
                if role == 'specialist' and not hasattr(user, 'specialist_profile'):
                    SpecialistProfile.objects.get_or_create(user=user)
                    created += 1
                elif role == 'businessman' and not hasattr(user, 'businessman_profile'):
                    BusinessmanProfile.objects.get_or_create(user=user)
                    created += 1
                elif role == 'consumer' and not hasattr(user, 'consumer_profile'):
                    ConsumerProfile.objects.get_or_create(user=user)
                    created += 1
            except Exception:
                # continuar con los demás usuarios; no abortar por un error en uno
                continue

        self.stdout.write(self.style.SUCCESS(f"✅ Perfiles sincronizados correctamente. Perfiles creados: {created}"))
