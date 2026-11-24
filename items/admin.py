"""
items/admin.py — Django admin registration.
"""
from django.contrib import admin
from django.utils import timezone

from .models import Conversation, ItemReport, Message, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_picture')
    search_fields = ('user__username', 'user__email')


@admin.register(ItemReport)
class ItemReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'report_type', 'category', 'status', 'location', 'date', 'posted_by', 'created_at')
    list_filter = ('report_type', 'status', 'category', 'date')
    list_editable = ('status',)
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('created_at', 'resolved_at')
    actions = ['mark_resolved']

    @admin.action(description='Mark selected reports as resolved')
    def mark_resolved(self, request, queryset):
        updated = queryset.filter(status=ItemReport.OPEN).update(
            status=ItemReport.RESOLVED, resolved_at=timezone.now())
        self.message_user(request, f'{updated} report(s) marked as resolved.')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sender', 'body', 'created_at', 'read_at')
    can_delete = False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('item', 'participant', 'created_at', 'updated_at')
    list_filter = ('item__report_type', 'item__status')
    search_fields = ('item__title', 'participant__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'created_at', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('body', 'sender__username')
    readonly_fields = ('created_at',)
