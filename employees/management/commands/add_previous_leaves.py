from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveBalance
from companies.models import Company


class Command(BaseCommand):
    help = "Add previous/carry-forward leaves to employee balances (Admin tool)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--employee-id", type=int, help="Add leaves for specific employee ID only"
        )
        parser.add_argument(
            "--company-id",
            type=int,
            help="Add leaves for all employees in specific company",
        )
        parser.add_argument(
            "--casual-leave",
            type=float,
            default=0.0,
            help="Casual leave to add (can be decimal like 2.5)",
        )
        parser.add_argument(
            "--sick-leave",
            type=float,
            default=0.0,
            help="Sick leave to add (can be decimal like 1.5)",
        )
        parser.add_argument(
            "--earned-leave",
            type=float,
            default=0.0,
            help="Earned leave to add (can be decimal like 3.0)",
        )
        parser.add_argument(
            "--comp-off",
            type=float,
            default=0.0,
            help="Comp off to add (can be decimal like 1.0)",
        )
        parser.add_argument(
            "--reason",
            type=str,
            default="Previous/Carry-forward leaves",
            help="Reason for adding leaves (for audit trail)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        employee_id = options.get("employee_id")
        company_id = options.get("company_id")
        casual_leave = options.get("casual_leave", 0.0)
        sick_leave = options.get("sick_leave", 0.0)
        earned_leave = options.get("earned_leave", 0.0)
        comp_off = options.get("comp_off", 0.0)
        reason = options.get("reason", "Previous/Carry-forward leaves")
        dry_run = options.get("dry_run", False)

        # Validate input
        if not employee_id and not company_id:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Please specify either --employee-id or --company-id"
                )
            )
            return

        if (
            casual_leave == 0
            and sick_leave == 0
            and earned_leave == 0
            and comp_off == 0
        ):
            self.stdout.write(
                self.style.ERROR("❌ Please specify at least one leave type to add")
            )
            return

        # Get employees to process
        if employee_id:
            try:
                employees = Employee.objects.filter(id=employee_id, is_active=True)
                if not employees.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ Employee with ID {employee_id} not found or inactive"
                        )
                    )
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error finding employee: {e}"))
                return
        elif company_id:
            try:
                company = Company.objects.get(id=company_id)
                employees = Employee.objects.filter(company=company, is_active=True)
                if not employees.exists():
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ No active employees found for company {company.name}"
                        )
                    )
                    return
            except Company.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ Company with ID {company_id} not found")
                )
                return

        # Show what will be added
        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN - Showing what would be added")
            )
        else:
            self.stdout.write("💰 Adding previous/carry-forward leaves")

        self.stdout.write(f"📝 Reason: {reason}")
        self.stdout.write("📊 Leaves to add:")
        if casual_leave > 0:
            self.stdout.write(f"   • Casual Leave: +{casual_leave}")
        if sick_leave > 0:
            self.stdout.write(f"   • Sick Leave: +{sick_leave}")
        if earned_leave > 0:
            self.stdout.write(f"   • Earned Leave: +{earned_leave}")
        if comp_off > 0:
            self.stdout.write(f"   • Comp Off: +{comp_off}")

        total_updated = 0

        # Process each employee
        for employee in employees:
            # Get or create leave balance
            leave_balance, created = LeaveBalance.objects.get_or_create(
                employee=employee,
                defaults={
                    "casual_leave_allocated": 0.0,
                    "sick_leave_allocated": 0.0,
                    "earned_leave_allocated": 0.0,
                    "comp_off_allocated": 0.0,
                    "casual_leave_used": 0.0,
                    "sick_leave_used": 0.0,
                    "earned_leave_used": 0.0,
                    "comp_off_used": 0.0,
                    "unpaid_leave": 0.0,
                    "carry_forward_leave": 0.0,
                    "lapsed_leave": 0.0,
                },
            )

            # Store original values
            original_cl = leave_balance.casual_leave_allocated
            original_sl = leave_balance.sick_leave_allocated
            original_el = leave_balance.earned_leave_allocated
            original_co = leave_balance.comp_off_allocated

            # Calculate new values
            new_cl = original_cl + casual_leave
            new_sl = original_sl + sick_leave
            new_el = original_el + earned_leave
            new_co = original_co + comp_off

            # Show changes
            changes = []
            if casual_leave > 0:
                changes.append(f"CL: {original_cl} → {new_cl} (+{casual_leave})")
            if sick_leave > 0:
                changes.append(f"SL: {original_sl} → {new_sl} (+{sick_leave})")
            if earned_leave > 0:
                changes.append(f"EL: {original_el} → {new_el} (+{earned_leave})")
            if comp_off > 0:
                changes.append(f"CO: {original_co} → {new_co} (+{comp_off})")

            self.stdout.write(
                f"   {employee.user.get_full_name()} ({employee.company.name}): {', '.join(changes)}"
            )

            # Apply changes if not dry run
            if not dry_run:
                leave_balance.casual_leave_allocated = new_cl
                leave_balance.sick_leave_allocated = new_sl
                leave_balance.earned_leave_allocated = new_el
                leave_balance.comp_off_allocated = new_co

                # Update carry_forward_leave field for audit trail
                leave_balance.carry_forward_leave += (
                    casual_leave + sick_leave + earned_leave + comp_off
                )

                leave_balance.save()

            total_updated += 1

        # Summary
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n🔍 DRY RUN COMPLETE - Would update {total_updated} employees"
                )
            )
            self.stdout.write(
                self.style.SUCCESS("To apply changes, remove --dry-run flag")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n🎉 Successfully added previous leaves to {total_updated} employees!"
                )
            )

        # Show usage examples
        if dry_run or total_updated > 0:
            self.stdout.write("\n📚 USAGE EXAMPLES:")
            self.stdout.write("   # Add 5 CL and 3 SL to specific employee")
            self.stdout.write(
                "   python manage.py add_previous_leaves --employee-id 1 --casual-leave 5 --sick-leave 3"
            )
            self.stdout.write("   ")
            self.stdout.write("   # Add 2.5 CL to all employees in company")
            self.stdout.write(
                "   python manage.py add_previous_leaves --company-id 1 --casual-leave 2.5"
            )
            self.stdout.write("   ")
            self.stdout.write("   # Test before applying (dry run)")
            self.stdout.write(
                "   python manage.py add_previous_leaves --employee-id 1 --casual-leave 5 --dry-run"
            )

        # Show integration note
        if not dry_run and total_updated > 0:
            self.stdout.write("\n✅ INTEGRATION NOTE:")
            self.stdout.write(
                "   • These manual adjustments will be preserved during monthly accrual"
            )
            self.stdout.write(
                "   • Monthly accrual will ADD to these balances, not overwrite them"
            )
            self.stdout.write(
                "   • Changes are tracked in carry_forward_leave field for audit"
            )
