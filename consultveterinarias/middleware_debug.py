import logging

logger = logging.getLogger('django')


class LogAuthHeaderMiddleware:
    """Middleware temporal para debug: registra la cabecera Authorization.

    - Añadir en `MIDDLEWARE` solo en entornos de desarrollo.
    - No dejar habilitado en producción por seguridad.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            auth = request.META.get('HTTP_AUTHORIZATION')
            logger.debug("AUTH HEADER: %s METHOD: %s PATH: %s", auth, request.method, request.path)
        except Exception:
            logger.exception("Error leyendo cabecera Authorization")
        return self.get_response(request)
