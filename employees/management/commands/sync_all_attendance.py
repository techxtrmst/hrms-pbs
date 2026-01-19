"""
Management command to sync all attendance records (leaves, holidays, and absents)
This should be run after deployment to ensure all attendance data is properly reflected
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.management import call_command
from datetime import date


class Command(BaseCommand):
    help = "Sync all attendance records: leaves, holidays, and absents for proper reporting"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.now().year,
            help="Year to sync (default: current year)",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="Specific month to sync (optional, default: all months)",
        )
        parser.add_argument(
            "--start-year", type=int, help="Start year for multi-year sync (optional)"
        )
        parser.add_argument(
            "--end-year", type=int, help="End year for multi-year sync (optional)"
        )

    def handle(self, *args, **options):
        year = options["year"]
        month = options.get("month")
        start_year = options.get("start_year")
        end_year = options.get("end_year")

        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(
            self.style.SUCCESS(
                "  ATTENDANCE SYNC - Complete Attendance Record Synchronization"
            )
        )
        self.stdout.write(self.style.SUCCESS("=" * 70))

        # Determine which years to process
        if start_year and end_year:
            years_to_process = range(start_year, end_year + 1)
        else:
            years_to_process = [year]

        for process_year in years_to_process:
            self.stdout.write(f"\n{'=' * 70}")
            self.stdout.write(self.style.WARNING(f"Processing Year: {process_year}"))
            self.stdout.write(f"{'=' * 70}\n")

            # Step 1: Sync approved leaves
            self.stdout.write(
                self.style.HTTP_INFO("\n📋 STEP 1: Syncing Approved Leaves")
            )
            self.stdout.write("-" * 70)
            try:
                if month:
                    call_command(
                        "sync_leave_holiday_attendance", year=process_year, month=month
                    )
                else:
                    call_command("sync_leave_holiday_attendance", year=process_year)
                self.stdout.write(self.style.SUCCESS("✓ Leave sync completed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error syncing leaves: {e}"))

            # Step 2: Mark absents
            self.stdout.write(self.style.HTTP_INFO("\n📋 STEP 2: Marking Absent Days"))
            self.stdout.write("-" * 70)
            try:
                if month:
                    call_command("mark_absents", year=process_year, month=month)
                else:
                    call_command("mark_absents", year=process_year)
                self.stdout.write(self.style.SUCCESS("✓ Absent marking completed"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error marking absents: {e}"))

        # Final summary
        self.stdout.write(f"\n{'=' * 70}")
        self.stdout.write(
            self.style.SUCCESS("✓ ATTENDANCE SYNC COMPLETED SUCCESSFULLY")
        )
        self.stdout.write(self.style.SUCCESS("=" * 70))

        self.stdout.write("\n📊 Summary:")
        self.stdout.write("  • Approved leaves have been synced to attendance records")
        self.stdout.write("  • Holidays have been synced to attendance records")
        self.stdout.write("  • Absent days have been marked for all employees")
        self.stdout.write(
            "\n✅ All attendance data is now properly reflected in reports"
        )
        self.stdout.write("\n" + "=" * 70 + "\n")
