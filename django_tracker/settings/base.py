import dj_database_url
import os

from django.core.exceptions import ImproperlyConfigured
from django.test.runner import DiscoverRunner
from pathlib import Path
from storages.backends.s3boto3 import S3Boto3Storage
from urllib import parse
from pathlib import Path

def get_env_variable(var_name):
    """Get the environment variable or return exception.""" 
    try:
        return os.environ[var_name] 
    except KeyError:
        error_msg = 'Set the {} environment 􏰁\
            variable'.format(var_name)
    raise ImproperlyConfigured(error_msg)

class StaticStorage(S3Boto3Storage):
    location = "static"
    default_acl = "public-read"


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = get_env_variable('DEBUG') == 'True'

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tracker',
    'crispy_forms',
    'crispy_bootstrap5',
    'django_extensions',
    'storages',
    'anymail',
    'hcaptcha',
]

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'django_tracker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_tracker.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

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

MAX_CONN_AGE = 600

# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_TZ = True

ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": get_env_variable('POSTMARK_API_KEY'),
    "POSTMARK_SENDER_DOMAIN": 'ccr.tools', 
}
EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
DEFAULT_FROM_EMAIL = "tracker@arocaction.org"
SERVER_EMAIL = "tracker@arocaction.org"

REDIS_URL = os.environ.get('REDIS_URL')

if REDIS_URL:
    parsed_url = parse.urlparse(REDIS_URL)
    query = dict(parse.parse_qsl(parsed_url.query))
    query['ssl_cert_reqs'] = 'CERT_NONE'
    new_query = parse.urlencode(query)

    REDIS_URL = parse.urlunparse(parsed_url._replace(query=new_query))

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

AWS_ACCESS_KEY_ID = get_env_variable('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_env_variable('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = get_env_variable('S3_BUCKET')
AWS_S3_CUSTOM_DOMAIN = '{}.s3.amazonaws.com'.format(
    AWS_STORAGE_BUCKET_NAME)
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'static'
AWS_PUBLIC_MEDIA_LOCATION = 'media/public'
AWS_PRIVATE_MEDIA_LOCATION = 'media/private'

STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATICFILES_STORAGE = 'StaticStorage'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'


# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Test Runner Config
class HerokuDiscoverRunner(DiscoverRunner):
    """Test Runner for Heroku CI, which provides a database for you.
    This requires you to set the TEST database (done for you by settings().)"""

    def setup_databases(self, **kwargs):
        self.keepdb = True
        return super(HerokuDiscoverRunner, self).setup_databases(**kwargs)

# Use HerokuDiscoverRunner on Heroku CI
if "CI" in os.environ:
    TEST_RUNNER = "gettingstarted.settings.HerokuDiscoverRunner"
# ---------------------------------------------------------------------
# HCAPTCHA (human verification on the intake form)
# ---------------------------------------------------------------------
# The captcha field only appears when a site key is configured, so
# local development without keys keeps working.
# Env var: HCAPTCHA_KEY (as configured on the production app). The
# Django setting itself must be named HCAPTCHA_SITEKEY because the
# django-hcaptcha package reads that name internally.
HCAPTCHA_SITEKEY = os.environ.get("HCAPTCHA_KEY", "")
HCAPTCHA_SECRET = os.environ.get("HCAPTCHA_SECRET", "")

# Public information sheet / data retention policy linked from the
# intake form. Overridable so the link can be corrected without a
# deploy.
DATA_RETENTION_DOC_URL = os.environ.get(
    "DATA_RETENTION_DOC_URL",
    "https://docs.google.com/document/d/"
    "1xSgz9NWLm-LIX1k4I75pnhXFrdoXPJxt3lVT3h04NYk/edit?tab=t.0",
)

# ---------------------------------------------------------------------
# UCP PORTAL
# ---------------------------------------------------------------------
# Service that holds per-district Uniform Complaint Procedures form
# specs and fills the district's official PDF. Used by the post-submit
# hand-off page (tracker.ucp).
# Server-sent complaint email is opt-in. A dedicated flag, not
# key-presence: POSTMARK_API_KEY is a required env in every deploy
# and holds placeholders in dev/staging, so its presence proves
# nothing. The admin flips UCP_EMAIL_DELIVERY=1 alongside the real
# Postmark key and a verified sender domain.
UCP_EMAIL_DELIVERY = os.environ.get("UCP_EMAIL_DELIVERY", "") == "1"

UCP_PORTAL_URL = os.environ.get(
    "UCP_PORTAL_URL",
    "https://ucp-complaint-helper-production.up.railway.app",
)
