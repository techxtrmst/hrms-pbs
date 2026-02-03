"""
Management command for cleaning up old observability data.

Implements data retention policies to prevent database bloat.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from observability.models import (
    ErrorGroup,
    ErrorLog,
    LogEntry,
    PerformanceMetric,
    RequestLog,
    SystemMetric,
)


class Command(BaseCommand):
    """Clean up old observability data based on retention policies."""

    help = "Clean up old observability data based on retention policies"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--request-days",
            type=int,
            default=None,
            help="Override retention days for request logs",
        )
        parser.add_argument(
            "--error-days",
            type=int,
            default=None,
            help="Override retention days for error logs",
        )
        parser.add_argument(
            "--log-days",
            type=int,
            default=None,
            help="Override retention days for log entries",
        )
        parser.add_argument(
            "--metric-days",
            type=int,
            default=None,
            help="Override retention days for metrics",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Get retention settings from OBSERVABILITY config or use defaults
        obs_config = getattr(settings, "OBSERVABILITY", {})
        retention = obs_config.get("RETENTION", {})

        # Retention periods in days
        request_log_days = options["request_days"] or retention.get("REQUEST_LOGS", 7)
        error_log_days = options["error_days"] or retention.get("ERROR_LOGS", 30)
        log_entry_days = options["log_days"] or retention.get("LOG_ENTRIES", 7)
        metric_days = options["metric_days"] or retention.get("METRICS", 90)
        system_metric_days = retention.get("SYSTEM_METRICS", 30)

        now = timezone.now()
        total_deleted = 0

        self.stdout.write(self.style.NOTICE("Starting observability data cleanup..."))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No data will be deleted"))

        # Clean up request logs
        request_cutoff = now - timedelta(days=request_log_days)
        request_count = RequestLog.objects.filter(timestamp__lt=request_cutoff).count()
        if request_count > 0:
            if not dry_run:
                RequestLog.objects.filter(timestamp__lt=request_cutoff).delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {request_count} request logs "
                f"older than {request_log_days} days"
            )
            total_deleted += request_count

        # Clean up error logs (but keep those linked to unresolved groups)
        error_cutoff = now - timedelta(days=error_log_days)
        error_queryset = ErrorLog.objects.filter(timestamp__lt=error_cutoff).exclude(
            group__status=ErrorGroup.Status.UNRESOLVED
        )
        error_count = error_queryset.count()
        if error_count > 0:
            if not dry_run:
                error_queryset.delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {error_count} error logs "
                f"older than {error_log_days} days"
            )
            total_deleted += error_count

        # Clean up resolved/ignored error groups older than retention
        group_cutoff = now - timedelta(days=error_log_days * 2)  # Keep groups longer
        group_queryset = ErrorGroup.objects.filter(
            last_seen__lt=group_cutoff,
            status__in=[ErrorGroup.Status.RESOLVED, ErrorGroup.Status.IGNORED],
        )
        group_count = group_queryset.count()
        if group_count > 0:
            if not dry_run:
                group_queryset.delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {group_count} resolved/ignored "
                f"error groups older than {error_log_days * 2} days"
            )
            total_deleted += group_count

        # Clean up log entries
        log_cutoff = now - timedelta(days=log_entry_days)
        log_count = LogEntry.objects.filter(timestamp__lt=log_cutoff).count()
        if log_count > 0:
            if not dry_run:
                LogEntry.objects.filter(timestamp__lt=log_cutoff).delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {log_count} log entries older than {log_entry_days} days"
            )
            total_deleted += log_count

        # Clean up hourly performance metrics (convert to daily after 7 days)
        hourly_cutoff = now - timedelta(days=7)
        hourly_count = PerformanceMetric.objects.filter(
            period=PerformanceMetric.Period.HOURLY, period_start__lt=hourly_cutoff
        ).count()
        if hourly_count > 0:
            if not dry_run:
                PerformanceMetric.objects.filter(
                    period=PerformanceMetric.Period.HOURLY, period_start__lt=hourly_cutoff
                ).delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {hourly_count} hourly metrics older than 7 days"
            )
            total_deleted += hourly_count

        # Clean up daily performance metrics
        metric_cutoff = now - timedelta(days=metric_days)
        daily_count = PerformanceMetric.objects.filter(
            period=PerformanceMetric.Period.DAILY, period_start__lt=metric_cutoff
        ).count()
        if daily_count > 0:
            if not dry_run:
                PerformanceMetric.objects.filter(
                    period=PerformanceMetric.Period.DAILY, period_start__lt=metric_cutoff
                ).delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {daily_count} daily metrics "
                f"older than {metric_days} days"
            )
            total_deleted += daily_count

        # Clean up system metrics
        system_cutoff = now - timedelta(days=system_metric_days)
        system_count = SystemMetric.objects.filter(timestamp__lt=system_cutoff).count()
        if system_count > 0:
            if not dry_run:
                SystemMetric.objects.filter(timestamp__lt=system_cutoff).delete()
            self.stdout.write(
                f"  {'Would delete' if dry_run else 'Deleted'} {system_count} system metrics "
                f"older than {system_metric_days} days"
            )
            total_deleted += system_count

        if total_deleted > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n{'Would delete' if dry_run else 'Deleted'} {total_deleted} total records")
            )
        else:
            self.stdout.write(self.style.SUCCESS("\nNo records to clean up"))
