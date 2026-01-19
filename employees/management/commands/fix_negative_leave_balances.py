from django.core.management.base import BaseCommand
from employees.models import LeaveBalance
from loguru import logger


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
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        # Get all leave balances with potential negative balances
        leave_balances = LeaveBalance.objects.all()
        fixed_count = 0

        for balance in leave_balances:
            employee_name = balance.employee.user.get_full_name()

            # Check for negative balances
            issues = []
            if balance.casual_leave_balance < 0:
                issues.append(f"CL: {balance.casual_leave_balance}")
            if balance.sick_leave_balance < 0:
                issues.append(f"SL: {balance.sick_leave_balance}")
            if balance.earned_leave_balance < 0:
                issues.append(f"EL: {balance.earned_leave_balance}")
            if balance.comp_off_balance < 0:
                issues.append(f"CO: {balance.comp_off_balance}")

            if issues:
                self.stdout.write(
                    f"Found negative balances for {employee_name}: {', '.join(issues)}"
                )

                if not dry_run:
                    # Fix the negative balances
                    old_lop = balance.unpaid_leave
                    if balance.fix_negative_balances():
                        new_lop = balance.unpaid_leave
                        lop_added = new_lop - old_lop
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fixed {employee_name}: Added {lop_added} days to LOP"
                            )
                        )
                        fixed_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Would fix negative balances for {employee_name}"
                        )
                    )
                    fixed_count += 1

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS("No negative balances found!"))
        else:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"Would fix {fixed_count} employees with negative balances"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fixed negative balances for {fixed_count} employees"
                    )
                )
