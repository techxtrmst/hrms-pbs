from django.core.management.base import BaseCommand
from django.utils import timezone
from employees.models import Employee, LeaveBalance
from companies.models import Company
from datetime import date


class Command(BaseCommand):
    help = 'Accrue monthly leaves for employees based on company-specific rules (preserves admin manual adjustments)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month to accrue leaves for (1-12, default: current month)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to accrue leaves for (default: current year)'
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Accrue leaves for specific company ID only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--preserve-manual',
            action='store_true',
            default=True,
            help='Preserve manual adjustments made by admin (default: True)'
        )

    def handle(self, *args, **options):
        # Get target month/year
        current_date = date.today()
        target_month = options.get('month') or current_date.month
        target_year = options.get('year') or current_date.year
        company_id = options.get('company_id')
        dry_run = options.get('dry_run', False)
        preserve_manual = options.get('preserve_manual', True)
        
        # Company-specific leave allocation rules
        leave_allocation_rules = {
            'Petabytz': {
                'casual_leave_monthly': 1.0,  # 1 CL per month
                'sick_leave_monthly': 1.0,    # 1 SL per month
            },
            'SoftStandards': {
                'casual_leave_monthly': 0.5,  # 0.5 CL per month
                'sick_leave_monthly': 0.5,    # 0.5 SL per month
            },
            'Bluebix': {
                'casual_leave_monthly': 0.5,  # 0.5 CL per month
                'sick_leave_monthly': 0.5,    # 0.5 SL per month
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
        
        target_date_str = f"{target_month:02d}/{target_year}"
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'🔍 DRY RUN - Showing what would be accrued for {target_date_str}'))
        else:
            self.stdout.write(f'💰 Accruing monthly leaves for {target_date_str}')
        
        if preserve_manual:
            self.stdout.write(self.style.SUCCESS('✅ Manual admin adjustments will be preserved'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Manual admin adjustments will be overwritten'))
        
        total_updated = 0
        
        for company in companies:
            company_name = company.name
            
            # Get allocation rules for this company
            if company_name in leave_allocation_rules:
                rules = leave_allocation_rules[company_name]
            else:
                # Skip companies without defined rules
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Skipping {company_name} - no leave rules defined'
                    )
                )
                continue
            
            self.stdout.write(f'\n📍 Processing Company: {company_name}')
            self.stdout.write(f'   Monthly allocation: {rules["casual_leave_monthly"]} CL + {rules["sick_leave_monthly"]} SL')
            
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
                
                # Store original values for comparison
                original_cl = leave_balance.casual_leave_allocated
                original_sl = leave_balance.sick_leave_allocated
                
                if preserve_manual:
                    # Add monthly accrual to existing balance (preserves manual adjustments)
                    new_cl = leave_balance.casual_leave_allocated + rules['casual_leave_monthly']
                    new_sl = leave_balance.sick_leave_allocated + rules['sick_leave_monthly']
                else:
                    # Calculate expected total based on months (overwrites manual adjustments)
                    # Calculate months from January 2026 to target month
                    start_month = date(2026, 1, 1)
                    target_date = date(target_year, target_month, 1)
                    months_elapsed = (target_date.year - start_month.year) * 12 + (target_date.month - start_month.month) + 1
                    
                    new_cl = rules['casual_leave_monthly'] * months_elapsed
                    new_sl = rules['sick_leave_monthly'] * months_elapsed
                
                # Show what would be done
                if preserve_manual:
                    self.stdout.write(
                        f'   {employee.user.get_full_name()}: '
                        f'CL {original_cl} → {new_cl} (+{rules["casual_leave_monthly"]}), '
                        f'SL {original_sl} → {new_sl} (+{rules["sick_leave_monthly"]}) '
                        f'[Manual adjustments preserved]'
                    )
                else:
                    self.stdout.write(
                        f'   {employee.user.get_full_name()}: '
                        f'CL {original_cl} → {new_cl}, '
                        f'SL {original_sl} → {new_sl} '
                        f'[Calculated total - manual adjustments overwritten]'
                    )
                
                # Apply changes if not dry run
                if not dry_run:
                    leave_balance.casual_leave_allocated = new_cl
                    leave_balance.sick_leave_allocated = new_sl
                    leave_balance.save()
                
                company_updated += 1
                total_updated += 1
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'   🔍 Would update {company_updated} employees for {company_name}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'   ✅ Updated {company_updated} employees for {company_name}'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY RUN COMPLETE - Would update {total_updated} employees'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'To apply changes, run: python manage.py accrue_monthly_leaves_by_company --month {target_month} --year {target_year}'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n🎉 Monthly leave accrual completed! Updated {total_updated} employees'
                )
            )
        
        # Show updated summary
        if not dry_run:
            self.stdout.write(f'\n📊 UPDATED LEAVE BALANCES:')
            for company in companies:
                company_name = company.name
                if company_name in leave_allocation_rules:
                    employees = Employee.objects.filter(company=company, is_active=True)
                    if employees.exists():
                        sample_balance = LeaveBalance.objects.filter(employee__company=company).first()
                        if sample_balance:
                            self.stdout.write(
                                f'   {company_name}: CL={sample_balance.casual_leave_allocated}, '
                                f'SL={sample_balance.sick_leave_allocated} '
                                f'(Sample from {sample_balance.employee.user.get_full_name()})'
                            )
        
        # Show admin guidance
        if not dry_run and preserve_manual:
            self.stdout.write(f'\n📝 ADMIN GUIDANCE:')
            self.stdout.write(f'   • Manual leave adjustments made via Django Admin are preserved')
            self.stdout.write(f'   • To add previous/carry-forward leaves: Edit individual employee leave balances in Admin')
            self.stdout.write(f'   • To override manual adjustments: Use --preserve-manual=False flag')
            self.stdout.write(f'   • Monthly accrual will continue to add to existing balances')