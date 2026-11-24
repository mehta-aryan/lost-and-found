"""
items/models.py — Database Models (the "M" in MVT)

  1. UserProfile – extends Django's User with a profile picture
  2. ItemReport  – a lost / found item report
  3. Claim       – a message from one student to the poster of a report
                   ("I found this" / "This is mine")
"""
from urllib.parse import quote

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """Extra profile data. Created automatically via a signal (signals.py)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(
        upload_to='profile_pics/', blank=True, null=True,
        help_text='Optional profile picture; the Google avatar or initials are used if empty.',
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def get_profile_picture_url(self):
        """Uploaded picture → Google avatar → generated initials avatar."""
        if self.profile_picture:
            return self.profile_picture.url
        account = self.user.socialaccount_set.first()
        if account:
            url = account.get_avatar_url()
            if url:
                return url
        name = quote(self.user.get_full_name() or self.user.username)
        return f"https://ui-avatars.com/api/?name={name}&background=2F4EDD&color=fff"


class ItemReport(models.Model):
    """A single lost or found item report."""
    LOST, FOUND = 'LOST', 'FOUND'
    REPORT_TYPE_CHOICES = [(LOST, 'Lost'), (FOUND, 'Found')]

    OPEN, RESOLVED = 'OPEN', 'RESOLVED'
    STATUS_CHOICES = [(OPEN, 'Open'), (RESOLVED, 'Resolved')]

    ELECTRONICS, WALLET_ID, BAGS, KEYS = 'ELECTRONICS', 'WALLET_ID', 'BAGS', 'KEYS'
    BOOKS, ACCESSORIES, OTHER = 'BOOKS', 'ACCESSORIES', 'OTHER'
    CATEGORY_CHOICES = [
        (ELECTRONICS, 'Electronics'),
        (WALLET_ID, 'Wallets & ID cards'),
        (BAGS, 'Bags'),
        (KEYS, 'Keys'),
        (BOOKS, 'Books & stationery'),
        (ACCESSORIES, 'Clothing & accessories'),
        (OTHER, 'Other'),
    ]
    CATEGORY_ICONS = {
        ELECTRONICS: 'bi-phone',
        WALLET_ID: 'bi-wallet2',
        BAGS: 'bi-backpack2',
        KEYS: 'bi-key',
        BOOKS: 'bi-book',
        ACCESSORIES: 'bi-watch',
        OTHER: 'bi-tag',
    }

    report_type = models.CharField(max_length=5, choices=REPORT_TYPE_CHOICES)
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES, default=OTHER)
    title = models.CharField(max_length=200, help_text='Short heading for the item')
    description = models.TextField(help_text='Detailed description of the item')
    image = models.ImageField(upload_to='item_images/', blank=True, null=True)
    location = models.CharField(max_length=200, help_text='Where the item was lost/found')
    date = models.DateField(help_text='Date the item was lost/found')
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=OPEN)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='item_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # "OPEN" sorts before "RESOLVED" alphabetically, so open items come first.
        ordering = ['status', '-created_at']
        indexes = [models.Index(fields=['report_type', 'status', '-created_at'])]

    def __str__(self):
        return f"[{self.report_type}] {self.title} ({self.status})"

    @property
    def is_open(self):
        return self.status == self.OPEN

    @property
    def ticket_number(self):
        return f"{self.pk:04d}"

    @property
    def category_icon(self):
        return self.CATEGORY_ICONS.get(self.category, 'bi-tag')

    def mark_resolved(self):
        self.status = self.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolved_at'])


class Claim(models.Model):
    """A message to the poster: "I found this" (on a LOST report) or "this is mine" (on FOUND)."""
    PENDING, ACCEPTED, REJECTED = 'PENDING', 'ACCEPTED', 'REJECTED'
    STATUS_CHOICES = [(PENDING, 'Pending'), (ACCEPTED, 'Accepted'), (REJECTED, 'Declined')]

    item = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='claims')
    claimant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claims')
    message = models.TextField()
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['item', 'claimant'], name='one_claim_per_user_per_item'),
        ]

    def __str__(self):
        return f"Claim by {self.claimant} on #{self.item_id} ({self.status})"
