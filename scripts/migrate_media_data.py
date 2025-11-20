#!/usr/bin/env python3
"""
Script ETL para migrar datos de Media del monolito a media-service.
Ejecutar después de crear la nueva base de datos de media-service.
"""
import os
import sys
import django

# Setup Django para el monolito
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultveterinarias.settings')
django.setup()

from media.models import Media as MonolithMedia
import psycopg2
from psycopg2.extras import execute_values
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_media_data():
    """
    Migra todos los registros de Media del monolito a la nueva base de datos.
    """
    # Configuración de la nueva base de datos
    new_db_config = {
        'host': os.getenv('NEW_DB_HOST', 'localhost'),
        'port': os.getenv('NEW_DB_PORT', '5436'),
        'database': os.getenv('NEW_DB_NAME', 'media_db'),
        'user': os.getenv('NEW_DB_USER', 'agrovet'),
        'password': os.getenv('NEW_DB_PASSWORD', 'agrovet_dev'),
    }
    
    logger.info(f"Conectando a nueva base de datos: {new_db_config['database']}")
    
    try:
        # Conectar a nueva base de datos
        conn = psycopg2.connect(**new_db_config)
        cur = conn.cursor()
        
        # Obtener todos los registros del monolito
        logger.info("Obteniendo registros del monolito...")
        media_objects = MonolithMedia.objects.all()
        total = media_objects.count()
        logger.info(f"Total de registros a migrar: {total}")
        
        if total == 0:
            logger.info("No hay registros para migrar")
            return
        
        # Preparar datos para inserción
        records = []
        for media in media_objects:
            records.append((
                media.id,
                media.name or '',
                media.description or '',
                float(media.price) if media.price else 0.0,
                media.url or '',
                media.created_at.isoformat(),
                media.content_type_id if media.content_type else None,
                media.object_id if media.object_id else None,
            ))
        
        # Insertar en nueva base de datos
        logger.info("Insertando registros en nueva base de datos...")
        insert_query = """
            INSERT INTO media_media 
            (id, name, description, price, url, created_at, content_type_id, object_id)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """
        
        execute_values(cur, insert_query, records, page_size=100)
        conn.commit()
        
        logger.info(f"✅ Migrados {len(records)} registros exitosamente")
        
        # Verificar migración
        cur.execute("SELECT COUNT(*) FROM media_media")
        count = cur.fetchone()[0]
        logger.info(f"Total de registros en nueva base de datos: {count}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        raise


if __name__ == '__main__':
    logger.info("🚀 Iniciando migración de datos de Media...")
    migrate_media_data()
    logger.info("✅ Migración completada")

