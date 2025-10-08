from django.conf import settings
from supabase import create_client

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def upload_image_to_supabase(file_obj, folder="profiles"):
    file_path = f"{folder}/{file_obj.name}"

    try:
        # 📤 Subir el archivo a Supabase Storage
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
