from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
import traceback
import logging

logger = logging.getLogger('chat.middleware')

User = get_user_model()


def _get_user_for_token_sync(token_key):
    """Synchronous helper to query the Token model. This will be run in a thread
    via `database_sync_to_async` to avoid calling ORM from the async loop.
    """
    try:
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()
    except Exception:
        traceback.print_exc()
        return AnonymousUser()


class QueryAuthMiddleware:
    """ASGI middleware to authenticate WebSocket connections using a
    `?token=<key>` query parameter.

    It uses `database_sync_to_async` to perform the DB lookup in a thread so
    we don't hit "You cannot call this from an async context" errors.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # decode and parse query string
        query_string = scope.get('query_string', b'')
        try:
            qs_text = query_string.decode()
        except Exception:
            qs_text = ''
        qs = parse_qs(qs_text)
        token_list = qs.get('token') or qs.get('access_token')

        user = AnonymousUser()
        # Debug prints so server console clearly shows token parsing steps
        try:
            if token_list:
                token_key = token_list[0]
                logger.debug('[QueryAuthMiddleware] raw_query_string=%s', qs_text)
                logger.debug('[QueryAuthMiddleware] token_candidate=%s', token_key)
                try:
                    user = await database_sync_to_async(_get_user_for_token_sync)(token_key)
                    if getattr(user, 'is_authenticated', False):
                        try:
                            logger.info('[QueryAuthMiddleware] token valid -> user_id=%s display=%s', user.id, getattr(user,'full_name', getattr(user,'username',None)))
                        except Exception:
                            logger.info('[QueryAuthMiddleware] token valid -> user (id/display unknown)')
                    else:
                        logger.info('[QueryAuthMiddleware] token NOT found in DB')
                except Exception as inner_exc:
                    logger.exception('QueryAuthMiddleware error while looking up token: %s', inner_exc)
            else:
                logger.debug('[QueryAuthMiddleware] no token found in query string: %s', qs_text)
        except Exception as e:
            logger.exception('QueryAuthMiddleware error while parsing token: %s', e)
            traceback.print_exc()

        scope['user'] = user
        return await self.inner(scope, receive, send)


def QueryAuthMiddlewareStack(inner):
    return QueryAuthMiddleware(inner)
