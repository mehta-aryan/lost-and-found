"""
items/signals.py — Auto-create a UserProfile when a new User is created.

Uses Django's post_save signal so we never have to manually
create UserProfile objects.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile automatically when a new User is saved."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile whenever the User is saved."""
    # Use getattr to avoid errors if profile doesn't exist yet
    profile = getattr(instance, 'profile', None)
    if profile:
        profile.save()

