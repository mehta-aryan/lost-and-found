"""
items/context_processors.py — Custom template context processors.

Makes ALLOWED_EMAIL_DOMAIN available in all templates as {{ ALLOWED_DOMAIN }}.
"""
from django.conf import settings


def allowed_domain(request):
    """Add the allowed email domain to every template context."""
    return {
        'ALLOWED_DOMAIN': getattr(settings, 'ALLOWED_EMAIL_DOMAIN', ''),
    }

