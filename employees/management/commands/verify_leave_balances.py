from django.core.management.base import BaseCommand
from django.db import transaction
from employees.models import Employee, LeaveBalance
from loguru import logger


class Command(BaseCommand):
    help = 'Verify and fix leave balance consistency after bulk uploads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=int,
            help='Verify leave balances for a specific company only',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix any inconsistencies found',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        fix_issues = options.get('fix', False)
        
        self.stdout.write("Starting leave balance verification...")
        
        # Get employees to check
        employees = Employee.objects.all()
        if company_id:
            employees = employees.filter(company_id=company_id)
        
        issues_found = 0
        issues_fixed = 0
        
        with transaction.atomic():
            for employee in employees:
                try:
                    # Get or create leave balance
                    leave_balance, created = LeaveBalance.objects.get_or_create(
                        employee=employee,
                        defaults={
                            'casual_leave_allocated': 0.0,
                            'sick_leave_allocated': 0.0,
                            'casual_leave_used': 0.0,
                            'sick_leave_used': 0.0,
                            'carry_forward_leave': 0.0
                        }
                    )
                    
                    if created:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Created missing leave balance for {employee.user.get_full_name()}"
                            )
                        )
                        issues_found += 1
                        if fix_issues:
                            issues_fixed += 1
                    
                    # Check for negative values
                    has_negative = False
                    if leave_balance.casual_leave_allocated < 0:
                        self.stdout.write(
                            self.style.ERROR(
                                f"{employee.user.get_full_name()}: Negative casual leave allocated: {leave_balance.casual_leave_allocated}"
                            )
                        )
                        has_negative = True
                        issues_found += 1
                        
                    if leave_balance.sick_leave_allocated < 0:
                        self.stdout.write(
                            self.style.ERROR(
                                f"{employee.user.get_full_name()}: Negative sick leave allocated: {leave_balance.sick_leave_allocated}"
                            )
                        )
                        has_negative = True
                        issues_found += 1
                        
                    if leave_balance.casual_leave_used < 0:
                        self.stdout.write(
                            self.style.ERROR(
                                f"{employee.user.get_full_name()}: Negative casual leave used: {leave_balance.casual_leave_used}"
                            )
                        )
                        has_negative = True
                        issues_found += 1
                        
                    if leave_balance.sick_leave_used < 0:
                        self.stdout.write(
                            self.style.ERROR(
                                f"{employee.user.get_full_name()}: Negative sick leave used: {leave_balance.sick_leave_used}"
                            )
                        )
                        has_negative = True
                        issues_found += 1
                    
                    # Fix negative values if requested
                    if has_negative and fix_issues:
                        leave_balance.validate_and_save()
                        issues_fixed += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fixed negative values for {employee.user.get_full_name()}"
                            )
                        )
                    
                    # Check for unrealistic values (more than 365 days)
                    if leave_balance.casual_leave_allocated > 365:
                        self.stdout.write(
                            self.style.WARNING(
                                f"{employee.user.get_full_name()}: Unusually high casual leave allocated: {leave_balance.casual_leave_allocated}"
                            )
                        )
                        issues_found += 1
                        
                    if leave_balance.sick_leave_allocated > 365:
                        self.stdout.write(
                            self.style.WARNING(
                                f"{employee.user.get_full_name()}: Unusually high sick leave allocated: {leave_balance.sick_leave_allocated}"
                            )
                        )
                        issues_found += 1
                    
                    # Log current balance for verification
                    self.stdout.write(
                        f"{employee.user.get_full_name()}: "
                        f"CL: {leave_balance.casual_leave_allocated}/{leave_balance.casual_leave_used} "
                        f"(Balance: {leave_balance.casual_leave_balance}), "
                        f"SL: {leave_balance.sick_leave_allocated}/{leave_balance.sick_leave_used} "
                        f"(Balance: {leave_balance.sick_leave_balance}), "
                        f"CF: {leave_balance.carry_forward_leave}"
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing {employee.user.get_full_name()}: {str(e)}"
                        )
                    )
                    issues_found += 1
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write(f"Verification completed for {employees.count()} employees")
        
        if issues_found > 0:
            self.stdout.write(
                self.style.WARNING(f"Issues found: {issues_found}")
            )
            if fix_issues:
                self.stdout.write(
                    self.style.SUCCESS(f"Issues fixed: {issues_fixed}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Run with --fix to automatically fix issues")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("No issues found! All leave balances are consistent.")
            )
        
        logger.info(f"Leave balance verification completed: {issues_found} issues found, {issues_fixed} fixed")