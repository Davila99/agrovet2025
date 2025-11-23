# utilities for uploading files from Chat service to Media service
import os
import requests
import logging

logger = logging.getLogger(__name__)

def upload_file_to_media_service(file_obj, folder="media"):
    """Upload a file to the Media service via multipart/form-data.

    Args:
        file_obj: Django UploadedFile or file-like object.
        folder: Target folder in Supabase bucket (default "media").

    Returns:
        dict with keys ``id`` and ``url`` if successful, otherwise ``None``.
    """
    media_service_url = os.getenv("MEDIA_SERVICE_URL", "http://localhost:8001")
    endpoint = f"{media_service_url}/api/media/"
    # Ensure file pointer at start
    try:
        file_obj.seek(0)
    except Exception:
        pass
    files = {"image": (file_obj.name, file_obj.read())}
    data = {"folder": folder}
    try:
        response = requests.post(endpoint, files=files, data=data, timeout=10)
        if response.status_code in (200, 201):
            return response.json()
        else:
            logger.error("Failed to upload to Media service: %s %s", response.status_code, response.text)
    except Exception as e:
        logger.exception("Exception uploading file to Media service")
    return None
