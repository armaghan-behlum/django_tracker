from .base import *

# get_env_variable returns a STRING; any non-empty value (including
# "False") is truthy, which turned debug pages on in production and
# exposed tracebacks, settings, and submitted data on errors.
DEBUG = get_env_variable('DEBUG') == 'True'

ALLOWED_HOSTS = ['tracker.arocaction.org', 
    'www.arocaction.org', 'arocaction.org', 
    'edtracker-93baffac3864.herokuapp.com']

DATABASES = {}

if "DATABASE_URL" in os.environ:
    # Configure Django for DATABASE_URL environment variable.
    DATABASES["default"] = dj_database_url.config(
        conn_max_age=MAX_CONN_AGE, ssl_require=True)

    # Enable test database if found in CI environment.
    if "CI" in os.environ:
        DATABASES["default"]["TEST"] = DATABASES["default"]

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
}

SECURE_SSL_REDIRECT = True

STATIC_URL = 'https://{0}/{1}/'.format(
    AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'