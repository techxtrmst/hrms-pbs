from datetime import timedelta

from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from .models import (
    ActivityPulse,
    ActivitySession,
    AppActivity,
    BrowserActivity,
    EmployeeDevice,
    SystemEvent,
)


@admin.register(EmployeeDevice)
class EmployeeDeviceAdmin(ModelAdmin):
    list_display = [
        "employee",
        "device_name_short",
        "status_indicator",
        "last_seen_display",
        "is_active",
        "created_at",
        "delete_button",
    ]
    list_filter = ["is_active", "created_at", "last_seen"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "device_name", "token"]
    readonly_fields = ["token", "created_at", "last_seen"]
    list_per_page = 50

    def delete_button(self, obj):
        url = reverse("admin:activity_monitoring_employeedevice_delete", args=[obj.pk])
        return format_html(
            '<a href="{}" class="px-2 py-1 text-xs font-semibold text-white bg-red-500 rounded hover:bg-red-600 transition-colors">Delete</a>',
            url,
        )

    delete_button.short_description = "Action"

    def device_name_short(self, obj):
        return obj.device_name[:50] + "..." if len(obj.device_name) > 50 else obj.device_name

    device_name_short.short_description = "Device"

    def status_indicator(self, obj):
        if not obj.last_seen:
            return format_html('<span style="color: gray;">⚫ Never Synced</span>')

        time_diff = timezone.now() - obj.last_seen
        if time_diff < timedelta(minutes=2):
            return format_html('<span style="color: green;">🟢 Online</span>')
        elif time_diff < timedelta(minutes=10):
            return format_html('<span style="color: orange;">🟠 Recently Active</span>')
        else:
            return format_html('<span style="color: red;">🔴 Offline</span>')

    status_indicator.short_description = "Status"

    def last_seen_display(self, obj):
        if not obj.last_seen:
            return "Never"
        time_diff = timezone.now() - obj.last_seen
        if time_diff < timedelta(minutes=1):
            return "Just now"
        elif time_diff < timedelta(hours=1):
            mins = int(time_diff.total_seconds() / 60)
            return f"{mins} min ago"
        elif time_diff < timedelta(days=1):
            hours = int(time_diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            return obj.last_seen.strftime("%Y-%m-%d %H:%M")

    last_seen_display.short_description = "Last Seen"


@admin.register(ActivitySession)
class ActivitySessionAdmin(ModelAdmin):
    list_display = ["employee", "start_time", "end_time", "is_active"]
    list_filter = ["start_time", "end_time"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    readonly_fields = ["start_time"]

    def is_active(self, obj):
        return obj.end_time is None

    is_active.boolean = True
    is_active.short_description = "Active"


@admin.register(AppActivity)
class AppActivityAdmin(ModelAdmin):
    list_display = ["employee", "app_name", "window_title_short", "start_time", "duration", "is_productive"]
    list_filter = ["is_productive", "start_time", "app_name"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "app_name", "window_title"]
    readonly_fields = ["start_time", "end_time"]
    list_per_page = 100

    def window_title_short(self, obj):
        return obj.window_title[:50] + "..." if len(obj.window_title) > 50 else obj.window_title

    window_title_short.short_description = "Window Title"


@admin.register(BrowserActivity)
class BrowserActivityAdmin(ModelAdmin):
    list_display = ["employee", "url_short", "title_short", "timestamp", "time_spent"]
    list_filter = ["timestamp"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "url", "title", "search_query"]
    readonly_fields = ["timestamp"]
    list_per_page = 100

    def url_short(self, obj):
        return obj.url[:40] + "..." if len(obj.url) > 40 else obj.url

    url_short.short_description = "URL"

    def title_short(self, obj):
        return obj.title[:50] + "..." if len(obj.title) > 50 else obj.title

    title_short.short_description = "Title"


@admin.register(SystemEvent)
class SystemEventAdmin(ModelAdmin):
    list_display = ["employee", "event_type", "description_short", "timestamp"]
    list_filter = ["event_type", "timestamp"]
    search_fields = ["employee__user__first_name", "employee__user__last_name", "description"]
    readonly_fields = ["timestamp", "metadata"]
    list_per_page = 100

    def description_short(self, obj):
        return obj.description[:60] + "..." if len(obj.description) > 60 else obj.description

    description_short.short_description = "Description"


@admin.register(ActivityPulse)
class ActivityPulseAdmin(ModelAdmin):
    list_display = ["employee", "timestamp", "is_idle", "idle_duration_display"]
    list_filter = ["is_idle", "timestamp"]
    search_fields = ["employee__user__first_name", "employee__user__last_name"]
    readonly_fields = ["timestamp"]
    list_per_page = 100

    def idle_duration_display(self, obj):
        if obj.idle_duration_seconds == 0:
            return "Active"
        mins = obj.idle_duration_seconds // 60
        secs = obj.idle_duration_seconds % 60
        return f"{mins}m {secs}s"

    idle_duration_display.short_description = "Idle Duration"  # Reload forced
