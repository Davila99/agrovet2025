from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    """Accept Authorization: Bearer <token> in addition to Token.

    Some frontends send 'Bearer' scheme; DRF's TokenAuthentication expects
    'Token'. This small subclass accepts 'Bearer' as the keyword.
    """
    keyword = 'Bearer'
