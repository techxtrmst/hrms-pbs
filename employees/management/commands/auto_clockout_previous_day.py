from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Attendance, AttendanceSession
from datetime import date, timedelta, datetime, time


class Command(BaseCommand):
    help = 'Automatically clock out employees who forgot to clock out from previous days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-back',
            type=int,
            default=1,
            help='Number of days back to check (default: 1 - yesterday only)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--auto-clockout-time',
            type=str,
            default='23:59',
            help='Time to set for auto clock-out (HH:MM format, default: 23:59)'
        )

    def handle(self, *args, **options):
        days_back = options.get('days_back', 1)
        dry_run = options.get('dry_run', False)
        auto_clockout_time_str = options.get('auto_clockout_time', '23:59')
        
        try:
            auto_clockout_hour, auto_clockout_minute = map(int, auto_clockout_time_str.split(':'))
            auto_clockout_time = time(auto_clockout_hour, auto_clockout_minute)
        except ValueError:
            self.stdout.write(self.style.ERROR('Invalid time format. Use HH:MM (e.g., 23:59)'))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN - Showing what would be auto-clocked out'))
        else:
            self.stdout.write('🕐 Auto-clocking out employees from previous days')
        
        today = date.today()
        total_fixed = 0
        
        for day_offset in range(1, days_back + 1):
            check_date = today - timedelta(days=day_offset)
            self.stdout.write(f'\n📅 Checking {check_date} ({day_offset} day{"s" if day_offset > 1 else ""} ago)')
            
            # Find incomplete sessions (clocked in but not clocked out)
            incomplete_sessions = AttendanceSession.objects.filter(
                date=check_date,
                clock_in__isnull=False,
                clock_out__isnull=True
            ).select_related('employee', 'employee__user')
            
            if not incomplete_sessions.exists():
                self.stdout.write('   ✅ No incomplete sessions found')
                continue
            
            day_fixed = 0
            
            for session in incomplete_sessions:
                employee = session.employee
                
                # Create auto clock-out time for that date
                auto_clockout_datetime = timezone.make_aware(
                    datetime.combine(check_date, auto_clockout_time)
                )
                
                # Calculate session duration
                duration = auto_clockout_datetime - session.clock_in
                duration_hours = duration.total_seconds() / 3600
                
                self.stdout.write(
                    f'   👤 {employee.user.get_full_name()}: '
                    f'Session {session.session_number} '
                    f'({session.clock_in.time()} → {auto_clockout_time}) '
                    f'= {duration_hours:.1f}h'
                )
                
                if not dry_run:
                    # Set auto clock-out
                    session.clock_out = auto_clockout_datetime
                    session.calculate_duration()
                    session.save()
                    
                    # Update attendance record
                    attendance = Attendance.objects.filter(
                        employee=employee,
                        date=check_date
                    ).first()
                    
                    if attendance:
                        # Update attendance status and working hours
                        attendance.is_currently_clocked_in = False
                        attendance.clock_out = auto_clockout_datetime
                        attendance.calculate_total_working_hours()
                        attendance.save()
                
                day_fixed += 1
                total_fixed += 1
            
            if dry_run:
                self.stdout.write(f'   🔍 Would auto-clock out {day_fixed} sessions')
            else:
                self.stdout.write(f'   ✅ Auto-clocked out {day_fixed} sessions')
        
        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY RUN COMPLETE - Would fix {total_fixed} incomplete sessions'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    'To apply changes, run: python manage.py auto_clockout_previous_day'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ AUTO CLOCK-OUT COMPLETED - Fixed {total_fixed} incomplete sessions'
                )
            )
        
        # Show usage examples
        self.stdout.write(f'\n📚 USAGE EXAMPLES:')
        self.stdout.write(f'   # Auto clock-out yesterday only (default)')
        self.stdout.write(f'   python manage.py auto_clockout_previous_day')
        self.stdout.write(f'   ')
        self.stdout.write(f'   # Check last 3 days')
        self.stdout.write(f'   python manage.py auto_clockout_previous_day --days-back 3')
        self.stdout.write(f'   ')
        self.stdout.write(f'   # Set custom auto clock-out time')
        self.stdout.write(f'   python manage.py auto_clockout_previous_day --auto-clockout-time 18:00')
        self.stdout.write(f'   ')
        self.stdout.write(f'   # Test before applying')
        self.stdout.write(f'   python manage.py auto_clockout_previous_day --dry-run')
        
        if total_fixed > 0:
            self.stdout.write(f'\n💡 RECOMMENDATIONS:')
            self.stdout.write(f'   • Set up daily cron job to run this command automatically')
            self.stdout.write(f'   • Run at start of each day (e.g., 6:00 AM)')
            self.stdout.write(f'   • Consider sending notifications to employees about auto clock-outs')
            self.stdout.write(f'   • Review regularization requests for these auto clock-outs')