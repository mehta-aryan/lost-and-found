"""
Django settings for lostfound_project.

MVT Mapping (for viva):
  - Model  → items/models.py   (database schema, ORM)
  - View   → items/views.py    (business logic, request handling)
  - Template → items/templates/ (HTML presentation layer)
"""
import os
from pathlib import Path

# ──────────────────────────────────────────────
# BASE DIRECTORY
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────
# SECURITY (change SECRET_KEY in production!)
# ──────────────────────────────────────────────
SECRET_KEY = 'django-insecure-change-me-in-production-abc123xyz'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# ──────────────────────────────────────────────
# COLLEGE EMAIL DOMAIN RESTRICTION
# Change this to your college domain, e.g. "mycollege.edu"
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
    'django.contrib.sites',           # Required by allauth

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
        'DIRS': [BASE_DIR / 'templates'],   # Project-level templates
        'APP_DIRS': True,                    # Also look in app templates/ dirs
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',   # Required by allauth
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'items.context_processors.allowed_domain',   # Custom: ALLOWED_DOMAIN
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
# STATIC FILES (CSS, JS, images)
# Served by Django in development via {% static %} tag
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
    'django.contrib.auth.backends.ModelBackend',       # Default backend
    'allauth.account.auth_backends.AuthenticationBackend',  # allauth backend
]

# Allauth behaviour settings
ACCOUNT_LOGIN_METHODS = {"email"}                      # Login via email (Google provides it)
ACCOUNT_SIGNUP_FIELDS = ['email*']                     # Email is mandatory, skip username/password
ACCOUNT_EMAIL_VERIFICATION = 'none'                    # Skip email verification (Google already verifies)
SOCIALACCOUNT_AUTO_SIGNUP = True                       # Auto-create user on first Google login
SOCIALACCOUNT_LOGIN_ON_GET = True                      # Skip the intermediate "Continue?" page

LOGIN_URL = '/accounts/google/login/'                  # Redirect here when @login_required triggers
LOGIN_REDIRECT_URL = '/'                               # After login, go to dashboard
LOGOUT_REDIRECT_URL = '/'                              # After logout, go to landing / login page

# Google provider config
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {
            'client_id': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_ID',       # ← set your key
            'secret': 'REPLACE_WITH_YOUR_GOOGLE_CLIENT_SECRET',      # ← set your key
            'key': '',
        },
    },
}

# Custom adapter to restrict login to the college email domain
SOCIALACCOUNT_ADAPTER = 'items.adapter.CollegeEmailAdapter'
