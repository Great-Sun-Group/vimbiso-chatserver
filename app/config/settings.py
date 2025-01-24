import os
from pathlib import Path
from decouple import config as env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Core settings
SECRET_KEY = env("DJANGO_SECRET")
DEBUG = env("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = env("ALLOWED_HOSTS", default="localhost 127.0.0.1").split(" ")

# Application definition
INSTALLED_APPS = [
    "django.contrib.auth",  # Required by DRF
    "django.contrib.contenttypes",  # Required by DRF
    "django.contrib.staticfiles",  # Required for collectstatic
    "corsheaders",  # For API security
    "core.config.apps.CoreConfig",  # Core bot app
]

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],  # Disable default auth
    'DEFAULT_PERMISSION_CLASSES': [],  # Disable default permissions
    'UNAUTHENTICATED_USER': None,  # Don't use django.contrib.auth.models.AnonymousUser
    'UNAUTHENTICATED_TOKEN': None,  # Don't use token authentication
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Storage paths
DEPLOYED_TO_AWS = env('DEPLOYED_TO_AWS', default=False, cast=bool)
if DEPLOYED_TO_AWS:
    BASE_PATH = "/efs-vols/app-data/data"
else:
    BASE_PATH = BASE_DIR / 'data'
    os.makedirs(BASE_PATH, exist_ok=True)

# Static files configuration
STATIC_URL = "/static/"
STATIC_ROOT = BASE_PATH / "static"

# Minimal SQLite database for Django internals (migrations, etc.)
# All application state is managed in Redis
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_PATH / 'db.sqlite3',  # Store in data directory
    }
}

# Redis configuration
REDIS_URL = env("REDIS_URL", default="redis://redis-state:6379/0")

# Cache configuration using Redis - shared with application state management
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,  # seconds
            "SOCKET_TIMEOUT": 5,  # seconds
            "RETRY_ON_TIMEOUT": True,
            "MAX_CONNECTIONS": 10,
            "HEALTH_CHECK_INTERVAL": 30,  # seconds
            "CONNECTION_POOL_CLASS": "redis.ConnectionPool",
            # Removed PARSER_CLASS since it's causing issues with newer Redis versions
            "REDIS_CLIENT_KWARGS": {
                "decode_responses": True  # Match existing client configuration
            }
        },
        "KEY_PREFIX": "vimbiso",  # Namespace cache keys
        "TIMEOUT": None,  # Disable cache timeouts since we're using it for state
    }
}


# Security settings
CORS_ALLOW_HEADERS = ["apiKey"]  # For WhatsApp webhook
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        # Core application logging
        "core": {
            "handlers": ["console"],
            "level": env("APP_LOG_LEVEL", default="DEBUG"),
            "propagate": False,
        },
        # Django framework logging
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        # Third party libraries
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# Time zone
TIME_ZONE = "Africa/Harare"
USE_TZ = True

# Required Django setting
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
