from django.core.management.base import BaseCommand
from django.db.models import Sum
from employees.models import Employee, LeaveBalance, LeaveRequest
from datetime import date


class Command(BaseCommand):
    help = 'Recalculate leave balances based on actual approved leave requests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making actual changes',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Recalculate for specific employee badge ID only',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        employee_id = options.get('employee_id')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Get employees to process
        employees = Employee.objects.all()
        if employee_id:
            employees = employees.filter(badge_id=employee_id)
            
        if not employees.exists():
            self.stdout.write(self.style.ERROR('No employees found'))
            return
            
        self.stdout.write(f'Processing {employees.count()} employees...\n')
        
        fixed_count = 0
        current_year = date.today().year
        
        for employee in employees:
            # Get or create leave balance
            leave_balance, created = LeaveBalance.objects.get_or_create(
                employee=employee,
                defaults={
                    'casual_leave_allocated': 0.0 if self.is_probation_employee(employee) else 12.0,
                    'sick_leave_allocated': 0.0 if self.is_probation_employee(employee) else 12.0,
                    'casual_leave_used': 0.0,
                    'sick_leave_used': 0.0,
                    'unpaid_leave': 0.0,
                }
            )
            
            # Calculate actual used leaves from approved requests (current year)
            approved_requests = LeaveRequest.objects.filter(
                employee=employee,
                status='APPROVED',
                start_date__year=current_year
            )
            
            # Calculate used leaves by type
            actual_cl_used = 0.0
            actual_sl_used = 0.0
            actual_ul_used = 0.0
            
            for request in approved_requests:
                days = request.total_days
                
                if request.leave_type == 'CL':
                    actual_cl_used += days
                elif request.leave_type == 'SL':
                    actual_sl_used += days
                elif request.leave_type == 'UL':
                    actual_ul_used += days
            
            # Check if recalculation is needed
            needs_update = False
            changes = []
            
            if leave_balance.casual_leave_used != actual_cl_used:
                changes.append(f"CL used: {leave_balance.casual_leave_used} → {actual_cl_used}")
                needs_update = True
                
            if leave_balance.sick_leave_used != actual_sl_used:
                changes.append(f"SL used: {leave_balance.sick_leave_used} → {actual_sl_used}")
                needs_update = True
                
            if leave_balance.unpaid_leave != actual_ul_used:
                changes.append(f"UL used: {leave_balance.unpaid_leave} → {actual_ul_used}")
                needs_update = True
            
            # Check allocation for probation employees
            expected_allocation = 0.0 if self.is_probation_employee(employee) else 12.0
            if leave_balance.casual_leave_allocated != expected_allocation:
                changes.append(f"CL allocated: {leave_balance.casual_leave_allocated} → {expected_allocation}")
                needs_update = True
                
            if leave_balance.sick_leave_allocated != expected_allocation:
                changes.append(f"SL allocated: {leave_balance.sick_leave_allocated} → {expected_allocation}")
                needs_update = True
            
            if needs_update:
                self.stdout.write(f'\n{employee.user.get_full_name()} ({employee.badge_id or f"EMP-{employee.id}"}):')
                for change in changes:
                    self.stdout.write(f'  - {change}')
                
                # Calculate new balances
                new_cl_balance = expected_allocation - actual_cl_used
                new_sl_balance = expected_allocation - actual_sl_used
                
                self.stdout.write(f'  - CL balance: {leave_balance.casual_leave_balance} → {new_cl_balance}')
                self.stdout.write(f'  - SL balance: {leave_balance.sick_leave_balance} → {new_sl_balance}')
                
                if not dry_run:
                    # Update the leave balance
                    leave_balance.casual_leave_allocated = expected_allocation
                    leave_balance.sick_leave_allocated = expected_allocation
                    leave_balance.casual_leave_used = actual_cl_used
                    leave_balance.sick_leave_used = actual_sl_used
                    leave_balance.unpaid_leave = actual_ul_used
                    leave_balance.save()
                    
                    self.stdout.write(self.style.SUCCESS('  ✓ Updated'))
                else:
                    self.stdout.write(self.style.WARNING('  (would be updated)'))
                
                fixed_count += 1
        
        if fixed_count == 0:
            self.stdout.write(self.style.SUCCESS('\nNo discrepancies found. All leave balances are correct.'))
        else:
            if dry_run:
                self.stdout.write(self.style.WARNING(f'\nFound {fixed_count} employees with discrepancies.'))
                self.stdout.write('Run without --dry-run to apply changes.')
            else:
                self.stdout.write(self.style.SUCCESS(f'\nSuccessfully fixed {fixed_count} employee leave balances.'))

    def is_probation_employee(self, employee):
        """Check if employee is still in probation period (first 90 days)"""
        if not employee.date_of_joining:
            return False
            
        from datetime import timedelta
        probation_end = employee.date_of_joining + timedelta(days=90)
        return date.today() <= probation_end