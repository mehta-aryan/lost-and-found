"""
items/models.py — Database Models (the "M" in MVT)

  1. UserProfile  – extends Django's User with a profile picture
  2. ItemReport   – a lost / found item report
  3. Conversation – private chat thread between report poster and one visitor
  4. Message      – a single chat message within a Conversation
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


class Conversation(models.Model):
    """
    A private chat thread between the report's poster and one visitor.
    The visitor is stored as `participant`; the other side is always item.posted_by.
    A user cannot be participant of their own report (enforced in the view).
    """
    item = models.ForeignKey(ItemReport, on_delete=models.CASCADE, related_name='conversations')
    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['item', 'participant'], name='one_conversation_per_user_per_item'),
        ]

    def __str__(self):
        return f"Chat: {self.participant} ↔ {self.item.posted_by} re #{self.item_id}"

    def touch(self):
        """Bump updated_at so inbox sorts by last activity."""
        self.updated_at = timezone.now()
        self.save(update_fields=['updated_at'])

    def other_user(self, me):
        """Return the user on the other side of this conversation."""
        return self.item.posted_by if me == self.participant else self.participant


class Message(models.Model):
    """A single chat message."""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['conversation', 'created_at'])]

    def __str__(self):
        return f"Msg #{self.pk} by {self.sender} in conv #{self.conversation_id}"
