import logging

import pytz
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from employees.models import Employee, LeaveBalance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Automatically accrues leaves for employees on the 1st of every month based on their location timezone"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting automated monthly leave accrual check..."))

        current_time_utc = timezone.now()
        updated_count = 0
        skipped_count = 0

        # Get all active employees with leave balances
        active_employees = Employee.objects.filter(is_active=True).select_related(
            "company", "location", "leave_balance"
        )

        for employee in active_employees:
            try:
                # Check if employee has completed probation period (3 months)
                if not employee.is_probation_completed():
                    # self.stdout.write(f"Skipping {employee}: Still in probation period.")
                    skipped_count += 1
                    continue

                # Get the leave balance OR create one if it doesn't exist
                balance, created = LeaveBalance.objects.get_or_create(employee=employee)

                # Determine local time for the employee
                tz_name = (
                    employee.location.timezone if (employee.location and employee.location.timezone) else "Asia/Kolkata"
                )
                try:
                    local_tz = pytz.timezone(tz_name)
                    local_time = current_time_utc.astimezone(local_tz)
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(f"Invalid timezone {tz_name} for {employee}. Falling back to Asia/Kolkata.")
                    )
                    local_tz = pytz.timezone("Asia/Kolkata")
                    local_time = current_time_utc.astimezone(local_tz)

                # Check if it's the 1st of the month in their local time
                if local_time.day != 1:
                    # self.stdout.write(f"Skipping {employee}: Today is {local_time.date()}, not the 1st.")
                    skipped_count += 1
                    continue

                # Check if we have already accrued for this month/year
                if balance.last_accrual_month == local_time.month and balance.last_accrual_year == local_time.year:
                    # self.stdout.write(f"Skipping {employee}: Already accrued for {local_time.month}/{local_time.year}")
                    skipped_count += 1
                    continue

                # Perform accrual based on company
                company_name = employee.company.name.lower()

                with transaction.atomic():
                    if "petabytz" in company_name:
                        # Petabytz: 1 Sick and 1 Casual leave
                        balance.sick_leave_allocated += 1.0
                        balance.casual_leave_allocated += 1.0
                        self.stdout.write(self.style.SUCCESS(f"Accrued 1 SL & 1 CL for {employee} (Petabytz)"))

                    elif "bluebix" in company_name or "softstandard" in company_name:
                        # Bluebix & Softstandard: 1 combined SL/CL
                        balance.combined_sick_casual_allocated += 1.0
                        self.stdout.write(
                            self.style.SUCCESS(f"Accrued 1 Combined SL/CL for {employee} ({employee.company.name})")
                        )

                    else:
                        # Default fallback (optional, as per current code)
                        balance.casual_leave_allocated += 1.0
                        balance.sick_leave_allocated += 1.0
                        self.stdout.write(self.style.SUCCESS(f"Accrued 1 SL & 1 CL for {employee} (Default)"))

                    # Update tracking fields
                    balance.last_accrual_month = local_time.month
                    balance.last_accrual_year = local_time.year
                    balance.save()
                    updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing {employee}: {str(e)}"))
                logger.error(f"Error during monthly accrual for {employee}: {str(e)}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished! Accrued leaves for {updated_count} employees. Skipped {skipped_count} (not 1st or already done)."
            )
        )
        logger.info(f"Monthly leave accrual check completed: {updated_count} updated, {skipped_count} skipped.")
