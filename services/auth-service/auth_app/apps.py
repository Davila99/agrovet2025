from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auth_app'
    def ready(self):
        # Import signals to register handlers
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass

