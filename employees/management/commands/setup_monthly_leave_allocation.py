from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, LeaveBalance
from companies.models import Company
from datetime import date


class Command(BaseCommand):
    help = 'Setup monthly leave allocation system for different companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all existing leave balances to 0 before applying new allocation'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Setup leaves for specific company ID only'
        )

    def handle(self, *args, **options):
        reset_balances = options.get('reset', False)
        company_id = options.get('company_id')
        
        # Company-specific leave allocation rules
        leave_allocation_rules = {
            'Petabytz': {
                'casual_leave_monthly': 1.0,  # 1 CL per month
                'sick_leave_monthly': 1.0,    # 1 SL per month
                'earned_leave_monthly': 0.0,  # No EL monthly accrual
            },
            'SoftStandards': {
                'casual_leave_monthly': 0.5,  # 0.5 CL per month
                'sick_leave_monthly': 0.5,    # 0.5 SL per month
                'earned_leave_monthly': 0.0,  # No EL monthly accrual
            },
            'Bluebix': {
                'casual_leave_monthly': 0.5,  # 0.5 CL per month
                'sick_leave_monthly': 0.5,    # 0.5 SL per month
                'earned_leave_monthly': 0.0,  # No EL monthly accrual
            }
        }
        
        # Get companies to process
        if company_id:
            companies = Company.objects.filter(id=company_id)
        else:
            companies = Company.objects.all()
        
        if not companies.exists():
            self.stdout.write(self.style.WARNING('No companies found'))
            return
        
        # Calculate months from January 2026 to current month
        current_date = date.today()
        start_month = date(2026, 1, 1)
        
        # Calculate number of months from January 2026 to current month
        months_elapsed = (current_date.year - start_month.year) * 12 + (current_date.month - start_month.month) + 1
        
        self.stdout.write(f'Setting up leave allocation from January 2026 to {current_date.strftime("%B %Y")}')
        self.stdout.write(f'Months to allocate: {months_elapsed}')
        
        total_updated = 0
        
        for company in companies:
            company_name = company.name
            
            # Get allocation rules for this company
            if company_name in leave_allocation_rules:
                rules = leave_allocation_rules[company_name]
            else:
                # Default rules for unknown companies
                rules = {
                    'casual_leave_monthly': 1.0,
                    'sick_leave_monthly': 1.0,
                    'earned_leave_monthly': 0.0,
                }
                self.stdout.write(
                    self.style.WARNING(
                        f'Using default rules for {company_name} (not in predefined rules)'
                    )
                )
            
            self.stdout.write(f'\n📍 Processing Company: {company_name}')
            self.stdout.write(f'   Rules: CL={rules["casual_leave_monthly"]}/month, SL={rules["sick_leave_monthly"]}/month')
            
            # Get active employees for this company
            employees = Employee.objects.filter(company=company, is_active=True)
            company_updated = 0
            
            for employee in employees:
                # Get or create leave balance
                leave_balance, created = LeaveBalance.objects.get_or_create(
                    employee=employee,
                    defaults={
                        'casual_leave_allocated': 0.0,
                        'sick_leave_allocated': 0.0,
                        'earned_leave_allocated': 0.0,
                        'comp_off_allocated': 0.0,
                        'casual_leave_used': 0.0,
                        'sick_leave_used': 0.0,
                        'earned_leave_used': 0.0,
                        'comp_off_used': 0.0,
                        'unpaid_leave': 0.0,
                        'carry_forward_leave': 0.0,
                        'lapsed_leave': 0.0,
                    }
                )
                
                # Reset balances if requested
                if reset_balances:
                    leave_balance.casual_leave_allocated = 0.0
                    leave_balance.sick_leave_allocated = 0.0
                    leave_balance.earned_leave_allocated = 0.0
                    leave_balance.comp_off_allocated = 0.0
                    leave_balance.casual_leave_used = 0.0
                    leave_balance.sick_leave_used = 0.0
                    leave_balance.earned_leave_used = 0.0
                    leave_balance.comp_off_used = 0.0
                    leave_balance.unpaid_leave = 0.0
                    leave_balance.carry_forward_leave = 0.0
                    leave_balance.lapsed_leave = 0.0
                
                # Calculate total allocation based on months elapsed
                total_cl = rules['casual_leave_monthly'] * months_elapsed
                total_sl = rules['sick_leave_monthly'] * months_elapsed
                total_el = rules['earned_leave_monthly'] * months_elapsed
                
                # Update allocations
                leave_balance.casual_leave_allocated = total_cl
                leave_balance.sick_leave_allocated = total_sl
                leave_balance.earned_leave_allocated = total_el
                
                leave_balance.save()
                company_updated += 1
                total_updated += 1
                
                if created:
                    action = 'Created'
                else:
                    action = 'Updated'
                
                self.stdout.write(
                    f'   {action} {employee.user.get_full_name()}: '
                    f'CL={total_cl}, SL={total_sl}, EL={total_el}'
                )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'   ✅ {company_updated} employees updated for {company_name}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n🎉 Total employees updated: {total_updated}'
            )
        )
        
        # Show summary by company
        self.stdout.write(f'\n📊 LEAVE ALLOCATION SUMMARY:')
        for company in companies:
            company_name = company.name
            if company_name in leave_allocation_rules:
                rules = leave_allocation_rules[company_name]
                monthly_cl = rules['casual_leave_monthly']
                monthly_sl = rules['sick_leave_monthly']
                
                total_cl = monthly_cl * months_elapsed
                total_sl = monthly_sl * months_elapsed
                
                employee_count = Employee.objects.filter(company=company, is_active=True).count()
                
                self.stdout.write(
                    f'   {company_name}: {employee_count} employees'
                )
                self.stdout.write(
                    f'     Monthly: {monthly_cl} CL + {monthly_sl} SL'
                )
                self.stdout.write(
                    f'     Total allocated ({months_elapsed} months): {total_cl} CL + {total_sl} SL'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Monthly leave allocation system setup completed!'
            )
        )