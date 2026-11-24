"""
items/context_processors.py — values available in every template.
"""
from django.conf import settings

from .models import Claim


def site_context(request):
    ctx = {
        'ALLOWED_DOMAIN': getattr(settings, 'ALLOWED_EMAIL_DOMAIN', ''),
        'MAX_UPLOAD_MB': getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5),
    }
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        ctx['pending_claims'] = Claim.objects.filter(
            item__posted_by=user, status=Claim.PENDING, item__status='OPEN',
        ).count()
        try:
            ctx['nav_avatar'] = user.profile.get_profile_picture_url()
        except Exception:        # profile missing (e.g. user created before signals)
            ctx['nav_avatar'] = ''
    return ctx
