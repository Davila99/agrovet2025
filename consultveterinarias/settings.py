from pathlib import Path
import os
from dotenv import load_dotenv
from corsheaders.defaults import default_headers
# Cargar las variables del archivo .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-fixf01*gy+umo#bo)jxwct3t+7kdv3+xra8rf2&3d)*fczj#y6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    'https://shante-klephtic-nahla.ngrok-free.dev',
]


# Application definition

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
    "chat",
    'drf_yasg',
    'media',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
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


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '3306'),
        # Ensure connections use utf8mb4 so 4-byte unicode (emoji) is supported.
        # This is the preferred permanent fix for emoji/storage issues.
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'",
        },
    }
}
## avoid printing secrets to stdout in production; use logging if needed
# print("DEBUG:", os.getenv('DEBUG'))
# print("DB_PASSWORD:", os.getenv('DB_PASSWORD'))



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = "auth_app.User"

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Additional static dirs for collectstatic to pick up
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration - prefer TokenAuthentication first so
# browser requests that include an Authorization: Token <key> header are
# authenticated by token and don't get blocked by SessionAuthentication CSRF checks.
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Accept both Bearer and Token schemes (BearerTokenAuthentication is a small subclass)
        'auth_app.api.authentication.BearerTokenAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    # For development ease we allow anonymous access by default.
    # Change to IsAuthenticated in production.
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

# CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://shante-klephtic-nahla.ngrok-free.dev",
    "http://localhost:5173",           # React local
    "https://agrovets.vercel.app",    # deploy (sin / al final)
]

# Allow the Authorization header for cross-origin requests (useful in dev)
CORS_ALLOW_HEADERS = list(default_headers) + [
    'authorization',
]
# If you need to send cookies for session auth from the frontend, enable this
CORS_ALLOW_CREDENTIALS = True

# Use the chat.asgi application which installs the QueryAuthMiddlewareStack
# so websocket connections can be authenticated via ?token=<key>
ASGI_APPLICATION = 'chat.asgi.application'
# Channel layer configuration
# - During development (DEBUG=True) prefer the in-memory channel layer so
#   websockets work without needing a local Redis instance. This is single-
#   process only and NOT suitable for production or multi-worker setups.
# - In non-DEBUG environments use channels_redis with host/port read from env.
if DEBUG:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }
else:
    # Support REDIS_URL (eg: redis://:password@host:port) which is convenient
    # for cloud providers like Upstash or Redis Cloud. If REDIS_URL is not set,
    # fall back to REDIS_HOST/REDIS_PORT tuple form.
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        hosts = [redis_url]
    else:
        hosts = [(
            os.getenv('REDIS_HOST', '127.0.0.1'),
            int(os.getenv('REDIS_PORT', '6379')),
        )]

    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": hosts,
            },
        },
    }
SUPABASE_URL = "https://kprsxavfuqotrgfxyqbj.supabase.co"
SUPABASE_KEY = "sb_secret_8jlGXGcs3ubH-9v7T6riiw_Hbq28d0R"
SUPABASE_BUCKET = "agrovet-profile"

# WhiteNoise static files storage for ASGI/Daphne
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Support ngrok dynamic origin (set NGROK_URL env var to full URL e.g. https://abc123.ngrok.io)
NGROK_URL = os.getenv('NGROK_URL')
if NGROK_URL:
    # CSRF_TRUSTED_ORIGINS requires the scheme
    CSRF_TRUSTED_ORIGINS = [NGROK_URL]
    try:
        CORS_ALLOWED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
    except Exception:
        CORS_ALLOWED_ORIGINS = []
    if NGROK_URL not in CORS_ALLOWED_ORIGINS:
        CORS_ALLOWED_ORIGINS.append(NGROK_URL)
    # If ALLOWED_HOSTS is not wildcard, append the ngrok host
    if ALLOWED_HOSTS != ['*']:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(NGROK_URL)
            if parsed.hostname and parsed.hostname not in ALLOWED_HOSTS:
                ALLOWED_HOSTS.append(parsed.hostname)
        except Exception:
            pass

# Cookie settings for cross-site requests (only when serving over HTTPS)
CSRF_COOKIE_SAMESITE = os.getenv('CSRF_COOKIE_SAMESITE', 'None')
SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'None')
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'True') == 'True'
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'True') == 'True'
CORS_ALLOW_CREDENTIALS = True



# Simple logging configuration for development to surface chat events
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'chat': {'handlers': ['console'], 'level': 'DEBUG'},
    },
}
