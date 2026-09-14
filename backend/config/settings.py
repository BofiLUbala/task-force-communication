"""
Django settings for the Task Force Présidentielle backend.
"""
# touch to force autoreload after .env changes (v3)

from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse, unquote

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

#: A deployment must never fall back to the shipped development key. Checked
#: here rather than in a runbook, because the failure is otherwise silent.
if not DEBUG and SECRET_KEY == 'django-insecure-change-me':
    raise ImproperlyConfigured(
        'SECRET_KEY must be set to a real secret when DEBUG is False.'
    )


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    'accounts',
    'content',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Must sit directly after SecurityMiddleware so static assets are served
    # without going through the rest of the stack.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# Managed Postgres providers hand out a single DATABASE_URL; the discrete
# DB_* variables stay the local convention. PostgreSQL either way — there is
# deliberately no SQLite fallback, so a misconfigured production environment
# fails loudly instead of quietly starting on an empty throwaway database.
def _database_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('postgres', 'postgresql', 'psql'):
        raise ImproperlyConfigured(f'Unsupported DATABASE_URL scheme: {parsed.scheme!r}')
    options = {}
    # Managed providers (Neon, Supabase, Render external) require TLS; the
    # flag travels in the URL as ?sslmode=require.
    if 'sslmode=' in (parsed.query or ''):
        for pair in parsed.query.split('&'):
            key, _, value = pair.partition('=')
            if key == 'sslmode':
                options['sslmode'] = value
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed.path.lstrip('/')),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': str(parsed.port or '5432'),
        'OPTIONS': options,
    }


DATABASE_URL = config('DATABASE_URL', default='')

if DATABASE_URL:
    DATABASES = {'default': _database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='taskforce_db'),
            'USER': config('DB_USER', default='taskforce_user'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

#: Reuse connections between requests instead of reconnecting on every one —
#: the single biggest latency win against a managed database.
DATABASES['default']['CONN_MAX_AGE'] = config('DB_CONN_MAX_AGE', default=60, cast=int)

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Kinshasa'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
#: `collectstatic` target. WhiteNoise serves this directory straight from the
#: application process, so the Django admin keeps its CSS without a separate
#: web server in front.
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media'))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# --------------------------------------------------------------------------
# Object storage for uploads (optional)
# --------------------------------------------------------------------------
# Uploads are the one thing that must outlive a container. On a platform with
# an ephemeral filesystem, point these at Cloudflare R2 (or any S3-compatible
# bucket) and every publication attachment survives a redeploy. Left empty,
# uploads stay on MEDIA_ROOT — correct only when that path is a persistent
# volume.
AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME', default='')
AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_S3_CUSTOM_DOMAIN = config('AWS_S3_CUSTOM_DOMAIN', default='')

USE_OBJECT_STORAGE = bool(AWS_STORAGE_BUCKET_NAME and AWS_ACCESS_KEY_ID)

if USE_OBJECT_STORAGE:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        'OPTIONS': {
            'bucket_name': AWS_STORAGE_BUCKET_NAME,
            'endpoint_url': AWS_S3_ENDPOINT_URL or None,
            'access_key': AWS_ACCESS_KEY_ID,
            'secret_key': AWS_SECRET_ACCESS_KEY,
            'custom_domain': AWS_S3_CUSTOM_DOMAIN or None,
            'file_overwrite': False,
            'querystring_auth': not AWS_S3_CUSTOM_DOMAIN,
            'default_acl': None,
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework / JWT
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS — web-app dev server
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173',
    cast=Csv(),
)
# Needed so the browser keeps the Django session cookie set when the SPA
# calls the social-accounts OAuth "start" endpoint cross-origin — that
# session is what verifies the OAuth "state" on the provider's callback.
CORS_ALLOW_CREDENTIALS = True

#: Django refuses cross-origin POSTs — the admin login included — unless the
#: scheme+host is listed here. Without it, the admin is unusable behind HTTPS
#: on a different hostname than the SPA.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000',
    cast=Csv(),
)

# --------------------------------------------------------------------------
# HTTPS hardening — production only
# --------------------------------------------------------------------------
# Kept behind `not DEBUG` so local development over plain HTTP still works;
# switching DEBUG off is what turns the whole set on.
if not DEBUG:
    # PaaS platforms terminate TLS at their edge and forward plain HTTP, so
    # Django only knows the request was secure from this header.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    # The SPA and the API are different hostnames, so the OAuth session cookie
    # has to survive a cross-site redirect back from Google/LinkedIn.
    SESSION_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SAMESITE = 'None'
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'

# Email
EMAIL_HOST = config('EMAIL_HOST', default=config('SMTP_HOST', default='smtp.gmail.com'))
EMAIL_PORT = config('EMAIL_PORT', default=config('SMTP_PORT', default=587, cast=int), cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=config('SMTP_USE_TLS', default=True, cast=bool), cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default=config('SMTP_USER', default=''))
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default=config('SMTP_PASSWORD', default=''))
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default=(
        'django.core.mail.backends.smtp.EmailBackend'
        if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD
        else 'django.core.mail.backends.console.EmailBackend'
    ),
)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=config('SMTP_FROM', default=EMAIL_HOST_USER))
CONTACT_EMAIL = config('CONTACT_EMAIL', default='contact@taskforce-presidentielle.cd')
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=15, cast=int)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

# Expo push notifications
EXPO_PUSH_URL = config('EXPO_PUSH_URL', default='https://exp.host/--/api/v2/push/send')

# open-wa (WhatsApp) bridge — optional, disabled by default
OPENWA_API_URL = config('OPENWA_API_URL', default='http://127.0.0.1:8002')
OPENWA_API_KEY = config('OPENWA_API_KEY', default='')
OPENWA_ENABLED = config('OPENWA_ENABLED', default=False, cast=bool)

# Social media auto-publishing — each platform is disabled until its
# developer app credentials are provided via environment variables.
SOCIAL_AUTH_REDIRECT_BASE = config('SOCIAL_AUTH_REDIRECT_BASE', default='http://localhost:8000')

#: Optional exact overrides, when one provider's console cannot follow the
#: shared base URL. Empty means "derive it from SOCIAL_AUTH_REDIRECT_BASE".
YOUTUBE_OAUTH_REDIRECT_URI = config('GOOGLE_OAUTH_REDIRECT_URI', default='')
LINKEDIN_OAUTH_REDIRECT_URI = config('LINKEDIN_OAUTH_REDIRECT_URI', default='')

LINKEDIN_CLIENT_ID = config('LINKEDIN_CLIENT_ID', default='')
LINKEDIN_CLIENT_SECRET = config('LINKEDIN_CLIENT_SECRET', default='')
LINKEDIN_ORGANIZATION_URN = config('LINKEDIN_ORGANIZATION_URN', default='')

GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = config('GOOGLE_CLIENT_SECRET', default='')
# public | unlisted | private — how uploaded videos appear on the channel.
YOUTUBE_PRIVACY_STATUS = config('YOUTUBE_PRIVACY_STATUS', default='public')

TIKTOK_CLIENT_KEY = config('TIKTOK_CLIENT_KEY', default='')
TIKTOK_CLIENT_SECRET = config('TIKTOK_CLIENT_SECRET', default='')

FACEBOOK_APP_ID = config('FACEBOOK_APP_ID', default='')
FACEBOOK_APP_SECRET = config('FACEBOOK_APP_SECRET', default='')
