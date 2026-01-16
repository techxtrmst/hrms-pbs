"""
Management command to sync attendance records for approved leaves and holidays
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from employees.models import Employee, Attendance, LeaveRequest
from companies.models import Holiday


class Command(BaseCommand):
    help = 'Create attendance records for approved leaves and holidays'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to sync (default: current year)'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Specific month to sync (optional, default: all months)'
        )

    def handle(self, *args, **options):
        year = options['year']
        month = options.get('month')
        
        self.stdout.write(f"Syncing attendance records for year {year}...")
        
        # Determine date range
        if month:
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        else:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
        
        # Don't process future dates
        today = timezone.now().date()
        if end_date > today:
            end_date = today
        
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        
        # 1. Sync approved leaves
        self.stdout.write("\n1. Syncing approved leaves...")
        approved_leaves = LeaveRequest.objects.filter(
            status='APPROVED',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('employee')
        
        leave_count = 0
        for leave in approved_leaves:
            # Determine the actual date range to process
            leave_start = max(leave.start_date, start_date)
            leave_end = min(leave.end_date, end_date)
            
            current_date = leave_start
            while current_date <= leave_end:
                # Skip weekly offs
                if not leave.employee.is_week_off(current_date):
                    # Create or update attendance record
                    att, created = Attendance.objects.update_or_create(
                        employee=leave.employee,
                        date=current_date,
                        defaults={
                            'status': 'LEAVE',
                            'clock_in': None,
                            'clock_out': None,
                        }
                    )
                    if created:
                        leave_count += 1
                        self.stdout.write(
                            f"  Created LEAVE attendance for {leave.employee.user.get_full_name()} on {current_date}"
                        )
                current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f"✓ Created {leave_count} leave attendance records"))
        
        # 2. Sync holidays
        self.stdout.write("\n2. Syncing holidays...")
        holidays = Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_active=True
        ).select_related('company', 'location')
        
        holiday_count = 0
        for holiday in holidays:
            # Get all employees for this company and location
            employees = Employee.objects.filter(
                company=holiday.company,
                location=holiday.location,
                is_active=True
            )
            
            for emp in employees:
                # Skip if it's a weekly off for this employee
                if not emp.is_week_off(holiday.date):
                    # Only create if no attendance record exists (don't override existing records)
                    att, created = Attendance.objects.get_or_create(
                        employee=emp,
                        date=holiday.date,
                        defaults={
                            'status': 'HOLIDAY',
                            'clock_in': None,
                            'clock_out': None,
                        }
                    )
                    if created:
                        holiday_count += 1
                        if holiday_count <= 10:  # Only show first 10 to avoid spam
                            self.stdout.write(
                                f"  Created HOLIDAY attendance for {emp.user.get_full_name()} on {holiday.date} ({holiday.name})"
                            )
        
        self.stdout.write(self.style.SUCCESS(f"✓ Created {holiday_count} holiday attendance records"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✓ Sync complete! Total records created: {leave_count + holiday_count}"))
