"""
HTTP client for communicating with Media Service.
"""
import os
import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MediaServiceClient:
    """
    Client for Media Service API.
    """
    
    def __init__(self):
        self.base_url = os.getenv('MEDIA_SERVICE_URL', 'http://localhost:8001')
        self.timeout = int(os.getenv('MEDIA_SERVICE_TIMEOUT', '5'))
    
    def get_media(self, media_id: int) -> Optional[Dict[str, Any]]:
        """
        Get media by ID from Media Service.
        
        Args:
            media_id: Media ID
        
        Returns:
            Media data dict or None if not found
        """
        url = f"{self.base_url}/api/media/{media_id}/"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Media Service returned {response.status_code}: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Failed to get media from Media Service: {e}")
            return None
    
    def get_multiple_media(self, media_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get multiple media objects by IDs.
        
        Args:
            media_ids: List of media IDs
        
        Returns:
            List of media data dicts
        """
        results = []
        for media_id in media_ids:
            media = self.get_media(media_id)
            if media:
                results.append(media)
        return results


# Global instance
_media_client = None


def get_media_client() -> MediaServiceClient:
    """Get or create the global Media Service client."""
    global _media_client
    if _media_client is None:
        _media_client = MediaServiceClient()
    return _media_client

