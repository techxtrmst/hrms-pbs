import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from employees.models import LeaveBalance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Accrues 1 Sick Leave and 1 Casual Leave for all employees"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting monthly leave accrual..."))

        try:
            with transaction.atomic():
                updated_count = 0
                leave_balances = LeaveBalance.objects.all()

                for balance in leave_balances:
                    company_name = balance.employee.company.name.lower()

                    if "bluebix" in company_name:
                        # For Bluebix: Combined sick/casual leave allocation of 1 per month
                        balance.combined_sick_casual_allocated += 1.0
                        # Don't allocate to separate pools for Bluebix
                    elif "petabytz" in company_name:
                        # Casual Leave: Standard 1.0 for Petabytz
                        balance.casual_leave_allocated += 1.0
                        balance.sick_leave_allocated += 1.0
                    elif "softstandard" in company_name:
                        # Casual Leave: Standard 1.0 for everyone (unless specified otherwise)
                        balance.casual_leave_allocated += 1.0
                        balance.sick_leave_allocated += 0.5
                    else:
                        # Default fallback
                        balance.casual_leave_allocated += 1.0
                        balance.sick_leave_allocated += 1.0

                    balance.save()
                    updated_count += 1

                self.stdout.write(self.style.SUCCESS(f"Successfully accrued leaves for {updated_count} employees."))
                logger.info(f"Monthly leave accrual completed for {updated_count} employees.")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during leave accrual: {str(e)}"))
            logger.error(f"Error during leave accrual: {str(e)}")
