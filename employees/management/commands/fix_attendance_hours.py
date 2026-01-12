from django.core.management.base import BaseCommand
from employees.models import Attendance, AttendanceSession
from datetime import date, timedelta


class Command(BaseCommand):
    help = "Fix attendance working hours calculation to use session-based logic"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days back to recalculate (default: 30)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalculate all attendance records (ignores --days)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )

    def handle(self, *args, **options):
        days_back = options.get("days", 30)
        recalculate_all = options.get("all", False)
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN - Showing what would be fixed")
            )
        else:
            self.stdout.write("🔧 Fixing attendance working hours calculation")

        # Determine date range
        if recalculate_all:
            attendances = Attendance.objects.all().order_by("-date")
            self.stdout.write("📅 Processing all attendance records")
        else:
            start_date = date.today() - timedelta(days=days_back)
            attendances = Attendance.objects.filter(date__gte=start_date).order_by(
                "-date"
            )
            self.stdout.write(
                f"📅 Processing attendance records from {start_date} to today"
            )

        total_records = attendances.count()
        if total_records == 0:
            self.stdout.write(self.style.WARNING("No attendance records found"))
            return

        self.stdout.write(f"📊 Found {total_records} attendance records to process")

        fixed_count = 0
        problematic_count = 0

        for attendance in attendances:
            # Get current values
            old_effective_hours = attendance.effective_hours

            # Calculate new values using session-based logic
            sessions = AttendanceSession.objects.filter(
                employee=attendance.employee,
                date=attendance.date,
                clock_in__isnull=False,
                clock_out__isnull=False,  # Only completed sessions
            )

            total_minutes = 0
            session_count = sessions.count()

            for session in sessions:
                duration = session.clock_out - session.clock_in
                session_minutes = duration.total_seconds() / 60
                total_minutes += session_minutes

            new_total_hours = round(total_minutes / 60, 2)

            # Calculate new effective hours display
            hours = int(new_total_hours)
            minutes = int((new_total_hours - hours) * 60)

            # Check for active sessions
            has_active_session = AttendanceSession.objects.filter(
                employee=attendance.employee,
                date=attendance.date,
                clock_in__isnull=False,
                clock_out__isnull=True,
            ).exists()

            new_effective_hours = (
                f"{hours}:{minutes:02d}{'+' if has_active_session else ''}"
                if new_total_hours > 0
                else "0:00"
            )

            # Check if this record needs fixing
            needs_fixing = False

            # Check for unrealistic hours (>16 hours per day)
            if new_total_hours > 16:
                problematic_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"⚠️  {attendance.employee.user.get_full_name()} ({attendance.date}): "
                        f"Unrealistic hours: {new_total_hours:.1f}h from {session_count} sessions"
                    )
                )

            # Check if values changed significantly
            try:
                # Parse old effective hours
                if ":" in str(old_effective_hours):
                    old_h, old_m = str(old_effective_hours).replace("+", "").split(":")
                    old_decimal = float(old_h) + float(old_m) / 60
                else:
                    old_decimal = float(str(old_effective_hours).replace("+", ""))

                if (
                    abs(old_decimal - new_total_hours) > 0.1
                ):  # More than 6 minutes difference
                    needs_fixing = True
            except (ValueError, AttributeError):
                needs_fixing = True

            # Check if there are any incomplete sessions that need attention
            incomplete_sessions = AttendanceSession.objects.filter(
                employee=attendance.employee,
                date=attendance.date,
                clock_in__isnull=False,
                clock_out__isnull=True,
            )

            if incomplete_sessions.exists():
                needs_fixing = True

            if needs_fixing:
                fixed_count += 1

                incomplete_info = (
                    f" ({incomplete_sessions.count()} incomplete)"
                    if incomplete_sessions.exists()
                    else ""
                )

                self.stdout.write(
                    f"   {attendance.employee.user.get_full_name()} ({attendance.date}): "
                    f"{old_effective_hours} → {new_effective_hours} "
                    f"({session_count} sessions{incomplete_info})"
                )

                # Apply changes if not dry run (recalculate using model method)
                if not dry_run:
                    # The model's effective_hours property already uses session-based calculation
                    # So we just need to trigger any necessary updates
                    attendance.save()

        # Summary
        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN COMPLETE"))
            self.stdout.write(f"   Records that would be fixed: {fixed_count}")
            self.stdout.write(f"   Problematic records found: {problematic_count}")
            self.stdout.write(
                self.style.SUCCESS(
                    "To apply changes, run: python manage.py fix_attendance_hours"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ ATTENDANCE HOURS FIXED"))
            self.stdout.write(f"   Records processed: {total_records}")
            self.stdout.write(f"   Records fixed: {fixed_count}")
            self.stdout.write(f"   Problematic records: {problematic_count}")

        # Show examples of fixed records
        if fixed_count > 0:
            self.stdout.write("\n📋 SUMMARY OF CHANGES:")
            self.stdout.write(
                "   • Only completed sessions counted (clock-in + clock-out)"
            )
            self.stdout.write("   • Incomplete sessions ignored (until regularization)")
            self.stdout.write("   • Realistic daily hours (typically 6-10 hours)")
            self.stdout.write("   • Multiple sessions properly summed")

        if problematic_count > 0:
            self.stdout.write("\n⚠️  PROBLEMATIC RECORDS:")
            self.stdout.write(f"   • {problematic_count} records with >16 hours/day")
            self.stdout.write("   • These may need manual review")
            self.stdout.write("   • Check for missing clock-outs or data issues")
