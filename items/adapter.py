"""
items/adapter.py — Custom allauth adapter to restrict login to the college email domain.

The ALLOWED_EMAIL_DOMAIN setting in settings.py controls which domain is allowed.
"""
from django.conf import settings
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.shortcuts import render


class CollegeEmailAdapter(DefaultSocialAccountAdapter):
    """
    Blocks social login if the user's email does not match the allowed domain.
    """

    def pre_social_login(self, request, sociallogin):
        """Called after Google authenticates but before the user is logged in."""
        email = sociallogin.account.extra_data.get('email', '')
        allowed_domain = getattr(settings, 'ALLOWED_EMAIL_DOMAIN', '')

        if allowed_domain and not email.endswith('@' + allowed_domain):
            # Reject the login — render an error page
            raise ImmediateHttpResponse(
                render(request, 'items/email_rejected.html', {
                    'email': email,
                    'allowed_domain': allowed_domain,
                })
            )

