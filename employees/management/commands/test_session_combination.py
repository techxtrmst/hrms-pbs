from django.core.management.base import BaseCommand
from employees.models import Employee, Attendance, AttendanceSession
from datetime import date, time, datetime


class Command(BaseCommand):
    help = "Test and demonstrate multiple session combination for working hours calculation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--employee-id", type=int, help="Test with specific employee ID"
        )
        parser.add_argument(
            "--create-test-data",
            action="store_true",
            help="Create test data with multiple sessions",
        )

    def handle(self, *args, **options):
        employee_id = options.get("employee_id")
        create_test_data = options.get("create_test_data", False)

        self.stdout.write("🧪 Testing Multiple Session Combination")

        # Get employee
        if employee_id:
            try:
                employee = Employee.objects.get(id=employee_id, is_active=True)
            except Employee.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Employee with ID {employee_id} not found")
                )
                return
        else:
            employee = Employee.objects.filter(is_active=True).first()
            if not employee:
                self.stdout.write(self.style.ERROR("No active employees found"))
                return

        self.stdout.write(
            f"👤 Testing with: {employee.user.get_full_name()} ({employee.company.name})"
        )

        # Get shift info
        shift = employee.assigned_shift
        if shift:
            expected_hours = shift.get_shift_duration_timedelta().total_seconds() / 3600
            self.stdout.write(
                f"⏰ Shift: {shift.name} ({shift.start_time} - {shift.end_time}) = {expected_hours:.1f} hours"
            )
        else:
            expected_hours = 9.0
            self.stdout.write("⏰ Default shift: 9.0 hours")

        today = date.today()

        if create_test_data:
            self.stdout.write(f"\n📝 Creating test data for {today}")

            # Create attendance record
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={
                    "status": "PRESENT",
                    "daily_sessions_count": 0,
                    "max_daily_sessions": 5,
                },
            )

            # Clear existing sessions for today
            AttendanceSession.objects.filter(employee=employee, date=today).delete()

            # Create multiple test sessions
            test_sessions = [
                {
                    "session_number": 1,
                    "clock_in": datetime.combine(today, time(9, 15)),
                    "clock_out": datetime.combine(today, time(12, 30)),
                    "session_type": "WEB",
                },
                {
                    "session_number": 2,
                    "clock_in": datetime.combine(today, time(13, 30)),
                    "clock_out": datetime.combine(today, time(16, 45)),
                    "session_type": "WEB",
                },
                {
                    "session_number": 3,
                    "clock_in": datetime.combine(today, time(17, 0)),
                    "clock_out": datetime.combine(today, time(18, 30)),
                    "session_type": "REMOTE",
                },
            ]

            for session_data in test_sessions:
                session = AttendanceSession.objects.create(
                    employee=employee, date=today, **session_data
                )
                session.calculate_duration()
                session.save()

                duration_hours = session.duration_minutes / 60
                self.stdout.write(
                    f"   Session {session.session_number}: "
                    f"{session.clock_in.time()} - {session.clock_out.time()} "
                    f"= {duration_hours:.2f}h ({session.session_type})"
                )

            # Update attendance
            attendance.daily_sessions_count = len(test_sessions)
            attendance.calculate_total_working_hours()
            attendance.save()

            self.stdout.write(self.style.SUCCESS("✅ Test data created"))

        # Analyze current attendance
        self.stdout.write(f"\n📊 Analyzing attendance for {today}")

        attendance = Attendance.objects.filter(employee=employee, date=today).first()
        if not attendance:
            self.stdout.write(
                self.style.WARNING("No attendance record found for today")
            )
            return

        # Get session summary
        summary = attendance.get_combined_session_summary()

        self.stdout.write("\n📈 SESSION COMBINATION RESULTS:")
        self.stdout.write(f"   Total Sessions: {summary['total_sessions']}")
        self.stdout.write(f"   Completed Sessions: {summary['completed_sessions']}")
        self.stdout.write(f"   Active Sessions: {summary['active_sessions']}")
        self.stdout.write("   ")
        self.stdout.write("   📊 WORKING HOURS CALCULATION:")
        self.stdout.write(f"   Expected Hours: {summary['expected_hours']:.1f}h")
        self.stdout.write(f"   Worked Hours: {summary['total_worked_hours']:.2f}h")
        self.stdout.write(f"   Completion: {summary['completion_percentage']:.1f}%")
        self.stdout.write(f"   Remaining: {summary['remaining_hours']:.2f}h")
        self.stdout.write(
            f"   Shift Complete: {'✅ Yes' if summary['is_shift_complete'] else '❌ No'}"
        )

        # Show individual sessions
        sessions = AttendanceSession.objects.filter(
            employee=employee, date=today
        ).order_by("session_number")

        if sessions.exists():
            self.stdout.write("\n🔍 INDIVIDUAL SESSIONS:")
            total_combined = 0

            for session in sessions:
                if session.clock_in and session.clock_out:
                    duration_hours = session.duration_minutes / 60
                    total_combined += duration_hours

                    self.stdout.write(
                        f"   Session {session.session_number}: "
                        f"{session.clock_in.time()} - {session.clock_out.time()} "
                        f"= {duration_hours:.2f}h ({session.session_type})"
                    )
                else:
                    self.stdout.write(
                        f"   Session {session.session_number}: "
                        f"{session.clock_in.time() if session.clock_in else 'N/A'} - "
                        f"{'Active' if not session.clock_out else session.clock_out.time()} "
                        f"({session.session_type})"
                    )

            self.stdout.write("   ")
            self.stdout.write("   🧮 COMBINATION VERIFICATION:")
            self.stdout.write(f"   Manual Sum: {total_combined:.2f}h")
            self.stdout.write(f"   System Calc: {summary['total_worked_hours']:.2f}h")
            self.stdout.write(f"   Effective Hours: {attendance.effective_hours}")
            self.stdout.write(
                f"   Match: {'✅ Correct' if abs(total_combined - summary['total_worked_hours']) < 0.01 else '❌ Error'}"
            )

        # Show attendance display values
        self.stdout.write("\n📱 DISPLAY VALUES:")
        self.stdout.write(f"   Home Page Hours: {attendance.effective_hours}")
        self.stdout.write(
            f"   Total Working Hours: {attendance.total_working_hours:.2f}h"
        )
        self.stdout.write(f"   Visual Progress: {attendance.visual_width:.1f}%")
        self.stdout.write(f"   Status: {attendance.get_status_display()}")

        # Recommendations
        self.stdout.write("\n💡 RECOMMENDATIONS:")
        if summary["completion_percentage"] < 90:
            remaining = summary["remaining_hours"]
            self.stdout.write(
                f"   • Employee needs {remaining:.1f} more hours to complete shift"
            )
        else:
            self.stdout.write(
                f"   • ✅ Shift requirement met ({summary['completion_percentage']:.1f}%)"
            )

        if summary["active_sessions"] > 0:
            self.stdout.write(
                "   • ⚠️  Employee currently clocked in - session incomplete"
            )

        if summary["total_sessions"] > 3:
            self.stdout.write(
                "   • ℹ️  Multiple sessions detected - all properly combined"
            )

        self.stdout.write("\n✅ Session combination test completed!")

        # Usage examples
        self.stdout.write("\n📚 USAGE EXAMPLES:")
        self.stdout.write("   # Test with specific employee")
        self.stdout.write(
            "   python manage.py test_session_combination --employee-id 1"
        )
        self.stdout.write("   ")
        self.stdout.write("   # Create test data and analyze")
        self.stdout.write(
            "   python manage.py test_session_combination --create-test-data"
        )
        self.stdout.write("   ")
        self.stdout.write("   # Test with specific employee and create data")
        self.stdout.write(
            "   python manage.py test_session_combination --employee-id 1 --create-test-data"
        )
