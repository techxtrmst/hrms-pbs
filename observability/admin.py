"""
Admin configuration for the observability app.

Provides comprehensive admin views for:
- Error tracking and analysis
- Request log viewing and filtering
- Performance metrics visualization
- System health monitoring

All admin classes use Unfold styling for consistency.
Hidden from admin when debug mode is disabled.
"""

from django.contrib import admin
from django.template.defaultfilters import truncatechars
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from core.middleware import is_debug_mode_enabled

from .models import (
    ErrorGroup,
    ErrorLog,
    LogEntry,
    PerformanceMetric,
    RequestLog,
    SystemMetric,
)


class DebugModeAdminMixin:
    """
    Mixin that hides admin models when debug mode is disabled.

    When debug mode is off:
    - Model won't appear in admin index/app list
    - Direct access to changelist/change views is blocked
    """

    def has_module_permission(self, request):
        """Hide from admin app index when debug mode is off."""
        if not is_debug_mode_enabled(request):
            return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        """Block view access when debug mode is off."""
        if not is_debug_mode_enabled(request):
            return False
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        """Block change access when debug mode is off."""
        if not is_debug_mode_enabled(request):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Block delete access when debug mode is off."""
        if not is_debug_mode_enabled(request):
            return False
        return super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        """Block add access when debug mode is off."""
        if not is_debug_mode_enabled(request):
            return False
        return super().has_add_permission(request)


class TimeRangeFilter(admin.SimpleListFilter):
    """Filter by time range."""

    title = "Time Range"
    parameter_name = "time_range"

    def lookups(self, request, model_admin):
        return [
            ("1h", "Last Hour"),
            ("24h", "Last 24 Hours"),
            ("7d", "Last 7 Days"),
            ("30d", "Last 30 Days"),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "1h":
            return queryset.filter(timestamp__gte=now - timezone.timedelta(hours=1))
        elif self.value() == "24h":
            return queryset.filter(timestamp__gte=now - timezone.timedelta(days=1))
        elif self.value() == "7d":
            return queryset.filter(timestamp__gte=now - timezone.timedelta(days=7))
        elif self.value() == "30d":
            return queryset.filter(timestamp__gte=now - timezone.timedelta(days=30))
        return queryset


class StatusCodeFilter(admin.SimpleListFilter):
    """Filter by HTTP status code category."""

    title = "Status Code"
    parameter_name = "status_category"

    def lookups(self, request, model_admin):
        return [
            ("2xx", "2xx Success"),
            ("3xx", "3xx Redirect"),
            ("4xx", "4xx Client Error"),
            ("5xx", "5xx Server Error"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "2xx":
            return queryset.filter(status_code__gte=200, status_code__lt=300)
        elif self.value() == "3xx":
            return queryset.filter(status_code__gte=300, status_code__lt=400)
        elif self.value() == "4xx":
            return queryset.filter(status_code__gte=400, status_code__lt=500)
        elif self.value() == "5xx":
            return queryset.filter(status_code__gte=500)
        return queryset


class SlowRequestFilter(admin.SimpleListFilter):
    """Filter for slow requests."""

    title = "Performance"
    parameter_name = "performance"

    def lookups(self, request, model_admin):
        return [
            ("slow", "Slow (>1s)"),
            ("very_slow", "Very Slow (>3s)"),
            ("fast", "Fast (<200ms)"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "slow":
            return queryset.filter(duration_ms__gt=1000)
        elif self.value() == "very_slow":
            return queryset.filter(duration_ms__gt=3000)
        elif self.value() == "fast":
            return queryset.filter(duration_ms__lt=200)
        return queryset


@admin.register(ErrorGroup)
class ErrorGroupAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for error groups (similar to Sentry issues)."""

    list_display = [
        "display_title",
        "exception_type",
        "display_status",
        "display_level",
        "event_count",
        "user_count",
        "display_first_seen",
        "display_last_seen",
        "display_assigned",
    ]
    list_filter = ["status", "level", "exception_type", "is_regression", TimeRangeFilter]
    search_fields = ["title", "exception_type", "exception_value", "culprit"]
    readonly_fields = [
        "fingerprint",
        "first_seen",
        "last_seen",
        "event_count",
        "user_count",
        "affected_users",
    ]
    ordering = ["-last_seen"]
    list_per_page = 50

    fieldsets = [
        (
            "Error Information",
            {
                "fields": [
                    "title",
                    "exception_type",
                    "exception_value",
                    "culprit",
                    "fingerprint",
                ],
            },
        ),
        (
            "Status & Assignment",
            {
                "fields": ["status", "level", "assigned_to", "is_regression"],
            },
        ),
        (
            "Statistics",
            {
                "fields": ["event_count", "user_count", "first_seen", "last_seen", "affected_users"],
            },
        ),
        (
            "Notes & Tags",
            {
                "fields": ["notes", "tags"],
                "classes": ["collapse"],
            },
        ),
    ]

    actions = ["mark_resolved", "mark_ignored", "mark_unresolved"]

    @display(description="Title", header=True)
    def display_title(self, obj):
        return truncatechars(obj.title, 60)

    @display(description="Status", label=True)
    def display_status(self, obj):
        colors = {
            "unresolved": "danger",
            "resolved": "success",
            "ignored": "warning",
            "muted": "info",
        }
        return obj.status, colors.get(obj.status, "info")

    @display(description="Level", label=True)
    def display_level(self, obj):
        colors = {
            "debug": "info",
            "info": "info",
            "warning": "warning",
            "error": "danger",
            "critical": "danger",
        }
        return obj.level, colors.get(obj.level, "info")

    @display(description="First Seen")
    def display_first_seen(self, obj):
        return obj.first_seen.strftime("%Y-%m-%d %H:%M")

    @display(description="Last Seen")
    def display_last_seen(self, obj):
        return obj.last_seen.strftime("%Y-%m-%d %H:%M")

    @display(description="Assigned")
    def display_assigned(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.email or str(obj.assigned_to)
        return "-"

    @action(description="Mark as Resolved")
    def mark_resolved(self, request, queryset):
        updated = queryset.update(status=ErrorGroup.Status.RESOLVED)
        self.message_user(request, f"Marked {updated} error(s) as resolved.")

    @action(description="Mark as Ignored")
    def mark_ignored(self, request, queryset):
        updated = queryset.update(status=ErrorGroup.Status.IGNORED)
        self.message_user(request, f"Marked {updated} error(s) as ignored.")

    @action(description="Mark as Unresolved")
    def mark_unresolved(self, request, queryset):
        updated = queryset.update(status=ErrorGroup.Status.UNRESOLVED)
        self.message_user(request, f"Marked {updated} error(s) as unresolved.")


@admin.register(ErrorLog)
class ErrorLogAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for individual error events."""

    list_display = [
        "display_id",
        "display_exception",
        "display_level",
        "display_culprit",
        "display_user",
        "request_method",
        "display_path",
        "display_timestamp",
    ]
    list_filter = ["level", "exception_type", TimeRangeFilter, "environment"]
    search_fields = [
        "exception_type",
        "exception_value",
        "request_path",
        "user_email",
        "culprit",
        "request_id",
    ]
    readonly_fields = [
        "id",
        "group",
        "exception_type",
        "exception_value",
        "exception_module",
        "traceback_display",
        "traceback_frames",
        "culprit",
        "filename",
        "function",
        "lineno",
        "request_id",
        "request_method",
        "request_path",
        "request_url",
        "request_query",
        "request_headers",
        "request_body",
        "user_id",
        "user_email",
        "user_ip",
        "user_agent",
        "server_name",
        "environment",
        "django_version",
        "python_version",
        "extra_context",
        "tags",
        "breadcrumbs",
        "timestamp",
        "response_time_ms",
        "sql_query_count",
        "sql_query_time_ms",
    ]
    ordering = ["-timestamp"]
    list_per_page = 50

    fieldsets = [
        (
            "Error Details",
            {
                "fields": [
                    "id",
                    "group",
                    "level",
                    "exception_type",
                    "exception_value",
                    "exception_module",
                ],
            },
        ),
        (
            "Stack Trace",
            {
                "fields": ["traceback_display", "culprit", "filename", "function", "lineno"],
            },
        ),
        (
            "Request Context",
            {
                "fields": [
                    "request_id",
                    "request_method",
                    "request_path",
                    "request_url",
                    "request_query",
                    "request_headers",
                    "request_body",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "User Information",
            {
                "fields": ["user_id", "user_email", "user_ip", "user_agent"],
            },
        ),
        (
            "Environment",
            {
                "fields": [
                    "server_name",
                    "environment",
                    "django_version",
                    "python_version",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Performance",
            {
                "fields": ["response_time_ms", "sql_query_count", "sql_query_time_ms"],
            },
        ),
        (
            "Additional Context",
            {
                "fields": ["extra_context", "tags", "breadcrumbs"],
                "classes": ["collapse"],
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["timestamp"],
            },
        ),
    ]

    def traceback_display(self, obj):
        """Display formatted traceback."""
        if obj.traceback_text:
            return format_html(
                '<pre style="background: #1e1e1e; color: #d4d4d4; padding: 15px; '
                "border-radius: 8px; overflow-x: auto; font-family: monospace; "
                'font-size: 12px; line-height: 1.4; max-height: 500px; overflow-y: auto;">{}</pre>',
                obj.traceback_text,
            )
        return "-"

    traceback_display.short_description = "Stack Trace"

    @display(description="ID")
    def display_id(self, obj):
        return str(obj.id)[:8]

    @display(description="Exception", header=True)
    def display_exception(self, obj):
        value = truncatechars(obj.exception_value, 50)
        return f"{obj.exception_type}: {value}"

    @display(description="Level", label=True)
    def display_level(self, obj):
        colors = {
            "debug": "info",
            "info": "info",
            "warning": "warning",
            "error": "danger",
            "critical": "danger",
        }
        return obj.level, colors.get(obj.level, "info")

    @display(description="Culprit")
    def display_culprit(self, obj):
        return truncatechars(obj.culprit, 40)

    @display(description="User")
    def display_user(self, obj):
        return obj.user_email or obj.user_id or "Anonymous"

    @display(description="Path")
    def display_path(self, obj):
        return truncatechars(obj.request_path, 30)

    @display(description="Time")
    def display_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RequestLog)
class RequestLogAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for HTTP request logs."""

    list_display = [
        "display_request_id",
        "display_method",
        "display_path",
        "display_status",
        "display_duration",
        "display_sql",
        "display_user",
        "display_timestamp",
    ]
    list_filter = [
        StatusCodeFilter,
        SlowRequestFilter,
        "method",
        TimeRangeFilter,
        "has_error",
    ]
    search_fields = ["path", "user_email", "user_ip", "request_id", "view_name"]
    readonly_fields = [
        "id",
        "request_id",
        "method",
        "path",
        "full_url",
        "query_params",
        "request_headers",
        "request_body",
        "request_content_type",
        "status_code",
        "response_headers",
        "response_body_size",
        "user_id",
        "user_email",
        "user_ip",
        "user_agent",
        "company_id",
        "duration_ms",
        "sql_query_count",
        "sql_query_time_ms",
        "sql_queries_display",
        "view_name",
        "view_class",
        "server_name",
        "environment",
        "error_log",
        "has_error",
        "timestamp",
    ]
    ordering = ["-timestamp"]
    list_per_page = 100

    fieldsets = [
        (
            "Request Overview",
            {
                "fields": [
                    "request_id",
                    "method",
                    "path",
                    "full_url",
                    "status_code",
                    "view_name",
                ],
            },
        ),
        (
            "Performance",
            {
                "fields": [
                    "duration_ms",
                    "sql_query_count",
                    "sql_query_time_ms",
                    "response_body_size",
                ],
            },
        ),
        (
            "Request Details",
            {
                "fields": [
                    "query_params",
                    "request_headers",
                    "request_body",
                    "request_content_type",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Response Details",
            {
                "fields": ["response_headers"],
                "classes": ["collapse"],
            },
        ),
        (
            "SQL Queries",
            {
                "fields": ["sql_queries_display"],
                "classes": ["collapse"],
            },
        ),
        (
            "User & Client",
            {
                "fields": ["user_id", "user_email", "user_ip", "user_agent", "company_id"],
            },
        ),
        (
            "Server & Environment",
            {
                "fields": ["server_name", "environment"],
            },
        ),
        (
            "Error Information",
            {
                "fields": ["has_error", "error_log"],
            },
        ),
        (
            "Timestamp",
            {
                "fields": ["timestamp"],
            },
        ),
    ]

    def sql_queries_display(self, obj):
        """Display SQL queries if available."""
        if not obj.sql_queries:
            return "No SQL queries recorded"

        queries_html = []
        for i, q in enumerate(obj.sql_queries, 1):
            queries_html.append(
                f'<div style="margin-bottom: 10px; padding: 10px; background: #f5f5f5; '
                f'border-radius: 4px;">'
                f"<strong>Query {i}</strong> ({q.get('time', 0):.2f}ms)<br>"
                f'<code style="font-size: 11px; word-break: break-all;">{q.get("sql", "")}</code>'
                f"</div>"
            )
        return mark_safe("".join(queries_html))

    sql_queries_display.short_description = "SQL Queries"

    @display(description="ID")
    def display_request_id(self, obj):
        return obj.request_id[:8]

    @display(description="Method", label=True)
    def display_method(self, obj):
        colors = {
            "GET": "info",
            "POST": "success",
            "PUT": "warning",
            "PATCH": "warning",
            "DELETE": "danger",
        }
        return obj.method, colors.get(obj.method, "info")

    @display(description="Path")
    def display_path(self, obj):
        return truncatechars(obj.path, 40)

    @display(description="Status", label=True)
    def display_status(self, obj):
        if obj.status_code < 300:
            color = "success"
        elif obj.status_code < 400:
            color = "info"
        elif obj.status_code < 500:
            color = "warning"
        else:
            color = "danger"
        return str(obj.status_code), color

    @display(description="Duration")
    def display_duration(self, obj):
        duration = f"{obj.duration_ms:.0f}"
        if obj.duration_ms > 3000:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}ms</span>',
                duration,
            )
        elif obj.duration_ms > 1000:
            return format_html('<span style="color: #ffc107;">{}ms</span>', duration)
        return f"{duration}ms"

    @display(description="SQL")
    def display_sql(self, obj):
        if obj.sql_query_count > 50:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} queries</span>',
                obj.sql_query_count,
            )
        elif obj.sql_query_count > 20:
            return format_html('<span style="color: #ffc107;">{} queries</span>', obj.sql_query_count)
        return f"{obj.sql_query_count} queries"

    @display(description="User")
    def display_user(self, obj):
        return obj.user_email or "Anonymous"

    @display(description="Time")
    def display_timestamp(self, obj):
        return obj.timestamp.strftime("%H:%M:%S")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LogEntry)
class LogEntryAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for application log entries."""

    list_display = [
        "display_level",
        "logger_name",
        "display_message",
        "display_request_id",
        "display_user",
        "display_timestamp",
    ]
    list_filter = ["level", "logger_name", TimeRangeFilter]
    search_fields = ["message", "logger_name", "request_id", "user_id"]
    readonly_fields = [
        "id",
        "level",
        "logger_name",
        "message",
        "filename",
        "function",
        "lineno",
        "module",
        "request_id",
        "user_id",
        "extra",
        "timestamp",
    ]
    ordering = ["-timestamp"]
    list_per_page = 100

    @display(description="Level", label=True)
    def display_level(self, obj):
        colors = {
            "debug": "info",
            "info": "info",
            "warning": "warning",
            "error": "danger",
            "critical": "danger",
        }
        return obj.level.upper(), colors.get(obj.level, "info")

    @display(description="Message")
    def display_message(self, obj):
        return truncatechars(obj.message, 80)

    @display(description="Request ID")
    def display_request_id(self, obj):
        return obj.request_id[:8] if obj.request_id else "-"

    @display(description="User")
    def display_user(self, obj):
        return obj.user_id or "-"

    @display(description="Time")
    def display_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(PerformanceMetric)
class PerformanceMetricAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for aggregated performance metrics."""

    list_display = [
        "path_pattern",
        "method",
        "period",
        "display_period_start",
        "total_requests",
        "display_error_rate",
        "display_duration_avg",
        "display_p95",
        "display_sql_avg",
    ]
    list_filter = ["period", "method", TimeRangeFilter]
    search_fields = ["path_pattern", "view_name"]
    readonly_fields = [
        "period",
        "period_start",
        "path_pattern",
        "method",
        "view_name",
        "total_requests",
        "error_count",
        "success_count",
        "duration_avg",
        "duration_min",
        "duration_max",
        "duration_p50",
        "duration_p95",
        "duration_p99",
        "sql_count_avg",
        "sql_time_avg",
        "error_rate",
        "unique_users",
    ]
    ordering = ["-period_start"]
    list_per_page = 100

    @display(description="Period Start")
    def display_period_start(self, obj):
        return obj.period_start.strftime("%Y-%m-%d %H:%M")

    @display(description="Error Rate", label=True)
    def display_error_rate(self, obj):
        if obj.error_rate > 10:
            color = "danger"
        elif obj.error_rate > 5:
            color = "warning"
        else:
            color = "success"
        return f"{obj.error_rate:.1f}%", color

    @display(description="Avg Duration")
    def display_duration_avg(self, obj):
        return f"{obj.duration_avg:.0f}ms"

    @display(description="P95")
    def display_p95(self, obj):
        if obj.duration_p95 > 3000:
            return format_html('<span style="color: #dc3545;">{:.0f}ms</span>', obj.duration_p95)
        elif obj.duration_p95 > 1000:
            return format_html('<span style="color: #ffc107;">{:.0f}ms</span>', obj.duration_p95)
        return f"{obj.duration_p95:.0f}ms"

    @display(description="Avg SQL")
    def display_sql_avg(self, obj):
        return f"{obj.sql_count_avg:.1f} queries"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SystemMetric)
class SystemMetricAdmin(DebugModeAdminMixin, ModelAdmin):
    """Admin for system-level metrics."""

    list_display = [
        "display_timestamp",
        "server_name",
        "requests_per_minute",
        "errors_per_minute",
        "display_avg_response",
        "active_users",
        "display_memory",
        "display_cpu",
    ]
    list_filter = ["server_name", TimeRangeFilter]
    readonly_fields = [
        "timestamp",
        "server_name",
        "requests_per_minute",
        "errors_per_minute",
        "avg_response_time_ms",
        "p95_response_time_ms",
        "db_connections_active",
        "db_connections_available",
        "memory_used_mb",
        "memory_available_mb",
        "cpu_percent",
        "active_users",
    ]
    ordering = ["-timestamp"]
    list_per_page = 100

    @display(description="Timestamp")
    def display_timestamp(self, obj):
        return obj.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @display(description="Avg Response")
    def display_avg_response(self, obj):
        return f"{obj.avg_response_time_ms:.0f}ms"

    @display(description="Memory")
    def display_memory(self, obj):
        if obj.memory_used_mb and obj.memory_available_mb:
            total = obj.memory_used_mb + obj.memory_available_mb
            pct = (obj.memory_used_mb / total) * 100
            return f"{obj.memory_used_mb:.0f}MB ({pct:.0f}%)"
        return "-"

    @display(description="CPU")
    def display_cpu(self, obj):
        if obj.cpu_percent is not None:
            if obj.cpu_percent > 80:
                return format_html('<span style="color: #dc3545;">{:.0f}%</span>', obj.cpu_percent)
            return f"{obj.cpu_percent:.0f}%"
        return "-"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
