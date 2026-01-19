from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveRequest, LeaveBalance
from django.db import transaction


class Command(BaseCommand):
    help = "Fix LOP calculation for all employees based on approved leave requests"

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

        employees = Employee.objects.all()
        fixed_count = 0

        for employee in employees:
            try:
                balance = employee.leave_balance

                # Calculate expected LOP based on approved leave requests
                expected_lop = self.calculate_expected_lop(employee)
                current_lop = balance.unpaid_leave

                if current_lop != expected_lop:
                    self.stdout.write(f"Employee: {employee.user.get_full_name()}")
                    self.stdout.write(
                        f"  Current LOP: {current_lop}, Expected LOP: {expected_lop}"
                    )

                    if not dry_run:
                        with transaction.atomic():
                            balance.unpaid_leave = expected_lop
                            balance.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✅ Fixed LOP for {employee.user.get_full_name()}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Would fix LOP for {employee.user.get_full_name()}"
                            )
                        )

                    fixed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing {employee.user.get_full_name()}: {e}"
                    )
                )

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ All LOP calculations are correct"))
        else:
            action = "Would fix" if dry_run else "Fixed"
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {action} LOP calculation for {fixed_count} employees"
                )
            )

    def calculate_expected_lop(self, employee):
        """Calculate expected LOP based on approved leave requests"""
        balance = employee.leave_balance
        expected_lop = 0.0

        # Get all approved leave requests
        approved_leaves = LeaveRequest.objects.filter(
            employee=employee, status="APPROVED"
        )

        # Track usage by leave type
        cl_used = 0.0
        sl_used = 0.0
        ul_used = 0.0

        for leave in approved_leaves:
            days = leave.total_days

            if leave.leave_type == "CL":
                if cl_used + days <= balance.casual_leave_allocated:
                    cl_used += days
                else:
                    # Excess goes to LOP
                    available = max(0, balance.casual_leave_allocated - cl_used)
                    cl_used += available
                    expected_lop += days - available

            elif leave.leave_type == "SL":
                if sl_used + days <= balance.sick_leave_allocated:
                    sl_used += days
                else:
                    # Excess goes to LOP
                    available = max(0, balance.sick_leave_allocated - sl_used)
                    sl_used += available
                    expected_lop += days - available

            elif leave.leave_type == "UL":
                expected_lop += days

        return expected_lop
