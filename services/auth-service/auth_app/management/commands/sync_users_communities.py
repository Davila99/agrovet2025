from django.core.management.base import BaseCommand
from auth_app.models import User
import os
import requests
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync existing users into foro communities based on role via internal foro endpoint'

    def handle(self, *args, **options):
        foro_url = os.getenv('FORO_SERVICE_URL', 'http://foro-service:8005')
        secret = os.getenv('FORO_INTERNAL_SECRET', 'dev-internal-secret')
        url = f"{foro_url}/api/foro/internal/add_user/"

        users = User.objects.all()
        total = users.count()
        self.stdout.write(f"Syncing {total} users to foro communities...")
        for u in users:
            try:
                payload = {'user_id': u.id, 'role': u.role}
                headers = {'Content-Type': 'application/json', 'X-Internal-Secret': secret}
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
                if resp.status_code not in (200, 201):
                    logger.warning(f"Failed to sync user {u.id}: {resp.status_code} {resp.text}")
                else:
                    self.stdout.write(f"Synced user {u.id}")
            except Exception as e:
                logger.error(f"Error syncing user {u.id}: {e}")

        self.stdout.write(self.style.SUCCESS('Sync completed.'))
