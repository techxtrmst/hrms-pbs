from django.core.management.base import BaseCommand
from employees.models import LeaveBalance, LeaveRequest
from loguru import logger


class Command(BaseCommand):
    help = "Fix LOP balances for users who have incorrect leave deductions"

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

        # Get all leave balances
        leave_balances = LeaveBalance.objects.all()
        fixed_count = 0

        for balance in leave_balances:
            employee_name = balance.employee.user.get_full_name()

            # Get all approved leave requests for this employee
            approved_leaves = LeaveRequest.objects.filter(
                employee=balance.employee, status="APPROVED"
            )

            # Calculate totals by leave type
            total_cl_approved = sum(
                leave.total_days
                for leave in approved_leaves
                if leave.leave_type == "CL"
            )
            total_sl_approved = sum(
                leave.total_days
                for leave in approved_leaves
                if leave.leave_type == "SL"
            )
            total_el_approved = sum(
                leave.total_days
                for leave in approved_leaves
                if leave.leave_type == "EL"
            )
            total_co_approved = sum(
                leave.total_days
                for leave in approved_leaves
                if leave.leave_type == "CO"
            )
            total_ul_approved = sum(
                leave.total_days
                for leave in approved_leaves
                if leave.leave_type == "UL"
            )

            # Calculate what the balances should be
            cl_should_use = min(total_cl_approved, balance.casual_leave_allocated)
            cl_excess = max(0, total_cl_approved - balance.casual_leave_allocated)

            sl_should_use = min(total_sl_approved, balance.sick_leave_allocated)
            sl_excess = max(0, total_sl_approved - balance.sick_leave_allocated)

            el_should_use = min(total_el_approved, balance.earned_leave_allocated)
            el_excess = max(0, total_el_approved - balance.earned_leave_allocated)

            co_should_use = min(total_co_approved, balance.comp_off_allocated)
            co_excess = max(0, total_co_approved - balance.comp_off_allocated)

            # Total LOP should be all excess + direct UL
            total_lop_should_be = (
                cl_excess + sl_excess + el_excess + co_excess + total_ul_approved
            )

            # Check if fix is needed
            needs_fix = (
                balance.casual_leave_used != cl_should_use
                or balance.sick_leave_used != sl_should_use
                or balance.earned_leave_used != el_should_use
                or balance.comp_off_used != co_should_use
                or balance.unpaid_leave != total_lop_should_be
            )

            if needs_fix:
                self.stdout.write(f"Found incorrect balances for {employee_name}:")
                self.stdout.write(
                    f"  CL: Used {balance.casual_leave_used} → Should be {cl_should_use}"
                )
                self.stdout.write(
                    f"  SL: Used {balance.sick_leave_used} → Should be {sl_should_use}"
                )
                self.stdout.write(
                    f"  EL: Used {balance.earned_leave_used} → Should be {el_should_use}"
                )
                self.stdout.write(
                    f"  CO: Used {balance.comp_off_used} → Should be {co_should_use}"
                )
                self.stdout.write(
                    f"  LOP: {balance.unpaid_leave} → Should be {total_lop_should_be}"
                )

                if not dry_run:
                    # Fix the balances
                    balance.casual_leave_used = cl_should_use
                    balance.sick_leave_used = sl_should_use
                    balance.earned_leave_used = el_should_use
                    balance.comp_off_used = co_should_use
                    balance.unpaid_leave = total_lop_should_be
                    balance.save()

                    self.stdout.write(
                        self.style.SUCCESS(f"Fixed balances for {employee_name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Would fix balances for {employee_name}")
                    )

                fixed_count += 1

        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS("No incorrect balances found!"))
        else:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"Would fix {fixed_count} employees with incorrect balances"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fixed incorrect balances for {fixed_count} employees"
                    )
                )
