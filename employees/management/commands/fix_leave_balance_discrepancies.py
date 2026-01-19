"""
Management command to fix leave balance discrepancies by recalculating 
used fields based on actual approved leave requests.
"""
from django.core.management.base import BaseCommand
from employees.models import Employee, LeaveRequest, LeaveBalance
from django.db.models import Sum
from django.db import transaction


class Command(BaseCommand):
    help = 'Fix leave balance discrepancies by recalculating used fields from approved leave requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )
        parser.add_argument(
            '--employee-id',
            type=int,
            help='Fix only specific employee by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        employee_id = options.get('employee_id')
        
        self.stdout.write("=" * 80)
        self.stdout.write("LEAVE BALANCE DISCREPANCY FIX")
        self.stdout.write("=" * 80)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Get employees to process
        if employee_id:
            try:
                employees = [Employee.objects.get(id=employee_id)]
                self.stdout.write(f"Processing specific employee ID: {employee_id}")
            except Employee.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Employee with ID {employee_id} not found"))
                return
        else:
            employees = Employee.objects.filter(is_active=True).select_related('user')
            self.stdout.write(f"Processing {employees.count()} active employees")
        
        fixed_count = 0
        error_count = 0
        
        for employee in employees:
            try:
                with transaction.atomic():
                    # Get or create leave balance
                    balance, created = LeaveBalance.objects.get_or_create(
                        employee=employee,
                        defaults={
                            'casual_leave_allocated': 0.0,
                            'sick_leave_allocated': 0.0,
                        }
                    )
                    
                    if created:
                        self.stdout.write(f"Created new leave balance for {employee.user.get_full_name()}")
                    
                    # Calculate actual approved leave usage
                    # Since total_days is a property, we need to calculate manually
                    approved_cl_requests = LeaveRequest.objects.filter(
                        employee=employee,
                        status='APPROVED',
                        leave_type='CL'
                    )
                    approved_cl = sum(req.total_days for req in approved_cl_requests)
                    
                    approved_sl_requests = LeaveRequest.objects.filter(
                        employee=employee,
                        status='APPROVED',
                        leave_type='SL'
                    )
                    approved_sl = sum(req.total_days for req in approved_sl_requests)
                    
                    approved_ul_requests = LeaveRequest.objects.filter(
                        employee=employee,
                        status='APPROVED',
                        leave_type='UL'
                    )
                    approved_ul = sum(req.total_days for req in approved_ul_requests)
                    
                    # Check for discrepancies
                    cl_discrepancy = balance.casual_leave_used != approved_cl
                    sl_discrepancy = balance.sick_leave_used != approved_sl
                    ul_discrepancy = balance.unpaid_leave != approved_ul
                    
                    if cl_discrepancy or sl_discrepancy or ul_discrepancy:
                        self.stdout.write(f"\n👤 {employee.user.get_full_name()}")
                        self.stdout.write("-" * 60)
                        
                        if cl_discrepancy:
                            self.stdout.write(
                                f"   CL: {balance.casual_leave_used} → {approved_cl} "
                                f"(diff: {approved_cl - balance.casual_leave_used})"
                            )
                        
                        if sl_discrepancy:
                            self.stdout.write(
                                f"   SL: {balance.sick_leave_used} → {approved_sl} "
                                f"(diff: {approved_sl - balance.sick_leave_used})"
                            )
                        
                        if ul_discrepancy:
                            self.stdout.write(
                                f"   UL: {balance.unpaid_leave} → {approved_ul} "
                                f"(diff: {approved_ul - balance.unpaid_leave})"
                            )
                        
                        # Show current vs corrected balances
                        current_cl_balance = balance.casual_leave_allocated - balance.casual_leave_used
                        corrected_cl_balance = balance.casual_leave_allocated - approved_cl
                        
                        current_sl_balance = balance.sick_leave_allocated - balance.sick_leave_used
                        corrected_sl_balance = balance.sick_leave_allocated - approved_sl
                        
                        self.stdout.write(f"   CL Balance: {current_cl_balance} → {corrected_cl_balance}")
                        self.stdout.write(f"   SL Balance: {current_sl_balance} → {corrected_sl_balance}")
                        
                        if not dry_run:
                            # Apply the corrections
                            balance.casual_leave_used = approved_cl
                            balance.sick_leave_used = approved_sl
                            balance.unpaid_leave = approved_ul
                            balance.save()
                            
                            self.stdout.write(self.style.SUCCESS("   ✅ Fixed"))
                        else:
                            self.stdout.write(self.style.WARNING("   📝 Would be fixed"))
                        
                        fixed_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error processing {employee.user.get_full_name()}: {e}")
                )
                error_count += 1
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Employees with discrepancies: {fixed_count}")
        self.stdout.write(f"Errors encountered: {error_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("No changes were made (dry run mode)"))
            self.stdout.write("Run without --dry-run to apply fixes")
        else:
            self.stdout.write(self.style.SUCCESS("All discrepancies have been fixed!"))
        
        self.stdout.write("=" * 80)