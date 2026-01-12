from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, Attendance
from datetime import timedelta


class Command(BaseCommand):
    help = "Mark week-off days in attendance for all employees"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of days to process (default: 30 days from today)",
        )
        parser.add_argument(
            "--employee-id", type=int, help="Process only specific employee ID"
        )

    def handle(self, *args, **options):
        days = options["days"]
        employee_id = options.get("employee_id")

        # Get employees
        if employee_id:
            employees = Employee.objects.filter(id=employee_id, is_active=True)
        else:
            employees = Employee.objects.filter(is_active=True)

        if not employees.exists():
            self.stdout.write(self.style.WARNING("No employees found"))
            return

        # Date range
        today = timezone.localdate()
        start_date = today - timedelta(days=days)
        end_date = today

        total_marked = 0

        for employee in employees:
            current_date = start_date
            employee_marked = 0

            while current_date <= end_date:
                # Check if this date is a week-off for this employee
                if employee.is_week_off(current_date):
                    # Get user timezone from employee's location
                    tz_name = (
                        employee.location.timezone
                        if employee.location
                        else "Asia/Kolkata"
                    )

                    # Get or create attendance record
                    attendance, created = Attendance.objects.get_or_create(
                        employee=employee,
                        date=current_date,
                        defaults={"status": "WEEKLY_OFF", "user_timezone": tz_name},
                    )

                    # Update timezone if record already existed
                    if not created and not attendance.user_timezone:
                        attendance.user_timezone = tz_name

                    # Update status if not already marked as week-off
                    if attendance.status != "WEEKLY_OFF":
                        # Only update if it's ABSENT (don't override PRESENT, LEAVE, etc.)
                        if attendance.status == "ABSENT":
                            attendance.status = "WEEKLY_OFF"
                            attendance.save()
                            employee_marked += 1
                    elif created:
                        employee_marked += 1

                current_date += timedelta(days=1)

            if employee_marked > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Marked {employee_marked} week-off days for {employee.user.get_full_name()}"
                    )
                )
                total_marked += employee_marked

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal: Marked {total_marked} week-off days for {employees.count()} employees"
            )
        )
