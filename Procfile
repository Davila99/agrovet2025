# Procfile - elige UNA de las líneas siguientes según necesites
# Opción A — WebSockets (Daphne) - recomendado si usas Channels
web: daphne -b 0.0.0.0 -p $PORT consultveterinarias.asgi:application

# Opción B — Solo HTTP (Gunicorn) - descomenta si no necesitas WebSockets
# web: gunicorn consultveterinarias.wsgi:application --bind 0.0.0.0:$PORT --workers 3
