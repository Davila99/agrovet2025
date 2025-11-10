#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import subprocess


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'consultveterinarias.settings')

    # Detectamos si se llamó a runserver
    if "runserver" in sys.argv:
        # Por defecto host y puerto
        host = "127.0.0.1"
        port = "8000"

        # Revisamos si se pasó host:puerto o solo puerto
        for arg in sys.argv[1:]:
            if ":" in arg:
                host, port = arg.split(":")
            elif arg.isdigit():
                port = arg

        # Comando para iniciar Daphne
        cmd = [
            sys.executable,
            "-m",
            "daphne",
            "-b",
            host,
            "-p",
            port,
            "consultveterinarias.asgi:application"
        ]

        print(f"Iniciando Daphne en http://{host}:{port} ...")
        subprocess.call(cmd)
        sys.exit(0)  # Salimos para no ejecutar runserver normal

    # Si no es runserver, ejecutamos los comandos normales de Django
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
