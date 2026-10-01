# Staging settings for the Railway review deployment: sqlite + local
# media on a mounted volume, whitenoise static, console email, no S3.
import os

from .base import *

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

_host = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")

ALLOWED_HOSTS = [
    h for h in (_host, "127.0.0.1", "localhost") if h
]

CSRF_TRUSTED_ORIGINS = (
    [f"https://{_host}"] if _host else []
)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "db.sqlite3",
    }
}

MEDIA_ROOT = DATA_DIR / "media"
MEDIA_URL = "media/"

MIDDLEWARE = (
    MIDDLEWARE[:1]
    + ["whitenoise.middleware.WhiteNoiseMiddleware"]
    + MIDDLEWARE[1:]
)

STATIC_URL = "static/"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
