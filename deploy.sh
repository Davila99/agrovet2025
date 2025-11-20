#!/usr/bin/env bash
# Script de despliegue mínimo para Railway / entornos Linux
# Ejecuta: ./deploy.sh (asegúrate de que tiene permisos de ejecución)

set -euo pipefail

echo "[deploy] Actualizando pip e instalando dependencias..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[deploy] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[deploy] Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo "[deploy] Comprobación rápida: mostrar estado de migraciones"
python manage.py showmigrations --list

echo "[deploy] Despliegue finalizado. Revisa logs si hay errores."
