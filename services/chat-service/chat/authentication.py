"""
Custom authentication for Chat Service.
Validates tokens with Auth Service instead of Django's Token model.
"""
from rest_framework import authentication, exceptions
import sys
import os
import logging

# Add common to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from common.http_clients.auth_client import get_auth_client

logger = logging.getLogger(__name__)


class AuthServiceTokenAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication that validates tokens with Auth Service.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using token from Auth Service.
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        # Extract token (support both "Token <token>" and "Bearer <token>")
        parts = auth_header.split()
        if len(parts) != 2:
            return None
        
        auth_type, token = parts
        if auth_type.lower() not in ('token', 'bearer'):
            return None
        
        # Validate token with Auth Service
        try:
            auth_client = get_auth_client()
            user_data = auth_client.verify_token(token)
            
            if not user_data:
                logger.warning(f"Token validation failed for token: {token[:10]}...")
                raise exceptions.AuthenticationFailed('Token inválido.')
            
            # Create a simple user-like object
            class UserProxy:
                def __init__(self, user_data):
                    self.id = user_data.get('id')
                    self.is_authenticated = True
                    self.is_anonymous = False
                    self.full_name = user_data.get('full_name')
                    self.phone_number = user_data.get('phone_number')
                    self.profile_picture = user_data.get('profile_picture')
                    self.email = user_data.get('email')
            
            user = UserProxy(user_data)
            return (user, token)
            
        except exceptions.AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Error authenticating token: {e}")
            raise exceptions.AuthenticationFailed('Error al validar token.')





