"""
ASGI middleware for authenticating WebSocket connections using token query parameter.
Validates tokens with Auth Service.
"""
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
import sys
import os
import logging

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_for_token(token_key):
    """
    Validate token with Auth Service and return user info.
    Returns a dict with user info or None.
    """
    try:
        auth_client = get_auth_client()
        user = auth_client.verify_token(token_key)
        if user:
            # Create a simple user-like object
            class UserProxy:
                def __init__(self, user_data):
                    self.id = user_data.get('id')
                    self.is_authenticated = True
                    self.is_anonymous = False
                    self.full_name = user_data.get('full_name')
                    self.phone_number = user_data.get('phone_number')
                    self.profile_picture = user_data.get('profile_picture')
            
            return UserProxy(user)
        return AnonymousUser()
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        return AnonymousUser()


class QueryAuthMiddleware:
    """
    ASGI middleware to authenticate WebSocket connections using a
    `?token=<key>` query parameter. Validates tokens with Auth Service.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Decode and parse query string
        query_string = scope.get('query_string', b'')
        try:
            qs_text = query_string.decode()
        except Exception:
            qs_text = ''
        
        qs = parse_qs(qs_text)
        token_list = qs.get('token') or qs.get('access_token')

        user = AnonymousUser()
        
        if token_list:
            token_key = token_list[0]
            logger.debug(f"[QueryAuthMiddleware] token_candidate={token_key[:10]}...")
            try:
                user = await _get_user_for_token(token_key)
                if hasattr(user, 'is_authenticated') and user.is_authenticated:
                    logger.info(f"[QueryAuthMiddleware] token valid -> user_id={user.id}")
                else:
                    logger.warning(f"[QueryAuthMiddleware] token invalid")
            except Exception as e:
                logger.error(f"[QueryAuthMiddleware] error validating token: {e}")
        else:
            logger.debug(f"[QueryAuthMiddleware] no token found in query string")

        scope['user'] = user
        return await self.inner(scope, receive, send)


def QueryAuthMiddlewareStack(inner):
    return QueryAuthMiddleware(inner)

