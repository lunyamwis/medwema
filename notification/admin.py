from django.contrib import admin
from django.utils.html import format_html

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "is_read",
        "read_badge",
        "created_at",
        "send_at",
    )
    list_filter = ("is_read", "created_at")
    search_fields = ("title", "body", "user__username", "user__email", "group_name")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    list_select_related = ("user",)
    ordering = ("-created_at",)
    actions = ["mark_read", "mark_unread"]

    @admin.display(description="Recipient", ordering="user__username")
    def recipient(self, obj):
        if obj.user:
            return obj.user.username
        return format_html('<span style="color:#94a3b8;">Broadcast</span>')

    @admin.display(description="Status")
    def read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color:#16a34a;font-weight:600;">● Read</span>')
        return format_html('<span style="color:#d97706;font-weight:600;">● Unread</span>')

    @admin.action(description="Mark selected as read")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")

    @admin.action(description="Mark selected as unread")
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")
