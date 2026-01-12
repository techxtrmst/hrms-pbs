from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, Attendance
from companies.models import Holiday
from datetime import timedelta


class Command(BaseCommand):
    help = "Mark holiday days in attendance for all employees based on their location"

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
        parser.add_argument(
            "--company-id", type=int, help="Process only specific company ID"
        )

    def handle(self, *args, **options):
        days = options["days"]
        employee_id = options.get("employee_id")
        company_id = options.get("company_id")

        # Get employees
        employees = Employee.objects.filter(is_active=True).select_related(
            "location", "company"
        )

        if employee_id:
            employees = employees.filter(id=employee_id)
        if company_id:
            employees = employees.filter(company_id=company_id)

        if not employees.exists():
            self.stdout.write(self.style.WARNING("No employees found"))
            return

        # Date range
        today = timezone.localdate()
        start_date = today - timedelta(days=days)
        end_date = today

        # Get all holidays in the date range
        holidays = Holiday.objects.filter(
            date__gte=start_date, date__lte=end_date, is_active=True
        ).select_related("company", "location")

        # Group holidays by company and location
        holiday_map = {}
        for holiday in holidays:
            company_id = holiday.company_id
            location_id = holiday.location_id

            if company_id not in holiday_map:
                holiday_map[company_id] = {}
            if location_id not in holiday_map[company_id]:
                holiday_map[company_id][location_id] = []

            holiday_map[company_id][location_id].append(holiday.date)

        total_marked = 0

        for employee in employees:
            if not employee.location:
                continue

            company_id = employee.company_id
            location_id = employee.location_id

            # Get holidays for this employee's company and location
            employee_holidays = holiday_map.get(company_id, {}).get(location_id, [])

            if not employee_holidays:
                continue

            employee_marked = 0

            for holiday_date in employee_holidays:
                if start_date <= holiday_date <= end_date:
                    # Get or create attendance record
                    attendance, created = Attendance.objects.get_or_create(
                        employee=employee,
                        date=holiday_date,
                        defaults={"status": "HOLIDAY"},
                    )

                    # Update status if not already marked as holiday
                    if attendance.status != "HOLIDAY":
                        # Only update if it's ABSENT (don't override PRESENT, LEAVE, etc.)
                        if attendance.status == "ABSENT":
                            attendance.status = "HOLIDAY"
                            attendance.save()
                            employee_marked += 1
                    elif created:
                        employee_marked += 1

            if employee_marked > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Marked {employee_marked} holiday days for {employee.user.get_full_name()} "
                        f"({employee.location.name})"
                    )
                )
                total_marked += employee_marked

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTotal: Marked {total_marked} holiday days for {employees.count()} employees"
            )
        )
