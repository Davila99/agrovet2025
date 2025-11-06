# run_daphne.py
import subprocess
import sys

"""
Este script arranca Daphne en desarrollo para manejar WebSockets y HTTP
igual que runserver, pero con soporte ASGI completo.
"""

# Puerto opcional, por defecto 8000
port = "8000"
if len(sys.argv) > 1:
    port = sys.argv[1]

# Comando Daphne
cmd = [
    sys.executable,  # python interpreter
    "-m",
    "daphne",
    "-b",
    "127.0.0.1",
    "-p",
    port,
    "consultveterinarias.asgi:application"
]

print(f"Iniciando Daphne en http://127.0.0.1:{port} ...")
subprocess.call(cmd)
