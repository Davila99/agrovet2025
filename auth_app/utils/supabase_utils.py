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
        # 📤 Subir el archivo a Supabase Storage
        # Usamos un nombre único generado arriba para evitar errores por recurso ya existente.
        res = supabase.storage.from_(settings.SUPABASE_BUCKET).upload(file_path, file_obj.read())

        # ✅ Verificar si hubo error
        if hasattr(res, "error") and res.error is not None:
            print("Error al subir a Supabase:", res.error)
            return None

        # 🌐 Obtener la URL pública (el SDK nuevo devuelve directamente el string)
        public_url = supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(file_path)

        print(f"✅ Imagen subida correctamente: {public_url}")
        return public_url

    except Exception as e:
        print("❌ Excepción al subir a Supabase:", e)
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
