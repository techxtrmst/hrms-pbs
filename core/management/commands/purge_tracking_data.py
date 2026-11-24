"""
Management command to purge desktop tracking data, screenshots, and system request logs.
Reclaims disk space using TRUNCATE CASCADE while strictly preserving all Core HR and Location data.
"""

import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Purge desktop tracking records, screenshots, and system logs to reclaim disk space."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show tables and paths that would be purged without actually truncating.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(
            self.style.WARNING(
                "\n" + ("=" * 70) + "\n"
                f"{'[DRY RUN] ' if dry_run else ''}Purging Desktop Tracking & System Logs (Location & HR data are PROTECTED)\n"
                + ("=" * 70)
            )
        )

        # Tables to truncate (ONLY tracking & request logs)
        # Note: LocationLog, SessionLocationLog, Attendance, and all HR models are EXCLUDED!
        tables_to_truncate = [
            "activity_monitoring_activitypulse",
            "activity_monitoring_appactivity",
            "activity_monitoring_browseractivity",
            "activity_monitoring_systemevent",
            "activity_monitoring_activityscreenshot",
            "activity_monitoring_activitysession",
            "observability_requestlog",
            "observability_logentry",
            "observability_systemmetric",
            "observability_performancemetric",
            "django_celery_results_taskresult",
        ]

        if dry_run:
            for table in tables_to_truncate:
                self.stdout.write(f"  [DRY RUN] Would truncate table: {table}")
        else:
            with connection.cursor() as cursor:
                for table in tables_to_truncate:
                    try:
                        self.stdout.write(f"  Truncating table: {table}...")
                        cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Freed space for {table}"))
                    except Exception as e:
                        # Some tables might not exist if app is not enabled
                        self.stdout.write(self.style.NOTICE(f"  - Skipped {table}: {e}"))

        # Clear screenshot media files from disk
        media_root = getattr(settings, "MEDIA_ROOT", "/app/media")
        screenshot_dir = os.path.join(str(media_root), "activity_screenshots")

        if os.path.exists(screenshot_dir):
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would delete screenshot files in: {screenshot_dir}")
            else:
                try:
                    self.stdout.write(f"  Clearing screenshot files in: {screenshot_dir}...")
                    shutil.rmtree(screenshot_dir)
                    os.makedirs(screenshot_dir, exist_ok=True)
                    self.stdout.write(self.style.SUCCESS("  ✓ Screenshot files deleted from disk."))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  Could not remove screenshot files: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                "\n✅ Done! Desktop tracking and screenshots purged. Disk space released."
                "\n(All Employee profiles, Attendance, and Location logs remain 100% intact.)\n"
            )
        )
