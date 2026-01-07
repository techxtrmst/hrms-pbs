from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Attendance
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Detect and mark attendance records with missing clock-out (missing punch)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write(self.style.WARNING("Starting missing punch detection..."))

        # Get all attendance records with clock_in but no clock_out
        incomplete_attendance = Attendance.objects.filter(
            clock_in__isnull=False, clock_out__isnull=True
        ).exclude(
            status="MISSING_PUNCH"  # Don't process already marked records
        )

        updated_count = 0
        now = timezone.now()

        for attendance in incomplete_attendance:
            # Check if shift end time has passed
            if (
                attendance.location_tracking_end_time
                and now >= attendance.location_tracking_end_time
            ):
                # Shift duration has passed, mark as missing punch

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRY RUN] Would mark as MISSING_PUNCH: "
                            f"{attendance.employee.user.get_full_name()} on {attendance.date}"
                        )
                    )
                else:
                    # Update the record
                    attendance.status = "MISSING_PUNCH"
                    attendance.location_tracking_active = False
                    attendance.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Marked as MISSING_PUNCH: "
                            f"{attendance.employee.user.get_full_name()} on {attendance.date}"
                        )
                    )

                    logger.info(
                        f"Missing punch detected: {attendance.employee.user.username} "
                        f"on {attendance.date} (ID: {attendance.id})"
                    )

                updated_count += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\\n[DRY RUN] Would update {updated_count} attendance record(s)"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\\nSuccessfully updated {updated_count} attendance record(s) to MISSING_PUNCH status"
                )
            )

        if updated_count == 0:
            self.stdout.write(self.style.SUCCESS("No missing punches detected."))
