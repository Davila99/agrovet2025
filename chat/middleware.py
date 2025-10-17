from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


class QueryAuthMiddleware:
    """Middleware ASGI para autenticar por ?token=<token> en la URL del websocket.

    Extrae token del query string y adjunta `scope['user']`.
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        query_string = scope.get('query_string', b'').decode()
        qs = parse_qs(query_string)
        token_list = qs.get('token') or qs.get('access_token')
        user = AnonymousUser()
        if token_list:
            token_key = token_list[0]
            try:
                token = Token.objects.select_related('user').get(key=token_key)
                user = token.user
            except Token.DoesNotExist:
                user = AnonymousUser()

        scope['user'] = user
        return self.inner(scope)


def QueryAuthMiddlewareStack(inner):
    return QueryAuthMiddleware(inner)
