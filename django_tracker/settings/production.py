from .base import *

# Never respect the environment here: debug pages expose tracebacks,
# settings, and submitted reporter data. Production is always False;
# local and staging settings keep their own debug switches.
DEBUG = False

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