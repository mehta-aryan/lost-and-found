"""
Django settings for lostfound_project.

MVT Mapping (for viva):
  - Model    → items/models.py          (database schema via Django ORM)
  - View     → items/views.py           (business logic, request handling)
  - Template → items/templates/, templates/  (HTML presentation with DTL)
"""
import os
from pathlib import Path

# ──────────────────────────────────────────────
# BASE DIRECTORY
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# SECURITY
# In production set the DJANGO_SECRET_KEY environment variable.
# The fallback value below is only for local development.
# ──────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-only-change-me-abc123xyz',
)
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# ──────────────────────────────────────────────
# COLLEGE EMAIL DOMAIN RESTRICTION
# ← Change "gmail.com" to your college domain, e.g. "mycollege.edu"
# ──────────────────────────────────────────────
ALLOWED_EMAIL_DOMAIN = "gmail.com"

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
    'allauth',                         # django-allauth core
    'allauth.account',                 # allauth account management
    'allauth.socialaccount',           # social login support
    'allauth.socialaccount.providers.google',  # Google OAuth provider

    # Our app
    'items',
]

# ──────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Required by allauth
]

ROOT_URLCONF = 'lostfound_project.urls'

# ──────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Project-level templates (base.html)
        'APP_DIRS': True,                    # Also look in each app's templates/ dir
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',   # Required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'items.context_processors.allowed_domain',      # Adds ALLOWED_DOMAIN
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

# ──────────────────────────────────────────────
# PASSWORD VALIDATION
# ──────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ──────────────────────────────────────────────
# INTERNATIONALIZATION
# ──────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ──────────────────────────────────────────────
# STATIC FILES (CSS, JS, images bundled with the project)
# Served by Django in dev via {% static %} template tag
# ──────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']  # Project-level static folder

# ──────────────────────────────────────────────
# MEDIA FILES (user-uploaded images)
# ──────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ──────────────────────────────────────────────
# DEFAULT PRIMARY KEY FIELD TYPE
# ──────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────
# DJANGO-ALLAUTH CONFIGURATION
# ──────────────────────────────────────────────
SITE_ID = 1   # Required by allauth; matches the default Site object

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',           # Default Django backend
    'allauth.account.auth_backends.AuthenticationBackend', # allauth social backend
]

# Allauth behaviour settings
ACCOUNT_LOGIN_METHODS = {"email"}                      # Login via email (Google provides it)
ACCOUNT_SIGNUP_FIELDS = ['email*']                     # Email is mandatory, skip username/password
ACCOUNT_EMAIL_VERIFICATION = 'none'                    # Skip verification (Google already verifies)
SOCIALACCOUNT_AUTO_SIGNUP = True                       # Auto-create user on first Google login
SOCIALACCOUNT_LOGIN_ON_GET = True                      # Skip the intermediate "Continue?" page

LOGIN_URL = '/accounts/google/login/'                  # Redirect here when @login_required triggers
LOGIN_REDIRECT_URL = '/'                               # After login → dashboard
LOGOUT_REDIRECT_URL = '/'                              # After logout → landing page

# Google provider config
# ← Replace these placeholders with your Google Cloud OAuth credentials
#   (or add them as a SocialApp in Django admin — see README.md)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID',
            'secret': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET',
            'key': '',
        },
    },
}

# Custom allauth adapter to restrict login to the college email domain
SOCIALACCOUNT_ADAPTER = 'items.adapter.CollegeEmailAdapter'

# ──────────────────────────────────────────────
# IMAGE UPLOAD LIMITS (used by ItemReportForm validation)
# ──────────────────────────────────────────────
MAX_UPLOAD_SIZE_MB = 5                                 # Max image upload size in MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
