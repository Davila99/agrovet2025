# Procfile - elige UNA de las líneas siguientes según tu necesidad:
# Opción A — Solo HTTP (Gunicorn)
web: gunicorn consultveterinarias.wsgi:application --bind 0.0.0.0:$PORT

# Opción B — WebSockets + Channels (Daphne)
# web: daphne -b 0.0.0.0 -p $PORT consultveterinarias.asgi:application
