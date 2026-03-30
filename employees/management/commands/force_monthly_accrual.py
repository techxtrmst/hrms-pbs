"""
Management command to force monthly leave accrual for a specific month/year.
This bypasses the "1st of month" check and is used for manual accrual.

Usage:
    python manage.py force_monthly_accrual --month 3 --year 2026
"""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from employees.models import Employee, LeaveBalance

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Force monthly leave accrual for a specific month/year (bypasses date check)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            type=int,
            help="Month number (1-12). Defaults to current month.",
        )
        parser.add_argument(
            "--year",
            type=int,
            help="Year (e.g., 2026). Defaults to current year.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force accrual even if already done for this month",
        )

    def handle(self, *args, **options):
        # Get target month/year
        now = timezone.now()
        target_month = options.get("month") or now.month
        target_year = options.get("year") or now.year
        force = options.get("force", False)

        self.stdout.write(
            self.style.SUCCESS(f"Starting forced monthly leave accrual for {target_month}/{target_year}...")
        )

        updated_count = 0
        skipped_count = 0
        error_count = 0

        # Get all active employees with leave balances
        active_employees = Employee.objects.filter(is_active=True).select_related(
            "company", "location", "leave_balance"
        )

        for employee in active_employees:
            try:
                # Check if employee has completed probation period (3 months)
                if not employee.is_probation_completed():
                    self.stdout.write(f"⏭️  Skipping {employee}: Still in probation period.")
                    skipped_count += 1
                    continue

                # Get or create leave balance
                balance, created = LeaveBalance.objects.get_or_create(employee=employee)

                # Check if already accrued (unless force flag is set)
                if (
                    not force
                    and balance.last_accrual_month == target_month
                    and balance.last_accrual_year == target_year
                ):
                    self.stdout.write(
                        f"⏭️  Skipping {employee}: Already accrued for {target_month}/{target_year} (use --force to override)"
                    )
                    skipped_count += 1
                    continue

                # Perform accrual based on company
                company_name = employee.company.name.lower()

                with transaction.atomic():
                    if "petabytz" in company_name:
                        # Petabytz: 1 Sick and 1 Casual leave
                        balance.sick_leave_allocated += 1.0
                        balance.casual_leave_allocated += 1.0
                        self.stdout.write(self.style.SUCCESS(f"✅ Accrued 1 SL & 1 CL for {employee} (Petabytz)"))

                    elif "bluebix" in company_name or "softstandard" in company_name:
                        # Bluebix & Softstandard: 1 combined SL/CL
                        balance.combined_sick_casual_allocated += 1.0
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Accrued 1 Combined SL/CL for {employee} ({employee.company.name})")
                        )

                    else:
                        # Default fallback
                        balance.casual_leave_allocated += 1.0
                        balance.sick_leave_allocated += 1.0
                        self.stdout.write(self.style.SUCCESS(f"✅ Accrued 1 SL & 1 CL for {employee} (Default)"))

                    # Update tracking fields
                    balance.last_accrual_month = target_month
                    balance.last_accrual_year = target_year
                    balance.save()
                    updated_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing {employee}: {str(e)}"))
                logger.error(f"Error during forced accrual for {employee}: {str(e)}")
                error_count += 1

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Finished! Accrued leaves for {updated_count} employees for {target_month}/{target_year}"
            )
        )
        self.stdout.write(f"⏭️  Skipped: {skipped_count} employees")
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"❌ Errors: {error_count} employees"))
        self.stdout.write("=" * 70)

        logger.info(
            f"Forced monthly leave accrual completed for {target_month}/{target_year}: "
            f"{updated_count} updated, {skipped_count} skipped, {error_count} errors"
        )
