from django.core.management.base import BaseCommand
from django.db import transaction

from employees.models import Employee


class Command(BaseCommand):
    help = "Set initial combined sick/casual leave allocation for Bluebix employees to 1 day"

    def add_arguments(self, parser):
        parser.add_argument(
            "--allocation",
            type=float,
            default=1.0,
            help="Combined sick/casual leave allocation (default: 1.0)",
        )

    def handle(self, *args, **options):
        allocation = options.get("allocation", 1.0)

        self.stdout.write(self.style.SUCCESS(f"Setting Bluebix combined leave allocation to {allocation} days..."))

        try:
            # Get all Bluebix employees
            bluebix_employees = Employee.objects.filter(company__name__icontains="bluebix")

            if not bluebix_employees.exists():
                self.stdout.write(self.style.WARNING("No Bluebix employees found"))
                return

            updated_count = 0

            with transaction.atomic():
                for employee in bluebix_employees:
                    try:
                        balance = employee.leave_balance

                        # Set the combined allocation
                        balance.combined_sick_casual_allocated = allocation
                        balance.save()

                        self.stdout.write(
                            f"✅ {employee.user.get_full_name()}: Set combined allocation to {allocation}"
                        )
                        updated_count += 1

                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"❌ Error updating {employee.user.get_full_name()}: {str(e)}")
                        )

            self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} Bluebix employees"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during update: {str(e)}"))
