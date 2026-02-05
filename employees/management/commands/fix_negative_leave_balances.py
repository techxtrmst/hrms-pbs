from django.core.management.base import BaseCommand

from employees.models import LeaveBalance


class Command(BaseCommand):
    help = "Fix negative leave balances by converting them to LOP"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Get all leave balances
        leave_balances = LeaveBalance.objects.all()
        fixed_count = 0

        for balance in leave_balances:
            employee_name = balance.employee.user.get_full_name()
            company_name = balance.employee.company.name.lower()
            is_combined = company_name in ["bluebix", "softstandard", "softstandard solutions"]

            # Check for negative balances (excess used)
            issues = []
            if is_combined:
                total_allowed = balance.combined_sick_casual_allocated + balance.carry_forward_leave
                if balance.combined_sick_casual_used > total_allowed:
                    diff = balance.combined_sick_casual_used - total_allowed
                    issues.append(f"Combined: {diff} excess")
            else:
                total_cl_allowed = balance.casual_leave_allocated + balance.carry_forward_leave
                if balance.casual_leave_used > total_cl_allowed:
                    diff = balance.casual_leave_used - total_cl_allowed
                    issues.append(f"CL: {diff} excess")

                if balance.sick_leave_used > balance.sick_leave_allocated:
                    diff = balance.sick_leave_used - balance.sick_leave_allocated
                    issues.append(f"SL: {diff} excess")

            if issues:
                self.stdout.write(f"Found negative balances for {employee_name}: {', '.join(issues)}")

                if not dry_run:
                    # Fix the negative balances
                    lop_added = balance.fix_negative_balances()
                    if lop_added > 0:
                        self.stdout.write(self.style.SUCCESS(f"Fixed {employee_name}: Added {lop_added} days to LOP"))
                        fixed_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f"Would fix negative balances for {employee_name}"))
                    fixed_count += 1

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS("No negative balances found!"))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f"Would fix {fixed_count} employees with negative balances"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Fixed negative balances for {fixed_count} employees"))
