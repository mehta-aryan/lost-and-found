"""
Django settings for lostfound_project.

MVT Mapping (for viva):
  - Model    → items/models.py          (database schema via Django ORM)
  - View     → items/views.py           (business logic, request handling)
  - Template → items/templates/, templates/  (HTML presentation with DTL)

Configuration is read from environment variables (see .env.example) so no
secrets are committed.  Sensible development defaults are provided.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Load KEY=value lines from a local .env file (if present) without extra packages.
# Real environment variables always win.
_env_file = BASE_DIR / '.env'
if _env_file.exists():
    for _line in _env_file.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _key, _value = _line.split('=', 1)
            os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))


def env_bool(name, default=False):
    return os.environ.get(name, '1' if default else '0').strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# ──────────────────────────────────────────────
# SECURITY
# DJANGO_DEBUG defaults to on for local development.
# In production set DJANGO_DEBUG=0 and provide DJANGO_SECRET_KEY.
# ──────────────────────────────────────────────
DEBUG = env_bool('DJANGO_DEBUG', default=True)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-change-me'
    else:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY when DJANGO_DEBUG=0.')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')

# Set DJANGO_HTTPS=1 when serving over HTTPS (cookies are then marked Secure).
if env_bool('DJANGO_HTTPS'):
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ──────────────────────────────────────────────
# COLLEGE EMAIL DOMAIN RESTRICTION
# Only Google accounts ending in this domain may sign in.
# "gmail.com" lets ANY Gmail user in — set your college domain
# (e.g. DJANGO_ALLOWED_EMAIL_DOMAIN=mycollege.edu) before going live.
# ──────────────────────────────────────────────
ALLOWED_EMAIL_DOMAIN = os.environ.get('DJANGO_ALLOWED_EMAIL_DOMAIN', 'gmail.com').strip().lower()

# ──────────────────────────────────────────────
# INSTALLED APPS
# ──────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',           # Required by django-allauth

    # Third-party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',

    # Our app
    'items',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'lostfound_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'items.context_processors.site_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'lostfound_project.wsgi.application'

# ──────────────────────────────────────────────
# DATABASE (SQLite for development)
# ──────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# STATIC + MEDIA
# ──────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'      # used by `collectstatic` in production

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Bootstrap has no "alert-error" class — map Django's ERROR level to "danger".
MESSAGE_TAGS = {message_constants.ERROR: 'danger'}

# ──────────────────────────────────────────────
# EMAIL (claim notifications)
# Prints emails to the console by default. For real email set
# DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# plus EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD.
# ──────────────────────────────────────────────
EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Campus Lost & Found <noreply@localhost>')

# ──────────────────────────────────────────────
# DJANGO-ALLAUTH
# ──────────────────────────────────────────────
SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*']
ACCOUNT_EMAIL_VERIFICATION = 'none'            # Google already verifies the address
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True              # skip the intermediate "Continue?" page

# Local sign-up is closed: accounts are only created via Google + domain check.
ACCOUNT_ADAPTER = 'items.adapter.NoLocalSignupAdapter'
SOCIALACCOUNT_ADAPTER = 'items.adapter.CollegeEmailAdapter'

LOGIN_URL = 'login'                            # our landing page, not straight to Google
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

_google = {
    'SCOPE': ['profile', 'email'],
    'AUTH_PARAMS': {'access_type': 'online', 'prompt': 'select_account'},
}
if ALLOWED_EMAIL_DOMAIN and ALLOWED_EMAIL_DOMAIN != 'gmail.com':
    _google['AUTH_PARAMS']['hd'] = ALLOWED_EMAIL_DOMAIN   # hint only; enforced in the adapter

# Credentials: set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET in the environment,
# OR leave them unset and add a "Social application" in /admin/ (see README).
if os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET'):
    _google['APP'] = {
        'client_id': os.environ['GOOGLE_CLIENT_ID'],
        'secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'key': '',
    }
SOCIALACCOUNT_PROVIDERS = {'google': _google}

# ──────────────────────────────────────────────
# APP SETTINGS
# ──────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = 5
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
ITEMS_PER_PAGE = 9
