from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from employees.models import Employee


class Command(BaseCommand):
    help = "Migrate existing Bluebix and Softstandard employees to combined sick/casual leave system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        self.stdout.write(self.style.SUCCESS("Starting combined leave migration..."))

        try:
            # Get all Bluebix and Softstandard employees
            bluebix_employees = Employee.objects.filter(
                Q(company__name__icontains="bluebix") | Q(company__name__icontains="softstandard")
            )

            if not bluebix_employees.exists():
                self.stdout.write(self.style.WARNING("No Bluebix employees found"))
                return

            migrated_count = 0

            with transaction.atomic():
                for employee in bluebix_employees:
                    try:
                        balance = employee.leave_balance

                        # Calculate current total allocated and used
                        total_allocated = balance.casual_leave_allocated + balance.sick_leave_allocated
                        total_used = balance.casual_leave_used + balance.sick_leave_used

                        self.stdout.write(f"Employee: {employee.user.get_full_name()}")
                        self.stdout.write(
                            f"  Current - CL: {balance.casual_leave_allocated} allocated, {balance.casual_leave_used} used"
                        )
                        self.stdout.write(
                            f"  Current - SL: {balance.sick_leave_allocated} allocated, {balance.sick_leave_used} used"
                        )
                        self.stdout.write(f"  Combined - Total: {total_allocated} allocated, {total_used} used")

                        if not dry_run:
                            # Migrate to combined system
                            balance.combined_sick_casual_allocated = total_allocated
                            balance.combined_sick_casual_used = total_used

                            # Reset individual allocations to 0 for Bluebix
                            balance.casual_leave_allocated = 0.0
                            balance.sick_leave_allocated = 0.0
                            balance.casual_leave_used = 0.0
                            balance.sick_leave_used = 0.0

                            balance.save()

                        migrated_count += 1
                        self.stdout.write(self.style.SUCCESS("  ✅ Migrated"))

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"  ❌ Error migrating {employee.user.get_full_name()}: {str(e)}")
                        )

            if dry_run:
                self.stdout.write(self.style.WARNING(f"DRY RUN: Would migrate {migrated_count} Bluebix employees"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully migrated {migrated_count} Bluebix employees to combined leave system"
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during migration: {str(e)}"))
