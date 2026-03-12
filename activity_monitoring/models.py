import uuid

from django.db import models
from django.utils import timezone

from employees.models import Employee


class ActivitySession(models.Model):
    """
    Groups activity into sessions (e.g., from clock-in to clock-out)
    to avoid querying millions of rows at once.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="activity_sessions")
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    total_productive_time = models.DurationField(default=timezone.timedelta(0))
    total_unproductive_time = models.DurationField(default=timezone.timedelta(0))

    class Meta:
        ordering = ["-start_time"]


class AppActivity(models.Model):
    """
    Tracks time spent on specific applications.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="app_activities")
    session = models.ForeignKey(ActivitySession, on_delete=models.CASCADE, related_name="apps", null=True, blank=True)
    app_name = models.CharField(max_length=255, db_index=True)
    window_title = models.CharField(max_length=500, blank=True, null=True)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    duration = models.DurationField()  # Pre-calculated duration for 'smooth' reporting

    # Metadata for productivity analysis
    is_productive = models.BooleanField(default=True)
    category = models.CharField(
        max_length=100, blank=True, null=True
    )  # e.g., 'Development', 'Social Media', 'Communication'

    class Meta:
        verbose_name_plural = "App Activities"
        indexes = [
            models.Index(fields=["employee", "start_time"]),
            models.Index(fields=["app_name"]),
        ]


class BrowserActivity(models.Model):
    """
    Tracks browser-specific activity (URLs, Titles, Searches).
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="browser_activities")
    session = models.ForeignKey(
        ActivitySession, on_delete=models.CASCADE, related_name="browser_logs", null=True, blank=True
    )
    url = models.URLField(max_length=2000)
    title = models.CharField(max_length=500, blank=True, null=True)
    search_query = models.CharField(max_length=500, blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    time_spent = models.DurationField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Browser Activities"
        indexes = [
            models.Index(fields=["employee", "timestamp"]),
        ]


class ActivityPulse(models.Model):
    """
    A lightweight 'heartbeat' to track if the user is active/idle.
    Stored in small batches to keep the system 'smooth'.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_idle = models.BooleanField(default=False)
    idle_duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        get_latest_by = "timestamp"


class EmployeeDevice(models.Model):
    """
    Represents a computer/device running the tracker.
    Stores the token used by the agent to authenticate.
    """

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="tracking_devices")
    device_name = models.CharField(max_length=255, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.device_name or 'Default Device'}"


class SystemEvent(models.Model):
    """
    Tracks hardware-level events like USB insertions, file transfers, or peripheral changes.
    """

    EVENT_TYPES = [
        ("USB_INSERT", "USB Device Inserted"),
        ("USB_REMOVE", "USB Device Removed"),
        ("NETWORK_CHANGE", "Network Connection Changed"),
        ("FILE_SYNC", "Large File Operation Detected"),
        ("FILE_TRANSFER", "Security Alert: File Transfer"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="system_events")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)  # To store drive letters, device names, etc.
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type} - {self.employee.user.username}"
