#!/usr/bin/env python
"""run_daphne.py

Arranca Daphne en desarrollo para manejar WebSockets y HTTP (ASGI).

Uso:
    python run_daphne.py [PORT] [HOST]

Ejemplo:
    python run_daphne.py 8000 127.0.0.1

El script usa el mismo intérprete Python/entorno virtual que se está
ejecutando (sys.executable) para invocar `python -m daphne ...`.
"""

import subprocess
import sys


def main():
    # Puerto y host opcionales
    port = "8000"
    host = "127.0.0.1"
    if len(sys.argv) > 1:
        port = sys.argv[1]
    if len(sys.argv) > 2:
        host = sys.argv[2]

    cmd = [
        sys.executable,
        "-m",
        "daphne",
        "-b",
        host,
        "-p",
        port,
        "consultveterinarias.asgi:application",
    ]

    print(f"Iniciando Daphne en http://{host}:{port} ...")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("Error: Daphne no parece estar instalado en este entorno.")
        print("Instala con: python -m pip install daphne")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Daphne terminó con código de salida {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
