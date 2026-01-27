"""
Background Location Tracking Management Command
Runs as a scheduled task to ensure location tracking continues even if browser-based tracking fails
"""

import time
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from loguru import logger

from employees.models import Attendance, Employee, LocationLog


class Command(BaseCommand):
    help = 'Background location tracking service for employees who are clocked in'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=3600,  # 1 hour in seconds
            help='Interval between location checks in seconds (default: 3600 = 1 hour)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as a daemon (continuous loop)'
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=7200,  # 2 hours in seconds
            help='Maximum age of last location log before considering employee for tracking (default: 7200 = 2 hours)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        daemon_mode = options['daemon']
        max_age_seconds = options['max_age']

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting background location tracking service...\n'
                f'Interval: {interval} seconds ({interval/60:.1f} minutes)\n'
                f'Max age: {max_age_seconds} seconds ({max_age_seconds/60:.1f} minutes)\n'
                f'Daemon mode: {daemon_mode}'
            )
        )

        if daemon_mode:
            self.run_daemon(interval, max_age_seconds)
        else:
            self.run_once(max_age_seconds)

    def run_daemon(self, interval, max_age_seconds):
        """Run continuously as a daemon"""
        logger.info(f"Background location tracker daemon started with {interval}s interval")
        
        while True:
            try:
                self.process_location_tracking(max_age_seconds)
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Background location tracker daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in background location tracker daemon: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

    def run_once(self, max_age_seconds):
        """Run once and exit"""
        logger.info("Running background location tracker once")
        self.process_location_tracking(max_age_seconds)

    def process_location_tracking(self, max_age_seconds):
        """Process location tracking for all eligible employees"""
        now = timezone.now()
        today = timezone.localdate()
        
        # Find all employees who are currently clocked in
        clocked_in_attendances = Attendance.objects.filter(
            date=today,
            is_currently_clocked_in=True
        ).select_related('employee', 'employee__user')

        tracked_count = 0
        skipped_count = 0
        error_count = 0

        for attendance in clocked_in_attendances:
            try:
                employee = attendance.employee
                
                # Check if employee needs location tracking
                if self.should_track_employee(employee, attendance, now, max_age_seconds):
                    success = self.request_employee_location(employee, attendance)
                    if success:
                        tracked_count += 1
                    else:
                        error_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing employee {attendance.employee.id}: {e}")
                error_count += 1

        logger.info(
            f"Background location tracking completed: "
            f"{tracked_count} tracked, {skipped_count} skipped, {error_count} errors"
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Location tracking cycle completed:\n'
                f'  Tracked: {tracked_count}\n'
                f'  Skipped: {skipped_count}\n'
                f'  Errors: {error_count}'
            )
        )

    def should_track_employee(self, employee, attendance, now, max_age_seconds):
        """Determine if an employee should be tracked"""
        
        # Check if shift is complete
        if attendance.should_stop_location_tracking():
            return False
            
        # Check last location log time
        last_log = LocationLog.objects.filter(
            employee=employee,
            log_type='HOURLY'
        ).order_by('-timestamp').first()
        
        if last_log:
            time_since_last = now - last_log.timestamp
            if time_since_last.total_seconds() < max_age_seconds:
                return False  # Recent location log exists
        
        # Check if it's been at least 1 hour since clock-in or last session start
        reference_time = attendance.clock_in
        current_session = attendance.get_current_session()
        
        if current_session and current_session.clock_in:
            if not reference_time or current_session.clock_in > reference_time:
                reference_time = current_session.clock_in
                
        if last_log and last_log.timestamp > reference_time:
            reference_time = last_log.timestamp
            
        if reference_time:
            time_since_reference = now - reference_time
            if time_since_reference.total_seconds() < 3600:  # Less than 1 hour
                return False
                
        return True

    def request_employee_location(self, employee, attendance):
        """Request location from employee (placeholder for future implementation)"""
        
        # For now, we'll create a placeholder log indicating that location was requested
        # In a real implementation, this would:
        # 1. Send a push notification to the employee's device
        # 2. Trigger a location request via WebSocket or similar
        # 3. Wait for the response and store the actual location
        
        try:
            # Create a system-generated location request log
            LocationLog.objects.create(
                employee=employee,
                attendance_session=attendance.get_current_session(),
                latitude=0.0,  # Placeholder - would be actual location
                longitude=0.0,  # Placeholder - would be actual location
                accuracy=0.0,
                log_type='SYSTEM_REQUEST',
                is_valid=False,  # Mark as invalid since it's just a request
                notes=f'Background location request sent at {timezone.now()}'
            )
            
            logger.info(f"Location request sent for employee {employee.user.get_full_name()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request location for employee {employee.id}: {e}")
            return False

    def cleanup_old_logs(self, days=30):
        """Clean up old location logs"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        deleted_count = LocationLog.objects.filter(
            timestamp__lt=cutoff_date,
            log_type='SYSTEM_REQUEST',
            is_valid=False
        ).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old system request logs")