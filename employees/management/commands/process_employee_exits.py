"""
Management command to process employee exits on their last working day.
This should be run daily via a cron job or scheduled task.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, ExitInitiative


class Command(BaseCommand):
    help = 'Process employee exits on their last working day'

    def handle(self, *args, **options):
        today = timezone.localdate()
        
        # Find all approved exit initiatives where last working day is today or in the past
        # and employee is still active
        exit_initiatives = ExitInitiative.objects.filter(
            status='APPROVED',
            last_working_day__lte=today,
            employee__is_active=True
        )
        
        processed_count = 0
        
        for exit_initiative in exit_initiatives:
            employee = exit_initiative.employee
            
            # Change employee to Ex-Employee type
            employee.employment_status = 'EX_EMPLOYEE'
            employee.is_active = False
            employee.save()
            
            # Disable user login
            user = employee.user
            user.is_active = False
            user.save()
            
            processed_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed exit for {employee.user.get_full_name()} '
                    f'(Last working day: {exit_initiative.last_working_day})'
                )
            )
        
        if processed_count == 0:
            self.stdout.write(self.style.WARNING('No employee exits to process today.'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {processed_count} employee exit(s).'
                )
            )
