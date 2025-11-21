"""
Utilities for uploading and deleting files from Supabase Storage.
"""
from django.conf import settings
from supabase import create_client
import re
import uuid
import time
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
# Initialize Supabase client
supabase = None
if settings.SUPABASE_URL and settings.SUPABASE_KEY:
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.warning(f"Failed to initialize Supabase client: {e}")
else:
    logger.warning("Supabase credentials not found. Image upload will be disabled.")


def _sanitize_filename(name: str) -> str:
    """Sanitize filename to remove unsafe characters."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def upload_image_to_supabase(file_obj, folder="profiles"):
    """
    Upload an image file to Supabase Storage.
    
    Args:
        file_obj: File object to upload
        folder: Folder path in Supabase bucket
    
    Returns:
        Public URL of uploaded file or None if failed
    """
    # Generate unique filename to avoid conflicts
    original_name = getattr(file_obj, 'name', 'file')
    safe_name = _sanitize_filename(original_name)
    unique_prefix = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    file_path = f"{folder}/{unique_prefix}_{safe_name}"

    if not supabase:
        logger.warning("Supabase client not initialized. Skipping upload.")
        return None

    try:
        # Ensure file pointer is at start
        try:
            file_obj.seek(0)
        except Exception:
            pass

        # Read file bytes
        data_bytes = file_obj.read()

        # Upload to Supabase Storage
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(file_path, data_bytes)

        # Check for errors
        try:
            err = None
            if isinstance(res, dict):
                err = res.get('error') or res.get('error_description')
            else:
                err = getattr(res, 'error', None)
            if err:
                logger.error(f'Error uploading to Supabase: {err}')
                return None
        except Exception:
            pass

        # Get public URL
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
        
        # Handle different response formats
        if isinstance(public_url, dict):
            public_url = public_url.get('publicURL') or public_url.get('public_url') or public_url.get('url') or public_url.get('data')
            if isinstance(public_url, dict):
                public_url = public_url.get('publicURL') or public_url.get('url') or None

        if not isinstance(public_url, str):
            public_url = getattr(public_url, 'public_url', None) or getattr(public_url, 'url', None) or None

        if not public_url:
            logger.warning(f'Could not resolve public_url from Supabase response: {public_url}')
            return None

        logger.info(f"✅ Image uploaded successfully: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f'❌ Exception uploading to Supabase: {repr(e)}')
        return None


def delete_image_from_supabase(image_url):
    """
    Delete an image from Supabase Storage.
    
    Args:
        image_url: Public URL of the image to delete
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not supabase:
            logger.warning("Supabase client not initialized. Skipping deletion.")
            return False

        # Remove query parameters
        clean_url = image_url.split("?")[0]

        # Extract file path from URL
        pattern = rf"{settings.SUPABASE_BUCKET}/(.*)$"
        match = re.search(pattern, clean_url)
        if match:
            file_path = match.group(1)
        else:
            # Fallback: extract from URL
            parts = clean_url.split("/")
            if len(parts) >= 2:
                file_path = "/".join(parts[-2:])
            else:
                file_path = clean_url.split("/")[-1]

        # Delete file
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).remove([file_path])

        logger.info(f"🗑️ Deleted file from Supabase: {file_path}")
        return True

    except Exception as e:
        logger.error(f"⚠️ Error deleting image from Supabase: {e}")
        return False

