from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process scheduled employee exits: Blocks access for employees whose last working day has passed"

    def handle(self, *args, **options):
        self.stdout.write("Checking for scheduled exits...")

        today = timezone.localdate()

        # Find active employees whose exit date is today or in the past
        # We look for employees where is_active is True but exit_date is set and <= today
        exiting_employees = Employee.objects.filter(
            is_active=True, exit_date__lte=today, exit_date__isnull=False
        )

        count = 0
        for employee in exiting_employees:
            try:
                self.stdout.write(
                    f"Processing exit for {employee.user.get_full_name()} (Exit Date: {employee.exit_date})"
                )

                # 1. Deactivate Employee Profile
                employee.is_active = False
                employee.save()

                # 2. Deactivate User Login
                if employee.user:
                    user = employee.user
                    user.is_active = False
                    user.save()
                    self.stdout.write(f"  - User login blocked for {user.username}")

                count += 1

            except Exception as e:
                logger.error(f"Error processing exit for {employee}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Error processing {employee}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {count} scheduled exits.")
        )
