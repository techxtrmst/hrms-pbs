"""
Views for the observability app.

Provides:
- Dashboard with overview statistics
- Error tracking views
- Request log views
- Performance analysis views
- API endpoints for charts
"""

from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Max, Q
from django.db.models.functions import TruncDate, TruncHour
from django.http import JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .models import (
    ErrorGroup,
    ErrorLog,
    RequestLog,
)


class AdminContextMixin:
    """Mixin to add Django admin site context for Unfold styling."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add admin site context for Unfold sidebar and navigation
        context.update(admin.site.each_context(self.request))
        return context


@method_decorator(staff_member_required, name="dispatch")
class DashboardView(AdminContextMixin, TemplateView):
    """Main observability dashboard."""

    template_name = "observability/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)

        # Error statistics
        context["unresolved_errors"] = ErrorGroup.objects.filter(status=ErrorGroup.Status.UNRESOLVED).count()
        context["errors_24h"] = ErrorLog.objects.filter(timestamp__gte=last_24h).count()
        context["errors_1h"] = ErrorLog.objects.filter(timestamp__gte=last_hour).count()

        # Request statistics
        requests_24h = RequestLog.objects.filter(timestamp__gte=last_24h)
        context["requests_24h"] = requests_24h.count()
        context["error_requests_24h"] = requests_24h.filter(has_error=True).count()

        # Performance statistics
        perf_stats = requests_24h.aggregate(
            avg_duration=Avg("duration_ms"),
            max_duration=Max("duration_ms"),
            avg_sql_count=Avg("sql_query_count"),
        )
        context["avg_response_time"] = perf_stats["avg_duration"] or 0
        context["max_response_time"] = perf_stats["max_duration"] or 0
        context["avg_sql_queries"] = perf_stats["avg_sql_count"] or 0

        # Recent errors
        context["recent_errors"] = ErrorLog.objects.select_related("group")[:10]

        # Top error groups
        context["top_error_groups"] = ErrorGroup.objects.filter(status=ErrorGroup.Status.UNRESOLVED).order_by(
            "-event_count"
        )[:5]

        # Slow requests
        context["slow_requests"] = RequestLog.objects.filter(timestamp__gte=last_24h, duration_ms__gt=1000).order_by(
            "-duration_ms"
        )[:10]

        # Error rate calculation
        if context["requests_24h"] > 0:
            context["error_rate"] = (context["error_requests_24h"] / context["requests_24h"]) * 100
        else:
            context["error_rate"] = 0

        return context


@method_decorator(staff_member_required, name="dispatch")
class ErrorListView(ListView):
    """List of error events."""

    model = ErrorLog
    template_name = "observability/error_list.html"
    context_object_name = "errors"
    paginate_by = 50
    ordering = ["-timestamp"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related("group")

        # Filter by time range
        time_range = self.request.GET.get("range", "24h")
        now = timezone.now()

        if time_range == "1h":
            queryset = queryset.filter(timestamp__gte=now - timedelta(hours=1))
        elif time_range == "24h":
            queryset = queryset.filter(timestamp__gte=now - timedelta(days=1))
        elif time_range == "7d":
            queryset = queryset.filter(timestamp__gte=now - timedelta(days=7))
        elif time_range == "30d":
            queryset = queryset.filter(timestamp__gte=now - timedelta(days=30))

        # Filter by level
        level = self.request.GET.get("level")
        if level:
            queryset = queryset.filter(level=level)

        # Filter by exception type
        exception_type = self.request.GET.get("type")
        if exception_type:
            queryset = queryset.filter(exception_type__icontains=exception_type)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(exception_value__icontains=search)
                | Q(request_path__icontains=search)
                | Q(user_email__icontains=search)
            )

        return queryset


@method_decorator(staff_member_required, name="dispatch")
class ErrorDetailView(DetailView):
    """Detail view for a single error event."""

    model = ErrorLog
    template_name = "observability/error_detail.html"
    context_object_name = "error"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get related errors from the same group
        if self.object.group:
            context["related_errors"] = (
                ErrorLog.objects.filter(group=self.object.group).exclude(pk=self.object.pk).order_by("-timestamp")[:10]
            )

        # Get request log if available
        context["request_log"] = getattr(self.object, "request_log", None)

        return context


@method_decorator(staff_member_required, name="dispatch")
class ErrorGroupListView(ListView):
    """List of error groups (issues)."""

    model = ErrorGroup
    template_name = "observability/error_group_list.html"
    context_object_name = "groups"
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by status
        status = self.request.GET.get("status", "unresolved")
        if status and status != "all":
            queryset = queryset.filter(status=status)

        # Sort
        sort = self.request.GET.get("sort", "-last_seen")
        if sort in ["-last_seen", "-event_count", "-first_seen", "-user_count"]:
            queryset = queryset.order_by(sort)

        return queryset


@method_decorator(staff_member_required, name="dispatch")
class ErrorGroupDetailView(DetailView):
    """Detail view for an error group."""

    model = ErrorGroup
    template_name = "observability/error_group_detail.html"
    context_object_name = "group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get events for this group
        context["events"] = self.object.events.order_by("-timestamp")[:50]

        # Event frequency over time (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        context["daily_counts"] = (
            self.object.events.filter(timestamp__gte=seven_days_ago)
            .annotate(date=TruncDate("timestamp"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        return context


@method_decorator(staff_member_required, name="dispatch")
class RequestLogListView(ListView):
    """List of HTTP request logs."""

    model = RequestLog
    template_name = "observability/request_list.html"
    context_object_name = "requests"
    paginate_by = 100
    ordering = ["-timestamp"]

    def get_queryset(self):
        queryset = super().get_queryset()

        # Time range filter
        time_range = self.request.GET.get("range", "1h")
        now = timezone.now()

        if time_range == "1h":
            queryset = queryset.filter(timestamp__gte=now - timedelta(hours=1))
        elif time_range == "24h":
            queryset = queryset.filter(timestamp__gte=now - timedelta(days=1))
        elif time_range == "7d":
            queryset = queryset.filter(timestamp__gte=now - timedelta(days=7))

        # Status code filter
        status = self.request.GET.get("status")
        if status:
            if status == "2xx":
                queryset = queryset.filter(status_code__gte=200, status_code__lt=300)
            elif status == "4xx":
                queryset = queryset.filter(status_code__gte=400, status_code__lt=500)
            elif status == "5xx":
                queryset = queryset.filter(status_code__gte=500)
            elif status == "error":
                queryset = queryset.filter(has_error=True)

        # Method filter
        method = self.request.GET.get("method")
        if method:
            queryset = queryset.filter(method=method)

        # Search
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(path__icontains=search) | Q(user_email__icontains=search) | Q(request_id__icontains=search)
            )

        return queryset


@method_decorator(staff_member_required, name="dispatch")
class RequestLogDetailView(DetailView):
    """Detail view for a single request log."""

    model = RequestLog
    template_name = "observability/request_detail.html"
    context_object_name = "request_log"


@method_decorator(staff_member_required, name="dispatch")
class PerformanceView(TemplateView):
    """Performance analysis view."""

    template_name = "observability/performance.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        # Endpoint performance summary
        context["endpoint_stats"] = (
            RequestLog.objects.filter(timestamp__gte=last_24h)
            .values("path", "method")
            .annotate(
                count=Count("id"),
                avg_duration=Avg("duration_ms"),
                max_duration=Max("duration_ms"),
                avg_sql=Avg("sql_query_count"),
                error_count=Count("id", filter=Q(has_error=True)),
            )
            .order_by("-count")[:20]
        )

        # Slowest endpoints
        context["slowest_endpoints"] = (
            RequestLog.objects.filter(timestamp__gte=last_24h)
            .values("path", "method")
            .annotate(avg_duration=Avg("duration_ms"), count=Count("id"))
            .filter(count__gte=5)
            .order_by("-avg_duration")[:10]
        )

        # Most SQL-heavy endpoints
        context["sql_heavy_endpoints"] = (
            RequestLog.objects.filter(timestamp__gte=last_24h)
            .values("path", "method")
            .annotate(avg_sql=Avg("sql_query_count"), count=Count("id"))
            .filter(count__gte=5)
            .order_by("-avg_sql")[:10]
        )

        return context


@method_decorator(staff_member_required, name="dispatch")
class SlowRequestsView(ListView):
    """View for slow requests."""

    model = RequestLog
    template_name = "observability/slow_requests.html"
    context_object_name = "slow_requests"
    paginate_by = 50

    def get_queryset(self):
        threshold = int(self.request.GET.get("min_duration", 1000))
        method = self.request.GET.get("method", "")
        now = timezone.now()

        queryset = RequestLog.objects.filter(duration_ms__gt=threshold, timestamp__gte=now - timedelta(days=7))

        if method:
            queryset = queryset.filter(method=method)

        return queryset.order_by("-duration_ms")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["min_duration"] = self.request.GET.get("min_duration", 1000)
        context["selected_method"] = self.request.GET.get("method", "")
        return context


# API Views for Charts


@method_decorator(staff_member_required, name="dispatch")
class StatsAPIView(View):
    """API endpoint for quick stats."""

    def get(self, request):
        now = timezone.now()
        last_hour = now - timedelta(hours=1)
        last_24h = now - timedelta(days=1)

        stats = {
            "errors_1h": ErrorLog.objects.filter(timestamp__gte=last_hour).count(),
            "errors_24h": ErrorLog.objects.filter(timestamp__gte=last_24h).count(),
            "requests_1h": RequestLog.objects.filter(timestamp__gte=last_hour).count(),
            "requests_24h": RequestLog.objects.filter(timestamp__gte=last_24h).count(),
            "unresolved_groups": ErrorGroup.objects.filter(status=ErrorGroup.Status.UNRESOLVED).count(),
        }

        return JsonResponse(stats)


@method_decorator(staff_member_required, name="dispatch")
class ErrorChartAPIView(View):
    """API endpoint for error chart data."""

    def get(self, request):
        hours = int(request.GET.get("hours", 24))
        now = timezone.now()
        start = now - timedelta(hours=hours)

        # Group errors by hour
        data = (
            ErrorLog.objects.filter(timestamp__gte=start)
            .annotate(hour=TruncHour("timestamp"))
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )

        return JsonResponse(
            {
                "labels": [d["hour"].strftime("%H:%M") for d in data],
                "values": [d["count"] for d in data],
            }
        )


@method_decorator(staff_member_required, name="dispatch")
class RequestChartAPIView(View):
    """API endpoint for request chart data."""

    def get(self, request):
        hours = int(request.GET.get("hours", 24))
        now = timezone.now()
        start = now - timedelta(hours=hours)

        # Group requests by hour
        data = (
            RequestLog.objects.filter(timestamp__gte=start)
            .annotate(hour=TruncHour("timestamp"))
            .values("hour")
            .annotate(
                total=Count("id"),
                errors=Count("id", filter=Q(has_error=True)),
            )
            .order_by("hour")
        )

        return JsonResponse(
            {
                "labels": [d["hour"].strftime("%H:%M") for d in data],
                "total": [d["total"] for d in data],
                "errors": [d["errors"] for d in data],
            }
        )


@method_decorator(staff_member_required, name="dispatch")
class PerformanceChartAPIView(View):
    """API endpoint for performance chart data."""

    def get(self, request):
        hours = int(request.GET.get("hours", 24))
        now = timezone.now()
        start = now - timedelta(hours=hours)

        # Group by hour and calculate avg response time
        data = (
            RequestLog.objects.filter(timestamp__gte=start)
            .annotate(hour=TruncHour("timestamp"))
            .values("hour")
            .annotate(avg_duration=Avg("duration_ms"))
            .order_by("hour")
        )

        return JsonResponse(
            {
                "labels": [d["hour"].strftime("%H:%M") for d in data],
                "values": [round(d["avg_duration"], 2) for d in data],
            }
        )
