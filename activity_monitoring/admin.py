from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import (
    ActivityScreenshot,
    EmployeeDevice,
)


@admin.register(EmployeeDevice)
class EmployeeDeviceAdmin(ModelAdmin):
    """
    Keep Device management in Admin for Token generation and status checks.
    """

    list_display = [
        "employee",
        "device_name",
        "status_indicator",
        "agent_version",
        "last_sync_error_display",
        "last_seen_display",
    ]
    list_filter = ["is_active", "agent_version"]
    readonly_fields = ["token", "created_at", "last_seen", "last_sync_error", "agent_version"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "device_name"]

    def status_indicator(self, obj):
        now = timezone.now()
        if not obj.last_seen:
            return format_html('<span style="color: gray;">⚫ Not Synced</span>')
        if (now - obj.last_seen) < timezone.timedelta(minutes=10):
            return format_html('<span style="color: #28a745; font-weight: bold;">🟢 Online</span>')
        return format_html('<span style="color: #6c757d;">⚪ Offline</span>')

    status_indicator.short_description = "Status"

    def last_sync_error_display(self, obj):
        if not obj.last_sync_error:
            return format_html('<span style="color: #28a745;">None</span>')
        return format_html('<span style="color: #dc3545;" title="{}">Error...</span>', obj.last_sync_error)

    last_sync_error_display.short_description = "Sync Health"

    def last_seen_display(self, obj):
        if not obj.last_seen:
            return "Never"
        return obj.last_seen.strftime("%Y-%m-%d %H:%M")

    last_seen_display.short_description = "Last Contact"


@admin.register(ActivityScreenshot)
class ActivityScreenshotAdmin(ModelAdmin):
    """
    Allow admins to see raw screenshot data if needed for audit.
    """

    list_display = ["employee", "timestamp", "active_window"]
    list_filter = ["timestamp"]
    readonly_fields = ["timestamp", "image_preview"]

    def active_window(self, obj):
        return obj.metadata.get("active_window", "Unknown")

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 500px;" />', obj.image.url)
        return "No Image"
