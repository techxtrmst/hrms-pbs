"""
Management command to clean up old high-volume activity and location data.

Usage:
    python manage.py cleanup_old_data              # default: delete records older than 90 days
    python manage.py cleanup_old_data --days 60    # delete records older than 60 days
    python manage.py cleanup_old_data --dry-run    # preview counts without deleting
"""

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete old activity monitoring and location tracking records to free up disk space."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Delete records older than this many days (default: 90)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview how many records would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(days=days)

        self.stdout.write(
            self.style.WARNING(
                f"\n{'[DRY RUN] ' if dry_run else ''}Cleaning up records older than {days} days "
                f"(before {cutoff.date()})\n"
            )
        )

        from activity_monitoring.models import (
            ActivityPulse,
            ActivityScreenshot,
            ActivitySession,
            AppActivity,
            BrowserActivity,
            SystemEvent,
        )
        from employees.models import LocationLog

        models_to_clean = [
            ("ActivityPulse", ActivityPulse, "timestamp"),
            ("AppActivity", AppActivity, "start_time"),
            ("BrowserActivity", BrowserActivity, "timestamp"),
            ("SystemEvent", SystemEvent, "timestamp"),
            ("LocationLog", LocationLog, "timestamp"),
        ]

        total_deleted = 0

        for label, model, time_field in models_to_clean:
            qs = model.objects.filter(**{f"{time_field}__lt": cutoff})
            count = qs.count()
            if not dry_run and count > 0:
                qs.delete()
            status = "[would delete]" if dry_run else "[deleted]"
            color = self.style.WARNING if dry_run else self.style.SUCCESS
            self.stdout.write(color(f"  {status} {label}: {count:,} records"))
            total_deleted += count

        # Screenshots — delete files too
        old_screenshots = ActivityScreenshot.objects.filter(timestamp__lt=cutoff)
        screenshot_count = old_screenshots.count()
        if not dry_run and screenshot_count > 0:
            for screenshot in old_screenshots.iterator(chunk_size=500):
                try:
                    if screenshot.image:
                        screenshot.image.delete(save=False)
                except Exception as e:
                    logger.warning(f"Could not delete screenshot file: {e}")
            old_screenshots.delete()
        status = "[would delete]" if dry_run else "[deleted]"
        color = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(color(f"  {status} ActivityScreenshot: {screenshot_count:,} records + files"))
        total_deleted += screenshot_count

        # ActivitySession — only orphaned ones (no child records left)
        orphan_sessions = ActivitySession.objects.filter(
            start_time__lt=cutoff,
            apps__isnull=True,
            browser_logs__isnull=True,
            screenshots__isnull=True,
        )
        session_count = orphan_sessions.count()
        if not dry_run and session_count > 0:
            orphan_sessions.delete()
        self.stdout.write(color(f"  {status} ActivitySession (orphaned): {session_count:,} records"))
        total_deleted += session_count

        self.stdout.write(
            self.style.SUCCESS(f"\n{'Would delete' if dry_run else 'Deleted'} {total_deleted:,} total records.\n")
        )
