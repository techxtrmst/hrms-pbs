"""
Management command to test calendar attendance statuses
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from employees.models import Employee, Attendance, LeaveRequest
from companies.models import Holiday
from collections import Counter


class Command(BaseCommand):
    help = "Test calendar attendance statuses to ensure all types are showing correctly"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=timezone.now().year,
            help="Year to test (default: current year)",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=timezone.now().month,
            help="Month to test (default: current month)",
        )

    def handle(self, *args, **options):
        year = options["year"]
        month = options["month"]

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("  CALENDAR ATTENDANCE STATUS TEST"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        # Calculate month range
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        num_days = month_end.day
        today = timezone.now().date()

        self.stdout.write(f"\nTesting: {month_start.strftime('%B %Y')}")
        self.stdout.write(f"Date range: {month_start} to {month_end}")
        self.stdout.write(f"Days in month: {num_days}")

        # Get first few employees for testing
        employees = Employee.objects.filter(is_active=True)[:5]

        if not employees.exists():
            self.stdout.write(self.style.ERROR("No active employees found!"))
            return

        self.stdout.write(f"Testing with {employees.count()} employees")

        # Track status distribution
        status_counts = Counter()

        for emp in employees:
            self.stdout.write(f"\n📋 Employee: {emp.user.get_full_name()}")
            self.stdout.write("-" * 60)

            # Get attendance for the month
            month_attendance = Attendance.objects.filter(
                employee=emp, date__range=[month_start, month_end]
            )
            att_map = {att.date.day: att for att in month_attendance}

            # Get sick leaves
            sick_leaves = LeaveRequest.objects.filter(
                employee=emp,
                status="APPROVED",
                leave_type="SL",
                start_date__lte=month_end,
                end_date__gte=month_start,
            )

            sick_leave_dates = set()
            for sl in sick_leaves:
                s = max(sl.start_date, month_start)
                e = min(sl.end_date, month_end)
                curr = s
                while curr <= e:
                    sick_leave_dates.add(curr.day)
                    curr += timedelta(days=1)

            # Test each day
            employee_statuses = []
            for day in range(1, min(num_days + 1, 15)):  # Test first 15 days
                day_date = date(year, month, day)
                att = att_map.get(day)

                status_class = ""
                status_desc = ""

                if att:
                    if att.status == "WFH":
                        status_class = "wfh"
                        status_desc = "Work from home"
                    elif att.status == "WEEKLY_OFF":
                        status_class = "weekly-off"
                        status_desc = "Weekly off"
                    elif att.status == "LEAVE":
                        if day in sick_leave_dates:
                            status_class = "sick-leave"
                            status_desc = "Sick leave"
                        else:
                            status_class = "paid-leave"
                            status_desc = "Paid leave"
                    elif att.status == "ABSENT":
                        status_class = "no-attendance"
                        status_desc = "No attendance"
                    elif att.status == "HOLIDAY":
                        status_class = "holiday"
                        status_desc = "Holiday"
                    elif att.status in ["PRESENT", "ON_DUTY", "HALF_DAY"]:
                        status_class = "present"
                        status_desc = "Present"
                    else:
                        status_class = "present"
                        status_desc = f"Present ({att.status})"
                else:
                    # No attendance record
                    if day_date > today:
                        status_class = "future"
                        status_desc = "Future date"
                    else:
                        # Check for holiday
                        is_holiday = Holiday.objects.filter(
                            company=emp.company,
                            location=emp.location,
                            date=day_date,
                            is_active=True,
                        ).exists()

                        if is_holiday:
                            status_class = "holiday"
                            status_desc = "Holiday (no record)"
                        elif emp.is_week_off(day_date):
                            status_class = "weekly-off"
                            status_desc = "Weekly off (no record)"
                        else:
                            status_class = "no-attendance"
                            status_desc = "Absent (no record)"

                employee_statuses.append(status_class)
                status_counts[status_class] += 1

                # Show first few days for each employee
                if day <= 7:
                    self.stdout.write(
                        f"  Day {day:2d}: {status_class:15s} - {status_desc}"
                    )

            # Show employee summary
            emp_counter = Counter(employee_statuses)
            self.stdout.write(f"  Summary: {dict(emp_counter)}")

        # Overall summary
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("OVERALL STATUS DISTRIBUTION")
        self.stdout.write("=" * 80)

        total_days = sum(status_counts.values())
        for status, count in sorted(status_counts.items()):
            percentage = (count / total_days * 100) if total_days > 0 else 0
            self.stdout.write(f"  {status:15s}: {count:3d} days ({percentage:5.1f}%)")

        self.stdout.write(f"\nTotal days processed: {total_days}")

        # Check if all expected statuses are present
        expected_statuses = [
            "present",
            "no-attendance",
            "wfh",
            "weekly-off",
            "paid-leave",
            "sick-leave",
            "holiday",
            "future",
        ]

        missing_statuses = [s for s in expected_statuses if s not in status_counts]
        if missing_statuses:
            self.stdout.write(
                f"\n⚠️  Missing statuses (no data found): {missing_statuses}"
            )
        else:
            self.stdout.write(f"\n✅ All status types found in data!")

        # Recommendations
        self.stdout.write(f"\n" + "=" * 80)
        self.stdout.write("RECOMMENDATIONS")
        self.stdout.write("=" * 80)

        if status_counts.get("no-attendance", 0) > 0:
            self.stdout.write(
                "📝 Run sync_all_attendance command to create missing attendance records"
            )

        if status_counts.get("future", 0) == 0:
            self.stdout.write("📝 Testing past month - future dates not applicable")

        if status_counts.get("holiday", 0) == 0:
            self.stdout.write(
                "📝 No holidays found - check if holidays are configured in database"
            )

        if status_counts.get("sick-leave", 0) == 0:
            self.stdout.write(
                "📝 No sick leaves found - check if SL leave requests are approved"
            )

        self.stdout.write(f"\n✅ Calendar status test completed!")
        self.stdout.write("=" * 80)
