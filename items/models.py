"""
items/models.py — Database Models (the "M" in MVT)

Two models:
  1. UserProfile – extends Django's User with a profile picture
  2. ItemReport  – stores lost/found item reports
"""
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends the built-in User model with extra profile fields.
    Created automatically via a post_save signal (see signals.py).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        blank=True,
        null=True,
        help_text='Optional profile picture; a placeholder is used if empty.'
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_profile_picture_url(self):
        """Return the profile picture URL, or a placeholder if none uploaded."""
        if self.profile_picture:
            return self.profile_picture.url
        # UI-friendly placeholder (uses a free avatar service)
        return "https://ui-avatars.com/api/?name={}&background=0D6EFD&color=fff".format(
            self.user.get_full_name() or self.user.username
        )


class ItemReport(models.Model):
    """
    Represents a single lost or found item report.
    """
    # Choices for report_type
    LOST = 'LOST'
    FOUND = 'FOUND'
    REPORT_TYPE_CHOICES = [
        (LOST, 'Lost'),
        (FOUND, 'Found'),
    ]

    # Choices for status
    OPEN = 'OPEN'
    RESOLVED = 'RESOLVED'
    STATUS_CHOICES = [
        (OPEN, 'Open'),
        (RESOLVED, 'Resolved'),
    ]

    report_type = models.CharField(max_length=5, choices=REPORT_TYPE_CHOICES)
    title = models.CharField(max_length=200, help_text='Short heading for the item')
    description = models.TextField(help_text='Detailed description of the item')
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    location = models.CharField(max_length=200, help_text='Where the item was lost/found')
    date = models.DateField(help_text='Date the item was lost/found')
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=OPEN)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='item_reports')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['status', '-created_at']   # Open items first, newest on top

    def __str__(self):
        return f"[{self.report_type}] {self.title} ({self.status})"

