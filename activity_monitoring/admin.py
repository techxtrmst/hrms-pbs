from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import (
    ActivityScreenshot,
    EmployeeDevice,
)


@admin.register(EmployeeDevice)
class EmployeeDeviceAdmin(ModelAdmin):
    """
    Rich Device management with Unfold theme support.
    Provides visual health status for agent syncing.
    """

    list_display = [
        "employee",
        "device_name",
        "agent_version",
        "last_sync_error_display",
        "last_seen_display",
    ]
    readonly_fields = ["token", "created_at", "last_seen", "last_sync_error", "agent_version"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "device_name"]

    def last_sync_error_display(self, obj):
        if not obj.last_sync_error:
            return format_html('<span style="color: #10b981; font-weight: bold;">● Healthy (Synced)</span>')
        return format_html(
            '<span style="color: #ef4444; font-weight: bold;" title="{}">● Error (Check Logs)</span>',
            obj.last_sync_error[:200],
        )

    last_sync_error_display.short_description = "Sync Health"

    def last_seen_display(self, obj):
        if not obj.last_seen:
            return "Never"
        return obj.last_seen.strftime("%Y-%m-%d %H:%M")

    last_seen_display.short_description = "Last Contact"

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_staff


@admin.register(ActivityScreenshot)
class ActivityScreenshotAdmin(ModelAdmin):
    """
    Allow admins to see raw screenshot data if needed for audit.
    """

    list_display = ["employee", "timestamp", "active_window"]
    list_filter = ["timestamp"]
    readonly_fields = ["timestamp", "image_preview"]

    def active_window(self, obj):
        return obj.metadata.get("active_window") or "N/A"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 500px; border-radius: 8px;"/>', obj.image.url)
        return "No Image"

    image_preview.short_description = "Capture Preview"
