from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from common.http_clients.auth_client import get_auth_client


class RemoteAuthServiceAuthentication(BaseAuthentication):
    """Authenticate requests by verifying tokens with the central Auth Service.

    This authentication class extracts the token from the `Authorization`
    header (supports both `Token` and `Bearer` schemes), calls the
    Auth Service via the shared `common.http_clients.auth_client` and,
    when valid, returns a lightweight user-like object.
    """

    def authenticate(self, request):
        raw = request.META.get('HTTP_AUTHORIZATION', '')
        token = raw.replace('Token ', '').replace('Bearer ', '') if raw else ''
        try:
            import logging
            logger = logging.getLogger('profiles.authentication')
            masked = (token[:6] + '...' + token[-4:]) if token and len(token) > 10 else (token[:3] + '...' if token else '')
            logger.debug(f"RemoteAuthServiceAuthentication: Authorization_present={bool(raw)} token_mask={masked} path={request.path}")
        except Exception:
            pass
        if not token:
            return None

        auth_client = get_auth_client()
        try:
            # Log where we're calling for easier tracing
            try:
                logger.debug(f"RemoteAuthServiceAuthentication: contacting auth service at {auth_client.base_url}/api/auth/users/me/ to verify token_mask={masked}")
            except Exception:
                pass
            user_data = auth_client.verify_token(token)
            if not user_data:
                try:
                    logger.warning(f"RemoteAuthServiceAuthentication: token verification failed for token_mask={masked}")
                except Exception:
                    pass
                raise AuthenticationFailed('Token inválido.')
        except AuthenticationFailed:
            raise
        except Exception as e:
            try:
                logger.error(f"RemoteAuthServiceAuthentication: unexpected error verifying token: {e}")
            except Exception:
                pass
            raise AuthenticationFailed('Token inválido.')

        # Build a minimal user-like object expected by DRF views
        class UserProxy:
            def __init__(self, data):
                self.id = data.get('id')
                self.username = data.get('username') or data.get('email')
                self.is_authenticated = True
                self.is_anonymous = False
                self.is_staff = data.get('is_staff', False)
                self.full_name = data.get('full_name')

            def __str__(self):
                return str(self.username or self.id)

        return (UserProxy(user_data), None)


class BearerTokenAuthentication:
    """Deprecated placeholder kept for compatibility (not used).

    We prefer `RemoteAuthServiceAuthentication` which validates tokens
    against the Auth Service instead of local DB-backed Token objects.
    """
    pass
