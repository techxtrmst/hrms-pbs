"""
Management command for aggregating performance metrics.

Aggregates request logs into hourly and daily performance metrics
for trend analysis and dashboards.
"""

import statistics
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Max, Min, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from observability.models import PerformanceMetric, RequestLog


class Command(BaseCommand):
    """Aggregate request logs into performance metrics."""

    help = "Aggregate request logs into performance metrics for analysis"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Number of hours to aggregate (default: 24)",
        )
        parser.add_argument(
            "--daily",
            action="store_true",
            help="Also aggregate daily metrics",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        include_daily = options["daily"]

        now = timezone.now()
        start_time = now - timedelta(hours=hours)

        self.stdout.write(f"Aggregating metrics from {start_time} to {now}...")

        # Get request logs grouped by hour and path
        hourly_data = (
            RequestLog.objects.filter(timestamp__gte=start_time)
            .annotate(hour=TruncHour("timestamp"))
            .values("hour", "path", "method")
            .annotate(
                total_requests=Count("id"),
                error_count=Count("id", filter=Q(has_error=True)),
                success_count=Count("id", filter=Q(has_error=False)),
                duration_avg=Avg("duration_ms"),
                duration_min=Min("duration_ms"),
                duration_max=Max("duration_ms"),
                sql_count_avg=Avg("sql_query_count"),
                sql_time_avg=Avg("sql_query_time_ms"),
                unique_users=Count("user_id", distinct=True),
            )
        )

        hourly_created = 0
        hourly_updated = 0

        for data in hourly_data:
            # Calculate percentiles from raw data
            durations = list(
                RequestLog.objects.filter(
                    timestamp__hour=data["hour"].hour,
                    timestamp__date=data["hour"].date(),
                    path=data["path"],
                    method=data["method"],
                ).values_list("duration_ms", flat=True)
            )

            p50 = statistics.median(durations) if durations else 0
            p95 = statistics.quantiles(durations, n=20)[18] if len(durations) >= 20 else max(durations, default=0)
            p99 = statistics.quantiles(durations, n=100)[98] if len(durations) >= 100 else max(durations, default=0)

            # Normalize path (remove IDs to group similar paths)
            normalized_path = self._normalize_path(data["path"])

            error_rate = (data["error_count"] / data["total_requests"] * 100) if data["total_requests"] > 0 else 0

            metric, created = PerformanceMetric.objects.update_or_create(
                period=PerformanceMetric.Period.HOURLY,
                period_start=data["hour"],
                path_pattern=normalized_path,
                method=data["method"] or "",
                defaults={
                    "total_requests": data["total_requests"],
                    "error_count": data["error_count"],
                    "success_count": data["success_count"],
                    "duration_avg": data["duration_avg"] or 0,
                    "duration_min": data["duration_min"] or 0,
                    "duration_max": data["duration_max"] or 0,
                    "duration_p50": p50,
                    "duration_p95": p95,
                    "duration_p99": p99,
                    "sql_count_avg": data["sql_count_avg"] or 0,
                    "sql_time_avg": data["sql_time_avg"] or 0,
                    "error_rate": error_rate,
                    "unique_users": data["unique_users"],
                },
            )

            if created:
                hourly_created += 1
            else:
                hourly_updated += 1

        self.stdout.write(f"  Hourly metrics: {hourly_created} created, {hourly_updated} updated")

        # Aggregate daily metrics if requested
        if include_daily:
            daily_start = now - timedelta(days=1)
            daily_data = (
                RequestLog.objects.filter(timestamp__gte=daily_start)
                .annotate(date=TruncDate("timestamp"))
                .values("date", "path", "method")
                .annotate(
                    total_requests=Count("id"),
                    error_count=Count("id", filter=Q(has_error=True)),
                    success_count=Count("id", filter=Q(has_error=False)),
                    duration_avg=Avg("duration_ms"),
                    duration_min=Min("duration_ms"),
                    duration_max=Max("duration_ms"),
                    sql_count_avg=Avg("sql_query_count"),
                    sql_time_avg=Avg("sql_query_time_ms"),
                    unique_users=Count("user_id", distinct=True),
                )
            )

            daily_created = 0
            daily_updated = 0

            for data in daily_data:
                normalized_path = self._normalize_path(data["path"])
                error_rate = (data["error_count"] / data["total_requests"] * 100) if data["total_requests"] > 0 else 0

                # Convert date to datetime for period_start
                period_start = timezone.make_aware(
                    timezone.datetime.combine(data["date"], timezone.datetime.min.time())
                )

                metric, created = PerformanceMetric.objects.update_or_create(
                    period=PerformanceMetric.Period.DAILY,
                    period_start=period_start,
                    path_pattern=normalized_path,
                    method=data["method"] or "",
                    defaults={
                        "total_requests": data["total_requests"],
                        "error_count": data["error_count"],
                        "success_count": data["success_count"],
                        "duration_avg": data["duration_avg"] or 0,
                        "duration_min": data["duration_min"] or 0,
                        "duration_max": data["duration_max"] or 0,
                        "sql_count_avg": data["sql_count_avg"] or 0,
                        "sql_time_avg": data["sql_time_avg"] or 0,
                        "error_rate": error_rate,
                        "unique_users": data["unique_users"],
                    },
                )

                if created:
                    daily_created += 1
                else:
                    daily_updated += 1

            self.stdout.write(f"  Daily metrics: {daily_created} created, {daily_updated} updated")

        self.stdout.write(self.style.SUCCESS("Metric aggregation complete"))

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a URL path by replacing IDs with placeholders.

        Examples:
            /employees/123/ -> /employees/<id>/
            /api/users/abc-def-123/ -> /api/users/<id>/
        """
        import re

        # Replace numeric IDs
        normalized = re.sub(r"/\d+(/|$)", r"/<id>\1", path)

        # Replace UUIDs
        normalized = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(/|$)",
            r"/<uuid>\1",
            normalized,
            flags=re.IGNORECASE,
        )

        # Replace short UUIDs (12 chars)
        normalized = re.sub(r"/[0-9a-f]{12}(/|$)", r"/<id>\1", normalized, flags=re.IGNORECASE)

        return normalized
