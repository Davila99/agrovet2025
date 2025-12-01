import os
import requests
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User

logger = logging.getLogger(__name__)


def _call_foro_add_user(user_id, role):
    try:
        foro_url = os.getenv('FORO_SERVICE_URL', 'http://foro-service:8005')
        secret = os.getenv('FORO_INTERNAL_SECRET', 'dev-internal-secret')
        url = f"{foro_url}/api/foro/internal/add_user/"
        payload = {'user_id': user_id, 'role': role}
        headers = {'Content-Type': 'application/json', 'X-Internal-Secret': secret}
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code not in (200, 201):
            logger.warning(f"_call_foro_add_user: unexpected status {resp.status_code} body={resp.text}")
        else:
            logger.info(f"_call_foro_add_user: user {user_id} synced to foro, resp={resp.text}")
    except Exception as e:
        logger.error(f"_call_foro_add_user error: {e}")


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """On user create or role change, inform foro-service to add user to communities."""
    try:
        role = instance.role
        user_id = instance.id
        # Best-effort: call foro internal endpoint asynchronously (fire-and-forget isn't implemented here)
        _call_foro_add_user(user_id, role)
    except Exception as e:
        logger.error(f"user_post_save signal error: {e}")
