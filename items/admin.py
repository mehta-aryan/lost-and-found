"""
items/admin.py — Register models with the Django admin site.

This lets you manage UserProfile and ItemReport objects
via /admin/ after creating a superuser.
"""
from django.contrib import admin
from .models import UserProfile, ItemReport


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_picture')
    search_fields = ('user__username', 'user__email')


@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'status', 'location', 'date', 'posted_by', 'created_at')
    list_filter = ('report_type', 'status', 'date')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('created_at',)

