"""
items/adapter.py — allauth adapters.

  • NoLocalSignupAdapter  – closes /accounts/signup/ so nobody can bypass Google
  • CollegeEmailAdapter   – only lets verified Google accounts from the
                            college domain (settings.ALLOWED_EMAIL_DOMAIN) in
"""
from django.conf import settings
from django.shortcuts import render
from allauth.account.adapter import DefaultAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class NoLocalSignupAdapter(DefaultAccountAdapter):
    """Disable email/password registration; accounts come from Google only."""

    def is_open_for_signup(self, request):
        return False


class CollegeEmailAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        # The social adapter defers to the account adapter by default,
        # which we closed above — so re-open it for Google sign-ups.
        return True

    def pre_social_login(self, request, sociallogin):
        """Runs after Google authenticates but before the user is logged in."""
        data = sociallogin.account.extra_data
        email = (data.get('email') or '').strip().lower()
        verified = data.get('email_verified', False)
        allowed = (getattr(settings, 'ALLOWED_EMAIL_DOMAIN', '') or '').lower()

        if allowed and not (verified and email.endswith('@' + allowed)):
            raise ImmediateHttpResponse(
                render(request, 'items/email_rejected.html', {
                    'email': email,
                    'allowed_domain': allowed,
                }, status=403)
            )
