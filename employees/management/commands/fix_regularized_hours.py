"""
Management command to fix working hours for regularized attendance records
"""

from django.core.management.base import BaseCommand

from employees.models import Attendance, AttendanceSession, RegularizationRequest


class Command(BaseCommand):
    help = "Fix working hours for regularized attendance records"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date-from",
            type=str,
            help="Start date (YYYY-MM-DD format)",
        )
        parser.add_argument(
            "--date-to",
            type=str,
            help="End date (YYYY-MM-DD format)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )

    def handle(self, *args, **options):
        # Get approved regularization requests
        approved_regs = RegularizationRequest.objects.filter(status="APPROVED")

        if options["date_from"]:
            approved_regs = approved_regs.filter(date__gte=options["date_from"])
        if options["date_to"]:
            approved_regs = approved_regs.filter(date__lte=options["date_to"])

        self.stdout.write(f"Found {approved_regs.count()} approved regularization requests")

        fixed_count = 0
        session_created_count = 0

        for reg in approved_regs:
            try:
                # Get the attendance record
                attendance = Attendance.objects.filter(employee=reg.employee, date=reg.date).first()

                if not attendance:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No attendance record found for {reg.employee.user.get_full_name()} on {reg.date}"
                        )
                    )
                    continue

                # Check if there are any sessions for this attendance
                sessions = AttendanceSession.objects.filter(employee=reg.employee, date=reg.date)

                # If no sessions exist but we have clock_in/clock_out, create a session
                if not sessions.exists() and attendance.clock_in and attendance.clock_out:
                    if not options["dry_run"]:
                        AttendanceSession.objects.create(
                            employee=reg.employee,
                            date=reg.date,
                            session_number=1,
                            clock_in=attendance.clock_in,
                            clock_out=attendance.clock_out,
                            session_type="WEB",
                            is_active=False,
                            location_validated=True,
                        )
                    session_created_count += 1
                    self.stdout.write(
                        f"{'[DRY RUN] Would create' if options['dry_run'] else 'Created'} session for {reg.employee.user.get_full_name()} on {reg.date}"
                    )

                # Recalculate working hours
                old_hours = attendance.total_working_hours
                if not options["dry_run"]:
                    attendance.calculate_total_working_hours()
                    attendance.save(update_fields=["total_working_hours"])

                new_hours = attendance.total_working_hours if not options["dry_run"] else "N/A (dry run)"

                if old_hours != attendance.total_working_hours or options["dry_run"]:
                    fixed_count += 1
                    self.stdout.write(
                        f"{'[DRY RUN] Would fix' if options['dry_run'] else 'Fixed'} hours for {reg.employee.user.get_full_name()} on {reg.date}: {old_hours} -> {new_hours}"
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing regularization for {reg.employee.user.get_full_name()} on {reg.date}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] Would fix' if options['dry_run'] else 'Fixed'} {fixed_count} attendance records"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] Would create' if options['dry_run'] else 'Created'} {session_created_count} attendance sessions"
            )
        )

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("This was a dry run. Use without --dry-run to apply changes."))
