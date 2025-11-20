from pathlib import Path
import os
from dotenv import load_dotenv
from corsheaders.defaults import default_headers
import pymysql

# ------------------ PyMySQL como reemplazo de MySQLdb ------------------
pymysql.install_as_MySQLdb()

# ------------------ Cargar variables del .env ------------------
load_dotenv()

# ------------------ Paths ------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------ Seguridad ------------------
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-fixf01*gy+umo#bo)jxwct3t+7kdv3+xra8rf2&3d)*fczj#y6')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ------------------ Aplicaciones ------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'add',
    'auth_app',
    'profiles',
    'corsheaders',
    'channels',
    'chat',
    'drf_yasg',
    'media',
    'foro.apps.ForoConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'consultveterinarias.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'consultveterinarias.wsgi.application'
ASGI_APPLICATION = 'chat.asgi.application'

# ------------------ Base de datos ------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'defaultdb'),
        'USER': os.getenv('DB_USER', 'avnadmin'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'AVNS_h-YXgvsOZnaedCfDFKh'),
        'HOST': os.getenv('DB_HOST', 'mysql-1168837b-davilaeliseo453-fd06.d.aivencloud.com'),
        'PORT': int(os.getenv('DB_PORT', 17576)),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'",
            'ssl': {'ssl-mode': 'REQUIRED'},  # Aiven necesita SSL
        },
    }
}


# ------------------ Autenticación ------------------
AUTH_USER_MODEL = "auth_app.User"
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------ Internacionalización ------------------
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------ Archivos estáticos ------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
#STATICFILES_DIRS = [BASE_DIR / 'static']

# ------------------ Django REST Framework ------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'auth_app.api.authentication.BearerTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

# ------------------ CORS ------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://agrovets.vercel.app",
    "http://shante-klephtic-nahla.ngrok-free.dev",
]
CORS_ALLOW_HEADERS = list(default_headers) + ['authorization', 'ngrok-skip-browser-warning']
CORS_ALLOW_CREDENTIALS = True

# ------------------ Channels (WebSockets) ------------------
use_redis_channels = os.getenv('USE_REDIS_CHANNELS') == '1' or bool(os.getenv('REDIS_URL'))

if use_redis_channels:
    redis_url = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_url]},
        },
    }
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# ------------------ Supabase ------------------
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://kprsxavfuqotrgfxyqbj.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'sb_secret_8jlGXGcs3ubH-9v7T6riiw_Hbq28d0R')
SUPABASE_BUCKET = os.getenv('SUPABASE_BUCKET', 'agrovet-profile')

# ------------------ Logging ------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'chat': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}

# ------------------ Cache con Redis ------------------
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}
DEFAULT_CACHE_TIMEOUT = 60 * 5  # 5 minutos
