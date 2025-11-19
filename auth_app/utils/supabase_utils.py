from django.conf import settings
from supabase import create_client
import re  # ✅ <-- Agregá esta línea
import uuid
import time

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def _sanitize_filename(name: str) -> str:
    # Simple sanitization: remove spaces and unsafe chars
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def upload_image_to_supabase(file_obj, folder="profiles"):
    # Generamos un nombre único para evitar conflictos 409 (resource exists)
    original_name = getattr(file_obj, 'name', 'file')
    safe_name = _sanitize_filename(original_name)
    unique_prefix = f"{int(time.time())}_{uuid.uuid4().hex}"
    file_path = f"{folder}/{unique_prefix}_{safe_name}"

    try:
        # Asegurarnos de leer desde el inicio si el file_obj soporta seek
        try:
            file_obj.seek(0)
        except Exception:
            pass

        # Leer bytes del archivo
        data_bytes = file_obj.read()

        # 📤 Subir el archivo a Supabase Storage
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(file_path, data_bytes)

        # El SDK puede devolver diferentes formas (objeto con .error, dict con 'error', etc.)
        # Normalizar la respuesta para diagnóstico
        try:
            # si es dict-like
            err = None
            if isinstance(res, dict):
                err = res.get('error') or res.get('error_description')
            else:
                # algún wrappers pueden exponer .error
                err = getattr(res, 'error', None)
            if err:
                print('Error al subir a Supabase:', err)
                return None
        except Exception:
            # si no podemos inspeccionar, seguimos y lo intentamos tomar como éxito
            pass

        # 🌐 Obtener la URL pública de manera robusta
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)
        # El SDK puede devolver un dict con keys diversas
        if isinstance(public_url, dict):
            # buscar los keys comunes
            public_url = public_url.get('publicURL') or public_url.get('public_url') or public_url.get('url') or public_url.get('data')
            # si es dict dentro de data
            if isinstance(public_url, dict):
                public_url = public_url.get('publicURL') or public_url.get('url') or None

        # Si sigue siendo un objeto con atributo 'public_url' o 'url'
        if not isinstance(public_url, str):
            public_url = getattr(public_url, 'public_url', None) or getattr(public_url, 'url', None) or None

        if not public_url:
            print('Advertencia: no se pudo resolver public_url desde la respuesta de Supabase', public_url)
            return None

        print(f"✅ Imagen subida correctamente: {public_url}")
        return public_url

    except Exception as e:
        # Log completo para diagnóstico (usar logging en producción)
        print('❌ Excepción al subir a Supabase:', repr(e))
        return None
def delete_image_from_supabase(image_url):
    try:
        # Quitar parámetros al final (como ?t=123456)
        clean_url = image_url.split("?")[0]

        # Extraer el path interno del bucket
        pattern = rf"{settings.SUPABASE_BUCKET}/(.*)$"
        match = re.search(pattern, clean_url)
        if match:
            file_path = match.group(1)
        else:
            # Si no coincide el patrón, tomamos lo que sigue después del último '/'
            file_path = clean_url.split("/")[-2] + "/" + clean_url.split("/")[-1] if "/" in clean_url else clean_url

        # 🗑️ Eliminar archivo
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).remove([file_path])

        print(f"🗑️ Intentando eliminar: {file_path}")
        print("🔍 Resultado de Supabase:", res)
        return True

    except Exception as e:
        print("⚠️ Error eliminando imagen en Supabase:", e)
        return False
