"""
HTTP client for communicating with Auth Service.
"""
import os
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AuthServiceClient:
    """
    Client for Auth Service API.
    """
    
    def __init__(self):
        self.base_url = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8002')
        self.timeout = int(os.getenv('AUTH_SERVICE_TIMEOUT', '5'))
    
    def get_user(self, user_id: int, token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get user by ID from Auth Service.
        
        Args:
            user_id: User ID
            token: Optional auth token for service-to-service communication
        
        Returns:
            User data dict or None if not found
        """
        url = f"{self.base_url}/api/auth/users/{user_id}/"
        headers = {}
        if token:
            # Support both Token and Bearer
            if token.startswith('Token ') or token.startswith('Bearer '):
                headers['Authorization'] = token
            else:
                headers['Authorization'] = f'Token {token}'
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Auth Service returned {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to get user from Auth Service: {e}")
            return None
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify auth token with Auth Service.
        Supports both 'Token' and 'Bearer' authentication.
        
        Args:
            token: Auth token (can be Token or Bearer format)
        
        Returns:
            User data if token is valid, None otherwise
        """
        url = f"{self.base_url}/api/auth/users/me/"
        # Try Token first, then Bearer
        for auth_type in ['Token', 'Bearer']:
            headers = {'Authorization': f'{auth_type} {token}'}
            try:
                response = requests.get(url, headers=headers, timeout=self.timeout)
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                logger.debug(f"Failed to verify token with {auth_type}: {e}")
                continue
        
        return None


# Global instance
_auth_client = None


def get_auth_client() -> AuthServiceClient:
    """Get or create the global Auth Service client."""
    global _auth_client
    if _auth_client is None:
        _auth_client = AuthServiceClient()
    return _auth_client

