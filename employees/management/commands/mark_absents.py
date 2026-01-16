"""
Management command to mark employees as absent for working days where they didn't clock in
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
from employees.models import Employee, Attendance
from companies.models import Holiday


class Command(BaseCommand):
    help = 'Mark employees as absent for working days where they did not clock in and have no leave/holiday'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='Year to process (default: current year)'
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Specific month to process (optional, default: all months)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        year = options['year']
        month = options.get('month')
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        self.stdout.write(f"Processing absents for year {year}...")
        
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
        
        # Don't process future dates or today (employees might still clock in)
        today = timezone.now().date()
        if end_date >= today:
            end_date = today - timedelta(days=1)  # Process up to yesterday
        
        if start_date > end_date:
            self.stdout.write(self.style.WARNING("No dates to process (start date is in the future)"))
            return
        
        self.stdout.write(f"Date range: {start_date} to {end_date}")
        
        # Get all active employees
        employees = Employee.objects.filter(is_active=True).select_related('company', 'location')
        
        # Get all holidays in the date range
        holidays = Holiday.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            is_active=True
        ).select_related('location')
        
        # Create holiday map by location and date
        holiday_map = {}
        for holiday in holidays:
            if holiday.location_id not in holiday_map:
                holiday_map[holiday.location_id] = set()
            holiday_map[holiday.location_id].add(holiday.date)
        
        absent_count = 0
        skipped_count = 0
        
        for emp in employees:
            # Get all existing attendance records for this employee in the date range
            existing_attendance = set(
                Attendance.objects.filter(
                    employee=emp,
                    date__gte=start_date,
                    date__lte=end_date
                ).values_list('date', flat=True)
            )
            
            # Process each date in the range
            current_date = start_date
            while current_date <= end_date:
                # Skip if attendance record already exists
                if current_date in existing_attendance:
                    current_date += timedelta(days=1)
                    continue
                
                # Skip if it's a weekly off
                if emp.is_week_off(current_date):
                    current_date += timedelta(days=1)
                    continue
                
                # Skip if it's a holiday for this employee's location
                if (emp.location_id and 
                    emp.location_id in holiday_map and 
                    current_date in holiday_map[emp.location_id]):
                    current_date += timedelta(days=1)
                    continue
                
                # Skip if employee joined after this date
                if emp.date_of_joining and current_date < emp.date_of_joining:
                    current_date += timedelta(days=1)
                    continue
                
                # This is a working day with no attendance record - mark as absent
                if not dry_run:
                    Attendance.objects.create(
                        employee=emp,
                        date=current_date,
                        status='ABSENT',
                        clock_in=None,
                        clock_out=None,
                    )
                
                absent_count += 1
                if absent_count <= 20:  # Show first 20 to avoid spam
                    self.stdout.write(
                        f"  {'[DRY RUN] Would mark' if dry_run else 'Marked'} {emp.user.get_full_name()} as ABSENT on {current_date}"
                    )
                elif absent_count == 21:
                    self.stdout.write("  ... (showing first 20 only)")
                
                current_date += timedelta(days=1)
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\n[DRY RUN] Would create {absent_count} absent records"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✓ Created {absent_count} absent records"))
        
        self.stdout.write(self.style.SUCCESS(f"✓ Processing complete!"))
