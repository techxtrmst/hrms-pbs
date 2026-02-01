"""
Models for the observability app.

Provides database models for:
- ErrorLog: Store exceptions with full stack traces
- RequestLog: HTTP request/response logging with timing
- PerformanceMetric: SQL query tracking and performance data
- ErrorGroup: Group similar errors together (like Sentry issues)
"""

import hashlib
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ErrorGroup(models.Model):
    """
    Groups similar errors together, like Sentry issues.

    Uses a fingerprint based on exception type, message pattern, and location.
    """

    class Status(models.TextChoices):
        UNRESOLVED = "unresolved", "Unresolved"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"
        MUTED = "muted", "Muted"

    class Level(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    fingerprint = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=500)
    culprit = models.CharField(max_length=500, blank=True, help_text="The function/module where the error originated")
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.ERROR)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNRESOLVED)

    exception_type = models.CharField(max_length=255, db_index=True)
    exception_value = models.TextField(blank=True)

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    event_count = models.PositiveIntegerField(default=1)
    user_count = models.PositiveIntegerField(default=0)

    # For tracking affected users
    affected_users = models.JSONField(default=list, blank=True)

    # Metadata
    tags = models.JSONField(default=dict, blank=True)
    is_regression = models.BooleanField(default=False, help_text="Was this error previously resolved?")

    # Assignment and notes
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_error_groups",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-last_seen"]
        verbose_name = "Error Group"
        verbose_name_plural = "Error Groups"
        indexes = [
            models.Index(fields=["status", "-last_seen"]),
            models.Index(fields=["exception_type", "-last_seen"]),
            models.Index(fields=["-event_count"]),
        ]

    def __str__(self):
        return f"{self.exception_type}: {self.title[:50]}"

    @classmethod
    def generate_fingerprint(cls, exception_type: str, exception_value: str, culprit: str) -> str:
        """Generate a unique fingerprint for grouping similar errors."""
        # Normalize the exception value (remove variable parts like IDs, timestamps)
        normalized_value = exception_value[:200] if exception_value else ""

        data = f"{exception_type}|{normalized_value}|{culprit}"
        return hashlib.sha256(data.encode()).hexdigest()[:64]

    def increment_event(self, user_id: str = None):
        """Increment event count and update last seen."""
        self.event_count = models.F("event_count") + 1
        self.last_seen = timezone.now()

        if user_id and user_id not in self.affected_users:
            if len(self.affected_users) < 100:  # Limit stored user IDs
                self.affected_users.append(user_id)
            self.user_count = len(set(self.affected_users))

        self.save(update_fields=["event_count", "last_seen", "affected_users", "user_count"])


class ErrorLog(models.Model):
    """
    Individual error/exception event with full details.

    Stores complete exception information including:
    - Full stack trace
    - Request context (headers, body, user)
    - Environment information
    - Custom context/tags
    """

    class Level(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(ErrorGroup, on_delete=models.CASCADE, related_name="events", null=True, blank=True)

    # Exception details
    exception_type = models.CharField(max_length=255, db_index=True)
    exception_value = models.TextField()
    exception_module = models.CharField(max_length=255, blank=True)

    # Stack trace - stored as JSON for structured access
    traceback_text = models.TextField(blank=True, help_text="Human-readable traceback")
    traceback_frames = models.JSONField(default=list, blank=True, help_text="Structured stack frames as JSON")

    # Error location
    culprit = models.CharField(max_length=500, blank=True, db_index=True)
    filename = models.CharField(max_length=500, blank=True)
    function = models.CharField(max_length=255, blank=True)
    lineno = models.PositiveIntegerField(null=True, blank=True)

    # Request context
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=2000, blank=True, db_index=True)
    request_url = models.URLField(max_length=2000, blank=True)
    request_query = models.TextField(blank=True, help_text="Query string parameters")
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = models.TextField(blank=True, help_text="Truncated request body")

    # User context
    user_id = models.CharField(max_length=255, blank=True, db_index=True)
    user_email = models.EmailField(blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    # Environment
    server_name = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=50, blank=True, default="production")
    release = models.CharField(max_length=100, blank=True, help_text="Application version/release")
    django_version = models.CharField(max_length=20, blank=True)
    python_version = models.CharField(max_length=20, blank=True)

    # Severity and categorization
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.ERROR)
    logger_name = models.CharField(max_length=255, blank=True)

    # Custom context
    extra_context = models.JSONField(default=dict, blank=True, help_text="Additional context data")
    tags = models.JSONField(default=dict, blank=True, help_text="Searchable tags")
    breadcrumbs = models.JSONField(default=list, blank=True, help_text="Event breadcrumbs/trail")

    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Performance context
    response_time_ms = models.FloatField(null=True, blank=True)
    sql_query_count = models.PositiveIntegerField(null=True, blank=True)
    sql_query_time_ms = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Error Log"
        verbose_name_plural = "Error Logs"
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["exception_type", "-timestamp"]),
            models.Index(fields=["level", "-timestamp"]),
            models.Index(fields=["request_path", "-timestamp"]),
            models.Index(fields=["user_id", "-timestamp"]),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.exception_type}: {self.exception_value[:50]}"

    def save(self, *args, **kwargs):
        """Override save to automatically group errors."""
        if not self.group_id and self.exception_type:
            fingerprint = ErrorGroup.generate_fingerprint(self.exception_type, self.exception_value, self.culprit)

            group, created = ErrorGroup.objects.get_or_create(
                fingerprint=fingerprint,
                defaults={
                    "title": self.exception_value[:500] if self.exception_value else self.exception_type,
                    "culprit": self.culprit,
                    "exception_type": self.exception_type,
                    "exception_value": self.exception_value[:1000] if self.exception_value else "",
                    "level": self.level,
                    "tags": self.tags,
                },
            )

            if not created:
                # Check for regression (was resolved, now occurring again)
                if group.status == ErrorGroup.Status.RESOLVED:
                    group.status = ErrorGroup.Status.UNRESOLVED
                    group.is_regression = True
                    group.save(update_fields=["status", "is_regression"])

                group.increment_event(self.user_id)

            self.group = group

        super().save(*args, **kwargs)


class RequestLog(models.Model):
    """
    HTTP request/response logging with timing and performance data.

    Tracks all requests for monitoring and debugging purposes.
    """

    class Method(models.TextChoices):
        GET = "GET", "GET"
        POST = "POST", "POST"
        PUT = "PUT", "PUT"
        PATCH = "PATCH", "PATCH"
        DELETE = "DELETE", "DELETE"
        HEAD = "HEAD", "HEAD"
        OPTIONS = "OPTIONS", "OPTIONS"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request_id = models.CharField(max_length=64, unique=True, db_index=True)

    # Request details
    method = models.CharField(max_length=10, choices=Method.choices)
    path = models.CharField(max_length=2000, db_index=True)
    full_url = models.URLField(max_length=2000, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    request_headers = models.JSONField(default=dict, blank=True)
    request_body = models.TextField(blank=True, help_text="Truncated request body")
    request_content_type = models.CharField(max_length=100, blank=True)

    # Response details
    status_code = models.PositiveSmallIntegerField(db_index=True)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body_size = models.PositiveIntegerField(null=True, blank=True, help_text="Response size in bytes")

    # User context
    user_id = models.CharField(max_length=255, blank=True, db_index=True)
    user_email = models.EmailField(blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    user_agent = models.CharField(max_length=500, blank=True)

    # Multi-tenant context
    company_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Performance metrics
    duration_ms = models.FloatField(help_text="Total request duration in milliseconds", db_index=True)
    time_to_first_byte_ms = models.FloatField(null=True, blank=True)

    # SQL query metrics
    sql_query_count = models.PositiveIntegerField(default=0)
    sql_query_time_ms = models.FloatField(default=0)
    sql_queries = models.JSONField(default=list, blank=True, help_text="List of SQL queries (if profiling enabled)")

    # View information
    view_name = models.CharField(max_length=255, blank=True, db_index=True)
    view_class = models.CharField(max_length=255, blank=True)

    # Metadata
    server_name = models.CharField(max_length=255, blank=True)
    environment = models.CharField(max_length=50, blank=True, default="production")

    # Error reference
    error_log = models.OneToOneField(
        ErrorLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="request_log"
    )
    has_error = models.BooleanField(default=False, db_index=True)

    # Timestamps
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Request Log"
        verbose_name_plural = "Request Logs"
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["status_code", "-timestamp"]),
            models.Index(fields=["path", "-timestamp"]),
            models.Index(fields=["user_id", "-timestamp"]),
            models.Index(fields=["has_error", "-timestamp"]),
            models.Index(fields=["-duration_ms"]),
        ]

    def __str__(self):
        return f"[{self.status_code}] {self.method} {self.path}"

    @property
    def is_slow(self) -> bool:
        """Check if request exceeded slow threshold (default 1000ms)."""
        return self.duration_ms > 1000

    @property
    def is_error(self) -> bool:
        """Check if response indicates an error."""
        return self.status_code >= 400


class PerformanceMetric(models.Model):
    """
    Aggregated performance metrics for endpoints.

    Stores hourly/daily aggregates for trend analysis.
    """

    class Period(models.TextChoices):
        HOURLY = "hourly", "Hourly"
        DAILY = "daily", "Daily"

    period = models.CharField(max_length=10, choices=Period.choices)
    period_start = models.DateTimeField(db_index=True)

    # Endpoint identification
    path_pattern = models.CharField(max_length=500, db_index=True, help_text="URL pattern (normalized)")
    method = models.CharField(max_length=10, blank=True)
    view_name = models.CharField(max_length=255, blank=True)

    # Request counts
    total_requests = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)  # 4xx/5xx responses
    success_count = models.PositiveIntegerField(default=0)  # 2xx/3xx responses

    # Duration statistics (in milliseconds)
    duration_avg = models.FloatField(default=0)
    duration_min = models.FloatField(default=0)
    duration_max = models.FloatField(default=0)
    duration_p50 = models.FloatField(default=0, help_text="50th percentile (median)")
    duration_p95 = models.FloatField(default=0, help_text="95th percentile")
    duration_p99 = models.FloatField(default=0, help_text="99th percentile")

    # SQL query statistics
    sql_count_avg = models.FloatField(default=0)
    sql_time_avg = models.FloatField(default=0)

    # Error rate
    error_rate = models.FloatField(default=0, help_text="Percentage of requests that errored")

    # Unique users
    unique_users = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start"]
        verbose_name = "Performance Metric"
        verbose_name_plural = "Performance Metrics"
        unique_together = ["period", "period_start", "path_pattern", "method"]
        indexes = [
            models.Index(fields=["period", "-period_start"]),
            models.Index(fields=["path_pattern", "-period_start"]),
            models.Index(fields=["-error_rate"]),
        ]

    def __str__(self):
        return f"{self.path_pattern} ({self.period}: {self.period_start})"


class SystemMetric(models.Model):
    """
    System-level metrics snapshot.

    Captures server health metrics at regular intervals.
    """

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    server_name = models.CharField(max_length=255, blank=True)

    # Request throughput
    requests_per_minute = models.PositiveIntegerField(default=0)
    errors_per_minute = models.PositiveIntegerField(default=0)

    # Response time (last minute aggregate)
    avg_response_time_ms = models.FloatField(default=0)
    p95_response_time_ms = models.FloatField(default=0)

    # Database
    db_connections_active = models.PositiveIntegerField(null=True, blank=True)
    db_connections_available = models.PositiveIntegerField(null=True, blank=True)

    # Memory (if available)
    memory_used_mb = models.FloatField(null=True, blank=True)
    memory_available_mb = models.FloatField(null=True, blank=True)

    # CPU (if available)
    cpu_percent = models.FloatField(null=True, blank=True)

    # Active users (last 5 minutes)
    active_users = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "System Metric"
        verbose_name_plural = "System Metrics"
        indexes = [
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"System Metrics at {self.timestamp}"


class LogEntry(models.Model):
    """
    General application log entries.

    Stores application logs for debugging and auditing.
    """

    class Level(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    level = models.CharField(max_length=20, choices=Level.choices, db_index=True)
    logger_name = models.CharField(max_length=255, db_index=True)
    message = models.TextField()

    # Source location
    filename = models.CharField(max_length=500, blank=True)
    function = models.CharField(max_length=255, blank=True)
    lineno = models.PositiveIntegerField(null=True, blank=True)
    module = models.CharField(max_length=255, blank=True)

    # Request context
    request_id = models.CharField(max_length=64, blank=True, db_index=True)
    user_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Additional data
    extra = models.JSONField(default=dict, blank=True)

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Log Entry"
        verbose_name_plural = "Log Entries"
        indexes = [
            models.Index(fields=["level", "-timestamp"]),
            models.Index(fields=["logger_name", "-timestamp"]),
            models.Index(fields=["request_id"]),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.logger_name}: {self.message[:50]}"
